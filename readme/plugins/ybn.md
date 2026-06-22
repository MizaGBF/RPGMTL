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
  
## Reference  
  
* [Official YU-RIS Engine Manual](http://yu-ris.net/manual/eris/html/top.html)  