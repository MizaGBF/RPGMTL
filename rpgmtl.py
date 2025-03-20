from __future__ import annotations
import asyncio
from aiohttp import web
from typing import Any
from dataclasses import dataclass
import os
import shutil
import copy
import traceback
import logging
from logging.handlers import RotatingFileHandler
import json
import difflib
from pathlib import Path
from tkinter import filedialog
import tkinter as Tk
import argparse
import ssl

import plugins

######################################################
# A simple helper class for the patch system
######################################################
@dataclass(slots=True)
class PatcherHelper():
    _content_ : bytes
    modified : bool

    def __init__(self : PatcherHelper, content : bytes) -> None:
        self._content_ = content
        self.modified = False

    # Access/Edit the file content
    @property
    def content(self : PatcherHelper) -> bytes:
        return self._content_

    @content.setter
    def content(self : PatcherHelper, b : bytes) -> None:
        self._content_ = b

    # Convert to/from String
    def to_str(self : PatcherHelper, *, encoding : str = 'utf-8') -> str:
        return self._content_.decode(encoding)

    def from_str(self : PatcherHelper, s : str, *, encoding : str = 'utf-8') -> None:
        self._content_ = s.encode(encoding)

    # Convert to/from JSON
    def to_json(self : PatcherHelper, *, encoding : str = 'utf-8') -> str:
        return json.loads(self._content_.decode(encoding))

    def from_json(self : PatcherHelper, s : str, *, encoding : str = 'utf-8', ensure_ascii : bool = False, indent : None|int = None, separators : None|tuple[str, str] = None) -> None:
        self._content_ = json.dumps(s, ensure_ascii=ensure_ascii, separators=separators, indent=indent).encode(encoding)

