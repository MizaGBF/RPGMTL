from __future__ import annotations
from . import Plugin, WalkHelper

class Ruby(Plugin):
    def __init__(self : Ruby) -> None:
        super().__init__()
        self.name : str = "Ruby"
        self.description : str = " v1.1\nHandle Ruby files"

    def file_extension(self : Ruby) -> list[str]:
        return ["rb"]

    def match(self : Ruby, file_path : str, is_for_action : bool) -> bool:
        return file_path.endswith(".rb")

    def read(self : Ruby, file_path : str, content : bytes) -> list[list[str]]:
        data = self.decode(content)
        return self._read_walk(data)

    def write(self : Ruby, file_path : str, content : bytes, strings : dict) -> tuple[bytes, bool]:
        data = self.decode(content)
        helper : WalkHelper = WalkHelper(file_path, strings)
        data = self._write_walk(data, helper)
        return self.encode(data), helper.modified

    # Standard ruby
    def _read_walk(self : Ruby, js : str) -> list[list[str]]:
        return self._parse_strings(js, None)[0]

    def _write_walk(self : Ruby, js : str, helper : WalkHelper) -> str:
        return self._parse_strings(js, helper)[1]

    # Detect strings in the given ruby text
    # If helper is not None, it will also replace the strings with translations
    # The returned value is a tuple, containing the list of group strings and the (modified or not) ruby text
    # Code inspired/reused from the javascript plugin
    def _parse_strings(self : Ruby, script : str, helper : WalkHelper|None, entry_offset : int|None = None) -> tuple[list[list[str]], str]:
        if entry_offset is None:
            if helper is None:
                entry_offset = 0
            else:
                entry_offset = helper.group
        entries = []
        i = 0
        group = [""]
        string_table : list[tuple] = []
        c : str = ""
        while i < len(script):
            prev : str = c
            c = script[i]
            if c == '#': # Single Line Comment
                i += 1
                while i < len(script) and script[i] != "\n":
                    i += 1
                prev = None
                continue
            elif c == "\n" and i + 6 < len(script) and script[i:i+7] == "\n=begin": # Multi Line Comment
                i += 6
                while i < len(script) and script[i] != "d" and script[i-4:i+1] != "\n=end":
                    i += 1
                prev = None
                continue
            if c == '"' and prev != '$':
                i += 1
                start = i
                while i < len(script):
                    c = script[i]
                    if c == '\\':  # skip escaped char
                        i += 2
                        continue
                    if c == '"':
                        literal = script[start:i]
                        if literal != "":
                            string_table.append((start, i, len(entries), len(group), '"')) # position in file, position in entries, quote
                            group.append(literal.replace('\\"', '"'))
                        i += 1
                        break
                    i += 1
            else:
                i += 1
        if len(group) > 1:
            entries.append(group)
        if helper is not None: # write mode
            for i in range(len(string_table)-1, -1, -1):
                st = string_table[i]
                tmp : str = helper.apply_string(entries[st[2]][st[3]], loc=(st[2]+entry_offset, st[3]))
                if tmp != entries[st[2]][st[3]]:
                    script = script[:st[0]] + tmp.replace(st[4], '\\'+st[4]) + script[st[1]:]
            if len(string_table) > 0:
                helper.group = string_table[-1][2]+entry_offset
                helper.index = string_table[-1][3]
                helper._goNext()
        return entries, script