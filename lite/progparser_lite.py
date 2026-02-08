#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2023 Yeh, Hsin-Hsien <yhh76227@gmail.com>
#

"""
Programming Register Parser (lite 1)
====================================

Only support the ini/hex conversion. 

"""

import argparse
import os
import shutil
import sys
import textwrap

from dataclasses import dataclass, field
from pathlib import Path
from typing import NamedTuple

PROG_VERSION = '0.7.2'


##############################################################################
### Class Definition

def str2int(str_: str, is_signed: bool=False, bits: int=32) -> int:
    """Convert string to integer (with HEX check)"""
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


@dataclass (slots=True)
class Reg:
    name:      str
    type:      str
    init_val:  None
    is_access: bool
    addr:      int  = None
    msb:       int  = None
    lsb:       int  = None
    is_signed: bool = None
    comment:   str  = None
    row_idx:   int  = None
    extra:     None = None


@dataclass (slots=True)
class RegList:
    title: str  = None
    regs:  list = field(default_factory=list)


@dataclass (slots=True)
class INIGroup:
    tag:     str
    max_len: int  = 0
    regs:    list = field(default_factory=list)


class ReferenceTable:
    """Reference table for register parsing"""

    def __init__(self, debug_mode: set=None):
        # reg_table = {addr1: reg_list1, addr2: reg_list2, ...}
        # ini_table = [INIGroup1, INIGroup2, ...]
        self.debug_mode = set() if not debug_mode else debug_mode
        self.reg_table = {} 
        self.ini_table = []
        self.hex_out = set()

    def txt_table_parser(self, table_fp: str):
        """Parse text style register table"""
        with open(table_fp, 'r') as f:
            line = f.readline()
            line_no = 1
            while line:
                toks = line.split()
                if len(toks):
                    if toks[0][0] == '#':
                        pass
                    elif toks[0] == 'T:':
                        try:
                            tag_name = ' '.join(toks[1:]).split('#')[0]
                            tag_name = tag_name.strip("\"\' ")
                            self.ini_table.append(INIGroup(tag_name))
                        except Exception as e:
                            print('-' * 60)
                            print("TableParseError: (line: {})".format(line_no))
                            print("syntax of group descriptor:")
                            print("  'T: <tag_name>'")
                            print('-' * 60)
                            raise e
                    elif toks[0] == 'A:':
                        try:
                            addr = str2int(toks[1])
                            reg_list = self.reg_table.setdefault(addr, RegList())
                            if len(toks) > 2:
                                title = ' '.join(toks[2:]).split('#')[0]
                                reg_list.title = title.strip("\"\' ")
                            else:
                                reg_list.title = None
                        except Exception as e:
                            print('-' * 60)
                            print("TableParseError: (line: {})".format(line_no))
                            print("syntax of address descriptor:")
                            print("  'A: <addr> <title>'")
                            print('-' * 60)
                            raise e
                    elif toks[0] == 'H:':
                        for reg in toks[1:]:
                            if reg[0] == '#':
                                break
                            self.hex_out.add(reg.upper())
                    elif toks[0] == '<br>':
                        ini_grp.regs.append(Reg('<br>', *[None]*3))
                    else:
                        reg_name = toks[0].upper()
                        if toks[1] == 'str':
                            try:
                                quote_type = toks[2]
                                init_val = ' '.join(toks[3:])
                                if init_val[0] == '#':
                                    raise e
                                else:
                                    init_val = init_val.split('#')[0]
                                    init_val = init_val.strip("\"\' ")

                                reg = Reg(reg_name, 'str', init_val, True, 
                                          extra=quote_type)
                            except Exception as e:
                                print('-' * 70)
                                print("TableParseError: (line: {})".format(line_no))
                                print("syntax of string descriptor:")
                                print("  '<name> str <init_val> [comment]'")
                                print('-' * 70)
                                raise e
                        elif toks[1] == 'float':
                            try:
                                if len(toks) < 4:
                                    comment = None 
                                else:
                                    comment = self.txt_get_comment(' '.join(toks[3:])) 

                                reg = Reg(reg_name, 'float', float(toks[2]), True, 
                                          comment=comment)
                            except Exception as e:
                                print('-' * 70)
                                print("TableParseError: (line: {})".format(line_no))
                                print("syntax of float descriptor:")
                                print("  '<name> float <init_val> [comment]'")
                                print('-' * 70)
                                raise e
                        elif toks[1] == 'int':
                            try:
                                # msb = str2int(toks[2])
                                # lsb = str2int(toks[3])
                                # is_signed = self.sign_check(toks[4])
                                # init_val = str2int(toks[5], is_signed, msb-lsb+1)
                                if len(toks) < 4:
                                    comment = None
                                else:
                                    comment = self.txt_get_comment(' '.join(toks[3:]))

                                reg = Reg(reg_name, 'int', int(toks[2]), True, 
                                          comment=comment)
                            except Exception as e:
                                print('-' * 70)
                                print("TableParseError: (line: {})".format(line_no))
                                print("syntax of int descriptor:")
                                print("  '<name> int <msb> <lsb> <sign_type> <init_val> [comment]'")
                                print('-' * 70)
                                raise e
                        else:
                            try:
                                addr = str2int(toks[1])
                                msb = str2int(toks[2])
                                lsb = str2int(toks[3])
                                is_signed = self.sign_check(toks[4])
                                is_access = self.access_check(toks[5])
                                init_val = str2int(toks[6], is_signed, msb-lsb+1)
                                if len(toks) < 8:
                                    comment = None
                                else:
                                    comment = self.txt_get_comment(' '.join(toks[7:]))

                                reg = Reg(reg_name, 'reg', init_val, is_access, 
                                          addr=addr, msb=msb, lsb=lsb, 
                                          is_signed=is_signed, comment=comment)

                                reg_list = self.reg_table.setdefault(addr, RegList())
                                reg_list.regs.append(reg)
                            except Exception as e:
                                print('-' * 70)
                                print("TableParseError: (line: {})".format(line_no))
                                print("syntax of register descriptor:")
                                print("  '<name> <addr> <msb> <lsb> <sign_type> <is_access> <init_val> [comment]'")
                                print('-' * 70)
                                raise e

                        if len(self.ini_table):
                            ini_grp = self.ini_table[-1]
                        else:
                            ini_grp = INIGroup(None)
                            self.ini_table.append(ini_grp)

                        reg_len = len(reg_name)
                        if reg_len > ini_grp.max_len:
                            ini_grp.max_len = reg_len
                        ini_grp.regs.append(reg)

                line = f.readline()
                line_no += 1

        if 't' in self.debug_mode:
            self.show_reg_table("=== REG TABLE PARSER ===")
            self.show_ini_table("=== INI TABLE PARSER ===")

    def sign_check(self, str_: str) -> bool:
        """Syntax check for sign type flag"""
        str_ = str_.lower()

        if str_ == 's':
            return True
        elif str_ == 'u':
            return False
        else:
            raise SyntaxError("sign type flag must be 's' or 'u'")

    def access_check(self, str_: str) -> bool:
        """Syntax check for access flag"""
        str_ = str_.lower()

        if str_ == 'y':
            return True
        elif str_ == 'n':
            return False
        else:
            raise SyntaxError("access flag must be 'y' or 'n'")

    def txt_get_comment(self, str_: str) -> str:
        """Get register comment"""
        return None if str_[0] == '#' else str_.split('#')[0].strip("\"\' ")


