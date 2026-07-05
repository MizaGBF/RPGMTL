# RPGMTL  
  
# YBN Plugin Manual  
  
## Quick Overview  
  
The YBN plugin targets script files from the YU-RIS Engine (typically named `ystXXXXX.ybn`).  
  
**Requirement**: Script files must be extracted using the **YPF Plugin** to ensure they are processed correctly.  
  
## Patching and Distribution  
  
The YU-RIS engine prioritizes files located in the `ybin/` directory within the game folder. To test or distribute your translation:  
1. Generate patched files using RPGMTL.  
2. Place the resulting `ybin/` folder at the root of the game directory.  
  
**Example Structure**:  
```text
Game Directory/
├── ybin/           (Patched .ybn files from RPGMTL)
├── pac/ysbin.ypf   (Original archive - remains untouched)
└── game.exe
```  
  
## Note  
  
The **YPF Plugin** will store encryption keys and  string-related opcodes are stored in the project `config.json` metadata, along in a `ypf.json` file in the `originals` directory, as a fallback (in case the `config.json` has been corrupted or manually edited by an user).  
These informations are read by this **YBN Plugin** during extraction and patching.  
  
## Reference  
  
* [Official YU-RIS Engine Manual](http://yu-ris.net/manual/eris/html/top.html)  