from __future__ import annotations
from . import Plugin, GloIndex, LocIndex, IntBool
from typing import Any
import textwrap

class GeneralActions(Plugin):
    def __init__(self : GeneralActions) -> None:
        super().__init__()
        self.name : str = "General Actions"
        self.description : str = "v1.2\nAdd specific file actions on all files and tools."
        self.related_tool_plugins : list[str] = [self.name]

    def get_setting_infos(self : GeneralActions) -> dict[str, list]:
        return {
            "char_limit_count": ["Character Limit (0 or less means None)", "num", 0, None],
            "char_limit_rpgmaker": ["Only check character limit of RPG Maker Text commands ", "bool", True, None],
        }

    def get_action_infos(self : GeneralActions) -> dict[str, list]:
        return {
            "char_limit_check": ["assets/plugins/char_limit_check.png", "Check the Character Limit", self.check_limit],
            "clear_modified_flag": ["assets/images/update.png", "Clear the Modified String indicators", self.clear_modified],
        }

    def get_tool_infos(self : GeneralActions) -> dict[str, list]:
        return {
            "general_clear_all_modified": [
                "assets/images/update.png", "Clear All Modified flags", self.clear_all, {"type":self.SIMPLE_TOOL}
            ],
            "general_text_wrap": [
                "assets/images/text_wrap.png", "Generic Text wrap", self.tool_text_wrap,
                {
                    "type":self.COMPLEX_TOOL,
                    "params":{
                        "_t_0000":["This Text Wrap can be DESTRUCTIVE. It's recommended to backup strings.bak-1.json after.", "display", None, None],
                        "_t_char_limit":["Character Limit", "num", 60, None],
                        "_t_space":["Fill with spaces instead of using a newline:", "bool", False, None],
                        "_t_file_ext":["Only on files ending with (Separate by ,)(Optional):", "str", "", None],
                        "_t_0001":["You can ignore the start of a string:", "display", None, None],
                        "_t_start":["Starting with (Optional):", "str", "", None],
                        "_t_end":["and ending with:", "str", "", None],
                    },
                    "help":"Tool to automatically wrap texts."
                }
            ],
            "general_special_character": [
                "assets/images/text_wrap.png", "Special Character Remover", self.tool_special_char,
                {
                    "type":self.COMPLEX_TOOL,
                    "params":{
                        "_t_0000":["This tool can be DESTRUCTIVE. It's recommended to backup strings.bak-1.json after.", "display", None, None],
                        "_t_0001":["Check what you want to replace:", "display", None, None],
                        "_t_dash":["– — − ‑ by -", "bool", True, None],
                        "_t_single_quote":["‘ ’ by '", "bool", True, None],
                        "_t_single_quote2":["『 』 by '", "bool", False, None],
                        "_t_double_quote":["“ ” « » by \"", "bool", True, None],
                        "_t_double_quote2":["「 」 by \"", "bool", False, None],
                        "_t_dot":["· 。 by .", "bool", True, None],
                        "_t_triple_dot":["… by ...", "bool", True, None],
                        "_t_file_ext":["Only on files ending with (Separate by ,)(Optional):", "str", "", None],
                    },
                    "help":"Tool to automatically replace specific special characters."
                }
            ],
        }

    def match(self : GeneralActions, file_path : str, is_for_action : bool) -> bool:
        return is_for_action

    def tool_text_wrap(self : GeneralActions, name : str, params : dict[str, Any]) -> str:
        try:
            limit : int = int(params["_t_char_limit"])
            if limit < 1:
                raise Exception()
        except:
            return "Invalid character limit, it must be a positive integer."
        try:
            extensions : tuple[str] = tuple(params["_t_file_ext"].split(","))
        except:
            return "Failed to parse file ending setting."
        try:
            self.owner.save() # save first!
            self.owner.backup_strings_file(name) # backup strings.json
            self.owner.load_strings(name)
            seen : set[str] = set() # used to track which strings we tested
            count : int = 0
            for file in self.owner.strings[name]["files"]:
                if len(extensions) > 0 and not file.endswith(extensions):
                    continue
                
                for i, group in enumerate(self.owner.strings[name]["files"][file]):
                    for j in range(1, len(group)):
                        sid : str = self.owner.strings[name]["files"][file][i][j][LocIndex.ID]
                        if self.owner.strings[name]["strings"][sid][GloIndex.TL] is not None:
                            if sid not in seen:
                                seen.add(sid)
                                s, b = self._tool_text_wrap_sub(
                                    limit,
                                    self.owner.strings[name]["strings"][sid][GloIndex.TL],
                                    params["_t_start"],
                                    params["_t_end"],
                                    params["_t_space"]
                                )
                                if b:
                                    self.owner.modified[name] = True
                                    self.owner.strings[name]["strings"][sid][GloIndex.TL] = s
                                    count += 1
                        
                        if self.owner.strings[name]["files"][file][i][j][LocIndex.TL] is not None:
                            s, b = self._tool_text_wrap_sub(
                                limit,
                                self.owner.strings[name]["strings"][sid][LocIndex.TL],
                                params["_t_start"],
                                params["_t_end"],
                                params["_t_space"]
                            )
                            if b:
                                self.owner.modified[name] = True
                                self.owner.strings[name]["files"][file][i][j][LocIndex.TL] = s
                                count += 1
            if count == 0:
                return "No strings have been modified"
            else:
                return str(count) + " strings have been wrapped"
        except Exception as e:
            self.owner.log.error("[JSON] Tool 'tool_text_wrap' failed with error:\n" + self.owner.trbk(e))
            return "An unexpected error occured"

    def _tool_text_wrap_sub(
        self : GeneralActions,
        limit : int,
        string : str,
        start_delim : str,
        end_delim : str,
        use_space : bool
    ) -> tuple[str, bool]:
        start : str = ""
        old : str = string
        if end_delim != "":
            if start_delim == "" or string.startswith(start_delim):
                split = string.split(end_delim, 1)
                if len(split) == 2:
                    start, string = split
                    start += end_delim
        if len(string) <= limit:
            return "", False
        p : list[str] = [
            s
            for s in string.replace("\n", " ").split(" ")
            if s != ""
        ]
        p = textwrap.wrap(" ".join(p), width=limit, break_on_hyphens=False)
        if use_space:
            for i in range(len(p) - 1):
                p[i] = p[i].ljust(limit)
            string = start + "".join(p)
        else:
            string = start + "\n".join(p)
        return string, string != old

    def tool_special_char(self : GeneralActions, name : str, params : dict[str, Any]) -> str:
        checks : dict[str, Any] = {
            "_t_dash" : (("–", "—", "−", "‑"), "-"),
            "_t_single_quote" : (("‘", "’"), "'"),
            "_t_single_quote2" : (("『", "』"), "'"),
            "_t_double_quote" : (("“", "”", "«", "»"), "\""),
            "_t_double_quote2" : (("「", "」"), "\""),
            "_t_dot" : (("·", "。"), "-"),
            "_t_triple_dot" : (("…"), "..."),
        }
        try:
            extensions : tuple[str] = tuple(params["_t_file_ext"].split(","))
        except:
            return "Failed to parse file ending setting."
        try:
            for k in list(checks.keys()):
                if params.get(k, False) == False:
                    checks.pop(k, None)
            if len(list(checks.keys())) == 0:
                return "Nothing has been selected"
            self.owner.save() # save first!
            self.owner.backup_strings_file(name) # backup strings.json
            self.owner.load_strings(name)
            seen : set[str] = set() # used to track which strings we tested
            count : int = 0
            for file in self.owner.strings[name]["files"]:
                if len(extensions) > 0 and not file.endswith(extensions):
                    continue
                for i, group in enumerate(self.owner.strings[name]["files"][file]):
                    for j in range(1, len(group)):
                        sid : str = self.owner.strings[name]["files"][file][i][j][LocIndex.ID]
                        if self.owner.strings[name]["strings"][sid][GloIndex.TL] is not None:
                            if sid not in seen:
                                seen.add(sid)
                                s, b = self._tool_special_char_parser(
                                    self.owner.strings[name]["strings"][sid][GloIndex.TL],
                                    checks
                                )
                                if b:
                                    self.owner.modified[name] = True
                                    self.owner.strings[name]["strings"][sid][GloIndex.TL] = s
                                    count += 1
                        
                        if self.owner.strings[name]["files"][file][i][j][LocIndex.TL] is not None:
                            s, b = self._tool_special_char_parser(
                                self.owner.strings[name]["strings"][sid][LocIndex.TL],
                                checks
                            )
                            if b:
                                self.owner.modified[name] = True
                                self.owner.strings[name]["files"][file][i][j][LocIndex.TL] = s
                                count += 1
            if count == 0:
                return "No strings have been modified"
            else:
                return str(count) + " strings have been modified"
        except Exception as e:
            self.owner.log.error("[JSON] Tool 'tool_special_char' failed with error:\n" + self.owner.trbk(e))
            return "An unexpected error occured"

    def _tool_special_char_parser(self : GeneralActions, s : str, checks : dict[str, Any]) -> tuple[str, bool]:
        m : str = s
        for k, (chars, replacement) in checks.items():
            for c in chars:
                m = m.replace(c, replacement)
        return m, m != s

    def check_limit(self : GeneralActions, name : str, file_path : str, settings : dict[str, Any] = {}) -> str:
        try:
            limit : int = int(settings.get("char_limit_count", 0))
            rpgonly : bool = settings.get("char_limit_rpgmaker", True)
            if limit <= 0:
                return "Please set a positive limit in this plugin settings"
            count : int = 0
            for g, group in enumerate(self.owner.strings[name]["files"][file_path]):
                if (rpgonly and group[0] == "Command: Show Text") or not rpgonly:
                    for i in range(1, len(group)):
                        lc = group[i]
                        gl = self.owner.strings[name]["strings"][lc[LocIndex.ID]]
                        if lc[LocIndex.LOCAL] and lc[LocIndex.TL] is not None:
                            s = lc[LocIndex.TL]
                        elif gl[1] is not None:
                            s = gl[GloIndex.TL]
                        else:
                            continue
                        if max([len(line) for line in s.split('\n')]) > limit:
                            count += 1
                            self.owner.strings[name]["files"][file_path][g][i][LocIndex.MODIFIED] = IntBool.TRUE
                            self.owner.modified[name] = True
            if count > 0:
                return "{} strings are over the limit and have been marked".format(count)
            else:
                return "No strings are over the limit"
        except Exception as e:
            self.owner.log.error("[General Actions] Action 'check_limit' failed with error:\n" + self.owner.trbk(e))
            return "An error occured."

    def clear_modified(self : GeneralActions, name : str, file_path : str, settings : dict[str, Any] = {}) -> str:
        try:
            limit : int = int(settings.get("char_limit_count", 0))
            if limit <= 0:
                return "Please set a positive limit in this plugin settings"
            for g, group in enumerate(self.owner.strings[name]["files"][file_path]):
                for i in range(1, len(group)):
                    if self.owner.strings[name]["files"][file_path][g][i][LocIndex.MODIFIED]:
                        self.owner.strings[name]["files"][file_path][g][i][LocIndex.MODIFIED] = IntBool.FALSE
                        self.owner.modified[name] = True
            return "Modified Flags have been cleared."
        except Exception as e:
            self.owner.log.error("[General Actions] Action 'clear_modified' failed with error:\n" + self.owner.trbk(e))
            return "An error occured."

    def clear_all(self : GeneralActions, name : str, params : dict[str, Any]) -> str:
        try:
            self.owner.load_strings(name)
            for file in self.owner.strings[name]["files"]:
                for i, group in enumerate(self.owner.strings[name]["files"][file]):
                    for j in range(1, len(group)):
                        self.owner.strings[name]["files"][file][i][j][LocIndex.MODIFIED] = IntBool.FALSE
            self.owner.modified[name] = True
            return "Modified Flags have been cleared."
        except Exception as e:
            self.owner.log.error("[General Actions] Action 'clear_all' failed with error:\n" + self.owner.trbk(e))
            return "An error occured."