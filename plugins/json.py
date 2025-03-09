from __future__ import annotations
from . import Plugin, WalkHelper
import json
import io
from typing import Any

class JSON(Plugin):
    DEFAULT_RPGMK_DATA_FILE : set[str] = set(["data/Actors.json", "data/Animations.json", "data/Armors.json", "data/Classes.json", "data/Enemies.json", "data/Items.json", "data/MapInfos.json", "data/Troops.json", "data/Skills.json", "data/States.json", "data/Tilesets.json", "data/Weapons.json"])
    RPGMVMZ_CODE_TABLE = {
        101: "Show Text",
        102: "Choices",
        103: "Number Input",
        104: "Select Item",
        105: "Scrolling Text",
        108: "Comment",
        109: "Skip",
        111: "If ...",
        112: "Loop ...",
        113: "Loop Break",
        115: "Exit Event",
        117: "Common Event",
        118: "Label",
        119: "Jump to Label",
        121: "Switch Control",
        122: "Variable Control",
        123: "Self Switch Control",
        124: "Timer Control",
        125: "Gold Change",
        126: "Item Change",
        127: "Weapon Change",
        128: "Armor Change",
        129: "Party Change",
        132: "Battle BGM Change",
        133: "Victory ME Change",
        134: "Save Access Change",
        135: "Menu Access Change",
        136: "Encounter Change",
        137: "Formation Access Change",
        138: "Window Color Change",
        139: "Defeat ME Change",
        140: "Vehicle BGM Change",
        201: "Transfer Player",
        202: "Set Vehicle Location",
        203: "Set Event Location",
        204: "Scroll Map",
        205: "Set Movement Route",
        206: "Toggle Vehicle",
        211: "Transparency Change",
        212: "Show Animation",
        213: "Show Balloon Icon",
        214: "Erase Event",
        216: "Change Player Followers",
        217: "Gather Followers",
        221: "Fadeout Screen",
        222: "Fadein Screen",
        223: "Tint Screen",
        224: "Flash Screen",
        225: "Shake Screen",
        230: "Wait",
        231: "Show Picture",
        232: "Move Picture",
        233: "Rotate Picture",
        234: "Tint Picture",
        235: "Erase Picture",
        236: "Set Weather",
        241: "Play BGM",
        242: "Fadeout BGM",
        243: "Save BGM",
        244: "Resume BGM",
        245: "Play BGS",
        246: "Fadeout BGS",
        249: "Play ME",
        250: "Play SE",
        251: "Stop SE",
        261: "Play Movie",
        281: "Map Name Display Change",
        282: "Tileset Change",
        283: "Battle Background Change",
        284: "Parallax Change",
        285: "Get Location Info",
        301: "Battle Processing",
        302: "Shop Processing",
        303: "Name Input Processing",
        311: "HP Change",
        312: "MP Change",
        313: "State Change",
        314: "Recover All",
        315: "EXP Change",
        316: "LVL Change",
        317: "Parameter Change",
        318: "Skill Change",
        319: "Equipment Change",
        320: "Name Change",
        321: "Class Change",
        322: "Actor Image Change",
        323: "Vehicle Image Change",
        324: "Nickname Change",
        325: "Profile Change",
        326: "TP Change",
        331: "Enemy HP Change",
        332: "Enemy MP Change",
        333: "Enemy State Change",
        334: "Enemy Recover All",
        335: "Enemy Appear",
        336: "Enemy Transform",
        337: "Show Battle Animation",
        339: "Force Action",
        340: "Abort Battle",
        342: "Enemy TP Change",
        351: "Open Menu Screen",
        352: "Open Save Screen",
        353: "Game Over",
        354: "Return to Title Screen",
        355: "Script",
        356: "Plugin Command (MV)",
        357: "Plugin Command (MZ)",
        401: "Text Line",
        402: "When ...",
        403: "When Cancel",
        405: "Scrolling Line",
        411: "Else ...",
        413: "Repeat above...",
        601: "If Battle Win",
        602: "If Battle Escape",
        603: "If Battle Lose",
        655: "Script Line",
    }
    
    def __init__(self : JSON) -> None:
        super().__init__()
        self.name : str = "JSON"
        self.description : str = "v1.0\nHandle JSON files, including ones from RPG Maker MV/MZ"

    def get_setting_infos(self : Plugin) -> dict[str, list]:
        return {
            "json_rpgm_multiline": ["Merge multiline elements into one string", "bool", False, None]
        }

    def file_extension(self : JSON) -> list[str]:
        return ["json"]

    def match(self : JSON, file_path : str) -> bool:
        return file_path.endswith(".json")

    def read(self : JSON, file_path : str, content : bytes) -> list[list[str]]:
        data = json.loads(self.decode(content))
        if file_path.endswith("data/System.json"): # System file of RPGMV/MZ
            return self._read_walk_system(data)
        elif len(file_path) >= 16 and file_path[-16:-8] == "data/Map": # Map file of RPGMV/MZ
            return self._read_walk_map(data)
        elif file_path.endswith("data/CommonEvents.json"): # CommonEvents file of RPGMV/MZ
            return self._read_walk_common(data)
        elif '/' in file_path and '/'.join(file_path.split('/')[-2:]) in self.DEFAULT_RPGMK_DATA_FILE:
            return self._read_walk_data(data)
        else:
            return self._read_walk(data)

    def write(self : JSON, file_path : str, content : bytes, strings : dict) -> tuple[bytes, bool]:
        data = json.loads(self.decode(content))
        helper : WalkHelper = WalkHelper(file_path, strings)
        if isinstance(data, str):
            data = helper.apply_string(data)
        else:
            if file_path.endswith("data/System.json"): # System file of RPGMV/MZ
                self._write_walk_system(data, helper)
            elif len(file_path) >= 16 and file_path[-16:-8] == "data/Map": # Map file of RPGMV/MZ
                self._write_walk_map(data, helper)
            elif file_path.endswith("data/CommonEvents.json"): # CommonEvents file of RPGMV/MZ
                self._write_walk_common(data, helper)
            elif '/' in file_path and '/'.join(file_path.split('/')[-2:]) in self.DEFAULT_RPGMK_DATA_FILE:
                self._write_walk_data(data, helper)
            else:
                self._write_walk(data, helper)
        return self.encode(json.dumps(data)), helper.modified
    
    def format(self : JSON, file_path : str, content : bytes) -> bytes:
        # Format in different way depending on what kind of file it is
        if '/' in file_path and '/'.join(file_path.split('/')[-2:]) in self.DEFAULT_RPGMK_DATA_FILE:
            # For these files, we try to keep the formatting as close as standard RPGMV/MZ as possible
            data = json.loads(self.decode(content))
            with io.StringIO() as f:
                self._format_element(f, data)
                return self.encode(f.getvalue())
        elif len(file_path) >= 16 and file_path[-16:-8] == "data/Map":
            # Keep the standard format of Map files
            data = json.loads(self.decode(content))
            with io.StringIO() as f:
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
                            self._format_element(f, v)
                            if k != keys[-1]:
                                f.write(",")
                            f.write("\n")
                        case _:
                            f.write("\"{}\":".format(k))
                            json.dump(v, f, ensure_ascii=False, separators=(',', ':'))
                            if k != keys[-1]:
                                f.write(",")
                f.write("}")
                return self.encode(f.getvalue())
        elif file_path.endswith("data/System.json"):
            # Keep the standard format of System.json
            data = json.loads(self.decode(content))
            with io.StringIO() as f:
                json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
                return self.encode(f.getvalue())
        return content
    
    # Used by format
    # Just JSON formatting mess
    def _format_element(self : JSON, f : io.StringIO, data : Any) -> None:
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
    
    # Generic JSON processing
    def _read_walk(self : JSON, obj : Any) -> list[list[str]]:
        entries : list[list[str]] = []
        match obj:
            case dict():
                for k in obj:
                    entries.extend(self._read_walk(obj[k]))
            case list():
                for i in range(len(obj)):
                    entries.extend(self._read_walk(obj[i]))
            case str():
                if obj != "":
                    entries.append(["", obj])
            case _:
                pass
        return entries

    def _write_walk(self : JSON, obj : Any, helper : WalkHelper) -> None:
        match obj:
            case dict():
                for k in obj:
                    if isinstance(obj[k], str):
                        if obj[k] != "":
                            obj[k] = helper.apply_string(obj[k])
                    else:
                        self._write_walk(obj[k], helper)
            case list():
                for i in range(len(obj)):
                    if isinstance(obj[i], str):
                        if obj[i] != "":
                            obj[i] = helper.apply_string(obj[i])
                    else:
                        self._write_walk(obj[i], helper)
            case str():
                raise Exception("[JSON] Invalid code path")
            case _:
                pass
    
    # RPGMV/MZ System.json processing
    def _read_walk_system(self : JSON, obj : dict[str, Any]) -> list[list[str]]|str:
        entries : list[list[str]] = []
        for k, v in obj.items():
            match v:
                case str():
                    if v != "":
                        entries.append([k, v])
                case list():
                    group : list[str] = [k]
                    for s in v:
                        if isinstance(s, str) and s != "":
                            group.append(s)
                    if len(group) > 1:
                        entries.append(group)
                case dict():
                    entries.extend(self._read_walk_system(v))
                case _:
                    pass
        return entries

    def _write_walk_system(self : JSON, obj : Any, helper : WalkHelper) -> None:
        for k, v in obj.items():
            match v:
                case str():
                    if v != "":
                        obj[k] = helper.apply_string(obj[k])
                case list():
                    for i in range(len(v)):
                        if isinstance(v[i], str) and v[i] != "":
                            obj[k][i] = helper.apply_string(obj[k][i])
                case dict():
                    self._write_walk_system(obj[k], helper)
                case _:
                    pass

    # RPGMV/MZ Map files processing
    def _read_walk_map(self : JSON, obj : Any) -> list[list[str]]:
        entries : list[list[str]] = []
        for k, v in obj.items():
            match v:
                case str():
                    if v != "":
                        entries.append([k, v])
                case list():
                    if k == "events":
                        for ev in v:
                            if isinstance(ev, dict):
                                for p in ev["pages"]:
                                    entries.extend(self._read_walk_event(p["list"]))
                    else:
                        group : list[str] = [k]
                        for s in v:
                            if isinstance(s, str) and s != "":
                                group.append(s)
                        if len(group) > 1:
                            entries.append(group)
                case dict():
                    entries.extend(self._read_walk_system(v))
                case _:
                    pass
        return entries

    def _write_walk_map(self : JSON, obj : Any, helper : WalkHelper) -> None:
        for k, v in obj.items():
            match v:
                case str():
                    if v != "":
                        obj[k] = helper.apply_string(obj[k])
                case list():
                    if k == "events":
                        for i in range(len(v)):
                            if isinstance(v[i], dict):
                                for j in range(len(v[i]["pages"])):
                                    self._write_walk_event(v[i]["pages"][j]["list"], helper)
                    else:
                        for i in range(len(v)):
                            if isinstance(v[i], str) and v[i] != "":
                                obj[k][i] = helper.apply_string(obj[k][i])
                case dict():
                    self._write_walk_system(obj[k], helper)
                case _:
                    pass

    # RPGMV/MZ CommonEvents processing
    def _read_walk_common(self : JSON, obj : Any) -> list[list[str]]:
        entries : list[list[str]] = []
        for ev in obj:
            if ev is None:
                continue
            strings = self._read_walk_event(ev["list"])
            if len(strings) > 0:
                entries.append(["Common Event " + str(ev["id"]) + " " + ev["name"]])
                entries.extend(strings)
        return entries

    def _write_walk_common(self : JSON, obj : Any, helper : WalkHelper) -> None:
        for i in range(len(obj)):
            if obj[i] is None:
                continue
            self._write_walk_event(obj[i]["list"], helper)

    # RPGMV/MZ Events processing
    # Used by both Map and CommonEvents
    # We process differently based on the event codes
    def _walk_event_continuous_command(self : JSON, i : index, cmds : list[dict], code : int) -> tuple[int, list[str]]:
        text : list[str] = []
        while i < len(cmds) and cmds[i]["code"] == code:
            text.append(cmds[i]["parameters"][0])
            i += 1
        i -= 1
        return i, text
    
    def _read_walk_event(self : JSON, cmds : list[dict]) -> list[list[str]]:
        entries : list[list[str]] = []
        group : list[str] = [""]
        i : int = 0
        while i < len(cmds):
            cmd = cmds[i]
            group[0] = "Command: " + self.RPGMVMZ_CODE_TABLE.get(cmd["code"], "Code " + str(cmd["code"]))
            match cmd["code"]:
                case 101: # Show Text commands
                    if len(cmd["parameters"]) >= 5 and isinstance(cmd["parameters"][4], str) and cmd["parameters"][4] != "": # Show Text, Speaker Name (MZ only)
                        group.append(cmd["parameters"][4])
                    i += 1
                    i, text = self._walk_event_continuous_command(i, cmds, 401)
                    if len(text) > 0:
                        if self.settings.get("json_rpgm_multiline", False):
                            group.append("\n".join(text))
                        else:
                            group.extend(text)
                case 355: # Scripting
                    if len(cmd["parameters"]) >= 1 and isinstance(cmd["parameters"][0], str) and cmd["parameters"][0] != "":
                        group.append(cmd["parameters"][0])
                    i += 1
                    i, text = self._walk_event_continuous_command(i, cmds, 655)
                    if len(text) > 0:
                        if self.settings.get("json_rpgm_multiline", False):
                            group.append("\n".join(text))
                        else:
                            group.extend(text)
                case 102: # Choices
                    if len(cmd["parameters"]) >= 1 and isinstance(cmd["parameters"][0], list):
                        for s in cmd["parameters"][0]:
                            if s != "":
                                group.append(s)
                case 108: # Comment
                    pass
                case 357: # Plugin Command (MZ only)
                    for pm in cmd["parameters"]:
                        if isinstance(pm, str) and pm != "":
                            group.append(pm)
                        elif isinstance(pm, dict):
                            for k, v in pm.items():
                                if isinstance(v, str) and v != "":
                                    group.append(v)
                case _: # Default
                    for pm in cmd["parameters"]:
                        if isinstance(pm, str) and pm != "":
                            group.append(pm)
            if len(group) > 1:
                entries.append(group)
                group = [""]
            i += 1
        return entries

    def _write_walk_event(self : JSON, cmds : list[dict], helper : WalkHelper) -> None:
        i : int = 0
        while i < len(cmds):
            cmd = cmds[i]
            group = "Command: " + self.RPGMVMZ_CODE_TABLE.get(cmd["code"], "Code " + str(cmd["code"]))
            match cmd["code"]:
                case 101: # Show Text commands
                    if len(cmd["parameters"]) >= 5 and isinstance(cmd["parameters"][4], str) and cmd["parameters"][4] != "": # Show Text, Speaker Name (MZ only)
                        cmd["parameters"][4] = helper.apply_string(cmd["parameters"][4], group)
                    i += 1
                    start = i
                    i, text = self._walk_event_continuous_command(i, cmds, 401)
                    if len(text) > 0:
                        if self.settings.get("json_rpgm_multiline", False):
                            # Multiline mode
                            combined : str = helper.apply_string("\n".join(text), group)
                            if helper.str_modified:
                                while combined.count('\n') < len(text)-1:
                                    combined += "\n "
                                if len(text) > 1:
                                    text = combined.split('\n', len(text)-1)
                                else:
                                    text[0] = combined
                        else:
                            # Single line mode
                            for j in range(len(text)):
                                text[j] = helper.apply_string(text[j], group)
                        for j in range(start, i+1):
                            cmds[j]["parameters"][0] = text[j-start]
                case 355: # Scripting
                    if len(cmd["parameters"]) >= 1 and isinstance(cmd["parameters"][0], str) and cmd["parameters"][0] != "":
                        cmd["parameters"][0] = helper.apply_string(cmd["parameters"][0], group)
                    i += 1
                    start = i
                    i, text = self._walk_event_continuous_command(i, cmds, 655)
                    if len(text) > 0:
                        if self.settings.get("json_rpgm_multiline", False):
                            # Multiline mode
                            combined : str = helper.apply_string("\n".join(text), group)
                            if helper.str_modified:
                                while combined.count('\n') < len(text)-1:
                                    combined += "\n "
                                if len(text) > 1:
                                    text = combined.split('\n', len(text)-1)
                                else:
                                    text[0] = combined
                        else:
                            # Single line mode
                            for j in range(len(text)):
                                text[j] = helper.apply_string(text[j], group)
                        for j in range(start, i+1):
                            cmds[j]["parameters"][0] = text[j-start]
                case 102: # Choices
                    if len(cmd["parameters"]) >= 1 and isinstance(cmd["parameters"][0], list):
                        for j in range(len(cmd["parameters"][0])):
                            if cmd["parameters"][0][j] != "":
                                cmd["parameters"][0][j] = helper.apply_string(cmd["parameters"][0][j], group)
                case 108: # Comment
                    pass
                case 357: # Plugin Command (MZ only)
                    for j in range(len(cmd["parameters"])):
                        if isinstance(cmd["parameters"][j], str) and cmd["parameters"][j] != "":
                            cmds[i]["parameters"][j] = helper.apply_string(cmds[i]["parameters"][j], group)
                        elif isinstance(cmd["parameters"][j], dict):
                            for k in cmd["parameters"][j]:
                                if isinstance(cmd["parameters"][j][k], str) and cmd["parameters"][j][k] != "":
                                    cmds[i]["parameters"][j][k] = helper.apply_string(cmds[i]["parameters"][j][k], group)
                case _: # Default
                    for j in range(len(cmd["parameters"])):
                        if isinstance(cmd["parameters"][j], str) and cmd["parameters"][j] != "":
                            cmds[i]["parameters"][j] = helper.apply_string(cmds[i]["parameters"][j], group)
            i += 1

    # RPGMV/MZ standard Data Files processing
    def _read_walk_data(self : JSON, obj : Any) -> list[list[str]]:
        entries : list[list[str]] = []
        for ev in obj:
            if ev is None:
                continue
            strings = self._read_walk(ev)
            if len(strings) > 0:
                entries.append(["ID " + str(ev["id"])])
                entries.extend(strings)
        return entries

    def _write_walk_data(self : JSON, obj : Any, helper : WalkHelper) -> None:
        for i in range(len(obj)):
            if obj[i] is None:
                continue
            self._write_walk(obj[i], helper)