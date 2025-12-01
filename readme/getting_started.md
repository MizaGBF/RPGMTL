# <img src="./assets/ui/favicon.svg" width="40"> RPGMTL  
  
Please refer to the main readme for installation.  
This assumes you have RPGMTL working and can access it through [localhost](http://localhost:8000) in your Internet Browser.  
  
Other readme files might go into deeper details into some aspects discussed below.  
  
## Getting started with your translation project  
  
If it's your first time ever launching RPGMTL, you can start by accessing the settings if you wish.  
Most of them probably don't need to be changed, except for the Translators'.  
Settings modified through the main page are global, meaning all projects will use them.  
If you modify a setting via a project, the modification will have priority and override the global settings for that particular project.  
  
Next, you can also change the default translators.  
Like for settings, defaults can be overriden on a project basis.
You can independently set the Translator plugin used for single translations and for batch translations.  
Single translations refer to the yellow translation button during editing.  
Batch translations refer to the `Translate this file` and `Batch Translate` buttons, which will edit many lines at a time.  
My recommendation is simple Translator plugins (for example Google Translate) for Single translations, and AI/LLM for batch tranlations (for exampel Google Gemini).  
  
Once set, you can start creating a project with the `New Project` button.  
You can then browse through the filesystem of the machine where RPGMTL is running from.  
Two things will show: Folders and executables. The later are usually at the root of a game directy.  
If it's the case for you, select the executable of the game you wish of translate.  
If it's not, there is a button at the bottom to `Select this Folder`.  
After this, you'll be asked to input a project name.  

The project will be created in the `projects/` sub-folder, in RPGMTL's directory.  
When creating a new project, RPGMTL backup relevant files in this folder, in the `originals` directory.  
If the game ever updates and you require to update your translation, use the `Update the Game Files` button to repeat this process.  
  
You're in theory on the project page and only a few buttons appear for now.  
Before anything, you can start by modifying your project settings, if there is anything particular it requires.  
If not, the next step is to `Extract the Strings`.  
RPGMTL will go through the game files and catalog the files.  
Once it's done, new buttons will appear on the project pages.  
  
Under Actions, you'll find the buttons you saw before, along new ones:  
- `Release a Patch` will create patched file in the `release` folder.  
- `Unload from Memory` will save the project and close it. Useful if you're an experimented user and needs to modify local RPGMTL project files.  
- `Replace Strings in batch` is exactly what it sounds like. You can set a string and what to replace it with. It'll go over all strings and apply the modification.  
- `Backup Control` allows you to revert to previous versions of `strings.json`, the file containing the translations. A new backup is made before each destructive operations.  
- `Knowledge Base` is a page to edit the knowledge base for AI Translator plugins.  
- `Notepad` allows you to take notes.  
- The `Import` buttons allow you to import string translations from other RPGMTL projects (any version) and RPGMakerTrans V3 projects.  
  
Under Tools, you have utilities (mostly text-wrap related ones), which you can favorite to make them directly accessible on the project page.  
During the first string extraction, the relevant ones are automatically favorited for your project.  

Finally, under Translate are the most important buttons:  
- `Browse Files` allows you to browser the extracted strings, per file. More onto it further below.  
- `Add a Fix` allows you to add Python code to run on some file, for some more detailed file patching. The codes are run during the `Release a Patch` process. Check other readmes for details.  
- `Batch Translate` will go over each file, one by one (unless they're set to be ignored) and translate them with the selected Batch Translator.  
  
Next is the `Browse Files` menu explanation.  
First, there is the browsing view.  
On top, there is a search bar, that you can use to search strings.  
Below is the current translation progress. Do note that it updates upon changing page.  
Next are the directories in the current folder.  
And finally the files present in the current folder.  
  
You can CTRL+Click on a file to toggle its Ignored state (it will appear red). Ignored files won't be patched or modified.  

You might also notice grey folders with a slightly different icon. Those are virtual folders containing virtual files, used for some archive files or big files.  
A common example is the RPG Maker CommonEvents.json file. The file will still appear as normal in the file list, but a virtual folder will be accessible, with ALL common events separated in their own virtual file.  
Do note that if the base file (CommonEvents.json in our example) is ignored, all virtual files will be.  

Upon clicking a file, you'll access the string list of this file.  
On top will appear Action buttons, automatically added by relevant plugins, to perform specific actions.  
Below is the string list.  
Strings are in order of occurence in the file, and automatically grouped.  
For example, in a RPG Maker event script, you might see a `Command: Show Text` group with three strings: This is a text box command.  
  
Like files, strings can be set to be ignored with CTRL+Click. They won't be modified during patching.  
You can modify a translation by clicking on the right area, which will open the editing panel.  

Finally, the occurences of a same string share the same translation accross the whole project by default. But you can SHIFT+Click on a string to switch it to Local mode: The translation that you then set will be ONLY for this occurence of the string.  

There are many more shortcuts, features and so on available.  
Be sure to take a look at the Help button `?` on the top right corner.  


