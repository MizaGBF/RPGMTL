# RPGMTL  
  
The `strings.json` file is the primary database for a translation project. It stores all extracted strings, their translations, and their metadata.  
  
# Strings.json format  
  
```json
{
    "version": 2,
    "strings": {
        "STRING_ID": [
            "ORIGINAL_STRING",
            "TRANSLATED_STRING_or_null",
            "OCCURENCE_INTEGER",
            "STRING_COLOR_MARKER"
        ],
        ...
    },
    "files": {
        "FILE_ID": [
            [
                "STRING_GROUP_NAME",
                [
                    "STRING_ID",
                    "LOCAL_TRANSLATED_STRING_or_null",
                    "IS_LOCAL_FLAG",
                    "IS_IGNORED_FLAG",
                    "IS_MODIFIED_FLAG"
                ],
                ...
            ],
            ...
        ],
        ...
    }
}
```  
  
## Field Definitions  
  
### Global Strings (`strings` object)  
  
The `strings` object maps a unique `STRING_ID` to its global data.  
* **ORIGINAL_STRING**: The source text extracted from the game.
* **TRANSLATED_STRING**: The global translation. If null, the string is considered untranslated.
* **OCCURRENCE_COUNT**: An integer representing how many times this string appears across the project.
* **MARKER_COLOR_INDEX**: An integer (0-6) representing the UI marker color.
  
### File Mappings (`files` object)
The `files` object organizes string occurrences by their source file.
* **FILE_ID**: A unique identifier for the source file.  
* **STRING_GROUP_NAME**: The name of the group the strings belong to (used for UI context).  
* **Local Entry**:  
    * **STRING_ID**: References the global string entry.  
    * **LOCAL_TRANSLATED_STRING**: If the string is unlinked (`IS_LOCAL_FLAG` is 1), this value overrides the global translation.  
    * **Flags**: Used to store the state of the string. These are stored as integers (0 or 1) to optimize file size.  
        * `IS_LOCAL_FLAG`: 1 if the string has a unique local translation.  
        * `IS_IGNORED_FLAG`: 1 if the string should be skipped during patching.  
        * `IS_MODIFIED_FLAG`: 1 if the string was updated or added in a recent extraction.  
  