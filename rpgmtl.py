from typing import Optional
import json
import zlib
import struct
import time
import textwrap
import traceback
import os
import sys
from pathlib import Path
import shutil
import tkinter as tk
from tkinter import filedialog
import csv
from io import StringIO
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR = GoogleTranslator(source='auto', target='en')
except:
    print("WARNING: Missing third-party module: deep_translator")
    print("Use the following command line to install: pip install deep_translator")
    TRANSLATOR = None

INPUT_FOLDER = "manual_edit/"
ORIGINAL_FOLDER = "untouched_files/"
OUTPUT_FOLDER = "release/"
FILES_TO_LOOK_FOR = set(['.json', '.js', '.csv', '.rxdata', '.rb'])
TALKING_STR = "#@TALKING:"
COMMENT_STR = "#"
FILE_STR = "#@@@"
DISABLE_STR = "#%%%"
PATCH_STR = "#@@@"
root = None
data_set = None

def init() -> None:
    try:
        if not os.path.exists(INPUT_FOLDER) or not os.path.isdir(INPUT_FOLDER):
            Path(INPUT_FOLDER).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print("Exception while checking for the existence of", INPUT_FOLDER)
        print(e)
    if not os.path.exists(ORIGINAL_FOLDER) or not os.path.isdir(ORIGINAL_FOLDER):
        print("No game data detected")
        if input("Import game data? ('yes' to confirm):").lower() == 'yes' and update_original():
            pass
        else:
            print("WARNING: This script might not function properly")
    try:
        if not os.path.exists("patches.py") or not os.path.isfile("patches.py"):
            with open("patches.py", mode="w", encoding="utf-8") as f:
                f.write(PATCH_STR + "file_name_example\n# Example for System.json:\ndata[\"locale\"] = \"en_UK\"")
    except Exception as e:
        print("Exception while generating patches.py")
        print(e)

def update_original(clean : bool = False) -> bool:
    global root
    print("Please select a RPGMV or RPGMZ Executable (It's usually named Game.exe)")
    if root is None:
        root = tk.Tk()
        root.withdraw()
    file_path = filedialog.askopenfilename(title="Select a RPGMV or RPGMZ Executable", filetypes=[("Game", ".exe")])
    if file_path != "":
        file_path = "/".join(file_path.split("/")[:-1])
        if not file_path.endswith('/'): file_path += '/'
        if clean:
            shutil.rmtree(ORIGINAL_FOLDER)
        encountered_path = set()
        for path, subdirs, files in os.walk(file_path):
            for name in files:
                fp = os.path.join(path, name).replace('\\', '/')
                try:
                    extension = '.' + fp.split('/')[-1].split('.')[1]
                    if extension not in FILES_TO_LOOK_FOR:
                        continue
                except:
                    pass
                fpr = fp.replace(file_path, '')
                target_dir = '/'.join(fpr.split('/')[:-1]) + '/'
                if target_dir not in encountered_path:
                    encountered_path.add(target_dir)
                    try:
                        os.makedirs(os.path.dirname(ORIGINAL_FOLDER + target_dir), exist_ok=True)
                    except Exception as e:
                        print("Couldn't create folder", ORIGINAL_FOLDER + target_dir)
                        print(e)
                try:
                    shutil.copy(fp, ORIGINAL_FOLDER + fpr)
                except Exception as e:
                    print("Couldn't copy", fp)
                    print(e)
                print("Found", fpr)
        print("Done")
        print("Please check in '{}' if any file or folder got copied by mistake (such as the save data folder...".format(ORIGINAL_FOLDER))
        return True
    else:
        print("Operation cancelled...")
        return False

def load_strings(with_file_strings : bool = False) -> tuple:
    try:
        with open("strings.py", mode="r", encoding="utf-8") as f:
            loaded = {}
            disabled = set()
            line_count = 1
            while line := f.readline():
                if line.startswith(DISABLE_STR):
                    disabled.add(line.replace(DISABLE_STR, '').strip())
                    if with_file_strings:
                        loaded[line.strip()] = None
                elif line.strip() == "":
                    pass
                elif not line.startswith(TALKING_STR) and not line.startswith(FILE_STR) and not line.startswith(COMMENT_STR):
                    try:
                        d = json.loads("{"+line+"}")
                        if not isinstance(d, dict):
                            raise Exception()
                    except:
                        raise Exception("Line", line_count, "is invalid")
                    loaded = loaded | d
                elif with_file_strings:
                    loaded[line.strip()] = None
                line_count += 1
        return loaded, disabled, True
    except Exception as e:
        b = "no such file" in str(e).lower()
        if not b:
            print("Failed to load strings.py")
            print(e)
            print("Try to fix its content.")
        return {}, set(), b

def load_groups() -> tuple:
    try:
        with open("groups.json", mode="r", encoding="utf-8") as f:
            loaded = json.load(f)
        return loaded, True
    except Exception as e:
        if "no such file" not in str(e).lower():
            print("Failed to load groups.json")
            print(e)
        return [], True

def save_files(strings : list, groups : Optional[list]) -> None:
    with open("strings.py", mode="w", encoding="utf-8") as f:
        f.write("\n".join(strings))
    if groups is not None:
        with open("groups.json", mode="w", encoding="utf-8") as f:
            json.dump(groups, f, ensure_ascii=False, indent=0)

