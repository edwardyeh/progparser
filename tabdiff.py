# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2022 Yeh, Hsin-Hsien <yhh76227@gmail.com>
#
"""
Programming reference table comparer.
"""
import argparse
import sys
import textwrap

from .utils.ref_table import ReferenceTable

### Class Definition ###

class CompareTable(ReferenceTable):
    """Programming register table"""  #{{{

    def __init__(self, table_fp: str, table_type: str, 
                 is_sign_ignore: bool, is_access_ignore: bool, debug_mode=None):
    #{{{ 
        super().__init__(debug_mode)

        self.is_sign_ignore = is_sign_ignore
        self.is_access_ignore = is_access_ignore

        if table_type == 'txt':
            self.txt_table_parser(table_fp)
        elif table_type == 'xlsx':
            self.xlsx_table_parser(table_fp)
        else:
            raise ValueError(f"Unsupported input table style '{table_type}'")
    #}}}

    def __eq__(self, other):
    #{{{
        max_reg_len = 0
        err_reg_list = []
        l_max_addr = max(self.reg_table.keys())
        r_max_addr = max(other.reg_table.keys())
        max_addr = l_max_addr if l_max_addr > r_max_addr else r_max_addr

        for addr in range(0, max_addr+4, 4):
            l_hit = addr in self.reg_table
            r_hit = addr in other.reg_table
            if l_hit and r_hit:
                l_reg_dict = {reg.lsb: reg for reg in sorted(self.reg_table[addr].regs, key=lambda reg: reg.lsb)}
                r_reg_dict = {reg.lsb: reg for reg in sorted(other.reg_table[addr].regs, key=lambda reg: reg.lsb)}
                for lsb in range(0, 32):
                    l_hit = lsb in l_reg_dict
                    r_hit = lsb in r_reg_dict
                    if l_hit and r_hit:
                        l_reg = l_reg_dict[lsb]
                        r_reg = r_reg_dict[lsb]
                        l_reg.comment = r_reg.comment = None
                        l_reg.row_idx = r_reg.row_idx = None
                        if self.is_sign_ignore:
                            l_reg.is_signed = r_reg.is_signed = None 
                        if self.is_access_ignore:
                            l_reg.is_access = r_reg.is_access = None
                        if l_reg != r_reg:
                            if l_reg.name != 'RESERVED' or r_reg.name != 'RESERVED':
                                err_reg_list.append(('d', l_reg, r_reg))
                                if (reg_len := len(l_reg.name)) > max_reg_len:
                                    max_reg_len = reg_len
                                if (reg_len := len(r_reg.name)) > max_reg_len:
                                    max_reg_len = reg_len
                    elif l_hit:
                        if (reg := l_reg_dict[lsb]).name != 'RESERVED':
                            err_reg_list.append(('l', reg))
                            if (reg_len := len(reg.name)) > max_reg_len:
                                max_reg_len = reg_len
                    elif r_hit:
                        if (reg := r_reg_dict[lsb]).name != 'RESERVED':
                            err_reg_list.append(('r', reg))
                            if (reg_len := len(reg.name)) > max_reg_len:
                                max_reg_len = reg_len
            elif l_hit:
                for reg in sorted(self.reg_table[addr].regs, key=lambda reg: reg.lsb):
                    if reg.name != 'RESERVED':
                        err_reg_list.append(('l', reg))
                        if (reg_len := len(reg.name)) > max_reg_len:
                            max_reg_len = reg_len
            elif r_hit:
                for reg in sorted(other.reg_table[addr].regs, key=lambda reg: reg.lsb):
                    if reg.name != 'RESERVED':
                        err_reg_list.append(('r', reg))
                        if (reg_len := len(reg.name)) > max_reg_len:
                            max_reg_len = reg_len

        if len(err_reg_list):
            max_reg_len += 4
            print("   {}".format('=' * (max_reg_len + 44)))
            print("   {}{:8}{:5}{:5}{:6}{:8}{:12}".format(
                'Register'.ljust(max_reg_len),
                'Addr', 'MSB', 'LSB', 'Sign', 'Access', 'Initial'))
            print("   {}".format('=' * (max_reg_len + 44)))

            pattern = r"{}{:<#8x}{:<5}{:<5}{:<6}{:<8}{:<#12x}"

            for err_reg in err_reg_list:
                if err_reg[0] == 'd':
                    reg = err_reg[1]
                    print("<!", pattern.format(reg.name.lower().ljust(max_reg_len),
                                               reg.addr, reg.msb, reg.lsb, 
                                               's' if reg.is_signed else 'u',
                                               'y' if reg.is_access else 'n', reg.init_val))
                    reg = err_reg[2]
                    print(">!", pattern.format(reg.name.lower().ljust(max_reg_len),
                                               reg.addr, reg.msb, reg.lsb, 
                                               's' if reg.is_signed else 'u',
                                               'y' if reg.is_access else 'n', reg.init_val))
                elif err_reg[0] == 'l':
                    reg = err_reg[1]
                    print("< ", pattern.format(reg.name.lower().ljust(max_reg_len),
                                               reg.addr, reg.msb, reg.lsb, 
                                               's' if reg.is_signed else 'u',
                                               'y' if reg.is_access else 'n', reg.init_val))
                else:
                    reg = err_reg[1]
                    print("> ", pattern.format(reg.name.lower().ljust(max_reg_len),
                                               reg.addr, reg.msb, reg.lsb, 
                                               's' if reg.is_signed else 'u',
                                               'y' if reg.is_access else 'n', reg.init_val))

            print("   {}".format('=' * (max_reg_len + 44)))
    #}}}
#}}}

### Main Function ###

def main():
    """Main function"""  #{{{
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description=textwrap.dedent('''
                Programming reference table comparer.
                '''))

    parser.add_argument('l_type', metavar='left_type', choices=['txt', 'xlsx'], 
                                    help="left table type (option: txt/xlsx)") 
    parser.add_argument('r_type', metavar='right_type', choices=['txt', 'xlsx'], 
                                    help="right table type (option: txt/xlsx)") 
    parser.add_argument('l_table_fp', metavar='left_table',
                                    help="left reference table") 
    parser.add_argument('r_table_fp', metavar='right_table',
                                    help="right reference table") 

    parser.add_argument('-s', dest='is_sign_ignore', action='store_true', 
                                help="ignore register sign check")
    parser.add_argument('-a', dest='is_access_ignore', action='store_true', 
                                help="ignore register access check")

    args, args_dbg = parser.parse_known_args()

    parser_dbg = argparse.ArgumentParser()
    parser_dbg.add_argument('--dbg', dest='debug_mode', metavar='<pattern>',
                                        help="debug mode (tag: t)")

    args_dbg = parser_dbg.parse_known_args(args_dbg)[0]

    debug_mode = set()
    try:
        for i in range(len(args_dbg.debug_mode)):
            debug_mode.add(args_dbg.debug_mode[i])
    except Exception:
        pass

    # Compare register table

    l_table = CompareTable(args.l_table_fp, args.l_type, args.is_sign_ignore, args.is_access_ignore)
    r_table = CompareTable(args.r_table_fp, args.r_type, args.is_sign_ignore, args.is_access_ignore)
    l_table == r_table
#}}}

if __name__ == '__main__':
    sys.exit(main())
