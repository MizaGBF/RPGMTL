from __future__ import annotations
from . import Plugin, WalkHelper
import csv
import io

class CSV(Plugin):
    def __init__(self : CSV) -> None:
        super().__init__()
        self.name : str = "CSV"
        self.description : str = " v1.0\nHandle CSV files, including externMessage files from RPG Maker MV/MZ"

    def file_extension(self : CSV) -> list[str]:
        return ["csv"]

    def match(self : CSV, file_path : str) -> bool:
        return file_path.endswith(".csv")

    def read(self : CSV, file_path : str, content : bytes) -> list[list[str]]:
        entries : list[list[str]] = []
        with io.StringIO(self.decode(content)) as sin:
            reader = csv.reader(sin)
            content = [row for row in reader]
        for i, row in enumerate(content):
            for j, cell in enumerate(row):
                if cell != "" and not cell.isdigit():
                    entries.append(["Cell {}x{}".format(i,j), cell])
        return entries

    def write(self : CSV, file_path : str, content : bytes, strings : dict) -> tuple[bytes, bool]:
        helper : WalkHelper = WalkHelper(file_path, strings)
        with io.StringIO(self.decode(content)) as sin:
            reader = csv.reader(sin)
            content = [row for row in reader]
            with io.StringIO() as sout:
                writer = csv.writer(sout, delimiter=',', lineterminator='\n')
                for i, row in enumerate(content):
                    for j, cell in enumerate(row):
                        if cell != "" and not cell.isdigit():
                            content[i][j] = helper.apply_string(content[i][j], "Cell {}x{}".format(i,j))
                    writer.writerow(content[i])
                sout.seek(0)
                return self.encode(sout.read()), helper.modified