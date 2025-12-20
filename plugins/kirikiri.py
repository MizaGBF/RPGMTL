from __future__ import annotations
from . import Plugin, WalkHelper, GloIndex, LocIndex
from typing import Any
import unicodedata

class KiriKiri(Plugin):
    def __init__(self : KiriKiri) -> None:
        super().__init__()
        self.name : str = "KiriKiri"
        self.description : str = " v1.4\nHandle KiriKiri KAG and script files"
        self.related_tool_plugins : list[str] = [self.name]

    def get_setting_infos(self : KiriKiri) -> dict[str, list]:
        return {
            "kirikiri_default_encoding": ["Select the default script encoding", "str", "shift_jis", ["auto"] + self.FILE_ENCODINGS]
        }

    def get_tool_infos(self : KiriKiri) -> dict[str, list]:
        return {
            "kirikiri_space_removers": [
                "assets/images/note.png", "Non-Standard Space Remover", self.tool_space_removal,
                {
                    "type":self.COMPLEX_TOOL,
                    "params":{
                        "_t_0000":["This tool can be DESTRUCTIVE. It's recommended to backup strings.bak-1.json after.", "display", None, None],
                        "_t_0001":["It will replace all non-standard whitespace characters with normal ones", "display", None, None],
                        "_t_0002":["OR, in case Zero-Width Spaces, will remove them.", "display", None, None],
                        "_t_0003":["It won't affect disabled strings.", "display", None, None],
                    },
                    "help":"Tool to automatically replace non-standard whitespace characters with normal ones."
                }
            ]
        }

    def tool_space_removal(self : KiriKiri, name : str, params : dict[str, Any]) -> str:
        try:
            self.owner.save() # save first!
            self.owner.backup_strings_file(name) # backup strings.json
            self.owner.load_strings(name)
            seen : set[str] = set() # used to track which strings we tested
            count : int = 0
            for file in self.owner.strings[name]["files"]:
                for i, group in enumerate(self.owner.strings[name]["files"][file]):
                    for j in range(1, len(group)):
                        sid : str = self.owner.strings[name]["files"][file][i][j][LocIndex.ID]
                        if self.owner.strings[name]["strings"][sid][GloIndex.TL] is not None:
                            if sid not in seen:
                                seen.add(sid)
                                s, b = self.edit_non_standard_spaces(self.owner.strings[name]["strings"][sid][GloIndex.TL])
                                if b:
                                    self.owner.modified[name] = True
                                    self.owner.strings[name]["strings"][sid][GloIndex.TL] = s
                                    count += 1
                        
                        if self.owner.strings[name]["files"][file][i][j][LocIndex.TL] is not None:
                            s, b = self.edit_non_standard_spaces(self.owner.strings[name]["files"][file][i][j][LocIndex.TL])
                            if b:
                                self.owner.modified[name] = True
                                self.owner.strings[name]["files"][file][i][j][LocIndex.TL] = s
                                count += 1
            if count == 0:
                return "No strings have been modified"
            else:
                return str(count) + " strings have been modified"
        except Exception as e:
            self.owner.log.error("[KiriKiri] Tool 'tool_space_removal' failed with error:\n" + self.owner.trbk(e))
            return "An unexpected error occured"

    def edit_non_standard_spaces(self : KiriKiri, text : str) -> tuple[str, bool]:
        modifications : dict[str, str] = {}

        for index, char in enumerate(text):
            if char != " ":
                category = unicodedata.category(char)
                # Note:
                # 'Zs' = Space Separator (includes NBSP, Ideographic Space)
                # 'Cf' = Format (includes Zero Width Space, ZWNJ)
                # 'Cc' = Control (includes \t, \n, \r) usually standard, but included here for context
                if (category.startswith('Z') or category == 'Cf'):
                    if category == 'Cf' and unicodedata.name(char, "") == "ZERO WIDTH SPACE":
                        modifications[char] = ""
                    else:
                        modifications[char] = " "

        modified = text
        for ori, modif in modifications.items():
            modified = modified.replace(ori, modif)
        return modified, modified != text

    def match(self : KiriKiri, file_path : str, is_for_action : bool) -> bool:
        lp : str = file_path.lower()
        return lp.endswith(".ks") or lp.endswith(".tjs")

    def read(self : KiriKiri, file_path : str, content : bytes) -> list[list[str]]:
        lp : str = file_path.lower()
        if lp.endswith(".ks"):
            return self.read_ks(file_path, content)
        elif lp.endswith(".tjs"):
            return self.read_tjs(file_path, content)
        else:
            return []

    def get_first_character(self : KiriKiri, string : str) -> str:
        for c in string:
            if not c.isspace():
                return c
        return ""

    def read_ks(self : KiriKiri, file_path : str, content : bytes) -> list[list[str]]:
        try:
            lines = content.decode(self.settings["kirikiri_default_encoding"]).splitlines()
        except:
            lines = self.decode(content).splitlines()
        entries : list[list[str]] = []
        group : list[str] = [""]
        i : int = 0
        while i < len(lines):
            line = lines[i]
            match self.get_first_character(line):
                case ";"|"@"|"":
                    if len(group) > 1:
                        entries.append(group)
                    group = [""]
                case "*":
                    p : int = line.find("|")
                    if p != -1:
                        line = line[p+1:]
                        if line.strip() != "":
                            if group[0] != "Label":
                                if len(group) > 1:
                                    entries.append(group)
                                group = ["Label"]
                            group.append(line)
                case "[":
                    ls : str = line.strip()
                    if ls.startswith("[seladd "):
                        if group[0] != "Selection":
                            if len(group) > 1:
                                entries.append(group)
                            group = ["Selection"]
                        if 'text="' in ls:
                            group.append(line.split('text="')[1].split('"')[0])
                        elif "text='" in ls:
                            group.append(line.split("text='")[1].split("'")[0])
                    elif ls.startswith("[link "):
                        if group[0] != "Choices":
                            if len(group) > 1:
                                entries.append(group)
                            group = ["Choices"]
                        group.append(line.split("]")[1].split("[")[0])
                    elif ls.startswith("[iscript]"):
                        i += 1
                        start = i
                        while not lines[i].strip().startswith("[endscript]"):
                            i += 1
                        if "Javascript" in self.owner.plugins:
                            result, _ = self.owner.plugins["Javascript"]._parse_strings("\r\n".join(lines[start:i]), None)
                            if len(result) > 0:
                                if len(group) > 1:
                                    entries.append(group)
                                group = [""]
                                entries.append(["Script"])
                                entries.extend(result)
                                entries.append(["Script End"])
                        else:
                            self.owner.log.warning("[KiriKiri] Can't parse TJS files, the Javascript plugin is required")
                    else:
                        if len(group) > 1:
                            entries.append(group)
                        group = [""]
                case _:
                    if group[0] != "":
                        if len(group) > 1:
                            entries.append(group)
                        group = [""]
                    group.append(line)
            i += 1
        if len(group) > 1:
            entries.append(group)
        return entries

    def read_tjs(self : KiriKiri, file_path : str, content : bytes) -> list[list[str]]:
        try:
            script = content.decode(self.settings["kirikiri_default_encoding"])
        except:
            script = self.decode(content)
        if "Javascript" in self.owner.plugins:
            entries, _ = self.owner.plugins["Javascript"]._parse_strings(script, None)
            return entries
        else:
            self.owner.log.warning("[KiriKiri] Can't parse TJS files, the Javascript plugin is required")
            return []

    def write(self : KiriKiri, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        lp : str = file_path.lower()
        if lp.endswith(".ks"):
            return self.write_ks(name, file_path, content)
        elif lp.endswith(".tjs"):
            return self.write_tjs(name, file_path, content)
        else:
            return content, False

    def write_ks(self : KiriKiri, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
        try:
            lines = content.decode(self.settings["kirikiri_default_encoding"]).splitlines()
            encoding = self.settings["kirikiri_default_encoding"]
        except:
            lines = self.decode(content).splitlines()
            encoding = self.FILE_ENCODINGS[self._enc_cur_]
        i : int = 0
        while i < len(lines):
            line = lines[i]
            match self.get_first_character(line):
                case ";"|"@"|"":
                    pass
                case "*":
                    p : int = line.find("|")
                    if p != -1:
                        label_txt = line[p+1:]
                        if label_txt.strip() != "":
                            tmp = helper.apply_string(label_txt, "Label")
                            if helper.str_modified:
                                lines[i] = line[:p+1] + tmp
                case "[":
                    ls : str = line.strip()
                    if ls.startswith("[seladd "):
                        quote_char : str = None
                        parts : list[str] = []
                        if 'text="' in ls:
                            parts = line.split('text="')
                            quote_char = '"'
                        elif "text='" in ls:
                            parts = line.split("text='")
                            quote_char = "'"
                        if quote_char is not None:
                            parts[0] += "text="
                            tmp = parts[1].split(quote_char)
                            parts = parts[:1]
                            parts.extend(tmp)
                            parts[1] = helper.apply_string(parts[1], "Selection")
                            if helper.str_modified:
                                lines[i] = quote_char.join(parts)
                    elif ls.startswith("[link "):
                        a = line.find("]")
                        b = line.find("[", a)
                        if b == -1:
                            choice_txt = line[a+1:]
                        else:
                            choice_txt = line[a+1:b]
                        tmp = helper.apply_string(choice_txt, "Choices")
                        if helper.str_modified:
                            tmp = line[:a+1] + tmp
                            if b != -1:
                                tmp += line[b:]
                            lines[i] = tmp
                    elif ls.startswith("[iscript]"):
                        i += 1
                        start = i
                        while not lines[i].strip().startswith("[endscript]"):
                            i += 1
                        if "Javascript" in self.owner.plugins:
                            tjs_script = "\r\n".join(lines[start:i])
                            _, changed = self.owner.plugins["Javascript"]._parse_strings(tjs_script, helper)
                            if tjs_script != changed:
                                changed = changed.splitlines()
                                for j in range(start, i):
                                    lines[j] = changed[j-start]
                case _:
                    tmp = helper.apply_string(line, "")
                    if helper.str_modified:
                        lines[i] = tmp
            i += 1
        if helper.modified:
            combined : str = "\r\n".join(lines)
            try:
                return combined.encode(encoding), True
            except Exception as e:
                se : str = str(e)
                if "codec can't encode character" in se:
                    try:
                        pos : int = int(se.split("in position ")[1].split(":")[0])
                        raise Exception(
                            "Invalid character for encoding '{}'. Part: '{}'".format(
                                encoding,
                                combined[max(0, pos - 10):pos + 10]
                            )
                        ) from e
                    except:
                        raise e
                else:
                    raise e
        else:
            return content, False

    def write_tjs(self : KiriKiri, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        try:
            script = content.decode(self.settings["kirikiri_default_encoding"])
            encoding = self.settings["kirikiri_default_encoding"]
        except:
            script = self.decode(content)
            encoding = self.FILE_ENCODINGS[self._enc_cur_]
        if "Javascript" in self.owner.plugins:
            helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
            _, data = self.owner.plugins["Javascript"]._parse_strings(script, helper)
            if helper.modified:
                return data.encode(encoding), True
        return content, False