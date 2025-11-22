# RPGMTL  
  
# API Manual  
  
RPGMTL interface is a web page.  
It communicates with RPGMTL via POST requests.  
  
Below is the server API used for the web interface, for documentation purpose.  
A POST request always return the following JSON:  
```json
{
    "result":"ok",
    "data":{},
    "message":"A popup message!"
}
```  
  
* `result` can be either `ok` or `bad`.  
* `data` content varies depending on the call. See below. Note: It's absent if the `result` is `bad`.  
    * When present inside `data`, `config` and `name` are automatically read.  
* `message` is a string, which will be displayed as a popup. It's optional and not always present.  
  
## Endpoints  
  
Endpoints without parameters don't need to be sent a payload.  
  
```
/api/main
Return in data: 'list' of project names, 'version' string, file 'history'
```
  
```
/api/shutdown
```
  
```
/api/update_location
Payload: selected 'path'
Return in data: game 'path' string
```
  
```
/api/update_location
Payload: project 'name', selected 'path'
Return in data: project 'name', project 'config'
name config
```
  
```
/api/translator (Global)
Return in data: 'list' of translator plugins, 'current' selected plugin, current 'batch' selected plugin
```
  
```
/api/translator (Project specific)
Payload: project 'name'
Return in data: project 'name', project 'config', 'list' of translator plugins, 'current' selected plugin, current 'batch' selected plugin
```
  
```
/api/update_translator (Global)
Payload: 'value' to set the current translator, 'index' (0 (DEFAULT FALLBACK) for single string translator, 1 for batch)
```
  
```
/api/update_translator (Project Specific)
Payload: project 'name', 'value' to set the current translator
Return in data: project 'name', project 'config', 'index' (0 (DEFAULT FALLBACK) for single string translator, 1 for batch)
```
  
```
/api/update_translator (Project Specific, reset the setting)
Payload: project 'name'
Return in data: project 'name', project 'config'
```
  
```
/api/settings (Global)
Return in data: menu 'layout', global 'settings', plugin 'description'
```
  
```
/api/settings (Project Specific)
Payload: project 'name'
Return in data: project 'name', project 'config', menu 'layout', global 'settings', plugin 'description'
```
  
```
/api/update_settings (Global)
Payload: setting 'key', new setting 'value'
```
  
```
/api/update_settings (Project Specific)
Payload: project 'name', setting 'key', new setting 'value'
Return in data: project 'name', project 'config'
```
  
```
/api/update_settings (Project Specific, reset the setting)
Payload: project 'name'
Return in data: project 'name', project 'config'
```
  
```
/api/new_project
Payload: project 'name', game 'path'
Return in data: project 'name', project 'config', RPGMTL 'tools'
```
  
```
/api/open_project
Payload: project 'name'
Return in data: project 'name', project 'config', RPGMTL 'tools'
```
  
```
/api/extract
Payload: project 'name'
Return in data: project 'name', project 'config', RPGMTL 'tools'
```
  
```
/api/unload
Payload: project 'name'
```
  
```
/api/browse
Payload: project 'name', folder 'path'
Return in data: project 'name', project 'config', folder 'path', list of 'files', list of 'folders'
```
  
```
/api/patches
Payload: project 'name'
Return in data: project 'name', project 'config'
```
  
```
/api/open_patch
Payload: project 'name', patch 'key'
Return in data: project 'name', project 'config', patch 'key'
```
  
```
/api/update_patch (Create/Edit patch)
Payload: project 'name', patch 'key', patch 'newkey', patch 'code'
Return in data: project 'name', project 'config'
```
  
```
/api/update_patch (Delete patch)
Payload: project 'name', patch 'key'
Return in data: project 'name', project 'config'
```
  
```
/api/release
Payload: project 'name'
Return in data: project 'name', project 'config'
```
  
```
/api/import
Payload: project 'name', file 'path'
Return in data: project 'name', project 'config'
```
  
```
/api/import_rpgmtrans
Payload: project 'name', file 'path'
Return in data: project 'name', project 'config'
```
  
```
/api/backups
Payload: project 'name'
Return in data: project 'name', project 'config', 'list' of backups
```
  
```
/api/load_backup
Payload: project 'name', backup 'file'
Return in data: project 'name', project 'config'
```
  
```
/api/ignore_file
Payload: project 'name', file 'path', ignore 'state'
Return in data: project 'name', project 'config', list of 'files', list of 'folders'
```
  
```
/api/file
Payload: project 'name', file 'path'
Return in data: project 'name', project 'config', file 'path', project 'strings', 'list' of strings in file, list of file 'actions'
```
  
```
/api/file_action
Payload: project 'name', file 'path', project 'version', action 'key'
Return in data: project 'name', project 'config'
```

```
/api/update_marker
Payload: project 'name', current file 'path', string global 'id', marker 'value' (0-6)
Return in data: project 'name', project 'config', file 'path', project 'strings', 'list' of strings in file
```

```
/api/update_string (Edit Translation)
Payload: project 'name', file 'path', project 'version', 'group' index, string 'index', 'string' translation
Return in data: project 'name', project 'config', file 'path', project 'strings', 'list' of strings in file
```

```
/api/update_string (Toggle Unlink/Ignore)
Payload: project 'name', file 'path', project 'version', 'group' index, string 'index', toggle 'setting' (0 for unlink, 1 for ignore, 2 for ignore all occurence in file, 3 for ignore all project-wide)
Return in data: project 'name', project 'config', file 'path', project 'strings', 'list' of strings in file
```

```
/api/translate_string
Payload: project 'name', 'string' to translate
Return in data: string 'translation'
```

```
/api/translate_file
Payload: project 'name', file 'path', project 'version'
Return in data: project 'name', project 'config', file 'path', project 'strings', 'list' of strings in file
```

```
/api/translate_project
Payload: project 'name'
Return in data: project 'name', project 'config'
```

```
/api/use_tool
Payload: project 'name', 'tool' key, tool 'params'
Return in data: project 'name', project 'config'
```

```
/api/bookmark_tool
Payload: project 'name', 'tool' key, bookmark 'value'
Return in data: project 'name', project 'config'
```

```
/api/search_string
Payload: project 'name', file 'path' (Only used for UI purpose), 'search' string, 'case' bool, 'contains' bool
Return in data: project 'name', project 'config', 'search' string, 'case' bool, 'contains' bool, matched 'files'
```

```
/api/local_path
Payload: directory 'path' (Empty string equals the last used directory, Invalid string will default to the working directory), 'mode' (0 and 1 for exe, 2 for JSON, 3 for RPGMAKERTRANSPATCH)
Return in data: 'path', list of 'folders', list of matching 'files'
```

```
/api/delete_knowledge
Payload: project 'name', 'entry' original string to delete
Return in data: project 'name', project 'config'
```

```
/api/update_knowledge
Payload: project 'name', 'entry' to update or null, 'original' string to set/update, 'translation' string, 'note', 'last_seen', 'occurence'
Return in data: project 'name', project 'config'
```

```
/api/update_notes
Payload: project 'name', 'notes'
Return in data: project 'name', project 'config'
```