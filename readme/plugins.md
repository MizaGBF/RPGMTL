# RPGMTL  
  
# Plugins Manual  
  
## Introduction  
  
Plugins are automatically loaded upon RPGMTL startup in alphabetical order of their filenames. If an error occurs during loading, the system skips the problematic plugin and records the error in the logs.  
  
Plugins must use unique names for their Python classes and for all setting, action, and tool keys to avoid conflicts and undefined behavior.  
  
### Plugin Types  
  
There are two primary types of plugins:  
1. **File Plugins**: Responsible for extracting strings from game files and patching them back.  
2. **Translator Plugins**: Interface with external translation APIs.  

Both types inherit from the `BasePlugin` class.
  
### Disabling Plugins  
  
To prevent a plugin from loading, create a file named `disabled.txt` in the same directory as `rpgmtl.py`. List the filenames of the plugins to be ignored, one per line (without the `.py` extension).  
  
Example `disabled.txt`:  
```
json
rm_marshal
```  
  
---
  
## Plugin development  
  
### Quickstart  
  
Create a new Python file in the `plugins` folder.  
  
* For **File Plugins**, import the base class: `from . import Plugin`  
* For **Translator Plugins**, import the base class: `from . import TranslatorPlugin`  
  
Inherit from the appropriate class and override the necessary methods.  
#### Required Methods for File Plugins:  
  
* `match`: Determines if the plugin handles a specific file.  
* **Standard I/O**: `read` and `write`.  
* **Streaming I/O** (for large files): `is_streaming`, `read_streaming`, and `write_streaming`.  
  
> [!NOTE]  
> `is_streaming` must return `True` to enable Streaming I/O operations. Otherwise, it defaults to Standard I/O.  
  
#### Required Methods for Translator Plugins:  
* `translate`  
* `translate_batch`  
  
Refer to the base class definitions in `plugins/__init__.py` and existing plugins for implementation examples and details.  
  
### Extracting Strings  
  
In `read` or `read_streaming`, you must return a list of **String Groups**. A String Group is a list of strings where the first element is the group name (can be empty but must be present).  
  
**Example:**  
```python
results = [
    ["Group 1", "string 1", "string 2"],
    ["Group 2", "string 3"],
]
```  
  
Empty strings should not be added to groups. However, a group containing only a name can be used to display informations in the UI.  
  
**Example:**  
```python
results = [
    ["Group 1", "string 1", "string 2"],
    ["Below are important strings!!"],
    ["Group 2", "string 3"],
]
```  
  
### Patching Strings  
  
In `write` or `write_streaming`, modify the file content using translated strings and return the updated content along with a boolean indicating if any modifications were made.  
  
The `WalkHelper` class is available to assist with patching and ensure data integrity:  
```python
from . import Plugin, WalkHelper

# Inside write function:
helper = WalkHelper(file_path, self.owner.strings[name])
data["key"] = helper.apply_string(data["key"], group_name)
```  
  
The `helper.modified` flag will be set to `True` if any strings were successfully replaced.  
  
If it raises an error, it means your writing function isn't following the same code path as your reading one.  
Or that you must re-extract the strings if the plugin has been updated.  
**A few more usages**: 
```python
# In this example, let's imagine we're patching a string in a Python dictionary:
data["mystring"] = helper.apply_string(data["mystring"], group_name) # The returned value will be either the same string OR the patched string if it exists
# Note 1: group_name is an OPTIONAL parameter and will raise an error if it's not the exact same as at the time of extracting this string.  
  
# Note 2: If the string can be modified right away for some reason, you can use str_modified:  
tmp = helper.apply_string(data["mystring"], group_name)
if helped.str_modified:
    # do stuff ...
    data["mystring"] = tmp
```  
  
### Archive and Virtual files  
  
For archive files (files containing other files), you can represent internal files as "Virtual Files" in the UI by adding a special prefix to a group name during extraction:  
  
```python
results = [
    [self.owner.CHILDREN_FILE_ID + "internal_file.txt"],
    ["Group 1", "extracted string"]
]
```  
  
