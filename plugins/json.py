from __future__ import annotations
from . import Plugin, WalkHelper, GloIndex, LocIndex, IntBool
import json
import io
from pathlib import PurePath
from typing import Any
import textwrap

class JSON(Plugin):
    DEFAULT_RPGMK_DATA_FILE : set[str] = set(["data/actors.json", "data/animations.json", "data/armors.json", "data/classes.json", "data/enemies.json", "data/items.json", "data/mapinfos.json", "data/skills.json", "data/states.json", "data/tilesets.json", "data/weapons.json"])
    RPGMVMZ_CODE_TABLE = {
        101: "Show Text",
        102: "Choices",
        103: "Number Input",
        104: "Select Item",
        105: "Scrolling Text",
        108: "Comment",
        109: "Skip",
        111: "If ...",
        112: "Loop ...",
        113: "Loop Break",
        115: "Exit Event",
        117: "Common Event",
        118: "Label",
        119: "Jump to Label",
        121: "Switch Control",
        122: "Variable Control",
        123: "Self Switch Control",
        124: "Timer Control",
        125: "Gold Change",
        126: "Item Change",
        127: "Weapon Change",
        128: "Armor Change",
        129: "Party Change",
        132: "Battle BGM Change",
        133: "Victory ME Change",
        134: "Save Access Change",
        135: "Menu Access Change",
        136: "Encounter Change",
        137: "Formation Access Change",
        138: "Window Color Change",
        139: "Defeat ME Change",
        140: "Vehicle BGM Change",
        201: "Transfer Player",
        202: "Set Vehicle Location",
        203: "Set Event Location",
        204: "Scroll Map",
        205: "Set Movement Route",
        206: "Toggle Vehicle",
        211: "Transparency Change",
        212: "Show Animation",
        213: "Show Balloon Icon",
        214: "Erase Event",
        216: "Change Player Followers",
        217: "Gather Followers",
        221: "Fadeout Screen",
        222: "Fadein Screen",
        223: "Tint Screen",
        224: "Flash Screen",
        225: "Shake Screen",
        230: "Wait",
        231: "Show Picture",
        232: "Move Picture",
        233: "Rotate Picture",
        234: "Tint Picture",
        235: "Erase Picture",
        236: "Set Weather",
        241: "Play BGM",
        242: "Fadeout BGM",
        243: "Save BGM",
        244: "Resume BGM",
        245: "Play BGS",
        246: "Fadeout BGS",
        249: "Play ME",
        250: "Play SE",
        251: "Stop SE",
        261: "Play Movie",
        281: "Map Name Display Change",
        282: "Tileset Change",
        283: "Battle Background Change",
        284: "Parallax Change",
        285: "Get Location Info",
        301: "Battle Processing",
        302: "Shop Processing",
        303: "Name Input Processing",
        311: "HP Change",
        312: "MP Change",
        313: "State Change",
        314: "Recover All",
        315: "EXP Change",
        316: "LVL Change",
        317: "Parameter Change",
        318: "Skill Change",
        319: "Equipment Change",
        320: "Name Change",
        321: "Class Change",
        322: "Actor Image Change",
        323: "Vehicle Image Change",
        324: "Nickname Change",
        325: "Profile Change",
        326: "TP Change",
        331: "Enemy HP Change",
        332: "Enemy MP Change",
        333: "Enemy State Change",
        334: "Enemy Recover All",
        335: "Enemy Appear",
        336: "Enemy Transform",
        337: "Show Battle Animation",
        339: "Force Action",
        340: "Abort Battle",
        342: "Enemy TP Change",
        351: "Open Menu Screen",
        352: "Open Save Screen",
        353: "Game Over",
        354: "Return to Title Screen",
        355: "Script",
        356: "Plugin Command (MV)",
        357: "Plugin Command (MZ)",
        401: "Text Line",
        402: "When ...",
        403: "When Cancel",
        405: "Scrolling Line",
        408: "Comment Line",
        411: "Else ...",
        413: "Repeat above...",
        601: "If Battle Win",
        602: "If Battle Escape",
        603: "If Battle Lose",
        655: "Script Line",
    }
    
    def __init__(self : JSON) -> None:
        super().__init__()
        self.name : str = "JSON"
        self.description : str = "v1.12\nHandle JSON files, including ones from RPG Maker MV/MZ"
        self.related_tool_plugins : list[str] = [self.name]

    def get_setting_infos(self : JSON) -> dict[str, list]:
        return {
            "json_rpgm_multiline": ["Merge multiline commands into one (Require re-extract)", "bool", False, None]
        }

    def get_tool_infos(self : JSON) -> dict[str, list]:
        return {
            "json_rpgm_text_wrap": [
                "assets/images/text_wrap.png", "RPGM Text wrap", self.tool_text_wrap,
                {
                    "type":self.COMPLEX_TOOL,
                    "params":{
                        "_t_char_limit":["Character Limit", "num", 60, None],
                        "_t_text":["Apply on Show Text commands", "bool", True, None],
                        "_t_name":["Ignore single-word first lines in Show Text commands", "bool", True, None],
                        "_t_desc":["Apply on Item/Equipment descriptions", "bool", False, None],
                        "_t_0000":["You can ignore the start of a string:", "display", None, None],
                        "_t_start":["Starting with (Optional):", "str", "", None],
                        "_t_end":["and ending with:", "str", "", None],
                    },
                    "help":"Tool to automatically wrap texts of RPG Maker games."
                }
            ],
            "json_rpgm_default_setup": [
                "assets/images/bandaid.png", "RPGM Default Setup", self.apply_default,
                {
                    "type":self.COMPLEX_TOOL,
                    "params":{
                        "_t_tl":["Apply Default Translations", "bool", True, None]
                    },
                    "help":"Tool to automatically setup RPGM Projects and more. Optionally, you can set common japanese strings to be set to some pre-translated english variants."
                }
            ]
        }

    def tool_text_wrap(self : JSON, name : str, params : dict[str, Any]) -> str:
        try:
            limit : int = int(params["_t_char_limit"])
            if limit < 1:
                raise Exception()
        except:
            return "Invalid character limit, it must be a positive integer."
        try:
            self.owner.save() # save first!
            self.owner.backup_strings_file(name) # backup strings.json
            self.owner.load_strings(name)
            seen : set[str] = set() # used to track which strings we tested
            count : int = 0
            for file in self.owner.strings[name]["files"]:
                for i, group in enumerate(self.owner.strings[name]["files"][file]):
                    mode = 0
                    if group[0] == "Command: Show Text":
                        if not params["_t_text"]:
                            continue
                        mode = 0
                    elif group[0] in {"description"} and file in {"data/Armors.json", "data/Weapons.json", "data/Items.json", "data/Skills.json"}:
                        if not params["_t_desc"]:
                            continue
                        mode = 1
                    else:
                        continue
                    for j in range(1, len(group)):
                        sid : str = self.owner.strings[name]["files"][file][i][j][LocIndex.ID]
                        if self.owner.strings[name]["strings"][sid][GloIndex.TL] is not None:
                            if sid not in seen:
                                seen.add(sid)
                                s, b = self._tool_text_wrap_sub(
                                    limit,
                                    self.owner.strings[name]["strings"][sid][GloIndex.TL],
                                    mode,
                                    params["_t_name"],
                                    params["_t_start"],
                                    params["_t_end"],
                                )
                                if b:
                                    self.owner.modified[name] = True
                                    self.owner.strings[name]["strings"][sid][GloIndex.TL] = s
                                    count += 1
                        
                        if self.owner.strings[name]["files"][file][i][j][LocIndex.TL] is not None:
                            s, b = self._tool_text_wrap_sub(
                                limit,
                                self.owner.strings[name]["strings"][sid][LocIndex.TL],
                                mode,
                                params["_t_name"],
                                params["_t_start"],
                                params["_t_end"],
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
        self : JSON,
        limit : int,
        string : str,
        mode : int,
        first_line : bool,
        start_delim : str,
        end_delim : str,
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
            # do nothing
            return "", False
        p : list[str] = string.split("\n")
        # remove name
        if mode == 0 and first_line:
            if " " not in p[0] and len(p[0]) <= limit:
                start += p[0]
                p = p[1:]
        # determine if has to check
        check = False
        if mode == 1 and len(p) > 2:
            check = True
        elif mode == 0 and len(p) > 4:
            check = True
        else:
            for k in p:
                if len(k) > limit:
                    check = True
                    break
        if not check:
            # do nothing
            return "", False
        p = textwrap.wrap(" ".join(p), width=limit, break_on_hyphens=False)
        string = start + "\n".join(p)
        return string, string != old

    def apply_default(self : JSON, name : str, params : dict[str, Any]) -> str:
        try:
            self.owner.save() # save first!
            self.owner.backup_strings_file(name) # backup strings.json
            self.owner.load_strings(name)
            modified_string : int = 0
            modified_file : int = 0
            # Applying default translation of common terms
            if params["_t_tl"]:
                default_tl = {
                    'レベル': 'Level', 'Lv': 'Lv', 'ＨＰ': 'HP', 'HP': 'HP', 'ＭＰ': 'MP', 'MP': 'MP',
                    'ＳＰ': 'SP', 'SP': 'SP', 'ＴＰ': 'TP', 'TP': 'TP', '経験値': 'Experience',
                    'EXP': 'EXP', '戦う': 'Fight', '逃げる': 'Run away', '攻撃': 'Attack',
                    'の攻撃！': ' attacked!', '%1の攻撃！': '%1 attacked!', '防御': 'Defend',
                    '連続攻撃': 'Continuous Attacks', '２回攻撃': 'Attack 2 times', '３回攻撃': 'Attack 3 times',
                    '様子を見る': 'Observe', '様子見': 'Wait and See', 'アイテム': 'Items', 'スキル': 'Skill',
                    '必殺技': 'Special', '装備': 'Equipment', 'ステータス': 'Status', '並び替え': 'Sort',
                    'セーブ': 'Save', 'ゲーム終了': 'To Title', 'オプション': 'Settings', '大事なもの': 'Key Items',
                    'ニューゲーム': 'New Game', 'コンティニュー': 'Continue', 'タイトルへ': 'Go to Title', 'やめる': 'Stop',
                    '購入する': 'Buy', '売却する': 'Sell', '最大ＨＰ': 'Max HP', '最大ＭＰ': 'Max MP', '最大ＳＰ': 'Max SP',
                    '最大ＴＰ': 'Max TP', '攻撃力': 'ATK', '防御力': 'DEF', '魔法力': 'M.ATK.', '魔法防御': 'M.DEF',
                    '敏捷性': 'AGI', '運': 'Luck', '命中率': 'ACC', '回避率': 'EVA', '持っている数': 'Owned',
                    'ヒール': 'Heal', 'ファイア': 'Fire', 'スパーク': 'Spark', '火魔法': 'Fire Magic', '氷魔法': 'Ice Magic',
                    '雷魔法': 'Thunder Magic', '水魔法': 'Water Magic', '土魔法': 'Earth Magic', '風魔法': 'Wind Magic',
                    '光魔法': 'Light Magic', '闇魔法': 'Dark Magic', '常時ダッシュ': 'Always run',
                    'コマンド記憶': 'Command Memory', 'タッチUI': 'Touch UI', 'BGM 音量': 'BGM volume',
                    'BGS 音量': 'BGS volume', 'ME 音量': 'ME Volume', 'SE 音量': 'SE volume', '所持数': 'Owned',
                    '現在の%1': 'Current %1', '次の%1まで': 'Until next %1',
                    'どのファイルにセーブしますか？': 'Which file do you want to save it to?',
                    'どのファイルをロードしますか？': 'Which file do you want to load?',
                    'ファイル': 'File', 'オートセーブ': 'Auto Save', '%1たち': '%1', '%1が出現！': '%1 appeared!',
                    '%1は先手を取った！': '%1 took the initiative!', '%1は不意をつかれた！': '%1 was caught off guard!',
                    '%1は逃げ出した！': '%1 ran away!', 'は逃げてしまった。': ' is running away.',
                    'は身を守っている。': ' is on guard.', 'は様子を見ている。': ' is watching the situation.',
                    'は%1を唱えた！': ' casted %1!', 'しかし逃げることはできなかった！': 'But escape is impossible!',
                    '%1の勝利！': '%1 wins!', '%1は戦いに敗れた。': '%1 lost the battle.', '%1 の%2を獲得！': 'Obtained %1 %2s!',
                    'お金を %1\\G 手に入れた！': 'Obtained %1 \\G!', '%1を手に入れた！': 'Obtained %1!',
                    '%1は%2 %3 に上がった！': '%1 rose to %2 %3!', '%1を覚えた！': 'Learned %1!', '%1は%2を使った！': '%1 used %2!',
                    '%1は身を守っている。': '%1 is defending.', '会心の一撃！！': 'A decisive blow!!',
                    '痛恨の一撃！！': 'A painful blow!!', '%1は %2 のダメージを受けた！': '%1 received %2 damage!',
                    '%1の%2が %3 回復した！': '%1\'s %2 recovered by %3!', '%1の%2が %3 増えた！': '%1\'s %2 increased by %3!',
                    '%1の%2が %3 減った！': '%1\'s %2 decreased %3!', '%1は%2を %3 奪われた！': '%1 was robbed of %2 %3!',
                    '%1はダメージを受けていない！': '%1 didn\'t receive any damage!',
                    'ミス！\u3000%1はダメージを受けていない！': 'Miss! %1 didn\'t receive any damage!',
                    '%1に %2 のダメージを与えた！': 'Inflicted %2 damage to %1!',
                    '%1の%2を %3 奪った！': '%2 of %1 was stolen from %3!',
                    '%1にダメージを与えられない！': 'Cannot damage %1!',
                    'ミス！\u3000%1にダメージを与えられない！': 'Miss! Can\'t damage %1!',
                    '%1は攻撃をかわした！': '%1 dodged the attack!', '%1は魔法を打ち消した！': '%1 canceled the magic!',
                    '%1は魔法を跳ね返した！': '%1 reflected the magic!', '%1の反撃！': "%1's counterattack!",
                    '%1が%2をかばった！': '%1 protected %2!', '%1の%2が上がった！': '%1\'s %2 increased!',
                    '%1の%2が下がった！': '%1\'s %2 decreased!', '%1の%2が元に戻った！': '%1\'s %2 is back to normal!',
                    '%1には効かなかった！': '%1 is unaffected!', 'は倒れた！': ' has fallen!',
                    'を倒した！': ' has been defeated!', '%1を倒した！': '%1 has been defeated!',
                    '%1は倒れた！': '%1 has collapsed!', 'は立ち上がった！': ' has stood up!',
                    '%1は立ち上がった！': '%1 has stood up!', '戦闘不能': 'Incapacited', '不死身': 'Immortality',
                    'は毒にかかった！': ' is poisoned!', 'に毒をかけた！': ' has been poisoned!',
                    'の毒が消えた！': ' isn\'t poisoned anymore!', '毒': 'Poison', 'は暗闇に閉ざされた！': ' is engulfed in darkness!',
                    'を暗闇に閉ざした！': ' has been engulfed in darkness!', 'の暗闇が消えた！': ' is free from the darkness!',
                    '暗闇': 'Darkness', 'は沈黙した！': ' is silenced!', 'を沈黙させた！': ' has been silenced!',
                    'の沈黙が解けた！': ' isn\'t silenced anymore!', '沈黙': 'Silence', 'は激昂した！': ' is enraged!',
                    'を激昂させた！': ' has been enraged!', 'は我に返った！': ' got their senses back!', '激昂': 'Enraged',
                    'は魅了された！': ' is captivated!', 'を魅了した！': ' has been charmed!', '魅了': 'Charm',
                    'は眠った！': ' is asleep!', 'を眠らせた！': ' has been put to sleep!', 'は眠っている。': ' is asleep.',
                    'は目を覚ました！': ' woke up!', '睡眠': 'Sleep', 'はい': 'Yes', 'いいえ': 'No', '一般防具':'Medium Armor',
                    '魔法防具':'Magic Armor', '軽装防具':'Light Armor', '重装防具':'Heavy Armor', '小型盾':'Small Shield',
                    '大型盾':'Large Shield', '短剣':'Dagger', '剣':'Sword', 'フレイル':'Flail', '斧':'Axe', 'ムチ':'Whip',
                    '杖':'Staff', '弓':'Bow', 'クロスボウ':'Crossbow', '銃':'Gun', '爪':'Claw', 'グローブ':'Gloves', '槍':'Spear',
                    'Ｇ':'G', '物理':'Physics', '炎':'Fire', '氷':'Ice', '雷':'Thunder', '水':'Water', '土':'Earth', '風':'Wind',
                    '光':'Light', '闇':'Dark', '盾':'Shield', '武器':'Weapon', '頭':'Head', '身体':'Body', '装飾品':'Accessories',
                    '魔法':'Magic', '特殊行動':'Special', 'ステート':'State', 'レベル':'Level', '気力':'Energy', '並び替え':'Sort',
                    '防具':'Armor', '最強装備':'Optimize', '全て外す':'Remove all', 'ja_JP':'en_US',
                    'はい':'Yes', 'いいえ':'No'
                }
                for s in self.owner.strings[name]["strings"]:
                    if (
                        self.owner.strings[name]["strings"][s][GloIndex.ORI] in default_tl and
                        self.owner.strings[name]["strings"][s][GloIndex.TL] is None
                            ):
                        self.owner.strings[name]["strings"][s][GloIndex.TL] = default_tl[self.owner.strings[name]["strings"][s][GloIndex.ORI]]
                        self.owner.modified[name] = True
                        modified_string += 1
            detected_rpgmv : bool = False
            # Disabling common unrelated files by default
            ignored_files = [
                "data/Animations.json", "data/MapInfos.json", "data/Tilesets.json", "package.json", "js/plugins/", "js/libs/", "js/main.js", "js/rpg_core.js", "js/rpg_managers.js", "js/rpg_objects.js", "js/rpg_scenes.js", "js/rpg_sprites.js", "js/rpg_windows.js", "js/rmmz_core.js", "js/rmmz_managers.js", "js/rmmz_objects.js", "js/rmmz_scenes.js", "js/rmmz_sprites.js", "js/rmmz_windows.js", "js/plugins.js/",
                "www/data/Animations.json", "www/data/MapInfos.json", "www/data/Tilesets.json", "www/package.json", "www/js/plugins/", "www/js/libs/", "www/js/main.js", "www/js/rpg_core.js", "www/js/rpg_managers.js", "www/js/rpg_objects.js", "www/js/rpg_scenes.js", "www/js/rpg_sprites.js", "www/js/rpg_windows.js", "www/js/rmmz_core.www/js", "www/js/rmmz_managers.www/js", "www/js/rmmz_objects.www/js", "www/js/rmmz_scenes.www/js", "www/js/rmmz_sprites.www/js", "www/js/rmmz_windows.www/js", "www/js/plugins.js/",
                "Data/Animations.rxdata", "Data/MapInfos.rxdata", "Data/Tilesets.rxdata", "Data/Scripts.rxdata",
                "Data/Animations.rvdata", "Data/MapInfos.rvdata", "Data/Tilesets.rvdata", "Data/Scripts.rvdata",
                "Data/Animations.rvdata2", "Data/MapInfos.rvdata2", "Data/Tilesets.rvdata2", "Data/Scripts.rvdata2"
            ]
            for f in self.owner.projects[name]["files"]:
                for i in ignored_files:
                    if i in f:
                        detected_rpgmv = True
                        self.owner.projects[name]["files"][f]["ignored"] = 1
                        self.owner.modified[name] = True
                        modified_file += 1
                        break
            # Disable RPG Maker switches, variables and others
            for f in ["www/data/System.json", "data/System.json"]:
                if f in self.owner.strings[name]["files"]:
                    detected_rpgmv = True
                    for i, g in enumerate(self.owner.strings[name]["files"][f]):
                        if g[0] in ['switches', 'variables', 'encryptionKey']:
                            for j in range(1, len(g)):
                                self.owner.strings[name]["files"][f][i][j][LocIndex.IGNORED] = IntBool.TRUE
                                self.owner.modified[name] = True
                                modified_string += 1
            # Disable some RPG Maker text files
            if detected_rpgmv:
                for f in self.owner.projects[name]["files"]:
                    if f.startswith(("www/img/tilesets/", "img/tilesets/")):
                        self.owner.projects[name]["files"][f]["ignored"] = IntBool.TRUE
                        self.owner.modified[name] = True
                        modified_file += 1
            # Disabling specific RPG maker event codes or groups
            text_codes = set(["Command: Show Text", "Command: Choices", "Command: When ...", "Command: Name Change"]) # allowed ones
            other_groups = set(["battlerName", "faceName", "characterName", "parallaxName", "switches", "variables", "encryptionKey", "formula", "note", "@icon_name", "@battler_name", "numberFontFilename", "fallbackFonts", "mainFontFilename", "title1Name", "title2Name", "battleback1Name", "battleback2Name"])
            for f in self.owner.strings[name]["files"]:
                for i, group in enumerate(self.owner.strings[name]["files"][f]):
                    if (
                        (group[0].startswith("Command: ") and group[0] not in text_codes) or
                        (group[0] == "name" and ("/Map" in f or f.endswith("System.json"))) or # disable specific map/system name
                        group[0] in other_groups
                            ):
                        for j in range(1, len(group)):
                            self.owner.strings[name]["files"][f][i][j][LocIndex.IGNORED] = IntBool.TRUE
                            self.owner.modified[name] = True
                            modified_string += 1
                            
                            
            # Disable number/boolean strings
            strids = set()
            for k, v in self.owner.strings[name]["strings"].items():
                if v[0] in ["True", "true", "False", "false"]: # bool check
                    strids.add(k)
                    continue
                try: # number check
                    float(v[0])
                    strids.add(k)
                except:
                    pass
            for f in self.owner.strings[name]["files"]:
                for i, group in enumerate(self.owner.strings[name]["files"][f]):
                    for j in range(1, len(group)):
                        if group[j][LocIndex.ID] in strids:
                            self.owner.strings[name]["files"][f][i][j][LocIndex.IGNORED] = IntBool.TRUE
                            self.owner.modified[name] = True
                            modified_string += 1
            self.owner.start_compute_translated(name)
            return "{} modifications applied".format(modified_string + modified_file)
        except Exception as e:
            self.owner.log.error("[JSON] Tool 'tool_text_wrap' failed with error:\n" + self.owner.trbk(e))
            return "An unexpected error occured"

    def match(self : JSON, file_path : str, is_for_action : bool) -> bool:
        return file_path.endswith(".json")

    def read(self : JSON, file_path : str, content : bytes) -> list[list[str]]:
        data = json.loads(self.decode(content))
        p : PurePath = PurePath(file_path) # path object equivalent
        dp : str = p.relative_to(p.parent.parent) # path one folder up (to detect Data folder)
        s : str = dp.as_posix().lower() # as lowercase posix string
        if s == "data/system.json": # System file of RPGMV/MZ
            return self._read_walk_system(data)
        elif s == "data/commonevents.json": # CommonEvents file of RPGMV/MZ
            return self._read_walk_common(data)
        elif s == "data/troops.json": # Troops.json file of RPGMV/MZ
            return self._read_walk_troops(data)
        elif s in self.DEFAULT_RPGMK_DATA_FILE:
            return self._read_walk_data(data)
        elif s.startswith("data/map"): # Map file of RPGMV/MZ (Note: Make sure it's after mapinfos or it'll be caught by it)
            return self._read_walk_map(data)
        else:
            return self._read_walk(data)

    def write(self : JSON, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        data = json.loads(self.decode(content))
        modified : bool = False
        format_mode : int = -1
        if isinstance(data, str):
            helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
            data = helper.apply_string(data)
            modified = helper.modified
        else:
            p : PurePath = PurePath(file_path) # path object equivalent
            dp : str = p.relative_to(p.parent.parent) # path one folder up (to detect Data folder)
            s : str = dp.as_posix().lower() # as lowercase posix string
            if s == "data/commonevents.json": # CommonEvents file of RPGMV/MZ
                modified = self._write_walk_common(name, file_path, self.owner.strings[name], data)
                format_mode = 0
            else:
                helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
                if s == "data/system.json": # System file of RPGMV/MZ
                    self._write_walk_system(data, helper)
                    format_mode = 2
                elif s == "data/troops.json": # Troops.json file of RPGMV/MZ
                    self._write_walk_troops(data, helper)
                    format_mode = 0
                elif s in self.DEFAULT_RPGMK_DATA_FILE:
                    self._write_walk_data(data, helper)
                    format_mode = 0
                elif s.startswith("data/map"): # Map file of RPGMV/MZ (Note: Make sure it's after mapinfos or it'll be caught by it)
                    self._write_walk_map(data, helper)
                    format_mode = 1
                else:
                    self._write_walk(data, helper)
                modified = helper.modified
        if modified:
            return self.format_json(data, format_mode), True
        else:
            return content, False
    
    def format_json(self : JSON, data : any, mode : int) -> bytes:
        # Format in different way depending on what kind of file it is
        match mode:
            case 0: # default rpg maker files
                # For these files, we try to keep the formatting as close as standard RPGMV/MZ as possible
                with io.StringIO() as f:
                    self._format_element(f, data)
                    return self.encode(f.getvalue())
            case 1: # Map files
                # Keep the standard format of Map files
                with io.StringIO() as f:
                    keys = list(data.keys())
                    f.write("{\n")
                    for k, v in data.items():
                        match k:
                            case "data":
                                f.write("\n")
                                f.write("\"{}\":".format(k))
                                json.dump(v, f, ensure_ascii=False, separators=(',', ':'))
                                if k != keys[-1]:
                                    f.write(",")
                            case "events":
                                f.write("\n")
                                f.write("\"{}\":".format(k))
                                self._format_element(f, v)
                                if k != keys[-1]:
                                    f.write(",")
                                f.write("\n")
                            case _:
                                f.write("\"{}\":".format(k))
                                json.dump(v, f, ensure_ascii=False, separators=(',', ':'))
                                if k != keys[-1]:
                                    f.write(",")
                    f.write("}")
                    return self.encode(f.getvalue())
            case 2: # System file
                # Keep the standard format of System.json
                with io.StringIO() as f:
                    json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
                    return self.encode(f.getvalue())
            case _:
                # Other json files
                return self.encode(json.dumps(data))
    
    # Used by format
    # Just JSON formatting mess
    def _format_element(self : JSON, f : io.StringIO, data : Any) -> None:
        match data:
            case dict():
                f.write("{\n")
                keys = list(data.keys())
                for k, v in data.items():
                    f.write("\"{}\":".format(k))
                    json.dump(v, f, ensure_ascii=False, separators=(',', ':'))
                    if k != keys[-1]:
                        f.write(",")
                    f.write("\n")
                f.write("}")
            case list():
                f.write("[\n")
                for i, v in enumerate(data):
                    json.dump(v, f, ensure_ascii=False, separators=(',', ':'))
                    if i < len(data) - 1:
                        f.write(",")
                    f.write("\n")
                f.write("]")
            case _:
                raise Exception("Error: " + str(type(data)))
    
    # Generic JSON processing
    def _read_walk(self : JSON, obj : Any, ignore_key : str|None = None) -> list[list[str]]:
        entries : list[list[str]] = []
        match obj:
            case dict():
                for k in obj:
                    if ignore_key is not None and ignore_key == k:
                        continue
                    if isinstance(obj[k], str):
                        if obj[k] != "":
                            entries.append([k, obj[k]])
                    else:
                        entries.extend(self._read_walk(obj[k], ignore_key))
            case list():
                for i in range(len(obj)):
                    if isinstance(obj[i], str):
                        if obj[i] != "":
                            entries.append([str(i), obj[i]])
                    else:
                        entries.extend(self._read_walk(obj[i], ignore_key))
            case str():
                if obj != "":
                    entries.append(["", obj])
            case _:
                pass
        return entries

    def _write_walk(self : JSON, obj : Any, helper : WalkHelper, ignore_key : str|None = None) -> None:
        match obj:
            case dict():
                for k in obj:
                    if ignore_key is not None and ignore_key == k:
                        continue
                    if isinstance(obj[k], str):
                        if obj[k] != "":
                            obj[k] = helper.apply_string(obj[k], k)
                    else:
                        self._write_walk(obj[k], helper, ignore_key)
            case list():
                for i in range(len(obj)):
                    if isinstance(obj[i], str):
                        if obj[i] != "":
                            obj[i] = helper.apply_string(obj[i], str(i))
                    else:
                        self._write_walk(obj[i], helper, ignore_key)
            case str():
                raise Exception("[JSON] Invalid code path")
            case _:
                pass
    
    # RPGMV/MZ System.json processing
    def _read_walk_system(self : JSON, obj : dict[str, Any]) -> list[list[str]]|str:
        entries : list[list[str]] = []
        for k, v in obj.items():
            match v:
                case str():
                    if v != "":
                        entries.append([k, v])
                case list():
                    group : list[str] = [k]
                    for s in v:
                        if isinstance(s, str) and s != "":
                            group.append(s)
                    if len(group) > 1:
                        entries.append(group)
                case dict():
                    entries.extend(self._read_walk_system(v))
                case _:
                    pass
        return entries

    def _write_walk_system(self : JSON, obj : Any, helper : WalkHelper) -> None:
        for k, v in obj.items():
            match v:
                case str():
                    if v != "":
                        obj[k] = helper.apply_string(obj[k])
                case list():
                    for i in range(len(v)):
                        if isinstance(v[i], str) and v[i] != "":
                            obj[k][i] = helper.apply_string(obj[k][i])
                case dict():
                    self._write_walk_system(obj[k], helper)
                case _:
                    pass

    # RPGMV/MZ Map files processing
    def _read_walk_map(self : JSON, obj : Any) -> list[list[str]]:
        entries : list[list[str]] = []
        for k, v in obj.items():
            match v:
                case str():
                    if v != "":
                        entries.append([k, v])
                case list():
                    if k == "events":
                        for ev in v:
                            if isinstance(ev, dict):
                                for i, p in enumerate(ev["pages"]):
                                    strings = self._read_walk_event(p["list"])
                                    if len(strings) > 0:
                                        entries.append(["Page {}".format(i+1)])
                                        entries.extend(strings)
                    else:
                        group : list[str] = [k]
                        for s in v:
                            if isinstance(s, str) and s != "":
                                group.append(s)
                        if len(group) > 1:
                            entries.append(group)
                case dict():
                    entries.extend(self._read_walk_system(v))
                case _:
                    pass
        return entries

    def _write_walk_map(self : JSON, obj : Any, helper : WalkHelper) -> None:
        for k, v in obj.items():
            match v:
                case str():
                    if v != "":
                        obj[k] = helper.apply_string(obj[k])
                case list():
                    if k == "events":
                        for i in range(len(v)):
                            if isinstance(v[i], dict):
                                for j in range(len(v[i]["pages"])):
                                    self._write_walk_event(v[i]["pages"][j]["list"], helper)
                    else:
                        for i in range(len(v)):
                            if isinstance(v[i], str) and v[i] != "":
                                obj[k][i] = helper.apply_string(obj[k][i])
                case dict():
                    self._write_walk_system(obj[k], helper)
                case _:
                    pass

    # RPGMV/MZ CommonEvents processing
    def _read_walk_common(self : JSON, obj : Any) -> list[list[str]]:
        entries : list[list[str]] = []
        for ev in obj:
            if ev is None:
                continue
            strings = self._read_walk_event(ev["list"])
            if len(strings) > 0:
                entries.append([self.owner.CHILDREN_FILE_ID + "{:04}".format(ev["id"]) + " " + ev["name"].replace("/", " ")])
                entries.extend(strings)
        return entries

    def _write_walk_common(self : JSON, name : str, file_path : str, strings : dict, obj : Any) -> bool:
        modified : bool = False
        for i in range(len(obj)):
            if obj[i] is None:
                continue
            evname : str = file_path + "/{:04}".format(obj[i]["id"]) + " " + obj[i]["name"].replace("/", " ")
            if evname in strings["files"] and not self.owner.projects[name]["files"][evname]["ignored"]:
                helper : WalkHelper = WalkHelper(evname, strings)
                self._write_walk_event(obj[i]["list"], helper)
                if helper.modified:
                    modified = True
        return modified

    # RPGMV/MZ Events processing
    # Used by both Map and CommonEvents
    # We process differently based on the event codes
    def _walk_event_continuous_command(self : JSON, i : int, cmds : list[dict], code : int) -> tuple[int, list[str]]:
        text : list[str] = []
        while i < len(cmds) and cmds[i]["code"] == code:
            text.append(cmds[i]["parameters"][0])
            i += 1
        i -= 1
        return i, text
    
    def _read_walk_event(self : JSON, cmds : list[dict]) -> list[list[str]]:
        entries : list[list[str]] = []
        group : list[str] = [""]
        i : int = 0
        while i < len(cmds):
            cmd = cmds[i]
            group[0] = "Command: " + self.RPGMVMZ_CODE_TABLE.get(cmd["code"], "Code " + str(cmd["code"]))
            match cmd["code"]:
                case 101: # Show Text commands
                    if len(cmd["parameters"]) >= 5 and isinstance(cmd["parameters"][4], str) and cmd["parameters"][4] != "": # Show Text, Speaker Name (MZ only)
                        group.append(cmd["parameters"][4])
                    i += 1
                    i, text = self._walk_event_continuous_command(i, cmds, 401)
                    if len(text) > 0:
                        if self.settings.get("json_rpgm_multiline", False):
                            group.append("\n".join(text))
                        else:
                            group.extend(text)
                case 355: # Scripting
                    if len(cmd["parameters"]) >= 1 and isinstance(cmd["parameters"][0], str):
                        tmp = cmd["parameters"][0]
                    else:
                        tmp = ""
                    i += 1
                    i, text = self._walk_event_continuous_command(i, cmds, 655)
                    if tmp != "" or len(text) > 0:
                        if self.settings.get("json_rpgm_multiline", False):
                            text.insert(0, tmp)
                            group.append("\n".join(text))
                        else:
                            if tmp != "":
                                group.append(tmp)
                            group.extend(text)
                case 102: # Choices
                    if len(cmd["parameters"]) >= 1 and isinstance(cmd["parameters"][0], list):
                        for s in cmd["parameters"][0]:
                            if s != "":
                                group.append(s)
                case 108|408: # Comment
                    pass
                case 357: # Plugin Command (MZ only)
                    for pm in cmd["parameters"]:
                        if isinstance(pm, str) and pm != "":
                            group.append(pm)
                        elif isinstance(pm, dict):
                            for k, v in pm.items():
                                if isinstance(v, str) and v != "":
                                    group.append(v)
                case _: # Default
                    for pm in cmd["parameters"]:
                        if isinstance(pm, str) and pm != "":
                            group.append(pm)
            if len(group) > 1:
                entries.append(group)
                group = [""]
            i += 1
        return entries

    def _write_walk_event(self : JSON, cmds : list[dict], helper : WalkHelper) -> None:
        i : int = 0
        while i < len(cmds):
            cmd = cmds[i]
            group = "Command: " + self.RPGMVMZ_CODE_TABLE.get(cmd["code"], "Code " + str(cmd["code"]))
            match cmd["code"]:
                case 101: # Show Text commands
                    if len(cmd["parameters"]) >= 5 and isinstance(cmd["parameters"][4], str) and cmd["parameters"][4] != "": # Show Text, Speaker Name (MZ only)
                        cmd["parameters"][4] = helper.apply_string(cmd["parameters"][4], group)
                    i += 1
                    start = i
                    i, text = self._walk_event_continuous_command(i, cmds, 401)
                    if len(text) > 0:
                        if self.settings.get("json_rpgm_multiline", False):
                            # Multiline mode
                            combined : str = helper.apply_string("\n".join(text), group)
                            if helper.str_modified:
                                while combined.count('\n') < len(text)-1:
                                    combined += "\n "
                                if len(text) > 1:
                                    text = combined.split('\n', len(text)-1)
                                else:
                                    text[0] = combined
                        else:
                            # Single line mode
                            for j in range(len(text)):
                                text[j] = helper.apply_string(text[j], group)
                        for j in range(start, i+1):
                            cmds[j]["parameters"][0] = text[j-start]
                case 355: # Scripting
                    if len(cmd["parameters"]) >= 1 and isinstance(cmd["parameters"][0], str):
                        tmp = cmd["parameters"][0]
                    else:
                        tmp = ""
                    start = i
                    i += 1
                    i, text = self._walk_event_continuous_command(i, cmds, 655)
                    text.insert(0, tmp)
                    if tmp != "" or len(text) > 1:
                        if self.settings.get("json_rpgm_multiline", False):
                            # Multiline mode
                            combined : str = helper.apply_string("\n".join(text), group)
                            if helper.str_modified:
                                while combined.count('\n') < len(text)-1:
                                    combined += "\n "
                                if len(text) > 1:
                                    text = combined.split('\n', len(text)-1)
                                else:
                                    text[0] = combined
                        else:
                            # Single line mode
                            for j in range(len(text)):
                                text[j] = helper.apply_string(text[j], group)
                        for j in range(start, i+1):
                            cmds[j]["parameters"][0] = text[j-start]
                case 102: # Choices
                    if len(cmd["parameters"]) >= 1 and isinstance(cmd["parameters"][0], list):
                        for j in range(len(cmd["parameters"][0])):
                            if cmd["parameters"][0][j] != "":
                                cmd["parameters"][0][j] = helper.apply_string(cmd["parameters"][0][j], group)
                case 108|408: # Comment
                    pass
                case 357: # Plugin Command (MZ only)
                    for j in range(len(cmd["parameters"])):
                        if isinstance(cmd["parameters"][j], str) and cmd["parameters"][j] != "":
                            cmds[i]["parameters"][j] = helper.apply_string(cmds[i]["parameters"][j], group)
                        elif isinstance(cmd["parameters"][j], dict):
                            for k in cmd["parameters"][j]:
                                if isinstance(cmd["parameters"][j][k], str) and cmd["parameters"][j][k] != "":
                                    cmds[i]["parameters"][j][k] = helper.apply_string(cmds[i]["parameters"][j][k], group)
                case _: # Default
                    for j in range(len(cmd["parameters"])):
                        if isinstance(cmd["parameters"][j], str) and cmd["parameters"][j] != "":
                            cmds[i]["parameters"][j] = helper.apply_string(cmds[i]["parameters"][j], group)
            i += 1

    # RPGMV/MZ standard Data Files processing
    def _read_walk_troops(self : JSON, obj : Any) -> list[list[str]]:
        entries : list[list[str]] = []
        for ev in obj:
            if ev is None:
                continue
            strings = self._read_walk(ev, "pages")
            if len(strings) > 0:
                entries.append(["ID " + str(ev["id"])])
                entries.extend(strings)
            if "pages" in ev:
                for i, p in enumerate(ev["pages"]):
                    strings = self._read_walk_event(p["list"])
                    if len(strings) > 0:
                        entries.append(["Page {}".format(i+1)])
                        entries.extend(strings)
        return entries

    def _write_walk_troops(self : JSON, obj : Any, helper : WalkHelper) -> None:
        for i in range(len(obj)):
            if obj[i] is None:
                continue
            self._write_walk(obj[i], helper, "pages")
            if "pages" in obj[i]:
                for j in range(len(obj[i]["pages"])):
                    self._write_walk_event(obj[i]["pages"][j]["list"], helper)

    # RPGMV/MZ standard Data Files processing
    def _read_walk_data(self : JSON, obj : Any) -> list[list[str]]:
        entries : list[list[str]] = []
        for ev in obj:
            if ev is None:
                continue
            strings = self._read_walk(ev)
            if len(strings) > 0:
                entries.append(["ID " + str(ev["id"])])
                entries.extend(strings)
        return entries

    def _write_walk_data(self : JSON, obj : Any, helper : WalkHelper) -> None:
        for i in range(len(obj)):
            if obj[i] is None:
                continue
            self._write_walk(obj[i], helper)