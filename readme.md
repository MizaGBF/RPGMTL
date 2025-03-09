# RPGMTL  
Small Tool to create Translation Patches for RPG Maker games (from XP to MZ) and more.  
  
## Table of contents  
* [Introduction](introduction)  
* [Installation](installation)  
* [Usage](usage)
* [Project Management](project-management)
* [Translation](translation)
* [Advanced Usage](advanced-usage)
* [Plugins](plugins)
* [API](api)
  
## Introduction  
  
### What is it?  
RPGMTL is a tool, written in Python, allowing you to extract, translate and patch strings from your Games.  
It works via a small web server, and the UI uses your own web browser.  
This system allows multiple people to work at the same time on the same project.  
  
### What's new?  
This 3rd version of RPGMTL is an entire rewrite.  
It's now more robust, and more flexible with a Plugin system.  
All your Translation Projects are managed in the same folder.  
  
## Installation  
Start by getting a copy of this repository.  
Either git clone:
```
git clone git@github.com:MizaGBF/RPGMTL.git
```  
or use the **Green** Code button on top and download as ZIP (Don't forget to unzip).  
  
Next, you need Python 3.13 installed.
An older version might work, but isn't supported.  
  
Finally, install the [requirements](https://github.com/MizaGBF/RPGMTL/blob/master/requirements.txt).  
Run the following command, in the same folder:  
```
python -m pip install -r requirements.txt
```  
  
## Usage  
  
### Quickstart
Simply run `rpgmtl.py` to start a small web server.  
  
Then you can access it with your favorite web browser.  
`localhost:8000` should be the default address.  
  
To stop it, use the *Shutdown* button on the top left of the Home Page, or press `CTRL+C` on the server console.  
An Autosave is ran on shutdown, and also every minute otherwise.  
  
> [!WARNING]  
> Don't close the console to shut it down! The abrupt stop might result in data losses or corruption.  
  
### Settings
Before starting anything, you can tinker with the various settings.  
Global settings will affect every new projects.  
They can be overrided individually for each project, if needed.
  
### HTTPS
The project is intended to be used on a local network.  
If you wish to access it remotely, it's **recommended** to enable HTTPS.  
You'll need to have a valid certificate and key.  
Place them in the folder and run **once**:  
```
python rpgmtl.py --https name_of_your_cert name_of_your_set
```  
If everything goes well, `SSL is enabled` should appear in the log.  
The certificate and key locations will be saved for the next use.  
  
If you wish to revert this setting, run **once**:  
```
python rpgmtl.py --http
```  
RPGMTL will *forget* these file locations.
  
## Project Management  
  
### Creation  
On the Home Page, click on `New Project`.  
A window will open. Select the location of the executable, of the game you wish to translate.  
You'll then be asked a project name. This name will be the one used for the project folder and in the Web UI.
Once done, hit `Create`.  
  
> [!NOTE]  
> Your Project files are located in the **projects** folder.  
  
> [!IMPORTANT]  
> The game you wish to translate must be on the same machine as RPGMTL.  
> It also means, if you access RPGMTL remotely, this function will softlock RPGMTL until someone select the game.  
  
### Project Structure  
If you go into the `projects` folder and into your project folder, you'll see:  
* `edit`: This is where you can add additional files to put in the final patches. Such as translated images, etc... The inside must mirror the game folder structure.  
* `originals`: This is where RPGMTL keeps a copy of the targeted game files. Although it's recommended to keep a clean copy of your game, you'll find original files here, if needed.  
* `release`: This folder only appears upon using the `Release a Patch` button. Your translated files will appear inside, and only the translated ones. Unaltered and ignored ones won't be copied inside.  
* `config.json`: A file containing various infos about your project.  
* `strings.json`: A file containing the game strings and translations. Backups are created when doing various operations (such as extracting) but nothing less. Feel free to do manual backups if you wish.  
  
More files and folders might appear.  
For a general use, you only need to care about the `edit` and `release` folders.  
  
### Deletion  
* Make sure RPGMTL isn't running.  
* Go into the `projects` folder and delete the project you wish to remove.  
  
## Translation  
  
### Browsing Game Files  
On your project page, click on `Browse Files`.  
Here you'll be able to go through the detected files.  
You can set a file to be **ignored** by pressing `CTRL+Left Click` on it. It'll then appear red.  
Some RPG Maker MV/MZ files are set to be ignored by default.  
  
### Modifying Strings  
Click on a file to open the list of strings found inside.  
Strings are listed in groups, and the group name, if it exists, is show on the top left. It's mostly here for context and as a visual aid.  
  
The list shows, on the left, original strings and, on the right, translations.  
You can click on one to open the editing box.  
All occurences of a string are, by default, linked. So, **if you translate a string**, all occurence of that string will have this translation.  
You can **change** this behavior by pressing `Shift+Left Click` on a string you wish to unlink. Its box will become green.
You can also set a string to be ignored, as for files, by pressing `CTRL+Left Click`. It'll be skipped during the patching process.  
Finally, to delete a translation, click on it and on the *Trashbin* button.
  
### Machine Translation  
  
When modifying a string, you have the option to get a machine translation using the yellow *Translate* button.  
Doing so will put the translation in the editing area, for you to modify.  

If you wish to translate a whole file, use the dedicated button on top of the string list.  
Be aware rate limits and the like might cause you issues if you plan to translate a lot of files this way in a short time span.  
Please refer to the [Plugins](plugins) section if you wish to extend RPGMTL capabilities in that regard.  
  
## Advanced Usage  
  
### Game Updates  
If you're translating a recently released game, you can easily update your project to the latest version.  
Click on `Update the Game Files` and select where this new version is. Fresh files will be fetched.  
You can then click on `Extract the Strings` to update the string list.  
A backup of `strings.json` will be created beforehand, just in case (be aware it exists).  
  
When browsing your updated string list, you might spot some with a yellow rectangle on the left: It indicates which strings got added in this new version.  
  
### Custom Patches  
You might want to automate the patching of the some part of the game.  
This can be done via the `Add a Fix` menu.  
Inside, you can set small Python code snippets, which will run during the patching process (after everything else, to be exact).  
  
To do so, create one and set what filename this code targets. For example, to target all the RPG Maker MV/MZ map files, you can set `data/Map`. Or to target a specific file, set its whole path (for example `data/Map001.json`).
  
In the `Fix Code` text box, you can put the Python code to run.  
You have access to a variable called `helper` to help you with your modifications.  
It includes the following:  
* A `content` bytes attribute: It's the patched file, as bytes, and what you must modify.  
* A `modified` bool attribute: Set it to True if you modified the file `content`.
* `from_str` method to get a String version of the `content`. `to_str` allow you to convert it back and set it inside `content`.  
* `from_json` and `to_json` do the same, with JSON content.  
  
Example, to edit a RPG Maker MV/MZ System.json locale:  
File match is:  
```  
data/System.json
```  
Code is:  
```python
d = helper.to_json() # get the content as json
d["locale"] = "en_UK" # modify the locale
helper.from_json(d, separators=(',',':')) # convert it back to bytes
helper.modified = True # raise modified flag to True
```  
  
The `PatcherHelper` is defined at the start of `rpgmtl.py`, if you wish to take a closer look at it.  
  
### Import Strings from older RPGMTL
This button allow you to import `strings.json` and `strings.py` files from older RPGMTL versions.  
Be aware it's a convenience feature and far from perfect.  
  
## Plugins  
  
### Existing Plugin  
  
The following File Plugins are available:  
* `CSV`: For CSV files.  
* `Javascript`: For Javascript Files.  
* `JSON`: For JSON files.  
    * It exposes one setting to merge RPG Maker Show Text/Script event commands as one string. You must re-extract the strings after changing it.
* `RM Marshal`: For Ruby Marshal files, such as RPG Maker rxdata, rvdata and rvdata2 files.  
    * It exposes one setting to merge RPG Maker Show Text/Script event commands as one string. You must re-extract the strings after changing it.
    * It exposes two File Actions to extract content and Ruby scripts, from those files.
* `Ruby`: For Ruby scripts. It's also called by `RM Marshal` to patch RPG Maker XP/VX/VX Ace scripts.  
  
The following Translator Plugins are available:  
* `TL Google`: For Google Translations.  
    * It exposes two settings to set the source and target languages.  
  
### Making your own Plugin  
  
File Plugins must inherit from the `Plugin` class defined in `plugins/__init__.py`.  
Translator Plugins must inherit from the `TranslatorPlugin` class defined in `plugins/__init__.py`.  
  
Your Plugins must go into the `plugins` folder. They will be automatically loaded on startup.  
I won't go into more details, check the existing Plugins for more informations.  

## API  
Below is the server API, for documentation purpose.  
An API call always return the following JSON:  
```json
{
    "result":"ok",
    "data":{},
    "message":"A popup message!"
}
```  
  
* `result` can be either `ok` or `bad`.  
* `data` content varies depending on the call. See below. Note: It's absent if the `result` is `bad`.  
    * When present inside `data`, `config` and `name` are automatically read.  
* `message` is a string, which will be displayed as a popup. It's optional.  
  
### API Endpoints  
All requires POST requests.  
The ones without parameters don't need to be sent a payload.  
  
```
/api/main
Return in data: array of project names, version string
```
  
```
/api/shutdown
```
  
```
/api/update_location
Return in data: game 'path' string
```
  
```
/api/update_location
Payload: project 'name'
Return in data: project 'name', project 'config'
name config
```
  
```
/api/translator (Global)
Return in data: 'list' of translator plugins, 'current' selected plugin
```
  
```
/api/translator (Project specific)
Payload: project 'name'
Return in data: project 'name', project 'config', 'list' of translator plugins, 'current' selected plugin
```
  
```
/api/update_translator (Global)
Payload: 'value' to set the current translator
```
  
```
/api/update_translator (Project Specific)
Payload: project 'name', 'value' to set the current translator
Return in data: project 'name', project 'config'
```
  
```
/api/update_translator (Project Specific, reset the setting)
Payload: project 'name'
Return in data: project 'name', project 'config'
```
  
```
/api/settings (Global)
Return in data: menu 'layout', global 'settings'
```
  
```
/api/settings (Project Specific)
Payload: project 'name'
Return in data: project 'name', project 'config', menu 'layout', global 'settings'
```
  
```
/api/update_settings (Global)
Payload: setting 'key', new setting 'value'
```
  
```
/api/update_settings (Project Specific)
Payload: project 'name', setting 'key', new setting 'value'
Return in data: project 'name', project 'config'
```
  
```
/api/update_settings (Project Specific, reset the setting)
Payload: project 'name'
Return in data: project 'name', project 'config'
```
  
```
/api/new_project
Payload: project 'name', game 'path'
Return in data: project 'name', project 'config'
```
  
```
/api/extract
Payload: project 'name'
Return in data: project 'name', project 'config'
```
  
```
/api/browse
Payload: project 'name', folder 'path'
Return in data: project 'name', project 'config', folder 'path', list of 'files', list of 'folders'
```
  
```
/api/patches
Payload: project 'name'
Return in data: project 'name', project 'config'
```
  
```
/api/open_patch
Payload: project 'name', patch 'key'
Return in data: project 'name', project 'config', patch 'key'
```
  
```
/api/update_patch (Create/Edit patch)
Payload: project 'name', patch 'key', patch 'newkey', patch 'code'
Return in data: project 'name', project 'config'
```
  
```
/api/update_patch (Delete patch)
Payload: project 'name', patch 'key'
Return in data: project 'name', project 'config'
```
  
```
/api/release
Payload: project 'name'
Return in data: project 'name', project 'config'
```
  
```
/api/import
Payload: project 'name'
Return in data: project 'name', project 'config'
```
  
```
/api/backups
Payload: project 'name'
Return in data: project 'name', project 'config', 'list' of backups
```
  
```
/api/load_backup
Payload: project 'name', backup 'file'
Return in data: project 'name', project 'config'
```
  
```
/api/ignore_file
Payload: project 'name', file 'path', ignore 'state'
Return in data: project 'name', project 'config', list of 'files', list of 'folders'
```
  
```
/api/file
Payload: project 'name', file 'path'
Return in data: project 'name', project 'config', file 'path', project 'strings', 'list' of strings in file, list of file 'actions'
```
  
```
/api/file_action
Payload: project 'name', file 'path', project 'version', action 'key'
Return in data: project 'name', project 'config'
```
  
```
/api/update_string
Payload: project 'name', file 'path', project 'version', action 'key'
Return in data: project 'name', project 'config'
```

```
/api/update_string (Edit Translation)
Payload:  project 'name', file 'path', project 'version', 'group' index, string 'index', 'string' translation
Return in data: project 'name', project 'config', file 'path', project 'strings', 'list' of strings in file
```

```
/api/update_string (Toggle Unlink/Ignore)
Payload:  project 'name', file 'path', project 'version', 'group' index, string 'index', toggle 'setting' (0 for unlink, 1 for ignore)
Return in data: project 'name', project 'config', file 'path', project 'strings', 'list' of strings in file
```

```
/api/translate_string
Payload:  project 'name', 'string' to translate
Return in data: string 'translation'
```

```
/api/translate_file
Payload:  project 'name', file 'path', project 'version'
Return in data: project 'name', project 'config', file 'path', project 'strings', 'list' of strings in file
'''