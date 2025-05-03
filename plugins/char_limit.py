from __future__ import annotations
from . import Plugin
from typing import Any

class CharaLimit(Plugin):
    def __init__(self : CharaLimit) -> None:
        super().__init__()
        self.name : str = "Character Limit"
        self.description : str = "v1.2\nAllow you to automatically set new lines when a string goes above a certain character threshold."

    def get_setting_infos(self : CharaLimit) -> dict[str, list]:
        return {
            "char_limit_count": ["Character Limit (0 or less means None)", "num", 0, None],
            "char_limit_rpgmaker": ["Only check RPG Maker Text commands ", "bool", True, None],
        }

    def get_action_infos(self : CharaLimit) -> dict[str, list]:
        return {
            "char_limit_check": ["Check the Character Limit", self.check_limit],
        }

    def match(self : CharaLimit, file_path : str, is_for_action : bool) -> bool:
        return is_for_action

    def check_limit(self : CharaLimit, name : str, file_path : str, settings : dict[str, Any] = {}) -> str:
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
                        gl = self.owner.strings[name]["strings"][lc[0]]
                        if lc[2] and lc[1] is not None:
                            s = lc[1]
                        elif gl[1] is not None:
                            s = gl[1]
                        else:
                            continue
                        if max([len(line) for line in s.split('\n')]) > limit:
                            count += 1
                            self.owner.strings[name]["files"][file_path][g][i][4] = 1
                            self.owner.modified[name] = True
            if count > 0:
                return "{} strings are over the limit and have been marked".format(count)
            else:
                return "No strings are over the limit"
        except Exception as e:
            self.owner.log.error("[Character Limit] Action 'check_limit' failed with error:\n" + self.owner.trbk(e))
            return "An error occured."