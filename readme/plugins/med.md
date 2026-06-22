# RPGMTL  
  
# MED Plugin Manual  
  
## Overview  
  
The MED plugin targets `md_scr.med` archives used by Triangle and Lusterise games. It extracts internal scripts as **Virtual Files** for an organized workflow.  
  
**Limitations**:
* The plugin is optimized for Japanese text extraction and may not extract other languages correctly in its current state.  
* Custom RPGMTL **Fixes** are not supported for this file format.  
  
## File Actions  
  
### Adjust New Line  
  
The engine often requires lines to be padded with spaces for proper text wrapping instead of using standard `\n` characters.  
* **Recommendation**: Run this action only once your translation is complete, as it is a destructive formatting process.  
* **Configuration**: The default line length is 64 characters, which can be adjusted in the plugin settings. Make sure to check the length of a line for your targeted game.  
  
### Look for invalid characters  
  
This utility identifies characters that may cause rendering or wrapping issues.  
* **ASCII Check**: It flags non-ASCII characters in the current file.  
* **Special Characters**: It also checks for `♪`, `[`, and `]`, which are known to cause issues in certain games.  
  
## Technical Details  
  
### Header Format (Little Endian)
1. **Magic Number**: `MDE0` (4 bytes).  
2. **File Entry Length**: 2 bytes.  
3. **Entry Count**: 2 bytes.  
4. **File Entries**: (16 bytes + File Entry Length) each:  
    * **Name**: NULL-terminated string (4 bytes + Entry Length).  
    * **Unknown**: 4 bytes.  
    * **Size**: 4 bytes.  
    * **Offset**: 4 bytes.  
  
### Encryption/Decryption
The archive uses a secret 24-byte key for encryption, derived from a file typically named `_VIEW`.  
  
1. **Key Extraction**: Locate the `_VIEW` file. Take bytes 16 through 39 (inclusive).
2. **Key Transformation**: Subtract each byte from the corresponding byte in the following sequence (If the result is **negative**, **add 256**):  
```python
b'\x00\x23\x52\x55\x4C\x45\x5F\x56\x49\x45\x57\x45\x52\x00\x3A\x56\x49\x45\x57\x5F\x30\x00\x7B\x00'
```  
3. **Processing**: Starting from the 16th byte of a script file, add (for decryption) or subtract (for encryption) the secret key bytes in a rotating fashion.  
  
### Script Format  
  
Script files consist of a 16-byte header followed by `cp932` (Shift-JIS) encoded strings and binary data.  