class Pat(NamedTuple):
    name: str
    regs: dict


class PatternList(ReferenceTable):
    """Programming pattern list"""

    def __init__(self, table_fp: str, debug_mode: set=None):
        # pat_list = [pat1, pat2, ...]

        super().__init__(debug_mode)
        self.pat_list  = []
        self.txt_table_parser(table_fp)

    def ini_parser(self, ini_fp: str, is_batch=False, start=0, end=0):
        """Pattern parser for INI format"""
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
                    elif line.startswith('#'):
                        pass
                    else:
                        toks = line.split()
                        try:
                            if len(toks) and toks[1] == '=':
                                str_ = ' '.join(toks[2:])
                                pat_regs[toks[0].upper()] = str_.split('#')[0].strip("\"\' ")
                        except Exception as e:
                            print('-' * 60)
                            print("INIRegParseError: (line: {})".format(line_no))
                            print("syntax of register descriptor:")
                            print("  '<reg_name> = <value> [comment]'")
                            print('-' * 60)
                            raise e
                    line = f.readline()
                    line_no += 1

            if 'p' in self.debug_mode:
                print(f"=== INI READ ({cfg_fp}) ===")
                for item in pat_regs.items():
                    print(item)
                print()

            pat_name = os.path.basename(cfg_fp)
            pat_name = os.path.splitext(pat_name)[0]
            self.pat_list.append(Pat(pat_name, pat_regs))

    def hex_parser(self, hex_fp: str, is_batch=False, start=0, end=0):
        """Pattern parser for HEX format"""
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

            if 'p' in self.debug_mode:
                print(f"=== HEX READ ({cfg_fp}) ===")
                for item in pat_regs.items():
                    print(item)
                print()

            pat_name = os.path.basename(cfg_fp)
            pat_name = os.path.splitext(pat_name)[0]
            self.pat_list.append(Pat(pat_name, pat_regs))

    def ini_dump(self, pat_dir, pat_name=None, pat_ext=None, is_force=False, 
                 info_dump=True):
        """Dump pattern with ini format"""
        if not pat_ext:
            pat_ext = '.ini'

        pat_cnt = 0
        pat_ignore = 0
        is_batch = len(self.pat_list) > 1

        for pat in self.pat_list:
            if pat_name:
                pname = pat_name + str(pat_cnt) if is_batch else pat_name
            else:
                pname = pat.name

            pat_path = pat_dir / (pname + pat_ext)

            if pat_path.exists() and not is_force:
                if input(f"{pname+pat_ext} existed, overwrite? (y/n) ").lower() != 'y':
                    print('Ignore')
                    pat_cnt += 1
                    pat_ignore += 1
                    continue

            with open(pat_path, 'w') as f:
                is_first_tag = True
                for ini_grp in self.ini_table:
                    if ini_grp.tag is not None:
                        if is_first_tag:
                            is_first_tag = False
                        else:
                            f.write("\n")
                        f.write(f"[{ini_grp.tag}]\n")

                    for reg in ini_grp.regs:
                        if reg.name == '<br>':
                            f.write("\n")
                            continue

                        if reg.is_access:
                            try:
                                if reg.name in pat.regs:
                                    if reg.type == 'str':
                                        match reg.extra:
                                            case 's':
                                                reg_val = f"\'{pat.regs[reg.name]}\'"
                                            case 'd':
                                                reg_val = f"\"{pat.regs[reg.name]}\""
                                            case _:
                                                reg_val = pat.regs[reg.name]
                                    elif reg.type == 'float':
                                        reg_val = float(pat.regs[reg.name])
                                    elif reg.type == 'int':
                                        reg_val = int(pat.regs[reg.name])
                                    else:
                                        reg_bits = reg.msb - reg.lsb + 1
                                        reg_val = str2int(pat.regs[reg.name], 
                                                          reg.is_signed, 
                                                          reg_bits)
                                else:
                                    print(f"[Warning] '{reg.name.lower()}' is not found in pattern '{pat.name}', use default value.")
                                    if reg.type == 'str' and reg.extra == 's':
                                        reg_val = f"\'{reg.init_val}\'" 
                                    elif reg.type == 'str' and reg.extra == 'd':
                                        reg_val = f"\"{reg.init_val}\"" 
                                    else:
                                        reg_val = reg.init_val
                            except Exception as e:
                                print('-' * 60)
                                print("RegisterValueError:")
                                print("pattern:  {}".format(pat.name))
                                print("register: {}".format(reg.name))
                                print('-' * 60)
                                raise SyntaxError("RegisterValueError") 

                            if reg.name in self.hex_out:
                                mask = (1 << (reg.msb - reg.lsb + 1)) - 1
                                if -65536 <= reg_val <= 65535:
                                    reg_val &= 0xffff
                                    lens = ini_grp.max_len + 12
                                    f.write(f"{reg.name.lower()} = {reg_val:#06x}".ljust(lens))
                                else:
                                    reg_val &= 0xffffffff
                                    lens = ini_grp.max_len + 16
                                    f.write(f"{reg.name.lower()} = {reg_val:#010x}".ljust(lens))
                            else:
                                lens = ini_grp.max_len + 11
                                f.write(f"{reg.name.lower()} = {reg_val}".ljust(lens))

                            if reg.comment is not None:
                                f.write(f" # {reg.comment}\n")
                            else:
                                f.write("\n")
            pat_cnt += 1

        if info_dump:
            print()
            print(f"=== Number of pattern generated: {pat_cnt - pat_ignore}")
            print(f"=== Number of pattern ignored:   {pat_ignore}")
            print()

    def hex_dump(self, pat_dir, pat_name=None, pat_ext=None, is_force=False, 
                 info_dump=True):
        """Dump pattern with hex format"""
        if not pat_ext:
            pat_ext = '.pat'

        pat_cnt = 0
        pat_ignore = 0
        is_batch = len(self.pat_list) > 1

        for pat in self.pat_list:
            if pat_name:
                pname = pat_name + str(pat_cnt) if is_batch else pat_name
            else:
                pname = pat.name

            pat_path = pat_dir / (pname + pat_ext)

            if pat_path.exists() and not is_force:
                if input(f"{pname+pat_ext} existed, overwrite? (y/n) ").lower() != 'y':
                    print('Ignore')
                    pat_cnt += 1
                    pat_ignore += 1
                    continue

            with open(pat_path, 'w') as f:
                for addr in range(0, max(self.reg_table.keys()) + 4, 4):
                    word_val = 0
                    try:
                        for reg in self.reg_table[addr].regs:
                            bits = reg.msb - reg.lsb + 1
                            mask = (1 << bits) - 1
                            is_reg_exist = reg.name in pat.regs

                            if reg.is_access:
                                if is_reg_exist:
                                    try:
                                        reg_val = str2int(pat.regs[reg.name], 
                                                          reg.is_signed, 
                                                          bits)
                                    except Exception as e:
                                        print('-' * 60)
                                        print("RegisterValueError:")
                                        print("pattern:  {}".format(pat.name))
                                        print("register: {}".format(reg.name))
                                        print('-' * 60)
                                        raise SyntaxError("RegisterValueError") 
                                else:
                                    print(f"[Warning] '{reg.name.lower()}' is not found in pattern '{pat.name}', use default value.")
                                    reg_val = reg.init_val
                            else:
                                reg_val = reg.init_val

                            word_val += (reg_val & mask) << reg.lsb

                        f.write("{:04x}{:08x}\n".format(addr, word_val))
                    except Exception as e:
                        if str(e) == 'RegisterValueError':
                            raise e
                        f.write("{:04x}{:08x}\n".format(addr, 0))
            pat_cnt += 1

        if info_dump:
            print()
            print(f"=== Number of pattern generated: {pat_cnt - pat_ignore}")
            print(f"=== Number of pattern ignored:   {pat_ignore}")
            print()


