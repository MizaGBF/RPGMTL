from __future__ import annotations
from importlib import import_module
import os
import ast
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from ..rpgmtl import RPGMTL

def get_plugin_from_ast(tree : ast.Module) -> tuple[list[ast.ClassDef], list[ast.ClassDef]]:
    classes : list[ast.ClassDef] = ([], [])
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if ((isinstance(base, ast.Name) and base.id == "Plugin") or (isinstance(base, ast.Attribute) and base.attr == "Plugin")):
                    classes[0].append(node)
                elif ((isinstance(base, ast.Name) and base.id == "TranslatorPlugin") or (isinstance(base, ast.Attribute) and base.attr == "TranslatorPlugin")):
                    classes[1].append(node)
    return classes

def _loadPlugin_(rpgmtl : RPGMTL, path_filename : str, filename : str, relative : str = "", package : str|None = None, silent : bool = False) -> None:
    try:
        with open(path_filename, mode='r', encoding='utf-8') as py:
            # check for BOM
            if ord(py.read(1)) != 65279:
                py.seek(0)
            tree : ast.Module = ast.parse(py.read())
            plugins, translators = get_plugin_from_ast(tree)
            for node in plugins:
                try:
                    module_name : str = filename[:-3]
                    _class : Plugin = getattr(import_module(relative + module_name, package=package), node.name)
                    rpgmtl.add_plugin(_class())
                except Exception as e2:
                    rpgmtl.log.error("Failed to instantiate plugin " + node.name + "\n" + rpgmtl.trbk(e2))
            
            for node in translators:
                try:
                    module_name : str = filename[:-3]
                    _class : Plugin = getattr(import_module(relative + module_name, package=package), node.name)
                    rpgmtl.add_translator(_class())
                except Exception as e2:
                    rpgmtl.log.error("Failed to instantiate translator " + node.name + "\n" + rpgmtl.trbk(e2))
    except Exception as e:
        rpgmtl.log.error("Exception in plugin file " + path_filename + "\n" + rpgmtl.trbk(e))

def load(rpgmtl : RPGMTL) -> None:
    for filename in os.listdir('plugins/'):
        path_filename = os.path.join('plugins/', filename)
        if filename not in ['__init__.py'] and filename.endswith('.py') and os.path.isfile(path_filename):
            _loadPlugin_(rpgmtl, path_filename, filename, relative=".", package='plugins')

class Plugin:
    FILE_ENCODINGS : list[str] = ["utf-8", "shift_jis", "iso8859-1", "cp1251", "cp1252", "ascii"] # To cover a lot of encoding scenarios
    
    def __init__(self : Plugin) -> None:
        # Be sure to call super first, in your Plugin
        self.owner : RPGMTL|None = None
        self.name : str = "__undefined__"
        self.description : str = "__undefined__"
        self.settings : dict[str, Any] = {} # internal variable containing current settings
        self._enc_cur_ : int = 0 # internal variable to keep track of what encoding was used
        self._enc_set_ : bool = False # internal variable keeping track if the above has been set

    def connect(self : Plugin, rpgmtl : RPGMTL) -> None:
        # No ned to reimplement this one
        self.owner = rpgmtl
        for ex in self.file_extension():
            self.owner.extensions.add(ex)
        self.owner.log.info("Plugin " + self.name + " has been loaded")

    def get_setting_infos(self : Plugin) -> dict[str, list]:
        # If your plugins need editable settings, return them here
        # Formatting Example
        # return {
        #    "setting_key": ["text_to_display", "expected_type", default_value, choice_list]
        #    ...
        # }
        # setting_key: must be unique among other plugin, use some unique ientifier
        # text_to_display: A string to be displayed on the UI
        # expected_type: A string type, either "bool", "num", "str" ("num" are treated as float internally, make sure to round/convert them internally if needed)
        # default_value: The default value of this setting
        # choice_list: A list of options. Will be ignored for bool type. Can be optional for other types (set to None in this case).
        return {}

    def get_action_infos(self : Plugin) -> dict[str, list]:
        # Allow to add custom actions when opening a file
        # Return them here
        # Formatting Example
        # return {
        #    "action_key": ["text_to_display", self.callback]
        #    ...
        # }
        # action_key: must be unique among other plugin, use some unique ientifier
        # text_to_display: A string to be displayed on the UI
        # callback: A function of your callback. It must take as a parameter the project name (str), the file path (str) and a (dict) of the plugin settings. The return parameter is a string (a message to display, can be empty)
        return {}

    def set_settings(self : Plugin, settings : dict[str, Any]) -> None:
        self.settings = settings

    def file_extension(self : Plugin) -> list[str]:
        # A list of file extensions, without the dot
        return []

    def match(self : Plugin, file_path : str, is_for_action : bool) -> bool:
        # Return True if your plugin want to handle this file
        # The second parameter indicates if it's for a file action
        return False

    def read(self : Plugin, file_path : str, file : bytes) -> list[list[str]]:
        # Return a list of group strings extracted from file
        # Formatting Example
        # return [
        #    ["group_1_name", "string_1", "string_2", ...],
        #    ["group_2_name", "string_3", "string_4", ...],
        # ]
        return []

    def write(self : Plugin, file_path : str, content : bytes, strings : dict) -> tuple[bytes, bool]:
        # Edit the file content with the translated strings and return it, plus a boolean indicating if it has been modified
        return (content, False)

    def format(self : Plugin, file_path : str, content : bytes) -> bytes:
        # Called last in the patching process
        # If you want to format the 
        return content

    # No need to implement the methods below unless you have the need for it
    def reset(self : Plugin) -> None:
        # If you reimplement this one, be sure to call super on this base version
        # Reset the encoding setting before patching
        self._enc_cur_ = 0
        self._enc_set_ = False

    # Decode bytes
    def decode(self : Plugin, b : bytes) -> str:
        while True:
            try:
                r = b.decode(self.FILE_ENCODINGS[self._enc_cur_])
                self._enc_set_ = True
                return r
            except Exception as e:
                if self._enc_set_:
                    raise e
                self._enc_cur_ += 1
                if self._enc_cur_ >= len(self.FILE_ENCODINGS):
                    raise Exception("Couldn't determine encoding of file content")

    # Encode string
    def encode(self : Plugin, s : str) -> bytes:
        while True:
            try:
                r = s.encode(self.FILE_ENCODINGS[self._enc_cur_])
                self._enc_set_ = True
                return r
            except Exception as e:
                if self._enc_set_:
                    raise e
                self._enc_cur_ += 1
                if self._enc_cur_ >= len(self.FILE_ENCODINGS):
                    raise Exception("Couldn't determine encoding of file content")

