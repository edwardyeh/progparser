# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2022 Yeh, Hsin-Hsien <yhh76227@gmail.com>
#
"""
Programming reference table convertor
"""
import argparse
import sys
import textwrap

from .utils.general import PROG_VERSION
from .utils.ref_table import ReferenceTable

### Class Definition ###

class RegisterTable(ReferenceTable):
    """Programming register table"""  #{{{

    def __init__(self, table_fp: str, table_type: str, debug_mode=None):
    #{{{ 
        super().__init__(debug_mode)

        if table_type == 'txt':
            self.txt_table_parser(table_fp)
        elif table_type == 'xlsx':
            self.xlsx_table_parser(table_fp)
        else:
            raise ValueError(f"Unsupported input table style '{table_type}'")
    #}}}
#}}}

### Main Function ###

def main():
    """Main function"""  #{{{
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description=textwrap.dedent("""
                Programming register table converter.
                """))

    parser.add_argument('--version', action='version', version=PROG_VERSION)

    parser.add_argument('in_type', metavar='input_type', choices=['txt', 'xlsx'],
                                    help="input type (option: txt/xlsx)") 
    parser.add_argument('out_type', metavar='output_type', choices=['txt', 'xlsx'], 
                                    help="output type (option: txt/xlsx)") 
    parser.add_argument('table_fp', metavar='table_in',
                                    help="reference table in") 

    parser.add_argument('-i', dest='is_init', action='store_true', 
                                help="create initial pattern")

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

    # Parser register table

    pat_list = RegisterTable(args.table_fp, args.in_type, debug_mode)

    # Dump register table

    if args.out_type == 'txt':
        pat_list.txt_export(args.is_init)
    else:
        pat_list.xlsx_export(args.is_init, is_rsv_ext=True)
#}}}

if __name__ == '__main__':
    sys.exit(main())
