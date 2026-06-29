# RPGMTL  
  
## Translating RPG Maker games  
  
RPG Maker is entirely supported by RPGMTL, from XP to MZ included.  
  
Here's a list of recommendations:  
- Before the first String extraction, enable the `Merge multiline commands into one` setting of the `JSON` plugin (for MV/MZ) or the `RPG Maker Marshal` plugin (for XP/VX/VX Ace). It usually results in better machine translations, at the cost of consistency if there are lot of repetitive text boxes with minor variations. It's recommended to leave it disabled it in the latter case.  
- After the first String extraction, use the `RPGM Default Setup` tool. It will disable files which should usually not be modified and apply basic default translations (if you wish to).  
- Then, at some point during translation, go over the script files (in the `js` folder for typical MV/MZ games) and see what might file might need to be allowed.  
- If you find untranslated text, try to search it to find if it has been disabled somewhere.  
  