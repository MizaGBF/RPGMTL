# RPGMTL  
  
# KiriKiri Plugin Manual  
  
## Quick Overview  
  
The KiriKiri plugin targets scripts from the KiriKiri (KrKr/TVP) engine, specifically KAG scripts (`.ks`) and TVP JavaScript scripts (`.tjs`).  
  
**Requirement**: The **JavaScript Plugin** must be enabled to parse `.tjs` files.  
  
## Workflow

The plugin does not handle the decryption or extraction of `.xp3` archives. You must extract the scripts manually before importing them into RPGMTL.  

### Preparation  
  
Extract the game scripts into a folder named `patch`. In most cases, you will need to register this folder with the engine:  
1. Move `patch/system/Config.tjs` to `patch/Config.tjs`.  
2. Append the following code to `patch/Config.tjs` to ensure the engine loads your patched files:  
```javascript
Storages.addAutoPath(System.exePath + "patch.xp3>scenario/");
Storages.addAutoPath(System.exePath + "patch.xp3>system/");
```  
  
*If `patch.xp3` already exists, increment the filename (e.g., `patch2.xp3`). Add additional `addAutoPath` lines for other directories (like images) as needed.*  
  
### Translation and Patching  
  
Import the extracted files into RPGMTL. After completing your translations, use the **Release a Patch** button. The patched files will be located in `<PROJECT_ROOT>/release/patch/`.
  
### Repacking
Use an XP3 repacker to pack the contents of the `release/patch/` folder into a `patch.xp3` archive and place it in the game directory.  
  
## Technical Notes  
  
* **Character Escaping**: If a line in your translation must start with the `[` character, you must double it (`[[`) to prevent it from being interpreted as a KAG command.  
  
## Development References  
  
* [KiriKiri KAG Documentation](https://kirikirikag.sourceforge.net/contents/index.html)  
* [KirikiriTools (GitHub)](https://github.com/arcusmaximus/KirikiriTools)  