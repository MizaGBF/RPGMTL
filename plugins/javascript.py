from __future__ import annotations
from . import Plugin, WalkHelper
import json

class Javascript(Plugin):
    def __init__(self : Javascript) -> None:
        super().__init__()
        self.name : str = "Javascript"
        self.description : str = " v1.5\nHandle Javascript files, including the plugins.js file from RPG Maker MV/MZ"

    def match(self : Javascript, file_path : str, is_for_action : bool) -> bool:
        return file_path.endswith(".js")

    def read(self : Javascript, file_path : str, content : bytes) -> list[list[str]]:
        data = self.decode(content)
        if file_path.endswith('js/plugins.js'):
            return self._read_walk_plugins(data)
        else:
            return self._read_walk(data)

    def write(self : Javascript, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        data = self.decode(content)
        modified : bool = False
        try:
            if not file_path.endswith('js/plugins.js'):
                raise Exception()
            data, modified = self._write_walk_plugins(name, file_path, self.owner.strings[name], data)
        except:
            helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
            data = self._write_walk(data, helper)
            modified = helper.modified
        if modified:
            return self.encode(data), True
        else:
            return content, False

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
        jslen : int = len(js)
        c : str = ""
        while i < jslen:
            c = js[i]
            if c == '/':
                # Handle comments.
                if i + 1 < jslen:
                    if js[i+1] == '/':
                        # single-line comment: skip until newline
                        i = js.find('\n', i+2)
                        if i == -1:
                            break
                        i += 1
                        continue
                    elif js[i+1] == '*':
                        # multi-line comment: skip until closing */
                        i = js.find('*/', i+2)
                        if i == -1:
                            break
                        i += 2
                        continue
            if c in ("'", '"', '`') or (c == '/' and regex_possible):
                # Extract a string literal.
                i += 1
                quote = c
                start = i
                end = start
                while True:
                    end = js.find(quote, end)
                    if end == -1:
                        i = jslen
                        break
                    else:
                        prev : str = js[end-1]
                        if prev != "\\" or (prev == "\\" and js[end-2] == "\\"):
                            if start != end:
                                literal = js[start:end]
                                string_table.append((start, end, len(entries), len(group), quote)) # position in file, position in entries, quote
                                group.append(literal.replace('\\'+quote, quote))
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
            plugins = self._parse_plugins(js)
            entries : list[list[str]] = []
            for i in range(len(plugins)):
                p = plugins[i]
                if p is None:
                    continue
                pluginname : str = self.owner.CHILDREN_FILE_ID + p.get("name", "")
                group : list[str] = [""]
                if 'parameters' in p:
                    for k, v in p['parameters'].items():
                        match v:
                            case str():
                                if v != "" and not v.isdigit():
                                    group.append(v)
                            case list():
                                for j in range(len(v)):
                                    if isinstance(v[j], str) and v[j] != "" and not v[j].isdigit():
                                        group.append(v[j])
                            case dict():
                                for elk, el in v.items():
                                    if isinstance(el, str) and el != "" and not el.isdigit():
                                        group.append(el)
                if len(group) > 1:
                    entries.append([pluginname])
                    entries.append(group)
            return entries
        except Exception as e:
            if str(e) == "Not the expected RPGMK plugins.js file":
                self.owner.log.warning("[Javascript] Failed to parse plugins.js, falling back to normal parsing...")
                return self._read_walk(js)
            else:
                raise e

    def _write_walk_plugins(self : Javascript, name : str, file_path : str, strings : dict, js : str) -> tuple[str, bool]:
        plugins = self._parse_plugins(js)
        modified : bool = False
        for i in range(len(plugins)):
            p = plugins[i]
            if p is None:
                continue
            pluginname : str = file_path + "/" + p.get("name", "")
            if pluginname in strings["files"] and not self.owner.projects[name]["files"][pluginname]["ignored"]:
                helper : WalkHelper = WalkHelper(pluginname, strings)
                group : list[str] = [""]
                if 'parameters' in p:
                    for k, v in p['parameters'].items():
                        match v:
                            case str():
                                if v != "" and not v.isdigit():
                                    plugins[i]['parameters'][k] = helper.apply_string(plugins[i]['parameters'][k], group[0])
                                    modified = True
                            case list():
                                for j in range(len(v)):
                                    if isinstance(v[j], str) and v[j] != "" and not v[j].isdigit():
                                        plugins[i]['parameters'][k][j] = helper.apply_string(plugins[i]['parameters'][k][j], group[0])
                                        modified = True
                            case dict():
                                for elk, el in v.items():
                                    if isinstance(el, str) and el != "" and not el.isdigit():
                                        plugins[i]['parameters'][k][elk] = helper.apply_string(plugins[i]['parameters'][k][elk], group[0])
                                        modified = True
        if modified:
            start = js.find('plugins =') + len('plugins =')
            end = len(js) - 1
            content = "\n[\n"
            for i in range(len(plugins)):
                content += json.dumps(plugins[i], ensure_ascii=False, separators=(',', ':'))
                if i != len(plugins)-1:
                    content += ",\n"
            content += "\n]"
            js = js[:start] + content + js[end:]
            return js, True
        else:
            return js, False

    # read the content of standard RPGMV/MZ plugins.js file
    def _parse_plugins(self : Javascript, js : str) -> dict:
        start = js.find('plugins =') + len('plugins =')
        if start == -1:
            raise Exception("Not the expected RPGMK plugins.js file")
        end = len(js) - 1
        while js[end] != ';':
            end -= 1
            if end <= start:
                raise Exception("Not the expected RPGMK plugins.js file")
        return json.loads(js[start:end])