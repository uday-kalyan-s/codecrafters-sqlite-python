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

def get_value(serial: int, database_file):
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