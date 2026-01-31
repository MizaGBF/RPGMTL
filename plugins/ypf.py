from __future__ import annotations
from . import Plugin, FileType, IntBool
import io
import os
import json
import struct
import zlib
from enum import Enum
from pathlib import PurePath
from typing import Any

# The logic is inspired from a C# code (I believe) to which I lost the original and link, feel free to point me to it so I can add the credit

# ##########################################################
# Checksum classes are used name and file data validation
# ##########################################################
class YChecksum:
    def compute_hash(self : YChecksum, data : bytes) -> int:
        raise NotImplementedError

    def compute_stream(self : YChecksum, stream: io.BufferedReader, length: int) -> int:
        data = stream.read(length)
        return self.compute_hash(data)

class YAdler32(YChecksum):
    def compute_hash(self : YAdler32, data : bytes) -> int:
        # zlib.adler32 returns signed int in Python3, mask to 32-bit unsigned
        return zlib.adler32(data) & 0xFFFFFFFF

class YCrc32(YChecksum):
    def compute_hash(self : YCrc32, data : bytes) -> int:
        return zlib.crc32(data) & 0xFFFFFFFF

class YMurmurHash2(YChecksum):
    def compute_hash(self : YMurmurHash2, data : bytes) -> int:
        # Implementation of MurmurHash2 (32-bit)
        seed = 0
        data_length = len(data)
        # magics
        m = 0x5bd1e995;
        r = 24;
        h = (seed ^ data_length) & 0xFFFFFFFF
        
        index = 0
        while data_length >= 4:
            k = struct.unpack_from('<I', data, index)[0]
            
            k = (k * m) & 0xFFFFFFFF
            k = (k ^ (k >> r)) & 0xFFFFFFFF
            k = (k * m) & 0xFFFFFFFF
            
            h = (h * m) & 0xFFFFFFFF
            h = (h ^ k) & 0xFFFFFFFF
            
            index += 4
            data_length -= 4
        
        # tail
        if data_length == 3:
            h = (h ^ (data[index + 2] << 16)) & 0xFFFFFFFF
            data_length -= 1
        
        if data_length == 2:
            h = (h ^ (data[index + 1] << 8)) & 0xFFFFFFFF
            data_length -= 1
        
        if data_length == 1:
            h = (h ^ data[index]) & 0xFFFFFFFF
            h = (h * m) & 0xFFFFFFFF

        h = (h ^ (h >> 13)) & 0xFFFFFFFF
        h = (h * m) & 0xFFFFFFFF
        h = (h ^(h >> 15)) & 0xFFFFFFFF

        return h

# ##########################################################
# YPFEntry describes a file Entry
# ##########################################################
class YPFEntry:
    class FileType(Enum):
        FILE = 0
        DIRECTORY = 1
        UNSUPPORTED = -1
        # Add other types if necessary

    def __init__(self : YPFHeader) -> None:
        self.name_checksum: int = 0
        self.file_name : PurePath = PurePath() # using PurePath instead of string
        self.type: YPFEntry.FileType = YPFEntry.FileType.FILE
        self.is_compressed: bool = False
        self.raw_file_size: int = 0
        self.compressed_file_size: int = 0
        self.offset: int = 0
        self.data_checksum: int = 0

