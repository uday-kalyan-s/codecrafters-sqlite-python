import sys

from dataclasses import dataclass

import os

# import sqlparse - available if you need it!

database_file_path = sys.argv[1]
command = sys.argv[2]

@dataclass
class Sql_Table_Record:
    record_size: int
    row_id: int
    header_size: int
    type_val: int
    name: str
    table_name: str
    rootpg_num: int
    sql: str

@dataclass
class Column:
    col_serial: int
    col_size: int
    col_value: str

@dataclass
class Record:
    record_size: int
    row_id: int
    columns: list[Column]

def get_size(serial: int):
    if serial <= 4:
        return serial
    elif 5 <= serial <= 7:
        return serial+1
    elif serial == 8 or serial == 9:
        return 0
    elif serial >= 12 and serial%2 == 0:
        return int((serial-12)/2)
    else:
        return int((serial-13)/2)

def get_value(serial: int, database_file: int):
    if serial == 0:
        return None
    elif serial <= 4:
        return read_big_endian(database_file, serial)
    elif 5 <= serial <= 7:
        return read_big_endian(database_file, serial+1)
    elif serial == 8:
        return 0
    elif serial == 9:
        return 1
    elif serial >= 12 and serial%2 == 0:
        return database_file.read((serial-12)//2)
    else:
        return database_file.read((serial-13)//2).decode('utf-8')

def read_record(database_file, start_pos):
    database_file.seek(start_pos)
    rec_size = get_varint(database_file)
    row_id = get_varint(database_file)
    # header
    header_size, h_byte = get_varint(database_file, True)
    header_size -= h_byte
    # print(header_size)
    columns: list[Column] = []
    while header_size > 0:
        col_serial, col_bytes = get_varint(database_file, True)
        col_size = get_size(col_serial)
        col = Column(col_serial, col_size, None)
        columns.append(col)
        header_size -= col_bytes
    for ind, col in enumerate(columns):
        col_value = get_value(col.col_serial, database_file)
        columns[ind].col_value = col_value
    # print(Record(rec_size, row_id, columns))
    return Record(rec_size, row_id, columns)

def get_sqltab_record(database_file, start_pos: int):
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
    sql_serial = get_varint(database_file)
    sql_size = get_size(sql_serial)
    type_text = database_file.read(type_size)
    name_text = database_file.read(name_size).decode('utf-8')
    table_name = database_file.read(tbl_name_size).decode('utf-8')
    rootpg_num = read_big_endian(database_file, 1)
    sql_text = database_file.read(sql_size).decode('utf-8')

    return Sql_Table_Record(rec_size, row_id, header_size, type_text, name_text, table_name, rootpg_num, sql_text)

def read_big_endian(database_file, size: int):
    return int.from_bytes(database_file.read(size), byteorder="big")

def get_varint(database_file, req_consumed=False):
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
    if req_consumed == False:
        return varint_res
    else:
        return varint_res, bytes_used

def fetch_tables():
    records = []
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
            record = get_sqltab_record(database_file, start_pos)
            records.append(record)
    return records

tables: list[Sql_Table_Record] = fetch_tables()

def get_pg_size():
    with open(database_file_path, "rb") as database_file:
        database_file.seek(16)
        return read_big_endian(database_file, 2)

db_page_size = get_pg_size()
# print(db_page_size)

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
    for table in tables:
        print(table.table_name, end=" ")
elif "COUNT" in command or "count" in command:
    # print(f"Invalid command: {command}")
    query_table_name = command.split(' ')[-1]
    right_rec = None
    for table in tables:
        # print(table, query_table_name)
        if table.table_name == query_table_name:
            right_rec = table
            break
    # print(right_rec)
    with open(database_file_path, "rb") as database_file:
        database_file.seek(db_page_size*(right_rec.rootpg_num-1))
        # shift to right offset
        database_file.seek(3, os.SEEK_CUR)
        rows = read_big_endian(database_file, 2)
        print(rows)
else:
    cmd_parts = command.split(' ')
    query_col_name = cmd_parts[1]
    query_table_name = cmd_parts[3]
    right_rec = None
    for table in tables:
        # print(table, query_table_name)
        if table.table_name == query_table_name:
            right_rec = table
            break
    def get_cols(sql_str: str):
        parts = sql_str.split(',')
        parts[0] = parts[0].split('(')[1]
        parts[-1] = parts[-1].split(')')[0]
        col_names = []
        for part in parts:
            part = part.strip()
            words = part.split(' ')
            col_names.append(words[0])
        return col_names
    col_names = get_cols(right_rec.sql)
    col_index = col_names.index(query_col_name)
    with open(database_file_path, "rb") as database_file:
        page_offset = db_page_size*(right_rec.rootpg_num-1)
        database_file.seek(page_offset)
        # shift to right offset
        database_file.seek(3, os.SEEK_CUR)
        num_rows = read_big_endian(database_file, 2)
        database_file.seek(page_offset+8)
        cell_start_pos = []
        for i in range(num_rows):
            cell_start_pos.append(read_big_endian(database_file, 2))
        for start_pos in cell_start_pos:
            record = read_record(database_file, start_pos+page_offset)
            print(record.columns[col_index].col_value)