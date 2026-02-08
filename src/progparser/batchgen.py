# SPDX-License-Identifier: GPL-2.0-only
#
# Batch pattern generator
#
# Copyright (C) 2022 Yeh, Hsin-Hsien <yhh76227@gmail.com>
#
import argparse
import copy
import glob
import os
import shutil
import sys
import textwrap
from pathlib import Path

from progparser import __version__
from progparser.progparser import Pat, PatternList

PROG_VERSION = f'{Path(__file__).stem} version {__version__}'

### Class Definition ###

class BatchPatGen(PatternList):
    """Batch Pattern Generator"""  #{{{

    def __init__(self, table_fp: str, table_type: str, debug_mode: set=None):
        super().__init__(table_fp, table_type, debug_mode)

    def gen_group_pat(self, test_plan, bat_dir, only_type: str):
        """Pattern parser for INI format"""  #{{{
        ref_dir = Path(test_plan.REF_DIR)
        ref_regs = self.read_ini(ref_dir / test_plan.REF_INI)
        mod_pat_list = test_plan.pat_gen()

        ## Pattern generate

        self.pat_list = []
        for pat_name, mod_regs in mod_pat_list.items():
            pat_regs = copy.deepcopy(ref_regs)
            for reg_name, value in mod_regs.items():
                pat_regs[reg_name.upper()] = str(value)
            self.pat_list.append(Pat(pat_name, pat_regs))

            if 'p' in self.debug_mode:
                print(f"=== INI READ ({pat_name}) ===")
                for item in pat_regs.items():
                    print(item)
                print()

        ## Dump pattern

        pat_dir = Path('progp_out')
        if pat_dir.exists():
            shutil.rmtree(pat_dir) if pat_dir.is_dir() else pat_dir.unlink()
        pat_dir.mkdir()
        self.ini_dump(pat_dir, info_dump=False)
        self.hex_dump(pat_dir, info_dump=False)

        if only_type is None:
            out_ini_fp = Path(test_plan.OUT_PAT).stem + '.ini'
            for pat_name in mod_pat_list.keys():
                out_dir = bat_dir / pat_name
                if out_dir.exists():
                    shutil.rmtree(out_dir) if out_dir.is_dir() else out_dir.unlink()
                shutil.copytree(ref_dir, out_dir, symlinks=True)
                Path(out_dir, test_plan.REF_INI).unlink()
                shutil.copy(pat_dir / f"{pat_name}.ini", out_dir / out_ini_fp)
                shutil.copy(pat_dir / f"{pat_name}.pat", out_dir / test_plan.OUT_PAT)
        else:
            if only_type == 'ini':
                pat_paths = pat_dir.glob('*.ini')
            else:
                pat_paths = pat_dir.glob('*.pat')

            for pat in pat_paths:
                shutil.copy(pat, bat_dir)

        shutil.rmtree(pat_dir)
        print(f"[INFO] {test_plan.__name__} generated.")
    #}}}

    def upd_group_pat(self, test_plan, bat_dir, only_type: str):
        """Parse existed INI pattern and update"""  #{{{
        ref_dir = Path(test_plan.REF_DIR)
        mod_pat_list = test_plan.pat_gen()

        ## Pattern generate

        ref_list = []
        self.pat_list = []
        if only_type is None or only_type == 'ini':
            for ref_fp in glob.glob(test_plan.REF_DIR + '/**/*.ini', recursive=True):
                pat_name = Path(ref_fp).parts[1] if only_type is None else Path(ref_fp).stem
                if pat_name in mod_pat_list:
                    ref_list.append(ref_fp)
                    pat_regs = self.read_ini(ref_fp)
                    for reg_name, value in mod_pat_list[pat_name].items():
                        pat_regs[reg_name.upper()] = str(value)
                    self.pat_list.append(Pat(pat_name, pat_regs))
        elif only_type == 'hex':
            print('[INFO] \'Only hex type\' doesn\'t support in group update mode.')
            exit(0)

        ## Dump pattern

        pat_dir = Path('progp_out')
        if pat_dir.exists():
            shutil.rmtree(pat_dir) if pat_dir.is_dir() else pat_dir.unlink()
        pat_dir.mkdir()
        self.ini_dump(pat_dir, info_dump=False)
        self.hex_dump(pat_dir, info_dump=False)

        if only_type is None:
            out_ini_fp = Path(test_plan.OUT_PAT).stem + '.ini'
            for ref_fp in ref_list:
                pat_name = Path(ref_fp).parts[1]
                out_dir = bat_dir / pat_name
                if out_dir.exists():
                    shutil.rmtree(out_dir) if out_dir.is_dir() else out_dir.unlink()
                shutil.copytree(Path(ref_fp).parent, out_dir, symlinks=True)
                Path(out_dir, test_plan.REF_INI).unlink()
                shutil.copy(pat_dir / f"{pat_name}.ini", out_dir / out_ini_fp)
                shutil.copy(pat_dir / f"{pat_name}.pat", out_dir / test_plan.OUT_PAT)
        else:
            if only_type == 'ini':
                pat_paths = pat_dir.glob('*.ini')
            else:
                pat_paths = pat_dir.glob('*.pat')

            for pat in pat_paths:
                shutil.copy(pat, bat_dir)

        shutil.rmtree(pat_dir)
        print(f"[INFO] {test_plan.__name__} generated.")
    #}}}

    def read_ini(self, ref_ini) -> dict:
        """Read INI setting"""  #{{{
        ref_regs = {}
        with open(ref_ini, 'r') as f:
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
                            ref_regs[toks[0].upper()] = str_.split('#')[0].strip("\"\' ")
                    except Exception as e:
                        print('-' * 60)
                        print("INIRegParseError: (line: {})".format(line_no))
                        print("syntax of register descriptor:")
                        print("  '<reg_name> = <value> [comment]'")
                        print('-' * 60)
                        raise e
                line = f.readline()
                line_no += 1

        return ref_regs
    #}}}
