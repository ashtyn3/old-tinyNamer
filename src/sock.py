"""
DEPRECATED - DO NOT USE
"""
import socket
import random
import json
import base58
import appdirs
import os



payload_max = 4000


class node:

    peers: dict[str, tuple[str, int]] = {}

    def __init__(self, light: bool):
        self.addr: list[tuple[str, int]] = []
        self.id = ""

        self.gen_addr()
        self.is_light = light

        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(self.addr[0])
        self.gen_id(self.server)
        print("connected as:", self.id)
        self.addr.append((self.addr[0][0], self.addr[0][1]+10))
        self.handlers: dict[str, callable[[str, str]]] = {
                "get_peers": self.handler_peers,
                "peers": self.handler_merge_peers
                }
        self.ltn_handlers: dict[str, callable[[socket.socket], bool]] = {
                "get_peers": self.ltn_handler_peers,
                }

    def handler_merge_peers(self, msg: str, addr: str):
        reply_frags = msg.splitlines()
        peer_str = reply_frags[2]
        reply_peers: dict = json.loads(base58.b58decode(peer_str))
        for key in reply_peers.keys():
            if key not in self.peers and key != self.id.strip():
                self.peers[key] = (reply_peers[key][0], reply_peers[key][1])
                print("new peer (from merge):", key)
                self.broadcast("get_peers")
                self.outbound_con(self.parse_addr(key))

    def ltn_handler_peers(self, con:socket.socket):
        p = base58.b58encode(json.dumps(self.peers))
        con.send(p)
        return True

    def handler_peers(self, msg: str, addr: str):
        p = base58.b58encode(json.dumps(self.peers))
        self.msg_peer("peers\n"+p.decode("utf-8"), self.parse_addr(addr), False)
        return True

    def gen_id(self, server):
        ip, port = server.getsockname()
        if self.is_light:
            self.id = "ltn@"+ip+":"+str(port)+"\n"
            return
        self.id = random.randbytes(10).hex()+"@"+ip+":"+str(port)+"\n"

    def gen_addr(self):
        self.addr.append(('', random.randint(8000, 8010)))

    def parse_addr(self, addr: str):
        [ip, port] = addr.split("@")[1].split(":")
        return (ip, int(port))

    def read(self, connection: socket.socket) -> str | None:
        data = connection.recv(payload_max)
        while 1:
            if data:
                str_data = data.decode("utf-8")
                return str_data
        return

    def connect_msg_peer(self, body: str, address: tuple[str, int], reply: bool = True):
        conn = self.make_connection(address)

        conn.send(self.id.encode())
        conn.send(body.encode())

        r = ""
        if reply:
            r = self.read(conn)

        conn.close()
        return r

    def broadcast(self, body: str):
        print("broadcasting ("+str(len(self.peers))+" peer(s)):", body)
        for k in self.peers.keys():
            self.msg_peer(body, self.peers[k], False)

    def make_connection(self, addr) -> socket.socket:
        conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        conn.connect(addr)
        return conn

    def inbound_con(self, conn: socket.socket):
        reply = self.read(conn)
        reply_frags = str(reply).splitlines()
        addr = reply_frags[0]
        if addr.split("@")[0] == "ltn":
            self.ltn_handlers[reply_frags[1]](conn)
            conn.close()
            return

        conn.close()
        if len(reply_frags) == 1 and addr not in self.peers.keys():
            self.peers[addr] = self.parse_addr(addr)
            print("new peer:", addr)
            self.msg_peer("", self.peers[addr], False)
            self.msg_peer("get_peers", self.peers[addr], False)
            return
        elif len(reply_frags) > 1:
            self.handlers[reply_frags[1]](reply, addr)

    def light_rep(self, body: str, con: socket.socket):
        con.send(body.encode())
        con.close()

    def outbound_con(self, address):
        self.msg_peer("", address, False)

    def bases(self):
        for i in range(10):
            try:
                self.outbound_con(('', 8000+i))
                # conn = self.make_connection(('', 8000+i))
                # conn.send(self.id.encode())
                break
            except socket.error:
                continue

    def run(self):
        if self.is_light:
            print("no initial discovery in light mode")
        else:
            self.bases()
        self.server.listen(1)

        while 1:
            connection, client_addr = self.server.accept()
            self.inbound_con(connection)
