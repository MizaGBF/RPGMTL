from __future__ import annotations
from . import Plugin, WalkHelper

class Ruby(Plugin):
    def __init__(self : Ruby) -> None:
        super().__init__()
        self.name : str = "Ruby"
        self.description : str = " v1.5\nHandle Ruby files"
        self.related_tool_plugins : list[str] = [self.name]

    def match(self : Ruby, file_path : str, is_for_action : bool) -> bool:
        return file_path.endswith(".rb")

    def read(self : Ruby, file_path : str, content : bytes) -> list[list[str]]:
        data = self.decode(content)
        return self._read_walk(data)

    def write(self : Ruby, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        data = self.decode(content)
        helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
        data = self._write_walk(data, helper)
        if helper.modified:
            return self.encode(data), True
        else:
            return content, False

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
        funcs = ["", ""]
        func_pos = [None, None]
        group = [""]
        string_table : list[tuple] = []
        scriptlen : int = len(script)
        while i < scriptlen:
            c : str = script[i]
            if c == '#': # Single Line Comment
                i = script.find('\n', i + 1)
                if i == -1:
                    break
                i += 1
                continue
            elif c == "\n" and i + 6 < scriptlen and script.startswith("\n=begin", i): # Multi Line Comment
                i = script.find("\n=end", i + 6)
                if i == -1:
                    break
                i += 4
                continue
            elif c == '"' and (i == 0 or script[i-1] != '$'):
                start = i + 1
                end = start
                while True:
                    end = script.find('"', end)
                    if end == -1:
                        i = len(script)
                        break
                    else:
                        prev : str = script[end-1]
                        if prev != "\\" or (prev == "\\" and script[end-2] == "\\"):
                            if start != end:
                                literal = script[start:end]
                                string_table.append((start, end, len(entries), len(group), '"'))
                                group.append(literal.replace('\\"', '"'))
                            i = end + 1
                            break
                        else:
                            end += 1
            else:
                if c.isalnum():
                    # Function name detection
                    if func_pos[0] is None:
                        func_pos[0] = i
                    func_pos[1] = i+1
                else:
                    # Function name detection
                    if func_pos[0] is not None:
                        funcs[-1] = script[func_pos[0]:func_pos[1]]
                        func_pos[0] = None
                    if funcs[-1] != "" and funcs[-2] == "def":
                        if len(group) > 1:
                            entries.append(group)
                            group = [""]
                        group[0] = funcs[-1] + "()"
                        funcs[0], funcs[1] = funcs[1], ""
                    else:
                        funcs[0], funcs[1] = funcs[1], ""
                i += 1
        if len(group) > 1:
            entries.append(group)
        if helper is not None: # write mode
            for i in range(len(string_table)-1, -1, -1):
                st = string_table[i]
                tmp : str = helper.apply_string(entries[st[2]][st[3]], entries[st[2]][0], loc=(st[2]+entry_offset, st[3]))
                if tmp != entries[st[2]][st[3]]:
                    script = script[:st[0]] + tmp.replace(st[4], '\\'+st[4]) + script[st[1]:]
            if len(string_table) > 0:
                helper.group = string_table[-1][2]+entry_offset
                helper.index = string_table[-1][3]
                helper._goNext()
        return entries, script