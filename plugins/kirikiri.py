from __future__ import annotations
from . import Plugin, WalkHelper

class KiriKiri(Plugin):
    def __init__(self : KiriKiri) -> None:
        super().__init__()
        self.name : str = "KiriKiri"
        self.description : str = " v1.0\nHandle KiriKiri KAG and script files"

    def get_setting_infos(self : KiriKiri) -> dict[str, list]:
        return {
            "kirikiri_default_encoding": ["Select the default script encoding", "str", "shift_jis", ["auto"] + self.FILE_ENCODINGS]
        }

    def match(self : KiriKiri, file_path : str, is_for_action : bool) -> bool:
        return file_path.endswith(".ks") or file_path.endswith(".tjs")

    def read(self : KiriKiri, file_path : str, content : bytes) -> list[list[str]]:
        if file_path.endswith(".ks"):
            return self.read_ks(file_path, content)
        elif file_path.endswith(".tjs"):
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
                    if line.strip().startswith("[link target="):
                        if group[0] != "Choices":
                            if len(group) > 1:
                                entries.append(group)
                            group = ["Choices"]
                        group.append(line.split("]")[1].split("[")[0])
                    elif line.strip().startswith("[iscript]"):
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
        if file_path.endswith(".ks"):
            return self.write_ks(name, file_path, content)
        elif file_path.endswith(".tjs"):
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
                    if line.strip().startswith("[link target="):
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
                    elif line.strip().startswith("[iscript]"):
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
            return "\r\n".join(lines).encode(encoding), True
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