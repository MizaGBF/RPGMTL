# RPGMTL  
  
# Strings.json format  
  
`...` means the previous element type can repeat.  
  
```json
{
    "version": 1,
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

## Notes:
- String `FLAG` can be either boolean or integer (0 or 1). The later is used to reduce file sizes.  
- `STRING_COLOR_MARKER` is for the marker on the left of the string list. 1 to 6 are colors. Other are non-colored.  