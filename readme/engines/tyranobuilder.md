# RPGMTL  
  
## Translating TyranoBuilder games  
  
### Extracting assets and scripts.  
  
The method might change depending on the Tyrano version and how the game was packaged.
For example, if packaged in the `.exe` itself: In this case, [GARbro](https://github.com/morkt/GARbro) is able to extract the data.  
Else it might be in `resources/app.asar`. `.asar` file can be opened in many ways. I personally use `7zip` with the [Asar7z](https://www.tc4shell.com/en/7zip/asar/) plugin.  
  
### Making a patch.  
The best method is to make a `.tpatch` file. This is just a `.zip` file under another name.  
The file must be named after the unique identifier of the game.  
An easy way to find it is to simply look for the game save file.  
For example, if it's named `something_sf.sav`, you must name the patch `something.tpatch`.  
The structure inside the `.zip` must match the one of the packaged data.  
Usually:  
```
data/
node_modules/
tyrano/
index.html
main.js
package.json
```  
The patch doesn't need to include all files, just the modified ones.  
  
As for RPGMTL, to simplify things, I make sure the folder tree matches it, for example:  
```
originals/
└── data/
    ├── scenario/
    └── system/
```  
This way, the structure will be the same in the release folder.  
  
To make the `.tpatch` file, I use a python script:  
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
  
### Apply Patch
To apply a `.tpatch` file, it must be present in the game folder.  
Then, simply start the game, and it will patch its own data with.  
In case of `app.asar` files, it will update it and delete the `.tpatch` afterward.  
The patching process can take time, be warned.  
  
### Testing  
  
Applying a new `.tpatch` every time you want to test a change can be time consuming.  
For `app.asar` files, there is an alternative:  
Extract the content into a folder named `app`, in the `resources` folder, so it will look like:  
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
Then simply copy and paste your patched files into this folder, overwriting existing ones.  
The game will ignore `app.asar` and use the content of this folder instead.  
  
### Know issues  
  
In case of `app.asar`, the game sometimes fail to patch it. Make sure to not confirm the patching prompt too fast, give it time to extract and patch properly.  
  
If the game has a `data/system/Config.tjs` file, you can change the game version and title inside.  
A simple RPGMTL `Fix` (via the `Add a fix` menu) can do the trick:  
```python
s = helper.to_str()
s = s.replace("ORIGINAL_VERSION", "PATCHED_VERSION")
s = s.replace("ORIGINAL_TITLE", "TRANSLATED_TITLE")
helper.from_str(s)
helper.modified = True
```  
Make sure the file isn't ignored in the file list.  
I can't confirm if changing the version is needed.  