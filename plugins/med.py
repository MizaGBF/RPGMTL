from __future__ import annotations
from . import Plugin, WalkHelper
from typing import Any
import io
import textwrap

# Based on some script I got from someone.
# The original author is unknown, feel free to hit me up so I can credit them if you know.
class MED(Plugin):
    CIPHER : bytes = b'\x00\x23\x52\x55\x4C\x45\x5F\x56\x49\x45\x57\x45\x52\x00\x3A\x56\x49\x45\x57\x5F\x30\x00\x7B\x00'
    
    def __init__(self : MED) -> None:
        super().__init__()
        self.name : str = "MED"
        self.description : str = "v1.7\nHandle md_scr.med MED files"
        self.related_tool_plugins : list[str] = [self.name]

    def match(self : MED, file_path : str, is_for_action : bool) -> bool:
        if is_for_action:
            return "md_scr.med" in file_path
        else:
            return file_path.endswith("md_scr.med")

    def get_setting_infos(self : MED) -> dict[str, list]:
        return {
            "med_char_per_line": ["Character Limit per line (0 or less means None)", "num", 64, None]
        }

    def get_action_infos(self : MED) -> dict[str, list]:
        return {
            "med_check_ascii": ["assets/plugins/med_ascii_check.png", "Look for invalid characters", self.look_non_ascii]
        }

    def get_tool_infos(self : MED) -> dict[str, list]:
        return {
            "med_text_wrap": [
                "assets/images/text_wrap.png", "ExS-TIA 1~3 Text wrap", self.lusterise_text_wrap,
                {
                    "type":self.COMPLEX_TOOL,
                    "params":{
                        "_t_0000":["This Text Wrap is DESTRUCTIVE, as it relies on spaces. It's recommended to backup strings.bak-1.json after.", "display", None, None],
                        "_t_0001":["Non-ASCII or special characters might also cause issues.", "display", None, None],
                        "_t_0002":["If you want to manually wrap some strings beforehand, do it and add 3 spaces at the end.", "display", None, None],
                        "_t_char_limit":["Character per line", "num", 64, None]
                    },
                    "help":"Tool to automatically wrap texts.<br>Only used and tested on the ExS-TIA Game series from Lusterise.<br>(Episode 1, 2, A, 3 and sides)"
                }
            ]
        }

    def lusterise_text_wrap(self : MED, name : str, params : dict[str, Any]) -> str:
        """
        Notes:
            Games that I tested don't support new lines so the text wrap works as such:
            - First, check if the string is bigger than N characters (64 in the ones I tested)
            - Use textwrap with N characters, break_on_hyphens set to False (to avoid new lines on - for example)
            - Pad the strings with space until size N
            - Join the strings
            
            As such, the logic break is the function is ran again on an already processed line.
            To counter this, three spaces are added at the end, to be used as padding.
        """
        try:
            limit : int = int(params["_t_char_limit"])
            if limit < 1:
                raise Exception()
        except:
            return "Invalid character limit, it must be a positive integer."
        try:
            self.owner.save() # save first!
            self.owner.backup_strings_file(name) # backup strings.json
            self.owner.load_strings(name) # if not loaded
            modified : int = 0
            for sid, sd in self.owner.strings[name]["strings"].items():
                if self.owner.strings[name]["strings"][sid][1] is not None and not self.owner.strings[name]["strings"][sid][1].endswith("   "):
                    s, b = self.textwrap_string(self.owner.strings[name]["strings"][sid][1], limit)
                    if b:
                        self.owner.strings[name]["strings"][sid][1] = s
                        modified += 1

            for file in self.owner.strings[name]["files"]:
                for i, group in enumerate(self.owner.strings[name]["files"][file]):
                    for j in range(1, len(group)):
                        if self.owner.strings[name]["files"][file][i][j][1] is not None and not self.owner.strings[name]["files"][file][i][j][1].endswith("   "):
                            s, b = self.textwrap_string(self.owner.strings[name]["files"][file][i][j][1], limit)
                            if b:
                                self.owner.strings[name]["files"][file][i][j][1] = s
                                modified += 1
            if modified:
                self.owner.modified[name] = True
                return "Text wrap applied to {} strings, make sure to backup strings.bak-1.json!".format(modified)
            else:
                return "No strings in need of text wrapping."
        except Exception as e:
            self.owner.log.error("[MED] Action 'lusterise_text_wrap' failed with error:\n" + self.owner.trbk(e))
            return "An error occured."

    def textwrap_string(self : MED, string : str, limit : int) -> tuple[str, bool]:
        if len(string) > limit:
            lines = textwrap.wrap(string, width=limit, break_on_hyphens=False)
            for i in range(len(lines) - 1):
                lines[i] = lines[i].ljust(limit)
            lines[i-1] = lines[i-1]
            wrapped = "".join(lines)
            if wrapped != string:
                wrapped += "   " # wrapped marker
                return wrapped, True
        return string, False

    def look_non_ascii(self : MED, name : str, file_path : str, settings : dict[str, Any] = {}) -> str:
        try:
            count : int = 0
            for g, group in enumerate(self.owner.strings[name]["files"][file_path]):
                for i in range(1, len(group)):
                    lc = group[i]
                    gl = self.owner.strings[name]["strings"][lc[0]]
                    if lc[2] and lc[1] is not None:
                        if "[" in lc[1] or "]" in lc[1] or "♪" in lc[1] or any(ord(ch) > 0x7F for ch in lc[1]): # check if has non-ASCII character
                            count += 1
                            self.owner.strings[name]["files"][file_path][g][i][4] = 1
                    elif gl[1] is not None:
                        if "[" in gl[1] or "]" in gl[1] or "♪" in gl[1] or any(ord(ch) > 0x7F for ch in gl[1]): # check if has non-ASCII character
                            count += 1
                            self.owner.strings[name]["files"][file_path][g][i][4] = 1
                    else:
                        continue
            if count > 0:
                self.owner.modified[name] = True
                return "{} strings contain non-ASCII characters in this file, and have been marked".format(count)
            else:
                return "No strings contain non-ASCII characters in this file"
        except Exception as e:
            self.owner.log.error("[MED] Action 'look_non_ascii' failed with error:\n" + self.owner.trbk(e))
            return "An error occured."

    def read(self : MED, file_path : str, content : bytes) -> list[list[str]]:
        files : dict[str, bytearray] = self.unpack(content)
        if files is not None:
            return self.extract_strings(files)
        else:
            return [[]]

    def write(self : MED, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        files : dict[str, bytearray] = self.unpack(content)
        if files is not None:
            return self.patch_strings(name, file_path, self.owner.strings[name], content, files)
        else:
            return content, False

    def remove_dupes(self : MED, key):
        for i in range(2, len(key)+1):
            cnt = int(len(key) / i + 1)
            tmp = key[:i]
            ans = bytearray(tmp)
            tmp *= cnt
            tmp = tmp[:len(key)]
            if tmp == key:
                return ans
        return None

    def decrypt(self : MED, data : bytes, key : bytearray) -> bytearray:
        content = bytearray(data)
        for i in range(0x10, len(content)):
            content[i] = (content[i]+key[(i - 0x10) % len(key)]) & 0xff
        return content

    def encrypt(self : MED, data: bytearray, key : bytearray) -> bytearray:
        for i in range(0x10, len(data)):
            data[i] = (data[i] - key[(i - 0x10) % len(key)]) & 0xff
        return data

    def unpack(self : MED, data : bytes) -> dict[str, bytearray]:
        if data[:4] != b'MDE0':
            raise Exception("[MED] Invalid Magic Number")
        enlen = int.from_bytes(data[4:6], byteorder='little')
        en_count = int.from_bytes(data[6:8], byteorder='little')

        files : dict[str, bytes] = {}
        secret : list[int]|None = None
        for i in range(en_count):
            entry : bytes = data[16 + i * enlen:16 + (i + 1) * enlen]
            offset : int = int.from_bytes(entry[-4:], byteorder='little')
            length : int = int.from_bytes(entry[-8:-4], byteorder='little')
            unk : int = int.from_bytes(entry[-12:-8], byteorder='little')
            name : str = ""
            for i in entry:
                if not i:
                    break
                else:
                    name += chr(i)
            filename = f'{name}_{unk}'
            files[filename] = data[offset:offset+length]
            
            if filename.startswith('_VIEW'):
                raw = files[filename][0x10:0x28]
                secret = []
                for i in range(24):
                    t = raw[i] - self.CIPHER[i]
                    t = - t
                    if t < 0:
                        t += 256
                    secret.append(t)

        if secret:
            key : bytearray = bytearray(map(lambda x: x & 0xff, secret))
            key = self.remove_dupes(key)
            for f, data in files.items():
                files[f] = self.decrypt(data, key)
            return files
        else:
            raise Exception("[MED] Failed to unpack file")

    def _is_valid_string(self : MED, line: bytes) -> bool:
        for ch in line:
            if ch < 0x1f and ch not in (9, 13, 10): # \t, \n, \r
                return False
        return True

    def _is_jp_text(self : MED, line: str) -> bool:
        for ch in line:
            if ('\u0800' <= ch <= '\u9fa5') or ('\uff01' <= ch <= '\uff5e'):
                return True
        return False

    def _is_comment(self : MED, line: str) -> bool:
        if len(line) == 0 or line[0] in ';#':
            return True
        return False

    def extract_strings(self : MED, files : dict[str, bytearray]) -> list[list[str]]:
        entries : list[list[str]] = []
        count = 0
        for f, data in files.items():
            offset : int = int.from_bytes(data[4:8], byteorder='little') + 0x10
            content : bytearray = data[offset:]
            file_content : bytes = b''
            strings : list[str] = [""]
            file_entries : list[list[str]] = [[self.owner.CHILDREN_FILE_ID + "{:05}_".format(count) + f]]
            for i in content:
                if i:
                    file_content += int.to_bytes(i, 1, byteorder='little')
                else:
                    try:
                        if self._is_valid_string(file_content):
                            decoded : str = file_content.decode('cp932', errors='ignore')
                            if not self._is_comment(decoded) and self._is_jp_text(decoded):
                                strings.append(decoded)
                            else:
                                if len(strings) > 1:
                                    file_entries.append(strings)
                                    strings = [""]
                                strings[0] = decoded
                    except Exception as e:
                        self.owner.log.warning("[MED] Error in 'extract_med':\n" + self.owner.trbk(e))
                    file_content = b''
            if len(strings) > 1:
                file_entries.append(strings)
            if len(file_entries) > 1:
                entries.extend(file_entries)
            count += 1
        return entries

    def patch_strings(self : MED, pname : str, file_path : str, strings : dict, content : bytes, files : dict[str, bytearray]) -> tuple[bytes, bool]:
        modified : bool = False
        count = 0
        for f in files:
            fname : str = file_path + "/{:05}_".format(count) + f.replace("/", " ").replace("\\", " ")
            group : str = ""
            if fname in strings["files"] and not self.owner.projects[pname]["files"][fname]["ignored"]:
                helper : WalkHelper = WalkHelper(fname, strings)
                data : bytearray = files[f]
                offset : int = int.from_bytes(data[4:8], byteorder='little') + 0x10
                buffer : bytes = b''
                while offset < len(data):
                    if data[offset]:
                        buffer += data[offset:offset+1]
                    else:
                        if self._is_valid_string(buffer):
                            decoded : str = buffer.decode('cp932', errors='ignore')
                            if self._is_comment(decoded) or not self._is_jp_text(decoded):
                                group = decoded
                                offset += 1
                                buffer = b''
                                continue
                            else:
                                tmp : str = helper.apply_string(decoded, group)
                                if helper.str_modified:
                                    offset -= len(buffer)
                                    encoded = tmp.encode('cp932', errors='ignore')
                                    data[offset:offset+len(buffer)] = encoded
                                    offset += len(encoded)
                                    modified = True
                                buffer = b''
                        else:
                            buffer = b''
                    offset += 1
                data[:4] = int.to_bytes(len(data)-0x10, 4, byteorder='little')
            count += 1
        if modified:
            # header
            enlen = int.from_bytes(content[4:6], byteorder='little')
            en_count = int.from_bytes(content[6:8], byteorder='little')
            
            # get secret
            secret : list[int]|None = None
            for i in range(en_count):
                entry : bytes = content[16 + i * enlen:16 + (i + 1) * enlen]
                offset : int = int.from_bytes(entry[-4:], byteorder='little')
                length : int = int.from_bytes(entry[-8:-4], byteorder='little')
                unk : int = int.from_bytes(entry[-12:-8], byteorder='little')
                name : str = ""
                for i in entry:
                    if not i:
                        break
                    else:
                        name += chr(i)
                f = f'{name}_{unk}'
                if f.startswith('_VIEW'):
                    view_data = content[offset:offset+length]
                    raw = view_data[0x10:0x28]
                    secret = []
                    for i in range(24):
                        t = raw[i] - self.CIPHER[i]
                        t = - t
                        if t < 0:
                            t += 256
                        secret.append(t)
                    key : bytearray = bytearray(map(lambda x: x & 0xff, secret))
                    key = self.remove_dupes(key)
                    break

            # write
            with io.BytesIO() as handle:
                # header
                handle.write(b'MDE0')
                handle.write(int.to_bytes(enlen, 1, byteorder='little'))
                handle.write(b'\x00')
                handle.write(int.to_bytes(en_count, 2, byteorder='little'))
                handle.write(b'\x00' * 8)
                
                offset = 0x10 + en_count * enlen
                
                file_data = []
                for f, data in files.items():
                    p = len(f) - 1
                    while f[p] != "_": # ???
                        p -= 1
                    name : bytes = f[:p].encode()
                    name += b'\x00' * (enlen - len(name) - 12)
                    unk = int.to_bytes(int(f[p+1:]), 4, byteorder='little')
                    
                    encrypted : bytearray = self.encrypt(data, key)
                    handle.write(name)
                    handle.write(unk)
                    handle.write(int.to_bytes(len(encrypted), 4, byteorder='little'))
                    handle.write(int.to_bytes(offset, 4, byteorder='little'))
                    offset += len(encrypted)
                    file_data.append(encrypted)
                handle.write(b''.join(file_data))
                return handle.getvalue(), True
        else:
            return content, False