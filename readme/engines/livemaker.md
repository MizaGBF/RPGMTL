# RPGMTL  
  
## Translating LiveMaker games  
  
LiveMaker games are recognizable by the presence of a `live.dll` file.  
The version of the engine can be found in the executable properties.  
You'll need [pylivemaker](https://github.com/pmrowla/pylivemaker) installed.  
Make sure Python and its scripts folder is in your PATH if you're on Windows.  
  
### Unpack a game  
  
Go in the directory of the game that you want to translate, with a terminal/command prompt.  
Start by making a folder:  
```console
mkdir game_files
```  
  
If the game data is packed in a split archive, you'll see something like `game.001`, `game.002`, ... and `game.ext`.  
Run:
```console
lmar x game.ext -o game_files
```  
If there is a simple `game.dat`, run:
```console
lmar x game.dat -o game_files
```  
Else, if the data is packed in the executable (it should be visible at its file size):  
```console
lmar x game.exe -o game_files
```  
  
### Convert to CSV  
  
The next step is to extract the strings from the CSV.  
You'll need to run the following two commands on each `.lsb` file:  
```console
lmlsb extractcsv --encoding=utf-8-sig FILE_NAME.lsb FILE_NAME.csv
lmlsb extractmenu --encoding=utf-8-sig FILE_NAME.lsb FILE_NAME_menu.csv
```  
You can then import those `.csv` in RPGMTL.  
  
### Patch the strings  
  