# ##########################################################
# YPFHeader describes a YPF file header
# ##########################################################
class YPFHeader:
    SIGNATURE = b'YPF\0'

    def __init__(self : YPFHeader, stream : io.BufferedReader) -> None:
        self.archived_files : list[YPFEntry] = []
        self.archived_files_header_size: int = 0
        self.name_checksum: YChecksum = None
        self.data_checksum: YChecksum = None
        self.file_name_encryption_key: int = 0
        self.length_swapping_table: bytes = b''

        self._read_from_stream(stream)

    @property
    def version(self : YPFHeader) -> int:
        return self._version

    @version.setter
    def version(self : YPFHeader, value : int):
        if value < 234 or value > 500:
            raise Exception(f"[YPF] Version {value} not supported")
        self._version = value
        self._set_length_swapping_table()
        self._set_checksum()
        self._assume_file_name_encryption_key()

    def one_complement(self : YPFHeader, value : int) -> int:
        # one's complement of a byte.
        return (~value) & 0xFF

    def read_uint(self : YPFHeader, stream : io.BufferedReader) -> int:
        # read 32 bits unsigned integer
        return struct.unpack('<I', stream.read(4))[0]

    def read_int(self : YPFHeader, stream : io.BufferedReader) -> int:
        # read 32 bits signed integer
        return struct.unpack('<i', stream.read(4))[0]

    def _set_length_swapping_table(self : YPFHeader) -> None:
        if self.version >= 500:
            table = [
                0x00, 0x01, 0x02, 0x0A, 0x04, 0x05, 0x35, 0x07, 0x08, 0x0B, 0x03, 0x09, 0x10, 0x13, 0x0E, 0x0F, 0x0C, 0x18, 0x12, 0x0D, 0x2E, 0x1B, 0x16, 0x17, 0x11, 0x19, 0x1A, 0x15, 0x1E, 0x1D, 0x1C, 0x1F, 0x23, 0x21, 0x22, 0x20, 0x24, 0x25, 0x29, 0x27, 0x28, 0x26, 0x2A, 0x2B, 0x2F, 0x2D, 0x14, 0x2C, 0x30, 0x31, 0x32, 0x33, 0x34, 0x06, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x48, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x5B, 0x5C, 0x5D, 0x5E, 0x5F, 0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F, 0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x8B, 0x8C, 0x8D, 0x8E, 0x8F, 0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF, 0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xCB, 0xCC, 0xCD, 0xCE, 0xCF, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF, 0xE0, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xEB, 0xEC, 0xED, 0xEE, 0xEF, 0xF0, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF
            ]
        else:
            table = [
                0x00, 0x01, 0x02, 0x48, 0x04, 0x05, 0x35, 0x07, 0x08, 0x0B, 0x0A, 0x09, 0x10, 0x13, 0x0E, 0x0F, 0x0C, 0x19, 0x12, 0x0D, 0x14, 0x1B, 0x16, 0x17, 0x18, 0x11, 0x1A, 0x15, 0x1E, 0x1D, 0x1C, 0x1F, 0x23, 0x21, 0x22, 0x20, 0x24, 0x25, 0x29, 0x27, 0x28, 0x26, 0x2A, 0x2B, 0x2F, 0x2D, 0x32, 0x2C, 0x30, 0x31, 0x2E, 0x33, 0x34, 0x06, 0x36, 0x37, 0x38, 0x39, 0x3A, 0x3B, 0x3C, 0x3D, 0x3E, 0x3F, 0x40, 0x41, 0x42, 0x43, 0x44, 0x45, 0x46, 0x47, 0x03, 0x49, 0x4A, 0x4B, 0x4C, 0x4D, 0x4E, 0x4F, 0x50, 0x51, 0x52, 0x53, 0x54, 0x55, 0x56, 0x57, 0x58, 0x59, 0x5A, 0x5B, 0x5C, 0x5D, 0x5E, 0x5F, 0x60, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6A, 0x6B, 0x6C, 0x6D, 0x6E, 0x6F, 0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77, 0x78, 0x79, 0x7A, 0x7B, 0x7C, 0x7D, 0x7E, 0x7F, 0x80, 0x81, 0x82, 0x83, 0x84, 0x85, 0x86, 0x87, 0x88, 0x89, 0x8A, 0x8B, 0x8C, 0x8D, 0x8E, 0x8F, 0x90, 0x91, 0x92, 0x93, 0x94, 0x95, 0x96, 0x97, 0x98, 0x99, 0x9A, 0x9B, 0x9C, 0x9D, 0x9E, 0x9F, 0xA0, 0xA1, 0xA2, 0xA3, 0xA4, 0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF, 0xB0, 0xB1, 0xB2, 0xB3, 0xB4, 0xB5, 0xB6, 0xB7, 0xB8, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF, 0xC0, 0xC1, 0xC2, 0xC3, 0xC4, 0xC5, 0xC6, 0xC7, 0xC8, 0xC9, 0xCA, 0xCB, 0xCC, 0xCD, 0xCE, 0xCF, 0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF, 0xE0, 0xE1, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6, 0xE7, 0xE8, 0xE9, 0xEA, 0xEB, 0xEC, 0xED, 0xEE, 0xEF, 0xF0, 0xF1, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF
            ]
        self.length_swapping_table = bytes(table)

    def _set_checksum(self : YPFHeader) -> None:
        if self.version < 479:
            self.data_checksum = YAdler32()
            self.name_checksum = YCrc32()
        else:
            self.data_checksum = YMurmurHash2()
            self.name_checksum = YMurmurHash2()

    def _assume_file_name_encryption_key(self : YPFHeader) -> None:
        if self.version == 290:
            self.file_name_encryption_key = 0x40
        elif self.version >= 500:
            self.file_name_encryption_key = 0x36
        else:
            self.file_name_encryption_key = 0x00

    def _read_from_stream(self : YPFHeader, stream : io.BufferedReader) -> None:
        sig = stream.read(4)
        if sig != self.SIGNATURE:
            raise Exception("[YPF] Invalid Archive Signature")
        self.version = struct.unpack('<I', stream.read(4))[0]
        files_count = struct.unpack('<I', stream.read(4))[0]
        self.archived_files_header_size = struct.unpack('<I', stream.read(4))[0]
        # skip reserved 16 bytes
        stream.seek(16, io.SEEK_CUR)

        if files_count <= 0:
            raise Exception("[YPF] Invalid Files Count")
        if self.archived_files_header_size <= 0:
            raise Exception("[YPF] Invalid Archived Files Header Size")

        for _ in range(files_count):
            entry = self._read_next_entry(stream)
            self.archived_files.append(entry)

    def _read_next_entry(self : YPFHeader, stream: io.BufferedReader) -> YPFEntry:
        entry = YPFEntry()
        # Name checksum
        entry.name_checksum = self.read_uint(stream)
        # Encoded filename length
        encoded_len = self.one_complement(stream.read(1)[0])
        decoded_len = self.length_swapping_table[encoded_len]
        # Read encoded filename
        encoded_name = bytearray(stream.read(decoded_len))
        for i in range(decoded_len):
            encoded_name[i] = self.one_complement(encoded_name[i]) ^ self.file_name_encryption_key
        entry.file_name = PurePath(encoded_name.decode('shift_jis'))
        # File type
        ft = stream.read(1)[0]
        try:
            entry.type = YPFEntry.FileType(ft)
        except Exception:
            entry.type = YPFEntry.FileType.UNSUPPORTED
        # Compressed flag
        entry.is_compressed = (stream.read(1)[0] == 1)
        # Sizes
        entry.raw_file_size = self.read_int(stream)
        entry.compressed_file_size = self.read_int(stream)
        # Offset
        if self.version < 479:
            entry.offset = self.read_int(stream)
        else:
            entry.offset = struct.unpack('<q', stream.read(8))[0]
        # Data checksum
        entry.data_checksum = self.read_uint(stream)

        # Validate name integrity
        calc = self.name_checksum.compute_hash(bytes(encoded_name))
        if calc != entry.name_checksum:
            raise Exception("[YPF] Invalid Name Checksum / Corrupted Name")

        return entry

    def validate_data_integrity(self : YPFHeader, stream: io.BufferedReader, position: int, length: int, checksum: int) -> None:
        stream.seek(position)
        calc = self.data_checksum.compute_stream(stream, length)
        if calc != checksum:
            raise Exception("[YPF] Invalid Data Checksum / Corrupted Data")

    def find_duplicate_entry(self : YPFHeader, file_checksum: int, file_size: int) -> YPFEntry|None:
        for e in self.archived_files:
            if e.data_checksum == file_checksum and e.raw_file_size == file_size:
                return e
        return None