def update_string_file_with_tl(strings : dict) -> None:
    try:
        with open("strings.py", mode="r", encoding="utf-8") as f:
            lines = []
            while line := f.readline():
                lines.append(line)
        for i, line in enumerate(lines):
            if not line.startswith(DISABLE_STR) and not line.startswith(TALKING_STR) and not line.startswith(FILE_STR) and not line.startswith(COMMENT_STR) and line.strip() != "":
                try:
                    d = json.loads("{"+line+"}")
                    if not isinstance(d, dict):
                        raise Exception()
                    st = list(d.keys())[0]
                    d[st] = strings.get(st, None)
                    lines[i] = "{}:{}\n".format(json.dumps(st, ensure_ascii=False, separators=(',', ':')), json.dumps(d[st], ensure_ascii=False, separators=(',', ':')))
                except Exception as x:
                    print(x)
                    raise Exception("Line", i+1, "is invalid", line)
            else:
                pass
            
        with open("strings.py", mode="w", encoding="utf-8") as f:
            for line in lines:
                f.write(line)
    except Exception as e:
        print("An error occured while updating strings.py")
        print(e)
    

def backup_strings_file() -> bool:
    try:
        # backing up...
        bak_strings = [".bak-5", ".bak-4", ".bak-3", ".bak-2", ".bak-1", ""]
        for i in range(1, len(bak_strings)):
            try: shutil.copyfile("strings"+bak_strings[i]+".py", "strings"+bak_strings[i-1]+".py")
            except: pass
    except Exception as e:
        if "no such file" not in str(e).lower():
            print("Failed to backup strings.py")
            print(e)
            if input("Type 'y' to continue anyway:").lower() != "y":
                return False
    return True

def check_confirmation(password : str) -> bool:
    return input("Type '{}' to confirm:".format(password)).lower().strip() == password

def untouched_CSV():
    try:
        fn = "data/ExternMessage.csv"
        with open(ORIGINAL_FOLDER + fn, mode="r", encoding="utf-8") as f:
            data = f.read()
        yield (fn.replace(ORIGINAL_FOLDER, ''), data)
    except:
        yield from []

def untouched_JAVA():
    for path, subdirs, files in os.walk(ORIGINAL_FOLDER):
        for name in files:
            if name.endswith('.js'):
                fn = os.path.join(path, name).replace('\\', '/')
                with open(fn, mode="r", encoding="utf-8") as f:
                    data = f.read()
                yield (fn.replace(ORIGINAL_FOLDER, ''), data)

def untouched_JSON():
    for path, subdirs, files in os.walk(ORIGINAL_FOLDER):
        for name in files:
            if name.endswith('.json'):
                fn = os.path.join(path, name).replace('\\', '/')
                with open(fn, mode="r", encoding="utf-8") as f:
                    data = json.load(f)
                yield (fn.replace(ORIGINAL_FOLDER, ''), data)

def read_MARSHAL_long(handle) -> int:
    length = struct.unpack("b", handle.read(1))[0]
    if length == 0:
        return 0
    if 5 < length < 128:
        return length - 5
    elif -129 < length < -5:
        return length + 5
    result = 0
    factor = 1
    for s in range(abs(length)):
        result += struct.unpack("B", handle.read(1))[0] * factor
        factor *= 256
    if length < 0:
        result = result - factor
    return result

def read_MARSHAL_short(handle):
    return struct.unpack("<H", handle.read(2))[0]

class MarshalElement():
    def __init__(self, token, content=None):
        self.token = token
        self.content = content
        self.extras = []

    def set(self, content, extras=None):
        self.content = content
        if extras is not None: self.extras = extras
        return self

    def __str__(self):
        return "MarshalElement<{}:{}:{}>".format(self.token, self.content, self.extras)

def read_MARSHAL(handle, token=None) -> tuple:
    if token is None:
        token = handle.read(1)
    elem = MarshalElement(token)
    match token:
        case b"0":
            return elem.set(None)
        case b"T":
            return elem.set(True)
        case b"F":
            return elem.set(False)
        case b"I":
            return elem.set(bytes(), [read_MARSHAL(handle)])
        case b'"':
            return elem.set(handle.read(read_MARSHAL_long(handle)))
        case b":":
            return elem.set(handle.read(read_MARSHAL_long(handle)))
        case b'i':
            return elem.set(read_MARSHAL_long(handle))
        case b"[":
            size = read_MARSHAL_long(handle)
            return elem.set([read_MARSHAL(handle) for i in range(size)])
        case b"{":
            size = read_MARSHAL_long(handle)
            return elem.set({read_MARSHAL(handle):read_MARSHAL(handle) for i in range(size)})
        case b"f":
            return elem.set(float(handle.read(read_MARSHAL_long(read_MARSHAL_long(handle))).split(b"\0")[0].decode("utf-8")))
        case b"l":
            return elem.set(handle.read(read_MARSHAL_long(handle)*2))
        case b"/":
            return elem.set(handle.read(read_MARSHAL_long(handle)))
        case b"U":
            return elem.set(bytes(), [read_MARSHAL(handle), read_MARSHAL(handle)])
        case b";":
            return elem.set(read_MARSHAL_long(handle))
        case b"@":
            return elem.set(read_MARSHAL_long(handle))
        case b"u":
            sym = read_MARSHAL(handle)
            pdata = read_MARSHAL(handle, b'"').content
            return elem.set(pdata, [sym])
        case b"m":
            return elem.set(read_MARSHAL(handle, b'"').content)
        case b"o":
            return elem.set(bytes(), [read_MARSHAL(handle), read_MARSHAL(handle, b"{")])
        case b"e":
            return elem.set(read_MARSHAL(handle, b'"').content)
        case b"c":
            return elem.set(read_MARSHAL(handle, b'"').content)
        case _:
            raise Exception("Uninplemented", token, handle.tell())

