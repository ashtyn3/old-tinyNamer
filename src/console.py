from prompt_toolkit.completion import WordCompleter
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
import sock
import base58
from threading import Thread
from pprint import pprint
from appdirs import *
import os
import os.path as path
from prompt_toolkit.key_binding import KeyBindings

appname = "blogd"
appauthor = "blogd"

bindings = KeyBindings()

cache = user_cache_dir(appname, appauthor)
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


words = WordCompleter(
    [
        "exit",
        "full",
        "get_peers",
        "connect",
    ],
    ignore_case=True,
)

def msg(body: str):
    t = Thread(target=n.run)
    t.start()
    pprint(base58.b58decode(str(n.msg_peer(body, prefered_client, True))).decode("utf-8"), indent=4)


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
        case "full":
            print("blocking...")
            n.is_light = False
            n.gen_id(n.server)
            n.run()
        case "get_peers":
            msg("get_peers")
        
