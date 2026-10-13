from dataclasses import dataclass

@dataclass
class Column:
    serial: int
    size: int
    value: str

@dataclass
class Record:
    size: int
    row_id: int
    columns: list[Column]