def read_MARSHAL_file(handle):
    if handle.read(1) != b"\x04" or handle.read(1) != b"\x08": raise Exception("Invalid Magic Number")
    return read_MARSHAL(handle)

def untouched_MARSHAL():
    for path, subdirs, files in os.walk(ORIGINAL_FOLDER):
        for name in files:
            if name.endswith('.rxdata'):
                fn = os.path.join(path, name).replace('\\', '/')
                with open(fn, mode="rb") as f:
                    data = read_MARSHAL_file(f)
                yield (fn.replace(ORIGINAL_FOLDER, ''), data)

def untouched_RUBY():
    for path, subdirs, files in os.walk(ORIGINAL_FOLDER):
        for name in files:
            if name.endswith('.rb'):
                fn = os.path.join(path, name).replace('\\', '/')
                with open(fn, mode="r", encoding="utf-8", errors='ignore') as f:
                    data = f.read()
                yield (fn.replace(ORIGINAL_FOLDER, ''), data)

def parse_MARSHAL_script(script : str) -> list:
    in_string = False
    escaped = False
    strings = []
    buf = ""
    for i in range(len(script)):
        c = script[i]
        if not in_string:
            if not escaped:
                if c == '"':
                    in_string = True
                    buf = ""
                elif c == "\\":
                    escaped = True
            else:
                escaped = False
        elif escaped:
            if c == "n": buf += "\n"
            else: buf += c
            escaped = False
        else:
            if c == '\\':
                escaped = True
            elif c == '"':
                strings.append(buf)
                buf = ""
                in_string = False
            else:
                buf += c
    return strings

def load_MARSHAL(element, is_script=False):
    strings = []
    if element.token == b"[":
        strings = []
        for e in element.content:
            s, g = load_MARSHAL(e, is_script)
            strings += s
    elif element.token == b"{":
        strings = []
        for k, v in element.content.items():
            s, g = load_MARSHAL(v, is_script)
            strings += s
    elif element.token == b'"':
        try:
            strings = [element.content.decode('utf-8')]
        except Exception as e:
            if is_script:
                d = zlib.decompressobj().decompress(element.content)
                strings = parse_MARSHAL_script(d.decode('utf-8'))
            else:
                raise e
    for e in element.extras:
        s, g = load_MARSHAL(e, is_script)
        strings += s
    return strings, []

def load_event_data(content, old : dict) -> tuple:
    strings = []
    groups = []
    current_group = []
    for cmd in content:
        match cmd["code"]:
            case 401:
                for pm in cmd["parameters"]:
                    if isinstance(pm, str):
                        strings.append(pm)
                        current_group.append(pm)
            case 320|122|405|111|401|324:
                for pm in cmd["parameters"]:
                    if isinstance(pm, str):
                        strings.append(pm)
            case 101:
                for p in cmd["parameters"]:
                    pt = str(p)
                    if isinstance(old.get(pt, None), str): pt = old[pt]
                strings.append(TALKING_STR + pt)
                if isinstance(cmd["parameters"][-1], str) and cmd["parameters"][-1] != "":
                    strings.append(cmd["parameters"][-1])
            case 402:
                strings.append(cmd["parameters"][-1])
            case 102:
                for pm in cmd["parameters"][0]:
                    if isinstance(pm, str):
                        strings.append(pm)
            case _:
                pass
        if cmd["code"] != 401 and len(current_group) > 0:
            if len(current_group) > 1: groups.append(current_group)
            current_group = []
    if len(current_group) > 1:
        groups.append(current_group)
    return strings, groups

def load_data_JSON(data, old : dict) -> tuple:
    strings = []
    groups = []
    for e in data:
        if isinstance(e, dict):
            for k in ["name", "description", "message1", "message2", "message3", "message4", "note", "list", "pages", "nickname", "profile"]:
                if k in e:
                    if k == "list":
                        s, g = load_event_data(e[k], old)
                        strings += s
                        groups += g
                    elif k == "pages":
                        for p in e[k]:
                            s, g = load_event_data(p["list"], old)
                            strings += s
                            groups += g
                    else:
                        if isinstance(e[k], str) and e[k] not in strings:
                            strings.append(e[k])
    return strings, groups

def load_map_JSON(data, old : dict) -> tuple:
    strings = []
    groups = []
    strings.append(data["displayName"])
    for ev in data["events"]:
        if isinstance(ev, dict):
            for p in ev["pages"]:
                s, g = load_event_data(p["list"], old)
                strings += s
                groups += g
    return strings, groups

def load_commonevent_JSON(data, old : dict) -> tuple:
    strings = []
    groups = []
    for i, ev in enumerate(data):
        if isinstance(ev, dict):
            s, g = load_event_data(ev["list"], old)
            strings += s
            groups += g
    return strings, groups

def load_system_JSON(data) -> tuple:
    strings = []
    groups = []
    for k, v in data.items():
        lk = k.lower()
        if k in ["variables", "switches", "locale", "name"] or "font" in lk or "battle" in lk or "character" in lk: continue
        if isinstance(v, str):
            strings.append(v)
        elif isinstance(v, list):
            for s in v:
                if isinstance(s, str):
                    strings.append(s)
        elif isinstance(v, dict):
            s, g = load_system_JSON(v)
            strings += s
            groups += g
    return strings, groups

def load_package_JSON(data) -> tuple:
    try: return [data["window"]["title"]], []
    except: return [], []

