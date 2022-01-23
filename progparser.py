#!/usr/bin/env python3
# -*- coding: utf-8 -*-
## ============================================================================
## Copyright (c) 2021 Hsin-Hsien Yeh (Edward Yeh).
## All rights reserved.
## ----------------------------------------------------------------------------
## Filename         : progparser.py
## File Description : Programming Register Parser
## ----------------------------------------------------------------------------
## Author           : Edward Yeh
## Created On       : Sat 18 Dec 2021 11:48:41 PM CST
## Format           : Python module
## ----------------------------------------------------------------------------
## Reuse Issues     : 
## ----------------------------------------------------------------------------
## Release History  : 
##   2021/12/18 Edward Yeh : Initial version.
## ============================================================================

import os, copy, shutil, sys
import argparse, textwrap
import openpyxl

### Class Definition ###

class TableError(Exception):
    pass

class PatternError(Exception):
    pass

class PatternList:
    """Programming pattern list"""

    def __init__(self, ref_fp: str, table_type: str, is_debug: bool):
    #{{{
        # reg_table = {addr1: reg_list1, addr2: reg_list2, ...}
        # reg_list = [tag, title, max_len, reg1, reg2, ...]
        # reg = [name, is_access, msb, lsb, init_val, comment, row_idx]
        # pat_list = [[pat_name1, pat_table1], [pat_name2, pat_table2], ...]
        # pat_table = {addr1: val_list1, addr2: val_list2, ...}
        # val_list = [val1, val2, ...]

        self.is_debug = is_debug
        self.comment_sign = '#'
        self.insert_ofs = 0x80000000
        self.reg_table = {}
        self.pat_list  = []

        if table_type == 'txt':
            self.txt_table_parser(ref_fp)
        elif table_type == 'xls':
            self.xls_table_parser(ref_fp)
        else:
            raise TypeError(f"Unsupport register table type ({table_type})")
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

    def ini_parser(self, ini_fp: str, is_batch=False, start=0, end=0):
        """Pattern parser for INI format"""  #{{{
        cfg_fps = []
        if is_batch:
            with open(ini_fp, 'r') as f:
                tmp_fps = f.readlines()

            if start < 1:
                start = 1
            elif start > len(tmp_fps):
                start = len(tmp_fps)

            if end == 0 or end > len(tmp_fps):
                end = len(tmp_fps)
            elif end < start:
                end = start

            for i in range(start-1, end):
                cfg_fps.append(tmp_fps[i].rstrip())
        else:
            cfg_fps.append(ini_fp)

        for cfg_fp in cfg_fps:
            cfg = {}
            with open(cfg_fp, 'r') as f:
                line = f.readline()
                line_no = 1
                while line:
                    if line.startswith('['):
                        pass
                    elif line.startswith(self.comment_sign):
                        pass
                    else:
                        toks = line.split()
                        if len(toks) and toks[1] == '=':
                            cfg[toks[0].upper()] = self.get_int_pat(toks[2], f"line: {line_no}")
                    line = f.readline()
                    line_no += 1

            if self.is_debug:
                print(f"=== INI READ ({cfg_fp}) ===")
                for item in cfg.items():
                    print(item)
                print()

            pat_table = {}
            for addr, reg_list in self.reg_table.items():
                val_list = []
                for reg in reg_list[3:]:
                    if reg[1] == 'n':
                        val_list.append(reg[4])
                    else:
                        val_list.append(cfg.get(reg[0], reg[4])) 
                pat_table[addr] = val_list

            if self.is_debug:
                self.show_pat_content(pat_table, f"=== PAT CONTENT ({cfg_fp}) ===")

            pat_name = os.path.basename(cfg_fp)
            pat_name = os.path.splitext(pat_name)[0]
            self.pat_list.append([pat_name, pat_table])
    #}}}

    def hex_parser(self, hex_fp: str, is_batch=False, start=0, end=0):
        """Pattern parser for HEX format"""  #{{{
        cfg_fps = []
        if is_batch:
            with open(hex_fp, 'r') as f:
                tmp_fps = f.readlines()

            if start < 1:
                start = 1
            elif start > len(tmp_fps):
                start = len(tmp_fps)

            if end == 0 or end > len(tmp_fps):
                end = len(tmp_fps)
            elif end < start:
                end = start

            for i in range(start-1, end):
                cfg_fps.append(tmp_fps[i].rstrip())
        else:
            cfg_fps.append(hex_fp)

        for cfg_fp in cfg_fps:
            cfg = {}
            with open(cfg_fp, 'r') as f:
                line = f.readline()
                while line:
                    addr = int(line[0:4], 16)
                    val = int(line[4:12], 16)
                    cfg[addr] = val
                    line = f.readline()

            if self.is_debug:
                print(f"=== HEX READ ({cfg_fp}) ===")
                for key, val in cfg.items():
                    print(f"{key:#06x}: {val:#010x}")
                print()

            pat_table = {}
            for addr, reg_list in self.reg_table.items():
                val_list = []
                if addr in cfg:
                    for reg in reg_list[3:]:
                        if reg[1] == 'n':
                            val_list.append(reg[4])
                        else:
                            mask = (1 << (reg[2] - reg[3] + 1)) - 1
                            reg_val = (cfg[addr] >> reg[3]) & mask
                            val_list.append(reg_val)
                else:
                    for reg in reg_list[3:]:
                        val_list.append(reg[4])
                pat_table[addr] = val_list

            if self.is_debug:
                self.show_pat_content(pat_table, f"=== PAT CONTENT ({cfg_fp}) ===")

            pat_name = os.path.basename(cfg_fp)
            pat_name = os.path.splitext(pat_name)[0]
            self.pat_list.append([pat_name, pat_table])
    #}}}

    def xls_parser(self, xls_fp: str, is_batch=False, start=0, end=0):
        """Pattern parser for INI format"""  #{{{
        wb = openpyxl.load_workbook(xls_fp, data_only=True)
        ws = wb.worksheets[0]
        
        if is_batch:
            if start < 6:
                start = 6
            elif start > ws.max_column:
                start = ws.max_column

            if end == 0 or end > ws.max_column:
                end = ws.max_column
            elif end < start:
                end = start
        elif start < 6:
            start = end = 6
        elif start > ws.max_column:
            start = end = ws.max_column
        else:
            end = start

        addr_col = tuple(ws.iter_cols(1, 1, None, None, True))[0]
        name_col = tuple(ws.iter_cols(5, 5, None, None, True))[0]
        row_st = addr_col.index('ADDR') + 1
        row_ed = addr_col.index('none')

        for j in range(start, end+1):
            val_col = tuple(ws.iter_cols(j, j, None, None, True))[0]
            pat_name = str(val_col[1])
            cfg = {}
            for i in range(row_st, row_ed):
                reg_name = name_col[i].split('\n')[0]
                if reg_name.upper() != 'RESERVED':
                    val = self.get_int_pat(str(val_col[i]), f"row: {i+1}")
                    cfg[reg_name] = val

            if self.is_debug:
                print(f"=== XLS READ ({pat_name}) ===")
                for item in cfg.items():
                    print(item)
                print()

            pat_table = {}
            for addr, reg_list in self.reg_table.items():
                val_list = []
                for reg in reg_list[3:]:
                    if reg[1] == 'n':
                        val_list.append(reg[4])
                    else:
                        val_list.append(cfg.get(reg[0], reg[4]))
                pat_table[addr] = val_list

            if self.is_debug:
                self.show_pat_content(pat_table, f"=== PAT CONTENT ({pat_name}) ===")
                exit(0)

            self.pat_list.append([pat_name, pat_table])

        wb.close()
    #}}}

    def ini_dump(self, pat_out_fp=None):
        """Dump pattern with ini format""" #{{{
        for pat in self.pat_list:
            if pat_out_fp is not None:
                pat_fp = pat_out_fp
            else:
                pat_fp = os.path.join('progp_out', pat[0]+'.ini')

            is_first = True
            is_insert = False
            with open(pat_fp, 'w') as f:
                for addr, reg_list in self.reg_table.items():
                    if reg_list[0] is not None:
                        if not is_first:
                            f.write('\n')
                        f.write(f'{reg_list[0]}\n')
                        is_first = False

                    if type(reg_list[1]) is tuple:
                        is_insert = True
                    else:
                        is_insert = False

                    for val, reg in zip(pat[1][addr], reg_list[3:]):
                        if len(reg[1]) == 2 and not is_insert:
                            pass
                        else:
                            if reg[1][0] == 'y':
                                f.write(f"{reg[0].lower()} = {val}")
                                if reg[5] is not None:
                                    f.write(f'  # {reg[5]}\n')
                                else:
                                    f.write("\n")
                                is_first = False
    #}}}

    def hex_dump(self, pat_out_fp=None):
        """Dump pattern with hex format""" #{{{
        for pat in self.pat_list:
            if pat_out_fp is not None:
                pat_fp = pat_out_fp
            else:
                pat_fp = os.path.join('progp_out', pat[0]+'.pat')

            with open(pat_fp, 'w') as f:
                addr_list = sorted(tuple(pat[1].keys()))
                end_addr = addr_list[-1];
                for i, addr in enumerate(addr_list):
                    if addr == self.insert_ofs:
                        end_addr = addr_list[i-1] if i > 0 else addr_list[i]
                        break

                for addr in range(0, end_addr+4, 4):
                    word_val = 0
                    if addr in pat[1]:
                        for val, reg in zip(pat[1][addr], self.reg_table[addr][3:]):
                            word_val += val << reg[3]
                    f.write("{:04x}{:08x}\n".format(addr, word_val))
    #}}}

    def xls_dump(self, ref_fp : str, pat_out_fp=None, is_init=False):
        """Dump pattern with excel format""" #{{{
        wb = openpyxl.load_workbook(ref_fp)
        ws = wb.worksheets[0]

        if is_init and ws.max_column >= 6:
            ws.delete_cols(6, ws.max_column)

        pat_idx = ws.max_column + 1

        addr_col = tuple(ws.iter_cols(1, 1, None, None, True))[0]
        row_st = addr_col.index('ADDR') + 2
        row_ed = addr_col.index('none') + 1

        for i in range(row_st, row_ed):
            string = ws.cell(i, 5).value
            reg_name = string.split('\n')[0].strip()
            if reg_name.upper() == 'RESERVED':
                row = ws.row_dimensions[i]
                cell = ws.cell(i, pat_idx, 0)
                cell.font = copy.copy(row.font)
                cell.fill = copy.copy(row.fill)
                cell.border = copy.copy(row.border)
                cell.alignment = copy.copy(row.alignment)

        for pat in self.pat_list:
            for addr, reg_list in self.reg_table.items():
                for val, reg in zip(pat[1][addr], reg_list[3:]):
                    row = ws.row_dimensions[reg[6]]
                    cell = ws.cell(reg[6], pat_idx, hex(val).upper()[2:])
                    cell.font = copy.copy(row.font)
                    cell.fill = copy.copy(row.fill)
                    cell.border = copy.copy(row.border)
                    cell.alignment = copy.copy(row.alignment)

            row = ws.row_dimensions[1]
            cell = ws.cell(1, pat_idx, pat_idx)
            cell.font = copy.copy(row.font)
            cell.fill = copy.copy(row.fill)
            cell.border = copy.copy(row.border)
            cell.alignment = copy.copy(row.alignment)

            row = ws.row_dimensions[2]
            cell = ws.cell(2, pat_idx, pat[0])
            cell.font = copy.copy(row.font)
            cell.fill = copy.copy(row.fill)
            cell.border = copy.copy(row.border)
            cell.alignment = copy.copy(row.alignment)

            pat_idx += 1

        if pat_out_fp is not None:
            wb.save(pat_out_fp)
        else:
            wb.save(os.path.join('progp_out', 'register.xlsx'))

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

    def get_int_pat(self, str_: str, msg=None) -> int:
        """Convert string to integer (with HEX check)"""  #{{{
        try:
            if str_.startswith('0x') or str_.startswith('0X') :
                return int(str_, 16)
            else:
                return int(str_)
        except ValueError as e:
            if msg is None:
                raise PatternError(e)
            else:
                raise PatternError(f"{e} ({msg})")
    #}}}

    def show_pat_content(self, pat : dict, comment : str):
        """Show pattern content""" #{{{
        print(comment)
        for addr, val_list in pat.items():
            print("addr: {}".format(hex(addr)))
            print("{}".format(val_list))
        print()
    #}}}

