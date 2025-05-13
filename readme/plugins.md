# RPGMTL  
  
# Plugins Manual  
  
## Introduction  
  
Plugins are loaded on RPGMTL boot.  
In case of an error, the plugin is skipped and an error message will appear in the logs.  
There are two types of Plugin:  
- Plugins, also referred as File Plugins below. They extract and patch strings in game files.  
- Translator Plugins, which interface to Translator APIs and such.  
  
## Plugin develoment  
  
### Quickstart
  
Create a new Python file in the `plugins` folder.  
  
For File Plugins, import `from . import Plugin`.  
For Translator Plugins, import `from . import TranslatorPlugin`.  
  
Then create a class inheriting from those type and implement the functions you wish to overload.  
  
For File Plugins, it will be at least the following methods:  
- `match`  
- `read` (for standard File Handling)  
- `write` (for standard File Handling)  
- `is_streaming` (for File Streaming)  
- `read_streaming` (for File Streaming)  
- `write_streaming` (for File Streaming)  
  
If `is_streaming` return True for a given file name, File Streaming will be used.  
It uses a handle instead of loading the whole file in memory.  
It's Intended for large files.  
  
For Translator Plugins, it will be at least the following methods:  
- `translate`  
- `translate_batch`  
  
Refer to the base class definitions in `plugins/__init__.py` if you need more infos or a list of all methods you can use.  
Refer to existing plugins if you need examples.  
  
### Extracting Strings  
  
In `read` or `read_streaming`, you must return a list of String Group.  
A String Group is a mere Python list of strings.  
The first string of a String Group is its name.  
It can be empty but MUST be present.  
It will be displayed to the user at the top of the String Group.  
Following it are the extract strings, in order.  
  
Hence why the return type is list[list[str]].  
For Example:  
```python
# Example of returned list of String Groups:
results = [
    ["Group 1", "string 1", "string 2"],
    ["Group 2", "string 3"],
    ["Group 3", "string 4", "string 5", "string 6", "string 7"],
    ["Group 4", "string 8"]
]
```  
Don't add empty strings to your String Groups.  
You can, however, add a String Group without strings, just to display something to the user between groups of strings:  
```python
# Example of returned list of String Groups:
results = [
    ["Group 1", "string 1", "string 2"],
    ["Hello World!"],
    ["Group 2", "string 3", "string 4", "string 5"],
    ["Group 3", "string 6"]
]
```  
  
### Patching Strings  
  
In `write` or `write_streaming`, you must modify the file content with modified strings and return it, along with a boolean indicating if the content has been modified.  
How to proceed will depend on the file format.  
However, you can use the `WalkHelper` to help with it.  
Add it to your import:  
```python
from . import Plugin, WalkHelper
```  
And instantiate it in your function:  
```python
helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
```  
  
This class helps you patch strings and make sure nothing is corrupted.  
If it raises an error, it means your writing function isn't following the same path as your reading one.  
To patch a string with:  
```
# In this example, let's imagine we're patching a string in a Python dictionary:
data["mystring"] = helper.apply_string(data["mystring"], group_name) # The returned value will be either the same string OR the patched string if it exists
# Note 1: group_name is an OPTIONAL parameter and will raise an error if it's not the exact same as at the time of extracting this string.  
  
# Note 2: If the string can be modified right away for some reason, you can use str_modified:  
tmp = helper.apply_string(data["mystring"], group_name)
if helped.str_modified:
    # do stuff ...
    data["mystring"] = tmp
```  
If at least one string has been modified, the `modified` parameter of the Helper will be set to True.  
You can use it in the return tuple of your writing function.  
  
### Archive and Virtual files  
  
