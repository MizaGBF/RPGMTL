from __future__ import annotations
from . import Plugin, WalkHelper
import csv
import io

class CSV(Plugin):
    LM_JP_TEXT = 3
    LM_EN_TEXT = 4
    
    def __init__(self : CSV) -> None:
        super().__init__()
        self.name : str = "CSV"
        self.description : str = " v2.0\nHandle CSV files, including externMessage files from RPG Maker MV/MZ"
        self.related_tool_plugins : list[str] = [self.name]

    def match(self : CSV, file_path : str, is_for_action : bool) -> bool:
        return file_path.endswith(".csv")

    def get_setting_infos(self : CSV) -> dict[str, list]:
        return {
            "csv_extract_grouping": ["Group strings by (Require re-extract)", "str", "Cell", ["Cell", "Row", "Column"]],
            "csv_ignore_non_string": ["Ignore empty strings and numbers (Require re-extract)", "bool", True, None],
        }

    def is_livemaker_csv(self : CSV, content : bytes) -> bool:
        return (
            content.startswith(b"ID,Label,Context,Original text,Translated text")
            and b"pylm" in content
        )    

    def read(self : CSV, file_path : str, content : bytes) -> list[list[str]]:
        if self.is_livemaker_csv(content):
            return self.read_livemaker(file_path, content)
        else:
            return self.read_standard(file_path, content)
    
    def read_standard(self : CSV, file_path : str, content : bytes) -> list[list[str]]:
        entries : list[list[str]] = []
        with io.StringIO(self.decode(content)) as sin:
            reader = csv.reader(sin)
            content = [row for row in reader]
        ignore_ns : bool = self.settings.get("csv_ignore_non_string", True)
        match self.settings.get("csv_extract_grouping", "Cell"):
            case "Row":
                for i, row in enumerate(content):
                    group : list[str] = [f"Row {i}"]
                    for j, cell in enumerate(row):
                        if not ignore_ns or (cell != "" and not cell.isdigit()):
                            group.append(cell)
                    if len(group) > 1:
                        entries.append(group)
            case "Column":
                # convert
                columns : list[list] = []
                for i, row in enumerate(content):
                    for j, cell in enumerate(row):
                        if j <= len(columns):
                            columns.append([])
                        print(i, j, len(columns))
                        columns[j].append(cell)
                for i, column in enumerate(columns):
                    group : list[str] = [f"Column {i}"]
                    for j, cell in enumerate(column):
                        if not ignore_ns or (cell != "" and not cell.isdigit()):
                            group.append(cell)
                    if len(group) > 1:
                        entries.append(group)
            case _: # cell
                for i, row in enumerate(content):
                    for j, cell in enumerate(row):
                        if not ignore_ns or (cell != "" and not cell.isdigit()):
                            entries.append([f"Cell {i}x{j}", cell])
        return entries

    def read_livemaker(self : CSV, file_path : str, content : bytes) -> list[list[str]]:
        entries : list[list[str]] = []
        with io.StringIO(self.decode(content)) as sin:
            reader = csv.reader(sin)
            group = [""]
            for i, row in enumerate(reader):
                if i == 0:
                    continue
                g = row[0].split(".lsb:", 1)[1].split(":")[0]
                if g != group[0]:
                    if len(group) > 1:
                        entries.append(group)
                        group = [g]
                    else:
                        group[0] = g
                group.append(row[self.LM_JP_TEXT])
            if len(group) > 1:
                entries.append(group)
        return entries

    def write(self : CSV, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        if self.is_livemaker_csv(content):
            return self.write_livemaker(name, file_path, content)
        else:
            return self.write_standard(name, file_path, content)
        
    def write_standard(self : CSV, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
        with io.StringIO(self.decode(content)) as sin:
            reader = csv.reader(sin)
            content = [row for row in reader]
        # patch
        ignore_ns : bool = self.settings.get("csv_ignore_non_string", True)
        match self.settings.get("csv_extract_grouping", "Cell"):
            case "Row":
                for i, row in enumerate(content):
                    for j, cell in enumerate(row):
                        if not ignore_ns or (cell != "" and not cell.isdigit()):
                            content[i][j] = helper.apply_string(content[i][j], f"Row {i}")
            case "Column":
                # convert
                columns : list[list] = []
                for i, row in enumerate(content):
                    for j, cell in enumerate(row):
                        if j <= len(columns):
                            columns.append([])
                        columns[j].append({"str":cell, "i":i, "j":j})
                for i, column in enumerate(columns):
                    for j, cell in enumerate(column):
                        if not ignore_ns or (cell["str"] != "" and not cell["str"].isdigit()):
                            content[cell["i"]][cell["j"]] = helper.apply_string(cell["str"], f"Column {i}")
            case _: # cell
                for i, row in enumerate(content):
                    for j, cell in enumerate(row):
                        if not ignore_ns or (cell != "" and not cell.isdigit()):
                            content[i][j] = helper.apply_string(content[i][j], f"Cell {i}x{j}")
        # write
        with io.StringIO() as sout:
            writer = csv.writer(sout, delimiter=',', lineterminator='\n')
            for i, row in enumerate(content):
                writer.writerow(content[i])
            sout.seek(0)
            if helper.modified:
                return self.encode(sout.read()), True
            else:
                return content, False
        
    def write_livemaker(self : CSV, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
        helper : WalkHelper = WalkHelper(file_path, self.owner.strings[name])
        with io.StringIO(self.decode(content)) as sin:
            reader = csv.reader(sin)
            content = [row for row in reader]
        for i, row in enumerate(content):
            if i == 0:
                continue
            group = row[0].split(".lsb:", 1)[1].split(":")[0]
            tl = helper.apply_string(row[self.LM_JP_TEXT], group)
            if tl != row[self.LM_JP_TEXT]:
                content[i][self.LM_EN_TEXT] = tl
        # write
        with io.StringIO() as sout:
            writer = csv.writer(sout, delimiter=',', lineterminator='\n')
            for i, row in enumerate(content):
                writer.writerow(content[i])
            sout.seek(0)
            if helper.modified:
                return self.encode(sout.read()), True
            else:
                return content, False