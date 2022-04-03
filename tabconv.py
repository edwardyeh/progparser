"""
Programming reference table convertor
"""
import argparse
import os
import shutil
import sys
import textwrap

from .utils.general import str2int
from .utils.ref_table import ReferenceTable

### Class Definition ###

class RegisterTable(ReferenceTable):
    """Programming register table"""  #{{{

    def __init__(self, table_fp: str, table_type: str, is_debug: bool):
    #{{{ 
        super().__init__(is_debug)

        if table_type == 'txt':
            self.txt_table_parser(table_fp)
        elif table_type == 'xls':
            self.xls_table_parser(table_fp)
        else:
            raise ValueError(f"Unsupported input table style '{table_type}'")
    #}}}
#}}}

### Main Function ###

def main(is_debug=False):
    """Main function"""  #{{{
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description=textwrap.dedent('''
                Programming register table converter.
                '''))

    parser.add_argument('in_type', metavar='input_type', 
                                    help='input type (option: txt/xls)') 
    parser.add_argument('out_type', metavar='output_type', 
                                    help='output type (option: txt/xls)') 
    parser.add_argument('table_fp', metavar='table_in',
                                    help='reference table in') 

    parser.add_argument('-i', dest='is_init', action='store_true', 
                                help='create initial pattern')

    args = parser.parse_args()

    # Parser register table

    pat_list = RegisterTable(args.table_fp, args.in_type, is_debug)

    # Dump register table

    if args.out_type == 'txt':
        pat_list.txt_export(args.is_init)
    elif args.out_type == 'xls':
        pat_list.xls_export(args.is_init, is_rsv_ext=True)
    else:
        raise ValueError(f"Unsupported output table type ({args.out_type})")
#}}}

if __name__ == '__main__':
    sys.exit(main(False))
