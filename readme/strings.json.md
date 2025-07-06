# RPGMTL  
  
# Strings.json format  
  
`...` means the previous element type can repeat.  
  
```json
{
    "strings": {
        "STRING_ID": [
            "ORIGINAL_STRING",
            "TRANSLATED_STRING_or_null",
            "OCCURENCE_INTEGER"
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