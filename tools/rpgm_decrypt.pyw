import tkinter as tk
from tkinter import filedialog, simpledialog
from pathlib import Path
import json
import argparse
import os

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DRAG_AND_DROP = True
except:
    DRAG_AND_DROP = False

class RPGMakerDecrypt:

    RPG_MAKER_HEADER : bytes = bytes.fromhex("5250474d560000000003010000000000")
    EXT_TABLE_DEC : dict[str, str] = {
        ".png_":".png",
        ".rpgmvp":".png",
        ".ogg_":".ogg",
        ".rpgmvo":".ogg"
    }
    EXT_TABLE_MV_ENC : dict[str, str] = {
        ".png":".rpgmvp",
        ".ogg":".rpgmvo"
    }
    
    def __init__(self) -> None:
        self.mode = "MV"
        self.output_folder = Path(os.getcwd())
        self.key = None
        self.log = print
    
    def reset_key(self) -> None:
        if self.key:
            self.key = None
            # Add your key reset connection logic here
            self.log("Encryption Key has been reset.")

    def set_key(self, key_str : str) -> None:
        try:
            self.key = bytes.fromhex(key_str)
            self.log(f"Encryption Key sets to {self.key.hex()}.")
        except:
            self.log(f"[ERROR] '{key_str}' is not valid hexadecimal.")

    def read_key(self, path : str) -> bool:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.set_key(json.load(f)["encryptionKey"])
                return True
        except:
            self.log(f"[ERROR] Failed to extract key from '{path}'.")
            return False

    def process_single_file(self, path : Path) -> None:
        with open(path, 'rb') as f:
            data = f.read()
        match path.suffix:
            case ".png_"|".ogg_"|".rpgmvp"|".rpgmvo":
                if not data.startswith(self.RPG_MAKER_HEADER[:8]):
                    self.log(f"[ERROR] Skipping: {path} (Doesn't appear to be an encrypted)")
                    return
                    
                encrypted_header : bytes = data[16:32]
                rest_of_file : bytes = data[32:]
                
                # XOR the encrypted header with the key
                decrypted_header : bytes = bytes(a ^ b for a, b in zip(encrypted_header, self.key))
                output_file : str = (path.stem + self.EXT_TABLE_DEC[path.suffix])
                with open(self.output_folder / output_file, 'wb') as f_out:
                    f_out.write(decrypted_header + rest_of_file)
                    
                self.log(f"Decrypted: {output_file}")
            case ".png"|".ogg":
                if len(data) < 16:
                    self.log(f"[ERROR] Skipping: {path} (File too small)")
                    return
                    
                original_header : bytes = data[:16]
                rest_of_file : bytes = data[16:]
                
                # XOR the first 16 bytes of the clean file
                encrypted_header : bytes = bytes(a ^ b for a, b in zip(original_header, self.key))
                
                output_file : str = path.stem + ((path.suffix + "_") if self.mode == "MZ" else self.EXT_TABLE_MV_ENC[path.suffix])
                with open(self.output_folder / output_file, 'wb') as f_out:
                    # Prepend the fake header, then the encrypted header, then the rest
                    f_out.write(self.RPG_MAKER_HEADER + encrypted_header + rest_of_file)
                    
                self.log(f"Encrypted: {output_file}")

    def process_files(self, file_paths : list[str]) -> None:
        if not self.output_folder.is_dir():
            self.log(f"[ERROR] '{self.output_folder}' isn't a valid directory.")
            return
        for path in file_paths:
            if path.lower().endswith("system.json"):
                if self.read_key(path):
                    break
        if self.key is None:
            self.log("[ERROR] Please provide System.json.")
            return
        for path in file_paths:
            try:
                self.process_single_file(Path(path))
            except Exception as e:
                self.log(f"[CRITICAL] An unexpected exception occured: {e}")
                self.log("Aborting...")
                return

