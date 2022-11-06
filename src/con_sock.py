import socket
import random
import json
import base58
import struct
import time
import peer
from multiprocessing import Process as Thread, Lock
import multiprocessing
import signal
import sys
from Crypto.Hash import keccak


payload_max = 1024
mutex = Lock()

class node:
    def __init__(self, light: bool):
        self.addr: list[tuple[str, int]] = []
        self.id = ""

        self.gen_addr()
        self.is_light = light

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(self.addr[0])
        self.gen_id(self.server)
        self.peers = peer.Peer_store()

        print("connected as:", self.id)
        self.addr.append((self.addr[0][0], self.addr[0][1]+10))
        self.handlers: dict[str, callable[[str, str]]] = {
                "get_peers": self.handler_peers,
                "peers": self.handler_merge_peers,
                "kill": self.handler_kill
                }
        self.ltn_handlers: dict[str, callable[[socket.socket], bool]] = {
                "get_peers": self.ltn_handler_peers,
                }

    def cleanup(self, signum, frame):
        print("cleaning up...")
        for a in self.peers.get_peers():
            p = self.peers.get_peer(a)
            if p:
                p.msg(b"kill")
        sys.exit()


    def handler_kill(self, msg: str, addr: str):
        print("Closing peer connection:", addr)
        p = self.peers.get_peer(addr)
        if p:
            mutex.acquire()
            p.connection.close()
            self.peers.del_peer(addr)
            p.run = False
            # for proc in multiprocessing.active_children():
            #     if proc.name == p.hash:
            #         proc.terminate()
        mutex.release()
        
    def handler_merge_peers(self, msg: str, addr: str):
        reply_frags = msg.splitlines()
        peer_str = reply_frags[3]
        reply_peers: list = json.loads(base58.b58decode(peer_str))
        for key in reply_peers:
            if key not in self.peers.get_peers() and key != self.id.strip():
                print("new peer (from merge):", key)
                self.peers.add_peer(peer.Peer(self.id, key))


    def ltn_handler_peers(self, con: peer.Peer):
        p = base58.b58encode(json.dumps(list(self.peers.get_peers())))
        con.msg(p)
        return True

    def handler_peers(self, msg: str, addr: str):
        p_list = base58.b58encode(json.dumps(list(self.peers.get_peers())))
        p = self.peers.get_peer(addr)
        if p:
            p.msg(b"peers\n"+p_list)
        return True

    def gen_id(self, server):
        ip, port = server.getsockname()
        if self.is_light:
            self.id = "ltn@"+ip+":"+str(port)
            return
        self.id = random.randbytes(10).hex()+"@"+ip+":"+str(port)

    def gen_addr(self):
        self.addr.append(('', random.randint(8000, 8010)))

    def connect_msg_peer(self, body: str, address: str, reply: bool = True):
        conn = self.make_connection(address)

        conn.send(self.id.encode())
        conn.send(body.encode())

        r = ""
        if reply:
            r = self.read(conn)

        conn.close()
        return r

    def broadcast(self, body: str):
        print("broadcasting ("+str(len(self.peers.peers))+" peer(s)):", body)
        for k in self.peers.get_peers():
            p = self.peers.get_peer(k)
            if p:
                p.msg(body.encode())

    def make_new_connection(self, addr: str):
        p = self.peers.add_peer(peer.Peer(self.id, addr))
        if p:
            p.msg(b"")
            t = Thread(target=self.mainloop, args=[p])
            t.start()

    def mainloop(self, n_peer: peer.Peer):
        mutex.acquire()
        reply = n_peer.read()
        q = [reply]
        global lh
        lh = ""
        while n_peer.run:
            if len(q) != 0:
                reply_frags = str(q.pop()).strip().splitlines()
                lh = reply_frags[1]
                addr = reply_frags[0]
                if addr.split("@")[0] == "ltn":
                    self.ltn_handlers[reply_frags[2]](n_peer)
                    print("processed ltn message")
                    return

                if len(reply_frags) == 2:
                    n_peer.addr = addr
                    print("started listening to peer:", addr)
                    self.peers.add_peer(n_peer)
                    n_peer.msg(b"")
                    mutex.release()
                    n_peer.msg(b"get_peers")
                elif len(reply_frags) > 1:
                    self.handlers[reply_frags[2]]("\n".join(reply_frags), addr)
            else:
                r = n_peer.read()
                if r:
                    if r.strip().splitlines()[1] != lh:
                        q.append(r)


    # def inbound_con(self, conn: socket.socket):
    #     reply = self.read(conn)
    #     reply_frags = str(reply).splitlines()
    #     addr = reply_frags[0]
    #     if addr.split("@")[0] == "ltn":
    #         self.ltn_handlers[reply_frags[1]](conn)
    #         conn.close()
    #         return
    #
    #     if len(reply_frags) == 1 and addr not in self.peers.get_peers():
    #         p = self.peers.add_peer(peer.Peer(self.id, addr))
    #         print("new peer:", addr)
    #         if p:
    #             p.msg(b"")
    #             # self.msg_peer("get_peers", self.peers[addr], False)
    #         return
    #     elif len(reply_frags) > 1:
    #         self.handlers[reply_frags[1]](reply, addr)

    def light_rep(self, body: str, con: socket.socket):
        con.send(body.encode())
        con.close()

    def outbound_con(self, p: peer.Peer):
        if p:
            p.msg(b"")
            mutex.acquire()
            t = Thread(target=self.mainloop, args=[p])
            p.thread = t
            mutex.release()
            t.start()

    def bases(self):
        for i in range(10):
            try:
                p = peer.Peer(self.id, from_tuple=True, tup=('', 8000+i))
                self.outbound_con(p)
                # self.outbound_con(('', 8000+i))
                # conn = self.make_connection(('', 8000+i))
                # conn.send(self.id.encode())
                break
            except socket.error:
                continue

    def run(self):
        signal.signal(signal.SIGINT, self.cleanup)
        # signal.signal(signal.SIGTERM, self.cleanup)
        if self.is_light:
            print("no initial discovery in light mode")
        else:
            self.bases()
        self.server.listen(1)

        while 1:
            connection, _ = self.server.accept()
            # self.inbound_con(connection)
            if connection:
                mutex.acquire()
                p = peer.Peer(self.id, from_con=True, connection=connection)
                p.msg(b"")
                t= Thread(target=self.mainloop, args=[p], name=p.hash)
                p.thread = t
                mutex.release()
                t.start()
