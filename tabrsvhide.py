#!/usr/bin/env python3
# -*- coding: utf-8 -*-
## +FHDR=======================================================================
## Copyright (c) 2022 Hsin-Hsien Yeh (Edward Yeh).
## All rights reserved.
## ----------------------------------------------------------------------------
## Filename         : tabrsvhide.py
## File Description : Hide reserved registers in the excel-style table
## ----------------------------------------------------------------------------
## Author           : Edward Yeh
## Created On       : Fri 25 Mar 2022 01:02:54 AM CST
## Format           : Python module
## ----------------------------------------------------------------------------
## Reuse Issues     : 
## ----------------------------------------------------------------------------
## Release History  : 
## -FHDR=======================================================================

import argparse
import textwrap
import openpyxl

### Function ###

def hide_rsv_reg(table_fp):
    """Hide reserved register"""  #{{{
    wb = openpyxl.load_workbook(table_fp)
    ws = wb.worksheets[0]
    addr_col = tuple(ws.iter_cols(1, 1, None, None, True))[0]
    start_row = addr_col.index('ADDR') + 2
    end_row = addr_col.index('none') + 1
    for row_idx in range(start_row, end_row):
        if str(ws.cell(row_idx, 2).value).lower() == 'reserved':
            ws.row_dimensions[row_idx].hidden = True
    wb.save(table_fp)
    wb.close()
#}}}

### Main ###

def main():
    """Main function"""  #{{{
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description=textwrap.dedent("""
                Hide reserved registers in the excel-style table.
                """))

    parser.add_argument('table_fp', metavar='table_in', help="reference table in")
    args = parser.parse_args()
    hide_rsv_reg(args.table_fp)
#}}}

if __name__ == '__main__':
    main()
