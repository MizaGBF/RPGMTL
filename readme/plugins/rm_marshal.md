# RPGMTL  
  
# RM Marshal Plugin Manual  
  
## Quick Overview  
  
The RM Marshal Plugin (RM stands for RPG Maker) targets RPG Maker XP, VX and VX Ace Data files (.rxdata, .rvdata, .rvdata2).  
Those files are Marshaled Ruby object files.  
The plugin uses the file name to determine if it's likely to be a RPG Maker files and read it accordingly to get the best context as possible.  
  
Each events of `CommonEvents` and `Scripts` are extracted as Virtual Files, for clarity sake.  
  
If the `Ruby` plugin is available and the according setting is set, each script inside `Scripts` will be passed to that plugin.  
  
The `Merge multiline commands into one (Require re-extract)` setting lets you merge strings into a single one, as they would show on a text box (if enabled). It might improve automatic translations.
  
## Development References  
   
[Documentation 1](https://docs.ruby-lang.org/en/2.6.0/marshal_rdoc.html)  
[Documentation 2](https://ruby-doc.org/core-2.6.8/Marshal.html)  
[C Implementation](https://ruby-doc.org/core-2.6.8/Marshal.html)  
[Test File](https://rubygems.org/latest_specs.4.8.gz)  