def apply_default(d : dict) -> dict:
    default_tl = {'レベル': 'Level', 'Lv': 'Lv', 'ＨＰ': 'HP', 'HP': 'HP', 'ＳＰ': 'SP', 'SP': 'SP', '経験値': 'Experience point', 'EXP': 'EXP', '戦う': 'Fight', '逃げる': 'Run away', '攻撃': 'Attack', '防御': 'Defense', 'アイテム': 'Items', 'スキル': 'Skills', '装備': 'Equipment', 'ステータス': 'Status', '並び替え': 'Sort', 'セーブ': 'Save', 'ゲーム終了': 'To Title', 'オプション': 'Settings', '大事なもの': 'Key Items', 'ニューゲーム': 'New Game', 'コンティニュー': 'Continue', 'タイトルへ': 'Go to Title', 'やめる': 'Stop', '購入する': 'Buy', '売却する': 'Sell', '最大ＨＰ': 'Max HP', '最大ＭＰ': 'Max MP', '攻撃力': 'ATK', '防御力': 'DEF', '魔法力': 'M.ATK.', '魔法防御': 'M.DEF', '敏捷性': 'AGI', '運': 'Luck', '命中率': 'ACC', '回避率': 'EVA', '常時ダッシュ': 'Always run', 'コマンド記憶': 'Command Memory', 'タッチUI': 'Touch UI', 'BGM 音量': 'BGM volume', 'BGS 音量': 'BGS volume', 'ME 音量': 'ME Volume', 'SE 音量': 'SE volume', '所持数': 'Owned', '現在の%1': 'Current %1', '次の%1まで': 'Until next %1', 'どのファイルにセーブしますか？': 'Which file do you want to save it to?', 'どのファイルをロードしますか？': 'Which file do you want to load?', 'ファイル': 'File', 'オートセーブ': 'Auto Save', '%1たち': '%1', '%1が出現！': '%1 appears!', '%1は先手を取った！': '%1 took the initiative!', '%1は不意をつかれた！': '%1 was caught off guard!', '%1は逃げ出した！': '%1 ran away!', 'しかし逃げることはできなかった！': "But I couldn't escape!", '%1の勝利！': '%1 wins!', '%1は戦いに敗れた。': '%1 lost the battle.', '%1 の%2を獲得！': 'Obtained %2 for %1!', 'お金を %1\\G 手に入れた！': 'Obtained %1 \\G!', '%1を手に入れた！': 'I got %1!', '%1は%2 %3 に上がった！': '%1 rose to %2 %3!', '%1を覚えた！': 'I learned %1!', '%1は%2を使った！': '%1 used %2!', '会心の一撃！！': 'A decisive blow! !', '痛恨の一撃！！': 'A painful blow! !', '%1は %2 のダメージを受けた！': '%1 received %2 damage!', '%1の%2が %3 回復した！': "%1's %2 has recovered his %3!", '%1の%2が %3 増えた！': '%2 of %1 has increased by %3!', '%1の%2が %3 減った！': '%1 %2 decreased %3!', '%1は%2を %3 奪われた！': '%1 was robbed of %2 %3!', '%1はダメージを受けていない！': '%1 has not received any damage!', 'ミス！\u3000%1はダメージを受けていない！': 'Miss! %1 has not received any damage!', '%1に %2 のダメージを与えた！': 'Inflicted %2 damage to %1!', '%1の%2を %3 奪った！': '%2 of %1 was stolen from %3!', '%1にダメージを与えられない！': 'Cannot damage %1!', 'ミス！\u3000%1にダメージを与えられない！': "Miss! Can't damage %1!", '%1は攻撃をかわした！': '%1 dodged the attack!', '%1は魔法を打ち消した！': '%1 canceled the magic!', '%1は魔法を跳ね返した！': '%1 rebounded the magic!', '%1の反撃！': "%1's counterattack!", '%1が%2をかばった！': '%1 protected %2!', '%1の%2が上がった！': '%2 of %1 has gone up!', '%1の%2が下がった！': '%2 of %1 has gone down!', '%1の%2が元に戻った！': '%2 of %1 is back to normal!', '%1には効かなかった！': "It didn't work for %1!"}
    d = default_tl | d
    return d

def generate_sub(fn : str, string_counter : int, index: set, strings: list, old: dict, groups : list, s : list, g : list) -> tuple:
    strings.append(FILE_STR + fn)
    previously_added = ""
    for st in s:
        if st is None or st == "" or st in index: continue
        if st.startswith(TALKING_STR):
            if previously_added.startswith(TALKING_STR):
                strings.pop(-1)
            strings.append(st)
        else:
            tl = old.get(st, None)
            strings.append(json.dumps(st, ensure_ascii=False) + ":" + json.dumps(tl, ensure_ascii=False))
            if st not in old:
                string_counter += 1
            index.add(st)
        previously_added = st
    groups += g
    return string_counter, index, strings, groups

