#!/usr/bin/python

import binascii
import sys
import struct

def read_struct(f, fmt):
    buf = f.read(struct.calcsize(fmt))
    if not buf:
        return None

    return struct.unpack_from(fmt, buf)

def main(file):
    addrs = []

    base = None
    with open(file, 'rb') as f:
        f.seek(0x890)
        for i in range(0, 32):
            addrhi, addrlo, blocks = read_struct(f, '>BHB')
            addr = (addrhi - 0x01)*0x3c*0x4b + (((addrlo >> 8) & 0xff) - 0x02)*0x4b + (addrlo & 0xff)
            addr *= 0x800
            addrs.append({
                    'addrcode': (addrhi << 16) | addrlo,
                    'addr': addr,
                    'blocks': blocks,
                })

        for addr in addrs:
            checksum = read_struct(f, '>L')[0]
            addr['checksum'] = checksum

        for addr in addrs:
            flags = read_struct(f, '>B')[0]
            if flags not in [0x00, 0x01, 0x02]:
                print("Error: wrong addr flags")
                return 1
            addr['addr_flags'] = flags

        for addr in addrs:
            flags = read_struct(f, '>B')[0]
            if flags not in [0x00, 0x01, 0x02]:
                print("Error: wrong maybe checksum flags")
                return 1
            addr['checksum_flags'] = flags

        for addr in addrs:
            source = read_struct(f, '>L')[0]
            if base is None:
                base = source
            addr['source'] = source

        for addr in addrs:
            flags = read_struct(f, '>B')[0]
            if flags not in [0x01, 0x02]:
                print("Error: wrong source flags")
                return 1
            addr['source_flags'] = flags

        for addr in addrs:
            addr['dest'] = read_struct(f, '>L')[0]

        for addr in addrs:
            flags = read_struct(f, '>B')[0]
            if flags not in [0x00, 0x01, 0x02]:
                print("Error: wrong dest flags")
                return 1
            addr['dest_flags'] = flags

        for addr in addrs:
            addr['length'] = read_struct(f, '>L')[0]

        length_sum = 0
        with open(file + '.mapped', 'wb') as o:
            for value in addrs:
                addr = value['addr']
                addrcode = value['addrcode']
                blocks = value['blocks']
                addr_flags = value['addr_flags']
                source = value['source']
                source_flags = value['source_flags']
                dest = value['dest']
                dest_flags = value['dest_flags']
                length = value['length']
                length_sum+=length
                checksum = value['checksum']
                print('0x%08x/0x%08x/0x%02x/0x%06x/0x%08x: Mapping 0x%x/0x%x len 0x%x to 0x%x/0x%x' % (
                    addr, blocks * 0x4000, addr_flags, addrcode, checksum,
                    source, source_flags, length, dest, dest_flags))

                # this mixes reading-in and mapping - should be two steps if
                # block sizes or address offsets differ
                f.seek(addr)
                data = f.read(blocks * 0x4000)

                checksum_calc = 0
                for (value,) in struct.iter_unpack(">L", data):
                    checksum_calc += value
                checksum_calc &= 0xffffffff

                if checksum_calc != checksum:
                    print("WARNING: Checksum mismatch: 0x%x != 0x%x" % (
                            checksum, checksum_calc))

                o.seek(dest)
                o.write(data)

    print("length: 0x%x (%d)" % (length_sum, length_sum))

    return 0

sys.exit(main(sys.argv[1]))
