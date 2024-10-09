# RPGMTL  
Small tool to create MTL patches for RPG Maker games.  
  
## Supported files  
* JSON files (such as RPG Maker MV/MZ data files)  
* JS files (such as RPG Maker MV/MZ js files)  
* CSV files (such as RPG Maker MV/MZ externMessages.csv file)  
* RXDATA files (RPG Maker XP. EXPERIMENTAL).  
* RB files (RPG Maker Ruby scripts. EXPERIMENTAL).  
  
## Requirements  
* Tested on Python 3.11. At least 3.10 should be required.
* See [requirements.txt](https://github.com/MizaGBF/RPGMTL/blob/master/requirements.txt) for a list of third-party modules.  
* `python -m pip install -r requirements.txt`, in a terminal/command prompt, to install or update them.  
  
## Usage  
Upon starting the script in an empty folder, it will prompt you to select the location of a game.  
It will create two folders: `manual_edit` where you can add files you manually edited yourself (for examples, image files) and `untouched_files` which is a **backup** of your game files and will be used to read the strings from.  
It will also created a file named `patches.py`. More on it on a section below.  
  
Once done, you can use the first option `Generate strings.json` by typing `0`. It will generate two files named `strings.py` and `groups.json`. Future uses will create backups of `strings.py` (in case of a mistake or bug).  

### strings.py
While it has a `.py` file extension, it's not an executable script. Its content is actually more of a mix of python and json.  
Open it in your favorite text editor:  
```python
#@@@data/Actors.json
"Hero":null
"Mage":null
"Warrior":null
```
(This is an example for illustration purpose)  
Each line of the file is a string, followed by a colon `:` and another string (if it's translated) or `null` if it's not.  
There are also special strings, which start with:  
* `#@@@`: Indicates which file this string is first encountered in.  
* `#%%%`: Add it so that the script to ignore the file entirely. Its strings will be discarded at the next generation..  
* `#@TALKING:`: Used for events. Indicates you which character is talking.  
* `#`: Use it if you wish to add a comment (NOTE: Comments are LOST when regenerating `strings.py`)  
  
These special strings can be modified by modifying them at the top of the script.  
I plan to build a dedicated editor, eventually.  
  
### groups.json  
You can ignore this file entirely, it's used by the auto translate feature.  
  
### manual_edit Folder  
Simply put the other files that you modified yourself inside.  
For example, if you want to modify `js/plugins.js`, make a new folder named `js` and copy the original `plugins.js` inside. Then edit it.  
When you'll create the patch, it will automatically be copied to the `release` folder. Do note that it overwrites any file created by the patch (if you have `A.whatever` in `manual_edit` and this file is also patched by the script, your will have the priority. Check the next section if you need to make specific modifications to patched files.  
  
### patches.py  
Used for fine tuning. You can set python code to run for specific files.  
It requires you to know a bit of python.  
The file will must look this way:  
```python
#@@@data/System.json
data["locale"] = "en_UK"
```  
The first line starting with `#@@@` indicates which file(s) are patched (you can put multiples separated by a semicolon. Example: `#@@@A.json;B.json;C.json` and the code will run for each of these files).  
The rest is python code to modify the file(s).  
For JSON files, you can simply access the data variable directly.  
In the example above, I modify the `locale` value to english.  
For text files (javascript, for example), a bit of trickery is involved as you'll have to mutate the data variable:  
```python
#@@@Myfile
global data_set
# do stuff
# ... for example, data = data.replace("my_string", "cool_string")
# end
data_set = data # set this variable
```  
If `data_set` is detected to not be `None` after the execution, its content is set back inside `data`.  
  
You can chain as many patches as you wish:  
```python
#@@@System.json
data["locale"] = "en_UK"

#@@@System.json
data["gameTitle"] = "Cool game"
```  
  
And, of course, the content in-between these lines must be valid python code.  
There is no real limit. Just make sure to escape the quote with a backslash. Use `\n` for new lines.  
Note: The code will always run AFTER the patching of the strings.  
  
The delimiter `#@@@` can be modified by changing `PATCH_STR` at the top of `rpgmtl.py`, like the others.  
  
### Settings  
The Settings menu allows you to change the script behavior.  
Settings are saved in `settings.json`.  
Currently:  
* **Multi-part mode**: Allows you to breakdown strings.py into multiple files (up to 10) for big projects. I recommend to enable it before starting any translation on your current project.  
* **Next loading file select**: The scripts will ask you to load either strings.py or part files the next time it loads strings. Useful if you tinkered with the Mult-part setting midway during a project.  
  
### Game update  
If a game got updated and you want to update the string list, simply use the fourth option `Game got updated` and select your game folder again. It will recreate the `untouched_files` folder. You can then reuse the first option `Generate strings.json`. It will add the new strings and delete the ones not used anymore.  
Make sure to not mix and matches different games by mistake.  
One thing you can do next is compare `strings.py` with one of its backup (usually `strings.bak-1.py`) in a file comparator, to see what strings changed and modify them quickly.
  
### Machine translation  
The script uses the [deep translator](https://github.com/prataffel/deep_translator) module for translations.  
This feature is still experimental and isn't perfect.
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
Another experimental feature.
Found in the the `test_server` folder are a few files to test the strings directly in game.  
Do note that it's VERY experimental and has only be tested in a few RPG Maker MV/MZ games.  
To use:  
1. Copy the content of `test_server` to the game folder.  
2. Copy your `strings.json` and `groups.json` to the game folder.  
3. Start a local web server. A way to do it is, with Python, is using the command `python -m http.server`. On Windows, you can double click `start_server.bat`.  
4. Open any Chromium-type Browser and go to `http://localhost:8000/server.html`.  
  
The strings will cycle one by one.  
You can use CTRL to skip ahead.  
You can also open the Dev tools (using F12), go to the Console tab and change the value of `test_count` to change the next line. Example, `test_count = 0;` will reset to the beginning.  
  