def generate() -> None:
    if check_confirmation("generate"):
        old, disabled, _continue = load_strings()
        if _continue:
            if backup_strings_file():
                string_counter = 0
                base_old = old
                old = apply_default(old)
                index = set()
                strings = []
                groups = []
                for fn, data in untouched_CSV():
                    if fn in disabled:
                        print("Skipping", fn, "(Disabled by user)")
                        continue
                    else:
                        print("Reading", fn)
                    sn = fn.split('/')[-1]
                    s, g = load_externmessage_CSV(data)
                    if len(s) > 0 or len(g) > 0:
                        string_counter, index, strings, groups = generate_sub(fn, string_counter, index, strings, old, groups, s, g)
                for fn, data in untouched_JSON():
                    if fn in disabled:
                        print("Skipping", fn, "(Disabled by user)")
                        continue
                    else:
                        print("Reading", fn)
                    sn = fn.split('/')[-1]
                    if sn.startswith("Map") and sn != "MapInfos.json":
                        s, g = load_map_JSON(data, old)
                    elif sn == "CommonEvents.json":
                        s, g = load_commonevent_JSON(data, old)
                    elif sn == "System.json":
                        s, g = load_system_JSON(data)
                    elif sn == "package.json":
                        s, g = load_package_JSON(data)
                    else:
                        s, g = load_data_JSON(data, old)
                    if len(s) > 0 or len(g) > 0:
                        string_counter, index, strings, groups = generate_sub(fn, string_counter, index, strings, old, groups, s, g)
                for fn, data in untouched_JAVA():
                    if 'plugins' in fn:
                        if fn in disabled:
                            print("Skipping", fn, "(Disabled by user)")
                            continue
                        else:
                            print("Reading", fn)
                        if fn.endswith('plugins.js'):
                            s, g = load_plugins_java(data)
                        else:
                            s, g = load_java(data)
                        if len(s) > 0 or len(g) > 0:
                            string_counter, index, strings, groups = generate_sub(fn, string_counter, index, strings, old, groups, s, g)
                for fn, data in untouched_MARSHAL():
                    if fn in disabled:
                        print("Skipping", fn, "(Disabled by user)")
                        continue
                    else:
                        print("Reading", fn)
                    sn = fn.split('/')[-1]
                    s, g = load_MARSHAL(data, "Scripts" in fn)
                    if len(s) > 0 or len(g) > 0:
                        string_counter, index, strings, groups = generate_sub(fn, string_counter, index, strings, old, groups, s, g)
                for fn, data in untouched_RUBY():
                    if fn in disabled:
                        print("Skipping", fn, "(Disabled by user)")
                        continue
                    else:
                        print("Reading", fn)
                    sn = fn.split('/')[-1]
                    s = parse_MARSHAL_script(data,)
                    if len(s) > 0:
                        string_counter, index, strings, groups = generate_sub(fn, string_counter, index, strings, old, groups, s, [])
                for fn in disabled:
                    strings.append(DISABLE_STR+fn)
                save_files(strings, groups)
                print("Done")
                if string_counter > 0:
                    print(string_counter, "new/updated string(s).")
                else:
                    print("No new/updated strings detected.")
                string_counter = 0
                for k in base_old:
                    if k not in index:
                        string_counter += 1
                if string_counter > 0:
                    print(string_counter, "removed unused string(s).")

def load_externmessage_CSV(data : str) -> tuple:
    reader = csv.reader(StringIO(data))
    content = [row for row in reader]
    strings = []
    for row in content:
        for cell in row:
            if cell != "" and not cell.isdigit():
                strings.append(cell)
    return strings, []

def load_plugins_java(data : str) -> tuple:
    try:
        strings = []
        start = data.find('plugins =') + len('plugins =')
        end = len(data) - 1
        while data[end] != ';': end -= 1
        plugins = json.loads(data[start:end])
        for p in plugins:
            if 'parameters' in p:
                for k, v in p['parameters'].items():
                    if v != "" and not v.isdigit():
                        strings.append(v)
        return strings, []
    except Exception as e:
        print("Failed to parse plugins.json")
        print(e)
        return [], []

def load_java(data : str) -> tuple:
    string_ouputs = []
    string = ""
    escaped = False
    string_char = None
    in_string = False
    in_comment = None
    skip_char = False
    for i, c in enumerate(data):
        if skip_char:
            skip_char = False
        elif in_comment is not None:
            if (in_comment == '/' and c == '\n') or (in_comment == '*' and c == '*' and i < len(data)-1 and data[i+1] == '/'):
                in_comment = None
        elif in_string and escaped:
            if c == "n": string += "\n"
            elif c == "\\": string += "\\\\"
            else:
                if string_char == '/': string += "\\"
                string += c
            escaped = False
        elif in_string:
            match c:
                case ('"'|"'"|'`'|'/'):
                    if c == string_char:
                        string_char = None
                        string_ouputs.append(string)
                        string = ""
                        in_string = False
                    else:
                        string += c
                case '\\':
                    escaped = True
                case _:
                    string += c
        elif c == '/': # regex check
            if i < len(data)-1 and data[i+1] in ('*', '/'):
                in_comment = data[i+1]
                skip_char = True
            elif i > 0 and data[i-1] == '(': # probably regex string. NOTE: doesn't cover all cases
                string_char = c
                in_string = True
        else:
            match c:
                case ('"'|"'"|'`'):
                    string_char = c
                    in_string = True
                case _:
                    pass
    return string_ouputs, []

def translate_string(s : str) -> str:
    time.sleep(0.2)
    cs = TRANSLATOR.translate(s)
    if cs is None or cs == "": raise Exception("Unusable translation")
    if " " not in cs and cs != s: cs = cs.capitalize()
    return cs

