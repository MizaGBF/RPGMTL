from __future__ import annotations
from . import Plugin, WalkHelper
import io
import struct
import math
from pathlib import Path, PurePath
from typing import Any, Iterator, Callable
from dataclasses import dataclass
import zlib
import json

# RPG Maker XP/VX/VX Ace data files are based on the Ruby Marshal format
# The following documentation for this plugin:
# https://docs.ruby-lang.org/en/2.6.0/marshal_rdoc.html
# https://ruby-doc.org/core-2.6.8/Marshal.html
# https://github.com/ruby/ruby/blob/master/marshal.c
# Test file: https://rubygems.org/latest_specs.4.8.gz
class RM_Marshal(Plugin):
    DEFAULT_RPGMK_DATA_FILE = ["data/actors", "data/animations", "data/armors", "data/classes", "data/enemies", "data/items", "data/skills", "data/states", "data/tilesets", "data/weapons"]
    EXTENSIONS : list[str] = ["rxdata", "rvdata", "rvdata2"]
    RPGMXP_CODE_TABLE = {
        101: "Show Text",
        102: "Choices",
        103: "Number Input",
        104: "Select Item",
        105: "Key Input",
        106: "Wait",
        108: "Comment",
        111: "If ...",
        112: "Loop ...",
        113: "Loop Break",
        115: "Exit Event",
        116: "Erase Event",
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
        131: "Window Skin Change",
        132: "Battle BGM Change",
        133: "Victory ME Change",
        134: "Save Access Change",
        135: "Menu Access Change",
        136: "Encounter Change",
        201: "Transfer Player",
        202: "Move Event",
        203: "Scroll Map",
        204: "Map Settings",
        205: "Fog Color Tone Change",
        206: "Fog Opacity Change",
        207: "Show Animation",
        208: "Transparency Flag",
        209: "Movement Route",
        210: "Wait for Movevement",
        221: "Prepare Transition",
        222: "Execute Transition",
        223: "Tint Screen",
        224: "Flash Screen",
        225: "Shake Screen",
        231: "Show Picture",
        232: "Move Picture",
        233: "Rotate Picture",
        234: "Tint Picture",
        235: "Erase Picture",
        236: "Set Weather",
        241: "Play BGM",
        242: "Fadeout BGM",
        245: "Play BGS",
        246: "Fadeout BGS",
        247: "Memorize BGM/BGS",
        248: "Restore BGM/BGS",
        249: "Play ME",
        250: "Play SE",
        251: "Stop SE",
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
        331: "Enemy HP Change",
        332: "Enemy MP Change",
        333: "Enemy State Change",
        334: "Enemy Recover All",
        335: "Enemy Appear",
        336: "Enemy Transform",
        337: "Show Battle Animation",
        338: "Deal Damage",
        339: "Force Action",
        340: "Abort Battle",
        351: "Open Menu Screen",
        352: "Open Save Screen",
        353: "Game Over",
        354: "Return to Title Screen",
        355: "Script",
        401: "Text Line",
        402: "When ...",
        403: "When Cancel",
        404: "Choices End",
        408: "Comment Line",
        411: "Else ...",
        412: "Branch End",
        413: "Repeat above...",
        509: "Move Command",
        601: "If Battle Win",
        602: "If Battle Escape",
        603: "If Battle Lose",
        604: "Battle Processing End",
        605: "Shop Item",
        655: "Script Line"
    }
    
    def __init__(self : RM_Marshal) -> None:
        super().__init__()
        self.name : str = "RPG Maker Marshal"
        self.description : str = "v3.2\nHandle files from RPG Maker XP, VX and VX Ace"
        self.allow_ruby_plugin : bool = True # Leave it on by default

    def get_setting_infos(self : RM_Marshal) -> dict[str, list]:
        return {
            "rm_marshal_multiline": ["Merge multiline commands into one (Require re-extract)", "bool", False, None]
        }

    def get_action_infos(self : RM_Marshal) -> dict[str, list]:
        return {
            "rm_marshal_export": ["Deserialize File Content", self._deserialize],
            "rm_marshal_script_export": ["Dump Ruby Scripts", self._export_script],
        }

    def _deserialize(self : RM_Marshal, name : str, file_path : str, settings : dict[str, Any] = {}) -> str:
        try:
            with open("projects/" + name + "/originals/" + file_path, mode="rb") as f:
                mc : MC = MC.load(f.read())
            is_script : bool = file_path.endswith("Scripts.rxdata") or file_path.endswith("Scripts.rvdata") or file_path.endswith("Scripts.rvdata2")
            output_path : str = "projects/" + name + "/rm_marshal_export/" + file_path + ".json"
            Path(output_path).parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, mode="w", encoding="utf-8") as f:
                mc.root.deserialize(f, is_script)
                f.write("\n")
            return "File deserialized to " + output_path
        except Exception as e:
            self.owner.log.error("[RPG Maker Marshal] Action 'rm_marshal_export' failed with error:\n" + self.owner.trbk(e))
            return "An error occured, the file might be badly formatted."

    def _export_script(self : RM_Marshal, name : str, file_path : str, settings : dict[str, Any] = {}) -> str:
        try:
            lfp : str = file_path.lower()
            if lfp.endswith("data/scripts.rxdata") or lfp.endswith("data/scripts.rvdata") or lfp.endswith("data/scripts.rvdata2"):
                self.allow_ruby_plugin = False
                with open("projects/" + name + "/originals/" + file_path, mode="rb") as f:
                    entries = self.read(file_path, f.read())
                base_path : Path = Path("projects", name, "rm_scripts")
                base_path.mkdir(parents=True, exist_ok=True)
                for i, e in enumerate(entries):
                    # determine file name
                    name = str(i).zfill(6)
                    if e[0] != "Script":
                        tmp = e[0][7:].replace('/', '').replace('<', '').replace('>', '').replace(':', '').replace('"', '').replace('\\', '').replace('|', '').replace('?', '').replace('*', '').strip()
                        if tmp != "":
                            name += " " + tmp
                    (base_path / (name + ".rb")).write_bytes(e[1].encode('utf-8'))
                self.allow_ruby_plugin = True
                return "Scripts dumped to " + base_path.as_posix()
            else:
                return "This action is only for RPG Maker Scripts files."
        except Exception as e:
            self.allow_ruby_plugin = True
            self.owner.log.error("[RPG Maker Marshal] Action 'rm_marshal_script_export' failed with error:\n" + self.owner.trbk(e))
            return "An error occured, the file might be badly formatted."

    def file_extension(self : RM_Marshal) -> list[str]:
        return self.EXTENSIONS

    def match(self : RM_Marshal, file_path : str, is_for_action : bool) -> bool:
        return '.' in file_path and file_path.split('.')[-1] in self.EXTENSIONS

    def read(self : RM_Marshal, file_path : str, content : bytes) -> list[list[str]]:
        p : PurePath = PurePath(file_path) # path object equivalent
        dp : str = p.relative_to(p.parent.parent) # path one folder up (to detect Data folder)
        dp = dp.parent / dp.stem # remove extension
        s : str = dp.as_posix().lower() # as lowercase posix string
        mc : MC = MC.load(content)
        entries : list[list[str]] = []
        if s == "data/commonevents":
            entries.extend(self._read_walk_common(mc.root))
        elif s == "data/scripts":
            entries.extend(self._read_walk_script(mc.root))
        elif s == "data/mapinfos":
            entries.extend(self._read_walk_mapinfo(mc.root))
        elif s == "data/troops":
            entries.extend(self._read_walk_troops(mc.root))
        elif s in self.DEFAULT_RPGMK_DATA_FILE:
            entries.extend(self._read_walk_data(mc.root))
        elif s.startswith("data/map"): # Map file (Must be after mapinfos check)
            entries.extend(self._read_walk_map(mc.root))
        else:
            entries.extend(self._read_walk(mc.root))
        return entries

    def write(self : RM_Marshal, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        p : PurePath = PurePath(file_path) # path object equivalent
        dp : str = p.relative_to(p.parent.parent) # path one folder up (to detect Data folder)
        dp = dp.parent / dp.stem # remove extension
        s : str = dp.as_posix().lower() # as lowercase posix string
        mc : MC = MC.load(content)
        if s == "data/scripts":
            if self._write_walk_script(name, file_path, self.owner.strings[name], mc.root):
                return mc.dump(), True
        else:
            helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
            if s == "data/commonevents":
                self._write_walk_common(mc.root, helper)
            elif s == "data/mapinfos":
                self._write_walk_mapinfo(mc.root, helper)
            elif s == "data/troops":
                self._write_walk_troops(mc.root, helper)
            elif s in self.DEFAULT_RPGMK_DATA_FILE:
                self._write_walk_data(mc.root, helper)
            elif s.startswith("data/map"): # Map file (Must be after mapinfos check)
                self._write_walk_map(mc.root, helper)
            else:
                self._write_walk(mc.root, helper)
            if helper.modified:
                return mc.dump(), True
        return content, False

    # Generic Ruby Marshal processing
    def _read_walk(self : RM_Marshal, me : ME, ignore_key : str|None = None) -> list[list[str]]:
        entries : list[list[str]] = []
        match me.token:
            case b'"':
                raise Exception("[RM_Marshal] Invalid code path")
            case b'[':
                for i, e in enumerate(me):
                    if e.token == b'"':
                        if e.data:
                            entries.append([str(i), e.data.decode('utf-8')])
                    else:
                        entries.extend(self._read_walk(e))
            case b'{'|b'o':
                for k, v in me:
                    key : str = k.decode('utf-8')
                    if ignore_key is not None and ignore_key == key:
                        continue
                    if v.token == b'"':
                        if v.data:
                            entries.append([key, v.data.decode('utf-8')])
                    else:
                        entries.extend(self._read_walk(v))
            case _:
                pass
        return entries

    def _write_walk(self : RM_Marshal, me : ME, helper : WalkHelper, ignore_key : str|None = None) -> None:
        match me.token:
            case b'"':
                raise Exception("[RM_Marshal] Invalid code path")
            case b'[':
                for i, e in enumerate(me):
                    if e.token == b'"':
                        if e.data:
                            tmp : str = helper.apply_string(e.data.decode('utf-8'), str(i))
                            if helper.str_modified:
                                e.data = tmp.encode('utf-8')
                    else:
                        self._write_walk(e, helper)
            case b'{'|b'o':
                for k, v in me:
                    key : str = k.decode('utf-8')
                    if ignore_key is not None and ignore_key == key:
                        continue
                    if v.token == b'"':
                        if v.data:
                            tmp : str = helper.apply_string(v.data.decode('utf-8'), key)
                            if helper.str_modified:
                                v.data = tmp.encode('utf-8')
                    else:
                        self._write_walk(v, helper)
            case _:
                pass

    # RPGMK Map files processing
    def _read_walk_map(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        evlist : ME = me.get(b"@events")
        if evlist is not None:
            for k, ev in evlist:
                name : ME = ev.get(b"@name")
                if name is None:
                    strings = [[""]]
                else:
                    strings = [[name.data.decode('utf-8')]]
                pages : ME = ev.get(b"@pages")
                if pages is not None:
                    for i, p in enumerate(pages):
                        cmds : ME = p.get(b"@list")
                        if cmds is not None:
                            results = self._read_walk_event(cmds)
                            if len(results) > 0:
                                strings.append(["Page {}".format(i+1)])
                                strings.extend(results)
                if len(strings) > 1:
                    entries.extend(strings)
        return entries

    def _write_walk_map(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        evlist : ME = me.get(b"@events")
        if evlist is not None:
            for k, ev in evlist:
                pages : ME = ev.get(b"@pages")
                if pages is not None:
                    for p in pages:
                        cmds : ME = p.get(b"@list")
                        if cmds is not None:
                            self._write_walk_event(cmds, helper)

    # RPGMK CommonEvents processing
    def _read_walk_common(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        for e in me:
            if e.token == b"0":
                continue
            cmds : ME = e.get(b"@list")
            if cmds is not None:
                strings = self._read_walk_event(cmds)
                if len(strings) > 0:
                    name = "Common Event"
                    eid : ME = e.get(b"@id")
                    if eid is not None:
                        name += " " + str(eid.data)
                    n : ME = e.get(b"@name")
                    if n is not None:
                        name += " " + n.data.decode('utf-8')
                    entries.append([name])
                    entries.extend(strings)
        return entries

    def _write_walk_common(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        for e in me:
            if e.token == b"0":
                continue
            cmds : ME = e.get(b"@list")
            if cmds is not None:
                self._write_walk_event(cmds, helper)

    # RPGMK Events processing (used by Map and CommonEvents)
    # Used by both Map and CommonEvents
    # We process differently based on the event codes
    def _walk_event_continuous_command(self : RM_Marshal, i : int, cmds : list[ME], code : int) -> tuple[int, list[str], list[ME]]:
        text : list[str] = []
        elements : list[ME] = []
        while i < len(cmds) and cmds[i].token == b'o' and cmds[i].get(b"@code").data == code:
            parameters = cmds[i].get(b"@parameters").data
            if parameters[0].token == b'"' and parameters[0].data:
                text.append(parameters[0].data.decode('utf-8'))
                elements.append(parameters[0])
            i += 1
        return i, text, elements

    def _read_walk_event(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        group : list[str] = [""]
        i : int = 0
        while i < len(me.data):
            cmd = me.data[i]
            if cmd.token != b'o' or cmd.data[0].at().data != b'RPG::EventCommand':
                i += 1
                continue
            r : ME = cmd.get(b"@parameters")
            if r is None or r.token != b'[':
                i += 1
                continue
            code : ME = cmd.get(b"@code").data
            parameters : list[ME] = r.data
            group[0] = "Command: " + self.RPGMXP_CODE_TABLE.get(code, "Code " + str(code))
            match code:
                case 101|355: # Show Text commands / Script Commands
                    follow_code : int = code + 300
                    tmp = parameters[0].data.decode('utf-8')
                    i, text, _unused_ = self._walk_event_continuous_command(i+1, me.data, follow_code)
                    i -= 1
                    if tmp or len(text) > 0:
                        if self.settings.get("rm_marshal_multiline", False):
                            text.insert(0, tmp)
                            group.append("\n".join(text))
                        else:
                            if tmp:
                                group.append(tmp)
                            group.extend(text)
                case 102:
                    for pm in parameters:
                        if pm.token == b'[':
                            for sub in pm:
                                if sub.token == b'"' and sub.data:
                                    group.append(sub.data.decode('utf-8'))
                        else:
                            if pm.token == b'"' and pm.data:
                                group.append(pm.data.decode('utf-8'))
                case 108|408: # Comment
                    pass
                case _: # Default
                    for pm in parameters:
                        if pm.token == b'"' and pm.data:
                            group.append(pm.data.decode('utf-8'))
            if len(group) > 1:
                entries.append(group)
                group = [""]
            i += 1
        return entries

    def _write_walk_event(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        i : int = 0
        while i < len(me.data):
            cmd = me.data[i]
            if cmd.token != b'o' or cmd.data[0].at().data != b'RPG::EventCommand':
                i += 1
                continue
            r : ME = cmd.get(b"@parameters")
            if r is None or r.token != b'[':
                i += 1
                continue
            code : ME = cmd.get(b"@code").data
            parameters : list[ME] = r.data
            group : str = "Command: " + self.RPGMXP_CODE_TABLE.get(code, "Code " + str(code))
            match code:
                case 101|355: # Show Text commands / Script Commands
                    follow_code : int = code + 300
                    tmp = parameters[0].data.decode('utf-8')
                    i, text, elements = self._walk_event_continuous_command(i+1, me.data, follow_code)
                    i -= 1
                    text.insert(0, tmp)
                    elements.insert(0, parameters[0])
                    if tmp or len(text) > 1:
                        if self.settings.get("rm_marshal_multiline", False):
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
                        for j in range(len(text)):
                            if elements[j].token == b'o':
                                parameters = elements[j].get(b"@parameters").data
                                if parameters[0].token == b'"' and parameters[0].data: # XP, VX
                                    parameters[0].data = text[j].encode("utf-8")
                case 102:
                    for pm in parameters:
                        if pm.token == b'[':
                            for sub in pm:
                                if sub.token == b'"' and sub.data:
                                    tmp : str = helper.apply_string(sub.data.decode('utf-8'), group)
                                    if helper.str_modified:
                                        sub.data = tmp.encode('utf-8')
                        else:
                            if pm.token == b'"' and pm.data:
                                tmp : str = helper.apply_string(pm.data.decode('utf-8'), group)
                                if helper.str_modified:
                                    pm.data = tmp.encode('utf-8')
                case 108|408: # Comment
                    pass
                case _: # Default
                    for pm in parameters:
                        if pm.token == b'"' and pm.data:
                            tmp : str = helper.apply_string(pm.data.decode('utf-8'), group)
                            if helper.str_modified:
                                pm.data = tmp.encode('utf-8')
            i += 1

    # RPGMK Scripts processing
    def _read_walk_script(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        count = 0
        for e in me:
            scriptname = self.owner.CHILDREN_FILE_ID + "{:04}".format(count)
            if e.data[1].data:
                scriptname += " " + e.data[1].data.decode('utf-8')
            if e.data[2].data:
                script = zlib.decompressobj().decompress(e.data[2].data).decode('utf-8')
                if self.allow_ruby_plugin and "Ruby" in self.owner.plugins:
                    self.owner.plugins["Ruby"].reset()
                    strings = self.owner.plugins["Ruby"]._parse_strings(script, None, len(entries))[0]
                    if len(strings) > 0:
                        entries.append([scriptname])
                        entries.extend(strings)
                else:
                    entries.append([scriptname])
                    entries.append([script])
            count += 1
        return entries

    def _write_walk_script(self : RM_Marshal, name : str, file_path : str, strings : dict, me : ME) -> bool:
        modified : bool = False
        count = 0
        for e in me:
            scriptname = file_path + "/{:04}".format(count)
            if e.data[1].data:
                scriptname += " " + e.data[1].data.decode('utf-8').replace("/", " ").replace("\\", " ")
            if scriptname in strings["files"] and not self.owner.projects[name]["files"][scriptname]["ignored"]:
                if e.data[2].data:
                    helper : WalkHelper = WalkHelper(scriptname, strings)
                    script = zlib.decompressobj().decompress(e.data[2].data).decode('utf-8')
                    if self.allow_ruby_plugin and "Ruby" in self.owner.plugins:
                        self.owner.plugins["Ruby"].reset()
                        newscript = self.owner.plugins["Ruby"]._parse_strings(script, helper)[1]
                        if newscript != script:
                            compressor = zlib.compressobj()
                            e.data[2].data = compressor.compress(newscript.encode('utf-8')) + compressor.flush()
                            modified = True
                    else:
                        tmp : str = helper.apply_string(script)
                        if helper.str_modified:
                            compressor = zlib.compressobj()
                            e.data[2].data = compressor.compress(tmp.encode('utf-8')) + compressor.flush()
                            modified = True
            count += 1
        return modified

    # RPGMK MapInfos processing
    def _read_walk_mapinfo(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        for e in me:
            if e[1].token == b'o':
                r : ME = e[1].get(b"@name")
                if r is not None:
                    entries.append(["Map " + str(e[0]), r.data.decode('utf-8')])
        return entries

    def _write_walk_mapinfo(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        for e in me:
            if e[1].token == b'o':
                r : ME = e[1].get(b"@name")
                if r is not None and r.token == b'"' and r.data:
                    tmp : str = helper.apply_string(r.data.decode('utf-8'), "Map " + str(e[0]))
                    if helper.str_modified:
                        r.data = tmp.encode('utf-8')

    # RPGMK Troops processing
    def _read_walk_troops(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        for e in me:
            if e.token == b'o' and e.data[0].at().data == b"RPG::Troop":
                strings = self._read_walk(e, "@pages")
                if len(strings) > 0:
                    r : ME = e.get(b"@id")
                    if r is not None:
                        entries.append(["ID " + str(r.data)])
                    else:
                        entries.append(["ID ?"])
                    entries.extend(strings)
                r : ME = e.get(b"@pages")
                if r is not None:
                    for i, p in enumerate(r):
                        u : ME = p.get(b"@list")
                        if u is not None:
                            strings = self._read_walk_event(u)
                            if len(strings) > 0:
                                entries.append(["Page {}".format(i+1)])
                                entries.extend(strings)
        return entries

    def _write_walk_troops(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        for e in me:
            if e.token == b'o' and e.data[0].at().data == b"RPG::Troop":
                self._write_walk(e, helper, "@pages")
                r : ME = e.get(b"@pages")
                if r is not None:
                    for i, p in enumerate(r):
                        u : ME = p.get(b"@list")
                        if u is not None:
                            self._write_walk_event(u, helper)

    # RPGMK standard Data Files processing
    def _read_walk_data(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        for e in me:
            if e.token == b'o':
                strings = self._read_walk(e)
                if len(strings) > 0:
                    r : ME = e.get(b"@id")
                    if r is not None:
                        entries.append(["ID " + str(r.data)])
                    else:
                        entries.append([""])
                    entries.extend(strings)
        return entries

    def _write_walk_data(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        for e in me:
            if e.token == b'o':
                self._write_walk(e, helper)

# Classes for handling Ruby Marshal files
@dataclass(slots=True)
class MC(): # for Marshal Container
    root : ME|None
    symtable : list[ME]
    objtable : list[ME]

    def __init__(self : MC) -> None:
        self.root = None
        self.symtable = []
        self.objtable = [None]

    # parse binary Marshal File content and return a Marshal Container
    def load(binary : bytes) -> MC:
        with io.BytesIO(binary) as handle:
            if handle.read(1) != b"\x04" or handle.read(1) != b"\x08":
                raise Exception("[RM_Marshal] Unsupported Ruby Marshal version or invalid file")
            mc : MC = MC()
            mc.root = mc._process_token(handle)
            return mc
    
    # generate binary Marshal File content from the Marshal Container
    def dump(self : MC) -> bytes:
        with io.BytesIO() as handle:
            handle.write(b"\x04\x08")
            self.root.dump(handle)
            return handle.getvalue()

    # Default function for unimplemented tokens, used during parsing
    def _token_unimplemented(self : MC, token : bytes, handle : io.BytesIO) -> None:
        raise Exception("[RM_Marshal] Token " + str(token) + " isn't implemented")

    # Read a byte (token) and create Marshal Element (ME) accordingly
    def _process_token(self : MC, handle : io.BytesIO, ivar=False) -> ME:
        token = handle.read(1)
        if token is None or token == b'':
            raise Exception("[RM_Marshal] Reached EOF")
        if token not in self.TOKEN_TABLE:
            return self._token_unimplemented(token, handle)
        else:
            index : int|None
            # Add spot to object table
            # Instance Var are in as we handle those differently
            if not ivar and token not in (b"0", b"T", b"F", b"i", b":", b";", b"@", b"I"): 
                index = len(self.objtable)
                self.objtable.append(None)
            else:
                index = None
            # Parse content
            me : ME = self.TOKEN_TABLE[token](self, token, handle)
            # Instance variable
            if ivar:
                me.attributes = self._read_hashtable(b"{", handle)
                me.attributes.silent_token = True
            # Fill object table
            if not ivar and index is not None:
                self.objtable[index] = me
            return me

    # Generic function to read a Ruby Marshal fixnum/long
    def util_read_fixnum(self : MC, handle : io.BytesIO) -> int:
        length = struct.unpack("b", handle.read(1))[0]
        if length == 0:
            return 0
        if 4 < length < 128:
            return length - 5
        elif -129 < length < -4:
            return length + 5
        result = 0
        alen = abs(length)
        data = handle.read(alen)
        result = int.from_bytes(data, byteorder="little", signed=False)
        if length < 0:
            result -= (1 << (8 * alen))
        return result

    # Generic function to write a Ruby Marshal fixnum/long
    def util_write_fixnum(self : MC, value : int) -> bytes:
        if value == 0:
            return b"\0"
        elif 0 < value < 123:
            return struct.pack("b", value + 5)
        elif -124 < value < 0:
            return struct.pack("b", value - 5)
        else:
            size = int(math.ceil(value.bit_length() / 8.0))
            if size > 5:
                raise Exception("[RM_Marshal] {} is too long for serialization".format(value))
            back = value
            factor = 256 ** size
            if value < 0 and value == -factor:
                size -= 1
                value += factor // 256  # adjust by one byte's factor
            elif value < 0:
                value += factor
            sign = int(math.copysign(size, back))
            return struct.pack("b", sign) + value.to_bytes(size, byteorder='little', signed=False)

    # functions used for parsing

    def _read_nil(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, None)

    def _read_true(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, True)

    def _read_false(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, False)

    def _read_instancevariable(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        me : ME = self._process_token(handle, True)
        self.objtable.append(ME(self, b"I", False)) # Dummy "instance"
        return me

    def _read_string(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, handle.read(self.util_read_fixnum(handle)))

    def _read_symbol(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        me : ME = ME(self, token, handle.read(self.util_read_fixnum(handle)))
        self.symtable.append(me)
        return me

    def _read_symlink(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        me : ME = ME(self, token, self.util_read_fixnum(handle))
        if me.data < 0 or me.data >= len(self.symtable): # check validity
            raise Exception("[RM_Marshal] Symbol Link isn't pointing to an existing symbol")
        return me

    def _read_fixnum(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, self.util_read_fixnum(handle))

    def _read_array(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        size = self.util_read_fixnum(handle)
        return ME(self, token, [self._process_token(handle) for i in range(size)])

    def _read_hashtable(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        me : ME = ME(self, token, None)
        size = self.util_read_fixnum(handle)
        hashtable : dict[ME, ME] = {}
        for i in range(size):
            original : ME = self._process_token(handle) # before the statement to be processed first
            hashtable[original.at().data] = (original, self._process_token(handle))
        me.data = hashtable
        return me

    def _read_float(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, handle.read(self.util_read_fixnum(handle)))

    def _read_bignum(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        sign = handle.read(1)
        size = self.util_read_fixnum(handle)
        b = b"" if size == 0 else handle.read(2*size)
        return ME(self, token, (sign, b))

    def _read_regex(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, handle.read(self.util_read_fixnum(handle)))

    def _read_usermarshal(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, (self._process_token(handle), self._process_token(handle)))

    def _read_object(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        symbol : ME = self._process_token(handle)
        table : ME = self._read_hashtable(b"{", handle)
        table.silent_token = True
        return ME(self, token, (symbol, table))

    def _read_link(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        me : ME = ME(self, token, self.util_read_fixnum(handle))
        if me.data <= 0 or me.data >= len(self.objtable): # check validity
            raise Exception("[RM_Marshal] Link isn't pointing to an existing element")
        return me

    def _read_userdefined(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, (self._process_token(handle), handle.read(self.util_read_fixnum(handle))))

    def _read_classmodule(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, handle.read(self.util_read_fixnum(handle)))
    
    TOKEN_TABLE = {
        b"0":_read_nil,
        b"T":_read_true,
        b"F":_read_false,
        b"I":_read_instancevariable,
        b'"':_read_string,
        b":":_read_symbol,
        b";":_read_symlink,
        b'i':_read_fixnum,
        b"[":_read_array,
        b"{":_read_hashtable,
        b"f":_read_float,
        b"l":_read_bignum,
        b"/":_read_regex,
        b"U":_read_usermarshal,
        b"o":_read_object,
        b"@":_read_link,
        b"u":_read_userdefined,
        b"m":_read_classmodule,
        b"c":_read_classmodule,
        b"M":_read_classmodule
    }

class HashTableIter: # Iterator to use for loop over Marshal HashTable
    def __init__(self : HashTableIter, d: dict[str, tuple[ME, ME]]):
        self._dict_ = d
        self._keys = iter(self._dict_) # get an iterator over the keys

    def __iter__(self : HashTableIter) -> Iterator[tuple[str, ME]]:
        return self

    def __next__(self : HashTableIter) -> tuple[str, ME]:
        try:
            key = next(self._keys)
            value_tuple = self._dict_[key]
            return key, value_tuple[1]
        except StopIteration:
            raise StopIteration

@dataclass(slots=True)
class ME(): # for Marshal Element
    owner : MC
    token : bytes
    data : Any
    attributes : ME|None # instance variable attributes
    silent_token : bool # set it to True so that the token isn't written during dump()
    _dump_call_ : Callable # used during dump and set in __init__ according to the given token
    
    def __init__(self : ME, owner : MC, token : bytes, data : Any = None) -> None:
        self.owner = owner
        self.token = token
        self.data = data
        self.attributes = None
        self.silent_token = False
        self._dump_call_ = self.DUMP_CALL_TABLE.get(self.token, self.dump_unimplemented)

    def __repr__(self : ME) -> str:
        return self.token.decode() + ":" + repr(self.data)

    def __str__(self : ME) -> str:
        return str(self.data)

    def __hash__(self : ME) -> int:
        return hash(self.data)

    def __iter__(self : ME) -> Iterator[Any]: # for loops
        match self.token:
            case b"[":
                return iter(self.data)
            case b"{":
                return HashTableIter(self.data)
            case b"o":
                return self.data[1].__iter__()
            case b";"|b"@":
                return self.at().__iter__()
            case _:
                raise Exception("[RM Marshal] This Marshal Element (" + str(self.token) + ") isn't iterable.")

    def __contains__(self : ME, key : bytes) -> bool: # 'in' calls
        match self.token:
            case b"[":
                return key in self.data
            case b"{":
                return key in self.data
            case b"o":
                return self.data[1].__contains__(key)
            case b";"|b"@":
                return self.at().__contains__(key)
            case _:
                raise Exception("[RM Marshal] This Marshal Element (" + str(self.token) + ") doesn't support __contains__.")

    def get(self : ME, key : bytes|int) -> ME|None: # get, meant to be used like dict.get
        match self.token:
            case b"[":
                return self.data[key]
            case b"{":
                return self.data.get(key, [None, None])[1]
            case b"o":
                return self.data[1].get(key)
            case b";"|b"@":
                return self.at().get(key)

    def at(self : ME) -> ME: # match links to their equivalent
        match self.token:
            case b";":
                return self.owner.symtable[self.data]
            case b"@":
                return self.owner.objtable[self.data]
            case _:
                return self

    # write the element into binary
    def dump(self : ME, handle : io.BytesIO) -> None:
        if self.attributes is not None:
            handle.write(b"I")
        if not self.silent_token:
            handle.write(self.token)
        self._dump_call_(self, handle)
        if self.attributes is not None:
            self.attributes.dump(handle)

    # dump functions

    def dump_none(self : ME, handle : io.BytesIO) -> None:
        pass

    def dump_binary(self : ME, handle : io.BytesIO) -> None:
        handle.write(self.owner.util_write_fixnum(len(self.data)))
        handle.write(self.data)

    def dump_fixnum(self : ME, handle : io.BytesIO) -> None:
        handle.write(self.owner.util_write_fixnum(self.data))

    def dump_array(self : ME, handle : io.BytesIO) -> None:
        handle.write(self.owner.util_write_fixnum(len(self.data)))
        for e in self.data:
            e.dump(handle)

    def dump_hashtable(self : ME, handle : io.BytesIO) -> None:
        handle.write(self.owner.util_write_fixnum(len(self.data)))
        for k, v in self.data.items():
            v[0].dump(handle)
            v[1].dump(handle)

    def dump_object(self : ME, handle : io.BytesIO) -> None:
        self.data[0].dump(handle)
        self.data[1].dump(handle)

    def dump_long(self : ME, handle : io.BytesIO) -> None:
        handle.write(self.data[0])
        handle.write(self.owner.util_write_fixnum(len(self.data[1])//2))
        handle.write(self.data[1])

    def dump_usermarshal(self : ME, handle : io.BytesIO) -> None:
        self.data[0].dump(handle)
        self.data[1].dump(handle)

    def dump_userdefined(self : ME, handle : io.BytesIO) -> None:
        self.data[0].dump(handle)
        handle.write(self.owner.util_write_fixnum(len(self.data[1])))
        handle.write(self.data[1])

    def dump_unimplemented(self : ME, handle : io.BytesIO) -> None:
        raise Exception("[RM_Marshal] Unknown token type:" + str(self.token))

    DUMP_CALL_TABLE = {
        b"0":dump_none,
        b"T":dump_none,
        b"F":dump_none,
        b'"':dump_binary,
        b":":dump_binary,
        b";":dump_fixnum,
        b'i':dump_fixnum,
        b"[":dump_array,
        b"{":dump_hashtable,
        b"f":dump_binary,
        b"l":dump_long,
        b"/":dump_binary,
        b"U":dump_usermarshal,
        b"o":dump_object,
        b"@":dump_fixnum,
        b"u":dump_userdefined,
        b"m":dump_binary,
        b"c":dump_binary,
        b"M":dump_binary
    }

    # For debugging purpose
    # Also used by the deserialize action
    def _write_indent(self : ME, handle : Any, indent) -> None:
        handle.write('\t' * indent)

    def _write_struct_start(self : ME, handle : Any, indent : int, type_name : str) -> None:
        handle.write('{\n')
        self._write_indent(handle, indent+1)
        handle.write('"ruby.type": "' + type_name + '",\n')
        self._write_indent(handle, indent+1)

    def _write_struct_end(self : ME, handle : Any, indent : int) -> None:
        handle.write('\n')
        self._write_indent(handle, indent)
        handle.write('}')
  
    def _write_generic(self : ME, handle : Any, indent : int, type_name : str) -> None:
        self._write_struct_start(handle, indent, type_name)
        handle.write('"binary": ')
        handle.write(json.dumps(str(self.data)))
        self._write_struct_end(handle, indent)

    def deserialize(self : ME, handle : Any, is_script : bool, *, indent : int = 0, write_indent : bool = True, parent : ME = None) -> None:
        if write_indent: self._write_indent(handle, indent)
        match self.token:
            case b"0":
                handle.write('null')
            case b"T":
                handle.write('true')
            case b"F":
                handle.write('false')
            case b'"':
                try:
                    handle.write(json.dumps(self.data.decode('utf-8'), ensure_ascii=False))
                except:
                    try:
                        if not is_script:
                            raise Exception()
                        handle.write(json.dumps(zlib.decompressobj().decompress(self.data).decode('utf-8'), ensure_ascii=False))
                    except:
                        handle.write('"<#ERROR>: String of unknown encoding"')
            case b":":
                handle.write(json.dumps(self.data.decode('utf-8'), ensure_ascii=False))
            case b'i':
                handle.write(json.dumps(self.data))
            case b"[":
                handle.write('[\n')
                for i in range(len(self.data)):
                    self.data[i].deserialize(handle, is_script, indent=indent+1, parent=self)
                    if i != len(self.data)-1:
                        handle.write(',\n')
                handle.write('\n')
                self._write_indent(handle, indent)
                handle.write(']')
            case b"{":
                handle.write('{\n')
                l : int = len(self.data)
                for k, v in self.data.items():
                    v[0].deserialize(handle, is_script, indent=indent+1, parent=self)
                    handle.write(': ')
                    v[1].deserialize(handle, is_script, indent=indent+1, write_indent=False, parent=self)
                    l -= 1
                    if l > 0:
                        handle.write(',\n')
                handle.write('\n')
                self._write_indent(handle, indent)
                handle.write('}')
            case b"f":
                self._write_generic(handle, indent, "Float")
            case b"l":
                self._write_generic(handle, indent, "BigNum")
            case b"/":
                self._write_generic(handle, indent, "Regex")
            case b"U":
                self._write_struct_start(handle, indent, "User Marshal")
                handle.write('"symbol": ')
                self.data[0].deserialize(handle, is_script, indent=indent+1, write_indent=False)
                handle.write(',\n')
                handle.write('"object": ')
                self.data[1].deserialize(handle, is_script, indent=indent+1, write_indent=False)
                self._write_struct_end(handle, indent)
            case b";"|b"@":
                at : ME = self.at()
                if at.token in (b";", b"@"):
                    raise Exception("[RM Marshal] Unexpected symbol/object link.")
                elif at.token == b"I":
                    handle.write('"<#ERROR>: Bad File, unexpected Instancied Variable"')
                elif at is parent:
                    handle.write('"<#ERROR>: Bad File, child is referencing parent"')
                else:
                    at.deserialize(handle, is_script, indent=indent, write_indent=False)
            case b"u":
                self._write_struct_start(handle, indent, "User Defined")
                handle.write('"symbol": ')
                self.data[0].deserialize(handle, is_script, indent=indent+1, write_indent=False)
                handle.write(',\n')
                self._write_indent(handle, indent+1)
                handle.write('"binary": ')
                handle.write(json.dumps(str(self.data[1])))
                self._write_struct_end(handle, indent)
            case b"m":
                self._write_generic(handle, indent, "Module")
            case b"o":
                self._write_struct_start(handle, indent, "Object")
                handle.write('"reference": ')
                self.data[0].deserialize(handle, is_script, indent=indent+1, write_indent=False)
                handle.write(',\n')
                self._write_indent(handle, indent+1)
                handle.write('"table": ')
                self.data[1].deserialize(handle, is_script, indent=indent+1, write_indent=False)
                self._write_struct_end(handle, indent)
            case b"c":
                self._write_generic(handle, indent, "Class")
            case b"M":
                self._write_generic(handle, indent, "Class or Module")
            case _:
                handle.write('"<#ERROR>: Uinplemented token ' + str(self.token) + '"')