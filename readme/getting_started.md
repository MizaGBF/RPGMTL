# RPGMTL  
  
# Getting Started with Your Translation Project  
  
This guide provides a walkthrough for setting up a translation project in RPGMTL. It assumes that RPGMTL is running and accessible via your web browser (typically at [http://localhost:8000](http://localhost:8000)).  
  
For installation instructions, please refer to the main [README.md](../readme.md).  
  
## Configuration  
  
### Global and Project Settings  
  
When accessing RPGMTL for the first time, review the settings. Settings modified through the main page are global and apply to all projects by default. However, settings can be overridden on a per-project basis, in which case the project-specific configuration takes priority.  
  
### Translator Plugins  
  
Default translators can also be configured globally or overridden per project. You can independently set translator plugins for two types of operations:
* **Single Translations**: Triggered by the manual translation button during editing. A simple translator (e.g., Google Translate) is recommended for this.
* **Batch Translations**: Triggered by the "Translate this file" or "Batch Translate" buttons. AI/LLM-based translators (e.g., Google Gemini) are recommended for processing multiple lines efficiently.  
  
---
  
## Creating a Project  
  
1. Click the **New Project** button on the home page.
2. Browse the filesystem to locate the game directory. The browser will display folders and executables.  
3. Select the game's executable if it is located at the root of the game directory. Otherwise, navigate to the appropriate folder and click **Select this Folder**.  
4. Input a name for the project.  
  
The project is created within the `projects/` sub-folder of the RPGMTL directory. During creation, RPGMTL backs up relevant files to the `originals` directory within your project folder. If the game is updated later, use the **Update the Game Files** button to update these files.  
  
---
  
## Workflow  
  
### Extracting Strings  
  
The initial project page will display limited options. The first step is to click **Extract the Strings**. RPGMTL will scan the game files and catalog all translatable strings. Once complete, additional management buttons will become available.  
  
### Actions and Management  
  
The **Actions** section provides several utilities:
* **Release a Patch**: Generates patched game files in the `release` folder.  
* **Save and Close**: Saves the project and closes it. This is useful before manually modifying local project files.  
* **Replace Strings in batch**: Performs a find-and-replace operation across all strings in the project.  
* **Backup Control**: Reverts `strings.json` (the translation database) to previous versions. Automatic backups are created before destructive operations.  
* **Knowledge Base**: Manages the context and terminology used by AI translator plugins.  
* **Notepad**: A built-in area for taking project notes.  
* **Import**: Allows importing translations from other RPGMTL projects or RPGMakerTrans V3 projects.  
  
The **Tools** section contains utilities (such as text-wrap helpers) that can be bookmarked for quick access.  
  
### Translation Process  
The **Translate** section contains the primary workflow buttons:  
* **Browse Files**: Navigate and edit extracted strings on a per-file basis.  
* **Add a Fix**: Allows the application of custom Python code to specific files for advanced patching. These scripts run during the **Release a Patch** process.  
* **Batch Translate**: Automatically translates all files (excluding those set to be ignored) using the selected batch translator.  
  
---
  
## File and String Browsing  
  
### File Browser  
  
The file browser displays the project's directory structure and translation progress.  
* **Ignored State**: `Ctrl+Click` a file to toggle its ignored state. Ignored files (highlighted in red) are not modified during the patching process.  
* **Virtual Folders**: Some archives or large files (e.g., RPG Maker `CommonEvents.json`) appear as virtual folders, allowing you to edit their contents as separate virtual files.  
  
### String List  
  
Clicking a file opens its string list. Strings are displayed in their order of occurrence and are automatically grouped by context (e.g., "Command: Show Text").  
* **Editing**: Click the right-hand area of a string to open the editing panel.
* **Linking**: By default, identical strings share the same translation project-wide. `Shift+Click` a string to switch it to **Local** mode, allowing a unique translation for that specific occurrence.  
* **Ignoring**: `Ctrl+Click` a string to ignore it during patching.  
  
For a full list of keyboard shortcuts and advanced features, click the **Help (?)** button in the top-right corner of the interface.  
  