class RPGMakerDecryptGUI:

    def __init__(self, root : tk.Tk) -> None:
        self.root = root
        self.root.title("RPG Maker Asset Decrypter")
        self.root.geometry("550x450")
        self.root.minsize(400, 300)
        self.root.resizable(False, False)

        self.rpgm = RPGMakerDecrypt()
        self.rpgm.log = self.log

        self._build_ui()
        if not DRAG_AND_DROP:
            self.log("[WARNING] Drag & Drop is disabled. Please run 'pip install tkinterdnd2' to install the missing dependency.")
        else:
            self._register_drag_and_drop()
        self.log("Awaiting key and files...")

    def _build_ui(self) -> None:
        # ==========================================
        # ROW 1: Controls (Reset Key, Mode, Output)
        # ==========================================
        self.frame_controls = tk.Frame(self.root)
        self.frame_controls.pack(side=tk.TOP, fill=tk.X, padx=10, pady=10)

        self.btn_set = tk.Button(self.frame_controls, text="Set Key", command=self.ask_key)
        self.btn_set.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_reset = tk.Button(self.frame_controls, text="Reset Key", command=self.rpgm.reset_key)
        self.btn_reset.pack(side=tk.LEFT, padx=(0, 5))

        self.btn_mode = tk.Button(self.frame_controls, text="MV (.rpgmvp .rpgmvo)", command=self.toggle_mode, width=18)
        self.btn_mode.pack(side=tk.LEFT, padx=5, expand=True)

        self.btn_output = tk.Button(self.frame_controls, text="Set Output Folder", command=self.set_output_folder)
        self.btn_output.pack(side=tk.RIGHT, padx=(5, 0))

        # ==========================================
        # ROW 2: Drag and Drop / File Selection Area
        # ==========================================
        self.frame_dnd = tk.Frame(self.root, relief=tk.SUNKEN, borderwidth=2, bg="#e0e0e0")
        self.frame_dnd.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # Give the DND area some height
        self.frame_dnd.pack_propagate(False)
        self.frame_dnd.config(height=120)

        self.lbl_dnd = tk.Label(
            self.frame_dnd,
            text=(
                "Drag & Drop files here\n(or use the button below)"
                if DRAG_AND_DROP
                else "Use the button below"
            ),
            bg="#e0e0e0",
            fg="#555555"
        )
        self.lbl_dnd.pack(expand=True)

        self.btn_select = tk.Button(self.frame_dnd, text="Select Files", command=self.select_files)
        self.btn_select.pack(pady=(0, 10))

        # ==========================================
        # ROW 3: Logging Area with Scrollbar
        # ==========================================
        self.frame_log = tk.Frame(self.root)
        self.frame_log.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, padx=10, pady=(5, 10))

        self.scrollbar = tk.Scrollbar(self.frame_log)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.text_log = tk.Text(self.frame_log, yscrollcommand=self.scrollbar.set, state=tk.DISABLED, wrap=tk.WORD, bg="#1e1e1e", fg="#00ff00")
        self.text_log.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.config(command=self.text_log.yview)

    # ==========================================
    # Drag and Drop Setup & Event Binding
    # ==========================================
    def _register_drag_and_drop(self) -> None:
        self.frame_dnd.drop_target_register(DND_FILES)
        
        # Bind functions to handle visual feedback states and the actual drop
        self.frame_dnd.dnd_bind('<<DropEnter>>', self.on_drop_enter)
        self.frame_dnd.dnd_bind('<<DropLeave>>', self.on_drop_leave)
        self.frame_dnd.dnd_bind('<<Drop>>', self.on_file_drop)

    def on_drop_enter(self, event) -> None:
        # Change drop zone colors to signal readiness
        self.frame_dnd.config(bg="#bbf7d0")
        self.lbl_dnd.config(bg="#bbf7d0", text="Drop your files")

    def on_drop_leave(self, event) -> None:
        # Revert colors if user drags away without releasing
        self.frame_dnd.config(bg="#e0e0e0")
        self.lbl_dnd.config(bg="#e0e0e0", text="Drag & Drop files here\n(or use the button below)")

    def on_file_drop(self, event) -> None:
        self.on_drop_leave(event) # Reset UI appearance
        
        raw_data = event.data
        if not raw_data:
            return

        # When dragging multiple files, or files with spaces,
        # TkinterDnD2 returns them wrapped in curly braces like '{C:/My Path/file.png} C:/NormalPath/file.png'.
        # Using Tcl's built-in splitlist splits them into clean paths seamlessly.
        file_paths = self.root.tk.splitlist(raw_data)
        
        if file_paths:
            self.rpgm.process_files(file_paths)

    # ==========================================
    # Logic & Event Handlers
    # ==========================================

    def ask_key(self) -> None:
        key = simpledialog.askstring(
            "Set key",
            "Input an encryption key:"
        )
        if key is not None:
            if key == "":
                self.log("[ERROR] The key can't be an empty string")
            else:
                self.rpgm.set_key(key.strip())

    def toggle_mode(self) -> None:
        if self.rpgm.mode == "MV":
            self.rpgm.mode = "MZ"
            self.btn_mode.config(text="MZ (.png_ .ogg_)")
        else:
            self.rpgm.mode = "MV"
            self.btn_mode.config(text="MV (.rpgmvp .rpgmvo)")
            
        self.log(f"Switched mode to {self.rpgm.mode}.")

    def set_output_folder(self) -> None:
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.rpgm.output_folder = Path(folder)
            self.log(f"Output folder set to: {self.rpgm.output_folder}")

    def select_files(self) -> None:
        # Determine which file extension to filter by based on the current mode
        ext = (
            "system.json *.png *.ogg *.rpgmvp *.rpgmvo"
            if self.rpgm.mode == "MV"
            else "system.json *.png *.ogg *.png_ *.ogg_"
        )
        filetypes = (
            (f"RPG Maker {self.rpgm.mode} Files", ext),
            ("All Files", "*.*")
        )
        
        files = filedialog.askopenfilenames(
            title="Select files to process",
            filetypes=filetypes,
            initialdir=self.rpgm.output_folder
        )
        if files:
            self.rpgm.process_files(files)

    def log(self, message : str) -> None:
        self.text_log.config(state=tk.NORMAL)
        self.text_log.insert(tk.END, message + "\n")
        self.text_log.see(tk.END)
        self.text_log.config(state=tk.DISABLED)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="RPG Maker MV/MZ Asset Encrypter/Decrypter")
    parser.add_argument("-m", "--mode", choices=["MZ", "MV"], default='MV', nargs='?', help="RPG Maker game engine")
    parser.add_argument("-o", "--output_folder", help="Output directory path")
    
    input_group = parser.add_mutually_exclusive_group()
    input_group.add_argument("-i", "--input", help="Input file path")
    input_group.add_argument("-f", "--filelistinput", help="Path to a file containing a list of files to decrypt/encrypt")
    
    # You only need one of these two arguments
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-k", "--key", help="The encryption key found in System.json")
    group.add_argument("-s", "--system", help="Path to System.json to extract the key automatically")

    args = parser.parse_args()
    if args.input is None and args.filelistinput is None:
        if DRAG_AND_DROP:
            root = TkinterDnD.Tk()
        else:
            root = tk.Tk()
        app = RPGMakerDecryptGUI(root)
        root.mainloop()
    else:
        try:
            rpgm = RPGMakerDecrypt()
            if args.key:
                rpgm.set_key(args.key)
            elif args.system:
                rpgm.read_key(args.system)
            else:
                parser.print_help()
                print("Please provide the encryption key with either '-k' or '-s'")
                os._exit(0)
            if args.output_folder:
                rpgm.output_folder = Path(args.output_folder)
            rpgm.mode = args.mode
            if args.input:
                rpgm.process_single_file(Path(args.input))
            else:
                try:
                    with open(args.filelistinput, mode="r", encoding="utf-8") as f:
                        file_list : list[str] = [fn.strip() for fn in f.readlines()]
                    rpgm.process_files(file_list)
                except Exception as e:
                    print(f"Failed to read '{args.filelistinput}': {e}")
                    os._exit(0)
        except Exception as e:
            print(f"Error: {e}")