`self.owner.CHILDREN_FILE_ID` is a constant defined in the `RPGMTL` class.  
  
**Implementation example:**  
```python
groups = []
for file in my_archive:
    # Method 1
    groups.append([self.owner.CHILDREN_FILE_ID + file.name])
    # extract String Groups and append them to groups...
    
    # Method 2
    groups.append([self.owner.CHILDREN_FILE_ID + file.name])
    # we call another plugin capable of handling this file
    if "PluginName" in self.owner.plugins: # Check if this plugin exists and is loaded
        self.owner.plugins["PluginName"].reset() # Reset its state (Don't forget!)
        groups.extend(self.owner.plugins["PluginName"].whatever_function(...)) # Do whatever you want with it and get the extracted strings
```  
  
For patching, this is the opposite process.  
```python
for file in my_archive:
    # Way 1
    helper : WalkHelper = WalkHelper(file.name, self.owner.strings[name])
    # patch the strings like you would normally
    
    # Way 2
    helper : WalkHelper = WalkHelper(file.name, self.owner.strings[name])
    # we call another plugin capable of handling this file
    if "PluginName" in self.owner.plugins: # Check if this plugin exists and is loaded
        self.owner.plugins["PluginName"].reset() # Reset its state (Don't forget!)
        content = self.owner.plugins["PluginName"].whatever_function(helper, ...) # Do whatever you want with it, make sure to pass the helper
        if helper.modified:
            # update the file content
            # ...
```  
  
### Translator Plugin Formats
You can override `get_format` in a `TranslatorPlugin` to specify how data is delivered to `translate_batch`.

* **STANDARD**: Input is a list of strings. Output is a corresponding list of translations or `None`.
* **AI**: Input is a JSON object containing file and group context, including previously translated strings for better accuracy. Output is a JSON object mapping string IDs to translations:  
```json
{
    "file":"FILE_NAME",
    "groups":[
        {
            "name":"GROUP_NAME",
            "strings":[
                {
                    "id":"GROUPINDEX-STRINGINDEX",
                    "ignore":False, // True if the string must be ignored
                    "original":"ORIGINAL_STRING",
                    "translation":"TRANSLATED_STRING"
                }
            ]
        }
    ]
}
```  
It contains even translated strings, for context.  
If you need to break it down to fit in a token budget, it's up to the plugin to handle it.  
  
The output format of `translate_batch` is:  
```json
{
    "STRING_ID":"TRANSLATION"
}
```  
For additional control, you can override:  
- `update_knowledge()`, to build some sort of knowledge base during translation.  
  
---
  
## UI Integration  
  
### Plugin Settings  
  
Plugins can provide configurable settings that users can adjust globally or per project. Implement `get_setting_infos` to return a dictionary of settings.  
  
**Types supported**: `str`, `text`, `password`, `bool`, `num`, `display`.
For example, to add a setting to RPGMTL:  
```python
    def get_setting_infos(self : MyPlugin) -> dict[str, list]:
        return {
            "myplugin_setting": ["This setting does something!", "bool", False, None]
        }
```  
  
The first parameter is the description of the setting.  
The second is the setting type:  
- `"str"`       Standard string input.  
- `"text"`      Multi-line text block.  
- `"password"`  Obfuscated string input.  
- `"bool"`      Boolean checkbox (True/False).  
- `"num"`       Numeric input (will match either Python int or float).  
- `"display"`   Read-only text, used purely to display the description parameter.  
  
The third is the default value.  
The fourth is the list of possible values, to display an option box. If you don't wish to use one, set it to None.  
  
### Plugin Actions
  
Actions are buttons that appear within a specific file view in the UI. Implement `get_action_infos` to define the icon, label, and callback function.  
  
```python
    def get_action_infos(self : MyPlugin) -> dict[str, list]:
        return {
            "myplugin_file_action": ["assets/images/setting.png", "This button does something", self.callback]
        }
```  
  
