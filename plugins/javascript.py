from __future__ import annotations
from . import Plugin, WalkHelper
import json

class Javascript(Plugin):
    def __init__(self : Javascript) -> None:
        super().__init__()
        self.name : str = "Javascript"
        self.description : str = " v1.0\nHandle Javascript files, including the plugins.js file from RPG Maker MV/MZ"

    def file_extension(self : Javascript) -> list[str]:
        return ["js"]

    def match(self : Javascript, file_path : str) -> bool:
        return file_path.endswith(".js")

    def read(self : Javascript, file_path : str, content : bytes) -> list[list[str]]:
        data = self.decode(content)
        if file_path.endswith('js/plugins.js'):
            return self._read_walk_plugins(data)
        else:
            return self._read_walk(data)

    def write(self : Javascript, file_path : str, content : bytes, strings : dict) -> tuple[bytes, bool]:
        data = self.decode(content)
        helper : WalkHelper = WalkHelper(file_path, strings)
        if file_path.endswith('js/plugins.js'):
            data = self._write_walk_plugins(data, helper)
        else:
            data = self._write_walk(data, helper)
        return self.encode(data), helper.modified

    # Standard javascript
    def _read_walk(self : Javascript, js : str) -> list[list[str]]:
        return self._parse_strings(js, None)[0]

    def _write_walk(self : Javascript, js : str, helper : WalkHelper) -> str:
        return self._parse_strings(js, helper)[1]

    # Detect strings in the given javascript text
    # If helper is not None, it will also replace the strings with translations
    # The returned value is a tuple, containing the list of group strings and the (modified or not) javascript text
    def _parse_strings(self : Javascript, js : str, helper : WalkHelper|None) -> tuple[list[list[str]], str]:
        entries = []
        i = 0
        funcs = ["", ""]
        func_pos = [None, None]
        group = [""]
        string_table : list[tuple] = []
        regex_possible : bool = False
        while i < len(js):
            c = js[i]
            if c == '/':
                # Handle comments.
                if i + 1 < len(js):
                    if js[i+1] == '/':
                        # single-line comment: skip until newline
                        i += 2
                        while i < len(js) and js[i] != '\n':
                            i += 1
                        continue
                    elif js[i+1] == '*':
                        # multi-line comment: skip until closing */
                        i += 2
                        while i + 1 < len(js) and not (js[i] == '*' and js[i+1] == '/'):
                            i += 1
                        i += 2
                        continue
            if c in ("'", '"', '`') or (c == '/' and regex_possible):
                # Extract a string literal.
                i += 1
                quote = c
                start = i
                while i < len(js):
                    c = js[i]
                    if c == '\\':  # skip escaped char
                        i += 2
                        continue
                    if c == quote:
                        literal = js[start:i]
                        if literal != "":
                            string_table.append((start, i, len(entries), len(group), quote)) # position in file, position in entries, quote
                            group.append(literal.replace('\\'+quote, quote))
                        i += 1
                        break
                    i += 1
            else:
                if c.isalnum():
                    # Function name detection
                    if func_pos[0] is None:
                        func_pos[0] = i
                    func_pos[1] = i+1
                    # Regex allowed detection
                    regex_possible = False
                else:
                    # Function name detection
                    if func_pos[0] is not None:
                        funcs[-1] = js[func_pos[0]:func_pos[1]]
                        func_pos[0] = None
                    shift_array : bool = False
                    if funcs[-1] != "":
                        if funcs[-1] == "function" and funcs[-2] != "":
                            if len(group) > 1:
                                entries.append(group)
                                group = [""]
                            group[0] = funcs[-2] + "()"
                        elif funcs[-2] == "function":
                            if len(group) > 1:
                                entries.append(group)
                                group = [""]
                            group[0] = funcs[-1] + "()"
                        shift_array = True
                    elif c in ("(", ")"):
                        shift_array = True
                    # Regex allowed detection
                    if c in (" ", "\t", "\n"):
                        regex_possible = (funcs[-1] == "return" or regex_possible)
                    elif c in ("=", "(", ","):
                        regex_possible = True
                    else:
                        regex_possible = False
                    # Shift funcs array
                    if shift_array:
                        funcs[0] = funcs[1]
                        funcs[1] = ""
                i += 1
        if len(group) > 1:
            entries.append(group)
        if helper is not None: # write mode
            for i in range(len(string_table)-1, -1, -1):
                st = string_table[i]
                tmp : str = helper.apply_string(entries[st[2]][st[3]], entries[st[2]][0], loc=(st[2], st[3]))
                if tmp != entries[st[2]][st[3]]:
                    js = js[:st[0]] + tmp.replace(st[4], '\\'+st[4]) + js[st[1]:]
        return entries, js

    # RPGMK MZ/MV plugins.js
    def _read_walk_plugins(self : Javascript, js : str) -> list[list[str]]:
        try:
            return self._parse_plugins(js, None)[0]
        except Exception as e:
            if str(e) == "Not the expected RPGMK plugins.js file":
                self.owner.log.warning("[Javascript] Failed to parse plugins.js, falling back to normal parsing...")
                return self._read_walk(js)
            else:
                raise e

    def _write_walk_plugins(self : Javascript, js : str, helper : WalkHelper) -> str:
        try:
            return self._parse_plugins(js, helper)[1]
        except Exception as e:
            if str(e) == "Not the expected RPGMK plugins.js file":
                self.owner.log.warning("[Javascript] Failed to parse plugins.js, falling back to normal parsing...")
                return self._write_walk(js, helper)
            else:
                raise e

    # Works the same as _parse_strings
    # entries isn't populated in write mode (i.e. when helper is not None)
    def _parse_plugins(self : Javascript, js : str, helper : WalkHelper|None) -> tuple[list[list[str]], str]:
        entries = []
        start = js.find('plugins =') + len('plugins =')
        if start == -1:
            raise Exception("Not the expected RPGMK plugins.js file")
        end = len(js) - 1
        while js[end] != ';':
            end -= 1
            if end <= start:
                raise Exception("Not the expected RPGMK plugins.js file")
        plugins = json.loads(js[start:end])
        for i in range(len(plugins)):
            p = plugins[i]
            if p is None:
                continue
            group = [p.get("name", "")]
            if 'parameters' in p:
                for k, v in p['parameters'].items():
                    match v:
                        case str():
                            if v != "" and not v.isdigit():
                                if helper is not None:
                                    plugins[i]['parameters'][k] = helper.apply_string(plugins[i]['parameters'][k], group[0])
                                else:
                                    group.append(v)
                        case list():
                            for j in range(len(v)):
                                if isinstance(v[j], str) and v[j] != "" and not v[j].isdigit():
                                    if helper is not None:
                                        plugins[i]['parameters'][k][j] = helper.apply_string(plugins[i]['parameters'][k][j], group[0])
                                    else:
                                        group.append(v[j])
                        case dict():
                            for elk, el in v.items():
                                if isinstance(el, str) and el != "" and not el.isdigit():
                                    if helper is not None:
                                        plugins[i]['parameters'][k][elk] = helper.apply_string(plugins[i]['parameters'][k][elk], group[0])
                                    else:
                                        group.append(el)
            if helper is None and len(group) > 1:
                entries.append(group)
        # write mode
        if helper is not None:
            content = "\n[\n"
            for i in range(len(plugins)):
                content += json.dumps(plugins[i], ensure_ascii=False, separators=(',', ':'))
                if i != len(plugins)-1:
                    content += ",\n"
            content += "\n]"
            js = js[:start] + content + js[end:]
        return entries, js