######################################################
# The Main class
######################################################
class RPGMTL():
    # constant
    VERSION = "3.6"
    def __init__(self : RPGMTL) -> None:
        # Setting up logging
        handler = RotatingFileHandler(filename="rpgmtl.log", encoding='utf-8', mode='w', maxBytes=51200, backupCount=3)
        handler.setFormatter(logging.Formatter("%(asctime)s|%(levelname)s|%(name)s : %(message)s"))
        logging.basicConfig(level=logging.INFO)
        self.loggers = {}
        for l in ['rpgmtl', 'aiohttp.access','aiohttp.client','aiohttp.internal','aiohttp.server','aiohttp.web','aiohttp.websocket']:
            self.loggers[l] = logging.getLogger(l)
            self.loggers[l].addHandler(handler)
        self.log = self.loggers['rpgmtl']
        self.log.info("RPGMTL is starting up...")
        # Web server
        self.app : web.Application = web.Application()
        # Autosave system
        self.app.on_startup.append(self.init_autosave)
        self.app.on_cleanup.append(self.stop_autosave)
        # HTTP Routes
        self.app.router.add_static('/assets/images', path='./assets/images', name='assets')
        self.app.add_routes([
                web.get('/', self.page),
                web.get('/script.js', self.script),
                web.get('/style.css', self.style),
                web.get('/favicon.ico', self.favicon),
                
                web.post('/api/main', self.project_list), # main menu
                web.post('/api/shutdown', self.shutdown), # stop RPGMTL
                web.post('/api/update_location', self.select_project_exe), # Game Path selection
                web.post('/api/new_project', self.create_project), # Create Project
                web.post('/api/open_project', self.get_project), # Open Project
                web.post('/api/translator', self.get_translator), # Open Translator menu
                web.post('/api/update_translator', self.update_translator), # Update Translator
                web.post('/api/settings', self.get_settings), # Open Settings
                web.post('/api/update_settings', self.update_setting), # Update Settings
                web.post('/api/extract', self.generate_project), # Extract Strings
                web.post('/api/release', self.release), # Create Translation Patch
                web.post('/api/patches', self.open_patches), # Open Fix/Patch List
                web.post('/api/open_patch', self.edit_patch), # Open specific Fix/Patch
                web.post('/api/update_patch', self.update_patch), # Update specific Fix/Patch
                web.post('/api/import', self.import_old), # Import Old RPGMTL data
                web.post('/api/import_rpgmtrans', self.import_rpgmtrans), # Import RPG Maker Trans data
                web.post('/api/backups', self.backup_list), # Open list of strings.json backups
                web.post('/api/load_backup', self.load_backup), # Load strings.json backup
                web.post('/api/browse', self.open_folder), # Browse Folders/Files
                web.post('/api/ignore_file', self.ignore_file), # Toggle File ignore value
                web.post('/api/file', self.open_file), # Open File
                web.post('/api/file_action', self.run_action), # Run file action
                web.post('/api/update_string', self.edit_string), # Edit string values
                web.post('/api/translate_string', self.translate_string), # Translate a string
                web.post('/api/translate_file', self.translate_file), # Translate a file
                web.post('/api/search_string', self.search_string), # Search a file
        ])
        
        # data containers
        self.projects : dict[str, Any] = {} # store loaded config.json
        self.strings : dict[str, Any] = {} # store loaded string.json
        self.modified : dict[str, bool] = {} # store flag indicating if config.json or string.json has pending changes waiting to be saved
        self.computing : dict[str, int] = {} # store state for compute_translated
        self.setting_key_set : set[str] = set(["rpgmtl_current_translator"]) # store existing setting keys
        self.action_key_set : set[str] = set() # store existing action keys
        self.settings : dict[str, Any] = {} # store global plugins setting
        self.settings_modified : bool = False
        self.setting_menu : dict[str, dict[str, list]] = {} # store info for setting menu, per plugin file
        self.plugin_descriptions : dict[str, str] = {} # store plugin descriptions
        self.actions : dict[str, list] = {} # store plugin actions
        # loaded plugins
        self.plugins : dict[str, plugins.Plugin] = {}
        self.translators : dict[str, plugins.TranslatorPlugin] = {}
        # extensions supported by plugins
        self.extensions : set[str] = set()
        # load settings.json
        self.load_settings()
        # load the plugins (see plugins/__init__.py )
        plugins.load(self)

    # Function to format an exception into something readable
    def trbk(self : RPGMTL, e : Exception) -> str:
        return "".join(traceback.format_exception(type(e), e, e.__traceback__))

    # Generic function used by add_plugin and add_translator
    def process_infos(self : RPGMTL, plugin : Any) -> None:
        # Process plugin settings
        for k, v in plugin.get_setting_infos().items(): # go over returned settings
            if len(v) != 4: # error if invalid format
                raise Exception("[{}] Expected 4 values for setting key {}".format(plugin.name, k))
            if k in self.setting_key_set: # error if setting key is already set
                raise Exception("[{}] Setting key {} is already in use by another plugin".format(plugin.name, k))
            self.setting_key_set.add(k)
            
            menu_info = [v[0]] # Setting UI text
            match v[1]: # check type
                case "bool":
                    menu_info.append(v[1]) # add type string
                    if not isinstance(v[2], bool): # check default value
                        raise Exception("[{}] Default value of setting key {} isn't of type bool".format(plugin.name, k))
                case "str":
                    menu_info.append(v[1])
                    if not isinstance(v[2], str):
                        raise Exception("[{}] Default value of setting key {} isn't of type str".format(plugin.name, k))
                case "num":
                    menu_info.append(v[1])
                    if not isinstance(v[2], float) and not isinstance(v[2], int):
                        raise Exception("[{}] Default value of setting key {} isn't of number".format(plugin.name, k))
                case _:
                    raise Exception("[{}] Unexpected type for setting key {}".format(plugin.name, k))
            menu_info.append(v[3]) # add choices
            # Add setting to list
            if plugin.name not in self.setting_menu:
                self.setting_menu[plugin.name] = {}
            self.setting_menu[plugin.name][k] = menu_info
            # Add default value (if missing) to settings.json
            if k not in self.settings:
                self.settings[k] = v[2]
        
        # Process plugin actions
        for k, v in plugin.get_action_infos().items(): # same principle
            if len(v) != 2: # check the format
                raise Exception("[{}] Expected 2 values for action key {}".format(plugin.name, k))
            if k in self.action_key_set: # check if key is already set
                raise Exception("[{}] Action key {} is already in use by another Plugin".format(plugin.name, k))
            self.action_key_set.add(k)
            # add action
            self.actions[k] = [plugin.name, v[0], v[1]] # plugin name (for reverse lookup), UI text and callback

    # Add a plugin to RPGMTL
    def add_plugin(self : RPGMTL, plugin : plugins.Plugin) -> None:
        # Check validity
        if plugin.name == "__undefined__":
            raise Exception("The plugin doesn't have a name defined")
        elif plugin.name in self.plugins:
            raise Exception("[{}] Another plugin with the same name is already loaded".format(plugin.name))
        # Parse setting and action infos (see above function)
        self.process_infos(plugin)
        # Add and connect plugin
        self.plugins[plugin.name] = plugin
        plugin.connect(self)
        self.plugin_descriptions[plugin.name] = plugin.description

    # Add a translator to RPGMTL
    def add_translator(self : RPGMTL, plugin : plugins.TranslatorPlugin) -> None:
        if plugin.name == "__undefined__":
            raise Exception("The plugin doesn't have a name defined")
        elif plugin.name in self.plugins:
            raise Exception("[{}] Another plugin with the same name is already loaded".format(plugin.name))
        # Parse setting and action infos
        self.process_infos(plugin)
        # Add and connect plugin
        self.translators[plugin.name] = plugin
        if "rpgmtl_current_translator" not in self.settings: # init translator setting if not set
            self.settings["rpgmtl_current_translator"] = plugin.name
            self.settings_modified = True
        plugin.connect(self)
        self.plugin_descriptions[plugin.name] = plugin.description

    # Retrieve a specific plugin by its name
    def get_plugin(self : RPGMTL, name : str) -> plugins.Plugin|None:
        return self.plugins.get(name, None)

    # return a tuple of the Translator-in-use name and instance
    # name is the project name (to check a specific project setting)
    def get_current_translator(self : RPGMTL, name : str|None) -> tuple[str, plugins.TranslatorPlugin|None]:
        if name is not None: # check project setting
            if "rpgmtl_current_translator" in self.projects[name]["settings"]:
                pname : str = self.projects[name]["settings"]["rpgmtl_current_translator"]
                if pname in self.translators:
                    return pname, self.translators[pname]
        if "rpgmtl_current_translator" in self.settings: # check global setting
            pname : str = self.settings["rpgmtl_current_translator"]
            if pname in self.translators:
                return pname, self.translators[pname]
        # default, not found, result
        return "", None

    # load settings.json
    def load_settings(self : RPGMTL) -> None:
        try:
            with open('settings.json', mode='r', encoding='utf-8') as f:
                self.settings = json.load(f)
        except Exception as e:
            self.log.warning("Failed to load settings.json, default value will be used:\n" + self.trbk(e))

    # Save config.json, strings.json and load_settings.json
    def save(self : RPGMTL) -> None:
        for k, v in self.modified.items(): # check modified flags
            if v: # if raised
                folder = 'projects/' + k + '/'
                try:
                    self.modified[k] = False # reset it
                    # write config.json
                    with open(folder + "_tmp_config_.json", mode='w', encoding='utf-8') as f: # file is written to temporary location in case of issue
                        json.dump(self.projects[k], f, ensure_ascii=False, indent=4)
                    # move file to actual name
                    shutil.move(folder + "_tmp_config_.json", folder + "config.json")
                    self.log.info("Updated projects/" + k + "/config.json")
                except Exception as e:
                    self.log.error("Failed to update projects/" + k + "/config.json:\n" + self.trbk(e))
                try:
                    if k in self.strings: # if strings.json is loaded
                        # also save it
                        with open(folder + "_tmp_strings_.json", mode='w', encoding='utf-8') as f:
                            f.write(self.serialize_format_json(self.strings[k]))
                        # move file to actual name
                        shutil.move(folder + "_tmp_strings_.json", folder + "strings.json")
                        self.log.info("Updated projects/" + k + "/strings.json")
                except Exception as e:
                    self.log.error("Failed to update projects/" + k + "/strings.json:\n" + self.trbk(e))
        if self.settings_modified: # write settings if flag is set
            try:
                self.settings_modified = False
                with open('settings.json', mode='w', encoding='utf-8') as f:
                    f.write(self.serialize_format_json(self.settings))
                self.log.info("Updated settings.json")
            except Exception as e:
                self.log.error("Failed to update settings.json:\n" + self.trbk(e))

    # Utility recursive function to format strings.json in a certain way, to make it humanly readable and easy to pick apart by git
    def serialize_format_json(self : RPGMTL, d : Any, level : int = 0, parent_is_list : bool = False) -> str|list[str]:
        parts : list[str] = [] # using an array instead of a string to avoid needless string allocations
        match d: # check type
            case dict():
                parts.append("{\n")
                if len(d) > 0:
                    last_key : str = list(d.keys())[-1]
                    for k, v in d.items():
                        parts.append(json.dumps(k, separators=(',', ':'), ensure_ascii=False))
                        parts.append(':')
                        parts.extend(self.serialize_format_json(v, level+1))
                        if k != last_key: parts.append(',')
                        parts.append('\n')
                parts.append('}')
            case list():
                if parent_is_list:
                    parts.append(json.dumps(d, separators=(',', ':'), ensure_ascii=False))
                else:
                    parts.append("[\n")
                    for i, e in enumerate(d):
                        parts.extend(self.serialize_format_json(e, level+1, True))
                        if i < len(d) - 1: parts.append(',')
                        parts.append('\n')
                    parts.append(']')
            case _:
                parts.append(json.dumps(d, separators=(',', ':'), ensure_ascii=False))
        # return array if level isn't 0
        if level > 0:
            return parts
        else: # else the string
            return "".join(parts)

    # autosave task
    async def autosave(self : RPGMTL):
        while True:
            try:
                await asyncio.sleep(300) # call save() every 300s
                self.save()
            except asyncio.CancelledError:
                return

    # start the autosave task
    async def init_autosave(self : RPGMTL, app : web.Application):
        self.autosave_task = asyncio.create_task(self.autosave())

    # stop the autosave task
    async def stop_autosave(self : RPGMTL, app : web.Application):
        self.autosave_task.cancel()

    # check the projects folder and return a list of folder containing config.json files inside
    def load_project_list(self : RPGMTL) -> list[str]:
        try:
            if not os.path.isdir('projects'): # create folder if not found
                os.mkdir('projects')
            dirs : list[str] = []
            for d in os.walk('projects'): # walk inside
                try:
                    if os.path.isfile(d[0] + '/config.json'): # take note of folders with a config.json inside
                        dirs.append(d[0].replace('projects/', '').replace('projects\\', ''))
                except:
                    pass
            return dirs
        except:
            return []

    # function to search a game executable
    # name is the project name and is only in use in case we're updating the exe location
    def select_exe(self : RPGMTL, name : str|None = None) -> None|str:
        try:
            # create a Tkinter context for the dialog (make it as invisible as possible)
            root = Tk.Tk()
            root.title('RPGMTL Dialog')
            root.geometry('1x1')
            root.iconify()
            self.log.info("Opening executable selection dialog...")
            file_path = filedialog.askopenfilename(title="Select a Game Executable", filetypes=[("", ".exe")], parent=root).replace("\\", "/") # format windows backslash to forward slash
            root.destroy() # clear the window
            self.log.info("Dialog output is: " + file_path)
            if file_path == "" or file_path is None: # empty, user cancelled
                return None
            else:
                file_path = "/".join(file_path.split('/')[:-1]) # get the foler path from it
                if name is not None: # if updating existing location, we set it
                    self.projects[name]["path"] = file_path + "/"
                    self.modified[name] = True
                    self.log.info("Project " + name + " path is updated to " + file_path)
                return file_path # return the path
        except Exception as e:
            self.log.error("Error during selection of an executable for project " + name + "\n" + self.trbk(e))
            return None

    # Backup game files matching the plugin extensions for the given project name
    def backup_game_files(self : RPGMTL, pname : str) -> None:
        self.log.info("Copying game files for project " + pname + "...")
        dir_path : str = "projects/" + pname + "/originals/"
        # delete existing backup
        if os.path.isdir(dir_path):
            shutil.rmtree(dir_path)
        update_file_dict : dict[str, dict] = {}
        encountered_path : set[str] = set()
        # walk into the game folder
        for path, subdirs, files in os.walk(self.projects[pname]["path"]):
            for name in files:
                if name.split('.')[-1] in self.extensions: # file has a supported extension
                    # get the:
                    fp = os.path.join(path, name).replace('\\', '/') # full file path
                    fpr = fp.replace(self.projects[pname]["path"], '') # relative file path
                    target_dir = '/'.join(fpr.split('/')[:-1]) + '/' # relative directory containing the file
                    if target_dir == '/':
                        target_dir = ""
                    if target_dir not in encountered_path and not os.path.isdir(target_dir): # create directory if not found
                        encountered_path.add(target_dir)
                        try:
                            # create dir if needed
                            os.makedirs(os.path.dirname(dir_path + target_dir), exist_ok=True)
                        except Exception as e:
                            self.log.error("Couldn't create the following folder:" + dir_path + target_dir + "\n" + self.trbk(e))
                    # backup
                    try:
                        # file copy to project folder
                        shutil.copy(fp, dir_path + fpr)
                        # add to config.json
                        update_file_dict[fpr] = {
                            "ignored":False,
                            "strings":0,
                            "translated":0,
                            "disabled_strings":0
                        }
                        self.log.info(fpr + " has been copied to project folder " + pname)
                    except Exception as e:
                        self.log.error("Couldn't copy the following file:" + fp + " to project folder " + pname + "\n" + self.trbk(e))
        # keep file setting if it exists
        for k, v in self.projects[pname].get("files", {}).items():
            if k in update_file_dict:
                update_file_dict[k] = v
        # update and save
        self.projects[pname]["files"] = update_file_dict
        self.modified[pname] = True

    # create a blank new project
    def create_new_project(self : RPGMTL, path : str, name : str) -> tuple[bool, str]:
        try:
            # remove forbidden chara from project name
            name = name.replace('/', '').replace('<', '').replace('>', '').replace(':', '').replace('"', '').replace('\\', '').replace('|', '').replace('?', '').replace('*', '')
            # check folder exist or validity
            if name == "" or os.path.isdir('projects/' + name): # if already exists
                count = 0
                while True:
                    if not os.path.isdir('projects/' + name + str(count)): # try by adding a number
                        name += str(count) # increase number
                        break
                    count += 1
            for k in ['', '/edit']: # create needed folders
                try:
                    os.mkdir('projects/' + name + k)
                    self.log.info("projects/" + name + k + " has been created")
                except Exception as ex:
                    self.log.error("Couldn't create the following folder:" + name + k + "\n" + self.trbk(ex))
            # initialize config.json
            self.projects[name] = {
                "version":0,
                "settings":self.settings,
                "path":path + "/",
                "patches":{}
            }
            # backup files
            self.backup_game_files(name)
            # extract strings
            self.generate(name)
            # apply default translations and settings
            self.apply_default(name)
            # save
            self.save()
            return True, name
        except Exception as e:
            self.log.critical("Error while copying game files for project " + name + "\n" + self.trbk(e))
            return False, str(e)

    def apply_default(self : RPGMTL, name : str) -> None:
        # Applying default translation of common terms
        default_tl = {
            'レベル': 'Level',
            'Lv': 'Lv',
            'ＨＰ': 'HP',
            'HP': 'HP',
            'ＭＰ': 'MP',
            'MP': 'MP',
            'ＳＰ': 'SP',
            'SP': 'SP',
            'ＴＰ': 'TP',
            'TP': 'TP',
            '経験値': 'Experience',
            'EXP': 'EXP',
            '戦う': 'Fight',
            '逃げる': 'Run away',
            '攻撃': 'Attack',
            'の攻撃！': ' attacked!',
            '%1の攻撃！': '%1 attacked!',
            '防御': 'Defend',
            '連続攻撃': 'Continuous Attacks',
            '２回攻撃': 'Attack 2 times',
            '３回攻撃': 'Attack 3 times',
            '様子を見る': 'Observe',
            '様子見': 'Wait and See',
            'アイテム': 'Items',
            'スキル': 'Skill',
            '必殺技': 'Special',
            '装備': 'Equipment',
            'ステータス': 'Status',
            '並び替え': 'Sort',
            'セーブ': 'Save',
            'ゲーム終了': 'To Title',
            'オプション': 'Settings',
            '大事なもの': 'Key Items',
            'ニューゲーム': 'New Game',
            'コンティニュー': 'Continue',
            'タイトルへ': 'Go to Title',
            'やめる': 'Stop',
            '購入する': 'Buy',
            '売却する': 'Sell',
            '最大ＨＰ': 'Max HP',
            '最大ＭＰ': 'Max MP',
            '最大ＳＰ': 'Max SP',
            '最大ＴＰ': 'Max TP',
            '攻撃力': 'ATK',
            '防御力': 'DEF',
            '魔法力': 'M.ATK.',
            '魔法防御': 'M.DEF',
            '敏捷性': 'AGI',
            '運': 'Luck',
            '命中率': 'ACC',
            '回避率': 'EVA',
            '持っている数': 'Owned',
            'ヒール': 'Heal',
            'ファイア': 'Fire',
            'スパーク': 'Spark',
            '火魔法': 'Fire Magic',
            '氷魔法': 'Ice Magic',
            '雷魔法': 'Thunder Magic',
            '水魔法': 'Water Magic',
            '土魔法': 'Earth Magic',
            '風魔法': 'Wind Magic',
            '光魔法': 'Light Magic',
            '闇魔法': 'Dark Magic',
            '常時ダッシュ': 'Always run',
            'コマンド記憶': 'Command Memory',
            'タッチUI': 'Touch UI',
            'BGM 音量': 'BGM volume',
            'BGS 音量': 'BGS volume',
            'ME 音量': 'ME Volume',
            'SE 音量': 'SE volume',
            '所持数': 'Owned',
            '現在の%1': 'Current %1',
            '次の%1まで': 'Until next %1',
            'どのファイルにセーブしますか？': 'Which file do you want to save it to?',
            'どのファイルをロードしますか？': 'Which file do you want to load?',
            'ファイル': 'File',
            'オートセーブ': 'Auto Save',
            '%1たち': '%1',
            '%1が出現！': '%1 appeared!',
            '%1は先手を取った！': '%1 took the initiative!',
            '%1は不意をつかれた！': '%1 was caught off guard!',
            '%1は逃げ出した！': '%1 ran away!',
            'は逃げてしまった。': ' is running away.',
            'は身を守っている。': ' is on guard.',
            'は様子を見ている。': ' is watching the situation.',
            'は%1を唱えた！': ' casted %1!',
            'しかし逃げることはできなかった！': 'But escape is impossible!',
            '%1の勝利！': '%1 wins!',
            '%1は戦いに敗れた。': '%1 lost the battle.',
            '%1 の%2を獲得！': 'Obtained %1 %2s!',
            'お金を %1\\G 手に入れた！': 'Obtained %1 \\G!',
            '%1を手に入れた！': 'Obtained %1!',
            '%1は%2 %3 に上がった！': '%1 rose to %2 %3!',
            '%1を覚えた！': 'Learned %1!',
            '%1は%2を使った！': '%1 used %2!',
            '%1は身を守っている。': '%1 is defending.',
            '会心の一撃！！': 'A decisive blow!!',
            '痛恨の一撃！！': 'A painful blow!!',
            '%1は %2 のダメージを受けた！': '%1 received %2 damage!',
            '%1の%2が %3 回復した！': '%1\'s %2 recovered by %3!',
            '%1の%2が %3 増えた！': '%1\'s %2 increased by %3!',
            '%1の%2が %3 減った！': '%1\'s %2 decreased %3!',
            '%1は%2を %3 奪われた！': '%1 was robbed of %2 %3!',
            '%1はダメージを受けていない！': '%1 didn\'t receive any damage!',
            'ミス！\u3000%1はダメージを受けていない！': 'Miss! %1 didn\'t receive any damage!',
            '%1に %2 のダメージを与えた！': 'Inflicted %2 damage to %1!',
            '%1の%2を %3 奪った！': '%2 of %1 was stolen from %3!',
            '%1にダメージを与えられない！': 'Cannot damage %1!',
            'ミス！\u3000%1にダメージを与えられない！': 'Miss! Can\'t damage %1!',
            '%1は攻撃をかわした！': '%1 dodged the attack!',
            '%1は魔法を打ち消した！': '%1 canceled the magic!',
            '%1は魔法を跳ね返した！': '%1 reflected the magic!',
            '%1の反撃！': "%1's counterattack!", '%1が%2をかばった！': '%1 protected %2!',
            '%1の%2が上がった！': '%1\'s %2 increased!',
            '%1の%2が下がった！': '%1\'s %2 decreased!',
            '%1の%2が元に戻った！': '%1\'s %2 is back to normal!',
            '%1には効かなかった！': '%1 is unaffected!',
            'は倒れた！': ' has fallen!',
            'を倒した！': ' has been defeated!',
            '%1を倒した！': '%1 has been defeated!',
            '%1は倒れた！': '%1 has collapsed!',
            'は立ち上がった！': ' has stood up!',
            '%1は立ち上がった！': '%1 has stood up!',
            '戦闘不能': 'Incapacited',
            '不死身': 'Immortality',
            'は毒にかかった！': ' is poisoned!',
            'に毒をかけた！': ' has been poisoned!',
            'の毒が消えた！': ' isn\'t poisoned anymore!',
            '毒': 'Poison',
            'は暗闇に閉ざされた！': ' is engulfed in darkness!',
            'を暗闇に閉ざした！': ' has been engulfed in darkness!',
            'の暗闇が消えた！': ' is free from the darkness!',
            '暗闇': 'Darkness',
            'は沈黙した！': ' is silenced!',
            'を沈黙させた！': ' has been silenced!',
            'の沈黙が解けた！': ' isn\'t silenced anymore!',
            '沈黙': 'Silence',
            'は激昂した！': ' is enraged!',
            'を激昂させた！': ' has been enraged!',
            'は我に返った！': ' got their senses back!',
            '激昂': 'Enraged',
            'は魅了された！': ' is captivated!',
            'を魅了した！': ' has been charmed!',
            '魅了': 'Charm',
            'は眠った！': ' is asleep!',
            'を眠らせた！': ' has been put to sleep!',
            'は眠っている。': ' is asleep.',
            'は目を覚ました！': ' woke up!',
            '睡眠': 'Sleep',
            'はい': 'Yes',
            'いいえ': 'No',
            '一般防具':'Medium Armor',
            '魔法防具':'Magic Armor',
            '軽装防具':'Light Armor',
            '重装防具':'Heavy Armor',
            '小型盾':'Small Shield',
            '大型盾':'Large Shield',
            '短剣':'Dagger',
            '剣':'Sword',
            'フレイル':'Flail',
            '斧':'Axe',
            'ムチ':'Whip',
            '杖':'Staff',
            '弓':'Bow',
            'クロスボウ':'Crossbow',
            '銃':'Gun',
            '爪':'Claw',
            'グローブ':'Gloves',
            '槍':'Spear',
            'Ｇ':'G',
            '物理':'Physics',
            '炎':'Fire',
            '氷':'Ice',
            '雷':'Thunder',
            '水':'Water',
            '土':'Earth',
            '風':'Wind',
            '光':'Light',
            '闇':'Dark',
            '盾':'Shield',
            '武器':'Weapon',
            '頭':'Head',
            '身体':'Body',
            '装飾品':'Accessories',
            '魔法':'Magic',
            '特殊行動':'Special',
            'ステート':'State',
            'レベル':'Level',
            '気力':'Energy',
            '並び替え':'Sort',
            '防具':'Armor',
            '最強装備':'Optimize',
            '全て外す':'Remove all',
            'ja_JP':'en_US'
        }
        for s in self.strings[name]["strings"]:
            if self.strings[name]["strings"][s][0] in default_tl:
                self.strings[name]["strings"][s][1] = default_tl[self.strings[name]["strings"][s][0]]
                self.modified[name] = True
        # Disabling common unrelated files by default
        ignored_starts = [
            "data/Animations.json", "data/MapInfos.json", "data/Tilesets.json", "package.json", "js/plugins/", "js/libs/", "js/main.js", "js/rpg_core.js", "js/rpg_managers.js", "js/rpg_objects.js", "js/rpg_scenes.js", "js/rpg_sprites.js", "js/rpg_windows.js", "js/rmmz_core.js", "js/rmmz_managers.js", "js/rmmz_objects.js", "js/rmmz_scenes.js", "js/rmmz_sprites.js", "js/rmmz_windows.js",
            "www/data/Animations.json", "www/data/MapInfos.json", "www/data/Tilesets.json", "www/package.json", "www/js/plugins/", "www/js/libs/", "www/js/main.js", "www/js/rpg_core.js", "www/js/rpg_managers.js", "www/js/rpg_objects.js", "www/js/rpg_scenes.js", "www/js/rpg_sprites.js", "www/js/rpg_windows.js", "www/js/rmmz_core.www/js", "www/js/rmmz_managers.www/js", "www/js/rmmz_objects.www/js", "www/js/rmmz_scenes.www/js", "www/js/rmmz_sprites.www/js", "www/js/rmmz_windows.www/js",
            "Data/Animations.rxdata", "Data/MapInfos.rxdata", "Data/Tilesets.rxdata",
            "Data/Animations.rvdata", "Data/MapInfos.rvdata", "Data/Tilesets.rvdata",
            "Data/Animations.rvdata2", "Data/MapInfos.rvdata2", "Data/Tilesets.rvdata2",
        ]
        for f in self.projects[name]["files"]:
            for i in ignored_starts:
                if f.startswith(i):
                    self.projects[name]["files"][f]["ignored"] = True
                    self.modified[name] = True
                    break
        # Disable RPG Maker switches, variables and others
        for f in ["www/data/System.json", "data/System.json"]:
            if f in self.strings[name]["files"]:
                for i, g in enumerate(self.strings[name]["files"][f]):
                    if g[0] in ['switches', 'variables', 'encryptionKey']:
                        for j in range(1, len(g)):
                            self.strings[name]["files"][f][i][j][3] = 1
                            self.modified[name] = True
        # Disabling specific RPG maker event codes or groups
        text_codes = set(["Command: Show Text", "Command: Choices", "Command: When ..."]) # allowed ones
        other_groups = set(["formula", "note", "@icon_name", "@battler_name"])
        for f in self.strings[name]["files"]:
            for i, group in enumerate(self.strings[name]["files"][f]):
                if (group[0].startswith("Command: ") and group[0] not in text_codes) or group[0] in other_groups:
                    for j in range(1, len(group)):
                        self.strings[name]["files"][f][i][j][3] = 1
                        self.modified[name] = True
        # Disable number/boolean strings
        strids = set()
        for k, v in self.strings[name]["strings"].items():
            if v[0] in ["True", "true", "False", "false"]: # bool check
                strids.add(k)
                continue
            try: # number check
                float(v[0])
                strids.add(k)
            except:
                pass
        for f in self.strings[name]["files"]:
            for i, group in enumerate(self.strings[name]["files"][f]):
                for j in range(1, len(group)):
                    if group[j][0] in strids:
                        self.strings[name]["files"][f][i][j][3] = 1
                        self.modified[name] = True

    # load a project config.json file
    def load_project(self : RPGMTL, name : str) -> dict[str, Any]:
        try:
            if name not in self.projects:
                with open('projects/' + name + '/config.json', mode='r', encoding='utf-8') as f:
                    self.projects[name] = json.load(f)
            return self.projects[name]
        except:
            return None

    # load a project strings.json file
    def load_strings(self : RPGMTL, name : str) -> dict[str, Any]:
        try:
            if name not in self.strings:
                with open('projects/' + name + '/strings.json', mode='r', encoding='utf-8') as f:
                    self.strings[name] = json.load(f)
            return self.strings[name]
        except:
            return None

    # backup a project strings.json file and backups
    def backup_strings_file(self : RPGMTL, name : str) -> None:
        fns : list[str] = ["strings.bak-5.json", "strings.bak-4.json", "strings.bak-3.json", "strings.bak-2.json", "strings.bak-1.json", "strings.json"]
        for i in range(1, len(fns)):
            try:
                shutil.copyfile('projects/' + name + '/' + fns[i], 'projects/' + name + '/' + fns[i-1])
            except:
                pass

    # extract strings from backed up files
    def generate(self : RPGMTL, name : str) -> int:
        self.save() # save first!
        self.backup_strings_file(name) # backup strings.json
        self.load_strings(name) # load strings.json
        self.log.info("Extracting strings for project " + name + "...")
        
        # start
        reverse_strings : dict[str, str] = {}
        str_id : int = 0
        update_run_flag : int = 0
        # keep copy of existing ones (if any)
        try:
            index = copy.deepcopy(self.strings[name])
            for k in index["strings"]:
                str_id = max(str_id, int(k)+1) # calculate last id
                reverse_strings[index["strings"][k][0]] = k # keep track of string and its id in a reverse lookup table
                index["strings"][k][2] = 0 # set occurence to 0
            old = index["files"] # put old files here
            index["files"] = {}
            self.log.info("Previous copy of projects/" + name + "/strings.json will be used")
            update_run_flag = 1
        except Exception as e:
            self.log.warning("The following error occured while loading existing strings (Ignore if it's a fresh project):\n" + self.trbk(e))
            index = {
                "strings":{},
                "files":{}
            }
            old = {}
            reverse_strings = {}
            str_id = 0
            self.log.info("projects/" + name + "/strings.json will be generated from scratch")
        # go over each files
        err : int = 0
        for f in self.projects[name]['files']:
            try:
                self.projects[name]['files'][f]["strings"] = 0
                for p in self.plugins.values():
                    if p.match(f, False): # this file match with the plugin
                        p.reset() # reset plugin state
                        p.set_settings(self.settings | self.projects[name]['settings']) # and set setting
                        index["files"][f] = []
                        # read the content
                        with open('projects/' + name + '/originals/' + f, mode="rb") as infile:
                            content = infile.read()
                        # has the plugin read it
                        for group in p.read(f, content):
                            # process group content
                            for i in range(1, len(group)):
                                s : str = group[i]
                                group[i] = [str(str_id), None, 0, 0, update_run_flag] # id, indiv_tl, unlinked, ignored, modified/new
                                self.projects[name]['files'][f]["strings"] += 1
                                # if string already occured
                                if s in reverse_strings:
                                    group[i][0] = reverse_strings[s] # get its id
                                    index["strings"][reverse_strings[s]][2] += 1 # increase occurence count
                                else:
                                    reverse_strings[s] = str(str_id) # new id
                                    index["strings"][str(str_id)] = [s, None, 1]
                                    str_id += 1 # increase for next id
                            index["files"][f].append(group)
                        break
            except Exception as e:
                err += 1
                self.log.error("Failed to extract strings from " + f + " for project " + name + "\n" + self.trbk(e))
        if update_run_flag:
            self.log.info("Matching with the previous strings of " + name + "...")
            # check old file and retrieve old strings
            for k in index["files"]:
                if len(index["files"][k]) == 0:
                    continue
                if k in old:
                    # list new strings
                    A : list[str] = []
                    A_index : list[tuple[int, int]] = []
                    for i, g in enumerate(index["files"][k]):
                        for j in range(1, len(g)):
                            A.append(g[j][0])
                            A_index.append((i, j))
                    # list old strings
                    B : list[str] = []
                    B_index : list[tuple[int, int]] = []
                    for i, g in enumerate(old[k]):
                        for j in range(1, len(g)):
                            B.append(g[j][0])
                            B_index.append((i, j))
                    # compare the lists
                    blocks = difflib.SequenceMatcher(a=A, b=B).get_matching_blocks()
                    for block in blocks:
                        for i in range(block.size):
                            xyA : tuple[int, int] = A_index[block.a+i]
                            xyB : tuple[int, int] = B_index[block.b+i]
                            index["files"][k][xyA[0]][xyA[1]] = old[k][xyB[0]][xyB[1]] # match old to new (to keep individual translations and settings)
        # set new string table
        self.strings[name] = index
        # increase project version
        self.projects[name]["version"] = self.projects[name].get("version", -1) + 1
        # start computing completion
        asyncio.create_task(self.compute_translated(name, self.projects[name]["version"]))
        # set save flag
        self.modified[name] = True
        self.log.info("Strings extraction for project " + name + " completed")
        return err

    # calculate number of translated lines
    async def compute_translated(self : RPGMTL, name : str, version : int) -> None:
        if version <= self.computing.get(name, -1):
            return
        self.computing[name] = version
        self.log.info("Computing the translation completion for project " + name + "...")
        mismatch_flag : bool = False
        for f in self.strings[name]["files"]:
            await asyncio.sleep(0.1)
            # check if still valid
            if version != self.projects[name]["version"]:
                self.log.info("Aborting computing of the translation completion for project " + name + "...")
                return
            # check for inconsistency
            if f not in self.projects[name]['files']:
                mismatch_flag = True
                continue
            # reset
            prev = self.projects[name]['files'][f]["translated"]
            self.projects[name]['files'][f]["translated"] = 0
            self.projects[name]['files'][f]["disabled_strings"] = 0
            # go over each string in file
            for g in self.strings[name]["files"][f]:
                for i in range(1, len(g)):
                    if g[i][3]:
                        self.projects[name]['files'][f]["disabled_strings"] += 1
                    elif (g[i][2] and g[i][1] is not None) or self.strings[name]["strings"][g[i][0]][1] is not None:
                        self.projects[name]['files'][f]["translated"] += 1
            if prev != self.projects[name]['files'][f]["translated"]:
                self.modified[name] = True
        if self.computing.get(name, -1) == version:
            self.computing.pop(name, None)
        if mismatch_flag:
            self.log.warning("Mismatch detected between project " + name + " config and strings, extracting the strings again might fix this issue, the translation percentages won't be accurate")
        else:
            self.log.info("Computing the translation completion for project " + name + " is complete and up-to-date")

    def get_list_of_update_string_index(self : RPGMTL, name : str, path : str, group : int, index : int, local : bool) -> list[int]:
        # this function checks what string(s) got changed for the given parameters
        # and return a list of index which should match the script.js strcachetable
        pos : int = 0
        if local: # for local edits
            for i in range(0, group):
                pos += len(self.strings[name]["files"][path][i]) - 1
            pos += index - 1
            return [pos]
        else: # for global edits
            sid : str = self.strings[name]["files"][path][group][index][0]
            positions : list[int] = []
            for g in self.strings[name]["files"][path]:
                for i in range(1, len(g)):
                    if g[i][0] == sid:
                        positions.append(pos)
                    pos += 1
            return positions

    # create the folder(s) needed for given path
    def mkdir_path_folder(self : RPGMTL, fn : str) -> None:
        Path('/'.join(fn.split('/')[:-1])).mkdir(parents=True, exist_ok=True)

    # release game patch
    def create_release(self : RPGMTL, name : str) -> tuple[int, int]:
        err : int = 0
        # clean existing folder
        if os.path.isdir('projects/' + name + '/release'):
            try:
                shutil.rmtree('projects/' + name + '/release')
                self.log.info("Cleaned up projects/" + name + "/release")
            except Exception as e:
                self.log.error("Failed to properly clean projects/" + name + "/release\n" + self.trbk(e))
                err += 1
        # load strings if not loaded
        self.load_strings(name)
        self.log.info("Patching files for project " + name + "...")
        # for each file
        patch_count : int = 0
        for f in self.projects[name]["files"]:
            if self.projects[name]["files"][f]["ignored"]: # skip ignored
                continue
            with open('projects/' + name + '/originals/' + f, mode="rb") as iofile:
                content = iofile.read()
            for p in self.plugins.values():
                try:
                    if len(self.strings[name]["files"][f]) == 0:
                        continue
                    if p.match(f, False): # file matches the plugin
                        p.reset()
                        p.set_settings(self.settings | self.projects[name]['settings'])
                        content, modified = p.write(f, content, self.strings[name]) # write content
                        content, modified = self.apply_fixes(name, f, content, modified) # apply fixes
                        # write file if modified
                        if modified:
                            content = p.format(f, content)
                            self.mkdir_path_folder('projects/' + name + '/release/' + f) # create folder first
                            with open('projects/' + name + '/release/' + f, mode="wb") as iofile:
                                iofile.write(content)
                            patch_count += 1
                except Exception as e:
                    self.log.error("Failed to patch strings in " + f + " for project " + name + " using the plugin " + p.name + "\n" + self.trbk(e))
                    err += 1
        # Copy edit content
        if os.path.isdir('projects/' + name + '/edit'):
            try:
                self.log.info("Copying the content of the edit folder for project " + name + "...")
                for path, subdirs, files in os.walk('projects/' + name + '/edit'):
                    for f in files:
                        fn = os.path.join(path, f)
                        Path(path.replace('projects/' + name + '/edit', 'projects/' + name + '/release')).mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(fn, fn.replace('projects/' + name + '/edit', 'projects/' + name + '/release'))
                        self.log.info("Copied edit/" + f + " for project " + name + "...")
            except:
                self.log.warning("Failed to copy the content of the edit folder for project " + name)
        if patch_count > 0:
            self.log.info("Patched {} files for project {} available in the release folder".format(patch_count, name))
        else:
            self.log.info("No patched {} files for project {}".format(patch_count, name))
        return patch_count, err

    # execute and apply runtime fix/patch
    def apply_fixes(self : RPGMTL, _name_ : str, _file_path_ : str, _content_ : bytes, _modified_ : bool) -> tuple[bytes, bool]:
        # variables got underscore on purpose, as the patch is executed in this context
        for _k_, _v_ in self.projects[_name_]["patches"].items(): # iterate over existing patches
            if _k_ in _file_path_: # if this patch matches this file
                try:
                    helper = PatcherHelper(_content_) # create helped with file content
                    exec(_v_) # run patch
                    if helper.modified: # check if modified flag has been raised
                        _modified_ = True # set our own modified flag
                        _content_ = helper._content_ # and replace the content with the new one
                        self.log.info("Applied fix " + _k_ + " on file " + _file_path_ + " for project " + _name_)
                except Exception as _e_:
                    self.log.error("Failed to apply the fix " + _k_ + " on file " + _file_path_ + " for project " + _name_ + "\n" + self.trbk(_e_))
        # return content (either old or new modified one) and modified flag
        return _content_, _modified_

    # Function to import strings from old RPGMTL formats (version 1 and 2)
    # Return value is a tuple of state (-1 = error occured, 0 = nothing, 1 = success) and the imported string count
    def import_old_data(self : RPGMTL, name : str) -> tuple[int, int]:
        try:
            count : int = 0
            self.load_strings(name)
            # create Tkinter context
            root = Tk.Tk()
            root.title('RPGMTL Dialog')
            root.geometry('1x1')
            root.iconify()
            file_path = filedialog.askopenfilename(title="Select an old RPGMTL strings file", filetypes=[("strings", ".json"), ("strings", ".py")], parent=root).replace("\\", "/") # change windows backslash to forward slash
            root.destroy()
            if file_path == "" or file_path is None:
                return 0, 0
            # backup project strings.json
            self.backup_strings_file(name)
            # read file
            with open(file_path, mode="rb") as f:
                data = f.read()
            if file_path.endswith(".json"): # old format 1
                data = json.loads(data.decode("utf-8"))
                if len(data) == 2 and "strings" in data: # very old format
                    ref = data["strings"]
                else:
                    ref = data
            elif file_path.endswith(".py"): # old format 2
                ref = {}
                for line in data.decode("utf-8").split('\n'):
                    try:
                        d = json.loads("{"+line+"}")
                        if not isinstance(d, dict):
                            raise Exception()
                        key = list(d.keys())[0]
                        ref[key] = d[key]
                    except:
                        pass
            else:
                return
            # go over our strings and match the strings we found
            for k, v in self.strings[name]["strings"].items():
                if v[1] is None and isinstance(ref.get(v[0], None), str):
                    self.strings[name]["strings"][k][1] = ref[v[0]]
                    count += 1
            if count > 0:
                # increase project version
                self.projects[name]["version"] = self.projects[name].get("version", -1) + 1
                self.modified[name] = True
                # start computing completion
                asyncio.create_task(self.compute_translated(name, self.projects[name]["version"]))
            return 1, count
        except:
            return -1, count

    # Function to import strings from RPGMaker Trans formats (version 3)
    # Return value is a tuple of state (-1 = error occured, 0 = nothing, 1 = success) and the imported string count
    # Documentation: https://rpgmakertrans.bitbucket.io/patchformatv3.html
    def import_rpgmtrans_data(self : RPGMTL, name : str) -> tuple[int, int]:
        try:
            count : int = 0
            self.load_strings(name)
            multiline_ruby = (self.settings | self.projects[name]["settings"]).get("rm_marshal_multiline", False)
            # create Tkinter context
            root = Tk.Tk()
            root.title('RPGMTL Dialog')
            root.geometry('1x1')
            root.iconify()
            file_path = filedialog.askopenfilename(title="Select a RPGMKTRANSPATCH file", filetypes=[("", "RPGMKTRANSPATCH")], parent=root).replace("\\", "/") # change windows backslash to forward slash
            root.destroy()
            if file_path == "" or file_path is None:
                return 0, 0
            # backup project strings.json
            self.backup_strings_file(name)
            file_path = "/".join(file_path.split("/")[:-1]) 
            patch_path : str = file_path + "/patch"
            table = {}
            for d in os.walk(file_path):
                if d[0].replace("\\", "/") == patch_path:
                    for p in d[2]:
                        # open file
                        with open(d[0] + '/' + p, mode="r", encoding="utf-8") as f:
                            lines : list[str] = f.read().splitlines()
                        # check first line according to documentation
                        if not lines[0].startswith("> RPGMAKER TRANS PATCH FILE VERSION 3"):
                            self.log.error("Invalid identifier for expected RPGMaker Trans File " + p + ", skipping...")
                            continue
                        i : int = 1
                        while i < len(lines): # go over check line
                            if lines[i] == "> BEGIN STRING": # look for this string
                                # containers for string lines
                                original : list[str] = []
                                translation : list[str] = []
                                i += 1
                                while i < len(lines) and not lines[i].startswith("> CONTEXT: "): # append to original until we meet context
                                    original.append(lines[i])
                                    i += 1
                                if i >= len(lines) or lines[i].endswith(" < UNTRANSLATED"): # if untranslated, skip the rest
                                    continue
                                is_inline_script : bool = False
                                if i < len(lines) and "InlineScript" in lines[i]: # detect RPG Maker inline scripts (see below)
                                    is_inline_script = True
                                while i < len(lines) and lines[i].startswith("> CONTEXT: "): # ignore further context strings
                                    i += 1
                                while i < len(lines) and (lines[i] != "> END STRING" and not lines[i].startswith("> CONTEXT: ")): # append to translation until we meet END or CONTEXT (multi context translations aren't supported)
                                    translation.append(lines[i])
                                    i += 1
                                if p == "Scripts.txt" or is_inline_script: # exception for Script strings and inline script
                                    for j in range(len(original)):
                                        if original[j].startswith('"') and original[j].endswith('"'): # remove quotes around the string
                                            original[j] = original[j][1:-1]
                                    for j in range(len(translation)):
                                        if translation[j].startswith('"') and translation[j].endswith('"'):
                                            translation[j] = translation[j][1:-1]
                                # Remove double escape and escape #
                                for j in range(len(original)):
                                    original[j] = original[j].replace("\\#", "#").replace("\\\\", "\\")
                                for j in range(len(translation)):
                                    translation[j] = translation[j].replace("\\#", "#").replace("\\\\", "\\")
                                i += 1
                                # Add to the table
                                # Behavior changes according to the RM Marshal plugin project setting
                                if multiline_ruby: # in this one, we join together into a single string
                                    jori : str = "\n".join(original)
                                    if jori in table:
                                        continue # skip
                                    else:
                                        table[jori] = "\n".join(translation)
                                else: # else we treat each line as a separate string
                                    # put array to same size
                                    if len(translation) > len(original):
                                        translation[len(original)-1] = "\n".join(translation[len(original)-1:])
                                    while len(translation) < len(original):
                                        translation.append("")
                                    for j in range(len(original)):
                                        if original[j] not in table:
                                            table[original[j]] = translation[j]
                            else: # else go to next line
                                i += 1
                    break
            checked = set()
            for f in self.strings[name]["files"]:
                for g, group in enumerate(self.strings[name]["files"][f]):
                    for i in range(1, len(group)):
                        sid = group[i][0]
                        if sid not in checked:
                            checked.add(sid)
                            if self.strings[name]["strings"][sid][1] is None:
                                if self.strings[name]["strings"][sid][0] in table:
                                    self.strings[name]["strings"][sid][1] = table[self.strings[name]["strings"][sid][0]]
                                    count += 1
                                elif group[0] == "Command: Script": # inline Script
                                    s : list[str] = self.strings[name]["strings"][sid][0].split('"')
                                    changed : bool = False
                                    for j in range(1, len(s), 2):
                                        if s[j] in table:
                                            s[j] = table[s[j]]
                                            changed = True
                                    if changed:
                                        self.strings[name]["strings"][sid][1] = '"'.join(s)
                                        count += 1
            if count > 0:
                # increase project version
                self.projects[name]["version"] = self.projects[name].get("version", -1) + 1
                self.modified[name] = True
                # start computing completion
                asyncio.create_task(self.compute_translated(name, self.projects[name]["version"]))
            return 1, count
        except Exception as e:
            self.log.error("The following exception occured in import_rpgmtrans_data():\n" + self.trbk(e))
            return -1, count

    # Return the file list and folder list inside a project folder
    def get_folder_content(self : RPGMTL, name : str, path : str) -> tuple[dict[str, bool], list[str]]:
        files : dict[str, bool] = {}
        folders : list[str] = []
        if path != "":
            folders.append("..")
        lp : int = len(path)
        self.load_strings(name)
        for f in self.strings[name]["files"]:
            if f.startswith(path):
                if '/' not in f[lp:]:
                    files[f] = self.projects[name]["files"][f]["ignored"] if f in self.projects[name]["files"] else False
                else:
                    d : str = (path + f[lp:].split('/')[0] if path != "" else f[lp:].split('/')[0]) + "/"
                    if d not in folders:
                        folders.append(d)
        files_keys = list(files.keys())
        files_keys.sort()
        files = {k : files[k] for k in files_keys}
        folders.sort()
        return files, folders

    # Start RPGMTL and run the server
    def run(self : RPGMTL) -> None:
        # Parse command line
        parser : argparse.ArgumentParser = argparse.ArgumentParser(prog="rpgmtl.py")
        command = parser.add_argument_group('command', 'Optional commands')
        command.add_argument('-s', '--https', help="provide paths to your SSL certificate and key", nargs=2, default=None)
        command.add_argument('-n', '--http', help="clear SSL certificate settings and force HTTP", action='store_const', const=True, default=False, metavar='')
        args : argparse.Namespace = parser.parse_args()
        
        # Check HTTPS/SSL
        ssl_context = None
        if args.http:
            if "https_cert" in self.settings:
                self.settings.pop("https_cert")
                self.settings_modified = True
                self.log.info("SSL settings have been deleted")
        else:
            if args.https is not None:
                try:
                    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                    ssl_context.load_cert_chain(args.https[0], args.https[1])
                    self.settings["https_cert"] = [args.https[0], args.https[1]]
                    self.settings_modified = True
                except:
                    ssl_context = None
            if ssl_context is None and "https_cert" in self.settings:
                try:
                    ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                    ssl_context.load_cert_chain(self.settings["https_cert"][0], self.settings["https_cert"][1])
                except:
                    ssl_context = None
        if ssl_context is not None:
            self.log.info("SSL is enabled")
            
        # Init
        self.load_project_list()
        
        # Start
        try:
            web.run_app(self.app, port=8000, shutdown_timeout=0, ssl_context=ssl_context)
        except Exception as e: # Ctrl+C is enough to trigger it
            self.log.warning("The following exception occured:\n" + self.trbk(e))
        self.log.info("RPGMTL is shutting down...")
        
        # Ssave on quit
        self.save()

    ######################################################
    # Request Responses start here
    ######################################################

    # Request the HTML page
    async def page(self : RPGMTL, request : web.Request) -> web.Response:
        return web.FileResponse('./assets/ui/index.html')

    # Request the javascript
    async def script(self : RPGMTL, request : web.Request) -> web.Response:
        return web.FileResponse('./assets/ui/script.js')

    # Request the stylesheet
    async def style(self : RPGMTL, request : web.Request) -> web.Response:
        return web.FileResponse('./assets/ui/style.css')

    # Request the favicon
    async def favicon(self : RPGMTL, request : web.Request) -> web.Response:
        return web.FileResponse('./assets/ui/favicon.ico')

    # /api/main
    async def project_list(self : RPGMTL, request : web.Request) -> web.Response:
        l : list[str] = self.load_project_list()
        self.log.info("A list of " + str(len(l)) + " project(s) has been sent to an user")
        return web.json_response({"result":"ok", "data":{"list":l, "verstring":self.VERSION}})

    # /api/shutdown
    async def shutdown(self : RPGMTL, request : web.Request) -> web.Response:
        loop = asyncio.get_event_loop()
        loop.call_later(0.2, loop.stop)
        return web.json_response({"result":"ok", "data":{}}, status=200)

    # /api/update_location
    async def select_project_exe(self : RPGMTL, request : web.Request) -> web.Response:
        try:
            payload = await request.json()
        except:
            payload = {}
        name = payload.get('name', None)
        file_path = self.select_exe(name)
        if name is None: # new project
            return web.json_response({"result":"ok", "data":{"path":file_path}, "message":"Please select a project name."})
        else: # update existing project
            if file_path is not None:
                self.backup_game_files(name)
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}, "message":"The project has been updated, please extract the strings"})

    # /api/new_project
    async def create_project(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        path = payload.get('path', None)
        name = payload.get('name', None)
        if path is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'path' parameter."}, status=400)
        elif name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter."}, status=400)
        else:
            flag, string = self.create_new_project(path, name)
            if flag:
                return  web.json_response({"result":"ok", "data":{"name":string, "config":self.projects[string]}})
            else:
                return  web.json_response({"result":"bad", "message":string}, status=500)

    # /api/open_project
    async def get_project(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter."}, status=400)
        else:
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.load_project(name)}})

    # /api/translator
    async def get_translator(self : RPGMTL, request : web.Request) -> web.Response:
        try:
            payload = await request.json()
        except:
            payload = {}
        name = payload.get('name', None)
        current : str = self.get_current_translator(name)[0]
        if "rpgmtl_current_translator" not in self.settings:
            return web.json_response({"result":"bad", "message":"No Translator Plugins loaded"}, status=400)
        translators : list[str] = list(self.translators.keys())
        if name is None:
            return web.json_response({"result":"ok", "data":{"list":translators, "current":current}})
        else:
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name], "list":translators, "current":current}})

    # /api/update_translator
    async def update_translator(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        value = payload.get('value', None)
        if name is None and value is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'value' parameter"}, status=400)
        elif value is not None and value not in self.translators:
            return web.json_response({"result":"bad", "message":"Bad request, invalid 'value' parameter"}, status=400)
        if name is None:
            self.settings["rpgmtl_current_translator"] = value
            self.settings_modified = True
            return web.json_response({"result":"ok", "data":{}})
        else:
            if value is None:
                if "rpgmtl_current_translator" in self.projects[name]["settings"]:
                    self.projects[name]["settings"].pop("rpgmtl_current_translator")
            else:
                self.projects[name]["settings"]["rpgmtl_current_translator"] = value
            self.modified[name] = True
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}})

    # /api/settings
    async def get_settings(self : RPGMTL, request : web.Request) -> web.Response:
        try:
            payload = await request.json()
        except:
            payload = {}
        name = payload.get('name', None)
        settings = copy.deepcopy(self.settings)
        if name is None:
            return web.json_response({"result":"ok", "data":{"layout":self.setting_menu, "settings":settings, "descriptions":self.plugin_descriptions}})
        else:
            settings = settings | self.projects[name].get("settings", {})
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name], "layout":self.setting_menu, "settings":settings, "descriptions":self.plugin_descriptions}})
        
    # /api/update_settings
    async def update_setting(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        key = payload.get('key', None)
        value = payload.get('value', None)
        if name is None and (key is None or key not in self.settings):
            return web.json_response({"result":"bad", "message":"Bad request, missing 'key' parameter"}, status=400)
        elif name is None and value is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'value' parameter"}, status=400)
        for f in self.setting_menu:
            if key in self.setting_menu[f]:
                try:
                    match self.setting_menu[f][key][1]:
                        case "str":
                            if not isinstance(value, str):
                                raise Exception()
                        case "bool":
                            if not isinstance(value, bool):
                                raise Exception()
                        case "num":
                            try:
                                value = float(value)
                            except:
                                value = int(value)
                except:
                    return web.json_response({"result":"bad", "message":"Invalid 'value' parameter, couldn't convert to setting type"}, status=400)
                break
        if name is None:
            self.settings[key] = value
            self.settings_modified = True
            return web.json_response({"result":"ok", "data":{"settings":self.settings}})
        else:
            if key is None:
                self.projects[name]["settings"] = {}
            else:
                self.projects[name]["settings"][key] = value
            self.modified[name] = True
            settings = self.settings | self.projects[name]["settings"]
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name], "settings":settings}})

    # /api/extract
    async def generate_project(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter."}, status=400)
        else:
            err = self.generate(name)
            self.save()
            message = "Strings extracted, but {} error(s) occured.".format(err) if err > 0 else "Strings extracted with success."
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}, "message":message})

    # /api/release
    async def release(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        else:
            patch_count, err = self.create_release(name)
            if patch_count > 0:
                message = "Patch generated in projects/{}/release, but {} error(s) occured.".format(name, err) if err > 0 else "Patch generated in projects/{}/release with success.".format(name)
            else:
                message = "No files patched and {} error(s) occured.".format(err) if err > 0 else "No files patched."
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}, "message":message})

    # /api/patches
    async def open_patches(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        else:
            l : list[str] = list(self.projects[name]["patches"].keys())
            l.sort()
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}})

    # /api/open_patch
    async def edit_patch(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        key = payload.get('key', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        elif key is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'key' parameter"}, status=400)
        else:
            return web.json_response({"result":"ok", "data":{"key":key, "name":name, "config":self.projects[name]}})

    # /api/update_patch
    async def update_patch(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        key = payload.get('key', None)
        newkey = payload.get('newkey', None)
        code = payload.get('code', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        else:
            if key is not None and key in self.projects[name]["patches"]:
                self.projects[name]["patches"].pop(key)
            if newkey is not None and code is not None:
                self.projects[name]["patches"][newkey] = code
                l : list[str] = list(self.projects[name]["patches"].keys())
                l.sort()
            self.modified[name] = True
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}})
        
    # /api/import
    async def import_old(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        else:
            state, count = self.import_old_data(name)
            match state:
                case 1:
                    return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}, "message":"Imported {} string(s) with success".format(count)})
                case -1:
                    return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}, "message":"Imported {} string(s), but an error occured".format(count)})
                case _:
                    return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}})
        
    # /api/import_rpgmtrans
    async def import_rpgmtrans(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        else:
            state, count = self.import_rpgmtrans_data(name)
            match state:
                case 1:
                    return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}, "message":"Imported {} string(s) with success".format(count)})
                case -1:
                    return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}, "message":"Imported {} string(s), but an error occured".format(count)})
                case _:
                    return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}})

    # /api/backups
    async def backup_list(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        else:
            targets : set[str] = set(["strings.bak-1.json", "strings.bak-2.json", "strings.bak-3.json", "strings.bak-4.json", "strings.bak-5.json"]) 
            l : list[list] = []
            with os.scandir("projects/" + name) as it:
                for item in it:
                    if item.name in targets:
                        l.append([item.name, item.stat().st_size, item.stat().st_mtime])
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name], "list":l}})
        
    # /api/load_backup
    async def load_backup(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        file = payload.get('file', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        elif file is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'file' parameter"}, status=400)
        else:
            self.save() # save
            shutil.copyfile('projects/' + name + '/' + file, 'projects/' + name + '/backup.tmp.file.json')
            bak : list[str] = ["strings.bak-5.json", "strings.bak-4.json", "strings.bak-3.json", "strings.bak-2.json", "strings.bak-1.json", "strings.bak.json"]
            meet : bool = False
            for i in range(0, len(bak)):
                if bak[i] == file:
                    meet = True
                    continue
                elif not meet:
                    continue
                else:
                    try:
                        shutil.copyfile('projects/' + name + '/' + bak[i], 'projects/' + name + '/' + bak[i-1])
                    except:
                        pass
            shutil.copyfile('projects/' + name + '/backup.tmp.file.json', 'projects/' + name + '/strings.json')
            self.projects[name]["version"] = self.projects[name].get("version", -1) + 1
            self.modified[name] = True
            self.strings.pop(name, None)
            self.load_strings(name)
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name]}, "message":"strings.json has been renamed strings.bak-1.json, and " + file + " became the new strings.json"})

    # /api/browse
    async def open_folder(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        path = payload.get('path', None)
        name = payload.get('name', None)
        if path is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'path' parameter."}, status=400)
        elif name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter."}, status=400)
        else:
            files, folders = self.get_folder_content(name, path)
            return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "path":path, "files":files, "folders":folders}})

    # /api/ignore_file
    async def ignore_file(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        path = payload.get('path', None)
        name = payload.get('name', None)
        state = payload.get('state', None)
        if path is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'path' parameter."}, status=400)
        elif name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter."}, status=400)
        elif state is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'state' parameter."}, status=400)
        else:
            if path in self.projects[name]["files"]:
                self.projects[name]["files"][path]["ignored"] = int(state)
                self.modified[name] = True
            files, folders = self.get_folder_content(name, "" if "/" not in path else ("/".join(path.split("/")[:-1]) + "/"))
            return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "path":path, "files":files, "folders":folders}})

    # /api/file
    async def open_file(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        path = payload.get('path', None)
        name = payload.get('name', None)
        if path is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'path' parameter."}, status=400)
        elif name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter."}, status=400)
        else:
            self.load_strings(name)
            if path not in self.strings[name]["files"]:
                return web.json_response({"result":"bad", "message":"Bad request, invalid 'path' parameter."}, status=400)
            else:
                actions = {k : v[1] for k, v in self.actions.items() if self.plugins[v[0]].match(path, True)}
                return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "path":path, "strings":self.strings[name]["strings"], "list":self.strings[name]["files"][path], "actions":actions}})

    # /api/file_action
    async def run_action(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        path = payload.get('path', None)
        name = payload.get('name', None)
        version = payload.get('version', None)
        key = payload.get('key', None)
        if path is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'path' parameter."}, status=400)
        elif name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter."}, status=400)
        elif version is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'version' parameter."}, status=400)
        elif key is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'key' parameter."}, status=400)
        elif key not in self.actions:
            return web.json_response({"result":"bad", "message":"Bad request, invalid 'key' parameter."}, status=400)
        else:
            if version != self.projects[name]["version"]:
                return web.json_response({"result":"bad", "message":"The project has been updated, redirecting..."})
            message = self.actions[key][2](name, path, self.settings | self.projects[name].get("settings", {}))
            if message != "":
                return web.json_response({"result":"ok", "data":{}, "message":message})
            else:
                return web.json_response({"result":"ok", "data":{}})

    # /api/update_string
    async def edit_string(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        setting = payload.get('setting', None)
        path = payload.get('path', None)
        name = payload.get('name', None)
        version = payload.get('version', None)
        group = payload.get('group', None)
        index = payload.get('index', None)
        string = payload.get('string', None)
        if path is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'path' parameter"}, status=400)
        elif version is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'version' parameter"}, status=400)
        elif name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        elif index is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'index' parameter"}, status=400)
        elif group is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'group' parameter"}, status=400)
        else:
            if version != self.projects[name]["version"]:
                return web.json_response({"result":"bad", "message":"The project has been updated, redirecting..."})
            if path not in self.strings[name]["files"]:
                return web.json_response({"result":"bad", "message":"Bad request, invalid 'path' parameter"}, status=400)
            else:
                updated : list[int] = [] # list of updated string positions
                match setting:
                    case 0: # Unlink
                        self.strings[name]["files"][path][group][index][2] = (self.strings[name]["files"][path][group][index][2] + 1) % 2
                        updated = self.get_list_of_update_string_index(name, path, group, index, True)
                    case 1: # Disable
                        self.strings[name]["files"][path][group][index][3] = (self.strings[name]["files"][path][group][index][3] + 1) % 2
                        updated = self.get_list_of_update_string_index(name, path, group, index, True)
                    case 2: # Disable all occurences in file
                        sid : str = self.strings[name]["files"][path][group][index][0] # retrieve id
                        state : int = (self.strings[name]["files"][path][group][index][3] + 1) % 2
                        for i in range(len(self.strings[name]["files"][path])):
                            for j in range(1, len(self.strings[name]["files"][path][i])):
                                if self.strings[name]["files"][path][i][j][0] == sid: # for all matching id, disable
                                    self.strings[name]["files"][path][i][j][3] = state
                                    updated.extend(self.get_list_of_update_string_index(name, path, i, j, True))
                    case _: # Change string
                        if self.strings[name]["files"][path][group][index][2]:
                            self.strings[name]["files"][path][group][index][1] = string
                            updated = self.get_list_of_update_string_index(name, path, group, index, True)
                        else:
                            self.strings[name]["strings"][self.strings[name]["files"][path][group][index][0]][1] = string
                            updated = self.get_list_of_update_string_index(name, path, group, index, False)
                # Remove modified flag
                self.strings[name]["files"][path][group][index][4] = 0
                self.modified[name] = True
                # Start computation
                asyncio.create_task(self.compute_translated(name, self.projects[name]["version"]))
                # Respond
                return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "path":path, "strings":self.strings[name]["strings"], "list":self.strings[name]["files"][path], "updated":updated}})

    # /api/translate_string
    async def translate_string(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        string = payload.get('string', None)
        name = payload.get('name', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        elif string is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'string' parameter"}, status=400)
        else:
            if string.strip() == "":
                translation = None
            else:
                # Getting translator
                current = self.get_current_translator(name)
                if current[1] is None:
                    return web.json_response({"result":"bad", "message":"No Translator currently set"})
                translation = await current[1].translate(string, self.settings | self.projects[name]['settings'])
                if translation is not None and (translation.lower() == string.lower() or translation.strip() == ""):
                    translation = None
            return web.json_response({"result":"ok", "data":{"translation":translation}})

    # /api/translate_file
    async def translate_file(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        path = payload.get('path', None)
        name = payload.get('name', None)
        version = payload.get('version', None)
        if path is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'path' parameter"}, status=400)
        elif version is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'version' parameter"}, status=400)
        elif name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        else:
            if version != self.projects[name]["version"]:
                return web.json_response({"result":"bad", "message":"The project has been updated, redirecting..."})
            # Getting translator
            current = self.get_current_translator(name)
            if current[1] is None:
                return web.json_response({"result":"bad", "message":"No Translator currently set"})
            # Fetching strings in need of translation
            self.log.info("Starting batch translation for project " + name + "...")
            version = self.projects[name]["version"]
            file = self.strings[name]["files"][path]
            revert_table = []
            to_translate = []
            global_ids = set()
            for group in file:
                await asyncio.sleep(0)
                for j in range(1, len(group)):
                    lc = group[j]
                    gl = self.strings[name]["strings"][lc[0]]
                    if gl[0].strip() == "" or lc[3]:
                        continue
                    if lc[2]:
                        if lc[1] is not None:
                            continue
                        to_translate.append(gl[0])
                        revert_table.append((group[j], group[j]))
                    else:
                        if gl[1] is not None or lc[0] in global_ids:
                            continue
                        global_ids.add(lc[0])
                        to_translate.append(gl[0])
                        revert_table.append((group[j], self.strings[name]["strings"][lc[0]]))
            if len(to_translate) > 0:
                # Translating
                self.log.info("Batch translating " + str(len(to_translate)) + " strings for project " + name + "...")
                result = await current[1].translate_batch(to_translate, self.settings | self.projects[name]['settings'])
                if len(result) != len(to_translate):
                    return web.json_response({"result":"bad", "message":"Batch translation failed"})
                if version != self.projects[name]["version"]:
                    self.log.error("Batch translation for project " + name + " has been aborted because of a version update")
                    return web.json_response({"result":"bad", "message":"The Project has been updated, the translation has been cancelled."})
                count = 0
                for i in range(len(result)):
                    if result[i] is None or result[i].strip() == "" or result[i].lower() == to_translate[i].lower():
                        continue
                    revert_table[i][1][1] = result[i]
                    revert_table[i][0][4] = 0
                    self.modified[name] = True
                    count += 1
                self.log.info(str(count) + " strings have been translated for project " + name)
            else:
                count = 0
            
            # Start computation
            if count > 0:
                asyncio.create_task(self.compute_translated(name, self.projects[name]["version"]))
            # Respond
            return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "path":path, "strings":self.strings[name]["strings"], "list":self.strings[name]["files"][path]}, "message":"{} string(s) have been translated".format(count)})

    # /api/search_string
    async def search_string(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        path = payload.get('path', None)
        name = payload.get('name', None)
        search = payload.get('search', None)
        if path is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'path' parameter"}, status=400)
        elif search is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'search' parameter"}, status=400)
        elif name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        else:
            lsearch = search.lower()
            id_matches : set[str] = ([k for k, s in self.strings[name]["strings"].items() if lsearch in s[0].lower() or (s[1] is not None and lsearch in s[1].lower())])
            files : set[str] = set()
            for f, groups in self.strings[name]["files"].items():
                for g in groups:
                    if f in files:
                        break
                    for i in range(1, len(g)):
                        if g[i][0] in id_matches or (g[i][1] is not None and lsearch in g[i][1].lower()):
                            files.add(f)
                            break
            result : dict[str, bool] = {}
            keys : list[str] = list(files)
            keys.sort()
            for f in keys:
                result[f] = self.projects[name]["files"].get(f, {}).get("ignored", False)
            return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "path":path, "search":search, "files":result}, "message":"Found in {} files".format(len(files))})

if __name__ == "__main__":
    RPGMTL().run()