The first parameter is the path towards the Action icon. You can reuse an existing one from the `assets/images` folder or create your own icon and put it in `assets/plugins`.  
The second parameter is the Action name displayed on the button.  
The third parameter is the function callback to be called when the user will press this button.  
An example of a callback is defined as such:  
```python
    def callback(self : MyPlugin, name : str, file_path : str, settings : dict[str, Any] = {}) -> str:
        """
            name: Project name
            file_path: File path from which the action has been invoked
            settings: Current plugins settings in given context
            
            return value: A string displayed to the user
        """
        try:
            #  
            # Do stuff...
            #
            # You can access a plugin setting for that project as such:
            # settings["myplugin_setting"]
            # Modifying them here is considered an undefined behavior.
            #  
            return "Hello world!" # the returning string is displayed to the user
        except Exception as e:
            self.owner.log.error(f"[MyPlugin] Action 'callback' failed with error:\n{self.owner.trbk(e)}")
            return "An unexpected error occured, please check the logs." # same here, any returning string is displayed to the user
```  
  
If you wish to restrict actions to specific files, you can either:  
- Add a check in the callback:  
```python
    def callback(self : MyPlugin, name : str, file_path : str, settings : dict[str, Any] = {}) -> str:
        if file_path != ...
            return "You can't use this action on this file"
        else:
            ...
```  
  
- In your implementation of `match`, return False for the given file to not show any actions for this plugin:  
```python
    def match(self : MyPlugin, file_path : str, is_for_action : bool) -> bool:
        if is_for_action:
            if file_path != something:
                return False
        # else
        # return the usual
        # ...
        #  
```  
  
### Plugin Tools
  
Tools are buttons that appear on the project dashboard.  
* **Simple Tools**: Execute a command immediately (optionally with a confirmation message).  
* **Complex Tools**: Open a dialog to request parameters from the user before execution.  
  
```python
    def get_tool_infos(self : MyPlugin) -> dict[str, list]:
        return {
            "myplugin_simple_tool": ["assets/images/setting.png", "Simple Tool", self.callback, {"type":self.SIMPLE_TOOL, "message":"Do something?"}]
        }
```  
`message` is an optional confirmation message displayed before execution.  
  
Complex tools open a page requesting specific parameters from the user before executing. Parameter definitions follow the identical format used for Plugin Settings.  
Example for a Complex tool:

```python
    def get_tool_infos(self : MyPlugin) -> dict[str, list]:
        return {
            "myplugin_complex_tool": [
                "assets/images/setting.png", "Complex Tool", self.callback,
                {
                    "type":self.COMPLEX_TOOL,
                    "params":{
                        "myplugin_complex_tool_0":["Some text", "display", None, None],
                        "myplugin_complex_tool_A":["Checkbox", "bool", True, None],
                        "myplugin_complex_tool_B":["Integer", "num", -1, None],
                        "myplugin_complex_tool_C":["Float", "num", 1.0, None],
                        "myplugin_complex_tool_D":["Text", "str", "RPGMTL", None],
                        "myplugin_complex_tool_E":["Paragrah", "text", "Hello\nworld!", None],
                        "myplugin_complex_tool_F":["Password", "password", "12345", None],
                        "myplugin_complex_tool_G":["Selection", "int", 3, [1, 2, 3, 4, 5, 6]]
                    },
                    "help":"This tool does something"
                }
            ]
        }
```  
The parameters follow the same format as for the settings.  
  
When used, both will trigger the callback. Callbacks have the same format for both types:  
```python
    def callback(self : MyPlugin, name : str, params : dict[str, Any]) -> str:
        """
            name: Project name
            params: The parameters. Empty dict for a Simple tool.
            return value: A string displayed to the user
        """
        try:
            #  
            # Do stuff...
            #  
            return "Hello world!" # the returning string is displayed to the user
        except Exception as e:
            self.owner.log.error(f"[MyPlugin] Tool 'callback' failed with error:\n{self.owner.trbk(e)}")
            return "An unexpected error occured, please check the logs." # same here, any returning string is displayed to the user
```  