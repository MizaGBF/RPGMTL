# RPGMTL  
  
# Javascript Plugin Manual  
  
## Quick Overview  
  
The Javascript Plugin targets RPG Maker MV and MZ Javascript (.js) files, along with any other Javascript files from any other games.  
It supports all string literals along with regexes.  
For context, String Groups are named with the function name of where the string is located.  
  
RPG Maker MV and MZ `plugins.js` files are processed differently, almost as a JSON file. Each plugin settings are extracted as Virtual Files, for clarity sake.  
  
## New Lines
For strings originally formatted as such:  
```Javascript
const string = "Hello\
world!";
```  
in RPGMTL, they will appear as:
```console
Hello
world!
```  
  
During patching processes, new lines will automatically be replaced by `\n`. Example:  
```console
Hello
world!
```  
is patched as  
```Javascript
const string = "Hello\nworld!";
```  
But they behave as javascript strings otherwise. Example:  
```console
Hello\nworld!
```  
is patched as  
```Javascript
const string = "Hello\nworld!";
```  
And the following **won't work**. Example:  
```console
Hello\
world!
```  
is patched as  
```Javascript
const string = "Hello\\nworld!";
```  