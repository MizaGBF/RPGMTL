# RPGMTL  
  
# Javascript Plugin Manual  
  
## Quick Overview  
  
The JavaScript plugin targets JavaScript (`.js`) files, including those from RPG Maker MV/MZ and other engines. It supports the extraction and patching of string literals and regular expressions.  
  
To provide context, String Groups are named after the function in which the string is located.  
  
## RPG Maker Specific Processing  
  
For RPG Maker MV and MZ, `plugins.js` files are treated similarly to JSON. Each plugin's settings are extracted as separate Virtual Files for improved clarity and management.  
  
## Handling New Lines  
  
The plugin handles various JavaScript string formatting conventions:  
  
### Multi-line Literals  
  
Strings formatted with a backslash for continuation:  
```javascript
const str = "Hello\
world!";
```  
will appear in RPGMTL as:
```text
Hello
world!
```  
  
### Patching Behavior  
  
During the patching process, literal new lines in the translation are automatically escaped as `\n`.

* **Input**:  
```text
Hello
world!
```  
* **Resulting Patch**:  
```javascript
const str = "Hello\nworld!";
```  
  
Explicitly typed `\n` characters are also preserved correctly. However, attempting to use the backslash continuation syntax (`\`) within the RPGMTL editor will result in an escaped backslash (`\\n`) and is not supported:  
  
* **Input**:  
```text
Hello\
world!
```  
* **Resulting Patch**:  
```Javascript
const string = "Hello\\nworld!";
```  