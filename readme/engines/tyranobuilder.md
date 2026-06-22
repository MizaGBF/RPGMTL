# RPGMTL  
  
## Translating TyranoBuilder games  
  
### Extracting Assets and Scripts.  
  
The extraction method varies depending on the TyranoBuilder version and packaging:  
  
* **Packed Executable**: Use [GARbro](https://github.com/morkt/GARbro) to extract game data from the `.exe`.  
* **ASAR Archive** (`resources/app.asar`): Open the archive using tools like `7-Zip` with the [Asar7z](https://www.tc4shell.com/en/7zip/asar/) plugin.  
  
### Creating a Patch.  
  
The recommended method for patching is creating a `.tpatch` file, which is a renamed `.zip` archive.  
  
### Patch Configuration
* **Naming**: The patch must be named after the game's unique identifier. This can often be found in the save file name (e.g., if the save is `gameid_sf.sav`, the patch should be `gameid.tpatch`).  
* **Structure**: The internal structure of the ZIP must mirror the original game data (e.g., `data/`, `tyrano/`, `index.html`).  
  
### RPGMTL Workflow  
  
Ensure your project's folder structure mirrors the game's, for example:
```
originals/
└── data/
    ├── scenario/
    └── system/
```
This ensures the `release/` folder will have the correct hierarchy.  

### Automation Script  
  
Use the following Python script to generate the `.tpatch` file from the `release/` directory:  
```python
import zipfile
import os

IDENTIFIER = "something"
FILES_AND_FOLDERS = ['release/data']

def create_zip(zip_name, items_to_add):
    with zipfile.ZipFile(zip_name, 'w', zipfile.ZIP_DEFLATED) as zip_canvas:
        for item in items_to_add:
            if os.path.isfile(item):
                # If it's a file, just add it
                zip_canvas.write(item, os.path.basename(item))
                print(f"Added file: {item}")
            
            elif os.path.isdir(item):
                # If it's a folder, walk through its contents
                for root, dirs, files in os.walk(item):
                    for file in files:
                        filepath = os.path.join(root, file)
                        # Create a relative path to keep the folder structure
                        arcname = os.path.relpath(filepath, os.path.dirname(item))
                        zip_canvas.write(filepath, arcname)
                print(f"Added folder: {item}")

# Usage

create_zip(IDENTIFIER + '.tpatch', FILES_AND_FOLDERS)
```  
Make sure to set `IDENTIFIER` and `FILES_AND_FOLDERS` to the proper value.  
In this case, it will put into the zip the folder `data` in the `release` folder, and name it `something.tpatch`.  
  
### Applying the Patch  
  
To apply a `.tpatch` file, it must be present in the game folder.  
Then, simply start the game, and it will patch its own data with.  
In case of `app.asar` files, it will update it and delete the `.tpatch` afterward.  
**The patching process can take time**, be warned.  
  
### Testing and Iteration  
  
To avoid repetitive patching during testing, you can use the unpacked `app` folder method:
1. Extract the `app.asar` content into a folder named `app` within the `resources/` directory.  
2. Copy your patched files directly into this folder.  
The game will prioritize the `app/` folder over the `app.asar` archive.  
```
resources/
└── app/
    ├── data/
    ├── node_modules/
    ├── tyrano/
    ├── index.html
    ├── main.js
    └── package.json
```  
  
## Known Issues and Tips
  
### Patching Stability  
  
When patching `app.asar` via a `.tpatch` file, do not close the game or proceed through prompts too quickly. Allow the engine sufficient time to complete the extraction and patching.  

### Versioning and Metadata
To change the game version or title (often found in `data/system/Config.tjs`), you can use a simple custom RPGMTL **Fix** (via the `Add a fix` menu):  
```python
s = helper.to_str()
s = s.replace("ORIGINAL_VERSION", "PATCHED_VERSION")
s = s.replace("ORIGINAL_TITLE", "TRANSLATED_TITLE")
helper.from_str(s)
helper.modified = True
```  
Ensure the file isn't ignored in the file list.  
  