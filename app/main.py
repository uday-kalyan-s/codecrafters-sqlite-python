import sys

from dataclasses import dataclass

import os

# import sqlparse - available if you need it!

database_file_path = sys.argv[1]
command = sys.argv[2]

@dataclass
class Record:
    record_size: int
    row_id: int
    header_size: int
    type_val: int
    name: str
    table_name: str

def get_record(database_file, start_pos: int):
    database_file.seek(start_pos)
    rec_size = get_varint(database_file)
    row_id = get_varint(database_file)
    # currently at header start
    header_size = get_varint(database_file)
    type_serial = get_varint(database_file)
    type_size = get_size(type_serial)
    name_serial = get_varint(database_file)
    name_size = get_size(name_serial)
    tbl_name_serial = get_varint(database_file)
    tbl_name_size = get_size(tbl_name_serial)
    _rootpg_serial = get_varint(database_file)
    _sql_serial = get_varint(database_file)
    type_text = database_file.read(type_size)
    name_text = database_file.read(name_size).decode('utf-8')
    table_name = database_file.read(tbl_name_size).decode('utf-8')
    return Record(rec_size, row_id, header_size, type_text, name_text, table_name)

def get_size(serial: int):
    if serial >= 12 and serial%2 == 0:
        return int((serial-12)/2)
    else: # TODO: rest of formats
        return int((serial-13)/2)

def read_big_endian(database_file, size: int):
    return int.from_bytes(database_file.read(size), byteorder="big")

def get_varint(database_file):
    varint_res = 0
    bytes_used = 0
    while True:
        bytes_used += 1
        cur_value = read_big_endian(database_file, 1)
        # print(cur_value)
        if bytes_used == 9:
            varint_res = varint_res*128 + cur_value
            break
        if (cur_value >> 7) & 1 > 0:
            varint_res = varint_res*128 + (cur_value & 0b01111111)
        else:
            varint_res = varint_res*128 + cur_value
            break
    # print(varint_res)
    return varint_res

if command == ".dbinfo":
    with open(database_file_path, "rb") as database_file:
        # You can use print statements as follows for debugging, they'll be visible when running tests.
        print("Logs from your program will appear here!", file=sys.stderr)

        # stage 1
        database_file.seek(16)  # Skip the first 16 bytes of the header
        page_size = read_big_endian(database_file, 2)
        print(f"database page size: {page_size}")

        # get the number of tables (cells in page header)
        # 100 for db header and +3 in that
        database_file.seek(100+3)
        table_count = read_big_endian(database_file, 2)
        print(f"number of tables: {table_count}")
elif command == '.tables':
    with open(database_file_path, "rb") as database_file:
        database_file.seek(100+3)
        table_count = read_big_endian(database_file, 2)
        
        database_file.seek(100+8)
        cell_start_pos = []
        # print(table_count)
        for i in range(table_count):
            cell_start_pos.append(read_big_endian(database_file, 2))
        # print(cell_start_pos)
        for start_pos in cell_start_pos:
            record = get_record(database_file, start_pos)
            print(record.table_name, end=" ")
    pass
else:
    print(f"Invalid command: {command}")
