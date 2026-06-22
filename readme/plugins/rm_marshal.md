# RPGMTL  
  
# RM Marshal Plugin Manual  
  
## Quick Overview  
  
The RM (RPG Maker) Marshal plugin targets data files from RPG Maker XP, VX, and VX Ace (`.rxdata`, `.rvdata`, `.rvdata2`). These files contain Marshaled Ruby objects.  
  
The plugin uses filename patterns to identify RPG Maker-specific data structures, providing optimal context for string extraction.  
  
## Features  
  
* **Virtual Files**: Individual entries in `CommonEvents` and `Scripts` are extracted as separate Virtual Files to improve the translation workflow.  
* **Ruby Integration**: If the **Ruby Plugin** is enabled, it can be configured to process scripts extracted from the `Scripts` database.  
* **Formatting Preservation**: The `format_json` utility (where applicable) helps maintain original file formatting for genuine appearance and easy comparison.  

## Settings

* **Merge Multiline Commands**: When enabled, the plugin merges consecutive text commands (as they would appear in a game's text box) into a single string. This often improves machine translation results. *Note: Changing this setting requires a fresh string extraction.*
  
## Development References  
  
* [Ruby Marshal Documentation](https://docs.ruby-lang.org/en/2.6.0/marshal_rdoc.html)  
* [Ruby Core Marshal API](https://ruby-doc.org/core-2.6.8/Marshal.html)  
[C Implementation](https://ruby-doc.org/core-2.6.8/Marshal.html)  
[Test File](https://rubygems.org/latest_specs.4.8.gz)  