Once the strings are translated, copy the modified `.csv` back to `game_files``.  
And run for each of them:  
```console
lmlsb insertcsv --encoding=utf-8-sig FILE_NAME.lsb FILE_NAME.csv
lmlsb insertmenu --encoding=utf-8-sig FILE_NAME.lsb FILE_NAME_menu.csv
```  
A backup of the `.lsb` will be created.  
  
### Repacking  
  
You can repack with a simple command (depending on how you extracted):  
```console
cd ..
lmpatch -r game.ext game_files
lmpatch -r game.dat game_files
lmpatch -r game.exe game_files
```  
**However**, there is a better method.  
The engine first checks if a file exists outside the archive.  
So, all you have to do is put your modified `.lsb` in the game folder.  
This also makes distributing a translation patch either.  
  
### Full-width ASCII  
  
[Relevant documentation](https://pylivemaker.readthedocs.io/en/latest/usage.html#notes-for-translation-patches)  
You'll likely notice that the engine forces ASCII characters to full-width, making it hardly usable for English translations.  
There are solutions, however.  
  
For LiveMaker 3 games, you must edit `メッセージボックス作成.lsb`.  
It's the file responsible for message boxes.  
Start by dumping the content:  
```console
lmlsb dump メッセージボックス作成.lsb > メッセージボックス作成.txt
```  
Open `メッセージボックス作成.txt`.  
You'll notice many lines such as:  
```console
36: MesNew "メッセージボックス" "メッセージボックス土台" ...
```
For each of them, run:
```console
lmlsb edit メッセージボックス作成.lsb 36
```  
by replacing 36 by the number at the beginning of the line.  
  
In the console, it will let you edit the values.  
Press Return to skip until you attain: `PR_FONTCHANGEABLED`  
If you see `PR_FONTCHANGEABLED[0]`, all good.  
If you see `PR_FONTCHANGEABLED[1]`, type `0` and press Return.  
Repeat this process for each `MesNew` line number.  
  
For LiveMaker 2 games, **there is no solution**.  
The best I can propose is to replace the game executable and `live.dll` with one from a v3 game (If the game data is packed in the `.exe`, make sure to extract in the game folder beforehand).  
Then, I had success replacing the original `メッセージボックス作成.lsb` with one coming from a v3 game of the same developer, with all the `PR_FONTCHANGEABLED` set to 0.  
  
### Translating the context Menu
  
In the extracted files, go into the `ノベルシステム` folder.  
Locate `■初期化.lsb`.  
Dump it:  
```console
lmlsb dump ■初期化.lsb > ■初期化.txt
```  
and open the text file.  
  
You should fine two StringArrays:  
```
  48: Calc StringToArray("文字を消す,シナリオ回想,読んだ文章を飛ばす,自動テキスト送り,セーブ,...
  49: Calc StringToArray("文字を消す,シナリオ回想,読んだ文章を飛ばす,自動テキスト送り,セーブ,...
```  
Note the number at the start of the **first one** and run:  
```console
lmlsb edit  ■初期化.lsb 48
```  
(Replace 48 with the number that you found).  
In the console, it will let you edit the values.  
The first entry will be the array variable, skip by pressing Return.  
The second should be the first string.  
In my example, `文字を消す`.  
To replace it by `Hide Text`, just type `"Hide Text"` and press return.  
Repeat the process for each menu entry.  
  
### Automation  
  
The following is a script to automate extracting the strings to CSV and patching them back.  
It requires the `pylivemaker` package to be installed.  
```python
import pathlib
import os
import tempfile
import csv
import shutil
from pathlib import Path, PureWindowsPath

import click

from livemaker.exceptions import BadLsbError, BadTextIdentifierError, LiveMakerException
from livemaker.lsb import LMScript
from livemaker.lsb.menu import LPMSelectionChoice
from livemaker.lsb.translate import TextBlockIdentifier, TextMenuIdentifier, make_identifier
from livemaker.project import PylmProject

from livemaker import LMArchive, LMCompressType

ENCODING = "utf-8"

def list_files(ext):
    # Convert string path to a Path object
    root = pathlib.Path(".")
    flist = []

    # .rglob('*') recursively finds everything; we filter for files only
    for path in root.rglob('*'):
        if path.is_file() and path.suffix == ext:
            flist.append(path.relative_to(root).as_posix())
    return flist

CSV_HEADER = ["ID", "Label", "Context", "Original text", "Translated text"]
def extractcsv(lsb_file, encoding=None, overwrite=False):
    if encoding is None:
        encoding = ENCODING
    csv_file = lsb_file.replace(".lsb", ".csv")
    lsb_file = Path(lsb_file)
    print(f"Extracting {lsb_file} ...")

    try:
        pylm = PylmProject(lsb_file)
        call_name = pylm.call_name(lsb_file)
    except LiveMakerException:
        pylm = None
        call_name = None

    try:
        with open(lsb_file, "rb") as f:
            lsb = LMScript.from_file(f, call_name=call_name, pylm=pylm)
    except BadLsbError as e:
        print(f"Failed to parse file: {e}")
        return

    csv_data = []
    for id_, block in lsb.get_text_blocks():
        csv_data.append([str(id_), id_.name, block.name_label, block.text, None])

    if len(csv_data) == 0:
        print("No text data found.")
        return

    if Path(csv_file).exists():
        if not overwrite:
            print(f"File {csv_file} already exists.")
            return

    with open(csv_file, "w", newline="\n", encoding=encoding) as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(CSV_HEADER)
        for row in csv_data:
            csv_writer.writerow(row)

    print(f"Extracted {len(csv_data)} text blocks.")

def _patch_csv_text(lsb, lsb_file, csv_data):
    text_objects = []
    untranslated = 0

    for row, (id_str, name, context, orig_text, translated_text) in enumerate(csv_data):
        try:
            id_ = make_identifier(id_str)
        except BadTextIdentifierError as e:
            if row > 0:
                # ignore possible header row
                print(f"Ignoring invalid text ID: {e}")
            continue

        if not isinstance(id_, TextBlockIdentifier):
            continue

        if id_.filename == lsb_file.name:
            if translated_text:
                text_objects.append((id_, translated_text))
            else:
                untranslated += 1

    translated, failed = lsb.replace_text(text_objects)

    return translated, failed, untranslated

def extractmenu(lsb_file, encoding=None, overwrite=False):
    if encoding is None:
        encoding = ENCODING
    csv_file = lsb_file.replace(".lsb", "_menu.csv")
    lsb_file = Path(lsb_file)
    print(f"Extracting {lsb_file} Menu ...")

    try:
        pylm = PylmProject(lsb_file)
        call_name = pylm.call_name(lsb_file)
    except LiveMakerException:
        pylm = None
        call_name = None

    try:
        with open(lsb_file, "rb") as f:
            lsb = LMScript.from_file(f, call_name=call_name, pylm=pylm)
    except BadLsbError as e:
        print(f"Failed to parse file: {e}")
        return

    if pylm:
        pylm.update_labels(lsb)

    csv_data = []
    names = set()
    for id_, choice in lsb.get_menu_choices():
        if isinstance(choice, LPMSelectionChoice):
            if True: # image based menu, disabled
                continue
            text = f"{choice.name} (Image: {choice.src_file})"
        else:
            text = choice.text
        name = id_.name
        if name in names:
            name = ""
        else:
            names.add(name)
        if pylm:
            _, target_name = pylm.resolve_label(choice.target)
        else:
            target_name = None
        target_name = f" ({target_name})" if target_name else ""
        context = [f"Target: {choice.target}{target_name}"]
        csv_data.append([str(id_), name, "\n".join(context), text, None])

    if len(csv_data) == 0:
        print("No menu data found.")
        return

    if Path(csv_file).exists():
        if not overwrite:
            print(f"File {csv_file} already exists.")
            return

    with open(csv_file, "w", encoding=encoding, newline="\n") as csvfile:
        csv_writer = csv.writer(csvfile, delimiter=",", quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(CSV_HEADER)
        for row in csv_data:
            csv_writer.writerow(row)

    print(f"{len(csv_data)} Menu entries extracted.")

def insertcsv(csv_file, encoding=None):
    if encoding is None:
        encoding = ENCODING
    if not Path(csv_file).exists():
        return False
    lsb_file = Path(csv_file.replace(".csv", ".lsb"))
    print(f"Patching {lsb_file} ...")

    try:
        pylm = PylmProject(lsb_file)
        call_name = pylm.call_name(lsb_file)
    except LiveMakerException:
        pylm = None
        call_name = None

    try:
        with open(lsb_file, "rb") as f:
            lsb = LMScript.from_file(f, call_name=call_name, pylm=pylm)
    except BadLsbError as e:
        print(f"Failed to parse file: {e}")
        return False

    csv_data = []

    with open(csv_file, newline="\n", encoding=encoding) as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        for row in csv_reader:
            csv_data.append(row)

    translated, failed, untranslated = _patch_csv_text(lsb, lsb_file, csv_data)
    print(f"  Translated {translated} lines")
    print(f"  Failed to translate {failed} lines")
    print(f"  Ignored {untranslated} untranslated lines")
    if not translated:
        return False

    try:
        new_lsb_data = lsb.to_lsb()
        with open(lsb_file, "wb") as f:
            f.write(new_lsb_data)
        print("Wrote new LSB.")
        return True
    except LiveMakerException as e:
        print(f"Could not generate new LSB file: {e}")
        return False

def _patch_csv_menus(lsb, lsb_file, csv_data):
    text_objects = []
    untranslated = 0

    for row, (id_str, name, context, orig_text, translated_text) in enumerate(csv_data):
        try:
            id_ = make_identifier(id_str)
        except BadTextIdentifierError as e:
            if row > 0:
                # ignore possible header row
                print(f"Ignoring invalid text ID: {e}")
            continue

        if not isinstance(id_, TextMenuIdentifier):
            continue

        if id_.filename == lsb_file.name:
            if translated_text:
                text_objects.append((id_, translated_text))
            else:
                untranslated += 1

    translated, failed = lsb.replace_text(text_objects)

    return translated, failed, untranslated

def insertmenu(csv_file, encoding=None):
    if encoding is None:
        encoding = ENCODING
    if not Path(csv_file).exists():
        return False
    lsb_file = Path(csv_file.replace("_menu.csv", ".lsb"))
    print(f"Patching {lsb_file} ...")

    try:
        pylm = PylmProject(lsb_file)
        call_name = pylm.call_name(lsb_file)
    except LiveMakerException:
        pylm = None
        call_name = None

    try:
        with open(lsb_file, "rb") as f:
            lsb = LMScript.from_file(f, pylm=pylm, call_name=call_name)
    except BadLsbError as e:
        print(f"Failed to parse file: {e}")
        return False

    csv_data = []

    with open(csv_file, newline="\n", encoding=encoding) as csvfile:
        csv_reader = csv.reader(csvfile, delimiter=",", quotechar='"')
        for row in csv_reader:
            csv_data.append(row)

    translated, failed, untranslated = _patch_csv_menus(lsb, lsb_file, csv_data)

    print(f"  Translated {translated} choices")
    print(f"  Failed to translate {failed} choices")
    print(f"  Ignored {untranslated} untranslated choices")
    if not translated:
        return False

    try:
        new_lsb_data = lsb.to_lsb()
        with open(lsb_file, "wb") as f:
            f.write(new_lsb_data)
        print("Wrote new LSB.")
        return True
    except LiveMakerException as e:
        print(f"Could not generate new LSB file: {e}")
        return False

def patch(archive_file, patched_lsb, recursive=True):
    archive_path = Path(archive_file).resolve()
    archive_dir = archive_path.parent
    archive_name = archive_path.name

    try:
        orig_lm = LMArchive(archive_path)
    except:
        return

    if orig_lm.is_exe:
        fd, tmp_exe = tempfile.mkstemp()
        fp = os.fdopen(fd, "wb")
        fp.write(orig_lm.read_exe())
        fp.close()
    else:
        if orig_lm.is_split:
            split = True
        tmp_exe = None

    backup_paths = {archive_path: Path(f"{archive_path}.bak")}
    if orig_lm.is_split:
        for p in orig_lm._split_files:
            backup_paths[Path(p)] = Path(f"{p}.bak")

    if Path(patched_lsb).is_dir():
        if not recursive:
            print(f"Cannot patch directory ({patched_lsb}) without recursive mode")
            return
    else:
        if recursive:
            print(f"Cannot patch file ({patched_lsb}) within recursive mode")
            return

    try:
        tmpdir = tempfile.mkdtemp()
        tmpdir_path = Path(tmpdir)
        print("Generating new archive contents...")
        with LMArchive(
            name=tmpdir_path.joinpath(archive_name), mode="w", version=orig_lm.version, exe=tmp_exe, split=split
        ) as new_lm:

            def bar_show(item):
                width, _ = shutil.get_terminal_size()
                width //= 4
                name = item.name if item is not None else ""
                if len(name) > width:
                    name = "".join(["...", name[-width:]])
                return name

            # patch
            with click.progressbar(orig_lm.infolist(), item_show_func=bar_show) as bar:
                for info in bar:
                    # replace existing with patch version
                    #
                    # TODO: support writing encrypted files
                    if info.compress_type == LMCompressType.ENCRYPTED:
                        compress_type = LMCompressType.NONE
                    elif info.compress_type == LMCompressType.ENCRYPTED_ZLIB:
                        compress_type = LMCompressType.ZLIB
                    else:
                        compress_type = info.compress_type

                    if recursive:
                        lsb_path = Path(patched_lsb).joinpath(info.path)
                        if not lsb_path.exists():
                            lsb_path = None
                    else:
                        lsb_path = Path(patched_lsb)
                        if info.path != PureWindowsPath(lsb_path):
                            lsb_path = None

                    if lsb_path:
                        new_lm.write(lsb_path, compress_type=compress_type, unk1=info.unk1, arcname=info.path)
                    else:
                        # copy original version
                        data = orig_lm.read(info, decompress=False)
                        new_lm.writebytes(info, data)

        orig_lm.close()

        # copy temp dir contents to output path then remove the temp dir
        # this operation needs to be a copy instead of rename (move)
        # in case windows system temp directory is on a different
        # logical drive than the output path
        print("Writing new archive files...")
        for root, dirs, files in os.walk(tmpdir_path):
            for name in files:
                tmp_p = Path(root).joinpath(name)
                orig_p = archive_dir.joinpath(name)
                if orig_p.exists():
                    orig_p.rename(backup_paths[orig_p])
                shutil.copy(tmp_p, archive_dir)
    except Exception as e:
        raise e
    finally:
        if tmp_exe is not None:
            Path(tmp_exe).unlink()

        print("Cleaning up temporary files...")
        if tmpdir_path:
            for root, dirs, files in os.walk(tmpdir_path):
                for name in files:
                    p = Path(root).joinpath(name)
                    p.unlink()
            tmpdir_path.rmdir()

def backup_lsb(lsb_file):
    target = f"{str(lsb_file)}.bak"
    if Path(target).exists():
        return 
    shutil.copyfile(str(lsb_file), target)

def revert_backup(lsb_file):
    target = f"{str(lsb_file)}.bak"
    if not Path(target).exists():
        return
    try:
        os.remove(str(lsb_file))
    except:
        pass
    try:
        os.rename(target, str(lsb_file))
    except:
        pass

# https://github.com/pmrowla/pylivemaker/blob/master/src/livemaker/cli/lmlsb.py
# https://pylivemaker.readthedocs.io/en/latest/usage.html
if __name__ == "__main__":
    while True:
        print()
        print("Select an action:")
        print("[0] Extract CSV from LSB")
        print("[1] Insert CSV into LSB")
        print("[2] Restore backup")
        print("[9] Toggle encoding (Current:", ENCODING, ")")
        print("[Any] Quit")
        match input():
            case "0":
                for f in list_files(".lsb"):
                    extractcsv(f)
                    extractmenu(f)
            case "1":
                for f in list_files(".lsb"):
                    backup_lsb(f)
                    csv_file = f.replace(".lsb", ".csv")
                    result = False
                    result = result or insertcsv(csv_file)
                    result = result or insertmenu(csv_file.replace(".csv", "_menu.csv"))
                    if not result:
                        revert_backup(f)
            case "2":
                for f in list_files(".bak"):
                    revert_backup(f.replace(".lsb.bak", ".lsb"))
            case "9":
                if ENCODING == "utf-8":
                    ENCODING = "utf-8-sig"
                elif ENCODING == "utf-8-sig":
                    ENCODING = "utf-8"
            case _:
                break
```  
The first option will go over each LSB recursively and create both CSV if possible.  
The second option does the opposite operation. It also creates a backup if needed.  
The third option will revert **all** `.lsb` files to their original backups.  
The fourth option lets you switch to `utf-8-sig`, if you need to use the CSV in Excel.  