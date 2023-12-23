#!/usr/bin/python

import struct
import sys

def read_struct(f, fmt):
    buf = f.read(struct.calcsize(fmt))
    if not buf:
        return None

    return struct.unpack_from(fmt, buf)

def read_struct_iter(f, fmt, count):
    buf = f.read(struct.calcsize(fmt) * count)
    if not buf:
        return None

    return struct.iter_unpack(fmt, buf)

yesno = {1: 'Yes', 0: 'No'}


def main(file):
    is_denso = False

    with open(file, 'rb') as f:
        # Loading Module Management Frame
        loading_module_management_frame = read_struct(f, '>HH')
        if not loading_module_management_frame:
            print('LMMF missing')
            return 1

        number_of_accomodated_systems, reserved = loading_module_management_frame
        print('Loading Module Management Frame:')
        print(f' Number of accomodated systems: {number_of_accomodated_systems}')

        # System Identification Information
        systems = []
        for system_identification_information in read_struct_iter(
                f, '>8sbbHHH', number_of_accomodated_systems):

            (manufacturer_location, manufacturer_floor, reserved, manufacturer_id_date,
                number_of_accomodated_modules, reserved) = system_identification_information

            # deviation from spec: just a name, no coordinates
            print('System Identification Information:')
            print(' Manufacturer Identifier:')
            if manufacturer_location == b'DENSO\0\0\0':
                is_denso = True
                manufacturer_name = manufacturer_location.decode('ascii').split('\0')[0]
                print(f'  Manufacturer name: {manufacturer_name}')
            else:
                manufacturer_lat, manufacturer_long = struct.unpack_from(">LL", manufacturer_location)
                print(f'  Manufacturer location:')
                print(f'   Lat: %d sec %s' % ((manufacturer_lat << 1) >> 12, {0: 'North', 1: 'South'}[manufacturer_lat >> 31]))
                print(f'   Long: %d sec %s' % ((manufacturer_long << 1) >> 12, {0: 'East', 1: 'West'}[manufacturer_long >> 31]))

            print(f'  Manufacturer floor: {manufacturer_floor}')
            print(f'  Manufacturer ID date: {manufacturer_id_date}')
            print(f' Number of accomodated modules: {number_of_accomodated_modules}')

            systems.append({
                'manufacturer_location': manufacturer_location,
                'manufacturer_floor': manufacturer_floor,
                'manufacturer_id_date': manufacturer_id_date,
                'number_of_accomodated_modules': number_of_accomodated_modules,
                'modules': []})

        for system_info in systems:
            # System Management Information
            # nothing to do

            number_of_accomodated_modules = system_info['number_of_accomodated_modules']
            modules = system_info['modules']

            # Module Identification Information
            for module_identification_information in read_struct_iter(
                    f, '>bbbb52s8s', number_of_accomodated_modules):

                (module_category, reserved, reserved, reserved,
                    module_name, module_version) = module_identification_information

                module_name = module_name.decode('ascii').split('\0')[0]
                module_version = module_version.decode('ascii').split('\0')[0]
                module_diagnostic_service_flag = (module_category >> 7) & 0x1
                module_test_flag = (module_category >> 6) & 0x1
                module_category_flag = module_category & 0x3
                print('Module Identification Information:')
                print(f' Module category: {module_category}')
                print(f' Module name: {module_name}')
                print(f' Module version: {module_version}')
                print(' Module is diagnostic service: %s' % yesno[module_diagnostic_service_flag])
                print(' Module is test: %s' % yesno[module_test_flag])
                print(' Module category: %s' % {
                    0: 'Initial program',
                    1: 'Program',
                    2: 'Library',
                    3: 'Data'}[module_category_flag])

                modules.append({
                    'module_category': module_category,
                    'module_name': module_name,
                    'module_version': module_version,
                    'module_diagnostic_service_flag': module_diagnostic_service_flag,
                    'module_test_flag': module_test_flag,
                    'module_category_flag': module_category_flag})

            # Module Management Information
            module_index = 0
            for module_management_information in read_struct_iter(
                    f, '>HH64s182sLH', number_of_accomodated_modules):

                (module_date_valid, module_date_invalid, module_title,
                    module_manufacturer_dependent_data, module_code_address,
                    module_code_size) = module_management_information

                module_title = module_title.decode('ascii').split('\0')[0]
                print('Module Management Information:')
                print(f' Module valid date: {module_date_valid}')
                print(f' Module invalid date: {module_date_invalid}')
                print(f' Module title: {module_title}')
                print(f' Module manufacturer dependent data: {module_manufacturer_dependent_data}')
                # deviation from spec: not a DSA but number of sectors
                # relative to last sector of headers
                print(f' Module code address: {module_code_address}')
                if not is_denso:
                    module_sector_address = (module_code_address >> 8) & 0xffffff
                    module_disk_side_flag = (module_code_address >> 7) & 0x1
                    module_storage_layer_flag = (module_code_address >> 6) & 0x1
                    module_logical_sectors = module_code_address & 0x3f
                    print(f' Module sector address: {module_sector_address}')
                    print(' Module disk side: %s' % {0: 'A', 1: 'B'}[module_disk_side_flag])
                    print(' Module storage layer: %s' % {0: 'Single layer', 1: 'Double layer'}[module_storage_layer_flag])
                    print(f' Module logical sectors: {module_logical_sectors}')
                print(f' Module code size: {module_code_size}')

                modules[module_index].update({
                    'module_date_valid': module_date_valid,
                    'module_date_invalid': module_date_invalid,
                    'module_title': module_title,
                    'module_manufacturer_dependent_data': module_manufacturer_dependent_data,
                    'module_code_address': module_code_address,
                    'module_code_size': module_code_size})

                if not is_denso:
                    modules[module_index].update({
                        'module_sector_address': module_sector_address,
                        'module_disk_side_flag': module_disk_side_flag,
                        'module_storage_layer_flag': module_storage_layer_flag,
                        'module_logical_sectors': module_logical_sectors})

                module_index += 1

        dvd_sector_size = 2048
        module_base_address = f.tell() // dvd_sector_size
        for system_info in systems:
            for module in system_info['modules']:
                module_code_size = module['module_code_size']
                module_name = module['module_name']

                #position = f.tell()
                #misalignment = position % dvd_sector_size
                #if misalignment:
                #    skip_bytes = dvd_sector_size - misalignment
                #    print(f'Skipping {skip_bytes} bytes to module {module_name}')
                #    f.read(skip_bytes)

                if is_denso:
                    sectors = module['module_code_address']
                else:
                    sectors = module['module_sector_address']
                module_base = (module_base_address + sectors) * dvd_sector_size
                f.seek(module_base)

                #module_code = f.read(module_code_size * dvd_sector_size)
                #with open(f'module_code.{module_name}' , 'wb') as f2:
                #    f2.write(module_code)

                if is_denso:
                    module_code_block_lengths = read_struct(f, '>4L')
                    if not module_code_block_lengths:
                        print('Module code block lengths missing')
                        return 1

                    module_code_header = read_struct(f, '>4s4s')
                    if not module_code_header:
                        print('Module code header missing')
                        return 1

                    (module_code_name, module_code_version) = module_code_header
                    module_code_name = module_code_name.decode('ascii')
                    module_code_version = module_code_version.decode('ascii')

                    print('Module code header:')
                    print(f' Module code name: {module_code_name}')
                    print(f' Module code version: {module_code_version}')

                    f.seek(module_base + dvd_sector_size)

                    module_code_block_count = 0
                    for module_code_block_length in module_code_block_lengths:
                        if module_code_block_length:
                            module_code_block = f.read(module_code_block_length)
                            with open(f'module_code.{module_name}.{module_code_block_count}' , 'wb') as f2:
                                f2.write(module_code_block)

                        module_code_block_count += 1

                    if f.tell() - module_base != module_code_size * dvd_sector_size:
                        print('Inconsistent module code block sizes')
                        return 1
                else:
                    module_code_block = f.read(module_code_size * dvd_sector_size)
                    with open(f'module_code.{module_name}' , 'wb') as f2:
                        f2.write(module_code_block)

        remainder = f.read()
        if len(remainder) > 0:
            print('WARNING: %d bytes of data left in file' % len(remainder))

    return 0

sys.exit(main(sys.argv[1]))