def translate() -> None:
    if check_confirmation("translate"):
        strings, disabled, _continue = load_strings(with_file_strings=True)
        if _continue:
            groups, _return = load_groups()
            if backup_strings_file():
                all = (input("Type 'all' if you want to translate all files:").lower().strip() == "all")
                group_table = {}
                for i, g in enumerate(groups):
                    for s in g:
                        if s not in group_table:
                            group_table[s] = i
                print("Starting translation...")
                if not all: print("Only translating Map, Event and Item strings...")
                current_file = None
                count = 0
                tl_count = 0
                print_flag = False
                for s in strings:
                    if s.startswith(FILE_STR):
                        current_file = s.replace(FILE_STR, '').strip()
                        if current_file in disabled:
                            sys.stdout.write("\rFile is disabled by the user, skipping...\n")
                        sys.stdout.write("\rIn section: {}              ".format(current_file))
                        sys.stdout.flush()
                        print_flag = True
                    elif s.startswith(COMMENT_STR) or s.startswith(DISABLE_STR) or s.startswith(TALKING_STR):
                        continue
                    elif current_file in disabled:
                        continue
                    elif strings[s] is None:
                        if not all and not current_file.startswith("Map") and current_file not in ["Actors.json", "Armors.json", "Classes.json", "CommonEvents.json", "Enemies.json", "Items.json", "Skills.json", "States.json", "Weapons.json"]:
                            continue
                        if print_flag:
                            print_flag = False
                            print("")
                        sys.stdout.write("\rProgress {:.2f}%                 ".format(100*count/len(strings)))
                        sys.stdout.flush()
                        if s in group_table:
                            g = groups[group_table[s]]
                            try:
                                cs = translate_string("\r\n".join(g)).replace("\r\n", "\n")
                                if len(cs.split("\n")) != len(g):
                                    cs = cs.replace("\n", "")
                                    l = len(cs) // len(g) + 10
                                    cs = textwrap.fill(cs, width=l).split("\n")
                                    while len(cs) > len(g):
                                        cs[len(cs)-2] = cs[len(cs)-2] + " " + cs[len(cs)-1]
                                        del cs[len(cs)-1]
                                else:
                                    cs = cs.split("\n")
                                if len(cs) != len(g):
                                    raise Exception("Invalid string group length")
                                for i in range(len(cs)):
                                    if strings[g[i]] is None:
                                        strings[g[i]] = cs[i].replace("……", "...").replace("…", "...").strip()
                                        tl_count += 1
                            except:
                                pass
                        else:
                            if s.startswith("<SG") and s.endswith(">"): # used by some plugin for special item description...
                                sg = s[1:-1].split(">\n<")
                                for ix in range(len(sg)):
                                    pair = sg[ix].split(":", 1)
                                    if pair[0] == "SG説明":
                                        try:
                                            pair[1] = translate_string(pair[1]).replace("……", "...").replace("…", "...").strip()
                                            sg[ix] = ":".join(pair)
                                        except:
                                            pass
                                sg = "<" + ">\n<".join(sg) + ">"
                                if sg != s:
                                    strings[s] = sg
                                    tl_count += 1
                            else:
                                try:
                                    strings[s] = translate_string(s).replace("……", "...").replace("…", "...").strip()
                                    tl_count += 1
                                except:
                                    pass
                    count += 1
                sys.stdout.write("\rProgress: 100%                 \n")
                sys.stdout.flush()
                print("Done")
                if tl_count > 0:
                    update_string_file_with_tl(strings)
                    print(tl_count, "modified strings")
                else:
                    print("No new string translation")

def write_json(path : str, data, file_type : int) -> None:
    with open(path, mode="w", encoding="utf-8") as f:
        if file_type == 1:
            keys = list(data.keys())
            f.write("{\n")
            for k, v in data.items():
                match k:
                    case "data":
                        f.write("\n")
                        f.write("\"{}\":".format(k))
                        json.dump(v, f, ensure_ascii=False, separators=(',', ':'))
                        if k != keys[-1]:
                            f.write(",")
                    case "events":
                        f.write("\n")
                        f.write("\"{}\":".format(k))
                        write_json_element(f, v)
                        if k != keys[-1]:
                            f.write(",")
                        f.write("\n")
                    case _:
                        f.write("\"{}\":".format(k))
                        json.dump(v, f, ensure_ascii=False, separators=(',', ':'))
                        if k != keys[-1]:
                            f.write(",")
            f.write("}")
        elif file_type == 2:
            json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
        else:
            write_json_element(f, data)

def write_json_element(f, data) -> None:
    match data:
        case dict():
            f.write("{\n")
            keys = list(data.keys())
            for k, v in data.items():
                f.write("\"{}\":".format(k))
                json.dump(v, f, ensure_ascii=False, separators=(',', ':'))
                if k != keys[-1]:
                    f.write(",")
                f.write("\n")
            f.write("}")
        case list():
            f.write("[\n")
            for i, v in enumerate(data):
                json.dump(v, f, ensure_ascii=False, separators=(',', ':'))
                if i < len(data) - 1:
                    f.write(",")
                f.write("\n")
            f.write("]")
        case _:
            raise Exception("Error: " + str(type(data)))

def patch_event_data(data, index : dict):
    for i, cmd in enumerate(data):
        match cmd["code"]:
            case 401:
                for j, pm in enumerate(cmd["parameters"]):
                    if isinstance(pm, str):
                        tl = index.get(pm, None)
                        if isinstance(tl, str): data[i]["parameters"][j] = tl
            case 320|122|405|111|401|324:
                for j, pm in enumerate(cmd["parameters"]):
                    if isinstance(pm, str):
                        tl = index.get(pm, None)
                        if isinstance(tl, str): data[i]["parameters"][j] = tl
            case 101|402:
                tl = index.get(cmd["parameters"][-1], None)
                if isinstance(tl, str): data[i]["parameters"][-1] = tl
            case 102:
                for j, pm in enumerate(cmd["parameters"][0]):
                    if isinstance(pm, str):
                        tl = index.get(pm, None)
                        if isinstance(tl, str): data[i]["parameters"][0][j] = tl
            case _:
                pass
    return data

