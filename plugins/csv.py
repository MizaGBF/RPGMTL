from __future__ import annotations
from . import Plugin, WalkHelper
import csv
import io

class CSV(Plugin):
    def __init__(self : CSV) -> None:
        super().__init__()
        self.name : str = "CSV"
        self.description : str = " v1.5\nHandle CSV files, including externMessage files from RPG Maker MV/MZ"
        self.related_tool_plugins : list[str] = [self.name]

    def match(self : CSV, file_path : str, is_for_action : bool) -> bool:
        return file_path.endswith(".csv")

    def get_setting_infos(self : CSV) -> dict[str, list]:
        return {
            "csv_extract_grouping": ["Group strings by (Require re-extract)", "str", "Cell", ["Cell", "Row", "Column"]],
            "csv_ignore_non_string": ["Ignore empty strings and numbers (Require re-extract)", "bool", True, None],
        }

    def read(self : CSV, file_path : str, content : bytes) -> list[list[str]]:
        entries : list[list[str]] = []
        with io.StringIO(self.decode(content)) as sin:
            reader = csv.reader(sin)
            content = [row for row in reader]
        ignore_ns : bool = self.settings.get("csv_ignore_non_string", True)
        match self.settings.get("csv_extract_grouping", "Cell"):
            case "Row":
                for i, row in enumerate(content):
                    group : list[str] = ["Row {}".format(i)]
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
                    group : list[str] = ["Column {}".format(i)]
                    for j, cell in enumerate(column):
                        if not ignore_ns or (cell != "" and not cell.isdigit()):
                            group.append(cell)
                    if len(group) > 1:
                        entries.append(group)
            case _: # cell
                for i, row in enumerate(content):
                    for j, cell in enumerate(row):
                        if not ignore_ns or (cell != "" and not cell.isdigit()):
                            entries.append(["Cell {}x{}".format(i,j), cell])
        return entries

    def write(self : CSV, name : str, file_path : str, content : bytes) -> tuple[bytes, bool]:
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
                            content[i][j] = helper.apply_string(content[i][j], "Row {}".format(i))
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
                            content[cell["i"]][cell["j"]] = helper.apply_string(cell["str"], "Column {}".format(i))
            case _: # cell
                for i, row in enumerate(content):
                    for j, cell in enumerate(row):
                        if not ignore_ns or (cell != "" and not cell.isdigit()):
                            content[i][j] = helper.apply_string(content[i][j], "Cell {}x{}".format(i,j))
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