# RPGMTL  
  
# MED Plugin Manual  
  
## Overview  
  
The MED Plugin targets the md_scr.med archive (containing Script Files) used in some japanese games from Triangle and Lusterise.  
While the plugin is mature, it hasn't been tested on a lot of games.  
It **won't** extract non-japanese strings in its current state.  
  
Each file contained inside are extracted as Virtual Files, for clarity sake.  
  
RPGMTL Fix/Patches aren't supported on this file format.  
  
## File Actions  
  
### Adjust New Line  
  
This engine doesn't always support newline `\n`, so lines must be padded with spaces to wrap properly.  
As this process can be quite destructive, it's not recommended to do it until your project is complete.  
This action automatically does it for you.  
The default is 64 characters per line and can be adjusted in the settings.  
  
### Look for invalid characters  
  
Non-ASCII characters (and some more) might break with text wrap above.  
As such, unless you're making a translation in Chinese or Korean for example, you must make sure your text only contains ASCII characters.  
This action will check and mark strings for you.  
Do note that it also check for the character `♪[]`, the first one could cause the same issue, and the later two can make the text break in some games.  
  
## Development References  
  
Those files start with `MDE0` as the first 4 bytes.  
Values inside are in little endian.  
  
The header is as such:  
- "Magic Number" `MDE0`, 4 bytes.  
- File Entry length, 2 bytes.  
- Number of File Entry, 2 bytes.  
- Each File Entry, one by one, 16 bytes PLUS the File Entry length:
    - File Name, 4 bytes PLUS the File Entry length, NULL terminated.  
    - An unknown value, 4 bytes.  
    - The File Size, 4 bytes.  
    - The File Offset, 4 bytes.  
  
To extract a file:  
- Go to its Offset.  
- Read the number of bytes corresponding to the File Size.  
- You'll need the secret key to decrypt the content.  
  
To get the secret key, search for the file whose name starts with `_VIEW`.  
Get its 16th byte to 40th (not included). 24 bytes total.  
Iterate over and substract the byte in the same position in this byte array:  
```python
b'\x00\x23\x52\x55\x4C\x45\x5F\x56\x49\x45\x57\x45\x52\x00\x3A\x56\x49\x45\x57\x5F\x30\x00\x7B\x00'
```
Add 256 if negative.  
The resulting 24 bytes is the secret key.  
  
Then to decrypt a file:  
- Iterate from the 16h byte to the end of the File.  
- Add the corresponding byte from the secret key (16th File byte corresponds to the 1st byte of the secret key, it wraps around the key).  
  
To encrypt, it's the opposite, substract the corresponding byte.  
  
A script file is composed of the following:  
- A 16 bytes header containing the length of the content (4 bytes), the offset (4 bytes) and possibly more data.  
- The file content, mostly null terminated strings encoded in `cp932`. 'Mostly' because there is what looks like binary data too, mostly at the beginning of files.  
  