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

import argparse
import copy
import math
import os
import pickle
import shutil
import sys
import textwrap
from dataclasses import dataclass
from typing import NamedTuple

import openpyxl

### Class Definition ###

class Reg(NamedTuple):
##{{{
    name: str
    addr: int
    msb: int
    lsb: int
    is_signed: bool
    is_access: bool
    init_val: int
    comment: str
    row_idx: int
##}}}

@dataclass
class RegList:
#{{{
    title: str
    regs: list
#}}}

@dataclass
class INIGroup:
#{{{ 
    tag: str
    max_len: int
    regs: list
#}}}

class Pat(NamedTuple):
##{{{
    name: str
    regs: dict
##}}}

class PatternList:
    """Programming pattern list"""  #{{{

    def __init__(self, table_fp: str, table_type: str, is_debug: bool):
    #{{{
        # reg_table = {addr1: reg_list1, addr2: reg_list2, ...}
        # ini_table = [INIGroup1, INIGroup2, ...]
        # pat_list = [pat1, pat2, ...]

        self.is_debug = is_debug
        self.comment_sign = '#'
        self.reg_table = {}
        self.ini_table = []
        self.hex_out = set()
        self.pat_list  = []

        if table_type == 'txt':
            self.txt_table_parser(table_fp)
        elif table_type == 'xls':
            self.xls_table_parser(table_fp)
        elif table_type == 'db':
            with open(table_fp, "rb") as f:
                self.reg_table = pickle.load(f)
                self.ini_table = pickle.load(f)
        else:
            raise ValueError(f"Unsupported register table type ({table_type})")
    #}}}

    def txt_table_parser(self, table_fp: str):
        """Parse text style register table"""  #{{{
        with open(table_fp, 'r') as f:
            line = f.readline()
            line_no = 1
            while line:
                toks = line.split()
                if len(toks):
                    if toks[0][0] == self.comment_sign:
                        pass
                    elif toks[0] == 'T:':
                        try:
                            tag_name = ' '.join(toks[1:]).strip("\"\'")
                            self.ini_table.append(INIGroup(tag_name, 0, []))
                        except Exception as e:
                            print("-" * 60)
                            print("TableParseError: (line: {})".format(line_no))
                            print("syntax of group descriptor:")
                            print("  'T: <tag_name>'")
                            print("-" * 60)
                            raise e
                    elif toks[0] == 'A:':
                        try:
                            addr = self.str2int(toks[1])
                            reg_list = self.reg_table.setdefault(addr, RegList(None, []))
                            reg_list.title = ' '.join(toks[2:]).strip("\"\'") if len(toks) > 2 else None
                        except Exception as e:
                            print("-" * 60)
                            print("TableParseError: (line: {})".format(line_no))
                            print("syntax of address descriptor:")
                            print("  'A: <addr> <title>'")
                            print("-" * 60)
                            raise e
                    elif toks[0] == 'H:':
                        for reg in toks[1:]:
                            if reg[0] == self.comment_sign:
                                break
                            self.hex_out.add(reg.upper())
                    else:
                        try:
                            reg_name = toks[0].upper()
                            addr = self.str2int(toks[1])
                            msb = self.str2int(toks[2])
                            lsb = self.str2int(toks[3])
                            is_signed = self.sign_check(toks[4])
                            is_access = self.access_check(toks[5])
                            init_val = self.str2int(toks[6], is_signed, msb - lsb + 1)
                            if len(toks) > 7:
                                comment = ' '.join(toks[7:])
                                comment = None if comment[0] == self.comment_sign else\
                                            comment.split(self.comment_sign)[0].strip("\"\' ")
                            else:
                                comment = None
                        except Exception as e:
                            print("-" * 70)
                            print("TableParseError: (line: {})".format(line_no))
                            print("syntax of register descriptor:")
                            print("  '<name> <addr> <msb> <lsb> <sign_type> <is_access> <init_val> [comment]'")
                            print("-" * 70)
                            raise e

                        reg = Reg(reg_name, addr, msb, lsb, is_signed, is_access, init_val, comment, None)
                        reg_list = self.reg_table.setdefault(addr, RegList(None, []))
                        reg_list.regs.append(reg)

                        if len(self.ini_table):
                            ini_grp = self.ini_table[-1]
                        else:
                            ini_grp = INIGroup(None, 0, [])
                            self.ini_table.append(ini_grp)

                        reg_len = len(reg_name)
                        if reg_len > ini_grp.max_len:
                            ini_grp.max_len = reg_len
                        ini_grp.regs.append(reg)

                line = f.readline()
                line_no += 1

        if self.is_debug:
            self.show_reg_table("=== REG TABLE PARSER ===")
            self.show_ini_table("=== INI TABLE PARSER ===")
    #}}}

    def xls_table_parser(self, table_fp: str):
        """Parse excel style reference table"""  #{{{
        wb = openpyxl.load_workbook(table_fp, data_only=True)
        ws = wb.worksheets[0]
        addr_col = tuple(ws.iter_cols(1, 1, None, None, True))[0]
        for i in range(addr_col.index('ADDR')+1, len(addr_col)):
            row_idx = i + 1
            if addr_col[i] is not None:
                addr = str(addr_col[i])
                if addr == 'none':
                    break
                else:
                    try:
                        addr = self.str2int(addr)
                    except Exception as e:
                        print("-" * 60)
                        print("ExcelParseError: (row: {})".format(row_idx))
                        print("address syntax error.")
                        print("-" * 60)
                        raise e

                    if addr in self.reg_table:
                        print("-" * 60)
                        print("ExcelParseError: (row: {})".format(row_idx))
                        print("the addess is existed in the table.")
                        print("-" * 60)
                        raise SyntaxError

                    title = ws.cell(row_idx, 2).value
                    if title is not None:
                        title = str(title).strip()
                    reg_list = RegList(title, [])
                    self.reg_table[addr] = reg_list

            try:
                bits = str(ws.cell(row_idx, 4).value).split('_')
                msb = self.str2int(bits[0])
                lsb = self.str2int(bits[1]) if len(bits) > 1 else msb
                try:
                    is_signed = ws.cell(row_idx, 3).font.__getattr__("color").rgb == "FF0000FF"
                except Exception:
                    is_signed = False
                init_val = self.str2int(str(ws.cell(row_idx, 3).value), is_signed, msb - lsb + 1)
                toks = str(ws.cell(row_idx, 5).value).split('\n')
                reg_name = toks[0].strip().upper()
                comment = None if len(toks) == 1 else ', '.join([tok.strip() for tok in toks[1:]])
            except Exception as e:
                print("-" * 60)
                print("ExcelParseError: (row: {})".format(row_idx))
                print("register syntax error (INI/Bits/Member).")
                print("-" * 60)
                raise e

            try:
                is_access = ws.cell(row_idx, 5).font.__getattr__("color").rgb != "FF808080"
            except Exception:
                is_access = True
            reg = Reg(reg_name, addr, msb, lsb, is_signed, is_access, init_val, comment, row_idx)
            reg_list.regs.append(reg)

            if len(self.ini_table):
                ini_grp = self.ini_table[-1]
            else:
                ini_grp = INIGroup(None, 0, [])
                self.ini_table.append(ini_grp)

            reg_len = len(reg_name)
            if reg_len > ini_grp.max_len:
                ini_grp.max_len = reg_len
            ini_grp.regs.append(reg)

        wb.close()

        if self.is_debug:
            self.show_reg_table("=== XLS TABLE PARSER ===")
            self.show_ini_table("=== INI TABLE PARSER ===")
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
                cfg_fps.append(tmp_fps[i].strip())
        else:
            cfg_fps.append(ini_fp)

        for cfg_fp in cfg_fps:
            pat_regs = {}
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
                        try:
                            if len(toks) and toks[1] == '=':
                                pat_regs[toks[0].upper()] = toks[2]
                        except Exception as e:
                            print("-" * 60)
                            print("INIRegParseError: (line: {})".format(line_no))
                            print("syntax of register descriptor:")
                            print("  '<reg_name> = <value> [comment]'")
                            print("-" * 60)
                            raise e
                    line = f.readline()
                    line_no += 1

            if self.is_debug:
                print(f"=== INI READ ({cfg_fp}) ===")
                for item in pat_regs.items():
                    print(item)
                print()

            pat_name = os.path.basename(cfg_fp)
            pat_name = os.path.splitext(pat_name)[0]
            self.pat_list.append(Pat(pat_name, pat_regs))
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
            pat_regs = {}
            with open(cfg_fp, 'r') as f:
                line = f.readline()
                while line:
                    addr = int(line[0:4], 16)
                    val = int(line[4:12], 16)
                    if addr in self.reg_table:
                        table_regs = self.reg_table[addr].regs
                        for reg in table_regs:
                            mask = (1 << (reg.msb - reg.lsb + 1)) - 1
                            pat_regs[reg.name] = hex((val >> reg.lsb) & mask)
                    line = f.readline()

            if self.is_debug:
                print(f"=== HEX READ ({cfg_fp}) ===")
                for item in pat_regs.items():
                    print(item)
                print()

            pat_name = os.path.basename(cfg_fp)
            pat_name = os.path.splitext(pat_name)[0]
            self.pat_list.append(Pat(pat_name, pat_regs))
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
            end = start = 6
        elif start > ws.max_column:
            end = start = ws.max_column
        else:
            end = start

        addr_col = tuple(ws.iter_cols(1, 1, None, None, True))[0]
        name_col = tuple(ws.iter_cols(5, 5, None, None, True))[0]
        row_st = addr_col.index('ADDR') + 1
        row_ed = addr_col.index('none')

        for j in range(start, end+1):
            val_col = tuple(ws.iter_cols(j, j, None, None, True))[0]
            pat_name = str(val_col[1]).strip()
            if pat_name == "None" or pat_name == "":
                continue

            try:
                if ws.cell(2, j).font.__getattr__("color").rgb == "FF808080":
                    continue
            except Exception:
                pass

            pat_regs = {}
            for i in range(row_st, row_ed):
                reg_name = name_col[i].split('\n')[0]
                reg_name = reg_name.strip().upper()
                if reg_name != 'RESERVED':
                    try:
                        pat_regs[reg_name] = "0x" + str(val_col[i])
                    except Exception as e:
                        print("-" * 60)
                        print("ExcelRegParseError: (row: {})".format(i+1))
                        print("-" * 60)
                        raise e

            if self.is_debug:
                print(f"=== XLS READ ({pat_name}) ===")
                for item in pat_regs.items():
                    print(item)
                print()

            self.pat_list.append(Pat(pat_name, pat_regs))

        wb.close()
    #}}}

    def ini_dump(self, pat_out_fp=None):
        """Dump pattern with ini format""" #{{{
        for pat in self.pat_list:
            if pat_out_fp is not None:
                pat_fp = pat_out_fp
            else:
                pat_fp = os.path.join('progp_out', pat.name + '.ini')

            with open(pat_fp, 'w') as f:
                is_first_tag = True
                for ini_grp in self.ini_table:
                    if ini_grp.tag is not None:
                        if is_first_tag:
                            is_first_tag = False
                        else:
                            f.write("\n")
                        f.write(f"[{ini_grp.tag}]\n")

                    for reg in ini_grp.regs:
                        if reg.is_access:
                            try:
                                if reg.name in pat.regs:
                                    reg_bits = reg.msb - reg.lsb + 1
                                    reg_val = self.str2int(pat.regs[reg.name], reg.is_signed, reg_bits)
                                else:
                                    reg_val = reg.init_val
                            except Exception as e:
                                print("-" * 60)
                                print("RegisterValueError:")
                                print("pattern:  {}".format(pat.name))
                                print("register: {}".format(reg.name))
                                print("-" * 60)
                                raise e

                            if reg.name in self.hex_out:
                                if reg_val > 0xffff:
                                    lens = ini_grp.max_len + 16
                                    f.write(f"{reg.name.lower()} = {reg_val:#010x}".ljust(lens))
                                else:
                                    lens = ini_grp.max_len + 12
                                    f.write(f"{reg.name.lower()} = {reg_val:#06x}".ljust(lens))
                            else:
                                lens = ini_grp.max_len + 11
                                f.write(f"{reg.name.lower()} = {reg_val}".ljust(lens))

                            if reg.comment is not None:
                                f.write(f" # {reg.comment}\n")
                            else:
                                f.write("\n")
    #}}}

    def hex_dump(self, pat_out_fp=None):
        """Dump pattern with hex format"""  #{{{
        for pat in self.pat_list:
            if pat_out_fp is not None:
                pat_fp = pat_out_fp
            else:
                pat_fp = os.path.join('progp_out', pat.name + '.pat')

            with open(pat_fp, 'w') as f:
                for addr in range(0, max(self.reg_table.keys()) + 4, 4):
                    word_val = 0
                    try:
                        for reg in self.reg_table[addr].regs:
                            bits = reg.msb - reg.lsb + 1
                            mask = (1 << bits) - 1

                            if reg.is_access and reg.name in pat.regs:
                                try:
                                    reg_val = self.str2int(pat.regs[reg.name], reg.is_signed, bits)
                                except Exception as e:
                                    print("-" * 60)
                                    print("RegisterValueError:")
                                    print("pattern:  {}".format(pat.name))
                                    print("register: {}".format(reg.name))
                                    print("-" * 60)
                                    raise e
                            else:
                                reg_val = reg.init_val

                            word_val += (reg_val & mask) << reg.lsb

                        f.write("{:04x}{:08x}\n".format(addr, word_val))
                    except Exception:
                        f.write("{:04x}{:08x}\n".format(addr, 0))
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
            str_ = ws.cell(i, 5).value
            reg_name = str_.split('\n')[0].strip()
            if reg_name.upper() == 'RESERVED':
                row = ws.row_dimensions[i]
                cell = ws.cell(i, pat_idx, 0)
                cell.font = copy.copy(row.font)
                cell.fill = copy.copy(row.fill)
                cell.border = copy.copy(row.border)
                cell.alignment = copy.copy(row.alignment)

        for pat in self.pat_list:
            for reg_list in self.reg_table.values():
                for reg in reg_list.regs:
                    bits = reg.msb - reg.lsb + 1
                    mask = (1 << bits) - 1

                    if not reg.is_access:
                        reg_val = 0
                    elif reg.name not in pat.regs:
                        reg_val = reg.init_val
                    else:
                        try:
                            reg_val = self.str2int(pat.regs[reg.name], reg.is_signed, bits)
                        except Exception as e:
                            print("-" * 60)
                            print("RegisterValueError:")
                            print("pattern:  {}".format(pat.name))
                            print("register: {}".format(reg.name))
                            print("-" * 60)
                            raise e

                    row = ws.row_dimensions[reg.row_idx]
                    cell = ws.cell(reg.row_idx, pat_idx, hex(reg_val & mask).upper()[2:])
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
            cell = ws.cell(2, pat_idx, pat.name)
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

    def str2int(self, str_: str, is_signed: bool=False, bits: int=32) -> int:
        """Convert string to integer (with HEX check)"""  #{{{
        if str_.startswith('0x') or str_.startswith('0X') :
            num = int(str_, 16)
            if num >> bits:
                raise ValueError("number overflow")
            if is_signed:
                sign = num >> (bits - 1)
                num |= ~((sign << bits) - 1)
        else:
            num = int(str_)
            if is_signed:
                bits -= 1
            if not is_signed and num < 0:
                raise ValueError("negative value founded in unsigned mode.")
            elif num > 0 and abs(num) >= (1 << bits):
                raise ValueError("number overflow")
            elif num < 0 and abs(num) > (1 << bits):
                raise ValueError("number overflow")
                
        return num
    #}}}

    def sign_check(self, str_: str) -> bool:
        """Syntax check for sign type flag"""  #{{{
        str_ = str_.lower()

        if str_ == 's':
            return True
        elif str_ == 'u':
            return False
        else:
            raise SyntaxError("sign type flag must be 's' or 'u'")
    #}}}

    def access_check(self, str_: str) -> bool:
        """Syntax check for access flag"""  #{{{
        str_ = str_.lower()

        if str_ == 'y':
            return True
        elif str_ == 'n':
            return False
        else:
            raise SyntaxError("access flag must be 'y' or 'n'")
    #}}}

    def show_reg_table(self, msg: str):
        """Show register table"""  #{{{
        print(msg)
        reg_cnt = 0
        for addr, reg_list in self.reg_table.items():
            print(f"Addr: {addr:#06x} Title: {reg_list.title}")
            for reg in reg_list.regs:
                print("  Reg:      {}, {}, {}, {}, {}, {}".format(
                    reg.name, reg.msb, reg.lsb, reg.is_signed, reg.is_access, reg.init_val))
                print("  Comment:  {}".format(reg.comment))
                print("  RowIndex: {}\n".format(reg.row_idx))
                reg_cnt += 1

        print(f"register count: {reg_cnt}\n")
    #}}}

    def show_ini_table(self, msg: str):
        """Show ini table"""  #{{{
        print(msg)
        reg_cnt = 0
        for ini_grp in self.ini_table:
            print(f"Tag: {ini_grp.tag}")
            for reg in ini_grp.regs:
                print("  {} = {}".format(
                        reg.name.ljust(ini_grp.max_len),
                        reg.init_val))
                reg_cnt += 1

        print(f"\nregister count: {reg_cnt}\n")
    #}}}

    def export_table_db(self, db_fp):
        """Export reference table dtabase (pickle type)"""  #{{{
        with open(db_fp, "wb") as f:
            pickle.dump(self.reg_table, f)
            pickle.dump(self.ini_table, f)
    #}}}
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
                to excel format by excel-style reference table is necessary.
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
    parser.add_argument('-d', dest='database_fp', metavar='<path>', type=str,
                                help=textwrap.dedent('''\
                                use pre-parsed reference table database (pickle type)'''))
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
    parser.add_argument('-p', dest='pickle_out_fp', metavar='<path>', type=str,
                                help=textwrap.dedent('''\
                                export reference table database (pickle type)'''))

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
    elif args.database_fp is not None:
        pat_list = PatternList(args.database_fp, 'db', is_debug)
    else:
        raise TypeError("missing the register table (please set -c or -x or -X)")

    ## Only dump reference table database

    if args.pickle_out_fp is not None:
        pat_list.export_table_db(args.pickle_out_fp)
        return 0

    ## Parse input pattern

    if args.in_fmt == 'ini':
        pat_list.ini_parser(args.pat_in_fp, args.is_batch, args.start_id, args.end_id) 
    elif args.in_fmt == 'hex':
        pat_list.hex_parser(args.pat_in_fp, args.is_batch, args.start_id, args.end_id)
    elif args.in_fmt == 'xls':
        # if args.xls_table_fp is None and args.xls_table_fp2 is None:
        #     raise TypeError('need an excel register table when input excel file')
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

