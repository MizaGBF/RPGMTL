# RPGMTL  
Small tool to create MTL patches for RPG Maker MV and MZ games.  
For now, it's exclusively for JSON files of the data folder.  
  
### Requirements  
* Tested on Python 3.11.
* See [requirements.txt](https://github.com/MizaGBF/RPGMTL/blob/master/requirements.txt) for a list of third-party modules.  
* `python -m pip install -r requirements.txt`, in a terminal/command prompt, to install or update them.  
  
### First time  
1. Create a folder for the game you want to patch. It doesn't have to be in this game folder.  
2. Copy and paste rpgmtl.py inside.  
3. Run it.  
4. It will ask you to select the location of the game executable (Usually, Game.exe).  
5. It will create two folders: `manual_edit` where you can add files you manually edited (for examples javascript or image files) and `untouched_files` which is a **backup** of your game `data` and `js` folders.  
6. `patches.json` should also have been created. More on it on a section below.  
7. In the terminal, you can use the first option `Generate strings.json` by typing `0`. You can then use the second option to attempt to translate them or manually edit it with your favorite text editor.  
8. Once you're done, you can use the third option `Create patch` by typing `2`. A new folder called `release` which will contain your patched files. You can copy them to your game folder and overwrite to test them.  
  
Repeat step 8 if you update your translation.  
  
### strings.json  
It's composed of two parts:  
* The string list, called `strings`. You'll see the original string and its translation on the right. They are ordered by order of occurence in the game files and only the first occurence is saved.  
* The group list, called `groups`. It's used to improve the machine translation. You can ignore it.  
  
Backups are automatically created when using the tool.  
It will also tell you if you made an error in the JSON format.  
  
### manual_edit Folder  
Simply put the other files that you modified yourself inside.  
For example, if you want to modify `js/plugins.js`, make a new folder named `js` and copy the original `plugins.js` inside. Then edit it.  
When you'll create the patch, it will automatically be copied to the `release` folder.  
  
### patches.json  
Used for fine tuning. You can set python code to run for specific files.  
The default file is always:  
```python
{
"System.json":[
"data[\"locale\"] = \"en_UK\""
]
}
```  
Where it sets the value of the `locale` of `System.json` to `"en_UK"`.
You can add how many as you want and they must be grouped by files:  
```python
{
"System.json":[
"data[\"locale\"] = \"en_UK\"",
"data[\"gameTitle\"] = \"I changed the game title!!\""
],
"Items.json":[
"data[0]["description"] = \"Super strong item, for real!\""
]
}
```  
And, of course, it must be valid python code.  
Note: They will always run AFTER the patching of the strings.  
  
### Game update  
If a game got updated and you want to update the string list, simply use the fourth option `Game got updated` and select your game folder again. It will recreate the `untouched_files` folder. You can then reuse the first option `Generate strings.json`. It will add the new strings and delete the ones not used anymore.  
Make sure to not mix and matches different games by mistake.  
  
### Machine translation  
The script uses the [deep translator](https://github.com/prataffel/deep_translator) module for translations.  
By default, the script is set and intended to be used with Google Translate, and it targets the english language.  
You can change this behavior by changing those line:  
```python
from deep_translator import GoogleTranslator
```  
  
```python
TRANSLATOR = GoogleTranslator(source='auto', target='en')
```  
And the `translate_string` function if you want to go further.  
See the Github repository linked above for more informations on deep translator..  
  
### Test Server  
Found in the the `test_server` folder are a few files to test the strings directly in game.  
Do note that it has only be tested in a few RPG Maker MZ games.  
To use:  
1. Copy the content of `test_server` to the game folder.  
2. Copy your `strings.json` to the game folder.  
3. Start a local web server. A way to do it is, with Python, is using the command `python -m http.server`. On Windows, you can double click `start_server.bat`.  
4. Open any Chromium-type Browser and go to `http://localhost:8000/server.html`.  
  
The strings will cycle one by one.  
You can use CTRL to skip ahead.  
You can also open the Dev tools (using F12), go to the Console tab and change the value of `test_count` to change the next line. Example, `test_count = 0;` will reset to the beginning.  
  
