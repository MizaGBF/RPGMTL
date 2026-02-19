# RPGMTL  
  
## Translating Live Maker games  
  
My workflow is the following.  
Start by installing [pylivemaker](https://github.com/pmrowla/pylivemaker).  
Go in the directory of the game that you want to translate, with a terminal/command prompt, and extract the files:  
```console
mkdir game_files
lmar x game.ext -o game_files
lmar x game.dat -o game_files
lmar x game.exe -o game_files
```
*You only need one of those three command, depending on where the files are packed.*  
  
The `game_files` folder should contain many `.lsb` files.  
```console
cd game_files
```
Not all of them have strings to translate, but you'll have to run the following command on all of them (Consider writing some sort of script to automate it):  
```console
lmlsb extractcsv --encoding=utf-8-sig FILE_NAME.lsb FILE_NAME.csv
```
  
You can now import the content of this folder into RPGMTL, the CSV plugin is able to handle those files.  
Once done, copy back the modified CSV files into the `game_files` folder.
You'll have to run this command again on each file with a matching `.csv` file:
```console
lmlsb insertcsv --encoding=utf-8-sig FILE_NAME.lsb FILE_NAME.csv
```
  
Note: Make sure the strings are CP932 compliants or they won't be patched in.  

  
Then, you can patch the game.  
```console
cd ..
lmpatch -r game.ext game_files
lmpatch -r game.dat game_files
lmpatch -r game.exe game_files
```
*You only need one of those three command, depending on where the files are packed.*  
  
Note: Technically, you don't have to patch. You can simply put your modified files in the game folder, respecting the original archive folder structure. The engine checks for files outside the archive first, and inside second.
  
## Full-width issue  
The engine forces alphanumeric characters to full-width by default.  
On the later versions (v3), it can be fixed according to [the pylivemaker Documentation](https://pylivemaker.readthedocs.io/en/latest/usage.html#notes-for-translation-patches).  
There is no solution for games using the v2 version to this date.  
