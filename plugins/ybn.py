from __future__ import annotations
from . import Plugin, WalkHelper
import struct
from collections import Counter
from io import BytesIO
import codecs
from pathlib import Path
import json

# Ported and adapted from https://github.com/regomne/chinesize/blob/master/yuris/extYbn/extYbn.go

# ##########################################################
# YBN Data structure
# ##########################################################
class YbnHeader:
    def __init__(
        self : YbnHeader, magic: bytes = b'YSTB', version: int = 0,
        inst_cnt: int = 0, code_size: int = 0,
        arg_size: int = 0, resource_size: int = 0,
        off_size: int = 0, resv: int = 0
    ) -> None:
        self.magic: bytes = magic         # [4]byte
        self.version: int = version       # uint32
        self.inst_cnt: int = inst_cnt     # uint32
        self.code_size: int = code_size   # uint32
        self.arg_size: int = arg_size     # uint32
        self.resource_size: int = resource_size # uint32
        self.off_size: int = off_size     # uint32
        self.resv: int = resv             # uint32

    @staticmethod
    def format_string() -> str:
        return "<4sIiiiiii" # Little-endian: magic, version, inst_cnt, code_size, arg_size, resource_size, off_size, resv

    @staticmethod
    def size() -> int:
        return struct.calcsize(YbnHeader.format_string())

    def pack(self) -> bytes:
        return struct.pack(YbnHeader.format_string(), self.magic, self.version, self.inst_cnt,
                           self.code_size, self.arg_size, self.resource_size, self.off_size, self.resv)

    @classmethod
    def unpack(cls, data: bytes) -> YbnHeader:
        magic, version, inst_cnt, code_size, arg_size, resource_size, off_size, resv = \
            struct.unpack(cls.format_string(), data)
        return cls(magic, version, inst_cnt, code_size, arg_size, resource_size, off_size, resv)

class YInst:
    def __init__(self : YInst, op: int = 0, arg_cnt: int = 0, unk: int = 0) -> None:
        self.op: int = op         # uint8
        self.arg_cnt: int = arg_cnt # uint8
        self.unk: int = unk       # uint16

    @staticmethod
    def format_string() -> str:
        return "<BBH" # Little-endian: op, arg_cnt, unk

    @staticmethod
    def size() -> int:
        return struct.calcsize(YInst.format_string())

    def pack(self) -> bytes:
        return struct.pack(YInst.format_string(), self.op, self.arg_cnt, self.unk)

    @classmethod
    def unpack(cls, data: bytes) -> YInst:
        op, arg_cnt, unk = struct.unpack(cls.format_string(), data)
        return cls(op, arg_cnt, unk)

class YArg:
    def __init__(self : YArg, value: int = 0, type: int = 0, res_size: int = 0, res_offset: int = 0) -> None:
        self.value: int = value         # uint16
        self.type: int = type           # uint16
        self.res_size: int = res_size   # uint32
        self.res_offset: int = res_offset # uint32

    @staticmethod
    def format_string() -> str:
        return "<HHII" # Little-endian: value, type, res_size, res_offset

    @staticmethod
    def size() -> int:
        return struct.calcsize(YArg.format_string())

    def pack(self : YArg) -> bytes:
        return struct.pack(YArg.format_string(), self.value, self.type, self.res_size, self.res_offset)

    @classmethod
    def unpack(cls, data: bytes) -> YArg:
        value, type, res_size, res_offset = struct.unpack(cls.format_string(), data)
        return cls(value, type, res_size, res_offset)

class YResInfo:
    def __init__(self : YResInfo, type: int = 0, length: int = 0) -> None:
        self.type: int = type     # uint8
        self.length: int = length # uint16

    @staticmethod
    def format_string() -> str:
        return "<BH" # Little-endian: type, length

    @staticmethod
    def size() -> int:
        return struct.calcsize(YResInfo.format_string())

    def pack(self : YResInfo) -> bytes:
        return struct.pack(YResInfo.format_string(), self.type, self.length)

    @classmethod
    def unpack(cls, data: bytes) -> YResInfo:
        type, length = struct.unpack(cls.format_string(), data)
        return cls(type, length)

class YKeyOps:
    def __init__(self : YKeyOps, msg_op: int = 0, call_op: int = 0, other_op: list[int]|None = None) -> None:
        self.msg_op: int = msg_op
        self.call_op: int = call_op
        self.other_op: list[int] = other_op if other_op is not None else []

