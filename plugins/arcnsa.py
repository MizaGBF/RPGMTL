from __future__ import annotations
from . import Plugin, WalkHelper
import io
import struct
from typing import Any
from pathlib import Path

class ArcNSA(Plugin):
    COMPRESSION_TYPES = {
        0: "None",
        1: "SPB",
        2: "LZSS",
        4: "NBZ",
    }
    def __init__(self : ArcNSA) -> None:
        super().__init__()
        self.name : str = "ArcNSA"
        self.description : str = " v0.2\nHandle arc.nsa archive files (Experimental)"

    def get_setting_infos(self : ArcNSA) -> dict[str, list]:
        return {
            "arcnsa_default_encoding": ["Select the default script encoding", "str", "shift_jis", ["auto"] + self.FILE_ENCODINGS],
        }

    def get_action_infos(self : ArcNSA) -> dict[str, list]:
        return {
            "arcnsa_export": ["Export Script Files", self._export]
        }

    def _export(self : ArcNSA, name : str, file_path : str, settings : dict[str, Any] = {}) -> str:
        try:
            base_path : Path = Path("projects", name, "nsa_script")
            base_path.mkdir(parents=True, exist_ok=True)
            with open("projects/" + name + "/originals/" + file_path, mode="rb") as reader:
                entries = self.read_archive_metadata(reader)
                for entry in entries:
                    if entry["name"].endswith(".txt") and entry["compression"] == "None":
                        reader.seek(entry["offset"])
                        (base_path / (file_path.replace('/', '_') + '_' + entry["name"])).write_bytes(reader.read(entry["size"]))
                return "Scripts dumped to " + base_path.as_posix()
        except Exception as e:
            self.owner.log.error("[ArcNSA] Action 'arcnsa_export' failed with error:\n" + self.owner.trbk(e))
            return "An error occured, the file might be badly formatted."

    def file_extension(self : ArcNSA) -> list[str]:
        return ["nsa"]

    def match(self : ArcNSA, file_path : str, is_for_action : bool) -> bool:
        return file_path.endswith(".nsa")

    def is_streaming(self : ArcNSA, file_path : str, is_for_action : bool) -> bool:
        return True

    def read_cstring(self : ArcNSA, reader : io.BufferedReader):
        chars = []
        while True:
            c = reader.read(1)
            if not c or c == b'\x00':
                break
            chars.append(c)
        return b''.join(chars)

    def read_archive_metadata(self : ArcNSA, reader : io.BufferedReader) -> list[dict]:
        # get file length
        reader.seek(0)
        length : int = reader.tell()
        reader.seek(0, 2)
        length = reader.tell() - length
        reader.seek(0)
        # handle signature
        if struct.unpack('>H', reader.read(2))[0] != 0:
            reader.seek(0)
        initial = reader.tell()
        # file count
        count = reader.read(2)
        if len(count) < 2:
            raise Exception("[ArcNSA] File too short or corrupt.")
        count = struct.unpack('>H', count)[0]
        # base offset
        base_offset = reader.read(4)
        if len(base_offset) < 4:
            raise Exception("[ArcNSA] File too short or corrupt (base offset missing).")
        base_offset = struct.unpack('>I', base_offset)[0]
        base_offset = initial + base_offset
        if base_offset >= length or base_offset < 15 * count:
            raise Exception("[ArcNSA] File too short or corrupt (bad base offset).")

        entries = []
        for i in range(count):
            if base_offset - reader.tell() < 15:
                raise Exception("[ArcNSA] Unexpected end-of-index.")

            name = self.read_cstring(reader)
            if not name:
                raise Exception("[ArcNSA] Empty filename encountered; aborting.")

            # Read 1 byte for compression type.
            comp_type_byte = reader.read(1)
            if len(comp_type_byte) != 1:
                raise Exception("[ArcNSA] Unexpected end-of-index (compression type).")
            comp_type = comp_type_byte[0]

            # Read 4 bytes for offset (big-endian) and add base_offset.
            offset = reader.read(4)
            if len(offset) < 4:
                raise Exception("[ArcNSA] Unexpected end-of-index (offset).")
            entry_offset = struct.unpack('>I', offset)[0] + base_offset

            # Read 4 bytes for size.
            size_bytes = reader.read(4)
            if len(size_bytes) < 4:
                raise Exception("[ArcNSA] Unexpected end-of-index (size).")
            size = struct.unpack('>I', size_bytes)[0]

            # Read 4 bytes for unpacked size.
            unpacked_bytes = reader.read(4)
            if len(unpacked_bytes) < 4:
                raise Exception("[ArcNSA] Unexpected end-of-index (unpacked size).")
            unpacked_size = struct.unpack('>I', unpacked_bytes)[0]

            entries.append({
                'bname': name,
                'name': name.decode('utf-8', errors='ignore'),
                'bcompression': comp_type_byte,
                'compression': self.COMPRESSION_TYPES.get(comp_type, f"Unknown ({comp_type})"),
                'offset': entry_offset,
                'size': size,
                'unpacked_size': unpacked_size,
                'modified_content': None
            })
        return entries

    def write_archive(self : ArcNSA, reader : io.BufferedReader, writer : io.BufferedWriter, entries : list[dict]) -> None:
        reader.seek(0)
        # handle signature
        s = reader.read(2)
        if s == b'\x00\x00':
            writer.write(s)
        else:
            reader.seek(0)
        writer.write(struct.pack('>H', len(entries)))
        reader.read(2)
        offset = reader.read(4)
        writer.write(offset)
        offset = 0
        for i, entry in enumerate(entries):
            writer.write(entry['bname'])
            writer.write(b'\x00')
            
            writer.write(entry['bcompression'])
            writer.write(struct.pack('>I', offset))
            offset += entry['size']
            writer.write(struct.pack('>I', entry['size']))
            writer.write(struct.pack('>I', entry['unpacked_size']))
            
        for i, entry in enumerate(entries):
            if entry['modified_content'] is None:
                reader.seek(entry['offset'])
                writer.write(reader.read(entry['size']))
            else:
                writer.write(entry['modified_content'])

    def read_stream(self : ArcNSA, file_path : str, reader : io.BufferedReader) -> list[list[str]]:
        entries : list[dict] = self.read_archive_metadata(reader)
        encoding : str = self.settings.get("arcnsa_default_encoding", "auto")
        groups : list[list[str]] = []
        for entry in entries:
            if entry["name"].endswith(".txt"):
                if entry["compression"] == "None":
                    group : list[str] = [""]
                    reader.seek(entry["offset"])
                    data : bytes = reader.read(entry["size"])
                    lines : list[str]
                    try:
                        if encoding == "auto":
                            raise Exception()
                        lines = data.decode(encoding, errors='ignore').split('\n')
                    except:
                        self.reset() # reset encoding
                        lines = self.decode(data).split('\n')
                        
                    for line in lines:
                        if line.strip() != "":
                            if line.endswith('\r'):
                                group.append(line[:-1])
                            else:
                                group.append(line)
                    if len(group) > 1:
                        groups.append([self.owner.CHILDREN_FILE_ID + entry["name"]])
                        groups.append(group)
                else:
                    self.owner.log.warning("[ArcNSA] Unsupported Compression for:" + entry["name"])
        return groups

    def write_stream(self : Plugin, name : str, file_path : str, reader : io.BufferedReader, output_path : Path) -> tuple[int, int]:
        entries : list[dict] = self.read_archive_metadata(reader)
        encoding : str = self.settings.get("arcnsa_default_encoding", "auto")
        modified : bool = False
        for entry in entries:
            if entry["name"].endswith(".txt"):
                if entry["compression"] == "None":
                    reader.seek(entry["offset"])
                    data : bytes = reader.read(entry["size"])
                    self.reset()
                    details : dict = {
                        "encoding":None,
                        "original":data.split(b"\n"),
                        "content":None
                    }
                    try:
                        if encoding == "auto":
                            raise Exception()
                        details["content"] = data.decode(encoding, errors='ignore').split('\n')
                        details["encoding"] = encoding
                    except:
                        self.reset() # reset encoding
                        details["content"] = self.decode(data).split('\n')
                        details["encoding"] = self.FILE_ENCODINGS[self._enc_cur_]
                    fname : str = file_path + "/" + entry["name"].replace("/", " ").replace("\\", " ")
                    if fname in self.owner.strings[name]["files"] and not self.owner.projects[name]["files"][fname]["ignored"]:
                        helper : WalkHelper = WalkHelper(fname, self.owner.strings[name])
                        # update string
                        for i, s in enumerate(details["content"]):
                            if s.strip() != "":
                                if s.endswith('\r'):
                                    tmp : str = helper.apply_string(s[:-1])
                                    if helper.str_modified:
                                        details["content"][i] = tmp + '\r'
                                        details["content"][i] = details["content"][i].encode(details["encoding"])
                                        modified = True
                                    else:
                                        details["content"][i] = details["original"][i]
                                else:
                                    tmp : str = helper.apply_string(s)
                                    if helper.str_modified:
                                        details["content"][i] = tmp.encode(details["encoding"])
                                        modified = True
                                    else:
                                        details["content"][i] = details["original"][i]
                            else:
                                details["content"][i] = details["original"][i]
                        details["content"] = b"\n".join(details["content"])
                        content, changed = self.owner.apply_fixes(name, file_path, details["content"], False)
                        if changed:
                            details["content"] = content
                        entry["modified_content"] = details["content"]
                        entry["size"] = len(details["content"])
                        entry["unpacked_size"] = entry["size"]
        if modified:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, mode="wb") as writer:
                self.write_archive(reader, writer, entries)
        return (1, 0)