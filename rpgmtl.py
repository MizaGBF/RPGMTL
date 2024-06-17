import json
import time
import textwrap
import traceback
import os
import sys
from pathlib import Path
import shutil
import tkinter as tk
from tkinter import filedialog
from deep_translator import GoogleTranslator

INPUT_FOLDER = "manual_edit/"
ORIGINAL_FOLDER = "untouched_files/"
OUTPUT_FOLDER = "release/"
FILES = next(os.walk(ORIGINAL_FOLDER + "/data"), (None, None, []))[2]
TRANSLATOR = GoogleTranslator(source='auto', target='en')
root = None


def init():
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
        if not os.path.exists("patches.json") or not os.path.isfile("patches.json"):
            with open("patches.json", mode="w", encoding="utf-8") as f:
                f.write("{\n\"System.json\":[\n\"data[\\\"locale\\\"] = \\\"en_UK\\\"\"\n]\n}")
    except Exception as e:
        print("Exception while generating patches.json")
        print(e)

def update_original(clean=False):
    global root
    print("Please select a RPGMV or RPGMZ Executable (It's usually named Game.exe)")
    if root is None:
        root = tk.Tk()
        root.withdraw()
    file_path = filedialog.askopenfilename(title="Select a RPGMV or RPGMZ Executable", filetypes=[("Game", ".exe")])
    if file_path != "":
        file_path = "/".join(file_path.split("/")[:-1])
        if clean:
            shutil.rmtree(INPUT_FOLDER)
        Path(INPUT_FOLDER).mkdir(parents=True, exist_ok=True)
        for f in ["js", "data"]:
            try:
                shutil.copytree(file_path + "/" + f, ORIGINAL_FOLDER + f)
            except Exception as e:
                print("Couldn't copy", file_path + "/" + f)
                print(e)
        print("Done")
        return True
    else:
        print("Operation cancelled...")
        return False

def load_strings(quit_on_error = False):
    try:
        with open("strings.json", mode="r", encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, dict) or "strings" not in loaded or "groups" not in loaded:
            raise Exception("Invalid strings.json format")
        return loaded, True
    except Exception as e:
        if "no such file" not in str(e).lower():
            print("Failed to load strings.json")
            print(e)
            if quit_on_error or input("Type 'y' to continue anyway:").lower() != "y":
                return {"strings":{}, "groups":[]}, False
        return {"strings":{}, "groups":[]}, True

