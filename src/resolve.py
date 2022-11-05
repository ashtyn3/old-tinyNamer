import plyvel
import os
import appdirs
import datetime
import hashlib
import json
from Crypto.Hash import keccak

data_dir = appdirs.user_data_dir("blogd", "blogd")

if not os.path.exists(data_dir):
    os.makedirs(data_dir)

class block:
    def __init__(self, prev: str, meta: dict):
        self.timestamp = datetime.datetime.now().isoformat()
        self.meta = meta
        self.prev_hash = prev
        self.transactions = []

    @property
    def hash(self) -> str:
        b = hashlib.blake2b()
        b.update((self.timestamp + self.prev_hash + json.dumps(self.meta)).encode())
        k = keccak.new(digest_bits=256)
        k.update(b.digest())
        return k.hexdigest()


class resolver:
    def __init__(self):
        self.db = plyvel.DB(data_dir+"/blocks", create_if_missing=True)


# resolver()

print(block("hi", {"name":"hi"}).hash)

