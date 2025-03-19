from __future__ import annotations
from . import Plugin, WalkHelper
import io
import struct
import math
import os
from typing import Any
from dataclasses import dataclass
import zlib
import json

# RPG Maker XP/VX/VX Ace data files are based on the Ruby Marshal format
# The following documentation for this plugin:
# https://docs.ruby-lang.org/en/2.1.0/marshal_rdoc.html
class RM_Marshal(Plugin):
    DEFAULT_RPGMXP_DATA_FILE = ["ata/Actors.rxdata", "ata/Animations.rxdata", "ata/Armors.rxdata", "ata/Classes.rxdata", "ata/Enemies.rxdata", "ata/Items.rxdata", "ata/Troops.rxdata", "ata/Skills.rxdata", "ata/States.rxdata", "ata/Tilesets.rxdata", "ata/Weapons.rxdata"]
    DEFAULT_RPGMVX_DATA_FILE = ["ata/Actors.rvdata", "ata/Animations.rvdata", "ata/Armors.rvdata", "ata/Classes.rvdata", "ata/Enemies.rvdata", "ata/Items.rvdata", "ata/Troops.rvdata", "ata/Skills.rvdata", "ata/States.rvdata", "ata/Tilesets.rvdata", "ata/Weapons.rvdata"]
    DEFAULT_RPGMACE_DATA_FILE = ["ata/Actors.rvdata2", "ata/Animations.rvdata2", "ata/Armors.rvdata2", "ata/Classes.rvdata2", "ata/Enemies.rvdata2", "ata/Items.rvdata2", "ata/Troops.rvdata2", "ata/Skills.rvdata2", "ata/States.rvdata2", "ata/Tilesets.rvdata2", "ata/Weapons.rvdata2"]
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
        self.description : str = "v1.4\nHandle files from RPG Maker XP, VX and VX Ace"
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
                mc = MC(file_path.endswith('rvdata2'))
                mc.load(f.read())
            is_script : bool = file_path.endswith("Scripts.rxdata") or file_path.endswith("Scripts.rvdata") or file_path.endswith("Scripts.rvdata2")
            output_path : str = "projects/" + name + "/rm_marshal_export/" + file_path + ".json"
            self.owner.mkdir_path_folder(output_path)
            with open(output_path, mode="w", encoding="utf-8") as f:
                mc.root.deserialize(f, is_script)
            return "File deserialized to " + output_path
        except Exception as e:
            self.owner.log.error("[RPG Maker Marshal] Action 'rm_marshal_export' failed with error:\n" + self.owner.trbk(e))
            return "An error occured."

    def _export_script(self : RM_Marshal, name : str, file_path : str, settings : dict[str, Any] = {}) -> str:
        try:
            if file_path.endswith("ata/Scripts.rxdata") or file_path.endswith("ata/Scripts.rvdata") or file_path.endswith("ata/Scripts.rvdata2"):
                self.allow_ruby_plugin = False
                with open("projects/" + name + "/originals/" + file_path, mode="rb") as f:
                    entries = self.read(file_path, f.read())
                base_path : str = "projects/" + name + "/rm_scripts/"
                self.owner.mkdir_path_folder(base_path)
                for i, e in enumerate(entries):
                    # determine file name
                    name = str(i).zfill(6)
                    if e[0] != "Script":
                        tmp = e[0][7:].replace('/', '').replace('<', '').replace('>', '').replace(':', '').replace('"', '').replace('\\', '').replace('|', '').replace('?', '').replace('*', '').strip()
                        if tmp != "":
                            name += " " + tmp
                    with open(base_path + name + ".rb", mode="wb") as f:
                        f.write(e[1].encode('utf-8'))
                self.allow_ruby_plugin = True
                return "Scripts dumped to " + base_path
            else:
                return "This action is only for RPG Maker Scripts files."
        except Exception as e:
            self.allow_ruby_plugin = True
            self.owner.log.error("[RPG Maker Marshal] Action 'rm_marshal_script_export' failed with error:\n" + self.owner.trbk(e))
            return "An error occured."

    def file_extension(self : RM_Marshal) -> list[str]:
        return self.EXTENSIONS

    def match(self : RM_Marshal, file_path : str, is_for_action : bool) -> bool:
        return '.' in file_path and file_path.split('.')[-1] in self.EXTENSIONS

    def load_content(self : RM_Marshal, content : bytes, is_rv2 : bool) -> MC:
        mc : MC = MC(is_rv2)
        mc.load(content)
        return mc

    def is_default_rpgm_file(self : RM_Marshal, file_path : str, table : list[str]) -> bool:
        for k in table:
            if file_path.endswith(k):
                return True
        return False

    def read(self : RM_Marshal, file_path : str, content : bytes) -> list[list[str]]:
        mc : MC = self.load_content(content, file_path.endswith(".rvdata2"))
        if file_path.endswith(".rxdata"):
            if file_path.endswith("ata/CommonEvents.rxdata"):
                return self._read_walk_common(mc.root)
            elif len(file_path) >= 18 and file_path[-17:-10] == "ata/Map": # Map file
                return self._read_walk_map(mc.root)
            elif file_path.endswith("ata/Scripts.rxdata"):
                return self._read_walk_script(mc.root)
            elif file_path.endswith("ata/MapInfos.rxdata"):
                return self._read_walk_mapinfo(mc.root)
            elif self.is_default_rpgm_file(file_path, self.DEFAULT_RPGMXP_DATA_FILE):
                return self._read_walk_data(mc.root)
            else:
                return self._read_walk(mc.root)
        elif file_path.endswith(".rvdata"):
            if file_path.endswith("ata/CommonEvents.rvdata"):
                return self._read_walk_common(mc.root)
            elif len(file_path) >= 18 and file_path[-17:-10] == "ata/Map": # Map file
                return self._read_walk_map(mc.root)
            elif file_path.endswith("ata/Scripts.rvdata"):
                return self._read_walk_script(mc.root)
            elif file_path.endswith("ata/MapInfos.rvdata"):
                return self._read_walk_mapinfo(mc.root)
            elif self.is_default_rpgm_file(file_path, self.DEFAULT_RPGMVX_DATA_FILE):
                return self._read_walk_data(mc.root)
            else:
                return self._read_walk(mc.root)
        elif file_path.endswith(".rvdata2"):
            if file_path.endswith("ata/CommonEvents.rvdata2"):
                return self._read_walk_common(mc.root)
            elif len(file_path) >= 19 and file_path[-18:-11] == "ata/Map": # Map file
                return self._read_walk_map_rv2(mc.root)
            elif file_path.endswith("ata/Scripts.rvdata2"):
                return self._read_walk_script_rv2(mc.root)
            elif file_path.endswith("ata/MapInfos.rvdata2"):
                return self._read_walk_mapinfo_rv2(mc.root)
            elif self.is_default_rpgm_file(file_path, self.DEFAULT_RPGMACE_DATA_FILE):
                return self._read_walk_data(mc.root)
            else:
                return self._read_walk(mc.root)
        else:
            return self._read_walk(mc.root)

    def write(self : RM_Marshal, file_path : str, content : bytes, strings : dict) -> tuple[bytes, bool]:
        mc : MC = self.load_content(content, file_path.endswith(".rvdata2"))
        helper : WalkHelper = WalkHelper(file_path, strings)
        if file_path.endswith(".rxdata"):
            if file_path.endswith("ata/CommonEvents.rxdata"):
                self._write_walk_common(mc.root, helper)
            elif len(file_path) >= 18 and file_path[-17:-10] == "ata/Map": # Map file
                self._write_walk_map(mc.root, helper)
            elif file_path.endswith("ata/Scripts.rxdata"):
                self._write_walk_script(mc.root, helper)
            elif file_path.endswith("ata/MapInfos.rxdata"):
                self._write_walk_mapinfo(mc.root, helper)
            elif self.is_default_rpgm_file(file_path, self.DEFAULT_RPGMXP_DATA_FILE):
                self._write_walk_data(mc.root, helper)
            else:
                self._write_walk(mc.root, helper)
        elif file_path.endswith(".rvdata"):
            if file_path.endswith("ata/CommonEvents.rvdata"):
                self._write_walk_common(mc.root, helper)
            elif len(file_path) >= 18 and file_path[-17:-10] == "ata/Map": # Map file
                self._write_walk_map(mc.root, helper)
            elif file_path.endswith("ata/Scripts.rvdata"):
                self._write_walk_script(mc.root, helper)
            elif file_path.endswith("ata/MapInfos.rvdata"):
                self._write_walk_mapinfo(mc.root, helper)
            elif self.is_default_rpgm_file(file_path, self.DEFAULT_RPGMVX_DATA_FILE):
                self._write_walk_data(mc.root, helper)
            else:
                self._write_walk(mc.root, helper)
        elif file_path.endswith(".rvdata2"):
            if file_path.endswith("ata/CommonEvents.rvdata2"):
                self._write_walk_common(mc.root, helper)
            elif len(file_path) >= 19 and file_path[-18:-11] == "ata/Map": # Map file
                self._write_walk_map_rv2(mc.root, helper)
            elif file_path.endswith("ata/Scripts.rvdata2"):
                self._write_walk_script_rv2(mc.root, helper)
            elif file_path.endswith("ata/MapInfos.rvdata2"):
                self._write_walk_mapinfo_rv2(mc.root, helper)
            elif self.is_default_rpgm_file(file_path, self.DEFAULT_RPGMACE_DATA_FILE):
                self._write_walk_data(mc.root, helper)
            else:
                self._write_walk(mc.root, helper)
        else:
            self._write_walk(mc.root, helper)
        return mc.dump(), helper.modified
    
    # Return None if invalid element token
    def _util_read_string(self : RM_Marshal, me : ME) -> str|None:
        match me.token:
            case b'"':
                return me.data.decode('utf-8')
            case b'I':
                return self._util_read_string(me.data)
            case _:
                return None

    # Return True if it encountered a string
    def _util_write_string(self : RM_Marshal, helper : WalkHelper, me : ME, group : str|None = None) -> bool:
        match me.token:
            case b'"':
                if me.data != b"":
                    tmp : str = helper.apply_string(me.data.decode('utf-8'), group)
                    if helper.str_modified:
                        me.data = tmp.encode('utf-8')
                return True
            case b'I':
                return self._util_write_string(helper, me.data)
            case _:
                return False

    # Generic Ruby Marshal processing
    def _read_walk(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        match me.token:
            case b'"'|b'I':
                raise Exception("[RM_Marshal] Invalid code path")
            case b'[':
                for i, e in enumerate(me.data):
                    tmp = self._util_read_string(e)
                    if tmp is not None:
                        if tmp != "":
                            entries.append([str(i), tmp])
                    else:
                        entries.extend(self._read_walk(e))
            case b'{':
                for e in me.data:
                    tmp = self._util_read_string(e[1])
                    if tmp is not None:
                        if tmp != "":
                            entries.append([e[0].at().data.decode('utf-8'), tmp])
                    else:
                        entries.extend(self._read_walk(e[1]))
            case b'o':
                for e in me.data[1]:
                    tmp = self._util_read_string(e[1])
                    if tmp is not None:
                        if tmp != "":
                            entries.append([e[0].at().data.decode('utf-8'), tmp])
                    else:
                        entries.extend(self._read_walk(e[1]))
            case _:
                pass
        return entries

    def _write_walk(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        match me.token:
            case b'"'|b'I':
                raise Exception("[RM_Marshal] Invalid code path")
            case b'[':
                for i in range(len(me.data)):
                    if not self._util_write_string(helper, me.data[i], str(i)):
                        self._write_walk(me.data[i], helper)
            case b'{':
                for i in range(len(me.data)):
                    if not self._util_write_string(helper, me.data[i][1], me.data[i][0].at().data.decode('utf-8')):
                        self._write_walk(me.data[i][1], helper)
            case b'o':
                for i in range(len(me.data[1])):
                    if not self._util_write_string(helper, me.data[1][i][1], me.data[1][i][0].at().data.decode('utf-8')):
                        self._write_walk(me.data[1][i][1], helper)
            case _:
                pass

    # RPGMK Map files processing
    def _read_walk_map(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        evlist = me.searchHash(b"@events")
        if len(evlist) > 0:
            for ev in evlist[0].data:
                r = ev[1].searchHash(b"@name")
                strings : list[list[str]] = []
                if len(r) == 0 or r[0].data == b"":
                    strings.append([""])
                else:
                    strings.append([r[0].data.decode('utf-8')])
                r = ev[1].searchHash(b"@pages")
                if len(r) > 0:
                    for i, p in enumerate(r[0].data):
                        r2 = p.searchHash(b"@list")
                        if len(r2) > 0:
                            results = self._read_walk_event(r2[0])
                            if len(results) > 0:
                                strings.append(["Page {}".format(i+1)])
                                strings.extend(results)
                if len(strings) > 1:
                    entries.extend(strings)
        return entries

    def _write_walk_map(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        evlist = me.searchHash(b"@events")
        if len(evlist) > 0:
            for ev in evlist[0].data:
                r = ev[1].searchHash(b"@pages")
                if len(r) > 0:
                    for p in r[0].data:
                        r2 = p.searchHash(b"@list")
                        if len(r2) > 0:
                            self._write_walk_event(r2[0], helper)

    # RPGMK Map files processing (VX Ace version)
    def _read_walk_map_rv2(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        evlist = me.searchHash(b"@events")
        if len(evlist) > 0:
            name = ""
            for i in range(len(evlist[0].data)):
                match evlist[0].data[i][0].at().token:
                    case b'i':
                        # reset
                        name = ""
                        # set id and name
                        r = evlist[0].data[i][1].searchHash(b"@name")
                        if len(r) > 0:
                            name = r[0].data.data.decode("utf-8")
                    case b':':
                        if evlist[0].data[i][0].at().data == b"@pages":
                            strings : list[str] = [[name]]
                            for p in evlist[0].data[i][1].data:
                                if p.token == b'o':
                                    r = p.searchHash(b"@list")
                                    if len(r) > 0:
                                        strings.extend(self._read_walk_event(r[0]))
                            if len(strings) > 1:
                                entries.extend(strings)
        return entries

    def _write_walk_map_rv2(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        evlist = me.searchHash(b"@events")
        if len(evlist) > 0:
            for i in range(len(evlist[0].data)):
                if evlist[0].data[i][0].at().token == b':' and evlist[0].data[i][0].at().data == b"@pages":
                    for p in evlist[0].data[i][1].data:
                        if p.token == b'o':
                            r = p.searchHash(b"@list")
                            if len(r) > 0:
                                self._write_walk_event(r[0], helper)

    # RPGMK CommonEvents processing
    def _read_walk_common(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        for e in me.data:
            if e.token == b"0":
                continue
            r = e.searchHash(b"@list")
            if len(r) > 0:
                strings = self._read_walk_event(r[0])
                if len(strings) > 0:
                    name = "Common Event"
                    r = e.searchHash(b"@id")
                    if len(r) > 0:
                        name += " " + str(r[0].data)
                    r = e.searchHash(b"@name")
                    if len(r) > 0:
                        name += " " + str(self._util_read_string(r[0]))
                    entries.append([name])
                    entries.extend(strings)
        return entries

    def _write_walk_common(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        for e in me.data:
            if e.token == b"0":
                continue
            r = e.searchHash(b"@list")
            if len(r) > 0:
                self._write_walk_event(r[0], helper)

    # RPGMK Events processing (used by Map and CommonEvents)
    # Used by both Map and CommonEvents
    # We process differently based on the event codes
    def _walk_event_continuous_command(self : RM_Marshal, i : int, cmds : list[ME], code : int) -> tuple[int, list[str]]:
        text : list[str] = []
        while i < len(cmds) and (cmds[i].token != b'o' or cmds[i].searchHash(b"@code")[0].data == code):
            if cmds[i].token == b'o':
                parameters = cmds[i].searchHash(b"@parameters")[0].data
                if parameters[0].token == b'"' and parameters[0].data != b"": # XP, VX
                    text.append(parameters[0].data.decode('utf-8'))
                elif parameters[0].token == b'I' and parameters[0].data.token == b'"' and parameters[0].data.data != b"": # VX Ace
                    text.append(parameters[0].data.data.decode('utf-8'))
            i += 1
        i -= 1
        return i, text

    def _read_walk_event(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        group : list[str] = [""]
        i : int = 0
        while i < len(me.data):
            cmd = me.data[i]
            if cmd.token != b'o':
                i += 1
                continue
            code = cmd.searchHash(b"@code")[0].data
            r = cmd.searchHash(b"@parameters")[0]
            if r.token != b'[':
                i += 1
                continue
            parameters = r.data
            group[0] = "Command: " + self.RPGMXP_CODE_TABLE.get(code, "Code " + str(code))
            match code:
                case 101: # Show Text commands
                    tmp = self._util_read_string(parameters[0])
                    if tmp is not None and tmp != "":
                        group.append(tmp)
                    i += 1
                    i, text = self._walk_event_continuous_command(i, me.data, 401)
                    if len(text) > 0:
                        if self.settings.get("rm_marshal_multiline", False):
                            group.append("\n".join(text))
                        else:
                            group.extend(text)
                case 355: # Show Text commands
                    tmp = self._util_read_string(parameters[0])
                    if tmp is not None and tmp != "":
                        group.append(tmp)
                    i += 1
                    i, text = self._walk_event_continuous_command(i, me.data, 655)
                    if len(text) > 0:
                        if self.settings.get("rm_marshal_multiline", False):
                            group.append("\n".join(text))
                        else:
                            group.extend(text)
                case 102:
                    for pm in parameters:
                        if pm.token == b'[':
                            for sub in pm.data:
                                tmp = self._util_read_string(sub)
                                if tmp is not None and tmp != "":
                                    group.append(tmp)
                        else:
                            tmp = self._util_read_string(pm)
                            if tmp is not None and tmp != "":
                                group.append(tmp)
                case 108|408: # Comment
                    pass
                case _: # Default
                    for pm in parameters:
                        tmp = self._util_read_string(pm)
                        if tmp is not None and tmp != "":
                            group.append(tmp)
            if len(group) > 1:
                entries.append(group)
                group = [""]
            i += 1
        return entries

    def _write_walk_event(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        i : int = 0
        while i < len(me.data):
            cmd = me.data[i]
            if cmd.token != b'o':
                i += 1
                continue
            code = cmd.searchHash(b"@code")[0].data
            r = cmd.searchHash(b"@parameters")[0]
            if r.token != b'[':
                i += 1
                continue
            parameters = r.data
            group : str = "Command: " + self.RPGMXP_CODE_TABLE.get(code, "Code " + str(code))
            match code:
                case 101: # Show Text commands
                    self._util_write_string(helper, parameters[0], group)
                    i += 1
                    start = i
                    i, text = self._walk_event_continuous_command(i, me.data, 401)
                    if len(text) > 0:
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
                        h : int = 0
                        for j in range(start, i+1):
                            if me.data[j].token == b'o':
                                parameters = me.data[j].searchHash(b"@parameters")[0].data
                                if parameters[0].token == b'"' and parameters[0].data != b"": # XP, VX
                                    parameters[0].data = text[h].encode("utf-8")
                                    h += 1
                                elif parameters[0].token == b'I' and parameters[0].data.token == b'"' and parameters[0].data.data != b"": # VX Ace
                                    parameters[0].data.data = text[h].encode("utf-8")
                                    h += 1
                case 355: # Show Text commands
                    self._util_write_string(helper, parameters[0], group)
                    i += 1
                    start = i
                    i, text = self._walk_event_continuous_command(i, me.data, 655)
                    if len(text) > 0:
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
                        h : int = 0
                        for j in range(start, i+1):
                            if me.data[j].token == b'o':
                                parameters = me.data[j].searchHash(b"@parameters")[0].data
                                if parameters[0].token == b'"' and parameters[0].data != b"": # XP, VX
                                    parameters[0].data = text[h].encode("utf-8")
                                    h += 1
                                elif parameters[0].token == b'I' and parameters[0].data.token == b'"' and parameters[0].data.data != b"": # VX Ace
                                    parameters[0].data.data = text[h].encode("utf-8")
                                    h += 1
                case 102:
                    for pm in parameters:
                        if pm.token == b'[':
                            for sub in pm.data:
                                self._util_write_string(helper, sub, group)
                        else:
                            self._util_write_string(helper, pm, group)
                case 108|408: # Comment
                    pass
                case _: # Default
                    for pm in parameters:
                        self._util_write_string(helper, pm, group)
            i += 1

    # RPGMK Scripts processing
    def _read_walk_script(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        for e in me.data:
            group : list[str] = ["Script"]
            if e.data[1].data != b"":
                group[0] = "Script: " + e.data[1].data.decode('utf-8')
            if e.data[2].data != b"":
                script = zlib.decompressobj().decompress(e.data[2].data).decode('utf-8')
                if self.allow_ruby_plugin and "Ruby" in self.owner.plugins:
                    self.owner.plugins["Ruby"].reset()
                    strings = self.owner.plugins["Ruby"]._parse_strings(script, None, len(entries))[0]
                    if len(strings) > 0:
                        entries.append(group)
                        entries.extend(strings)
                        group = [""]
                else:
                    group.append(script)
            if len(group) >1:
                entries.append(group)
        return entries

    def _write_walk_script(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        for e in me.data:
            group : str = "Script"
            if e.data[1].data != b"":
                s = e.data[1].data.decode('utf-8')
                group = "Script: " + s
            if e.data[2].data != b"":
                script = zlib.decompressobj().decompress(e.data[2].data).decode('utf-8')
                if self.allow_ruby_plugin and "Ruby" in self.owner.plugins:
                    self.owner.plugins["Ruby"].reset()
                    newscript = self.owner.plugins["Ruby"]._parse_strings(script, helper)[1]
                    if newscript != script:
                        compressor = zlib.compressobj()
                        e.data[2].data = compressor.compress(newscript.encode('utf-8')) + compressor.flush()
                else:
                    tmp : str = helper.apply_string(script, group)
                    if helper.str_modified:
                        compressor = zlib.compressobj()
                        e.data[2].data = compressor.compress(tmp.encode('utf-8')) + compressor.flush()

    # RPGMK Scripts processing (VX Ace version)
    def _read_walk_script_rv2(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        name : str = "Script"
        for e in me.data:
            if e.token in (b'"', b'I'):
                if e.token == b'I':
                    if e.data.token == b'"':
                        target = e.data
                    else:
                        continue
                else:
                    target = e
                try:
                    tmp = target.data.decode('utf-8')
                    if name == "":
                        name = "Script"
                    else:
                        name = "Script: " + tmp
                except:
                    if target.data != b"":
                        script = zlib.decompressobj().decompress(target.data).decode('utf-8')
                        if self.allow_ruby_plugin and "Ruby" in self.owner.plugins:
                            self.owner.plugins["Ruby"].reset()
                            strings = self.owner.plugins["Ruby"]._parse_strings(script, None, len(entries))[0]
                            if len(strings) > 0:
                                entries.append([name])
                                entries.extend(strings)
                        else:
                            entries.append([name, script])
                        name = ""
        return entries

    def _write_walk_script_rv2(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        name : str = "Script"
        for e in me.data:
            if e.token in (b'"', b'I'):
                if e.token == b'I':
                    if e.data.token == b'"':
                        target = e.data
                    else:
                        continue
                else:
                    target = e
                try:
                    tmp = target.data.decode('utf-8')
                    if name == "":
                        name = "Script"
                    else:
                        name = "Script: " + tmp
                except:
                    if target.data != b"":
                        script = zlib.decompressobj().decompress(target.data).decode('utf-8')
                        if self.allow_ruby_plugin and "Ruby" in self.owner.plugins:
                            self.owner.plugins["Ruby"].reset()
                            newscript = self.owner.plugins["Ruby"]._parse_strings(script, helper)[1]
                            if newscript != script:
                                compressor = zlib.compressobj()
                                target.data = compressor.compress(newscript.encode('utf-8')) + compressor.flush()
                        else:
                            tmp : str = helper.apply_string(script, name)
                            if helper.str_modified:
                                compressor = zlib.compressobj()
                                target.data = compressor.compress(tmp.encode('utf-8')) + compressor.flush()
                        name = ""

    # RPGMK MapInfos processing
    def _read_walk_mapinfo(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        for e in me.data:
            if e[1].token == b'o':
                r : list[ME] = e[1].searchHash(b"@name")
                if len(r) > 0:
                    entries.append(["Map " + str(e[0]), r[0].data.decode('utf-8')])
        return entries

    def _write_walk_mapinfo(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        for e in me.data:
            if e[1].token == b'o':
                r : list[ME] = e[1].searchHash(b"@name")
                if len(r) > 0:
                    tmp : str = helper.apply_string(r[0].data.decode('utf-8'), "Map " + str(e[0]))
                    if helper.str_modified:
                        r[0].data = tmp.encode('utf-8')

    # RPGMK MapInfos processing (VX Ace version)
    def _read_walk_mapinfo_rv2(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        for e in me.data:
            if e[1].token == b'o':
                r : list[ME] = e[1].searchHash(b"@name")
                if len(r) > 0:
                    entries.append(["Map " + str(e[0]), r[0].data.data.decode('utf-8')])
        return entries

    def _write_walk_mapinfo_rv2(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        for e in me.data:
            if e[1].token == b'o':
                r : list[ME] = e[1].searchHash(b"@name")
                if len(r) > 0:
                    tmp : str = helper.apply_string(r[0].data.data.decode('utf-8'), "Map " + str(e[0]))
                    if helper.str_modified:
                        r[0].data.data = tmp.encode('utf-8')

    # RPGMK standard Data Files processing
    def _read_walk_data(self : RM_Marshal, me : ME) -> list[list[str]]:
        entries : list[list[str]] = []
        for e in me.data:
            if e.token == b'o':
                strings = self._read_walk(e)
                if len(strings) > 0:
                    r : list[ME] = e.searchHash(b"@id")
                    if len(r) > 0:
                        entries.append(["ID " + str(r[0].data)])
                    else:
                        entries.append([""])
                    entries.extend(strings)
        return entries

    def _write_walk_data(self : RM_Marshal, me : ME, helper : WalkHelper) -> None:
        for e in me.data:
            if e.token == b'o':
                self._write_walk(e, helper)

# Classes for handling Ruby Marshal files
@dataclass(slots=True)
class MC(): # for Marshal Container
    root : ME|None
    symtable : list[ME]
    objtable : list[ME]
    is_rv2 : bool

    def __init__(self : MC, is_rv2 : bool = False) -> None:
        self.root = None
        self.symtable = []
        self.objtable = [None]
        self.is_rv2 = is_rv2

    def load(self : MC, binary : bytes) -> None:
        if self.root is not None:
            raise Exception("[RM_Marshal] This Marshal Container is already initialized")
        with io.BytesIO(binary) as handle:
            if handle.read(1) != b"\x04" or handle.read(1) != b"\x08":
                raise Exception("[RM_Marshal] Invalid Magic Number in binary")
            self.root = self._process_token(handle)

    def _token_unimplemented(self : MC, token : bytes, handle : io.BytesIO) -> None:
        raise Exception("[RM_Marshal] Token " + str(token) + " isn't implemented")

    def _process_token(self : MC, handle : io.BytesIO) -> ME:
        token = handle.read(1)
        if token is None:
            raise Exception("[RM_Marshal] Reached EOF")
        if token not in self.TOKEN_TABLE:
            return self._token_unimplemented(token, handle)
        else:
            index : int|None
            if token not in (b"0", b"T", b"F", b"i", b":", b";", b"@"): 
                index = len(self.objtable)
                self.objtable.append(None)
            else:
                index = None
            me : ME = self.TOKEN_TABLE[token](self, token, handle)
            if index is not None:
                self.objtable[index] = me
            return me

    def util_read_fixnum(self : MC, handle : io.BytesIO) -> int:
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
                value += factor / 256
            elif value < 0:
                value += factor
            sign = int(math.copysign(size, back))
            output = struct.pack("b", sign)
            for i in range(size):
                output += struct.pack("B", value % 256)
                value = value >> 8
            return output

    def _read_nil(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, None)

    def _read_true(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, True)

    def _read_false(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, False)

    def _read_instancevariable(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, self._process_token(handle))

    def _read_string(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        me : ME = ME(self, token, handle.read(self.util_read_fixnum(handle)))
        if self.is_rv2:
            b : bytes = handle.read(1) # To read extra 0x06 byte
            if b != b"\x06":
                handle.seek(-1, os.SEEK_CUR)
            else:
                me._b06_ = True
        return me

    def _read_symbol(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        me : ME = ME(self, token, handle.read(self.util_read_fixnum(handle)))
        self.symtable.append(me)
        return me

    def _read_symlink(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        me : ME = ME(self, token, self.util_read_fixnum(handle))
        if me.data < 0 or me.data >= len(self.symtable):
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
        hashtable : list[tuple] = []
        for i in range(size):
            hashtable.append((self._process_token(handle), self._process_token(handle)))
        me.data = hashtable
        return me

    def _read_float(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, handle.read(self.util_read_fixnum(handle)))

    def _read_bignum(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        sign = handle.read(1)
        size = self.util_read_fixnum(handle)
        b = b""
        for i in range(size):
            b += handle.read(2)
        return ME(self, token, (sign, b))

    def _read_regex(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, handle.read(self.util_read_fixnum(handle)))

    def _read_usermarshal(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, (self._process_token(handle), self._process_token(handle)))

    def _read_object(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, (self._process_token(handle), self._read_hashtable(b'', handle).data))

    def _read_link(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        me : ME = ME(self, token, self.util_read_fixnum(handle))
        if me.data <= 0 or me.data >= len(self.objtable):
            raise Exception("[RM_Marshal] Link isn't pointing to an existing element")
        return me

    def _read_userdefined(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        return ME(self, token, (self._process_token(handle), handle.read(self.util_read_fixnum(handle))))

    def _read_classmodule(self : MC, token : bytes, handle : io.BytesIO) -> ME:
        me : ME = ME(self, token, handle.read(self.util_read_fixnum(handle)))
        self.objtable[-1] = me
        return me
    
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
    
    def dump(self : MC) -> bytes:
        if self.root is None:
            raise Exception("[RM_Marshal] Marshal Container is uninitialized, use load() first")
        with io.BytesIO() as handle:
            handle.write(b"\x04\x08")
            self.root.dump(handle)
            return handle.getvalue()

@dataclass(slots=True)
class ME(): # for Marshal Element
    owner : MC
    token : bytes
    data : Any
    _b06_ : bool
    
    def __init__(self : ME, owner : MC, token : bytes, data : Any = None) -> None:
        self.owner = owner
        self.token = token
        self.data = data
        self._b06_ = False

    def __repr__(self : ME) -> str:
        return self.token.decode() + ":" + repr(self.data)

    def __str__(self : ME) -> str:
        return str(self.data)

    def __hash__(self : ME) -> int:
        return hash((self.token, self.data))

    def at(self : ME) -> ME:
        match self.token:
            case b";":
                return self.owner.symtable[self.data]
            case b"@":
                return self.owner.objtable[self.data]
            case _:
                return self

    def searchHash(self : ME, h : bytes) -> list[ME]:
        results : list[ME] = []
        match self.token:
            case b"{":
                for e in self.data:
                    if e[0].at().data == h:
                        results.append(e[1])
            case b"o":
                for e in self.data[1]:
                    if e[0].at().data == h:
                        results.append(e[1])
        return results

    def dump(self : ME, handle : io.BytesIO) -> None:
        handle.write(self.token)
        match self.token:
            case b"0"|b"T"|b"F":
                pass
            case b"I":
                self.data.dump(handle)
            case b'"'|b":"|b"f"|b"/"|b"m"|b"c"|b"M":
                handle.write(self.owner.util_write_fixnum(len(self.data)))
                handle.write(self.data)
                if self.token == b'"' and self._b06_: # Writing extra 0x06 byte of this file version
                    handle.write(b"\x06")
            case b"i":
                handle.write(self.owner.util_write_fixnum(self.data))
            case b"[":
                handle.write(self.owner.util_write_fixnum(len(self.data)))
                for e in self.data:
                    e.dump(handle)
            case b"{":
                handle.write(self.owner.util_write_fixnum(len(self.data)))
                for e in self.data:
                    e[0].dump(handle)
                    e[1].dump(handle)
            case b"l":
                handle.write(self.data[0])
                handle.write(self.owner.util_write_fixnum(len(self.data[1])))
                handle.write(self.data[1])
            case b"U":
                self.data[0].dump(handle)
                self.data[1].dump(handle)
            case b";"|b"@":
                handle.write(self.owner.util_write_fixnum(self.data))
            case b"u":
                self.data[0].dump(handle)
                handle.write(self.owner.util_write_fixnum(len(self.data[1])))
                handle.write(self.data[1])
            case b"o":
                self.data[0].dump(handle)
                handle.write(self.owner.util_write_fixnum(len(self.data[1])))
                for e in self.data[1]:
                    e[0].dump(handle)
                    e[1].dump(handle)
            case _:
                raise Exception("[RM_Marshal] Unknown token type:" + str(self.token))

    # For debugging purpose
    def deserialize(self : ME, handle : Any, is_script : bool, level : int = 0) -> Any:
        for i in range(level):
            handle.write('\t')
        if level < 0:
            level = - level
        match self.token:
            case b"0":
                handle.write('null')
            case b"T":
                handle.write('true')
            case b"F":
                handle.write('false')
            case b"I":
                handle.write('[ "#InsVar", ')
                self.data.deserialize(handle, is_script, -(level+1))
                handle.write(' ]')
            case b'"':
                try:
                    handle.write(json.dumps(self.data.decode('utf-8'), ensure_ascii=False))
                except:
                    try:
                        if not is_script:
                            raise Exception()
                        handle.write(json.dumps(zlib.decompressobj().decompress(self.data).decode('utf-8'), ensure_ascii=False))
                    except:
                        handle.write('#ERROR: String of unknown encoding')
            case b":":
                handle.write('[ "#Symbol", ')
                handle.write(json.dumps(self.data.decode('utf-8')))
                handle.write(' ]')
            case b'i':
                handle.write(json.dumps(self.data))
            case b"[":
                handle.write('[\n')
                for i in range(len(self.data)):
                    self.data[i].deserialize(handle, is_script, level+1)
                    if i != len(self.data)-1:
                        handle.write(',\n')
                handle.write('\n')
                for i in range(level):
                    handle.write('\t')
                handle.write(']')
            case b"{":
                handle.write('{\n')
                for i in range(len(self.data)):
                    self.data[i][0].deserialize(handle, is_script, level+1)
                    handle.write(': ')
                    self.data[i][1].deserialize(handle, is_script, -(level+1))
                    if i != len(self.data)-1:
                        handle.write(',\n')
                handle.write('\n')
                for i in range(level):
                    handle.write('\t')
                handle.write('}')
            case b"f":
                handle.write('[ "#Float", ')
                handle.write(json.dumps(str(self.data)))
                handle.write(' ]')
            case b"l":
                handle.write('[ "#BigNum", ')
                handle.write(json.dumps(str(self.data)))
                handle.write(' ]')
            case b"/":
                handle.write('[ "#Regex", ')
                handle.write(json.dumps(str(self.data)))
                handle.write(' ]')
            case b"U":
                return ["type:U",self.data[0].deserialize(is_script),self.data[1].deserialize(is_script)]
            case b";":
                handle.write('[ "#SymbolLink", ')
                handle.write(json.dumps(str(self.data)))
                handle.write(' ]')
            case b"@":
                handle.write('[ "#Link", ')
                handle.write(json.dumps(str(self.data)))
                handle.write(' ]')
            case b"u":
                return ["type:u",str(self.data[0]), str(self.data[1])]
            case b"m":
                handle.write('[ "#Module", ')
                handle.write(json.dumps(str(self.data)))
                handle.write(' ]')
                return ["type:m",str(self.data)]
            case b"o":
                handle.write('[ "#Object:", ')
                self.data[0].deserialize(handle, is_script, -(level+1))
                handle.write(', ')
                handle.write('{\n')
                for i in range(len(self.data[1])):
                    self.data[1][i][0].deserialize(handle, is_script, level+1)
                    handle.write(': ')
                    self.data[1][i][0].deserialize(handle, is_script, -(level+1))
                    if i != len(self.data[1])-1:
                        handle.write(',\n')
                handle.write('\n')
                for i in range(level):
                    handle.write('\t')
                handle.write('}')
                handle.write(' ]')
            case b"d":
                handle.write('[ "#Extended", ')
                handle.write(json.dumps(str(self.data)))
                handle.write(' ]')
            case b"c":
                handle.write('[ "#Class", ')
                handle.write(json.dumps(str(self.data)))
                handle.write(' ]')
            case b"M":
                handle.write('[ "#Class/Module", ')
                handle.write(json.dumps(str(self.data)))
                handle.write(' ]')
            case _:
                handle.write("#ERROR: Uinplemented token " + str(self.token))