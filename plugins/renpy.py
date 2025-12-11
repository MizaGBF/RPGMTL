from __future__ import annotations
from . import Plugin, WalkHelper

class Renpy(Plugin):
    def __init__(self : Renpy) -> None:
        super().__init__()
        self.name : str = "Renpy"
        self.description : str = " v1.0\nHandle RPY files"
        self.related_tool_plugins : list[str] = [self.name]

    def match(self : Renpy, file_path : str, is_for_action : bool) -> bool:
        return file_path.endswith(".rpy")

    def read(self : Renpy, file_path : str, content : bytes) -> list[list[str]]:
        return self._read_walk(self.decode(content))

    def write(self : Renpy, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
        data = self._write_walk(self.decode(content), helper)
        if helper.modified:
            return self.encode(data), True
        else:
            return content, False

    # Standard Renpy
    def _read_walk(self : Renpy, content : str) -> list[list[str]]:
        return self._parse_strings(content, None)[0]

    def _write_walk(self : Renpy, content : str, helper : WalkHelper) -> str:
        return self._parse_strings(content, helper)[1]

    # Detect strings in the given Renpy text
    # If helper is not None, it will also replace the strings with translations
    # The returned value is a tuple, containing the list of group strings and the (modified or not) Renpy text
    def _parse_strings(self : Renpy, script : str, helper : WalkHelper|None) -> tuple[list[list[str]], str]:
        if helper is None:
            entry_offset = 0
        else:
            entry_offset = helper.group
        entries : list[list[str]] = []
        i = 0
        group = [""]
        string_table : list[tuple] = []
        scrlen : int = len(script)
        is_text_string : bool = True
        ctx : str|None = None
        while i < scrlen:
            c = script[i]
            if c == '#':
                # comment
                i = script.find("\n", i)
                if i == -1:
                    break
                continue
            elif c == '"':
                err : bool = False
                start = i + 1
                while True:
                    i += 1
                    q : int = script.find('"', i)
                    if q == -1:
                        err = True
                        break
                    elif script[q-1] == "\\" and script[q-2] != "\\":
                        i = q
                    else:
                        i = q + 1
                        break
                if not err and ctx not in {"music", "Solid", "color", "who_font", "fit"}:
                    literal = script[start:q]
                    string_table.append((start, q, len(entries), len(group), '"')) # position in file, position in entries, quote
                    if ctx is not None:
                        if is_text_string:
                            group[0] = "Text: " + ctx
                        else:
                            group[0] = "Code: " + ctx
                    group.append(literal.replace('\\"', '"'))
                    entries.append(group)
                    group = [""]
            elif c in {'\r', '\n'}:
                ctx = None
                is_text_string = True
                i += 1
            elif c in {' ', ':', '(', ')', '='}:
                i += 1
            else:
                start = i
                i += 1
                while script[i] not in {' ', ':', '(', ')', '=', '\r', '\n', '"'}:
                    i += 1
                if ctx is not None:
                    is_text_string = False
                ctx = script[start:i]
        if helper is not None: # write mode
            for i in range(len(string_table)-1, -1, -1):
                st = string_table[i]
                tmp : str = helper.apply_string(entries[st[2]][st[3]], entries[st[2]][0], loc=(st[2]+entry_offset, st[3]))
                if tmp != entries[st[2]][st[3]]:
                    script = script[:st[0]] + tmp.replace(st[4], '\\'+st[4]) + script[st[1]:]
        return entries, script