class YResEntry:
    def __init__(
        self : YResEntry, type: int = 0,
        res : bytes|None = None,
        res_raw : bytes|None = None,
        res_str : str = ""
    ) -> None:
        self.type : int = type
        self.res : bytes|None = res
        self.res_raw : bytes|None = res_raw
        self.res_str : str = res_str

class YArgInfo:
    def __init__(
        self : YArgInfo, value : int = 0, type : int = 0,
        res : YResEntry|None = None,
        res_info : int = 0, res_offset : int = 0
    ) -> None:
        self.value: int = value
        self.type: int = type
        self.res: YResEntry = res if res is not None else YResEntry()
        # These are from YArg if not a type 3 resource or if YArg.Type == 0
        self.res_info_val: int = res_info # Corresponds to YArg.ResSize when YArg.Type == 0
        self.res_offset_val: int = res_offset # Corresponds to YArg.ResOffset when YArg.Type == 0

class YInstInfo:
    def __init__(
        self : YInstInfo, op: int = 0, unk: int = 0,
        args : list[YArgInfo]|None = None
    ):
        self.op: int = op
        self.unk: int = unk
        self.arg_cnt: int = 0 # Will be populated from YInst's ArgCnt
        self.args: list[YArgInfo] = args if args is not None else []

class YbnInfo:
    def __init__(
        self : YbnInfo,
        header : YbnHeader|None = None,
        insts : list[YInstInfo]|None = None,
        offs : list[int]|None = None
    ) -> None:
        self.header: YbnHeader = header if header is not None else YbnHeader()
        self.insts: list[YInstInfo] = insts if insts is not None else []
        self.offs: list[int] = offs if offs is not None else []

