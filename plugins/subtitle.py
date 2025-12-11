from __future__ import annotations
from . import Plugin, WalkHelper
import re


class Subtitle(Plugin):
    LRC_TIMECODE = re.compile("^\\s*\\d+\\s*:\\s*\\d+\\s*.\\s*\\d+\\s*")
    
    def __init__(self : Subtitle) -> None:
        super().__init__()
        self.name : str = "Subtitle"
        self.description : str = " v1.0\nHandle various Subtitle file formats"
        self.related_tool_plugins : list[str] = [self.name]

    def match(self : Subtitle, file_path : str, is_for_action : bool) -> bool:
        return file_path.lower().endswith(
            (
                ".ass",
                ".ssa",
                ".srt",
                ".lrc"
            )
        )

    def read(self : Subtitle, file_path : str, content : bytes) -> list[list[str]]:
        decoded = self.decode(content)
        match file_path.lower().rsplit(".", 1)[-1]:
            case "srt":
                return self.read_srt(decoded)
            case "ssa"|"ass":
                return self.read_ssa(decoded)
            case "lrc":
                return self.read_lrc(decoded)
            case _:
                return []

    def write(self : Subtitle, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
        decoded = self.decode(content)
        match file_path.lower().rsplit(".", 1)[-1]:
            case "srt":
                return self.write_srt(decoded, helper)
            case "ssa"|"ass":
                return self.write_ssa(decoded, helper)
            case "lrc":
                return self.write_lrc(decoded, helper)
            case _:
                return content, False

    # SRT parser ########################################################

    def read_srt(self : Subtitle, content : str) -> list[list[str]]:
        state : int = 0
        entries : list[list[str]] = []
        string : list[str] = []
        group_name : str = ""
        for line in content.splitlines():
            match state:
                case 0: # sequence
                    try:
                        int(line)
                        state = 1
                    except:
                        pass
                case 1: # timestamp
                    if "-->" in line:
                        group_name = line
                        state = 2
                case 2: # text
                    if line == "":
                        state = 0
                        if len(string) > 0:
                            entries.append([
                                group_name,
                                "\n".join(string)
                            ])
                            string.clear()
                            group_name = ""
                    else:
                        string.append(line)
        return entries

    def write_srt(self : Subtitle, content : str, helper : WalkHelper) -> tuple[bytes, bool]:
        state : int = 0
        string_start : int = -1
        string : list[str] = []
        group_name : str = ""
        lines = content.splitlines()
        i : int = 0
        while i < len(lines):
            match state:
                case 0: # sequence
                    try:
                        int(lines[i])
                        state = 1
                    except:
                        pass
                case 1: # timestamp
                    if "-->" in lines[i]:
                        group_name = lines[i]
                        string_start = i + 1
                        state = 2
                case 2: # text
                    if lines[i] == "":
                        state = 0
                        if len(string) > 0:
                            res : str = helper.apply_string("\n".join(string), group_name)
                            if helper.str_modified:
                                lines = (
                                    lines[:string_start] +
                                    [res] +
                                    lines[i:]
                                )
                                i -= (i - string_start) - 1
                            string.clear()
                            group_name = ""
                    else:
                        string.append(lines[i])
            i += 1
        if len(lines) > 1 and lines[-1] != "":
            lines.append("") # failsafe
        return self.encode("\n".join(lines)), helper.modified

    # SSA parser ########################################################

    def _ssa_look_for(
        self : Subtitle,
        content : str,
        cursor : int,
        target : str
    ) -> int:
        cursor = content.find(target, cursor + 1)
        if cursor != -1:
            cursor += len(target)
        return cursor

    def _ssa_get_line(
        self : Subtitle,
        content : str,
        cursor : int
    ) -> int:
        while content[cursor] != "\n" or content[cursor - 1] == "\\":
            cursor = content.find("\n", cursor + 1)
            if cursor == -1:
                cursor = len(content)
                break
        return cursor

    def _ssa_parse_format(
        self : Subtitle,
        content : str,
        cursor : int
    ) -> tuple[int, list[str]|None]:
        cursor = self._ssa_look_for(content, cursor, "Format: ")
        if cursor == -1:
            return cursor, None
        start : int = cursor
        cursor = self._ssa_get_line(content, cursor)
        if cursor == -1:
            return cursor, None
        return cursor, [
            s.strip() for s in content[start:cursor].replace("\n", "").replace("\\", "").split(",")
        ]

    def _ssa_next_dialog(
        self : Subtitle,
        content : str,
        cursor : int
    ) -> [int, int]:
        cursor = self._ssa_look_for(content, cursor, "Dialogue: ")
        if cursor == -1:
            return -1, cursor
        start : int = cursor
        cursor = self._ssa_get_line(content, cursor)
        return start, cursor

    def _ssa_next_dialog_part(
        self : Subtitle,
        content : str,
        cursor : int,
        limit : int
    ) -> int:
        next : int = content.find(",", cursor + 1)
        if next == -1 or next >= limit:
            next = content.find("\n", cursor + 1)
            if next == -1:
                next = limit
        return next

    def _ssa_parse_dialog(
        self : Subtitle,
        content : str,
        start : int,
        end : int,
        format : list[str]
    ) -> list[str]:
        comma_diff : int = content[start:end].count(",") + 1 - len(format)
        cursor : int = start
        index : int = 0
        group_name : list[str] = ["", ""]
        string : str = ""
        while cursor < end and index < len(format):
            next : int = self._ssa_next_dialog_part(content, cursor, end)
            if next == -1:
                break;
            match format[index]:
                case "Start":
                    group_name[0] = content[cursor + 1:next].replace("\\\n", "")
                case "End":
                    group_name[1] = content[cursor + 1:next].replace("\\\n", "")
                case "Text":
                    for n in range(comma_diff):
                        next = self._ssa_next_dialog_part(content, next, end)
                    string = content[cursor + 1:next].replace("\\\n", "").replace("\\N", "\n")
                case _:
                    pass
            cursor = next
            index += 1
        if string != "":
            return [" --> ".join(group_name), string]
        else:
            return []

    def _ssa_patch_dialog(
        self : Subtitle,
        content : str,
        start : int,
        end : int,
        format : list[str],
        helper : WalkHelper
    ) -> list[str]:
        comma_diff : int = content[start:end].count(",") + 1 - len(format)
        cursor : int = start
        index : int = 0
        group_name : list[str] = ["", ""]
        string_delimiters : None|tuple[int, int] = None
        while cursor < end and index < len(format):
            next : int = self._ssa_next_dialog_part(content, cursor, end)
            if next == -1:
                break;
            match format[index]:
                case "Start":
                    group_name[0] = content[cursor + 1:next].replace("\\\n", "")
                case "End":
                    group_name[1] = content[cursor + 1:next].replace("\\\n", "")
                case "Text":
                    for n in range(comma_diff):
                        next = self._ssa_next_dialog_part(content, next, end)
                    string_delimiters = (cursor + 1, next)
                    string = content[cursor + 1:next].replace("\\\n", "").replace("\\N", "\n")
                case _:
                    pass
            cursor = next
            index += 1
        if string_delimiters is not None:
            string : str = content[string_delimiters[0]:string_delimiters[1]].replace("\\\n", "").replace("\\N", "\n")
            if string != "":
                og_len : int = len(string)
                string = helper.apply_string(string, " --> ".join(group_name)).replace("\n", "\\N")
                if helper.str_modified:
                    content = (
                        content[:string_delimiters[0]] +
                        string +
                        content[string_delimiters[1]:]
                    )
                    return content, end + len(string) - og_len
        return content, end

    def read_ssa(self : Subtitle, content : str) -> list[list[str]]:
        entries : list[list[str]] = []
        cursor : int = self._ssa_look_for(content, 0, "[Events]")
        if cursor == -1:
            return entries
        format : list[str]
        start : int
        cursor, format = self._ssa_parse_format(content, cursor)
        while cursor != -1:
            start, cursor = self._ssa_next_dialog(content, cursor)
            if cursor != -1:
                group : list[str] = self._ssa_parse_dialog(content, start, cursor, format)
                if len(group) > 0:
                    entries.append(group)
        return entries

    def write_ssa(self : Subtitle, content : str, helper : WalkHelper) -> tuple[bytes, bool]:
        cursor : int = self._ssa_look_for(content, 0, "[Events]")
        if cursor == -1:
            return self.encode(content), False
        format : list[str]
        start : int
        cursor, format = self._ssa_parse_format(content, cursor)
        while cursor != -1:
            start, cursor = self._ssa_next_dialog(content, cursor)
            if cursor != -1:
                content, cursor = self._ssa_patch_dialog(content, start, cursor, format, helper)
        return self.encode(content), helper.modified

    # LRC parser ########################################################

    def _lrc_extract_code(
        self : Subtitle,
        content : str,
        start : int
    ) -> tuple[int|None, str]:
        if start < len(content) and content[start] == "[":
            end = content.find("]", start)
            if end != -1:
                code : str = content[start + 1:end]
                if self.LRC_TIMECODE.match(code):
                    return end, code
        return None, ""

    def _lrc_update_lyrics(
        self : Subtitle,
        lyrics : dict[str, tuple],
        codes : dict[str, bool],
        strings : list[str],
        string_pos : list[int]
    ) -> None:
        string : str = "\n".join(strings)
        repeatitions : list[int] = [len(codes)] # shared reference between instances
        for c, b in codes.items():
            lyrics[c] = (string, string_pos.copy(), repeatitions)
        codes.clear()
        strings.clear()
        string_pos = [0, 0]

    def _lrc_parse(self : Subtitle, lines : list[str]) -> dict[str, tuple]:
        lyrics : dict[str, tuple] = {}
        codes : dict[str, bool] = {}
        strings : list[str] = []
        string_pos : list[int] = [0, 0]
        for i, line in enumerate(lines):
            if line.startswith("["):
                if len(strings) > 0:
                    self._lrc_update_lyrics(lyrics, codes, strings, string_pos)
                cursor : int = 0
                while True:
                    next : int|None
                    code : str
                    next, code = self._lrc_extract_code(line, cursor)
                    if next is None:
                        if cursor != 0:
                            strings.append(line[cursor:])
                            string_pos[0] = i
                        break
                    else:
                        codes[code] = cursor != 0
                        cursor = next + 1
            else:
                if len(strings) > 0:
                    if line == "":
                        self._lrc_update_lyrics(lyrics, codes, strings, string_pos)
                    else:
                        strings.append(line)
                        string_pos[1] += 1
        if len(strings) > 0:
            self._lrc_update_lyrics(lyrics, codes, strings, string_pos)
        # sort and return
        return {
            k: lyrics[k]
            for k in sorted(
                lyrics.keys(),
                key=lambda x: (
                    float(x.split(":")[0]),
                    float(x.split(":")[1])
                )
            )
        }

    def read_lrc(self : Subtitle, content : str) -> list[list[str]]:
        lyrics : dict[str, tuple] = self._lrc_parse(content.splitlines())
        entries : list[list[str]] = []
        for code, (string, positions, repeatitions) in lyrics.items():
            entries.append([code, string])
        return entries

    def write_lrc(self : Subtitle, content : str, helper : WalkHelper) -> tuple[bytes, bool]:
        lines : list[str] = content.splitlines()
        lyrics : dict[str, tuple] = self._lrc_parse(lines)
        patch_segment : list[str] = []
        patched : list[str] = []
        for code, (string, positions, is_repeat) in lyrics.items():
            string = helper.apply_string(string, code)
            if helper.str_modified:
                patched.append(code)
                patch_segment.append("[{}]{}".format(code, string))
        if helper.modified:
            # remove patched
            lines_to_delete : list[int] = []
            for code in patched:
                string, positions, repeatitions = lyrics[code]
                if repeatitions[0] > 1:
                    repeatitions[0] -= 1
                    lines[positions[0]] = lines[positions[0]].replace("[{}]".format(code), "")
                else:
                    for i in range(positions[1] + 1):
                        lines_to_delete.append(positions[0] + i)
            lines_to_delete.sort(reverse=True)
            for i in lines_to_delete:
                if i == len(lines):
                    continue
                lines.pop(i)
            lines.extend(patch_segment)
            return self.encode("\n".join(lines)), True
        return self.encode(content), False

    # LRC parser ########################################################