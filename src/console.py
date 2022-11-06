from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
import con_sock as sock
from appdirs import *
import os
import os.path as path
from prompt_toolkit.key_binding import KeyBindings
from pathlib import Path
import sys

appname = "tinyNamer"
appauthor = "tinyNamer"

bindings = KeyBindings()

cache = str(Path.home().absolute()) + "/.tinyNamer"

if not path.exists(cache):
    os.mkdir(cache)

# Create prompt object.
history = FileHistory(cache+"/cli_history")
session = PromptSession(
    history=history,
    auto_suggest=AutoSuggestFromHistory(),
    enable_history_search=True,
) 
prefered_client = ("", 8001)
n = sock.node(True)
global PEER
PEER = None


words = WordCompleter(
    [
        "exit",
        "full",
        "get_peers",
        "connect",
    ],
    ignore_case=True,
)

try:
    while True:
        # Do multiple input calls.
        prompt: str = session.prompt("> ", completer=words, complete_while_typing=True, key_bindings=bindings, mouse_support=True)
        frags = prompt.strip().split(" ")
        match frags[0]:
            case "exit":
                break
            case "connect":
                if len(frags) == 1:
                    print("connect expects an argument.")
                    break
                parts = frags[1].split(":")
                prefered_client = (parts[0], int(parts[1]))
                PEER = n.peers.add_peer(sock.peer.Peer(n.id, from_tuple=True, tup=prefered_client))
                if PEER:
                    print(PEER.read())
            case "full":
                print("blocking...")
                n.is_light = False
                n.gen_id(n.server)
                n.run()
            case "get_peers":
                if PEER:
                    PEER.msg(b"get_peers")
                    ps = str(PEER.read()).splitlines()[2]
                    print(sock.base58.b58decode(ps).decode("utf-8"))
except KeyboardInterrupt:
    sys.exit()
