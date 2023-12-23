#!/usr/bin/python

import sys
import struct

def read_struct(f, fmt):
    buf = f.read(struct.calcsize(fmt))
    if not buf:
        return None

    return struct.unpack_from(fmt, buf)

def main(file):
    with open(file, 'rb') as f:
        f.seek(0x800)

        sum = 0
        for i in range(0, 0x3ff):
            sum += read_struct(f, '>L')[0]
            sum = sum % 2**32

    print("sum: 0x%x" % sum)

    return 0

sys.exit(main(sys.argv[1]))
