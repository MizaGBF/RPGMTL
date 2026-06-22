# RPGMTL  
  
# JSON Plugin Manual  
  
## Quick Overview  
  
The JSON plugin targets JSON files from various engines, with optimized support for RPG Maker MV and MZ. It uses file naming patterns to identify RPG Maker-specific data and provides specialized context during extraction.  
  
## Features  
  
* **RPGMTL Context**: Automatically identifies common RPG Maker structures to provide helpful metadata for strings.  
* **Formatting Preservation**: The `format_json` utility ensures that patched files maintain a format consistent with original RPG Maker MV/MZ files, allowing for easy comparison and genuine appearance.  
* **Virtual Files**: Entries in `CommonEvents.json` are extracted as separate Virtual Files to simplify the translation workflow.  
  
## Settings  
  
* **Merge Multiline Commands**: When enabled, the plugin merges consecutive text commands (as they would appear in a game's text box) into a single string. This can significantly improve the accuracy of machine translations. *Note: Changing this setting requires a fresh string extraction.*  