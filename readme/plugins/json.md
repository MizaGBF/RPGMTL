# RPGMTL  
  
# JSON Plugin Manual  
  
## Quick Overview  
  
The JSON Plugin targets RPG Maker MV and MZ JSON files, along with any other JSON files from any other games.  
It uses the file name to determine if it's likely to be a RPG Maker files and read it accordingly to get the best context as possible.  
  
The `format_json` is here to help keep the original format of RPG Maker MV and MZ JSON files, so that they look genuine and be easily compared with their originals, if needed.  
  
Each events of `CommonEvents.json` are extracted as Virtual Files, for clarity sake.  
  
The `Merge multiline commands into one (Require re-extract)` setting lets you merge strings into a single one, as they would show on a text box (if enabled). It might improve automatic translations.