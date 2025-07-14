# RPGMTL  
  
# NScripter Plugin Manual  
  
## Quick Overview  
  
The NScripter Plugin targets scripts from the NScripter engine.  
  
## Usage  
  
Depending on the game, the script files can be either in the `arc.nsa` or `nscript.dat` files, or both. And the patching process can be different.  
As such, this plugin is intended to support Open Source forks of the engine such as [ONScripter](https://github.com/Galladite27/ONScripter-EN).  
  
To not interfer with the TXT plugin, the scripts are expected to have the `nscript` extension instead.  
  
Example for a game with a `nscript.dat`:  
1. Use `nscdec` to decompile the file into `result.txt`.  
2. Rename `result.txt` to `result.nscript`.  
3. Create a new RPGMTL project and import the game content with `result.nscript`.  
4. Make your edit and generate the patched `result.nscript`.  
5. Make any extra edit you need for compatibility with [ONScripter](https://github.com/Galladite27/ONScripter-EN).  
6. Use `nscmake` (example: `nscmake.exe result.nscript`) on the patched file to generate an up-to-date `nscript.dat`.  
  
The `nscripter_single_byte` Plugin setting is enabled by default and will add a backquote before english lines to avoid some issues.  
See [this documentation](https://kaisernet.org/onscripter/api/NScrAPI.html#_backquote`).  
  
## Development References  
  
[API](https://07th-mod.github.io/ponscripter-fork/api/)  