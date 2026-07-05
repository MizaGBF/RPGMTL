# RPGMTL  
  
# YPF Plugin Manual  
  
## Quick Overview  
  
The YPF plugin targets archive files from the YU-RIS Engine.  
  
It handles the extraction of internal YBN script files.  
During extraction, YBN encryption keys and string-related opcodes are stored in the project `config.json` metadata, along in a `ypf.json` file in the `originals` directory, as a fallback (in case the `config.json` has been corrupted or manually edited by an user).  
The **YBN Plugin** will use these informations for string extraction and patching.  