def patch_data_JSON(data, index : dict):
    for i in range(len(data)):
        if isinstance(data[i], dict):
            for k in ["name", "description", "message1", "message2", "message3", "message4", "note", "list", "pages", "nickname", "profile"]:
                if k in data[i]:
                    if k == "list":
                        data[i][k] = patch_event_data(data[i][k], index)
                    elif k == "pages":
                        for j, p in enumerate(data[i][k]):
                            data[i][k][j]["list"] = patch_event_data(data[i][k][j]["list"], index)
                    else:
                        if isinstance(data[i][k], str):
                            tl = index.get(data[i][k], None)
                            if isinstance(tl, str): data[i][k] = tl
    return data

def patch_map_JSON(data, index : dict):
    if isinstance(data["displayName"], str):
        tl = index.get(data["displayName"], None)
        if isinstance(tl, str): data["displayName"] = tl
    for i in range(len(data["events"])):
        if isinstance(data["events"][i], dict):
            for j in range(len(data["events"][i]["pages"])):
                data["events"][i]["pages"][j]["list"] = patch_event_data(data["events"][i]["pages"][j]["list"], index)
    return data

def patch_commonevent_JSON(data, index : dict):
    for i in range(len(data)):
        if isinstance(data[i], dict):
            data[i]["list"] = patch_event_data(data[i]["list"], index)
    return data

def patch_system_JSON(data, index : dict):
    for k, v in data.items():
        if k in ["variables", "switches", "battlerName", "locale", "name"] or "font" in k.lower(): continue
        if isinstance(v, str):
            tl = index.get(v, None)
            if isinstance(tl, str): data[k] = tl
        elif isinstance(v, list):
            for j, s in enumerate(v):
                if isinstance(s, str):
                    tl = index.get(s, None)
                    if isinstance(tl, str): data[k][j] = tl
        elif isinstance(v, dict):
            data[k] = patch_system_JSON(v, index)
    return data

def patch_json(fn : str, data, index : dict, patches : dict):
    sn = fn.split('/')[-1]
    if sn.startswith("Map") and sn != "MapInfos.json":
        data = patch_map_JSON(data, index)
    elif sn == "CommonEvents.json":
        data = patch_commonevent_JSON(data, index)
    elif sn == "System.json":
        data = patch_system_JSON(data, index)
    elif sn == "package.json":
        try:
            tl = index.get(data["window"]["title"], None)
            if tl is not None:
                data["window"]["title"] = tl
        except:
            pass
    else:
        data = patch_data_JSON(data, index)
    if fn in patches:
        global data_set
        for p in patches[fn]:
            try:
                data_set = None
                exec(p)
                if data_set is not None:
                    data = data_set
            except Exception as e:
                print("Failed to run the following patch:")
                print(p)
                print("Exception:")
                print(e)
    return data

def patch_java(fn : str, data, index : dict, patches):
    if 'plugins' in fn:
        if fn.endswith('plugins.js'):
            try:
                start = data.find('plugins =') + len('plugins =')
                end = len(data) - 1
                while data[end] != ';': end -= 1
                plugins = json.loads(data[start:end])
                for i in range(len(plugins)):
                    if 'parameters' in plugins[i]:
                        for k, v in plugins[i]['parameters'].items():
                            if v != "" and not v.isdigit() and index.get(v, None) is not None:
                                plugins[i]['parameters'][k] = index[v]
                content = "\n[\n"
                for i in range(len(plugins)):
                    content += json.dumps(plugins[i], ensure_ascii=False, separators=(',', ':'))
                    if i != len(plugins)-1: content += ","
                    content += "\n"
                content += "\n]"
                data = data[:start] + content + data[end:]
            except Exception as e:
                print("Failed to parse plugins.js")
                print(e)
        else: # regular json
            begin = -1
            string = ""
            escaped = False
            string_char = None
            in_string = False
            in_comment = None
            i = 0
            while i < len(data):
                c = data[i]
                if in_comment is not None:
                    if (in_comment == '/' and c == '\n') or (in_comment == '*' and c == '*' and i < len(data)-1 and data[i+1] == '/'):
                        in_comment = None
                elif in_string and escaped:
                    if c == "n": string += "\n"
                    elif c == "\\": string += "\\\\"
                    else:
                        if string_char == '/': string += "\\"
                        string += c
                    escaped = False
                elif in_string:
                    match c:
                        case ('"'|"'"|'`'|'/'):
                            if c == string_char:
                                if string != "":
                                    tl = index.get(string, None)
                                    if isinstance(tl, str):
                                        tl = tl.replace('\n', '\\n').replace(string_char, '\\'+string_char)
                                        data = data[:begin] + tl + data[i:]
                                        i = begin + len(tl)
                                        begin = -1
                                string_char = None
                                string = ""
                                in_string = False
                            else:
                                string += c
                        case '\\':
                            escaped = True
                        case _:
                            string += c
                elif c == '/': # regex check
                    if i < len(data)-1 and data[i+1] in ('*', '/'):
                        in_comment = data[i+1]
                        i += 1 # skip char
                    elif i > 0 and data[i-1] == '(': # probably regex string. NOTE: doesn't cover all cases
                        string_char = c
                        in_string = True
                else:
                    match c:
                        case ('"'|"'"|'`'):
                            begin = i + 1
                            string_char = c
                            in_string = True
                        case _:
                            pass
                i += 1
    if fn in patches:
        global data_set
        for p in patches[fn]:
            try:
                data_set = None
                exec(p)
                if data_set is not None:
                    data = data_set
            except Exception as e:
                print("Failed to run the following patch:")
                print(p)
                print("Exception:")
                print(e)
    return data