#}}}

### Main Function ###

def main():
    """Main function""" #{{{
    parser = argparse.ArgumentParser(
            formatter_class=argparse.RawTextHelpFormatter,
            description=textwrap.dedent("""
                Batch generator of simulation patterns.
                """))

    parser.add_argument('--version', action='version', version=PROG_VERSION)

    table_gparser = parser.add_mutually_exclusive_group(required=True)
    table_gparser.add_argument('-t', dest='txt_table_fp', metavar='<path>',
                                        help="use text-style reference table")
    # table_gparser.add_argument('-x', dest='xlsx_table_fp', metavar='<path>',
    #                                     help=textwrap.dedent("""\
    #                                     use excel-style reference table (current table append)"""))
    # table_gparser.add_argument('-X', dest='xlsx_table_fp2', metavar='<path>',
    #                                     help=textwrap.dedent("""\
    #                                     use excel-style reference table (new table create)"""))

    parser.add_argument('--dir', dest='cus_dir', metavar='<path>',
                                    help="custom dump directory")
    parser.add_argument('--only', dest='only_type', metavar='<type>', choices=['ini', 'hex'],
                                    help="input format (choices: ini/hex/xlsx)") 

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

    ## Import batchgen define file

    sys.path.insert(0, '')
    try:
        import batchg_define as bd
    except ModuleNotFoundError:
        print("ModuleNotFoundError: Please create 'batchg_define' module in current directory")
        exit(1)

    ## Parser register table

    if args.txt_table_fp:
        batch_gen = BatchPatGen(args.txt_table_fp, 'txt', debug_mode)
    elif args.xlsx_table_fp:
        batch_gen = BatchPatGen(args.xlsx_table_fp, 'xlsx', debug_mode)
    elif args.xlsx_table_fp2:
        batch_gen = BatchPatGen(args.xlsx_table_fp2, 'xlsx', debug_mode)

    if args.cus_dir is not None:
        bat_dir = Path(args.cus_dir)
    else:
        bat_dir = Path('batchg_out')
        if bat_dir.exists():
            shutil.rmtree(bat_dir) if bat_dir.is_dir() else bat_dir.unlink()

    bat_dir.mkdir()

    for test_plan, is_active in bd.pat_grp:
        if is_active:
            try:
                if test_plan.UPD_MOD is True:
                    batch_gen.upd_group_pat(test_plan, bat_dir, args.only_type)
                else:
                    batch_gen.gen_group_pat(test_plan, bat_dir, args.only_type)
            except AttributeError: 
                batch_gen.gen_group_pat(test_plan, bat_dir, args.only_type)


#}}}

if __name__ == '__main__':
    sys.exit(main())

