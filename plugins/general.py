from __future__ import annotations
from . import Plugin, GloIndex, LocIndex, IntBool
from typing import Any
import re
import textwrap
import unicodedata

class GeneralActions(Plugin):
    COMMA_SPLIT : re.Pattern = re.compile(r'(?<!\\),')
    def __init__(self : GeneralActions) -> None:
        super().__init__()
        self.name : str = "General Actions"
        self.description : str = "v1.4\nAdd specific file actions on all files and tools."
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
                "assets/images/text_wrap.png", "Text wrap", self.tool_text_wrap,
                {
                    "type":self.COMPLEX_TOOL,
                    "params":{
                        "_t_0000":["The Text Wrap can be DESTRUCTIVE. It's recommended to backup strings.bak-1.json after.", "display", None, None],
                        "_t_char_limit":["Character Limit per line:", "num", 55, None],
                        "_t_line_limit":["Maximum number of lines (0 or less for unlimited):", "num", 4, None],
                        "_t_spacer_1":["", "display", None, None],
                        "_t_0001":["Text Wrap Options", "display", None, None],
                        "_t_smart":["Detect punctuation for smart newline placements:", "bool", True, None],
                        "_t_smart_char":["Punctuation characters:", "str", "』”»\"」·。.…！!？?】]）)♪～~♡::、,;", None],
                        "_t_file_match":["Only apply on File Paths containing (Optional) (Example: .json):", "str", "", None],
                        "_t_group_match_desc":["Only apply for those string groups (separated by comma, support \\ escaping, case & space sensitive):", "display", None, None],
                        "_t_group_match":["Example: Command: Show Text,Command: Set Variable", "str", "Command: Show Text", None],
                        "_t_spacer_2":["", "display", None, None],
                        "_t_0002":["Text Box Name detection", "display", None, None],
                        "_t_name_detect":["Ignore the first line if it doesn't contain spaces in the Untranslated String", "bool", True, None],
                        "_t_name_group_desc":["Ignore the first line if it contains one of these strings in the Untranslated String (separated by comma, support \\ escaping, case & space sensitive):", "display", None, None],
                        "_t_additional_names":["Example: アリス,ジャン", "str", "", None],
                        "_t_name_chara":["Ignore the first line if the second of the Untranslated String starts with:", "str", "『「(", None],
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
                        "_t_dash":["– ― — − ‑ by -", "bool", True, None],
                        "_t_single_quote":["‘ ’ by '", "bool", True, None],
                        "_t_single_quote2":["『 』 by '", "bool", False, None],
                        "_t_double_quote":["“ ” « » by \"", "bool", True, None],
                        "_t_double_quote2":["「 」 by \"", "bool", False, None],
                        "_t_dot":["· 。 by .", "bool", True, None],
                        "_t_triple_dot":["… by ...", "bool", True, None],
                        "_t_exclamation":["！ by !", "bool", True, None],
                        "_t_question":["？ by ?", "bool", True, None],
                        "_t_bracket1":["【 by [", "bool", False, None],
                        "_t_bracket2":["】 by ]", "bool", False, None],
                        "_t_parenthesis1":["（ by (", "bool", False, None],
                        "_t_parenthesis2":["） by )", "bool", False, None],
                        "_t_accent":["Latin Accented Letters", "bool", False, None],
                        "_t_file_ext":["Only on files ending with (Separate by ,)(Optional):", "str", "", None],
                    },
                    "help":"Tool to automatically replace specific special characters."
                }
            ],
            "general_clear_unlinked": [
                "assets/images/trash.png", "Clear all unlinked strings", self.tool_clear_unlinked,
                {
                    "type":self.COMPLEX_TOOL,
                    "params":{
                        "_t_0000":["This tool can be DESTRUCTIVE. It's recommended to backup strings.bak-1.json after.", "display", None, None],
                        "_t_0001":["All unlinked strings will be deleted and removed.", "display", None, None],
                        "_t_0002":["The purpose is to clear garbage created by multiple batch translations at the start of a new translation project.", "display", None, None],
                        "_t_confirm":["I've read and I understand that data will be deleted.", "bool", False, None],
                    },
                    "help":"Tool to automatically clear all unlinked strings."
                }
            ],
        }

    def match(self : GeneralActions, file_path : str, is_for_action : bool) -> bool:
        return is_for_action

    def tool_text_wrap(self : GeneralActions, name : str, params : dict[str, Any]) -> str:
        try:
            char_limit : int = int(params["_t_char_limit"])
            if char_limit < 1:
                raise Exception()
        except:
            return "Invalid character limit, it must be a positive integer."
        try:
            line_limit : int = int(params["_t_line_limit"])
        except:
            return "Invalid line limit, it must an positive integer."
        be_smart : bool
        smart_punctuation : set[str] = set(params["_t_smart_char"])
        if len(smart_punctuation) == 0:
            be_smart = False
        else:
            be_smart = params["_t_smart"]
        smart_punctuation_tup : tuple[str, ...] = tuple(smart_punctuation)
        try:
            file_match : str = params["_t_file_match"]
            group_matches : list[str] = list(set(self.COMMA_SPLIT.split(params["_t_group_match"])))
            name_detect_space : bool = params["_t_name_detect"]
            additional_names : set[str] = set(self.COMMA_SPLIT.split(params["_t_additional_names"]))
            second_line_chara : tuple[str, ...] = tuple(set(list(params["_t_name_chara"])))
            # parameters preparation ends
            self.owner.save() # save first!
            self.owner.backup_strings_file(name) # backup strings.json
            self.owner.load_strings(name)
            seen : set[str] = set() # used to track which strings we tested
            count : int = 0
            for file in self.owner.strings[name]["files"]:
                if len(file_match) > 0 and file_match not in file:
                    continue
                for i, group in enumerate(self.owner.strings[name]["files"][file]):
                    # group name matching check
                    if len(group_matches) > 0:
                        is_ok : bool = False
                        for gn in group_matches:
                            if gn in group[0]:
                                is_ok = True
                                break
                        if not is_ok:
                            continue
                    for j in range(1, len(group)):
                        sid : str = self.owner.strings[name]["files"][file][i][j][LocIndex.ID]
                        original : str = self.owner.strings[name]["strings"][sid][GloIndex.ORI]
                        # local string
                        if self.owner.strings[name]["files"][file][i][j][LocIndex.LOCAL]:
                            if self.owner.strings[name]["files"][file][i][j][LocIndex.TL] is not None:
                                s : str = self.wrap_string(
                                    original,
                                    self.owner.strings[name]["files"][file][i][j][LocIndex.TL],
                                    char_limit, line_limit,
                                    be_smart, smart_punctuation, smart_punctuation_tup,
                                    name_detect_space, additional_names, second_line_chara
                                )
                                if s != self.owner.strings[name]["files"][file][i][j][LocIndex.TL]:
                                    self.owner.strings[name]["files"][file][i][j][LocIndex.TL] = s
                                    self.owner.modified[name] = True
                                    count += 1
                            
                        else:
                            # global string
                            if sid not in seen and self.owner.strings[name]["strings"][sid][GloIndex.TL] is not None:
                                seen.add(sid)
                                s : str = self.wrap_string(
                                    original,
                                    self.owner.strings[name]["strings"][sid][GloIndex.TL],
                                    char_limit, line_limit,
                                    be_smart, smart_punctuation, smart_punctuation_tup,
                                    name_detect_space, additional_names, second_line_chara
                                )
                                if s != self.owner.strings[name]["strings"][sid][GloIndex.TL]:
                                    self.owner.strings[name]["strings"][sid][GloIndex.TL] = s
                                    self.owner.modified[name] = True
                                    count += 1
            if count == 0:
                return "No strings have been modified"
            else:
                return f"{count} strings have been wrapped"
        except Exception as e:
            self.owner.log.error("[General Actions] Tool 'tool_text_wrap' failed with error:\n" + self.owner.trbk(e))
            return "An unexpected error occured"

    def wrap_string(
        self : GeneralActions,
        ori : str, tl : str,
        char_limit : int, line_limit : int,
        be_smart : bool, smart_punctuation : set[str],  smart_punctuation_tup : tuple[str, ...],
        name_detect_space : bool, additional_names : set[str], second_line_chara : tuple[str, ...]
    ) -> str:
        # check name
        has_name : bool = False
        ori_lines : list[str] = ori.split("\n")
        if name_detect_space and ori_lines[0].count(" ") == 0:
            has_name = True
        elif ori_lines[0] in additional_names:
            has_name = True
        elif len(ori_lines) > 1 and ori_lines[1].startswith(second_line_chara):
            has_name = True
        # text wrap
        ## smart wrap
        if be_smart:
            lines : list[str] = tl.split("\n")
            start : int = 1 if has_name else 0
            smart_start : int = start
            # detect proper lines
            for i in range(start, len(lines)):
                if len(lines[i]) <= char_limit:
                    smart_start = i + 1
                else:
                    break
            if smart_start >= len(lines): # no need for changes
                return tl
            # parse punctuation groups count of the original string
            punc_map : dict[int, int] = {}
            for i in range(start, len(ori_lines)):
                punc_state : bool = False
                for c in ori_lines[i]:
                    if punc_state:
                        if c not in smart_punctuation:
                            punc_state = False
                    else:
                        if c in smart_punctuation:
                            punc_map[i] = punc_map.get(i, 0) + 1
                            punc_state = True
            # break per word/punctuation
            # lines are broken per word based on spaces or punctuation
            split_lines : list[list[str]] = []
            if has_name:
                split_lines.append([lines[0]])
            for i in range(start, len(lines)):
                split_lines.append([""])
                state : bool = False
                # read line characters
                for j, c in enumerate(lines[i]):
                    if c == " ": # space
                        split_lines[i][-1] += c
                        state = False
                        split_lines[i].append("")
                    else:
                        if state: # in a punctuation group
                            if c not in smart_punctuation:
                                state = False
                                split_lines[i].append("") # add new line
                        else:
                            if c in smart_punctuation:
                                state = True
                        # append character
                        split_lines[i][-1] += c
                if len(split_lines[i]) > 1 and split_lines[i][-1] == "":
                    # remove the last line if it's empty
                    split_lines[i].pop()
            # now attempt to wrap
            # we start with the minimum of line and
            # expand more and more
            while smart_start >= start:
                cpy_lines = []
                for i, line in enumerate(split_lines):
                    cpy_lines.append(line)
                    if smart_start <= i < len(split_lines) - 1:
                        # append a space at the end of modifiable line
                        # this is to avoid situations where we have "...word" as a result
                        cpy_lines[-1][-1] += " "
                result_lines : list[list[str]]|None = self.attempt_smart_wrap(
                    cpy_lines,
                    smart_start, char_limit, line_limit,
                    punc_map,
                    smart_punctuation_tup
                )
                if result_lines is not None:
                    # assemble the text
                    for i in range(0, len(result_lines)):
                        result_lines[i] = "".join(result_lines[i])
                        if result_lines[i].endswith(" "):
                            result_lines[i] = result_lines[i][:-1]
                    return "\n".join(result_lines)
                else:
                    smart_start -= 1
        ## normal wrap
        result : str
        if has_name:
            name, text = tuple(tl.split("\n", 1))
            result = name +"\n" + "\n".join(textwrap.wrap(text, width=char_limit, break_on_hyphens=False))
        else:
            result = "\n".join(textwrap.wrap(tl, width=char_limit, break_on_hyphens=False))
        if result.count("\n") >= line_limit:
            return tl
        else:
            return result

    def attempt_smart_wrap(
        self : GeneralActions,
        lines : list[list[str]],
        start : int, char_limit : int, line_limit : int, 
        punc_map : dict[int, int],
        smart_punctuation_tup : tuple[str, ...]
    ) -> list[list[str]]|None:
        result : list[list[str]] = []
        current_line_len : int = 0
        current_punc : int = 0
        debt_punc : int = 0
        for i in range(0, len(lines)):
            if i < start:
                result.append(lines[i])
                continue
            elif i == start:
                result.append([])
            for word in lines[i]:
                expected_count : int = punc_map.get(len(result) - 1, 0)
                space_shift : int = 1 if word.endswith(" ") else 0
                # check if there is space on the line
                if current_line_len + len(word) - space_shift > char_limit:
                    if len(result[-1]) == 0 or len(result) == line_limit:
                        return None # failsafe
                    # increase debt if we're missing punctuation groups
                    if current_punc < expected_count:
                        debt_punc += expected_count - current_punc
                    current_punc = 0
                    result.append([word]) # append on new line
                    current_line_len = len(word)
                else:
                    result[-1].append(word)
                    current_line_len += len(word)
                # if word ends with punctuation
                if word.endswith(smart_punctuation_tup):
                    current_punc += 1 # increase count
                    # check if we're matching expected count and if there are space for remaining lines
                    if len(result) < line_limit and current_punc >= expected_count + debt_punc:
                        current_line_len = 0
                        debt_punc -= min(debt_punc, current_punc)
                        current_punc = 0
                        result.append([])
        if len(result[-1]) == 0: # remove final empty line if any
            result.pop()
        return result

    def tool_special_char(self : GeneralActions, name : str, params : dict[str, Any]) -> str:
        checks : dict[str, Any] = {
            "_t_dash" : (("–", "―", "—", "−", "‑"), "-"),
            "_t_single_quote" : (("‘", "’"), "'"),
            "_t_single_quote2" : (("『", "』"), "'"),
            "_t_double_quote" : (("“", "”", "«", "»"), "\""),
            "_t_double_quote2" : (("「", "」"), "\""),
            "_t_dot" : (("·", "。"), "-"),
            "_t_triple_dot" : (("…"), "..."),
            "_t_exclamation" : (("！"), "!"),
            "_t_question" : (("？"), "?"),
            "_t_bracket1" : (("【"), "["),
            "_t_bracket2" : (("】"), "]"),
            "_t_parenthesis1": (("（"), "("),
            "_t_parenthesis2": (("）"), ")"),
            "_t_accent" : ((""), ""),
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
                                self.owner.strings[name]["files"][file][i][j][LocIndex.TL],
                                checks
                            )
                            if b:
                                self.owner.modified[name] = True
                                self.owner.strings[name]["files"][file][i][j][LocIndex.TL] = s
                                count += 1
            if count == 0:
                return "No strings have been modified"
            else:
                return f"{count} strings have been modified"
        except Exception as e:
            self.owner.log.error("[General Actions] Tool 'tool_special_char' failed with error:\n" + self.owner.trbk(e))
            return "An unexpected error occured"

    def _tool_special_remove_latin_accent(self : GeneralActions, input_string: str) -> str:
        nfd_string = unicodedata.normalize('NFD', input_string)
        return ''.join(char for char in nfd_string if unicodedata.category(char) != 'Mn')

    def _tool_special_char_parser(self : GeneralActions, s : str, checks : dict[str, Any]) -> tuple[str, bool]:
        m : str = s
        for k, (chars, replacement) in checks.items():
            if k == "_t_accent":
                m = self._tool_special_remove_latin_accent(m)
            else:
                for c in chars:
                    m = m.replace(c, replacement)
        return m, m != s

    def tool_clear_unlinked(self : GeneralActions, name : str, params : dict[str, Any]) -> str:
        try:
            if params["_t_confirm"]:
                self.owner.save() # save first!
                self.owner.backup_strings_file(name) # backup strings.json
                self.owner.load_strings(name)
                count : int = 0
                for file in self.owner.strings[name]["files"]:
                    for i, group in enumerate(self.owner.strings[name]["files"][file]):
                        for j in range(1, len(group)):
                            m : bool = False
                            if self.owner.strings[name]["files"][file][i][j][LocIndex.TL] is not None:
                                self.owner.strings[name]["files"][file][i][j][LocIndex.TL] = None
                                m = True
                            if self.owner.strings[name]["files"][file][i][j][LocIndex.LOCAL] == IntBool.TRUE:
                                self.owner.strings[name]["files"][file][i][j][LocIndex.LOCAL] = IntBool.FALSE
                                m = True
                            if m:
                                count += 1
                if count > 0:
                    self.owner.modified[name] = True
                    self.owner.start_compute_translated(name)
                    return f"{count} unlinked strings have been cleared"
                else:
                    return "No strings required modifications"
            else:
                return "Please confirm that you understand the purpose of this tool" 
        except Exception as e:
            self.owner.log.error("[General Actions] Tool 'tool_clear_unlinked' failed with error:\n" + self.owner.trbk(e))
            return "An unexpected error occured"

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
                        if lc[LocIndex.LOCAL]:
                            if lc[LocIndex.TL] is not None:
                                s = lc[LocIndex.TL]
                            else:
                                continue
                        elif gl[1] is not None:
                            s = gl[GloIndex.TL]
                        else:
                            continue
                        if max([len(line) for line in s.split('\n')]) > limit:
                            count += 1
                            self.owner.strings[name]["files"][file_path][g][i][LocIndex.MODIFIED] = IntBool.TRUE
                            self.owner.modified[name] = True
            if count > 0:
                return f"{count} strings are over the limit and have been marked"
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