For archive type files (i.e. files containing other files), you might want to separate them in the UI.  
To do so, add an empty group with a special name uring the extraction:  
```python
# Example of returned list of String Groups:
results = [
    [self.owner.CHILDREN_FILE_ID + "script.txt"],
    ["Group 1", "string 1", "string 2"],
    [self.owner.CHILDREN_FILE_ID + "data.txt"],
    ["Group 2", "string 3", "string 4", "string 5"],
    ["Group 3", "string 6"]
]
```  
`self.owner.CHILDREN_FILE_ID` is defined in the main `RPGMTL` class.  
  
In this example, Group 1 will appear under the Virtual File `script.txt` in the user interface, and Groupe 2 under `data.txt`.  
Your plugin is still responsible of extracting and patching their strings.  
Although you can also call other plugins if you wish:  
```python
groups = []
for file in my_archive:
    # Way 1
    groups.append([self.owner.CHILDREN_FILE_ID + file.name])
    # extract String Groups and append them to groups...
    
    # Way 2
    groups.append([self.owner.CHILDREN_FILE_ID + file.name])
    # we call another plugin
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
    # we call another plugin
    if "PluginName" in self.owner.plugins: # Check if this plugin exists and is loaded
        self.owner.plugins["PluginName"].reset() # Reset its state (Don't forget!)
        content = self.owner.plugins["PluginName"].whatever_function(helper, ...) # Do whatever you want with it, make sure to pass the helper
        if helper.modified:
            # update the file content
            # ...
```  
  
### Translator Plugin Batch Format
  
You can override a `TranslatorPlugin` `get_format` so that `translate_batch` will receive and return data in a different way.  
If set with `TranslatorBatchFormat.DEFAULT`:  
Input is a list of string to translate.  
Output is a list, of same size, of translated strings (or None if one failed to translate). Indexes must correspond with the Input.  
 
If set with `TranslatorBatchFormat.CONTEXT`:  
Input format is the following:  
```json
{
    "file":"FILE",
    "number":BATCH_NUMBER,
    "strings":[
        {
            "id":"STRING_ID",
            "parent":"GROUP OF WHICH THIS STRING IS PART OF",
            "source":"ORIGINAL_STRING",
            "translation":"TRANSLATED_STRING"
        },
        {
            "id":"STRING_ID",
            "parent":"GROUP OF WHICH THIS STRING IS PART OF",
            "source":"ORIGINAL_STRING"
        }
    ]
}
```  
It contains even translated strings, for context.  
  
Output format is:  
```json
{
    "STRING_ID":"TRANSLATION"
}
```  
  
## Plugin Settings  
  
Both Plugin types can provide a list of settings to RPGMTL.  
The user can then change those settings at a Global level or per projects.  
  
To do so, implement the function `get_setting_infos`.  
For example:  
```python
    def get_setting_infos(self : MyPlugin) -> dict[str, list]:
        return {
            "myplugin_setting": ["This setting does something!", "bool", False, None]
        }
```  
  
This add one setting to RPGMTL.  
The first parameter is the description.  
The second is the type of the setting. It can be `"str"`, `"bool"`, `"num"` (Which can be either a Python Integer or Float).  
The third is the default value.  
The fourth is the list of possible values. If you don't wish to provide one, set it to None.  
  
## Plugin Actions
  
Actions are buttons than the user can press in a file, to perform specific actions provided by File Plugins.  
  
To do so, you must first implement the function `get_action_infos`.
For example:

```python
    def get_action_infos(self : MyPlugin) -> dict[str, list]:
        return {
            "myplugin_file_action": ["assets/images/setting.png", "This button does something", self.callback]
        }
```  
  
The first parameter is the path towards the Action icon. You can reuse an existing one from the `assets/images` folder or create your own icon and put it in `assets/plugins`.  
The second parameter is the Action name displayed on its button.  
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
            return "Hello world!"
        except Exception as e:
            self.owner.log.error("[MyPlugin] Action 'callback' failed with error:\n" + self.owner.trbk(e))
            return "An error occured."
```  
  
If you wish to restrict actions to specific files, you can either:  
- Add a check in the callback.  
- In your implementation of match, return False for the given file to not show any actions for this plugin:  
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