# RPGMTL  
  
# NScripter Plugin Manual  
  
## Quick Overview  
  
The NScripter plugin targets script files used by the NScripter engine. It is designed to facilitate translations for use with modern open-source engine forks like [ONScripter-EN](https://github.com/Galladite27/ONScripter-EN).  
  
To prevent conflicts with the standard TXT plugin, script files should use the `.nscript` extension.  
  
## Workflow Example (nscript.dat)  
  
1. **Decompile**: Use `nscdec` to decompile the `nscript.dat` file into a text file (e.g., `result.txt`).  
2. **Rename**: Rename the decompiled file to `result.nscript`.  
3. **Import**: Create an RPGMTL project and import `result.nscript`.  
4. **Translate**: Perform your translations and generate the patched `.nscript` file.  
5. **Recompile**: Use `nscmake` (e.g., `nscmake.exe result.nscript`) on the patched file to generate an updated `nscript.dat`.  
  
## Compatibility Settings  
  
* **Single-byte Mode**: This plugin setting (enabled by default) prepends a backquote (`` ` ``) to English lines. This is required by some engine versions to ensure correct rendering of single-byte characters. Refer to the [ONScripter API Documentation](https://kaisernet.org/onscripter/api/NScrAPI.html#_backquote) for more details.  
  
## Development References  
  
* [PONSScripter API Documentation](https://07th-mod.github.io/ponscripter-fork/api/)  