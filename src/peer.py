import socket
import struct
from threading import Lock
import datetime
from Crypto.Hash import keccak

def parse_addr(addr: str) -> tuple[str, int]:
    [ip, port] = addr.split("@")[1].split(":")
    return (ip, int(port))

def make_msg(id: str, body: bytes):
    k = keccak.new(digest_bits=256)
    k.update(id.encode()+body)
    data = id.encode()+b"\n"+k.hexdigest().encode()+b"\n"+ body
    data_size = struct.pack(">I",len(data))
    return data_size + data

mutex = Lock()

class Peer:
    def __init__(self, self_id: str, addr: str = "", from_con: bool = False, connection: socket.socket | None = None, from_tuple: bool = False, tup: tuple[str, int] = ("", 0)):
        self.addr: str = addr
        self.err = False
        if not from_con and not from_tuple:
            self.connection: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            if len(addr) > 0:
                self.peer_tuple = parse_addr(addr)
            self.connection.connect(self.peer_tuple)
        elif from_tuple:
            self.connection: socket.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.peer_tuple = tup
            self.connection.connect(self.peer_tuple)
        else:
            if connection:
                self.connection = connection
                # p_addr = self.read()
                # if p_addr:
                #     self.peer_tuple = parse_addr(p_addr)
        self.host_id = self_id

    def read_segment(self, n: int) -> bytes | None:
        data = bytearray()
        while len(data) < n:
            chunk = self.connection.recv(n - len(data))
            if not chunk:
                return None
            if chunk == b"":
                return None
            data.extend(chunk)
        return data

    def read(self) -> str | None:
        len_bytes = self.read_segment(4)
        if not len_bytes:
            return None
        msglen = struct.unpack('>I', len_bytes)
        data = self.read_segment(msglen[0])
        if data:
            str_data = data.decode("utf-8")
            return str_data
        return None

    def msg(self, body: bytes):
        self.connection.send(make_msg(self.host_id, body))
        
class Peer_store:
    def __init__(self, MAX: int = 5):
        self.max = MAX
        self.peers = {}
    
    def add_peer(self, p: Peer):
        if len(self.peers) + 1 > self.max:
            print("hit max peer count:", self.max)
            return
        with mutex:
            self.peers[p.addr] = p
        return p

    def del_peer(self, address: str):
        with mutex:
            del self.peers[address]

    def get_peer(self, address: str) -> Peer | None:
        if address in self.peers.keys():
            with mutex:
                return self.peers[address]

    def get_peers(self):
        with mutex:
            return self.peers.keys()
