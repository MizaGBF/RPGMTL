from __future__ import annotations
from . import Plugin, WalkHelper

class INI(Plugin):
    def __init__(self : INI) -> None:
        super().__init__()
        self.name : str = "INI"
        self.description : str = " v1.2\nHandle INI files"

    def file_extension(self : INI) -> list[str]:
        return ["ini"]

    def match(self : INI, file_path : str, is_for_action : bool) -> bool:
        return file_path.endswith(".ini")

    def load(self : INI, content : bytes) -> list[str|list[str]]:
        lines = self.decode(content).splitlines()
        result : list[str|list[str]] = []
        for line in lines:
            if "=" in line:
                result.append(line.split("=", 1))
            else:
                result.append(line)
        return result

    def dump(self : INI, lines : list[str|list[str]]) -> bytes:
        for i in range(len(lines)):
            if isinstance(lines[i], list):
                lines[i] = "=".join(lines[i])
        return self.encode("\n".join(lines))

    def read(self : INI, file_path : str, content : bytes) -> list[list[str]]:
        lines = self.load(content)
        entries : list[list[str]] = []
        for i in range(len(lines)):
            if isinstance(lines[i], list) and lines[i][1] != "":
                entries.append(lines[i])
        return entries

    def write(self : INI, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
        lines = self.load(content)
        for i in range(len(lines)):
            if isinstance(lines[i], list) and lines[i][1] != "":
                lines[i][1] = helper.apply_string(lines[i][1], lines[i][0])
        if helper.modified:
            return self.dump(lines), True
        else:
            return content, False