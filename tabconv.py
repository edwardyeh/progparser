#!/usr/bin/env python3
# -*- coding: utf-8 -*-
## +FHDR=======================================================================
## Copyright (c) 2022 Hsin-Hsien Yeh (Edward Yeh).
## All rights reserved.
## ----------------------------------------------------------------------------
## Filename         : tabconv.py
## File Description : Programming reference table convertor
## ----------------------------------------------------------------------------
## Author           : Edward Yeh
## Created On       : Wed 12 Jan 2022 02:34:24 AM CST
## Format           : Python module
## ----------------------------------------------------------------------------
## Reuse Issues     : 
## ----------------------------------------------------------------------------
## Release History  : 
## -FHDR=======================================================================

import os, shutil
import argparse, textwrap
import openpyxl

from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

### Class Definition ###

class TableError(Exception):
    pass

class RegisterTable:
    """Programming register table"""

    def __init__(self, ref_fp: str, table_type: str, is_debug: bool):
    #{{{ 
        # reg_table = {addr1: reg_list1, addr2: reg_list2, ...}
        # reg_list = [tag, title, max_len, reg1, reg2, ...]
        # reg = [name, is_access, msb, lsb, init_val, comment, row_idx]

        self.is_debug = is_debug
        self.comment_sign = '#'
        self.insert_ofs = 0x80000000
        self.reg_table = {}

        if table_type == 'txt':
            self.txt_table_parser(ref_fp)
        elif table_type == 'xls':
            self.xls_table_parser(ref_fp)
        else:
            raise ValueError(f"Unsupport input table style '{table_type}'")
    #}}}

    def txt_table_parser(self, ref_fp: str):
        """Parse text style reference table"""  #{{{
        # insert_table = [insert_list1, insert_list2, ...]
        # insert_list = [tag, (addr, ), max_len, reg1, reg2, ...]

        insert_table = []
        is_insert = False
        insert_addr = self.insert_ofs

        reg_list = [None, None, 0] 
        reg_act = False
        reg_addr = 0

        with open(ref_fp, 'r') as f:
            line = f.readline()
            line_no = 1
            while line:
                toks = line.split()
                if len(toks):
                    if toks[0] == 'T:' or toks[0] == 'I:' or toks[0] == 'A:':
                        if reg_act:
                            if is_insert:
                                self.reg_table[insert_addr] = reg_list
                                insert_table.append(reg_list)
                                is_insert = False
                                insert_addr += 4
                            else:
                                self.reg_table[reg_addr] = reg_list
                            reg_list = [None, None, 0] 

                        if toks[0] == 'T:':
                            reg_list[0] = self.get_tag(toks[1], f"line: {line_no}")  # tag
                            reg_act = False
                        elif toks[0] == 'I:':
                            reg_addr = self.get_int(toks[1], f"line: {line_no}")
                            reg_list[1] = (reg_addr, )
                            reg_act = True
                            is_insert = True
                        else:
                            reg_addr = self.get_int(toks[1], f"line: {line_no}")
                            if len(toks) > 2:
                                reg_list[1] = ' '.join(toks[2:]).strip("\"\'")  # title
                            reg_act = True
                    else:
                        reg = [toks[0].upper(),                               # name
                               self.get_access(toks[1], f"line: {line_no}"),  # is_access
                               self.get_int(toks[2], f"line: {line_no}"),     # msb
                               self.get_int(toks[3], f"line: {line_no}"),     # lsb
                               self.get_int(toks[4], f"line: {line_no}")]     # init_val

                        if is_insert:
                            reg[1] = reg[1] + 'i'

                        if len(toks) > 5:
                            reg.append(' '.join(toks[5:]).strip("\"\'"))  # comment
                        else:
                            reg.append(None)

                        reg.append(None)  # row_idx is no use in this mode

                        name_len = len(reg[0])
                        if name_len > reg_list[2]:
                            reg_list[2] = name_len  # max_len
                        reg_list.append(reg)
                line = f.readline()
                line_no += 1

            if reg_act:
                if is_insert:
                    self.reg_table[insert_addr] = reg_list
                    insert_table.append(reg_list)
                else:
                    self.reg_table[reg_addr] = reg_list

            for insert_list in insert_table:
                if not insert_list[1][0] in self.reg_table:
                    raise TableError("address of insert register is unexisted in register table")
                reg_list = self.reg_table[insert_list[1][0]]
                for reg in insert_list[3:]:
                    reg_list.append(reg)

        if self.is_debug:
            print("=== REG INSERTION TABLE ===")
            for reg_list in insert_table:
                print(reg_list)
            print()
            self.show_reg_table("=== REG TABLE PARSER ===")
    #}}}

    def xls_table_parser(self, ref_fp: str):
        """Parse excel style reference table"""  #{{{
        reg_list = [None, None, 0] 
        reg_act = False
        reg_addr = 0

        wb = openpyxl.load_workbook(ref_fp, data_only=True)
        ws = wb.worksheets[0]

        addr_col = tuple(ws.iter_cols(1, 1, None, None, True))[0]
        for i in range(addr_col.index('ADDR')+1, len(addr_col)):
            row_idx = i + 1

            if addr_col[i] is not None:
                if reg_act:
                    self.reg_table[reg_addr] = reg_list

                addr = str(addr_col[i])
                if addr == 'none':
                    break
                else:
                    reg_addr = self.get_int(addr, f"row: {row_idx}")
                    reg_list = [None, None, 0]
                    title = ws.cell(row_idx, 2).value
                    if title is not None:
                        reg_list[1] = str(title).strip()  # title

            reg_val = self.get_int(str(ws.cell(row_idx, 3).value), f"row: {row_idx}")

            bits = str(ws.cell(row_idx, 4).value).split('_')
            if len(bits) > 1:
                msb = self.get_int(bits[0], f"row: {row_idx}")
                lsb = self.get_int(bits[1], f"row: {row_idx}")
            else:
                msb = lsb = self.get_int(bits[0], f"row: {row_idx}")

            toks = str(ws.cell(row_idx, 5).value).split('\n');
            reg_name = toks[0].strip().upper()

            if len(toks) == 1:
                comment = None
            else:
                for i in range(1, len(toks)):
                    toks[i] = toks[i].strip()
                comment = ', '.join(toks[1:])

            if ws.cell(row_idx, 5).font.__getattr__('color'):
                is_access = 'n'
            else:
                is_access = 'y'

            name_len = len(reg_name)
            if name_len > reg_list[2]:
                reg_list[2] = name_len  # max_len

            reg_list.append([reg_name, is_access, msb, lsb, reg_val, comment, row_idx])
            reg_act = True

        wb.close()

        if self.is_debug:
            self.show_reg_table("=== XLS TABLE PARSER ===")
    #}}}

    def txt_export(self, is_init: bool, is_rm_tag: bool, is_rm_insert: bool, is_addr_ro: bool):
        """Export text style reference table"""  #{{{
        with open('table_dump.txt', 'w') as f:
            is_first = True
            is_insert = False
            for addr, reg_list in self.reg_table.items():
                name_len = (reg_list[2] >> 2 << 2) + 4

                if reg_list[0] is not None and not is_rm_tag:
                    f.write(f'T: {reg_list[0]}\n\n')

                if type(reg_list[1]) is tuple:
                    if not is_rm_insert:
                        f.write(f'I: {hex(reg_list[1][0]):9}\n')
                    is_insert = True
                else:
                    f.write(f'A: {hex(addr):9}')
                    if reg_list[1] is not None:
                        f.write(f'"{reg_list[1]}"')
                    f.write('\n')
                    is_insert = False

                if is_insert and is_rm_insert:
                    pass
                else:
                    for reg in reg_list[3:]:
                        show_insert = not is_insert if is_rm_insert else is_insert
                        if len(reg[1]) == 2 and not show_insert:
                            pass
                        else:
                            f.write('{}{}{:<4}{:<4}{:<4}{:<12}'.format(reg[0].lower(), 
                                                                       (' ' * (name_len - len(reg[0]))),
                                                                       reg[1][0], 
                                                                       reg[2], 
                                                                       reg[3], 
                                                                       hex(reg[4])))
                            if reg[5] is not None:
                                f.write(f'"{reg[5]}"\n')
                            else:
                                f.write('\n')

                    is_first = False
                    f.write('\n')

        if is_init:
            is_first = True
            is_insert = False
            with open('reg_dump.ini', 'w') as f:
                for addr, reg_list in self.reg_table.items():
                    if reg_list[0] is not None:
                        if not is_first:
                            f.write('\n')
                        if not is_rm_tag:
                            f.write(f'{reg_list[0]}\n')
                        is_first = False

                    if type(reg_list[1]) is tuple:
                        is_insert = True
                    else:
                        is_insert = False

                    if is_insert and is_rm_insert:
                        pass
                    else:
                        show_insert = not is_insert if is_rm_insert else is_insert
                        for reg in reg_list[3:]:
                            if len(reg[1]) == 2 and not show_insert:
                                pass
                            else:
                                if reg[1][0] == 'y':
                                    f.write(f'{reg[0].lower()} = {reg[4]}')
                                    if reg[5] is not None:
                                        f.write(f'  # {reg[5]}\n')
                                    else:
                                        f.write('\n')
                                    is_first = False
    #}}}

    def xls_export(self, is_init: bool):
        """Export excel style reference table"""  #{{{
        GREY_FONT = Font(color='808080')

        GREEN_FILL = PatternFill(fill_type='solid', start_color='92d050')
        GREY_FILL = PatternFill(fill_type='solid', start_color='dddddd')
        ORANGE_FILL = PatternFill(fill_type='solid', start_color='ffcc99')
        YELLOW_FILL = PatternFill(fill_type='solid', start_color='ffffcc')
        VIOLET_FILL = PatternFill(fill_type='solid', start_color='e6ccff')

        THIN_SIDE = Side(border_style='thin', color='000000')
        OUTER_BORDER = Border(left=THIN_SIDE, right=THIN_SIDE, top=THIN_SIDE, bottom=THIN_SIDE)

        LT_ALIGN = Alignment(horizontal='left', vertical='top', wrapText=True)
        LC_ALIGN = Alignment(horizontal='left', vertical='center', wrapText=True)
        CT_ALIGN = Alignment(horizontal='center', vertical='top', wrapText=True)
        CC_ALIGN = Alignment(horizontal='center', vertical='center', wrapText=True)
        RT_ALIGN = Alignment(horizontal='right', vertical='top', wrapText=True)
        RC_ALIGN = Alignment(horizontal='right', vertical='center', wrapText=True)

        # Initial workbook 

        wb = openpyxl.Workbook()
        ws = wb.worksheets[0]

        ws.column_dimensions['A'].width = 15.46
        ws.column_dimensions['B'].width = 41.23
        ws.column_dimensions['C'].width = 10.31
        ws.column_dimensions['D'].width = 10.31
        ws.column_dimensions['E'].width = 41.23

        for i in (1, 2):
            row = ws.row_dimensions[i]
            row.fill = VIOLET_FILL
            row.border = OUTER_BORDER
            row.alignment = CC_ALIGN

        for i in (3, 4, 5):
            row = ws.row_dimensions[i]
            row.border = OUTER_BORDER
            row.alignment = CC_ALIGN

        row = ws.row_dimensions[6]
        row.fill = GREEN_FILL
        row.border = OUTER_BORDER
        row.alignment = CC_ALIGN

        for row in ws['A1:D5']:
            for cell in row:
                cell.border = OUTER_BORDER
                cell.alignment = CC_ALIGN

        values = ['Chip', 'Eng.', 'Date']
        for row, val in enumerate(values, start=2):
            cell = ws.cell(row, 1, val)
            cell.fill = ORANGE_FILL
            cell.border = OUTER_BORDER
            cell.alignment = CC_ALIGN

        values = ['Number', 'FileName', 'Metion1', 'Metion2', 'PatternStatus']
        for row, val in enumerate(values, start=1):
            cell = ws.cell(row, 5, val)
            cell.fill = YELLOW_FILL
            cell.border = OUTER_BORDER
            cell.alignment = LC_ALIGN

        cell = ws.cell(6, 1, 'ADDR')
        cell.fill = GREEN_FILL
        cell.border = OUTER_BORDER
        cell.alignment = CC_ALIGN

        cell = ws.cell(6, 2, 'Register')
        cell.fill = GREEN_FILL 
        cell.border = OUTER_BORDER
        cell.alignment = LC_ALIGN

        cell = ws.cell(6, 3, 'INI')
        cell.fill = GREEN_FILL
        cell.border = OUTER_BORDER
        cell.alignment = RC_ALIGN

        cell = ws.cell(6, 4, 'Bits')
        cell.fill = GREEN_FILL
        cell.border = OUTER_BORDER
        cell.alignment = RC_ALIGN

        cell = ws.cell(6, 5, 'Member')
        cell.fill = GREEN_FILL
        cell.border = OUTER_BORDER
        cell.alignment = LC_ALIGN

        if is_init:
            cell = ws.cell(1, 6, 6)
            cell.fill = VIOLET_FILL
            cell.border = OUTER_BORDER
            cell.alignment = CC_ALIGN

            cell = ws.cell(2, 6, 'PAT-1')
            cell.fill = VIOLET_FILL
            cell.border = OUTER_BORDER
            cell.alignment = CC_ALIGN

        # Dump register

        row_st = row_ed = 7

        for addr in sorted(tuple(self.reg_table.keys())):
            reg_list = self.reg_table[addr]
            is_first = True

            if type(reg_list[1]) is not tuple:
                for reg in sorted(reg_list[3:], key=lambda reg: reg[3]):
                    cell_fill = YELLOW_FILL if is_first else PatternFill()

                    if is_first:
                        ws.cell(row_ed, 1, hex(addr))
                        ws.cell(row_ed, 2, reg_list[1])

                    cell = ws.cell(row_ed, 1)
                    cell.fill = cell_fill
                    cell.border = OUTER_BORDER
                    cell.alignment = CT_ALIGN

                    cell = ws.cell(row_ed, 2)
                    cell.fill = cell_fill
                    cell.border = OUTER_BORDER
                    cell.alignment = LT_ALIGN

                    cell = ws.cell(row_ed, 3, hex(reg[4]))
                    cell.fill = cell_fill
                    cell.border = OUTER_BORDER
                    cell.alignment = RT_ALIGN

                    if reg[2] == reg[3]:
                        cell = ws.cell(row_ed, 4, str(reg[2]))
                    else:
                        cell = ws.cell(row_ed, 4, '_'.join([str(reg[2]), str(reg[3])]))

                    cell.fill = cell_fill
                    cell.border = OUTER_BORDER
                    cell.alignment = RT_ALIGN

                    cell_font = GREY_FONT if reg[1][0] == 'n' else Font()

                    if reg[0] == 'RESERVED':
                        cell = ws.cell(row_ed, 5, reg[0].lower())
                    else:
                        toks = [] if reg[5] is None else reg[5].split(',')
                        members = [reg[0]]
                        for tok in toks:
                            members.append(tok.strip())
                        cell = ws.cell(row_ed, 5, '\n'.join(members))

                    cell.font = cell_font
                    cell.fill = cell_fill
                    cell.border = OUTER_BORDER
                    cell.alignment = LT_ALIGN

                    if is_init:
                        cell = ws.cell(row_ed, 6, hex(reg[4]).upper()[2:])
                        cell.font = cell_font
                        cell.fill = cell_fill
                        cell.border = OUTER_BORDER
                        cell.alignment = CC_ALIGN

                    row = ws.row_dimensions[row_ed]
                    row.font = cell_font
                    row.fill = cell_fill
                    row.border = OUTER_BORDER
                    row.alignment = CC_ALIGN

                    row_ed += 1
                    is_first = False

        row = ws.row_dimensions[row_ed]
        row.fill = GREY_FILL
        row.border = OUTER_BORDER
        row.alignment = CC_ALIGN

        cell = ws.cell(row_ed, 1, 'none')
        cell.fill = GREY_FILL
        cell.border = OUTER_BORDER
        cell.alignment = CC_ALIGN
        row_ed += 1

        wb.save("table_dump.xlsx")
        wb.close()
    #}}}

    def get_int(self, str_: str, msg=None) -> int:
        """Convert string to integer (with HEX check)"""  #{{{
        try:
            if str_.startswith('0x') or str_.startswith('0X') :
                return int(str_, 16)
            else:
                return int(str_)
        except ValueError as e:
            if msg is None:
                raise TableError(e)
            else:
                raise TableError(f"{e} ({msg})")
    #}}}

    def get_tag(self, str_: str, msg=None) -> str:
        """Syntax check for tag"""  #{{{
        if not str_.startswith('[') or not str_.endswith(']'):
            if msg is None:
                raise TableError("tag must be included in square brackets")
            else:
                raise TableError(f"tag must be included in square brackets ({msg})")
        else:
            return str_
    #}}}

    def get_access(self, str_: str, msg=None) -> str:
        """Syntax check for access flag"""  #{{{
        str_ = str_.lower()
        if str_ != 'y' and str_ != 'n':
            if msg is None:
                raise TableError(f"access flga must be 'y' or 'n'")
            else:
                raise TableError(f"access flga must be 'y' or 'n' ({msg})")
        else:
            return str_
    #}}}

    def show_reg_table(self, comment : str):
        """Show register table"""  #{{{
        print(comment)
        for addr, reg_list in self.reg_table.items():
            print("{}".format([hex(addr)] + reg_list[0:3]))
            for reg in reg_list[3:]:
                print(f"  {reg}")
        print()
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
    parser.add_argument('ref_fp', metavar='table_in',
                                    help='reference table in') 

    parser.add_argument('-i', dest='is_init', action='store_true', 
                                help='create initial pattern')
    parser.add_argument('-rt', dest='is_rm_tag', action='store_true', 
                                help='remove tag')
    parser.add_argument('-ri', dest='is_rm_insert', action='store_true', 
                                help='rearrange insert register')

    args = parser.parse_args()

    # Parser register table

    pat_list = RegisterTable(args.ref_fp, args.in_type, is_debug)

    # Dump register table

    if args.out_type == 'txt':
        pat_list.txt_export(args.is_init, args.is_rm_tag, args.is_rm_insert, args.is_addr_ro)
    elif args.out_type == 'xls':
        pat_list.xls_export(args.is_init)
    else:
        raise TypeError(f"Unsupport output table type ({args.out_type})")
#}}}

if __name__ == '__main__':
    main(False)
else:
    pass