# ##########################################################
# The RPGMTL plugin
# Extract and look for ybn files
# ##########################################################
class YBN(Plugin):
    TXT_FUNCTION : set[str] = (
        '"es.sel.set"',
        '"es.char.name.mark.set"',
        '"es.char.name"',
        '"es.input.str.set"',
        '"es.tips.def.set"',
        '"es.tips.tx.def.set"',
    )
    HEADER_SIZE = YbnHeader.size()
    
    def __init__(self : YBN) -> None:
        super().__init__()
        self.name : str = "YBN"
        self.description : str = " v1.0\nHandle YBN files."
        self.last_ypf_path : Path|None = None
        self.last_ypf_data : dict[str, str|int] = {}

    def match(self : YBN, file_path : str, is_for_action : bool) -> bool:
        return file_path.endswith("ybn")

    def reset(self : YBN, project_path : Path = Path(), filename : str = "") -> None:
        # Kinda hacky way to share the decrypt key and opcodes between files
        # Reset is called before each read or write
        # So we try to load the corresponding ypf.json (generated by the YPF plugin), which contains the key and opcodes for that folder
        p : Path = (project_path / filename).parent.parent
        if p != self.last_ypf_path:
            self.load_last_ypf(p)

    def load_last_ypf(self : YBN, folder : Path) -> None:
        try:
            with open((folder / "ypf.json").as_posix(), mode="r", encoding="utf-8") as f:
                self.last_ypf_data = json.load(f)
            # Convert hexadecimal to bytes
            if isinstance(self.last_ypf_data.get("key", None), str):
                self.last_ypf_data["key"] = bytes.fromhex(self.last_ypf_data["key"])
        except Exception as e:
            self.owner.log.warning("[YPF] No ypf.json found in " + folder.as_posix() + "\n" + self.owner.trbk(e))
            self.last_ypf_data = {}

    def read(self : YBN, file_path : str, content : bytes) -> list[list[str]]:
        path : Path = Path(file_path)
        # we only care about yst00000.ybn files
        if path.name.startswith("yst") and path.name[3].isdigit() and path.suffix == ".ybn":
            script, ops, _ = self.parse_ybn(
                content,
                key=self.last_ypf_data.get("key", None),
                msg_op=self.last_ypf_data.get("msg", 0),
                call_op=self.last_ypf_data.get("call", 0)
            )
            return self.extract_strings(script, ops)
        else:
            return []

    def write(self : YBN, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        path : Path = Path(file_path)
        if path.name.startswith("yst") and path.name[3].isdigit() and path.suffix == ".ybn":
            helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
            content = self.patch_ybn(
                content,
                helper,
                key=self.last_ypf_data.get("key", None),
                msg_op=self.last_ypf_data.get("msg", 0),
                call_op=self.last_ypf_data.get("call", 0)
            )
            return content, helper.modified
        else:
            return content, False

    # Function for the YPF plugin
    # It parse the file preemptively and return what it thinks is the key and the opcodes
    def get_codes(self : YBN, content : bytes, file_path) -> tuple[str|None, int|None, int|None]:
        try:
            _, ops, key = self.parse_ybn(content)
            return key, ops.msg_op, ops.call_op
        except:
            return None, None, None

    # Main function to parse the YBN
    def parse_ybn(
        self : YBN, content: bytes,
        *,
        key : bytes|None = None,
        msg_op : int = 0,
        call_op : int = 0
    ) -> tuple[YbnInfo, YKeyOps, str]:
        script = YbnInfo()

        if len(content) < self.HEADER_SIZE:
            raise Exception("File too small to contain a YBN header.")

        script.header = YbnHeader.unpack(content[:self.HEADER_SIZE])
        header = script.header

        if header.magic != b"YSTB":
            raise Exception("Not a YBN file (magic mismatch).")

        yinst_size = YInst.size()
        if header.code_size != header.inst_cnt * yinst_size:
            raise Exception("YBN File Code Size mismatch.")

        expected_file_size = self.HEADER_SIZE + header.code_size + header.arg_size + header.resource_size + header.off_size

        if expected_file_size != len(content):
            if expected_file_size > len(content):
                raise Exception(f"File size error. Expected at least {expected_file_size}, got {len(content)}")
            self.owner.log.warning(f"[YBN] Actual file size ({len(content)}) is greater than expected ({expected_file_size}). May contain extra data.")
        if header.resv != 0:
            self.owner.log.warning("[YBN] Reserved field is not 0, maybe can't extract all the info.")

        # convert content to byte array
        working = bytearray(content)
        # attempt to guess key if not provided (occurs via get_codes())
        if key is None:
            key = self.guess_key(working[YbnHeader.size():])
        if key != b"\x00\x00\x00\x00":
            self.decrypt_ybn(working, key, header)

        decrypted = BytesIO(working)
        decrypted.seek(self.HEADER_SIZE)
        
        # Read instructions
        raw_insts_data = decrypted.read(header.code_size)
        if len(raw_insts_data) != header.code_size:
            raise Exception("Failed to find YBN file complete code section.")

        script.insts = []
        for i in range(int(header.inst_cnt)):
            offset = i * yinst_size
            if offset + yinst_size > len(raw_insts_data):
                raise Exception("Not enough data for instruction {i} in code section.")
            y_inst = YInst.unpack(raw_insts_data[offset : offset + yinst_size])
            inst_info = YInstInfo(op=y_inst.op, unk=y_inst.unk)
            inst_info.arg_cnt = y_inst.arg_cnt # Store arg_cnt from YInst
            script.insts.append(inst_info)

        # Read arguments
        raw_args_data = decrypted.read(header.arg_size)
        if len(raw_args_data) != header.arg_size:
            raise Exception(f"Couldn't read complete arg section. Expected {header.arg_size}, got {len(raw_args_data)}.")

        yarg_size = YArg.size()
        num_yargs = 0
        if yarg_size > 0 :
            num_yargs = header.arg_size // yarg_size
            if header.arg_size % yarg_size != 0:
                raise Exception(f"ArgSize ({header.arg_size}) not a multiple of YArg size ({yarg_size}).")

        rargs: list[YArg] = []
        for i in range(num_yargs):
            offset = i * yarg_size
            if offset + yarg_size > len(raw_args_data):
                raise Exception(f"Not enough data for YArg {i} in argument section.")
            rargs.append(YArg.unpack(raw_args_data[offset : offset + yarg_size]))

        res_start_abs_offset = self.HEADER_SIZE + header.code_size + header.arg_size
        rarg_idx = 0

        for i in range(int(header.inst_cnt)):
            inst_info = script.insts[i]
            inst_info.args = []

            for _ in range(inst_info.arg_cnt): # Use stored arg_cnt
                if rarg_idx >= len(rargs):
                    raise Exception(f"Argument count mismatch: instruction {i} expected more arguments than available in rargs list (rarg_idx: {rarg_idx}, len(rargs): {len(rargs)})")

                rarg = rargs[rarg_idx]
                rarg_idx += 1

                arg_info_entry = YArgInfo(type=rarg.type, value=rarg.value)

                if rarg.type == 0 and inst_info.arg_cnt != 1:
                    arg_info_entry.res_info_val = rarg.res_size
                    arg_info_entry.res_offset_val = rarg.res_offset
                else:
                    # Resource is present, read it from the main resource section
                    # Check if resource offset and size are valid
                    if rarg.res_offset >= header.resource_size:
                        raise Exception(f"Resource offset {rarg.res_offset} is out of bounds for resource section size {header.resource_size} (inst {i}, arg type {rarg.type})")

                    # Temporarily seek in the main decrypted stream to read the resource
                    ori_pos = decrypted.tell()
                    decrypted.seek(res_start_abs_offset + rarg.res_offset)

                    res_entry = arg_info_entry.res

                    if rarg.type == 3:
                        y_res_info_size = YResInfo.size()
                        if rarg.res_size < y_res_info_size:
                             # This used to be an error. Go code implies res_size is for the YResInfo + data.
                             # Let's check if rarg.res_offset + y_res_info_size exceeds resource section.
                             if res_start_abs_offset + rarg.res_offset + y_res_info_size > res_start_abs_offset + header.resource_size:
                                raise Exception(f"Resource (type 3) at offset {rarg.res_offset} with YResInfo would read past resource section end.")

                        res_info_data = decrypted.read(y_res_info_size)
                        if len(res_info_data) < y_res_info_size:
                            raise Exception(f"Could not read YResInfo at offset {rarg.res_offset} in resource section (inst {i})")

                        y_res_info = YResInfo.unpack(res_info_data)
                        res_entry.type = y_res_info.type

                        # Check if y_res_info.length would read past end of specified rarg.res_size
                        # or past end of the entire resource section
                        if y_res_info_size + y_res_info.length > rarg.res_size:
                            raise Exception(f"YResInfo length ({y_res_info.length}) + YResInfo size ({y_res_info_size}) > YArg.ResSize ({rarg.res_size}) for inst {i}, rarg offset {rarg.res_offset}. Clamping read.")
                            bytes_to_read = rarg.res_size - y_res_info_size
                        else:
                            bytes_to_read = y_res_info.length

                        if res_start_abs_offset + rarg.res_offset + y_res_info_size + bytes_to_read > res_start_abs_offset + header.resource_size:
                            raise Exception(f"Resource data read (len {bytes_to_read}) for type 3 at offset {rarg.res_offset} would exceed resource section end.")

                        res_entry.res = decrypted.read(bytes_to_read)
                        if len(res_entry.res) != bytes_to_read:
                            raise Exception(f"Could not read full resource data for type 3. Expected {bytes_to_read}, got {len(res_entry.res)} (inst {i}, rarg offset {rarg.res_offset})")
                    else: # Type is not 3, read rarg.res_size bytes as raw resource
                        if res_start_abs_offset + rarg.res_offset + rarg.res_size > res_start_abs_offset + header.resource_size:
                            raise Exception(f"Raw resource read (size {rarg.res_size}) at offset {rarg.res_offset} would exceed resource section end.")

                        res_entry.res_raw = decrypted.read(rarg.res_size)
                        if len(res_entry.res_raw) != rarg.res_size:
                            raise Exception(f"Could not read full raw resource data. Expected {rarg.res_size}, got {len(res_entry.res_raw)} (inst {i}, rarg offset {rarg.res_offset})")

                    decrypted.seek(ori_pos) # Restore position

                inst_info.args.append(arg_info_entry)

        off_tbl_offset_in_file = self.HEADER_SIZE + header.code_size + header.arg_size + header.resource_size
        decrypted.seek(off_tbl_offset_in_file)

        script.offs = []
        if header.off_size > 0 :
            expected_off_size = header.inst_cnt * 4 # Each offset is uint32
            if header.off_size != expected_off_size:
                self.owner.log.warning(f"[YBN] OffSize in header ({header.off_size}) does not match InstCnt*4 ({expected_off_size}). Will read {header.inst_cnt} offsets.")

            num_offsets_to_read = int(header.inst_cnt)

            # Check if reading this many offsets would exceed the file's offset section or total size
            bytes_for_offsets_to_read = num_offsets_to_read * 4
            if bytes_for_offsets_to_read > header.off_size :
                self.owner.log.warning(f"[YBN] Calculated bytes for offsets ({bytes_for_offsets_to_read}) > header.off_size ({header.off_size}). Clamping to header.off_size.")
                bytes_for_offsets_to_read = header.off_size
                num_offsets_to_read = header.off_size // 4

            if off_tbl_offset_in_file + bytes_for_offsets_to_read > len(working):
                raise Exception(f"Offset table read ({bytes_for_offsets_to_read} bytes) would exceed total file data.")

            for _ in range(num_offsets_to_read):
                off_data = decrypted.read(4)
                if len(off_data) < 4:
                    raise Exception("Could not read full offset entry from offset table (EOF or short read).")
                script.offs.append(struct.unpack("<I", off_data)[0])

        ops = YKeyOps(msg_op, call_op)
        self.guess_ybn_op(script, ops) # guess_ybn_op updates ops in-place
        return script, ops, key.hex()

    # Function to guess the decryption key from the byte content
    def guess_key(self : YBN, encrypted : bytearray) -> bytes:
        # The idea was inspired from this post https://forums.fuwanovel.moe/topic/24704-a-complete-guide-to-unpack-and-repack-yu-ris-engine-files/
        # The key is 4 bytes long
        # The goal is to "guess" for sections of 0x00000000 bytes
        # It's not 100% accurate, but as it will repeated on all files via get_codes calls in the YPF plugin, it will have a list of all possible keys and one in particular should have way more occurences
        streams = [encrypted[i::4] for i in range(4)]
        # count byte frequencies in each stream
        key = bytearray(4)
        for i, s in enumerate(streams):
            freq = Counter(s)
            # assume plaintext has a lot of 0x00: the most common ciphertext byte = key[i]
            key[i], _ = freq.most_common(1)[0]
        return key

    def decrypt_block(self : YBN, encrypted: bytearray, start_offset: int, end_offset: int, key: bytes):
        if len(key) != 4:
            raise Exception("Key length error")
        # Ensure end_offset does not exceed length
        actual_end_offset = min(end_offset, len(encrypted))
        for i in range(start_offset, actual_end_offset):
            # Key index must be relative to the start of the current block being processed
            encrypted[i] ^= key[(i - start_offset) & 3]

    def decrypt_ybn(self : YBN, encrypted : bytearray, key: bytes, header: YbnHeader) -> bytearray:
        current_offset = YbnHeader.size()
        section_start = current_offset
        section_end = current_offset + header.code_size
        if section_end > len(encrypted):
            self.owner.log.warning(f"[YBN] code section end ({section_end}) exceeds encrypted length ({len(encrypted)})"); section_end = len(encrypted)
        self.decrypt_block(encrypted, section_start, section_end, key)
        current_offset = section_end

        section_start = current_offset
        section_end = current_offset + header.arg_size
        if section_end > len(encrypted):
            self.owner.log.warning(f"[YBN] arg section end ({section_end}) exceeds encrypted length ({len(encrypted)})"); section_end = len(encrypted)
        self.decrypt_block(encrypted, section_start, section_end, key)
        current_offset = section_end

        section_start = current_offset
        section_end = current_offset + header.resource_size
        if section_end > len(encrypted):
            self.owner.log.warning(f"[YBN] resource section end ({section_end}) exceeds encrypted length ({len(encrypted)})"); section_end = len(encrypted)
        self.decrypt_block(encrypted, section_start, section_end, key)
        current_offset = section_end

        section_start = current_offset
        section_end = current_offset + header.off_size
        if section_end > len(encrypted):
            self.owner.log.warning(f"[YBN] offset section end ({section_end}) exceeds encrypted length ({len(encrypted)})"); section_end = len(encrypted)
        self.decrypt_block(encrypted, section_start, section_end, key)
        return encrypted

    def guess_ybn_op(self : YBN, script: YbnInfo, ops : YKeyOps) -> bool:
        msg_stat = [0] * 256
        call_stat = [0] * 256

        # Determine if we need to guess msg_op or call_op
        should_guess_msg_op = (ops.msg_op == 0)
        should_guess_call_op = (ops.call_op == 0)

        # If both ops are already provided by user and we are not forced to output, no guessing needed.
        if not should_guess_msg_op and not should_guess_call_op:
            return True

        for inst in script.insts:
            # If ops that needed guessing have been found, or if we only needed to output pre-set ops, stop.
            if not should_guess_msg_op and not should_guess_call_op:
                break

            if should_guess_msg_op and len(inst.args) == 1 and (self.is_jap_or_chn_msg(inst.args[0]) or self.is_english_msg(inst.args[0])):
                msg_stat[inst.op] += 1
                if msg_stat[inst.op] > 10:
                    ops.msg_op = inst.op
                    should_guess_msg_op = False # Mark as found, stop guessing this one

            if should_guess_call_op and len(inst.args) >= 1 and inst.args[0].res and \
               inst.args[0].value == 0 and inst.args[0].type == 3 and inst.args[0].res.res is not None:

                res_bytes = inst.args[0].res.res
                s = ""
                try:
                    s = res_bytes.decode('ascii')
                except UnicodeDecodeError:
                    pass

                if inst.args[0].res.type == 0x4d and len(s) > 4 and \
                   s.startswith('"e') and s.endswith('"'):
                    call_stat[inst.op] += 1
                    if call_stat[inst.op] > 5:
                        ops.call_op = inst.op
                        should_guess_call_op = False # Mark as found, stop guessing this one
        return ops.msg_op != 0 and ops.call_op != 0

    # Extract strings return string groups in the RPGMTL format
    def extract_strings(self : YBN, script : YbnInfo, ops : YKeyOps) -> list[list[str]]:
        entries : list[list[str]] = []
        for inst_idx, inst in enumerate(script.insts):
            if inst.op == ops.msg_op:
                if len(inst.args) != 1:
                    # Log warning instead of hard error to match Go behavior of continuing
                    self.owner.log.warning(f"Message op 0x{ops.msg_op:x} (inst {inst_idx}) has {len(inst.args)} args, expected 1. Skipping.")
                    continue

                arg = inst.args[0]
                raw_str_bytes: bytes|None = None
                # Go logic: Type 3 uses res.Res, otherwise res.ResRaw
                if arg.type == 3 and arg.res and arg.res.res is not None:
                    raw_str_bytes = arg.res.res
                elif arg.res and arg.res.res_raw is not None:
                    raw_str_bytes = arg.res.res_raw

                if raw_str_bytes is not None:
                    if len(entries) == 0 or entries[-1][0] != "Message":
                        entries.append(["Message"])
                    entries[-1].append(self.decode_string(raw_str_bytes))
                else:
                    self.owner.log.warning(f"Warning: Msg op 0x{ops.msg_op:x} (inst {inst_idx}), arg type {arg.type} had no decodable bytes.")

            elif inst.op == ops.call_op:
                if not inst.args:
                    self.owner.log.warning(f"Warning: Call op 0x{ops.call_op:x} (inst {inst_idx}) has no arguments. Skipping.")
                    continue

                func_name_arg = inst.args[0]
                if func_name_arg.res and func_name_arg.res.res and self.is_function_to_extract(func_name_arg.res.res):
                    for arg_sub_idx, arg in enumerate(inst.args[1:]):
                        if arg.type == 3 and arg.res and arg.res.res is not None and arg.res.res != b'""' and arg.res.res != b"''":
                            if len(entries) == 0 or entries[-1][0] != "Function":
                                entries.append(["Function"])
                            entries[-1].append(self.decode_string(arg.res.res))

            elif ops.other_op and inst.op in ops.other_op:
                for arg_idx, arg in enumerate(inst.args):
                     if arg.type == 3 and arg.res and arg.res.res is not None and arg.res.res != b'""' and arg.res.res != b"''":
                            if len(entries) == 0 or entries[-1][0] != f"Other {inst.op}":
                                entries.append([f"Other {inst.op}"])
                            entries[-1].append(self.decode_string(arg.res.res))
        return entries

    # Adapted from https://github.com/regomne/chinesize/blob/master/yuris/extYbn/extYbn.go
    # Note: Might change it later if it's judged not good enough
    def is_long_english_sentence(self : YBN, s : bytes|None) -> bool:
        if s is None:
            return False
        space_count = 0
        if not s:
            return False # Empty bytes object
        for char_val in s:
            if char_val >= 0x80:
                return False
            elif char_val == ord(' '): space_count += 1
        return space_count > 5

    def is_english_msg(self : YBN, arg : YArgInfo) -> bool:
        if arg.value == 0 and arg.type == 3 and arg.res and arg.res.res is not None:
            return self.is_long_english_sentence(arg.res.res)
        return False

    def is_jap_or_chn_msg(self : YBN, arg : YArgInfo) -> bool:
        if arg.value == 0 and arg.type == 0 and arg.res and arg.res.res_raw is not None:
            if len(arg.res.res_raw) > 0 and arg.res.res_raw[0] > 0x80:
                return True
        return False

    # Note: Unused, for debug
    def decode_script_string(self : YBN, script : YbnInfo, ops : YKeyOps):
        for inst in script.insts:
            for arg in inst.args:
                if arg.res:
                    # Preference to res (Type 3 typically)
                    if arg.res.res is not None:
                        arg.res.res_str = self.decode_string(arg.res.res)
                    # Fallback to res_raw if res is None, especially for msg op
                    elif arg.res.res_raw is not None and (inst.op == ops.msg_op or arg.type != 3) :
                        arg.res.res_str = self.decode_string(arg.res.res_raw)

    def is_function_to_extract(self : YBN, name_bytes : bytes|None) -> bool:
        if name_bytes is None:
            return False
        try:
            name_str = name_bytes.decode('ascii').lower()
        except UnicodeDecodeError:
            return False
        return name_str in [n.lower() for n in self.TXT_FUNCTION]

    def decode_string(self : YBN, byte_str : bytes) -> str:
        codepage_name = "shift_jis" # default, might add an option later?
        if codepage_name == "unknown" or not codepage_name:
            codepage_name = "shift_jis" # Default fallback
            self.owner.log.warning(f"[YBN] Unknown or empty codepage, defaulting to {codepage_name}.")

        try:
            return codecs.decode(byte_str, codepage_name, errors='replace')
        except LookupError:
            self.owner.log.warning(f"[YBN] Codepage {codepage_name} not found. Trying utf-8.")
            return codecs.decode(byte_str, "utf-8", errors='replace')
        except Exception as e:
            self.owner.log.error(f"[YBN] Error decoding string with {codepage_name}: {e}. Falling back to latin-1.")
            return byte_str.decode('latin-1', errors='replace')

    def encode_string(self : YBN, text_str : str) -> bytes:
        codepage_name = "shift_jis" # default, might add an option later?
        if codepage_name == "unknown" or not codepage_name:
            codepage_name = "shift_jis" # Default fallback
            self.owner.log.warning(f"[YBN] Unknown or empty codepage for encoding, defaulting to {codepage_name}.")
        try:
            return codecs.encode(text_str, codepage_name, errors='replace')
        except LookupError:
            self.owner.log.warning(f"[YBN] Codepage {codepage_name} not found for encoding. Trying utf-8.")
            return codecs.encode(text_str, "utf-8", errors='replace')
        except Exception as e:
            self.owner.log.error(f"[YBN] encoding string with {codepage_name}: {e}. Falling back to latin-1.")
            return text_str.encode('latin-1', errors='replace')

    def patch_ybn(
        self : YBN, content: bytes,
        helper : WalkHelper,
        *,
        key : bytes,
        msg_op : int,
        call_op : int
    ) -> bytes:
        # First, we parse
        script, ops, _ = self.parse_ybn(
            content,
            key=self.last_ypf_data.get("key", None),
            msg_op=self.last_ypf_data.get("msg", 0),
            call_op=self.last_ypf_data.get("call", 0)
        )
        # then, we patch
        return self.pack_string_to_ybn(
            content,
            helper,
            script,
            ops,
            key
        )

    def pack_string_to_ybn(
        self : YBN,
        content : bytes,
        helper : WalkHelper,
        script : YbnInfo,
        ops : YKeyOps,
        key : bytes
    ) -> bytes:
        # preparation
        working = bytearray(content)
        if key != b"\x00\x00\x00\x00":
            self.decrypt_ybn(working, key, script.header)
        # arg data
        arg_section_start_offset = self.HEADER_SIZE + script.header.code_size
        arg_section_end_offset = arg_section_start_offset + script.header.arg_size
        if arg_section_end_offset > len(working):
            raise Exception("Argument section end offset exceeds decrypted content length.")
        arg_data = bytearray(working[arg_section_start_offset:arg_section_end_offset])
        
        # resource data
        res_section_start_offset = arg_section_end_offset
        res_section_end_offset = res_section_start_offset + script.header.resource_size
        if res_section_end_offset > len(working):
            raise Exception("Resource section end offset exceeds decrypted content length.")
        res_data = working[res_section_start_offset:res_section_end_offset]

        appended_new_data = bytearray()
        
        new_offset = script.header.resource_size
        arg_cursor = 0 # Tracks current YArg's start position in arg_data
        for inst_idx, inst in enumerate(script.insts):
            is_msg_op = inst.op == ops.msg_op
            is_call_op_for_extraction = False
            if inst.op == ops.call_op and inst.args and inst.args[0].res and inst.args[0].res.res is not None: # Ensure res and res.res exist
                 is_call_op_for_extraction = self.is_function_to_extract(inst.args[0].res.res)
            is_other_relevant_op = ops.other_op and inst.op in ops.other_op
            for arg_idx, arg in enumerate(inst.args):
                # Calculate offsets for YArg.ResSize and YArg.ResOffset within modified_arg_data_bytearray
                # YArg structure: Value(2), Type(2), ResSize(4), ResOffset(4)
                size_field_offset = arg_cursor + 4
                offset_field_offset = arg_cursor + 8

                should_process_this_arg = False
                original = None
                group = None
                if is_msg_op and arg_idx == 0:
                    should_process_this_arg = True
                    if arg.type == 3 and arg.res and arg.res.res is not None:
                        raw_str_bytes = arg.res.res
                    elif arg.res and arg.res.res_raw is not None:
                        raw_str_bytes = arg.res.res_raw
                    original = self.decode_string(raw_str_bytes)
                    group = "Message"
                elif is_call_op_for_extraction and arg_idx > 0: # Skip func name arg
                    if arg.type == 3 and arg.res and arg.res.res is not None and arg.res.res != b'""' and arg.res.res != b"''":
                        should_process_this_arg = True
                        original = self.decode_string(arg.res.res)
                        group = "Function"
                elif is_other_relevant_op:
                    if arg.type == 3 and arg.res and arg.res.res is not None and arg.res.res != b'""' and arg.res.res != b"''":
                        should_process_this_arg = True
                        original = self.decode_string(arg.res.res)
                        group = f"Other {inst.op}"

                if should_process_this_arg:
                    string = helper.apply_string(original, group)
                    if helper.str_modified:
                        new_res = self.pack_line(arg, string)

                        # Update ResSize and ResOffset in the mutable modified_arg_data_bytearray
                        struct.pack_into("<I", arg_data, size_field_offset, len(new_res))
                        struct.pack_into("<I", arg_data, offset_field_offset, new_offset)

                        appended_new_data.extend(new_res)
                        new_offset += len(new_res)

                arg_cursor += YArg.size() # Advance to the next YArg's position
        # Assemble the new YBN file
        final_ybn_buffer = BytesIO()

        # Modified Header
        output_header = YbnHeader.unpack(script.header.pack()) # Start with a copy
        output_header.resource_size += len(appended_new_data) # Update total resource size
        final_ybn_buffer.write(output_header.pack())

        # Original Code Section (from decrypted content)
        code_section_start = self.HEADER_SIZE
        code_section_end = code_section_start + script.header.code_size # Use original code size
        final_ybn_buffer.write(working[code_section_start:code_section_end])

        # Modified Argument Section
        final_ybn_buffer.write(arg_data)

        # Original Resource Section
        final_ybn_buffer.write(res_data)

        # New Appended Resource Data
        final_ybn_buffer.write(appended_new_data)

        # Original Offset Table (from decrypted content)
        # Offset table's position is after the *original* total resource size.
        ori_start_offset = self.HEADER_SIZE + script.header.code_size + script.header.arg_size + script.header.resource_size # Original sizes
        ori_end_offset = ori_start_offset + script.header.off_size

        if ori_end_offset > len(working):
            raise Exception("Original offset table end exceeds decrypted content length.")
        final_ybn_buffer.write(working[ori_start_offset:ori_end_offset])

        # Get the complete new YBN data as a mutable bytearray for potential encryption
        final_ybn_bytearray = bytearray(final_ybn_buffer.getvalue())

        # Encrypt sections if a key is provided (using the *new* header with updated resource_size)
        if key != b"\x00\x00\x00\x00":
            self.decrypt_ybn(final_ybn_bytearray, key, output_header) # decrypt_ybn is XOR, so it also encrypts

        return bytes(final_ybn_bytearray)

    def pack_line(self : YBN, arg_info : YArgInfo, line : str) -> bytes:
        encoded_str_bytes = self.encode_string(line)
        if arg_info.type == 3:
            # Preserve original resource type from arg_info.res.type
            res_info = YResInfo(type=arg_info.res.type, length=len(encoded_str_bytes))
            return res_info.pack() + encoded_str_bytes
        return encoded_str_bytes # For non-type 3, return raw encoded bytes