def save_strings(data):
    with open("strings.json", mode="w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)

def backup_strings_file(loaded = None) -> bool:
    try:
        if not loaded:
            with open("strings.json", mode="r", encoding="utf-8") as f: # checking for validity
                loaded = json.load(f)
        if not isinstance(loaded, dict) or "strings" not in loaded or "groups" not in loaded:
            raise Exception("Invalid strings.json format")
        # backing up...
        bak_strings = [".bak-5", ".bak-4", ".bak-3", ".bak-2", ".bak-1", ""]
        for i in range(1, len(bak_strings)):
            try: shutil.copyfile("strings"+bak_strings[i]+".json", "strings"+bak_strings[i-1]+".json")
            except: pass
    except Exception as e:
        if "no such file" not in str(e).lower():
            print("Failed to backup strings.json")
            print(e)
            if input("Type 'y' to continue anyway:").lower() != "y":
                return False
    return True

def check_confirmation(password : str) -> bool:
    return input("Type '{}' to confirm:".format(password)).lower().strip() == password

def untouched_JSON():
    for fn in FILES:
        with open(ORIGINAL_FOLDER + "data/" + fn, mode="r", encoding="utf-8") as f:
            data = json.load(f)
        yield (fn, data)

def load_event_data(content):
    strings = []
    groups = []
    current_group = []
    prev = -1
    for cmd in content:
        match cmd["code"]:
            case 401:
                for pm in cmd["parameters"]:
                    if isinstance(pm, str):
                        strings.append(pm)
                        current_group.append(pm)
            case 320|122|405|111:
                for pm in cmd["parameters"]:
                    if isinstance(pm, str):
                        strings.append(pm)
            case 101|402:
                strings.append(cmd["parameters"][-1])
            case 102:
                for pm in cmd["parameters"][0]:
                    if isinstance(pm, str):
                        strings.append(pm)
            case _:
                pass
        prev = cmd["code"]
        if prev != 401 and len(current_group) > 1:
            groups.append(current_group)
            current_group = []
    if len(current_group) > 1:
        groups.append(current_group)
    return strings, groups
    

def load_data_JSON(data):
    strings = []
    groups = []
    for e in data:
        if isinstance(e, dict):
            for k in ["name", "description", "message1", "message2", "message3", "message4", "note", "list"]:
                if k in e:
                    if k == "list":
                        s, g = load_event_data(e[k])
                        strings += s
                        groups += g
                    else:
                        if isinstance(e[k], str) and e[k] not in strings:
                            strings.append(e[k])
    return strings, groups

def load_map_JSON(data):
    strings = []
    groups = []
    strings.append(data["displayName"])
    for ev in data["events"]:
        if isinstance(ev, dict):
            for p in ev["pages"]:
                s, g = load_event_data(p["list"])
                strings += s
                groups += g
    return strings, groups

def load_commonevent_JSON(data):
    strings = []
    groups = []
    for i, ev in enumerate(data):
        if isinstance(ev, dict):
            s, g = load_event_data(ev["list"])
            strings += s
            groups += g
    return strings, groups

def load_system_JSON(data):
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

def apply_default(d):
    default_tl = {'レベル': 'Level', 'Lv': 'Lv', 'ＨＰ': 'HP', 'HP': 'HP', 'ＳＰ': 'SP', 'SP': 'SP', '経験値': 'Experience point', 'EXP': 'EXP', '戦う': 'Fight', '逃げる': 'Run away', '攻撃': 'Attack', '防御': 'Defense', 'アイテム': 'Items', 'スキル': 'Skills', '装備': 'Equipment', 'ステータス': 'Status', '並び替え': 'Sort', 'セーブ': 'Save', 'ゲーム終了': 'To Title', 'オプション': 'Settings', '大事なもの': 'Key Items', 'ニューゲーム': 'New Game', 'コンティニュー': 'Continue', 'タイトルへ': 'Go to Title', 'やめる': 'Stop', '購入する': 'Buy', '売却する': 'Sell', '最大ＨＰ': 'Max HP', '最大ＭＰ': 'Max MP', '攻撃力': 'ATK', '防御力': 'DEF', '魔法力': 'M.ATK.', '魔法防御': 'M.DEF', '敏捷性': 'AGI', '運': 'Luck', '命中率': 'ACC', '回避率': 'EVA', '常時ダッシュ': 'Always run', 'コマンド記憶': 'Command Memory', 'タッチUI': 'Touch UI', 'BGM 音量': 'BGM volume', 'BGS 音量': 'BGS volume', 'ME 音量': 'ME Volume', 'SE 音量': 'SE volume', '所持数': 'Owned', '現在の%1': 'Current %1', '次の%1まで': 'Until next %1', 'どのファイルにセーブしますか？': 'Which file do you want to save it to?', 'どのファイルをロードしますか？': 'Which file do you want to load?', 'ファイル': 'File', 'オートセーブ': 'Auto Save', '%1たち': '%1', '%1が出現！': '%1 appears!', '%1は先手を取った！': '%1 took the initiative!', '%1は不意をつかれた！': '%1 was caught off guard!', '%1は逃げ出した！': '%1 ran away!', 'しかし逃げることはできなかった！': "But I couldn't escape!", '%1の勝利！': '%1 wins!', '%1は戦いに敗れた。': '%1 lost the battle.', '%1 の%2を獲得！': 'Obtained %2 for %1!', 'お金を %1\\G 手に入れた！': 'Obtained %1 \\G!', '%1を手に入れた！': 'I got %1!', '%1は%2 %3 に上がった！': '%1 rose to %2 %3!', '%1を覚えた！': 'I learned %1!', '%1は%2を使った！': '%1 used %2!', '会心の一撃！！': 'A decisive blow! !', '痛恨の一撃！！': 'A painful blow! !', '%1は %2 のダメージを受けた！': '%1 received %2 damage!', '%1の%2が %3 回復した！': "%1's %2 has recovered his %3!", '%1の%2が %3 増えた！': '%2 of %1 has increased by %3!', '%1の%2が %3 減った！': '%1 %2 decreased %3!', '%1は%2を %3 奪われた！': '%1 was robbed of %2 %3!', '%1はダメージを受けていない！': '%1 has not received any damage!', 'ミス！\u3000%1はダメージを受けていない！': 'Miss! %1 has not received any damage!', '%1に %2 のダメージを与えた！': 'Inflicted %2 damage to %1!', '%1の%2を %3 奪った！': '%2 of %1 was stolen from %3!', '%1にダメージを与えられない！': 'Cannot damage %1!', 'ミス！\u3000%1にダメージを与えられない！': "Miss! Can't damage %1!", '%1は攻撃をかわした！': '%1 dodged the attack!', '%1は魔法を打ち消した！': '%1 canceled the magic!', '%1は魔法を跳ね返した！': '%1 rebounded the magic!', '%1の反撃！': "%1's counterattack!", '%1が%2をかばった！': '%1 protected %2!', '%1の%2が上がった！': '%2 of %1 has gone up!', '%1の%2が下がった！': '%2 of %1 has gone down!', '%1の%2が元に戻った！': '%2 of %1 is back to normal!', '%1には効かなかった！': "It didn't work for %1!"}
    d["strings"] = default_tl | d["strings"]
    return d

def generate():
    if check_confirmation("generate"):
        old, _continue = load_strings()
        if _continue:
            if backup_strings_file(old):
                old = apply_default(old)
                index = {"strings":{}, "groups":[]}
                for fn, data in untouched_JSON():
                    print("Reading", fn)
                    if fn.startswith("Map") and fn != "MapInfos.json":
                        s, g = load_map_JSON(data)
                    elif fn == "CommonEvents.json":
                        s, g = load_commonevent_JSON(data)
                    elif fn == "System.json":
                        s, g = load_system_JSON(data)
                    else:
                        s, g = load_data_JSON(data)
                    index["strings"]["============== " + fn + " =============="] = 0
                    for st in s:
                        if st is None or st == "": continue
                        if st not in index["strings"]:
                            index["strings"][st] = old["strings"].get(st, None)
                    index["groups"] += g
                save_strings(index)
                print("Done")

def translate_string(s):
    time.sleep(0.2)
    cs = TRANSLATOR.translate(s)
    if cs is None or cs == "": raise Exception("Unusable translation")
    if " " not in cs and cs != s: cs = cs.capitalize()
    return cs

def translate():
    if check_confirmation("translate"):
        index, _continue = load_strings(quit_on_error=True)
        if _continue:
            if backup_strings_file(index):
                group_table = {}
                for i, g in enumerate(index["groups"]):
                    for s in g:
                        if s not in group_table:
                            group_table[s] = i
                count = 0
                tl_count = 0
                for s in index["strings"]:
                    if index["strings"][s] is None:
                        if s in group_table:
                            g = index["groups"][group_table[s]]
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
                                    if index["strings"][g[i]] is None:
                                        index["strings"][g[i]] = cs[i].replace("……", "...").replace("…", "...")
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
                                            pair[1] = translate_string(pair[1])
                                            sg[ix] = ":".join(pair)
                                        except:
                                            pass
                                sg = "<" + ">\n<".join(sg) + ">"
                                if sg != s:
                                    index["strings"][s] = sg
                                    tl_count += 1
                            else:
                                try:
                                    index["strings"][s] = translate_string(s)
                                    tl_count += 1
                                except:
                                    pass
                    count += 1
                    sys.stdout.write("\rString {} / {}                ".format(count, len(index["strings"])))
                    sys.stdout.flush()
                print("")
                print("Done")
                if tl_count > 0:
                    save_strings(index)
                    print(tl_count, "modified strings")
                else:
                    print("No new string translation")

def write_json(path : str, data, file_type : int):
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

def write_json_element(f, data):
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

def patch_event_data(data, index):
    for i, cmd in enumerate(data):
        match cmd["code"]:
            case 401:
                for j, pm in enumerate(cmd["parameters"]):
                    if isinstance(pm, str):
                        tl = index["strings"].get(pm, None)
                        if isinstance(tl, str): data[i]["parameters"][j] = tl
            case 320|122|405|111:
                for j, pm in enumerate(cmd["parameters"]):
                    if isinstance(pm, str):
                        tl = index["strings"].get(pm, None)
                        if isinstance(tl, str): data[i]["parameters"][j] = tl
            case 101|402:
                tl = index["strings"].get(cmd["parameters"][-1], None)
                if isinstance(tl, str): data[i]["parameters"][-1] = tl
            case 102:
                for j, pm in enumerate(cmd["parameters"][0]):
                    if isinstance(pm, str):
                        tl = index["strings"].get(pm, None)
                        if isinstance(tl, str): data[i]["parameters"][0][j] = tl
            case _:
                pass
    return data

def patch_data_JSON(data, index):
    for i in range(len(data)):
        if isinstance(data[i], dict):
            for k in ["name", "description", "message1", "message2", "message3", "message4", "note", "list"]:
                if k in data[i]:
                    if k == "list":
                        data[i][k] = patch_event_data(data[i][k], index)
                    else:
                        if isinstance(data[i][k], str):
                            tl = index["strings"].get(data[i][k], None)
                            if isinstance(tl, str): data[i][k] = tl
    return data

def patch_map_JSON(data, index):
    if isinstance(data["displayName"], str):
        tl = index["strings"].get(data["displayName"], None)
        if isinstance(tl, str): data["displayName"] = tl
    for i in range(len(data["events"])):
        if isinstance(data["events"][i], dict):
            for j in range(len(data["events"][i]["pages"])):
                data["events"][i]["pages"][j]["list"] = patch_event_data(data["events"][i]["pages"][j]["list"], index)
    return data

def patch_commonevent_JSON(data, index):
    for i in range(len(data)):
        if isinstance(data[i], dict):
            data[i]["list"] = patch_event_data(data[i]["list"], index)
    return data

def patch_system_JSON(data, index):
    for k, v in data.items():
        if k in ["variables", "switches", "battlerName", "locale", "name"] or "font" in k.lower(): continue
        if isinstance(v, str):
            tl = index["strings"].get(v, None)
            if isinstance(tl, str): data[k] = tl
        elif isinstance(v, list):
            for j, s in enumerate(v):
                if isinstance(s, str):
                    tl = index["strings"].get(s, None)
                    if isinstance(tl, str): data[k][j] = tl
        elif isinstance(v, dict):
            data[k] = patch_system_JSON(v, index)
    return data

def patch_json(fn : str, data, index, patches):
    if fn.startswith("Map") and fn != "MapInfos.json":
        data = patch_map_JSON(data, index)
    elif fn == "CommonEvents.json":
        data = patch_commonevent_JSON(data, index)
    elif fn == "System.json":
        data = patch_system_JSON(data, index)
    else:
        data = patch_data_JSON(data, index)
    if fn in patches:
        for p in patches[fn]:
            try:
                exec(p)
            except Exception as e:
                print("Failed to run the following patch:")
                print(p)
                print("Exception:")
                print(e)
    return data

def patch():
    if check_confirmation("patch"):
        index, _continue = load_strings()
        if _continue:
            if os.path.exists(OUTPUT_FOLDER) and os.path.isdir(OUTPUT_FOLDER):
                try:
                    shutil.rmtree(OUTPUT_FOLDER)
                    print("Cleaned up", OUTPUT_FOLDER)
                except Exception as e:
                    print("WARNING:", OUTPUT_FOLDER, "cleanup failed")
                    print(e)
            try:
                Path(OUTPUT_FOLDER+"data/").mkdir(parents=True, exist_ok=True)
            except Exception as e:
                print("WARNING: Couldn't create", OUTPUT_FOLDER)
                print(e)
            try:
                with open("patches.json", mode="r", encoding="utf-8") as f:
                    patches = json.load(f)
            except Exception as e:
                print("WARNING: Couldn't load patches.json")
                print(e)
                patches = {}
            for fn, data in untouched_JSON():
                old_data = str(data)
                data = patch_json(fn, data, index, patches)
                if str(data) != old_data:
                    file_type = 0
                    if fn.startswith("Map") and fn != "MapInfos.json": file_type = 1
                    elif fn == "System.json": file_type = 2
                    write_json(OUTPUT_FOLDER+"data/" + fn, data, file_type)
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

def main():
    print("RPG Maker MV/MZ MTL Patcher v1.1")
    init()
    while True:
        print("")
        print("[0] Generate strings.json")
        print("[1] Machine Translate")
        print("[2] Create patch")
        print("===========================")
        print("[3] Game got updated")
        print("[Any] Quit")
        try:
            match input().strip():
                case "0":
                    generate()
                case "1":
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