##############################################################################
### Main Function

def main():
    """Main function"""
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description=textwrap.dedent("""
                Programming Register Parser (lite 1).

                Convert register setting between ini/hex format use the reference table.
                Output patterns will be exported to the new directory 'progp_out' by default.

                Single-source Examples:

                    @: %(prog)s ini hex table.txt reg.ini
                    
                        Convert a setting from ini to hex by text-style reference table.

                Multi-source Examples:

                    @: %(prog)s ini hex table.txt <src_list_path> -b

                        Batch mode, convert all settings in the list.

                    @: %(prog)s ini hex table.txt <src_list_path> -b -s 2 -e 5

                        Batch mode, convert settings from the 2nd row to the 5th row in the list.
                """))

    parser.add_argument('in_fmt', metavar='format_in', choices=['ini', 'hex'],
                                    help="input format (choices: ini/hex)") 
    parser.add_argument('out_fmt', metavar='format_out', choices=['ini', 'hex'], 
                                    help="output format (choices: ini/hex)") 
    parser.add_argument('txt_table_fp', metavar='table_path',
                                        help="reference table path")
    parser.add_argument('pat_in_fp', metavar='pattern_in',
                                    help="input pattern path") 

    parser.add_argument('--version', action='version', version=PROG_VERSION)

    parser.add_argument('-b', dest='is_batch', action='store_true', 
                                help="enable batch mode")
    parser.add_argument('-s', dest='start_id', metavar='<id>', type=int, default=0,
                                help="start pattern index")
    parser.add_argument('-e', dest='end_id', metavar='<id>', type=int, default=0,
                                help="end pattern index")

    parser.add_argument('-f', dest='is_force', action='store_true', 
                                    help="force write with custom pattern dump")
    parser.add_argument('--dir', dest='cus_dir', metavar='<path>',
                                    help="custom dump directory")
    parser.add_argument('--pat', dest='cus_pat', metavar='<path>',
                                    help="custom dump pattern name")
    parser.add_argument('--ext', dest='cus_ext', metavar='<ext>',
                                    help="custom dump file extension (excel ignore)")

    args, args_dbg = parser.parse_known_args()

    parser_dbg = argparse.ArgumentParser()
    parser_dbg.add_argument('--dbg', dest='debug_mode', metavar='<pattern>',
                                        help="debug mode (tag: t/p)")

    args_dbg = parser_dbg.parse_known_args(args_dbg)[0]

    debug_mode = set()
    try:
        for i in range(len(args_dbg.debug_mode)):
            debug_mode.add(args_dbg.debug_mode[i])
    except Exception:
        pass

    ## Parser register table

    pat_list = PatternList(args.txt_table_fp, debug_mode)

    ## Parse input pattern

    if args.in_fmt == 'ini':
        pat_list.ini_parser(args.pat_in_fp, args.is_batch, 
                            args.start_id, args.end_id) 
    elif args.in_fmt == 'hex':
        pat_list.hex_parser(args.pat_in_fp, args.is_batch, 
                            args.start_id, args.end_id)

    ## Dump pattern

    if not args.cus_dir:
        pat_dir = Path('progp_out')
        if pat_dir.exists():
            shutil.rmtree(pat_dir) if pat_dir.is_dir() else pat_dir.unlink()
        pat_dir.mkdir()
    else:
        if not args.is_batch:
            if (pat_dir := Path(args.cus_dir)).resolve() != Path().resolve():
                if pat_dir.exists():
                    if (not args.is_force 
                        and input("output directory existed, overwrite? (y/n) ").lower() != 'y'):
                        print('Terminated')
                        exit(0)
                    shutil.rmtree(pat_dir) if pat_dir.is_dir() else pat_dir.unlink()
                pat_dir.mkdir()
        else:
            if (pat_dir := Path(args.cus_dir)).resolve() == Path().resolve():
                print("[Error] custom dump directory can't be '.' in the batch mode.")
                exit(1)
            if pat_dir.exists():
                if (not args.is_force 
                    and input("output directory existed, overwrite? (y/n) ").lower() != 'y'):
                    print('Terminated')
                    exit(0)
                shutil.rmtree(pat_dir) if pat_dir.is_dir() else pat_dir.unlink()
            pat_dir.mkdir()

    pat_name = args.cus_pat if args.cus_pat else None

    try:
        pat_ext = '.' + args.cus_ext.split('.')[-1]
    except Exception:
        pat_ext = None

    if args.out_fmt == 'ini':
        pat_list.ini_dump(pat_dir, pat_name, pat_ext, args.is_force)
    elif args.out_fmt == 'hex':
        pat_list.hex_dump(pat_dir, pat_name, pat_ext, args.is_force)


if __name__ == '__main__':
    sys.exit(main())