# ##########################################################
# The RPGMTL plugin
# Extract and look for ybn files
# ##########################################################
class YPF(Plugin):
    SIGNATURE = b'YPF\0'

    def __init__(self : YPF):
        super().__init__()
        self.name : str = "YPF"
        self.description : str = " v1.3\nExtract content from YPF files"
        self.related_tool_plugins : list[str] = [self.name]

    def extract(
        self : YPF,
        update_file_dict : dict[str, Any],
        full_path : PurePath,
        target_dir : PurePath,
        backup_path : PurePath
    ) -> bool:
        if full_path.suffix.lower() != ".ypf":
            return False
        try:
            ybn_keys : dict[str, int] = {}
            ybn_msgs : dict[int, int] = {}
            ybn_calls : dict[int, int] = {}
            with open(full_path, mode="rb") as stream:
                # Extract the header
                ypfh = YPFHeader(stream)
                # Go through the files
                for entry in ypfh.archived_files:
                    file_path : PurePath = target_dir / entry.file_name
                    if file_path.suffix.lower() not in (".ybn",):
                        continue
                    # Validate the file
                    ypfh.validate_data_integrity(stream, entry.offset, entry.compressed_file_size, entry.data_checksum)
                    # Read it
                    stream.seek(entry.offset)
                    data = stream.read(entry.compressed_file_size)
                    # Decompress
                    if entry.is_compressed:
                        data = zlib.decompress(data)
                        # Verify size
                        if len(data) != entry.raw_file_size:
                            raise Exception("[YPF] Invalid decompressed file size")
                    # create directory if not found
                    if not os.path.isdir(file_path.parent):
                        try:
                            # create dir if needed
                            os.makedirs(file_path.parent.as_posix(), exist_ok=True)
                        except Exception as e:
                            self.owner.log.error("[YPF] Couldn't create the following folder:" + file_path.parent.as_posix() + "\n" + self.trbk(e))
                    # write file
                    with open(file_path, mode="wb") as out:
                        out.write(data)
                    for p in self.owner.plugins.values():
                        if p.match(file_path.name, False):
                            # add to update_file_dict
                            update_file_dict[(file_path.relative_to(backup_path)).as_posix()] = {
                                "file_type":FileType.NORMAL,
                                "ignored":IntBool.FALSE,
                                "strings":0,
                                "translated":0,
                                "disabled_strings":0
                            }
                            # retrieve data to help with parsing later
                            if p.name == "YBN":
                                key, msg_op, call_op = p.get_codes(data, file_path)
                                if key is not None:
                                    ybn_keys[key] = ybn_keys.get(key, 0) + 1
                                    if msg_op != 0:
                                        ybn_msgs[msg_op] = ybn_msgs.get(msg_op, 0) + 1
                                    if call_op != 0:
                                        ybn_calls[call_op] = ybn_calls.get(call_op, 0) + 1
                # we take note of most commonly used key, msg_opcode and call_opcode in a separate, commong json file
                if "YBN" in self.owner.plugins:
                    with open(target_dir / "ypf.json", mode="w", encoding="utf-8") as f:
                        d = {
                            "key":None,
                            "msg":None,
                            "op":None
                        }
                        if len(ybn_keys) > 0:
                            d["key"] = max(ybn_keys, key=ybn_keys.get)
                        if len(ybn_msgs) > 0:
                            d["msg"] = max(ybn_msgs, key=ybn_msgs.get)
                        if len(ybn_calls) > 0:
                            d["op"] = max(ybn_calls, key=ybn_calls.get)
                        json.dump(d, f)
                return True
        except Exception as e:
            self.owner.log.error("[YPF] Failed to extract content from:" + full_path.as_posix() + "\n" + self.owner.trbk(e))
            return False

if __name__ == "__main__":
    YPF().extract("ysbin.ypf")