def patch_csv(fn : str, data, index : dict, patches):
    reader = csv.reader(StringIO(data))
    content = [row for row in reader]
    output = StringIO()
    writer = csv.writer(output, delimiter=',', lineterminator='\n')
    for i in range(len(content)):
        for j in range(len(content[i])):
            tl = index.get(content[i][j], None)
            if isinstance(tl, str):
                content[i][j] = tl
        writer.writerow(content[i])
    output.seek(0)
    data = output.read()
    if fn in patches:
        global data_set
        for p in patches[fn]:
            try:
                data_set = None
                exec(p)
                if data_set is not None:
                    data = data_set
            except Exception as e:
                print("Failed to run the following patch:")
                print(p)
                print("Exception:")
                print(e)
    return data
def patch_mkdir(fn : str) -> None:
    try:
        Path(OUTPUT_FOLDER+'/'.join(fn.split('/')[:-1])).mkdir(parents=True, exist_ok=True)
    except Exception as e:
        print("WARNING: Couldn't create", OUTPUT_FOLDER)
        print(e)

def load_python_patches() -> dict:
    patches = {}
    try:
        with open("patches.py", mode="r", encoding="utf-8") as f:
            content = f.read()
        try:
            content = content.split("\n")
            string = []
            target_file = []
            for line in content:
                if line.startswith(PATCH_STR):
                    if len(target_file) > 0 and len(string) > 0:
                        for f in target_file:
                            
                            if f not in patches:
                                patches[f] = []
                            patches[f].append("\n".join(string))
                    string = []
                    target_file = line[len(PATCH_STR):].split(";")
                    for i in range(len(target_file)):
                        target_file[i] = target_file[i].strip()
                else:
                    string.append(line)
            if len(target_file) > 0 and len(string) > 0:
                for f in target_file:
                    
                    if f not in patches:
                        patches[f] = []
                    patches[f].append("\n".join(string))
        except Exception as e:
            print("WARNING: Couldn't load patches.py")
            print(e)
    except:
        pass
    return patches

def patch() -> None:
    if check_confirmation("patch"):
        strings, disabled, _continue = load_strings()
        if _continue:
            if os.path.exists(OUTPUT_FOLDER) and os.path.isdir(OUTPUT_FOLDER):
                try:
                    shutil.rmtree(OUTPUT_FOLDER)
                    print("Cleaned up", OUTPUT_FOLDER)
                except Exception as e:
                    print("WARNING:", OUTPUT_FOLDER, "cleanup failed")
                    print(e)
            patches = load_python_patches()
            for fn, data in untouched_CSV():
                if fn in disabled:
                    print("Skipping", fn, "(Disabled by user)")
                    continue
                old_data = str(data)
                data = patch_csv(fn, data, strings, patches)
                if str(data) != old_data:
                    patch_mkdir(fn)
                    with open(OUTPUT_FOLDER + fn, mode="w", encoding="utf-8") as f:
                        f.write(data)
                    print("Patched file", fn)
            for fn, data in untouched_JAVA():
                if fn in disabled:
                    print("Skipping", fn, "(Disabled by user)")
                    continue
                old_data = str(data)
                data = patch_java(fn, data, strings, patches)
                if str(data) != old_data:
                    patch_mkdir(fn)
                    with open(OUTPUT_FOLDER + fn, mode="w", encoding="utf-8") as f:
                        f.write(data)
            for fn, data in untouched_JSON():
                if fn in disabled:
                    print("Skipping", fn, "(Disabled by user)")
                    continue
                sn = fn.split('/')[-1]
                old_data = str(data)
                data = patch_json(fn, data, strings, patches)
                if str(data) != old_data:
                    file_type = 0
                    if sn.startswith("Map") and sn != "MapInfos.json": file_type = 1
                    elif sn == "System.json": file_type = 2
                    patch_mkdir(fn)
                    write_json(OUTPUT_FOLDER+fn, data, file_type)
                    print("Patched file", fn)
            try:
                for path, subdirs, files in os.walk(INPUT_FOLDER):
                    for name in files:
                        fn = os.path.join(path, name)
                        Path(path.replace(INPUT_FOLDER, OUTPUT_FOLDER)).mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(fn, fn.replace(INPUT_FOLDER, OUTPUT_FOLDER))
                        print("Copied file", fn)
            except:
                print("WARNING: Couldn't copy content from the folder 'manual_edit'. Ignore if it doesn't exist")
            print("Done")
            print("The patched files are available in the", OUTPUT_FOLDER, "folder")

def main():
    print("RPG Maker MV/MZ MTL Patcher v2.0")
    init()
    while True:
        print("")
        print("[0] Generate strings.json")
        print("[1] Machine Translate" + (" (Requires the deep_translator module)" if TRANSLATOR is None else ""))
        print("[2] Create patch")
        print("===========================")
        print("[3] Game got updated")
        print("[Any] Quit")
        try:
            match input().strip():
                case "0":
                    generate()
                case "1":
                    if TRANSLATOR is None:
                        print("Missing third-party module: deep_translator")
                        print("Use the following command line to install: pip install deep_translator")
                        print("ERROR: Can't proceed with machine translation. Restart the script once deep_translator has been installed.")
                    else:
                        translate()
                case "2":
                    patch()
                case "3":
                    if update_original(clean=True):
                        print("Regenerate strings.json to update the strings")
                case _:
                    break
        except Exception as e:
            print(e)
            print("".join(traceback.format_exception(type(e), e, e.__traceback__)))

if __name__ == "__main__":
    main()