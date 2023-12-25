#!/usr/bin/python

import binascii
import sys
import struct

sector_size = 0x800

def c_string(a):
    return a.split(b'\0')[0].decode('shift_jis')

empty = bytes(sector_size)

def main(file):
    sector = 0
    with open(file, 'rb') as f:
        with open(f'{file}.remapped', 'wb') as o:
            while True:
                f.seek(sector * sector_size)
                data = f.read(sector_size)

                header_fmt = '<8s12s4s32s8s16s2L'
                if len(data) < struct.calcsize(header_fmt):
                    break

                (miut, name, category, component, version, date, load_addr,
                    entry) = struct.unpack_from(header_fmt, data)

                if miut == b'MIUT\0\0\0\0':
                    miut = c_string(miut)
                    name = c_string(name)
                    category = c_string(category)
                    component = c_string(component)
                    version = c_string(version)
                    date = c_string(date)
                    print('0x%08x: %-12s %-4s %-32s %-8s %-16s %08x %08x' % (
                            sector * sector_size, name, category, component,
                            version, date, load_addr, entry))

                    o.seek(load_addr)

                if len(data) != 0x800:
                    break

                # special handling for "kernel space"
                if sector * sector_size == 0x80000000:
                    o.seek(0x80000000)

                # consecutively write additional blocks which contain no MIUT
                if data != empty:
                    #print("Writing to 0x%8x" % o.tell())
                    o.write(data)

                sector += 1

    return 0

sys.exit(main(sys.argv[1]))
