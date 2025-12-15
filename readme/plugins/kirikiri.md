# RPGMTL  
  
# KiriKiri Plugin Manual  
  
## Quick Overview  
  
The KiriKiri Plugin targets scripts from the KiriKiri (also known as KrKr or TVP) engine.  
  
**The Javascript Plugin is required** to parse `.tjs` files, so make sure it's present and enabled.  
  
## Usage  
  
This plugin targets only the KAG scripts (`.ks`) and TVP Javascript scripts (`.tjs`).  
The plugin **doesn't** handle decryption of `.xp3` files ans so on, as the method can vary from one game to another.  
  
Start by extracting those files from your targeted game, into a folder called `patch`.  
Optional but likely needed in most case:  
1. Move `patch/system/Config.ts` to `patch/Config.ts`.
2. Append the following code inside:  
```javascript
Storages.addAutoPath(System.exePath + "patch.xp3>scenario/");
Storages.addAutoPath(System.exePath + "patch.xp3>system/");
```
If patch.xp3 already exists, change it above for `patch2.xp3`, and so on.  
If you have other folders mattering (for example, image ones), add a new line in the same maner pointing to it.  
  
Now import the game into RPGMTL, make your edit then release the patch.  
The folder structure will likely be something like `<PROJECT>/release/patch/...`.  
Run your repacker of choice on the **patch** folder to generate `patch.xp3`.  
  
## Note  
  
If you need to start a line with the `[` character, make sure to double it (`[[`) to not cause issues.  
  
## Development References  
  
[Doc](https://kirikirikag.sourceforge.net/contents/index.html)  
[KirikiriTools](https://github.com/arcusmaximus/KirikiriTools)  