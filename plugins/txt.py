from __future__ import annotations
from . import Plugin, WalkHelper

class TXT(Plugin):
    def __init__(self : TXT) -> None:
        super().__init__()
        self.name : str = "TXT"
        self.description : str = " v1.0\nHandle TXT files"

    def match(self : TXT, file_path : str, is_for_action : bool) -> bool:
        lowerpath : str = file_path.lower()
        return file_path.endswith(".txt") and "readme" not in lowerpath and "read me" not in lowerpath # skip readme files

    def read(self : TXT, file_path : str, content : bytes) -> list[list[str]]:
        lines = self.decode(content).splitlines()
        entries : list[list[str]] = []
        group : list[str] = [""]
        for i in range(len(lines)):
            if lines[i] != "":
                group.append(lines[i])
            else:
                if len(group) > 1:
                    entries.append(group)
                    group = [""]
        if len(group) > 1:
            entries.append(group)
        return entries

    def write(self : TXT, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
        text : str = self.decode(content)
        lines = text.splitlines()
        end_line : str = "\r\n" if "\r\n" in text else "\n"
        for i in range(len(lines)):
            if lines[i] != "":
                lines[i] = helper.apply_string(lines[i])
        if helper.modified:
            return self.encode(end_line.join(lines)), True
        else:
            return content, False