class TranslatorPlugin:
    def __init__(self : TranslatorPlugin) -> None:
        # Be sure to call super first, in your TranslatorPlugin
        self.owner : RPGMTL|None = None
        self.name : str = "__undefined__"
        self.description : str = "__undefined__"

    def connect(self : TranslatorPlugin, rpgmtl : RPGMTL) -> None:
        # No ned to reimplement this one
        self.owner = rpgmtl
        self.owner.log.info("Translator " + self.name + " has been loaded")

    def get_setting_infos(self : TranslatorPlugin) -> dict[str, list]:
        # Work the same as for Plugin
        return {}

    def get_action_infos(self : Plugin) -> dict[str, list]:
        # Work the same as for Plugin
        return {}

    async def translate(self : TranslatorPlugin, string : str, settings : dict[str, Any] = {}) -> str|None:
        # Translate a string
        # Return the translated String or None on error
        return None

    async def translate_back(self : TranslatorPlugin, strings : list[str], settings : dict[str, Any] = {}) -> list[str|None]:
        # Translate a string
        # Return the translated String or None on error
        return []

@dataclass(slots=True)
class WalkHelper():
    group : int
    index : int
    modified : bool
    str_store : str
    str_modified : bool
    file_path : str
    strings : dict[str, Any]

    def __init__(self : WalkHelper, file_path : str, project_strings : dict[str, Any]) -> None:
        self.group = 0
        self.index = 0
        self.modified = False
        self.str_store = ""
        self.str_modified = False
        self.file_path = file_path
        self.strings = project_strings
        self._goNext()

    # Reset walker state
    def reset(self : WalkHelper) -> None:
        self.group = 0
        self.index = 0
        self._goNext()

    # Internal function to go to the next string
    def _goNext(self : WalkHelper) -> None:
        self.index += 1
        if self.group >= len(self.strings["files"][self.file_path]):
            raise Exception("[WalkHelper] Reached the end of known strings") 
        while self.index >= len(self.strings["files"][self.file_path][self.group]):
            self.group += 1
            self.index = 1
            if self.group >= len(self.strings["files"][self.file_path]):
                return

    # Check if the given string (and optional group) matches the current one and, if a translation is available, set it in self.str_store and set its str_modified state
    def check_string(self : WalkHelper, string : str, group : None|str = None, *, loc : tuple[int, int]|None = None) -> None:
        self.str_modified = False
        auto_go_next : bool = loc is None
        if loc is None:
            loc = (self.group, self.index)
        else:
            self.group = loc[0]
            self.index = loc[1]
        if group is not None and group != self.strings["files"][self.file_path][self.group][0]:
            raise Exception("[WalkHelper] Invalid group match at (" + str(loc[0]) + "," + str(loc[1]) + ")")
        local = self.strings["files"][self.file_path][self.group][self.index]
        if auto_go_next:
            self._goNext()
        if not local[3]:
            glbal = self.strings["strings"][local[0]]
            if glbal[0] != string:
                raise Exception("[WalkHelper] Invalid string match at (" + str(loc[0]) + "," + str(loc[1]) + ")")
            if local[2]:
                if local[1] is not None:
                    self.str_store = local[1]
                    self.str_modified = True
            elif glbal[1] is not None and glbal[1] != "":
                self.str_store = glbal[1]
                self.str_modified = True

    # Simple function to do all the needed step to update a string
    # Simply do something like:
    # for i in range(0, len(mystrings)):
    #    mystrings[i] = helper.apply_string(mystrings[i])
    # The return value will be either the original unmodified one OR the new one, and the helper internal state will be set
    def apply_string(self : WalkHelper, string : str, group : None|str = None, *, loc : tuple[int, int]|None = None) -> str:
        self.check_string(string, group, loc=loc)
        if self.str_modified:
            self.modified = True
            return self.str_store
        else:
            return string