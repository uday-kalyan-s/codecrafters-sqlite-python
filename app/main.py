import sys

from .models import Column, Record
from .utils import *
from .schemas import Sqlite_Schema

import os

# import sqlparse - available if you need it!

database_file_path = sys.argv[1]
command = sys.argv[2]

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
        col_value = get_value(col.serial, database_file)
        columns[ind].value = col_value
    # print(Record(rec_size, row_id, columns))
    return Record(rec_size, row_id, columns)

def fetch_tables():
    records = []
    with open(database_file_path, "rb") as database_file:
        database_file.seek(100+3)
        table_count = read_big_endian(database_file, 2)
        database_file.seek(100+8)
        cell_start_pos = []
        for i in range(table_count):
            cell_start_pos.append(read_big_endian(database_file, 2))
        for start_pos in cell_start_pos:
            record = read_record(database_file, start_pos)
            records.append(record)
    return records

tables: list[Record] = fetch_tables()

def get_pg_size():
    with open(database_file_path, "rb") as database_file:
        database_file.seek(16)
        return read_big_endian(database_file, 2)

db_page_size = get_pg_size()
# print(db_page_size)

def search(query_table_name: str, query_col_names: str):
    right_rec = None
    for table in tables:
        # print(table, query_table_name)
        if table.columns[Sqlite_Schema.TABLE_NAME].value == query_table_name:
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
    col_names = get_cols(right_rec.columns[Sqlite_Schema.SQL].value)
    # col_index = col_names.index(query_col_name)
    col_indexes = [col_names.index(qcn) for qcn in query_col_names]
    response = []
    with open(database_file_path, "rb") as database_file:
        page_offset = db_page_size*(right_rec.columns[Sqlite_Schema.ROOTPG].value-1)
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
            # print(record.columns[col_index].col_value)
            response.append([record.columns[col_index].value for col_index in col_indexes])
    return response

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
        print(table.columns[Sqlite_Schema.TABLE_NAME].value, end=" ")
elif "COUNT" in command or "count" in command:
    query_table_name = command.split(' ')[-1]
    right_rec = None
    for table in tables:
        if table.columns[Sqlite_Schema.TABLE_NAME].value == query_table_name:
            right_rec = table
            break
    # print(right_rec)
    with open(database_file_path, "rb") as database_file:
        database_file.seek(db_page_size*(right_rec.columns[Sqlite_Schema.ROOTPG].value-1))
        # shift to right offset
        database_file.seek(3, os.SEEK_CUR)
        rows = read_big_endian(database_file, 2)
        print(rows)
elif "where" in command or "WHERE" in command:
    cmd_parts = command.split(' ')
    query_where_val = cmd_parts[-1].replace("'", '').strip()
    query_where_col = cmd_parts[-3]
    cmd_parts = cmd_parts[:-4]
    query_table_name = cmd_parts[-1]
    cmd_parts = cmd_parts[1:-2]
    query_col_names = [x.replace(',', '').strip() for x in cmd_parts]
    # print(query_col_names + [query_where_col])
    response = search(query_table_name, query_col_names + [query_where_col])
    # print(response)
    response_filters = list(filter(lambda row: row[-1] == query_where_val, response))
    response_filters = list(map(lambda row: row[:-1], response_filters))
    # print(response_filters)
    for row in response_filters:
        print("|".join(row))
elif "," in command:
    cmd_parts = command.split(' ')
    query_table_name = cmd_parts[-1]
    cmd_parts = cmd_parts[1:-2]
    query_col_names = [x.replace(',', '').strip() for x in cmd_parts]
    response = search(query_table_name, query_col_names)
    for row in response:
        print("|".join(row))
else:
    cmd_parts = command.split(' ')
    query_col_name = cmd_parts[1]
    query_table_name = cmd_parts[3]
    response = search(query_table_name, [query_col_name])
    for r in response:
        print(r[0])