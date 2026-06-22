# RPGMTL  
  
# API Manual  
  
The RPGMTL interface is a web application that communicates with the server via POST requests. This document outlines the server API used by the web interface for documentation purposes.  
  
## Response Format  
  
All POST requests return a JSON object in the following format:  
```json
{
    "result":"ok",
    "data":{},
    "message":"A popup message!"
}
```  
  
* `result`: Indicates the status of the request, either `"ok"` or `"bad"`.  
* `data`: Contains the response payload. The content varies depending on the endpoint. This field is absent if `result` is `"bad"`.  
    * When present, `config` and `name` fields within `data` are automatically processed by the interface and will match the project name and the `config.json` data.  
* `message`: An optional string to be displayed as a popup message in the interface.  
  
---
  
## Endpoints  
  
Endpoints without listed parameters do not require a payload.  
  
### General  
  
`/api/main`  
* **Returns**: `list` of project names, `version` string, file `history`, `logoff` flag  
  
`/api/shutdown`  
* **Returns**: Nothing  
  
### Project Related  
  
`/api/update_location`  
* **Variant 1**:  
    * **Payload**: selected `path`  
    * **Returns**: game `path` string  
* **Variant 2**:  
    * **Payload**: project `name`, selected `path`  
    * **Returns**: project `name`, project `config`  
  
`/api/new_project`  
* **Payload**: project `name`, game `path`, `icon_path`  
* **Returns**: project `name`, project `config`  
  
`/api/open_project`  
* **Payload**: project `name`  
* **Returns**: project `name`, project `config`, RPGMTL `tools`  
  
`/api/clear_project_path`  
* **Payload**: project `name`  
* **Returns**: project `name`, project `config`  
  
`/api/unload`  
* **Payload**: project `name`  
* **Returns**: Nothing  
  
`/api/update_icon`  
* **Payload**: project `name`, icon `path` or url or null to delete it  
* **Returns**: project `name`, project `config`  
  
### Settings  
  
`/api/translator `  
* **Variant 1 (Global)**:  
    * **Returns**: `list` of translator plugins, `current` selected plugin, current `batch` selected plugin  
* **Variant 2 (Project specific)**:  
    * **Payload**: project `name`  
    * **Returns**: project `name`, project `config`, `list` of translator plugins, `current` selected plugin, current `batch` selected plugin  
  
`/api/update_translator `  
* **Variant 1 (Global)**:  
    * **Payload**: `value` to set the current translator, `index` (0 (DEFAULT FALLBACK) for single string translator, 1 for batch)  
    * **Returns**: Nothing  
* **Variant 2 (Project Specific)**:  
    * **Payload**: project `name`, `value` to set the current translator  
    * **Returns**: project `name`, project `config`, `index` (0 (DEFAULT FALLBACK) for single string translator, 1 for batch)  
* **Variant 3 (Project Specific, reset the setting)**:  
    * **Payload**: project `name`  
    * **Returns**: project `name`, project `config`  
  
`/api/settings `  
* **Variant 1 (Global)**:  
    * **Returns**: menu `layout`, global `settings`, plugin `description`  
* **Variant 2 (Project Specific)**:  
    * **Payload**: project `name`  
    * **Returns**: project `name`, project `config`, menu `layout`, global `settings`, plugin `description`, `modified_default` setting keys list  
  
`/api/update_settings `  
* **Variant 1 (Global)**:  
    * **Payload**: setting `key`, new setting `value`, `modified_default` setting keys list  
    * **Returns**: Nothing  
* **Variant 2 (Project Specific)**:  
    * **Payload**: project `name`, setting `key`, new setting `value`  
    * **Returns**: project `name`, project `config`, `modified_default` setting keys list  
* **Variant 3 (Project Specific, reset the setting)**:  
    * **Payload**: project `name`  
    * **Returns**: project `name`, project `config`, `modified_default` setting keys list  
  
### Files
  
`/api/browse`  
* **Payload**: project `name`, folder `path`  
* **Returns**: project `name`, project `config`, folder `path`, list of `files`, list of `folders`, `updating_progress` flag  
  
`/api/ignore_file`  
* **Payload**: project `name`, file `path`, ignore `state`  
* **Returns**: project `name`, project `config`, list of `files`, list of `folders`  
  
`/api/file`  
* **Payload**: project `name`, file `path`  
* **Returns**: project `name`, project `config`, file `path`, project `strings`, `list` of strings in file, list of file `actions`  
  
### Strings and Patching
  