### Main Function ###

def main(is_debug=False):
    """Main function""" #{{{
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description=textwrap.dedent('''
                Programming Register convertor.

                Convert register setting between ini/hex/excel format use the reference table.
                Output patterns will be exported to the new directory 'progp_out' by default.

                Single-source Examples:

                    @: %(prog)s -t table.txt ini hex reg.ini
                    
                        Convert a setting from ini to hex by text-style reference table.

                    @: %(prog)s -x table.xlsx ini xls reg.ini

                        Copy excel-style reference table and append a converted setting.

                    @: %(prog)s -X table.xlsx ini xls reg.ini

                        Create an empty excel reference table and append a converted setting.
                        
                Multi-source Examples:

                    @: %(prog)s -t table.txt ini hex <src_list_path> -s 2

                        Single mode, convert the setting at the 2nd row in the list.

                    @: %(prog)s -t table.txt ini hex <src_list_path> -b

                        Batch mode, convert all settings in the list.

                    @: %(prog)s -t table.txt ini hex <src_list_path> -b -s 2 -e 5

                        Batch mode, convert settings from the 2nd row to the 5th row in the list.

                    @: %(prog)s -x table.xls ini xls <src_list_path> -b -s 6 -e 8

                        Batch mode, convert settings from the 6th column to 8th column in the excel table.

                Convert between ini/hex with any format of reference table is permitted, but convert
                from/to excel format by excel-style reference table is necessary.
                '''))

    parser.add_argument('in_fmt', metavar='format_in', type=str, 
                                    help='input format (option: ini/hex/xls)') 
    parser.add_argument('out_fmt', metavar='format_out', type=str, 
                                    help='output format (option: ini/hex/xls)') 
    parser.add_argument('pat_in_fp', metavar='pattern_in', type=str, 
                                    help='input pattern path') 

    parser.add_argument('-t', dest='txt_table_fp', metavar='<path>', type=str, 
                                help='use text-style reference table')
    parser.add_argument('-x', dest='xls_table_fp', metavar='<path>', type=str,
                                help=textwrap.dedent('''\
                                use excel-style reference table 
                                (copy current table when excel out)'''))
    parser.add_argument('-X', dest='xls_table_fp2', metavar='<path>', type=str,
                                help=textwrap.dedent('''\
                                use excel-style reference table 
                                (create new table when excel out)'''))
    parser.add_argument('-b', dest='is_batch', action='store_true', 
                                help='enable batch mode')
    parser.add_argument('-s', dest='start_id', metavar='<id>', type=int, default=0,
                                help='start pattern index')
    parser.add_argument('-e', dest='end_id', metavar='<id>', type=int, default=0,
                                help='end pattern index')
    parser.add_argument('-o', dest='pat_out_fp', metavar='<path>', type=str,
                                help=textwrap.dedent('''\
                                specify output file path 
                                (ignore when ini/hex out at batch mode)'''))
    parser.add_argument('-O', dest='force_pat_out_fp', metavar='<path>', type=str,
                                help=textwrap.dedent('''\
                                specify output file path 
                                (force overwrite, ignore when ini/hex out at batch mode)'''))

    args = parser.parse_args()

    ## Parser register table

    pat_list = None
    is_init = False
    if args.txt_table_fp is not None:
        pat_list = PatternList(args.txt_table_fp, 'txt', is_debug)
    elif args.xls_table_fp is not None:
        pat_list = PatternList(args.xls_table_fp, 'xls', is_debug)
    elif args.xls_table_fp2 is not None:
        pat_list = PatternList(args.xls_table_fp2, 'xls', is_debug)
        is_init = True
    else:
        raise TypeError("missing the register table (please set -c or -x or -X)")

    ## Parse input pattern

    if args.in_fmt == 'ini':
        pat_list.ini_parser(args.pat_in_fp, args.is_batch, args.start_id, args.end_id) 
    elif args.in_fmt == 'hex':
        pat_list.hex_parser(args.pat_in_fp, args.is_batch, args.start_id, args.end_id)
    elif args.in_fmt == 'xls':
        if args.xls_table_fp is None and args.xls_table_fp2 is None:
            raise TypeError('need an excel register table when input excel file')
        pat_list.xls_parser(args.pat_in_fp, args.is_batch, args.start_id, args.end_id)
    else:
        raise ValueError(f"unknown input type ({args.in_fmt})")

    ## Dump pattern

    pat_out_fp = None
    if (args.is_batch and args.out_fmt != 'xls') or \
       (args.force_pat_out_fp is None and args.pat_out_fp is None):
        if os.path.isfile('progp_out'):
            os.remove('progp_out')
        elif os.path.isdir('progp_out'):
            shutil.rmtree('progp_out')
        os.mkdir('progp_out')
    else:
        if args.force_pat_out_fp is not None:
            pat_out_fp = args.force_pat_out_fp
        else:
            pat_out_fp = args.pat_out_fp
            if os.path.exists(args.pat_out_fp):
                ret = input("File existed, overwrite? (y/n) ")
                if ret.lower() == 'y':
                    os.remove(pat_out_fp)
                else:
                    print('Terminated')
                    exit(1)

    if args.out_fmt == 'ini':
        pat_list.ini_dump(pat_out_fp)
    elif args.out_fmt == 'hex':
        pat_list.hex_dump(pat_out_fp)
    elif args.out_fmt == 'xls':
        if args.xls_table_fp is not None:
            pat_list.xls_dump(args.xls_table_fp, pat_out_fp, is_init)
        elif args.xls_table_fp2 is not None:
            pat_list.xls_dump(args.xls_table_fp2, pat_out_fp, is_init)
        else:
            raise TypeError("need an excel register table when output excel file")
    else:
        raise ValueError(f"unknown output type ({args.out_fmt})")
#}}}

if __name__ == '__main__':
    main(False)
else:
    pass
