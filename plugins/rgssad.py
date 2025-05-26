from __future__ import annotations
from . import Plugin, FileType
from pathlib import PurePath
import struct
import os
from typing import Any

class RGSSAD(Plugin):
    def __init__(self : RGSSAD) -> None:
        super().__init__()
        self.name : str = "RGSSAD"
        self.description : str = " v1.0\nExtract content from RGSSAD files"

    def extract(
        self : RGSSAD,
        update_file_dict : dict[str, Any],
        full_path : PurePath,
        target_dir : PurePath,
        backup_path : PurePath
    ) -> bool:
        if full_path.suffix.lower() not in (".rgssad", ".rgss2a", ".rgss3a"):
            return False
        try:
            with open(full_path, mode="rb") as f:
                magic = f.read(6).decode('ascii')
                if magic != "RGSSAD":
                    return False
                version = f.read(2)[1]
                if version not in (0x01, 0x03):
                    return False
                # read file list
                metadatas = self.read_rgssad_v3(f) if version == 0x03 else self.read_rgssad_v1(f)
                
                for metadata in metadatas:
                    file_path : PurePath = target_dir / metadata["filename"]
                    if os.path.isfile(file_path):
                        self.owner.log.error("[RGSSAD] Failed to extract:" + metadata["filename"] + ", file already exists\n" + self.owner.trbk(e))
                        continue
                    # check if file is valid for a plugin
                    for p in self.owner.plugins.values():
                        if p.match(file_path.name, False):
                            # create directory if not found
                            if not os.path.isdir(file_path.parent):
                                try:
                                    # create dir if needed
                                    os.makedirs(file_path.parent.as_posix(), exist_ok=True)
                                except Exception as e:
                                    self.owner.log.error("Couldn't create the following folder:" + file_path.parent.as_posix() + "\n" + self.trbk(e))
                            # write file
                            with open(file_path, mode="wb") as out:
                                f.seek(metadata["offset"])
                                out.write(self.decrypt_file_data(f.read(metadata["size"]), metadata["key_for_data"]))
                            # add to update_file_dict
                            update_file_dict[(file_path.relative_to(backup_path)).as_posix()] = {
                                "file_type":FileType.NORMAL,
                                "ignored":False,
                                "strings":0,
                                "translated":0,
                                "disabled_strings":0,
                            }
                            break
                return len(metadatas) > 0
        except Exception as e:
            self.owner.log.error("[RGSSAD] Failed to extract content from:" + full_path.as_posix() + "\n" + self.owner.trbk(e))
            return False

    def decrypt_file_data(self : RGSSAD, encrypted_data : bytes, initial_key : int) -> bytes:
        decrypted_data = bytearray()
        temp_key = initial_key
        for i, byte_val in enumerate(encrypted_data):
            if i > 0 and i % 4 == 0: # Update key every 4 bytes, but not before the first byte
                temp_key = (temp_key * 7 + 3) & 0xFFFFFFFF
            
            key_byte = (temp_key >> (8 * (i % 4))) & 0xFF
            decrypted_data.append(byte_val ^ key_byte)
        return bytes(decrypted_data)

    def read_int(self : RGSSAD, handle):
        return struct.unpack('<I', handle.read(4))[0]

    def decrypt_int_v1(self : RGSSAD, value : int, current_key : int):
        decrypted_value = value ^ current_key
        new_key = (current_key * 7 + 3) & 0xFFFFFFFF
        return decrypted_value, new_key

    def decrypt_filename_v1(self : RGSSAD, encrypted_name_bytes : bytes, current_key : int):
        decrypted_name = bytearray()
        for i, byte in enumerate(encrypted_name_bytes):
            decrypted_name.append(byte ^ (current_key & 0xFF))
            current_key = (current_key * 7 + 3) & 0xFFFFFFFF
        return decrypted_name, current_key

    def decrypt_int_v3(self : RGSSAD, value, key):
        return value ^ key

    def decrypt_filename_v3(self : RGSSAD, encrypted_name_bytes : bytes, key : int):
        decrypted_name = bytearray()
        for i, byte in enumerate(encrypted_name_bytes):
            decrypted_name.append(byte ^ (key >> (8 * (i % 4))) & 0xFF)
        return decrypted_name.decode('utf-8', errors='ignore')

    def read_rgssad_v1(self : RGSSAD, handle):
        # for .rgssad and .rgss2a
        archived_files = []
        handle.seek(8)
        key = 0xDEADCAFE # key is fixed
        
        while True:
            try:
                length_decrypted, key = self.decrypt_int_v1(self.read_int(handle), key)
                encrypted_name_bytes = handle.read(length_decrypted)
                decrypted_name_bytes, key = self.decrypt_filename_v1(encrypted_name_bytes, key)
                filename = decrypted_name_bytes.decode('utf-8', errors='ignore')
                size_decrypted, key = self.decrypt_int_v1(self.read_int(handle), key)

                archived_files.append({
                    'filename': filename.replace("\\", "/"),
                    'size': size_decrypted,
                    'key_for_data': key,
                    'offset': handle.tell()
                })
                handle.seek(size_decrypted, 1)
            except:
                break
        return archived_files

    def read_rgssad_v3(self : RGSSAD, handle):
        # for .rgss3a
        archived_files = []
        handle.seek(8)
        key = (self.read_int(handle) * 9 + 3) & 0xFFFFFFFF # key is at the beginning of the file
        
        while True:
            offset = self.decrypt_int_v3(self.read_int(handle), key)
            size_decrypted = self.decrypt_int_v3(self.read_int(handle), key)
            file_key = self.decrypt_int_v3(self.read_int(handle), key)
            length = self.decrypt_int_v3(self.read_int(handle), key)
            if(offset == 0):
                break
            filename = self.decrypt_filename_v3(handle.read(length), key)
            
            archived_files.append({
                'filename': filename.replace("\\", "/"),
                'size': size_decrypted,
                'key_for_data': file_key,
                'offset': offset
            })
        return archived_files