`/api/extract`  
* **Payload**: project `name`  
* **Returns**: project `name`, project `config`  
  
`/api/release`  
* **Payload**: project `name`  
* **Returns**: project `name`, project `config`  
  
`/api/update_marker`  
* **Payload**: project `name`, current file `path`, string global `id`, marker `value` (0-6)  
* **Returns**: project `name`, project `config`, file `path`, project `strings`, `list` of strings in file  
  
`/api/update_string `  
* **Variant 1 (Edit Translation)**:  
    * **Payload**: project `name`, file `path`, project `version`, `group` index, string `index`, `string` translation  
    * **Returns**: project `name`, project `config`, file `path`, project `strings`, `list` of strings in file  
* **Variant 2 (Toggle Unlink/Ignore)**:  
    * **Payload**: project `name`, file `path`, project `version`, `group` index, string `index`, toggle `setting` (0 for unlink, 1 for ignore, 2 for ignore all occurence in file, 3 for ignore all project-wide)  
    * **Returns**: project `name`, project `config`, file `path`, project `strings`, `list` of strings in file  
  
`/api/search_string`  
* **Payload**: project `name`, file `path` (Only used for UI purpose), `search` string, `case` bool, `contains` bool  
* **Returns**: project `name`, project `config`, `search` string, `useorigin` bool, `case` bool, `contains` bool, matched `files`  
  
`/api/replace_strings`  
* **Payload**: `src` string, `dst` string, string `casing` boolean, `file_match` string  
* **Returns**: `count` of modified strings  
  
`/api/import`  
* **Payload**: project `name`, file `path`  
* **Returns**: project `name`, project `config`  
  
`/api/import_rpgmtrans`  
* **Payload**: project `name`, file `path`  
* **Returns**: project `name`, project `config`  
  
`/api/backups`  
* **Payload**: project `name`  
* **Returns**: project `name`, project `config`, `list` of backups  
  
`/api/load_backup`  
* **Payload**: project `name`, backup `file`  
* **Returns**: project `name`, project `config`  
`/api/patches`  
* **Payload**: project `name`  
* **Returns**: project `name`, project `config`  
  
`/api/open_patch`  
* **Payload**: project `name`, patch `key`  
* **Returns**: project `name`, project `config`, patch `key`  
  
`/api/update_patch `  
* **Variant 1 (Create/Edit patch)**:  
    * **Payload**: project `name`, patch `key`, patch `newkey`, patch `code`  
    * **Returns**: project `name`, project `config`  
* **Variant 2 (Delete patch)**:  
    * **Payload**: project `name`, patch `key`  
    * **Returns**: project `name`, project `config`  
  
`/api/import_patch`  
* **Payload**: project `name`  
* **Returns**: project `name`, project `config`  
  
`/api/export_patch`  
* **Payload**: project `name`  
* **Returns**: project `name`, project `config`  
  
### Translations  
  
`/api/translate_string`  
* **Payload**: project `name`, `string` to translate  
* **Returns**: string `translation`  
  
`/api/translate_file`  
* **Payload**: project `name`, file `path`, project `version`  
* **Returns**: project `name`, project `config`, file `path`, project `strings`, `list` of strings in file  
  
`/api/translate_project`  
* **Payload**: project `name`  
* **Returns**: project `name`, project `config`  
  
`/api/delete_knowledge`  
* **Payload**: project `name`, `entry` original string to delete  
* **Returns**: project `name`, project `config`  
  
`/api/update_knowledge`  
* **Payload**: project `name`, `entry` to update or null, `original` string to set/update, `translation` string, `note`, `last_seen`, `occurence`  
* **Returns**: project `name`, project `config`  
  
### Miscellaneous
  
`/api/file_action`  
* **Payload**: project `name`, file `path`, project `version`, action `key`  
* **Returns**: project `name`, project `config`  
  
`/api/use_tool`  
* **Payload**: project `name`, `tool` key, tool `params`  
* **Returns**: project `name`, project `config`  
  
`/api/bookmark_tool`  
* **Payload**: project `name`, `tool` key, bookmark `value`  
* **Returns**: project `name`, project `config`  
  
`/api/local_path`  
* **Payload**: directory `path` (Empty string equals the last used directory, Invalid string will default to the working directory), `mode` (0 and 1 for exe, 2 for JSON, 3 for RPGMAKERTRANSPATCH)  
* **Returns**: `path`, list of `folders`, list of matching `files`  
  
`/api/update_notes`  
* **Payload**: project `name`, `notes`  
* **Returns**: project `name`, project `config`  
  