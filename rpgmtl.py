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
from pathlib import Path, PurePath
import string
import argparse
import ssl

import plugins
from plugins import BasePlugin, TranslatorPlugin, FileType, GloIndex, LocIndex, IntBool

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
    VERSION = "3.29"
    CHILDREN_FILE_ID = "@__children_file__@:"
    HISTORY_LIMIT = 10

    def __init__(self : RPGMTL) -> None:
        # Setting up logging
        handler = RotatingFileHandler(filename="rpgmtl.log", encoding='utf-8', mode='w', maxBytes=51200, backupCount=3)
        handler.setFormatter(logging.Formatter("%(asctime)s|%(levelname)s|%(name)s : %(message)s"))
        logging.basicConfig(level=logging.INFO)
        # add loggers to our RotatingFileHandler
        self.loggers = {}
        for l in ['rpgmtl', 'aiohttp.access','aiohttp.client','aiohttp.internal','aiohttp.server','aiohttp.web','aiohttp.websocket']:
            self.loggers[l] = logging.getLogger(l)
            self.loggers[l].addHandler(handler)
        # Disable other loggers
        for l in ['httpx']:
            logging.getLogger(l).setLevel(logging.FATAL)
        self.log = self.loggers['rpgmtl']
        self.log.info("RPGMTL v{} is starting up...".format(self.VERSION))
        # Web server
        self.app : web.Application = web.Application(middlewares=[self.ip_whitelist])
        # Autosave system
        self.app.on_startup.append(self.init_autosave)
        self.app.on_cleanup.append(self.stop_autosave)
        # HTTP Routes
        self.app.router.add_static('/assets/images', path='./assets/images', name='assets')
        self.app.router.add_static('/assets/plugins', path='./assets/plugins', name='plugins_assets')
        self.app.router.add_static('/assets/ui', path='./assets/ui', name='ui')
        self.app.add_routes([
                web.get('/', self.index), # index.html 
                
                web.post('/api/main', self.project_list), # main menu
                web.post('/api/shutdown', self.shutdown), # stop RPGMTL
                web.post('/api/update_location', self.select_project_exe), # Game Path selection
                web.post('/api/new_project', self.create_project), # Create Project
                web.post('/api/open_project', self.get_project), # Open Project
                web.post('/api/translator', self.get_translator), # Open Translator menu
                web.post('/api/update_translator', self.update_translator), # Update Translator
                web.post('/api/settings', self.get_settings), # Open Settings
                web.post('/api/update_settings', self.update_setting), # Update Settings
                web.post('/api/unload', self.unload_project), # Unload project
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
                web.post('/api/update_marker', self.update_marker), # Edit string marker
                web.post('/api/update_string', self.edit_string), # Edit string values
                web.post('/api/translate_string', self.translate_string), # Translate a string
                web.post('/api/translate_file', self.translate_file), # Translate a file
                web.post('/api/translate_project', self.translate_project), # Translate a project
                web.post('/api/search_string', self.search_string), # Search a string
                web.post('/api/local_path', self.local_path), # Browse local files
                web.post('/api/replace_strings', self.replace_strings), # Browse local files
                web.post('/api/use_tool', self.use_tool), # Use a tool
                web.post('/api/bookmark_tool', self.bookmark_tool), # Bookmark a tool
                web.post('/api/delete_knowledge', self.delete_knowledge), # delete a knowledge base entry
                web.post('/api/update_knowledge', self.update_knowledge), # update a knowledge base entry
                web.post('/api/update_notes', self.update_notes), # update project notes
        ])
        # variables
        self.port : int = 8000 # Port to start the server with
        self.last_directory = os.getcwd() # used for file browsing
        self.is_posix = os.name != 'nt' # set to True if OS isn't windows
        self.projects : dict[str, Any] = {} # store loaded config.json
        self.strings : dict[str, Any] = {} # store loaded string.json
        self.modified : dict[str, bool] = {} # store flag indicating if config.json or string.json has pending changes waiting to be saved
        self.computing : dict[str, asyncio.Task] = {} # store state for compute_translated
        self.setting_key_set : set[str] = set(["rpgmtl_current_translator", "rpgmtl_current_batch_translator"]) # store existing setting keys
        self.action_key_set : set[str] = set() # store existing action keys
        self.tool_key_set : set[str] = set() # store existing tool keys
        self.settings : dict[str, Any] = {} # store global plugins setting
        self.settings_modified : bool = False
        self.setting_menu : dict[str, dict[str, list]] = {} # store info for setting menu, per plugin file
        self.plugin_descriptions : dict[str, str] = {} # store plugin descriptions
        self.actions : dict[str, list] = {} # store plugin actions
        self.tools : dict[str, list] = {} # store plugin tools
        self.tool_list_info : list[Any] = [] # used to pass the tool list to the client
        self.history : list[list[str]] = [] # store link to last ten accessed files
        self.allowed_ips : list[str] = [] # allowed ips
        # loaded plugins
        self.plugins : dict[str, plugins.Plugin] = {}
        self.translators : dict[str, plugins.TranslatorPlugin] = {}
        # load settings.json
        self.load_settings()
        # parse arguments
        self.parse_command_line()
        # load the plugins (see plugins/__init__.py )
        plugins.load(self)
        # preset tool_list_info
        for key, data in self.tools.items():
            self.tool_list_info.append(
                [
                    key,
                    data[0],
                    data[1],
                    data[2],
                    data[4]
                ]
            )

    # Function to format an exception into something readable
    def trbk(self : RPGMTL, e : Exception) -> str:
        return "".join(traceback.format_exception(type(e), e, e.__traceback__))

    # Generic function used by add_plugin and add_translator
    def process_infos(self : RPGMTL, plugin : BasePlugin) -> None:
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
                case "str"|"password"|"text":
                    menu_info.append(v[1])
                    if not isinstance(v[2], str):
                        raise Exception("[{}] Default value of setting key {} isn't of type str".format(plugin.name, k))
                case "num":
                    menu_info.append(v[1])
                    if not isinstance(v[2], float) and not isinstance(v[2], int):
                        raise Exception("[{}] Default value of setting key {} isn't of number".format(plugin.name, k))
                case "display":
                    menu_info.append(v[1])
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
            if len(v) not in (2, 3): # check the format
                raise Exception("[{}] Expected 2 or 3 values for action key {}".format(plugin.name, k))
            if k in self.action_key_set: # check if key is already set
                raise Exception("[{}] Action key {} is already in use by another Plugin".format(plugin.name, k))
            self.action_key_set.add(k)
            # add action
            if len(v) == 2: # old format without icon
                self.log.warning("Format of action {} in plugin {} is deprecated. Icon is missing.".format(k, plugin.name))
                self.actions[k] = [plugin.name, None, v[0], v[1]] # plugin name (for reverse lookup), UI text, no icon and callback
            else:
                self.actions[k] = [plugin.name, v[0], v[1], v[2]] # plugin name (for reverse lookup), icon path, UI text, and callback

        # Process tool actions
        for k, v in plugin.get_tool_infos().items(): # same principle
            if len(v) != 4: # check the format
                raise Exception("[{}] Expected 4 values for tool key {}".format(plugin.name, k))
            if k in self.tool_key_set: # check if key is already set
                raise Exception("[{}] Action key {} is already in use by another Plugin".format(plugin.name, k))
            self.tool_key_set.add(k)
            # add tool
            self.tools[k] = [plugin.name, v[0], v[1], v[2], v[3]] # plugin name (for reverse lookup), icon path, UI text, callback and params

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
        for key in ("rpgmtl_current_translator", "rpgmtl_current_batch_translator"): # init special settings if not set
            if key not in self.settings: # init translator setting if not set
                self.settings[key] = plugin.name
                self.settings_modified = True
        plugin.connect(self)
        self.plugin_descriptions[plugin.name] = plugin.description

    # Retrieve a specific plugin by its name
    def get_plugin(self : RPGMTL, name : str) -> plugins.Plugin|None:
        return self.plugins.get(name, None)

    # return a tuple of the Translator-in-use name and instance
    # name is the project name (to check a specific project setting)
    def get_current_translator(self : RPGMTL, name : str|None) -> tuple[str, plugins.TranslatorPlugin|None, str, plugins.TranslatorPlugin|None]:
        # load if it's not loaded
        self.load_project(name)
        pname : str|None = None
        bname : str|None = None
        if name is not None: # check project setting
            pname : str|None = self.projects[name]["settings"].get("rpgmtl_current_translator", None)
            bname : str|None = self.projects[name]["settings"].get("rpgmtl_current_batch_translator", None)
            if pname not in self.translators:
                pname = None
            if bname not in self.translators:
                bname = None
        # check global setting if needed
        if pname is None and "rpgmtl_current_translator" in self.settings:
            pname = self.settings["rpgmtl_current_translator"]
        if bname is None and "rpgmtl_current_batch_translator" in self.settings:
            bname = self.settings["rpgmtl_current_batch_translator"]
        # return
        if pname in self.translators:
            if bname in self.translators:
                return pname, self.translators[pname], bname, self.translators[bname]
            else:
                return pname, self.translators[pname], "", None
        elif bname in self.translators:
            return "", None, bname, self.translators[bname]
        # default not found result
        return "", None, "", None

    # load settings.json
    def load_settings(self : RPGMTL) -> None:
        try:
            with open('settings.json', mode='r', encoding='utf-8') as f:
                data = json.load(f)
                ver = data.get("version", 0)
                if ver < 1:
                    self.settings = data
                elif ver >= 1:
                    self.settings = data["settings"]
                    self.history = data["history"]
        except Exception as e:
            self.log.warning("Failed to load settings.json, default value will be used:\n" + self.trbk(e))

    # Save config.json, strings.json and load_settings.json
    def save(self : RPGMTL) -> None:
        for k, v in self.modified.items(): # check modified flags
            if v: # if raised
                folder = 'projects/' + k + '/'
                try:
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
                self.modified[k] = False # reset it
        if self.settings_modified: # write settings if flag is set
            try:
                with open('settings.json', mode='w', encoding='utf-8') as f:
                    json.dump({"version":1, "settings":self.settings, "history":self.history}, f, ensure_ascii=False, indent=0, separators=(',', ':'))
                self.log.info("Updated settings.json")
            except Exception as e:
                self.log.error("Failed to update settings.json:\n" + self.trbk(e))
            self.settings_modified = False

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
    async def autosave(self : RPGMTL) -> None:
        while True:
            try:
                await asyncio.sleep(300) # call save() every 300s
                self.save()
            except asyncio.CancelledError:
                return

    # start the autosave task
    async def init_autosave(self : RPGMTL, app : web.Application) -> None:
        self.autosave_task = asyncio.create_task(self.autosave())

    # stop the autosave task
    async def stop_autosave(self : RPGMTL, app : web.Application) -> None:
        self.autosave_task.cancel()

    def load_ip_whitelist(self : RPGMTL) -> None:
        try:
            with open("whitelist.txt", mode="r", encoding="utf-8") as f:
                ip_list = f.read()
        except:
            self.log.warning("Failed to open whitelist.txt, a new file has been created")
            try:
                with open("whitelist.txt", mode="w", encoding="utf-8") as f:
                    pass
            except:
                pass
            return
        self.allowed_ips = [ip.strip() for ip in ip_list.replace("\r", "").split("\n")]
        self.log.info("{} IP are allowed".format(len(self.allowed_ips)))

    # check the projects folder and return a list of folder containing config.json files inside
    def load_project_list(self : RPGMTL) -> list[str]:
        try:
            if not os.path.isdir('projects'): # create folder if not found
                os.mkdir('projects')
            dirs : list[str] = []
            for d in os.walk('projects'): # walk inside
                try:
                    p = PurePath(d[0])
                    if os.path.isfile(p / 'config.json'): # take note of folders with a config.json inside
                        dirs.append(Path(*p.parts[1:]).as_posix())
                except:
                    pass
            return dirs
        except:
            return []

    # function to search a game executable
    # name is the project name and is only in use in case we're updating the exe location
    def select_exe(self : RPGMTL, file_path : str, name : str|None = None) -> None|str:
        try:
            self.log.info("Dialog output is: " + file_path)
            if file_path == "" or file_path is None: # empty, user cancelled
                return None
            else:
                file_path = PurePath(file_path).parent.as_posix() # get the foler path from it
                if name is not None: # if updating existing location, we set it
                    self.projects[name]["path"] = file_path
                    self.modified[name] = True
                    self.log.info("Project " + name + " path is updated to " + file_path)
                return file_path # return the path
        except Exception as e:
            self.log.error("Error during selection of an executable for project " + name + "\n" + self.trbk(e))
            return None

    # Backup game files matching the plugin extensions for the given project name
    def backup_game_files(self : RPGMTL, pname : str) -> None:
        self.log.info("Copying game files for project " + pname + "...")
        backup_path : PurePath = PurePath("projects", pname, "originals") # project backup path
        # delete existing backup
        if os.path.isdir(backup_path):
            shutil.rmtree(backup_path)
        update_file_dict : dict[str, dict] = {}
        # walk into the game folder
        game_path : PurePath = PurePath(self.projects[pname]["path"])
        for path, subdirs, files in os.walk(game_path):
            for name in files:
                copied : bool = False
                extracted : bool = False
                fp : PurePath = PurePath(path, name) # full file path
                fpr : PurePath = fp.relative_to(game_path) # relative target file path
                target_dir = backup_path / fpr.parent # directory containing the file
                
                for p in self.plugins.values():
                    # check if file is supported by an extension
                    if not extracted and p.extract(update_file_dict, fp, target_dir, backup_path):
                        extracted = True
                    
                    # check if the file must be backed up
                    if not copied and p.match(name, False):
                        if not os.path.isdir(target_dir): # create directory if not found
                            try:
                                # create dir if needed
                                os.makedirs(target_dir.as_posix(), exist_ok=True)
                            except Exception as e:
                                self.log.error("Couldn't create the following folder:" + target_dir.as_posix() + "\n" + self.trbk(e))
                        # backup
                        try:
                            # file copy to project folder
                            shutil.copy(fp, backup_path / fpr)
                            # add to config.json
                            update_file_dict[fpr.as_posix()] = {
                                "file_type":FileType.NORMAL,
                                "ignored":IntBool.FALSE,
                                "strings":0,
                                "translated":0,
                                "disabled_strings":0
                            }
                            self.log.info(fpr.as_posix() + " has been copied to project folder " + pname)
                        except Exception as e:
                            self.log.error("Couldn't copy the following file:" + fp.as_posix() + " to project folder " + pname + "\n" + self.trbk(e))
                        copied = True
        # keep file setting if it exists
        for k, v in self.projects[pname].get("files", {}).items():
            if k in update_file_dict or v["file_type"] in (FileType.ARCHIVE, FileType.VIRTUAL, FileType.VIRTUAL_UNDEFINED):
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
                "format_version":2, # config.json format version
                "version":0, # string iteration
                "settings":{},
                "path":path + "/",
                "patches":{},
                "ai_knowledge_base":[]
            }
            # backup files
            self.backup_game_files(name)
            # save
            self.save()
            return True, name
        except Exception as e:
            self.log.critical("Error while copying game files for project " + name + "\n" + self.trbk(e))
            return False, str(e)

    # load a project config.json file
    def load_project(self : RPGMTL, name : str) -> dict[str, Any]:
        try:
            if name not in self.projects:
                with open('projects/' + name + '/config.json', mode='r', encoding='utf-8') as f:
                    self.projects[name] = self.update_project_config_format(json.load(f))
            return self.projects[name]
        except:
            return None

    # Update the content of config.json to later formats
    def update_project_config_format(self : RPGMTL, data : dict[str, Any]) -> dict[str, Any]:
        ver = data.get("format_version", 0)
        if ver < 1:
            if "ai_knowledge_base" in data["settings"]:
                data["ai_knowledge_base"] = data["settings"]["ai_knowledge_base"]
                data["settings"].pop("ai_knowledge_base")
            else:
                data["ai_knowledge_base"] = []
        if ver < 2:
            if "gemini_knowledge_base" in data:
                data["ai_knowledge_base"] = data["gemini_knowledge_base"]
                data["settings"].pop("gemini_knowledge_base")
            data["notes"] = ""
        data["format_version"] = 2
        return data

    # load a project strings.json file
    def load_strings(self : RPGMTL, name : str) -> dict[str, Any]:
        try:
            if name not in self.strings:
                with open('projects/' + name + '/strings.json', mode='r', encoding='utf-8') as f:
                    self.strings[name] = self.update_string_format(json.load(f))
                self.start_compute_translated(name) # force an up to date compute
            return self.strings[name]
        except OSError:
            return None
        except Exception as e:
            self.log.error("Failed to load strings of project " + name + "\n" + self.trbk(e))
            raise e

    # Update the content of strings.json to later formats
    def update_string_format(self : RPGMTL, strings : dict[str, Any]) -> dict[str, Any]:
        ver = strings.get("version", 0)
        if ver < 1:
            for sid in strings["strings"]:
                # adding color marker
                strings["strings"][sid].insert(GloIndex.COLOR, IntBool.FALSE)
        strings["version"] = 1
        return strings

    # backup a project strings.json file and backups
    def backup_strings_file(self : RPGMTL, name : str) -> None:
        fns : list[str] = ["strings.bak-5.json", "strings.bak-4.json", "strings.bak-3.json", "strings.bak-2.json", "strings.bak-1.json", "strings.json"]
        for i in range(1, len(fns)):
            try:
                shutil.copyfile('projects/' + name + '/' + fns[i], 'projects/' + name + '/' + fns[i-1])
            except:
                pass

    # extract the strings from given file
    def extract_game_file(self : RPGMTL, name : str, filename : str) -> tuple[bool, list[list[str]], list[str]]:
        p_path : Path = Path('projects', name, 'originals')
        for p in self.plugins.values():
            if p.match(filename, False): # this file match with the plugin
                p.reset(p_path, filename) # reset plugin state
                p.set_settings(self.settings | self.projects[name]['settings']) # and set setting
                # read the content
                if p.is_streaming(filename, False):
                    with open((p_path / filename).as_posix(), mode="rb") as infile:
                        return True, p.read_stream(name, filename, infile)
                else:
                    with open((p_path / filename).as_posix(), mode="rb") as infile:
                        content = infile.read()
                return True, p.read(filename, content), p.related_tool_plugins
        return False, [], []

    # patch the strings from given file, and write to the release folder
    # return value is a tuple of counts, for successfully patched files and errors
    def patch_game_file(self : RPGMTL, name : str, filename : str, release_folder : PurePath) -> tuple[int, int]:
        p_path : Path = Path('projects', name, 'originals')
        totalerr : int = 0
        for p in self.plugins.values():
            try:
                if p.match(filename, False): # file matches the plugin
                    p.reset(p_path, filename)
                    p.set_settings(self.settings | self.projects[name]['settings'])
                    if p.is_streaming(filename, False):
                        with open((p_path / filename).as_posix(), mode="rb") as iofile:
                            return p.write_stream(name, filename, iofile, Path(release_folder, filename))
                    else:
                        with open((p_path / filename).as_posix(), mode="rb") as iofile:
                            content = iofile.read()
                        content, modified = p.write(name, filename, content) # write content
                        content, modified, errcount = self.apply_fixes(name, filename, content, modified) # apply fixes
                        totalerr += errcount
                        # write file if modified
                        if modified:
                            content = p.format(filename, content)
                            output : Path = Path(release_folder, filename)
                            output.parent.mkdir(parents=True, exist_ok=True)
                            output.write_bytes(content)
                            return (1, totalerr)
            except Exception as e:
                self.log.error("Failed to patch strings in " + filename + " for project " + name + " using the plugin " + p.name + "\n" + self.trbk(e))
                return (0, totalerr + 1)
        return (0, totalerr)

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
                reverse_strings[index["strings"][k][GloIndex.ORI]] = k # keep track of string and its id in a reverse lookup table
                index["strings"][k][GloIndex.COUNT] = 0 # set occurence to 0
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
        # ... first to set virtual as undefined
        for f in list(self.projects[name]['files'].keys()):
            if self.projects[name]['files'][f]["file_type"] == FileType.VIRTUAL:
                self.projects[name]['files'][f]["file_type"] = FileType.VIRTUAL_UNDEFINED
        # ... next to extract the strings
        err : int = 0
        used_plugins : set[str] = set()
        for f in list(self.projects[name]['files'].keys()):
            try:
                # references
                file_info : dict[str, Any] = self.projects[name]['files'][f]
                if file_info["file_type"] not in (FileType.NORMAL, FileType.ARCHIVE):
                    continue
                file_info["file_type"] = FileType.NORMAL # reset to normal for now
                target : dict[str, Any] = file_info # reference for children files
                target_file : str = f
                # reset string
                target["strings"] = 0
                # extract strings
                extracted, groups, related_plugins = self.extract_game_file(name, f)
                if extracted:
                    for related in related_plugins:
                        used_plugins.add(related)
                    index["files"][target_file] = []
                    for group in groups:
                        if len(group) == 1 and group[0].startswith(self.CHILDREN_FILE_ID):
                            # special group identifying a sub file
                            target_file = f + "/" + group[0][len(self.CHILDREN_FILE_ID):].replace("/", "").replace("/", "\\")
                            file_info["file_type"] = FileType.ARCHIVE
                            if target_file in self.projects[name]['files']: # confirm file as virtual
                                self.projects[name]['files'][target_file]["file_type"] = FileType.VIRTUAL
                            else: # else create it
                                self.projects[name]['files'][target_file] = {
                                    "file_type":FileType.VIRTUAL,
                                    "ignored":IntBool.FALSE,
                                    "strings":IntBool.FALSE,
                                    "translated":IntBool.FALSE,
                                    "disabled_strings":IntBool.FALSE
                                }
                            self.projects[name]['files'][target_file]["parent"] = f
                            if target_file not in index["files"]: # add to index too
                                index["files"][target_file] = []
                            target = self.projects[name]['files'][target_file] # set as target
                            target["strings"] = 0 # reset to 0 (if needed)
                            continue
                        # normal string processing
                        # process group content
                        for i in range(1, len(group)):
                            s : str = group[i]
                            # Note: Also use integer instead of boolean to keep file size low
                            group[i] = [str(str_id), None, 0, 0, update_run_flag] # id, indiv_tl, unlinked, ignored, modified/new
                            target["strings"] += 1
                            # if string already occured
                            if s in reverse_strings:
                                group[i][LocIndex.ID] = reverse_strings[s] # get its id
                                index["strings"][reverse_strings[s]][GloIndex.COUNT] += 1 # increase occurence count
                            else:
                                reverse_strings[s] = str(str_id) # new id
                                # base string, global translation, occurence count, color marker
                                index["strings"][str(str_id)] = [s, None, 1, 0]
                                str_id += 1 # increase for next id
                        index["files"][target_file].append(group)
            except Exception as e:
                err += 1
                self.log.error("Failed to extract strings from " + f + " for project " + name + "\n" + self.trbk(e))
        if update_run_flag:
            # cleanup virtual files still undefined
            self.log.info("Cleaning config.json of " + name + "...")
            for f in list(self.projects[name]['files'].keys()):
                if self.projects[name]['files'][f]["file_type"] == FileType.VIRTUAL_UNDEFINED:
                    self.projects[name]['files'].pop(f)
            # check old file and retrieve old strings
            self.log.info("Matching with the previous strings of " + name + "...")
            for k in index["files"]:
                if len(index["files"][k]) == 0:
                    continue
                if k in old:
                    # list new strings
                    A : list[str] = []
                    A_index : list[tuple[int, int]] = []
                    for i, g in enumerate(index["files"][k]):
                        for j in range(1, len(g)):
                            A.append(g[j][LocIndex.ID])
                            A_index.append((i, j))
                    # list old strings
                    B : list[str] = []
                    B_index : list[tuple[int, int]] = []
                    for i, g in enumerate(old[k]):
                        for j in range(1, len(g)):
                            B.append(g[j][LocIndex.ID])
                            B_index.append((i, j))
                    # compare the lists
                    blocks = difflib.SequenceMatcher(a=A, b=B).get_matching_blocks()
                    for block in blocks:
                        for i in range(block.size):
                            xyA : tuple[int, int] = A_index[block.a+i]
                            xyB : tuple[int, int] = B_index[block.b+i]
                            index["files"][k][xyA[0]][xyA[1]] = old[k][xyB[0]][xyB[1]] # match old to new (to keep individual translations and settings)
        else:
            # auto bookmark tools for starting projects
            self.projects[name]["bookmarked_tools"] = []
            for p in used_plugins:
                if p in self.plugins:
                    for t in self.plugins[p].get_tool_infos():
                        self.projects[name]["bookmarked_tools"].append(t)
        # set new string table
        self.strings[name] = index
        # increase project version
        self.projects[name]["version"] = self.projects[name].get("version", 0) + 1
        # start computing completion
        self.start_compute_translated(name)
        # set save flag
        self.modified[name] = True
        self.log.info("Strings extraction for project " + name + " completed")
        return err

    def start_compute_translated(self : RPGMTL, name : str) -> None:
        if name in self.computing:
            self.computing[name].cancel()
        self.computing[name] = asyncio.create_task(self.compute_translated(name))

    # calculate number of translated lines
    async def compute_translated(self : RPGMTL, name : str) -> None:
        try:
            tl_table : dict[str, bool] = {s : self.strings[name]["strings"][s][GloIndex.TL] is not None for s in self.strings[name]["strings"]}
            for f in self.strings[name]["files"]:
                await asyncio.sleep(0.005) # i.e 5s for 1000 files
                counts = [0, 0, 0]
                for g in self.strings[name]["files"][f]:
                    counts[2] += len(g) - 1
                    for i in range(1, len(g)):
                        if g[i][LocIndex.IGNORED]:
                            counts[1] += 1 # disabled count
                        elif (g[i][LocIndex.LOCAL] and g[i][LocIndex.TL] is not None) or tl_table[g[i][LocIndex.ID]]:
                            counts[0] += 1 # translated count
                if f not in self.projects[name]['files']:
                    return
                self.projects[name]['files'][f]["translated"] = counts[0]
                self.projects[name]['files'][f]["disabled_strings"] = counts[1]
                self.projects[name]['files'][f]["strings"] = counts[2]
            # Note: Not changing modified flag
            # This function is already called after modifying something
            # It's to avoid too much writes
        except asyncio.CancelledError:
            return
        except Exception as e:
            self.log.error("Unexpected error in compute_translated for project " + name + "\n" + self.trbk(e))

    # release game patch
    def create_release(self : RPGMTL, name : str) -> tuple[int, int]:
        err : int = 0
        # clean existing folder
        release_folder : PurePath = PurePath('projects', name, 'release')
        if os.path.isdir(release_folder):
            try:
                shutil.rmtree(release_folder)
                self.log.info("Cleaned up " + release_folder.as_posix())
            except Exception as e:
                self.log.error("Failed to properly clean " + release_folder.as_posix() + "\n" + self.trbk(e))
                err += 1
        # load strings if not loaded
        self.load_strings(name)
        self.log.info("Patching files for project " + name + "...")
        # for each file
        patch_count : int = 0
        for f in self.projects[name]["files"]:
            ftype : int = self.projects[name]["files"][f]["file_type"]
            if (self.projects[name]["files"][f]["ignored"]
                    or ftype in (FileType.VIRTUAL, FileType.VIRTUAL_UNDEFINED)):
                # skip ignored files and virtual files
                continue
            r : tuple[int, int] = self.patch_game_file(name, f, release_folder)
            if r[0] > 0:
                patch_count += 1
            if r[1] > 0:
                err += 1
        # Copy edit content
        edit_folder : PurePath = PurePath('projects', name, 'edit')
        if os.path.isdir(edit_folder):
            try:
                self.log.info("Copying the content of the edit folder for project " + name + "...")
                for path, subdirs, files in os.walk(edit_folder):
                    for f in files:
                        origin : PurePath = PurePath(os.path.join(path, f))
                        target : PurePath = release_folder / origin.relative_to(edit_folder)
                        if not os.path.isdir(target.parent):
                            os.makedirs(target.parent, exist_ok=False)
                        shutil.copyfile(origin, target)
                        self.log.info("Copied edit/" + f + " for project " + name + "...")
            except:
                self.log.warning("Failed to copy the content of the edit folder for project " + name)
                err += 1
        if patch_count > 0:
            self.log.info("Patched {} files for project {} with {} errors, available in the release folder".format(patch_count, name, err))
        else:
            self.log.info("Patched {} files for project {} with {} errors,".format(patch_count, name, err))
        return patch_count, err

    # execute and apply runtime fix/patch
    def apply_fixes(self : RPGMTL, _name_ : str, _file_path_ : str, _content_ : bytes, _modified_ : bool) -> tuple[bytes, bool, int]:
        # variables got underscore on purpose, as the patch is executed in this context
        _error_ : int = 0
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
                    _error_ += 1
        # return content (either old or new modified one), modified flag and error count
        return _content_, _modified_, _error_

    # Function to import strings from old RPGMTL formats (version 1 and 2)
    # Return value is a tuple of state (-1 = error occured, 0 = nothing, 1 = success) and the imported string count
    def import_old_data(self : RPGMTL, name : str, file_path : str) -> tuple[int, int]:
        try:
            count : int = 0
            self.load_strings(name)
            if file_path == "" or file_path is None:
                return 0, 0
            # backup project strings.json
            self.backup_strings_file(name)
            # read file
            with open(file_path, mode="rb") as f:
                data = f.read()
            if file_path.endswith(".json"): # old format 1
                data = json.loads(data.decode("utf-8"))
                flag : bool = "strings" in data
                if flag:
                    if "files" in data: # current v3 format
                        ref = {v[0]:v[1] for k, v in data["strings"].items() if v[1] is not None}
                    elif len(data) == 2: # very old format
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
                if v[GloIndex.TL] is None and isinstance(ref.get(v[GloIndex.ORI], None), str):
                    self.strings[name]["strings"][k][GloIndex.TL] = ref[v[GloIndex.ORI]]
                    count += 1
            if count > 0:
                # increase project version
                self.projects[name]["version"] = self.projects[name].get("version", -1) + 1
                self.modified[name] = True
                # start computing completion
                self.start_compute_translated(name)
            return 1, count
        except:
            return -1, count

    # Function to import strings from RPGMaker Trans formats (version 3)
    # Return value is a tuple of state (-1 = error occured, 0 = nothing, 1 = success) and the imported string count
    # Documentation: https://rpgmakertrans.bitbucket.io/patchformatv3.html
    def import_rpgmtrans_data(self : RPGMTL, name : str, file_path : str) -> tuple[int, int]:
        try:
            count : int = 0
            self.load_strings(name)
            multiline_ruby = (self.settings | self.projects[name]["settings"]).get("rm_marshal_multiline", False)
            if file_path == "" or file_path is None:
                return 0, 0
            # backup project strings.json
            self.backup_strings_file(name)
            patch_path : PurePath = PurePath(file_path).parent / "patch"
            table = {}
            for d in os.walk(patch_path):
                for p in d[-1]:
                    # open file
                    with open((patch_path / p).as_posix(), mode="r", encoding="utf-8") as f:
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
            checked = set()
            for f in self.strings[name]["files"]:
                for g, group in enumerate(self.strings[name]["files"][f]):
                    for i in range(1, len(group)):
                        sid = group[i][LocIndex.ID]
                        if sid not in checked:
                            checked.add(sid)
                            if self.strings[name]["strings"][sid][GloIndex.TL] is None:
                                if self.strings[name]["strings"][sid][GloIndex.ORI] in table:
                                    self.strings[name]["strings"][sid][GloIndex.TL] = table[self.strings[name]["strings"][sid][GloIndex.ORI]]
                                    count += 1
                                elif group[0] == "Command: Script": # inline Script
                                    s : list[str] = self.strings[name]["strings"][sid][GloIndex.ORI].split('"')
                                    changed : bool = False
                                    for j in range(1, len(s), 2):
                                        if s[j] in table:
                                            s[j] = table[s[j]]
                                            changed = True
                                    if changed:
                                        self.strings[name]["strings"][sid][GloIndex.TL] = '"'.join(s)
                                        count += 1
            if count > 0:
                # increase project version
                self.projects[name]["version"] = self.projects[name].get("version", -1) + 1
                self.modified[name] = True
                # start computing completion
                self.start_compute_translated(name)
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
        folder : PurePath = PurePath(path)
        self.load_strings(name)
        for f in self.strings[name]["files"]:
            if f not in self.projects[name]["files"]: # double check to be sure we're on the same version
                continue
            pf : PurePath = PurePath(f)
            if pf.is_relative_to(folder):
                relative = pf.relative_to(folder)
                if len(relative.parts) == 1:
                    files[f] = self.projects[name]["files"][f]["ignored"] if f in self.projects[name]["files"] else False
                elif len(relative.parts) > 1:
                    d : str = (folder / relative.parts[0]).as_posix() + "/"
                    if d not in folders:
                        folders.append(d)
        files_keys = list(files.keys())
        files_keys.sort()
        files = {k : files[k] for k in files_keys}
        folders.sort()
        return files, folders

    # add file to access history
    def add_to_history(self : RPGMTL, name : str, path : str) -> None:
        i : int = 0
        while i < len(self.history):
            if self.history[i][0] == name and self.history[i][1] == path:
                if i == 0: # first place, don't do anything if it's already in the right spot
                    return
                self.history.pop(i) # else delete
                break
            else:
                i += 1
        self.history.insert(0, [name, path])
        if len(self.history) > self.HISTORY_LIMIT:
            self.history = self.history[:self.HISTORY_LIMIT]
        self.settings_modified = True

    # parse command line arguments
    def parse_command_line(self : RPGMTL) -> None:
        # Parse command line
        parser : argparse.ArgumentParser = argparse.ArgumentParser(prog="rpgmtl.py")
        command = parser.add_argument_group('command', 'Optional commands')
        command.add_argument('-p', '--port', help="set the web server port", nargs=1, type=int, metavar='PORT', default=[8000])
        command.add_argument('-s', '--https', help="provide paths to your SSL certificate and key", nargs=2, default=None)
        command.add_argument('-n', '--http', help="clear SSL certificate settings and force HTTP", action='store_const', const=True, default=False, metavar='FILES')
        command.add_argument('-i', '--ip', help="set the IP filter status. Add 1, on, enable, enabled, 0, off, disable or disabled to set it.", nargs=1, default=None, metavar='STATE')
        command.add_argument('-d', '--debug', help="remove some strings from the standard output for clarity", action='store_const', const=True, default=False, metavar='')
        args : argparse.Namespace = parser.parse_args()
        
        # set server port
        self.port = args.port[0]
        
        # Remove aiohttp.access
        if args.debug:
            self.loggers['aiohttp.access'].propagate = False
        
        # Check HTTPS/SSL
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
                    self.log.info("HTTPS Certificates are set")
                except Exception as e:
                    self.log.error("Failed to set HTTPS Certificates, Exception: " + str(e))
        if args.ip is not None:
            match args.ip[0].lower():
                case "1"|"true"|"on"|"enable"|"enabled":
                    self.settings["ip_filter"] = True
                    self.settings_modified = True
                    self.log.info("IP Filter is enabled")
                case "0"|"false"|"off"|"disable"|"disabled":
                    self.settings["ip_filter"] = False
                    self.settings_modified = True
                    self.log.info("IP Filter is disabled")
                case _:
                    self.log.error("Unknown value for -i/--ip parameter.")

    # Start RPGMTL and run the server
    def run(self : RPGMTL) -> None:
        # Init
        ssl_context = None
        if "https_cert" in self.settings:
            try:
                ssl_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
                ssl_context.load_cert_chain(self.settings["https_cert"][0], self.settings["https_cert"][1])
            except:
                ssl_context = None
        if ssl_context is not None:
            self.log.info("SSL is enabled")
        if self.settings.get("ip_filter", False):
            self.load_ip_whitelist()
        self.load_project_list()
        
        # Start
        try:
            self.log.info("Starting RPGMTL on port {}".format(self.port))
            web.run_app(self.app, port=self.port, shutdown_timeout=0, ssl_context=ssl_context)
        except Exception as e: # Ctrl+C is enough to trigger it
            self.log.warning("The following exception occured:\n" + self.trbk(e))
        self.log.info("RPGMTL is shutting down...")
        
        # Ssave on quit
        self.save()

    ######################################################
    # Request Responses start here
    ######################################################

    @web.middleware
    async def ip_whitelist(self : RPGMTL, request, handler):
        """
        This middleware checks if the client's IP address is in the whitelist.
        """
        if self.settings.get("ip_filter", False):
            # peername is a tuple (host, port) from the transport socket
            # we get the host, i.e. the IP address.
            client_ip = request.transport.get_extra_info('peername')[0] if request.transport else None
            if client_ip not in self.allowed_ips:
                raise web.HTTPForbidden(reason=f"IP {client_ip} not allowed")
        return await handler(request)

    # Request the HTML page
    async def index(self : RPGMTL, request : web.Request) -> web.Response:
        return web.FileResponse('./assets/ui/index.html')

    # /api/main
    async def project_list(self : RPGMTL, request : web.Request) -> web.Response:
        l : list[str] = self.load_project_list()
        self.log.info("A list of " + str(len(l)) + " project(s) has been sent to an user")
        return web.json_response({"result":"ok", "data":{"list":l, "verstring":self.VERSION, "history":self.history}})

    # /api/shutdown
    async def shutdown(self : RPGMTL, request : web.Request) -> web.Response:
        loop = asyncio.get_event_loop()
        loop.call_later(0.2, loop.stop)
        return web.json_response({"result":"ok", "data":{}}, status=200)

    # /api/update_location
    async def select_project_exe(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        path = payload.get('path', None)
        file_path = self.select_exe(path, name)
        cwd : Path = Path.cwd().resolve()
        path_exe : Path = Path(file_path).resolve()
        if path_exe in cwd.parents or path_exe == cwd:
            return web.json_response({"result":"bad", "message":"RPGMTL is present further down in the selected folder."})
        else:
            if not self.is_posix: # windows
                if path_exe.as_posix() == "C:/":
                    return web.json_response({"result":"bad", "message":"Selecting an executable in the root of the Windows C: Drive is forbidden."})
                elif path_exe.as_posix() in ("C:/Program Files", "C:/Program Files (x86)", "C:/ProgramData"):
                    return web.json_response({"result":"bad", "message":"Selecting an executable in the root of the Program Files folders is forbidden."})
                else:
                    for dir, dir_name in (("C:/Nvidia", "Nvidia"), ("C:/Windows", "Windows"), ("C:/sources", "Sources")):
                        path_dir : Path = Path(dir)
                        if path_dir in path_exe.parents or path_dir == path_exe:
                            return web.json_response({"result":"bad", "message":"Selecting an executable in the {} system directory or sub-directory is forbidden.".format(dir_name)})
            else: # unix
                if path_exe.as_posix() == "/":
                    return web.json_response({"result":"bad", "message":"Selecting an executable in the root directory is forbidden."})
                else:
                    for dir, dir_name in (("/boot", "boot"), ("/dev", "dev"), ("/etc", "etc"), ("/lib", "lib"), ("/lib64", "lib64"), ("/proc", "proc"), ("/sys", "sys"), ("/usr", "usr")):
                        path_dir : Path = Path(dir)
                        if path_dir in path_exe.parents or path_dir == path_exe:
                            return web.json_response({"result":"bad", "message":"Selecting an executable in the {} system directory or sub-directory is forbidden.".format(dir_name)})
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
                return  web.json_response({"result":"ok", "data":{"name":string, "config":self.projects[string]}, "message":"You can now set your Settings and Extract the strings"})
            else:
                return  web.json_response({"result":"bad", "message":string}, status=500)

    # /api/open_project
    async def get_project(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter."}, status=400)
        else:
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.load_project(name), "tools":self.tool_list_info}})

    # /api/translator
    async def get_translator(self : RPGMTL, request : web.Request) -> web.Response:
        try:
            payload = await request.json()
        except:
            payload = {}
        name = payload.get('name', None)
        current, _, batch, _ = self.get_current_translator(name)
        translators : list[str] = list(self.translators.keys())
        if name is None:
            return web.json_response({"result":"ok", "data":{"list":translators, "current":current, "batch":batch}})
        else:
            self.load_project(name)
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name], "list":translators, "current":current, "batch":batch}})

    # /api/update_translator
    async def update_translator(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        value = payload.get('value', None)
        index = payload.get('index', None)
        if name is None and value is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'value' parameter"}, status=400)
        elif value is not None and value not in self.translators:
            return web.json_response({"result":"bad", "message":"Bad request, invalid 'value' parameter"}, status=400)
        if name is None:
            if index is None:
                return web.json_response({"result":"bad", "message":"Bad request, missing 'index' parameter"}, status=400)
            match index:
                case 1:
                    self.settings["rpgmtl_current_batch_translator"] = value
                case _:
                    self.settings["rpgmtl_current_translator"] = value
            self.settings_modified = True
            return web.json_response({"result":"ok", "data":{}})
        else:
            if value is None:
                self.projects[name]["settings"].pop("rpgmtl_current_translator", None)
                self.projects[name]["settings"].pop("rpgmtl_current_batch_translator", None)
            else:
                if index is None:
                    return web.json_response({"result":"bad", "message":"Bad request, missing 'index' parameter"}, status=400)
                match index:
                    case 1:
                        self.projects[name]["settings"]["rpgmtl_current_batch_translator"] = value
                    case _:
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
            self.load_project(name)
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
        if value is not None:
            for f in self.setting_menu:
                if key in self.setting_menu[f]:
                    try:
                        match self.setting_menu[f][key][1]:
                            case "bool":
                                if not isinstance(value, bool):
                                    raise Exception()
                            case "num":
                                try:
                                    value = float(value)
                                except:
                                    value = int(value)
                            case _:
                                if not isinstance(value, str):
                                    raise Exception()
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
                self.modified[name] = True
            elif key in self.projects[name]["settings"]:
                if value is None or value == self.settings.get(key, None):
                    self.projects[name]["settings"].pop(key)
                    self.modified[name] = True
            elif value is not None:
                self.projects[name]["settings"][key] = value
                self.modified[name] = True
            settings = self.settings | self.projects[name]["settings"]
            return web.json_response({"result":"ok", "data":{"name":name, "config":self.projects[name], "settings":settings}})

    # /api/unload
    async def unload_project(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter."}, status=400)
        else:
            self.save()
            if name in self.computing:
                self.computing[name].cancel()
                self.computing.pop(name)
            if name in self.strings:
                self.strings.pop(name)
            if name in self.projects:
                self.projects.pop(name)
            if name in self.modified:
                self.modified.pop(name)
            return web.json_response({"result":"ok", "data":{}, "message":"Project has been unloaded."})

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
            self.load_project(name)
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
            self.load_project(name)
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
        path = payload.get('path', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        else:
            state, count = self.import_old_data(name, path)
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
        path = payload.get('path', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        else:
            state, count = self.import_rpgmtrans_data(name, path)
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
            self.load_project(name)
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
            shutil.move("projects/" + name + "/" + file, "projects/" + name + "/backup.tmp.file.json")
            bak : list[str] = [
                "strings.bak-5.json",
                "strings.bak-4.json",
                "strings.bak-3.json",
                "strings.bak-2.json",
                "strings.bak-1.json",
                "strings.json"
            ]
            meet : bool = False
            for i in range(0, len(bak)):
                if bak[i] == file:
                    meet = True
                    continue
                elif not meet:
                    continue
                else:
                    try:
                        if i == 0:
                            os.remove("projects/" + name + "/" + bak[i])
                        else:
                            shutil.move("projects/" + name + "/" + bak[i], "projects/" + name + "/" + bak[i-1])
                    except:
                        pass
            shutil.move("projects/" + name + "/backup.tmp.file.json", "projects/" + name + "/strings.json")
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
            self.load_project(name)
            self.load_strings(name)
            try:
                files, folders = self.get_folder_content(name, path)
                return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "path":path, "files":files, "folders":folders}})
            except Exception:
                return web.json_response({"result":"bad", "message":"Strings doesn't exist. You might have to extract them."}, status=400)

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
            self.load_project(name)
            self.load_strings(name)
            self.add_to_history(name, path)
            if path not in self.strings[name]["files"]:
                return web.json_response({"result":"bad", "message":"Bad request, invalid 'path' parameter."}, status=400)
            else:
                actions = {k : [v[0], v[1], v[2]] for k, v in self.actions.items() if self.plugins[v[0]].match(path, True)}
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
            message = self.actions[key][3](name, path, self.settings | self.projects[name].get("settings", {}))
            if message != "":
                return web.json_response({"result":"ok", "data":{}, "message":message})
            else:
                return web.json_response({"result":"ok", "data":{}})

    # /api/update_marker
    async def update_marker(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        sid = payload.get('id', None)
        value = payload.get('value', None)
        path = payload.get('path', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        elif sid is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'sid' parameter"}, status=400)
        elif value is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'value' parameter"}, status=400)
        elif path is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'path' parameter"}, status=400)
        else:
            self.strings[name]["strings"][sid][GloIndex.COLOR] = value
            self.modified[name] = True
            return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "path":path, "strings":self.strings[name]["strings"], "list":self.strings[name]["files"][path]}})

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
                ref = self.strings[name]["files"][path][group][index] # reference
                match setting:
                    case 0: # Unlink
                        ref[LocIndex.LOCAL] = (ref[LocIndex.LOCAL] + 1) % 2
                    case 1: # Disable
                        ref[LocIndex.IGNORED] = (ref[LocIndex.IGNORED] + 1) % 2
                    case 2: # Disable all occurences in file
                        sid : str = ref[0] # retrieve id
                        state : int = (ref[LocIndex.IGNORED] + 1) % 2
                        for i in range(len(self.strings[name]["files"][path])):
                            for j in range(1, len(self.strings[name]["files"][path][i])):
                                if self.strings[name]["files"][path][i][j][LocIndex.ID] == sid: # for all matching id, disable
                                    self.strings[name]["files"][path][i][j][LocIndex.IGNORED] = state
                    case 3: # Disable all occurences in project
                        sid : str = ref[LocIndex.ID] # retrieve id
                        state : int = (ref[LocIndex.IGNORED] + 1) % 2
                        for file in self.strings[name]["files"]:
                            for i in range(len(self.strings[name]["files"][file])):
                                for j in range(1, len(self.strings[name]["files"][file][i])):
                                    if self.strings[name]["files"][file][i][j][LocIndex.ID] == sid: # for all matching id, disable
                                        self.strings[name]["files"][file][i][j][LocIndex.IGNORED] = state
                    case _: # Change string
                        if ref[LocIndex.LOCAL]:
                            ref[LocIndex.TL] = string
                        else:
                            self.strings[name]["strings"][ref[LocIndex.ID]][GloIndex.TL] = string
                # Remove modified flag
                ref[LocIndex.MODIFIED] = 0
                self.modified[name] = True
                # Start computation
                self.start_compute_translated(name)
                # Respond
                return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "path":path, "strings":self.strings[name]["strings"], "list":self.strings[name]["files"][path]}})

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
                    return web.json_response({"result":"bad", "message":"No Single Translator currently set"})
                translation = await current[1].translate(name, string, self.settings | self.projects[name]['settings'])
                if translation is not None and (translation.lower() == string.lower() or translation.strip() == ""):
                    translation = None
            return web.json_response({"result":"ok", "data":{"translation":translation}})

    # subroutine of translate_file() for TranslatorBatchFormat.STANDARD
    async def standard_batch_translate_file(self : RPGMTL, name : str, path : str, plugin : TranslatorPlugin) -> tuple[bool, bool, int|str]:
        version = self.projects[name]["version"]
        file = self.strings[name]["files"][path]
        revert_table = []
        to_translate = []
        global_ids = set()
        for group in file:
            await asyncio.sleep(0)
            for j in range(1, len(group)):
                lc = group[j]
                gl = self.strings[name]["strings"][lc[LocIndex.ID]]
                if gl[GloIndex.ORI].strip() == "" or lc[LocIndex.IGNORED]:
                    continue
                if lc[LocIndex.LOCAL]:
                    if lc[LocIndex.TL] is not None:
                        continue
                    to_translate.append(gl[GloIndex.ORI])
                    revert_table.append((group[j], group[j]))
                else:
                    if gl[GloIndex.TL] is not None or lc[LocIndex.ID] in global_ids:
                        continue
                    global_ids.add(lc[LocIndex.ID])
                    to_translate.append(gl[GloIndex.ORI])
                    revert_table.append((group[j], self.strings[name]["strings"][lc[LocIndex.ID]]))
        count : int
        if len(to_translate) > 0:
            # Translating
            self.log.info("Batch translating {} strings in file '{}' for project {}...".format(len(to_translate), path, name))
            result, continue_flag = await plugin.translate_batch(name, to_translate, self.settings | self.projects[name]['settings'])
            if len(result) != len(to_translate):
                self.log.error("Batch translation for project " + name + " failed")
                return False, False, "Batch translation failed."
            if version != self.projects[name]["version"]:
                self.log.error("Batch translation for project " + name + " has been aborted because of a version update")
                return False, False, "The Project has been updated, the translation has been cancelled."
            count = 0
            for i in range(len(result)):
                if result[i] is None or result[i].strip() == "" or result[i].lower() == to_translate[i].lower():
                    continue
                revert_table[i][1][1] = result[i] # 1 is the TL index, can be either global or local
                revert_table[i][0][LocIndex.MODIFIED] = IntBool.FALSE
                count += 1
            self.log.info("{} strings have been translated in file '{}' for project {}...".format(count, path, name))
        else:
            count = 0
            continue_flag = False
        if count > 0:
            self.modified[name] = True
            self.start_compute_translated(name)
        # Respond
        return True, continue_flag, count

    # subroutine of translate_file() for TranslatorBatchFormat.AI
    async def ai_batch_translate_file(self : RPGMTL, name : str, path : str, plugin : TranslatorPlugin) -> tuple[bool, bool, int|str]:
        version = self.projects[name]["version"]
        file = self.strings[name]["files"][path]
        untranslated : int = 0
        batch : dict[str, Any] = {"file":path, "groups":[]}
        ignore : set[str] = set()
        for i, group in enumerate(file):
            batch["groups"].append({"name":group[0], "strings":[]})
            for j in range(1, len(group)):
                lc = group[j]
                gl = self.strings[name]["strings"][lc[LocIndex.ID]]
                
                s : dict[str, Any] = {}
                s["id"] = "{}-{}".format(i, j)
                s["ignore"] = lc[LocIndex.IGNORED] == IntBool.TRUE
                if s["ignore"]:
                    ignore.add(s["id"])
                s["original"] = gl[GloIndex.ORI]
                if lc[LocIndex.LOCAL]:
                    if lc[LocIndex.TL] is not None:
                        s["translation"] = lc[LocIndex.TL]
                    elif not s["ignore"]:
                        untranslated += 1
                else:
                    if gl[GloIndex.TL] is not None:
                        s["translation"] = gl[GloIndex.TL]
                    elif not s["ignore"]:
                        untranslated += 1
                batch["groups"][-1]["strings"].append(s)
        
        if untranslated == 0:
            return True, True, 0
        
        self.log.info("Batch translating {} strings in file '{}' for project {}...".format(untranslated, path, name))
        count : int = 0
        try:
            translated, continue_flag = await plugin.translate_batch(name, batch, self.settings | self.projects[name]['settings'])
        except Exception as e:
            self.log.error("File translation aborted due to the following exception:\n" + self.trbk(e))
            return False, True, str(e)
        if translated is not None:
            # check version
            if version != self.projects[name]["version"]:
                self.log.error("Batch translation for project " + name + " has been aborted because of a version update")
                return False, False, "The Project has been updated, the translation has been cancelled."
            # apply translated strings
            for sid, tl in translated.items():
                try:
                    if sid in ignore: # Don't modify strings not part of our modifications
                        continue
                    split_sid = sid.split("-")
                    i = int(split_sid[0])
                    j = int(split_sid[1])
                    lc = file[i][j]
                    gl = self.strings[name]["strings"][lc[LocIndex.ID]]
                    if lc[LocIndex.LOCAL]:
                        lc[LocIndex.TL] = tl
                    elif gl[GloIndex.TL] is None:
                        gl[GloIndex.TL] = tl
                    elif gl[GloIndex.TL] == tl:
                        continue
                    else:
                        lc[LocIndex.TL] = tl
                        lc[LocIndex.LOCAL] = IntBool.TRUE
                    lc[LocIndex.MODIFIED] = IntBool.FALSE
                    count += 1
                except Exception as e:
                    self.log.error("Exception: " + self.trbk(e))
        if count > 0:
            self.log.info("{} strings have been translated in file '{}' for project {}...".format(count, path, name))
            self.modified[name] = True
            self.start_compute_translated(name)
        return True, continue_flag, count

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
            current = self.get_current_translator(name)[3]
            if current is None:
                return web.json_response({"result":"bad", "message":"No Batch Translator currently set"})
            # Fetching strings in need of translation
            match current.get_format():
                case TranslatorPlugin.TranslatorBatchFormat.AI:
                    state, _unused_, res = await self.ai_batch_translate_file(name, path, current)
                case _:
                    state, _unused_, res = await self.standard_batch_translate_file(name, path, current)
            msg : str
            match res:
                case int():
                    msg = "{} string(s) have been translated".format(res)
                case _:
                    msg = "An error occured: {}".format(res)
            return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "path":path, "strings":self.strings[name]["strings"], "list":self.strings[name]["files"][path]}, "message":msg})

    # /api/translate_project
    async def translate_project(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        else:
            self.load_project(name)
            self.load_strings(name)
            if name not in self.strings:
                return web.json_response({"result":"bad", "data":{"name":name, "config":self.projects[name]}, "message":"The strings haven't been extracted."})
            # Getting translator
            current = self.get_current_translator(name)[3]
            if current is None:
                return web.json_response({"result":"bad", "data":{"name":name, "config":self.projects[name]}, "message":"No Batch Translator currently set"})
            if name in self.computing:
                while not self.computing[name].done(): # to make sure string counts are up to date
                    await asyncio.sleep(1)
            # Fetching strings in need of translation
            count : int = 0
            file_count : int = 0
            error : int = 0
            continue_flag : bool = True
            for path in self.strings[name]["files"]:
                if path not in self.projects[name]["files"]:
                    continue
                ignored = self.projects[name]["files"][path].get("ignored", True)
                string_count = (
                    self.projects[name]["files"][path].get("strings", 0)
                    - self.projects[name]["files"][path].get("disabled", 0)
                    - self.projects[name]["files"][path].get("translated", 0)
                )
                if not ignored and string_count > 0:
                    file_count += 1
                    try:
                        match current.get_format():
                            case TranslatorPlugin.TranslatorBatchFormat.AI:
                                state, continue_flag, res =  await self.ai_batch_translate_file(name, path, current)
                            case _:
                                state, continue_flag, res =  await self.standard_batch_translate_file(name, path, current)
                    except Exception as e:
                        self.log.error("Exception: " + self.trbk(e))
                        self.log.error("An exception has been raised and 'translate_project' has been aborted for project " + name)
                        error += 1
                        break
                    if isinstance(res, int):
                        count += res
                    if not state:
                        error += 1
                    if not continue_flag:
                        break
            msg : str
            if count == 0:
                if error > 0:
                    msg = "{} error(s) occured, no strings have been translated in {} file(s).".format(error, file_count)
                else:
                    msg = "No strings have been translated in {} file(s).".format(file_count)
            else:
                if error > 0:
                    msg = "{} string(s) have been translated in {} file(s), {} error(s) occured.".format(count, file_count, error)
                else:
                    msg = "{} string(s) have been translated in {} file(s)".format(count, file_count)
            return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "path":path, "strings":self.strings[name]["strings"], "list":self.strings[name]["files"][path]}, "message":msg})

    # /api/search_string
    async def search_string(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        path = payload.get('path', None)
        name = payload.get('name', None)
        search = payload.get('search', None)
        case = payload.get('case', None)
        contains = payload.get('contains', None)
        if path is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'path' parameter"}, status=400)
        elif search is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'search' parameter"}, status=400)
        elif name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        elif case is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'case' parameter"}, status=400)
        elif contains is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'contains' parameter"}, status=400)
        else:
            self.load_project(name)
            self.load_strings(name)
            # set search term and list all string matching in set
            lsearch : str = search.lower() if not case else search
            original_matches : set[str] # contains string id matching at original level
            translation_matches : set[str] # contains string id matching at translation level
            if not case:
                if contains:
                    original_matches = {k for k, s in self.strings[name]["strings"].items() if lsearch in s[GloIndex.ORI].lower()}
                    translation_matches = {k for k, s in self.strings[name]["strings"].items() if (s[GloIndex.TL] is not None and lsearch in s[GloIndex.TL].lower())}
                else:
                    original_matches = {k for k, s in self.strings[name]["strings"].items() if lsearch == s[GloIndex.ORI].lower()}
                    translation_matches = {k for k, s in self.strings[name]["strings"].items() if (s[GloIndex.TL] is not None and lsearch == s[GloIndex.TL].lower())}
            else:
                if contains:
                    original_matches = {k for k, s in self.strings[name]["strings"].items() if lsearch in s[GloIndex.ORI]}
                    translation_matches = {k for k, s in self.strings[name]["strings"].items() if (s[GloIndex.TL] is not None and lsearch in s[GloIndex.TL])}
                else:
                    original_matches = {k for k, s in self.strings[name]["strings"].items() if lsearch == s[GloIndex.ORI]}
                    translation_matches = {k for k, s in self.strings[name]["strings"].items() if (s[GloIndex.TL] is not None and lsearch == s[GloIndex.TL])}
            files : set[str] = set()
            for f, groups in self.strings[name]["files"].items():
                for g in groups:
                    if f in files:
                        break
                    for i in range(1, len(g)):
                        if g[i][LocIndex.ID] in original_matches:
                            files.add(f)
                        elif g[i][LocIndex.LOCAL]:
                            if g[i][LocIndex.TL] is not None:
                                if not case:
                                    if contains:
                                        if lsearch in g[i][LocIndex.TL].lower():
                                            files.add(f)
                                            break
                                    else:
                                        if lsearch == g[i][LocIndex.TL].lower():
                                            files.add(f)
                                            break
                                else:
                                    if contains:
                                        if lsearch in g[i][LocIndex.TL]:
                                            files.add(f)
                                            break
                                    else:
                                        if lsearch == g[i][LocIndex.TL]:
                                            files.add(f)
                                            break
                        elif g[i][LocIndex.ID] in translation_matches:
                            files.add(f)
                            break
            result : dict[str, bool] = {}
            keys : list[str] = list(files)
            keys.sort()
            for f in keys:
                result[f] = self.projects[name]["files"].get(f, {}).get("ignored", False)
            return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "path":path, "search":search, "case":case, "contains":contains, "files":result}, "message":"Found in {} files".format(len(files))})

    # /api/local_path
    async def local_path(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        spath = payload.get('path', None)
        mode = payload.get('mode', None)
        if spath is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'path' parameter"}, status=400)
        elif mode is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'mode' parameter"}, status=400)
        else:
            if not self.is_posix and len(spath) == 2 and spath.endswith(":"):
                # special exceptions to list Windows drive letters
                if spath.startswith(":"):
                    dirs : list[str] = []
                    for letter in string.ascii_uppercase:
                        drive_path : Path = Path(letter + ":/") 
                        if drive_path.exists():
                            dirs.append(drive_path.as_posix()[:-1])
                    return web.json_response({"result":"ok", "data":{"path":"", "folders":dirs, "files":[]}})
                else:
                    spath += "/"
            path : Path = Path(self.last_directory) if spath == "" else Path(spath)
            if not path.is_dir():
                path = Path(os.getcwd())
            self.last_directory = path.as_posix()
            files : list[str] = []
            dirs : list[str] = []
            if not self.is_posix or (self.is_posix and path != "/"):
                dirs.append("..")
            for item in path.iterdir():
                if item.is_dir():
                    dirs.append(item.as_posix())
                elif item.is_file():
                    match mode:
                        case 0|1:
                            if item.suffix.lower() == ".exe":
                                files.append(item.as_posix())
                        case 2:
                            if item.suffix.lower() in (".json", ".py"):
                                files.append(item.as_posix())
                        case 3:
                            if item.name == "RPGMKTRANSPATCH":
                                files.append(item.as_posix())
                        case _:
                            return web.json_response({"result":"bad", "message":"Bad request, invalid 'mode' parameter"}, status=400)
            return web.json_response({"result":"ok", "data":{"path":path.as_posix(), "folders":dirs, "files":files}})

    # /api/replace_strings
    async def replace_strings(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        src = payload.get('src', None)
        dst = payload.get('dst', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        elif src is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'src' parameter"}, status=400)
        elif dst is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'dst' parameter"}, status=400)
        else:
            self.save() # save first!
            self.backup_strings_file(name) # backup strings.json
            self.load_strings(name) # load strings.json
            count : int = 0
            modified : set[str] = set()
            for k, v in self.strings[name]["strings"].items():
                if v[GloIndex.TL] is not None:
                    s : str = v[GloIndex.TL].replace(src, dst)
                    if s != v[GloIndex.TL]:
                        modified.add(k)
                        self.strings[name]["strings"][k][GloIndex.TL] = s
            for f, data in self.strings[name]["files"].items():
                for g in range(len(data)):
                    for i in range(1, len(data[g])):
                        if data[g][i][LocIndex.LOCAL]: # is local
                            if data[g][i][LocIndex.TL] is not None:
                                s : str = data[g][i][LocIndex.TL].replace(src, dst)
                                if s != data[g][i][LocIndex.TL]:
                                    data[g][i][LocIndex.TL] = s
                                    data[g][i][LocIndex.MODIFIED] = IntBool.TRUE
                                    count += 1
                        elif data[g][i][LocIndex.ID] in modified:
                            data[g][i][LocIndex.MODIFIED] = IntBool.TRUE
                            count += 1
            if count > 0:
                self.modified[name] = True
            return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name, "count":count}, "message":"{} strings have been modified".format(count)})
            
    # /api/use_tool
    async def use_tool(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        tool = payload.get('tool', None)
        params = payload.get('params', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        elif tool is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'tool' parameter"}, status=400)
        elif params is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'params' parameter"}, status=400)
        else:
            return web.json_response(
                {
                    "result":"ok", "data":{"config":self.projects[name], "name":name},
                    "message":self.tools[tool][3](name, params)
                }
            )
            
    # /api/bookmark_tool
    async def bookmark_tool(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        tool = payload.get('tool', None)
        value = payload.get('value', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        elif tool is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'tool' parameter"}, status=400)
        elif value is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'value' parameter"}, status=400)
        elif not isinstance(value, bool):
            return web.json_response({"result":"bad", "message":"Bad request, invalid 'value' parameter"}, status=400)
        else:
            s : set[str] = set(self.projects[name].get("bookmarked_tools", []))
            if value:
                s.add(tool)
                msg = "This tool has been added to the Project page"
            else:
                s.discard(tool)
                msg = "This tool has been removed from the Project page"
            self.projects[name]["bookmarked_tools"] = list(s)
            self.modified[name] = True
            return web.json_response(
                {
                    "result":"ok", "data":{"config":self.projects[name], "name":name},
                    "message":msg
                }
            )
            
    # /api/delete_knowledge
    async def delete_knowledge(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        entry = payload.get('entry', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        elif entry is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'entry' parameter"}, status=400)
        else:
            for i  in range(len(self.projects[name]["ai_knowledge_base"])):
                if self.projects[name]["ai_knowledge_base"][i]["original"] == entry:
                    del self.projects[name]["ai_knowledge_base"][i]
                    self.modified[name] = True
                    return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name}, "message":"The entry has been deleted"})
            return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name}, "message":"The entry isn't found, nothing has been deleted"})
            
    # /api/update_knowledge
    async def update_knowledge(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        entry = payload.get('entry', None)
        original = payload.get('original', None)
        translation = payload.get('translation', None)
        note = payload.get('note', None)
        last_seen = payload.get('last_seen', None)
        occurence = payload.get('occurence', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        elif original is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'original' parameter"}, status=400)
        elif translation is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'translation' parameter"}, status=400)
        elif note is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'note' parameter"}, status=400)
        elif last_seen is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'last_seen' parameter"}, status=400)
        elif occurence is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'occurence' parameter"}, status=400)
        else:
            try:
                last_seen = int(last_seen)
                if last_seen < 0:
                    raise Exception()
            except:
                return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name}, "message":"Error, 'Last Seen' isn't a positive integer"})
            try:
                occurence = int(occurence)
                if occurence < 0:
                    raise Exception()
            except:
                return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name}, "message":"Error, 'Occurence' isn't a positive integer"})
            updated : bool = False
            index : int = -1
            # check existing entries to replace if needed
            i : int = 0
            while i < len(self.projects[name]["ai_knowledge_base"]):
                if (
                    self.projects[name]["ai_knowledge_base"][i]["original"] == entry or
                    self.projects[name]["ai_knowledge_base"][i]["original"] == original
                ):
                    if index == -1:
                        index = i
                        i += 1
                    else:
                        del self.projects[name]["ai_knowledge_base"][i]
                    updated = True
                else:
                    i += 1
            if index == -1:
                self.projects[name]["ai_knowledge_base"].append(None)
            self.projects[name]["ai_knowledge_base"][index] = {
                "original":original,
                "translation":translation,
                "note":note,
                "last_seen":last_seen,
                "occurence":occurence
            }
            self.modified[name] = True
            return web.json_response(
                {
                    "result":"ok",
                    "data":{"config":self.projects[name], "name":name},
                    "message":("The entry has been added" if not updated else "The entry has been updated")
                }
            )
            
    # /api/update_notes
    async def update_notes(self : RPGMTL, request : web.Request) -> web.Response:
        payload = await request.json()
        name = payload.get('name', None)
        notes = payload.get('notes', None)
        if name is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'name' parameter"}, status=400)
        elif notes is None:
            return web.json_response({"result":"bad", "message":"Bad request, missing 'notes' parameter"}, status=400)
        else:
            self.projects[name]["notes"] = notes
            self.modified[name] = True
            return web.json_response({"result":"ok", "data":{"config":self.projects[name], "name":name}, "message":"Saved"})

if __name__ == "__main__":
    RPGMTL().run()