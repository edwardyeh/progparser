# SPDX-License-Identifier: GPL-2.0-only
#
# Define pattern generator
#
# Copyright (C) 2022 Yeh, Hsin-Hsien <yhh76227@gmail.com>
#
import argparse
import copy
import shutil
import sys
import textwrap
from pathlib import Path

from .progparser import Pat, PatternList

try:
    import pattern_define as pat_def
except ModuleNotFoundError:
    print("ModuleNotFoundError: Please create 'pattern_define' module in current directory")

### Class Definition ###

class BatchPatGen(PatternList):
    """Batch Pattern Generator"""  #{{{

    def __init__(self, table_fp: str, table_type: str, debug_mode: set=None):
        super().__init__(table_fp, table_type, debug_mode)

    def ini_parser(self, ref_fp, mod_pat_list: list):
        """Pattern parser for INI format"""  #{{{
        ref_regs = {}
        with open(ref_fp, 'r') as f:
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
                            ref_regs[toks[0].upper()] = toks[2]
                    except Exception as e:
                        print('-' * 60)
                        print("INIRegParseError: (line: {})".format(line_no))
                        print("syntax of register descriptor:")
                        print("  '<reg_name> = <value> [comment]'")
                        print('-' * 60)
                        raise e
                line = f.readline()
                line_no += 1

        self.pat_list = []
        for pat_name, mod_regs in mod_pat_list:
            pat_regs = copy.deepcopy(ref_regs)
            for reg_name, value in mod_regs.items():
                pat_regs[reg_name.upper()] = str(value)
            self.pat_list.append(Pat(pat_name, pat_regs))

            if 'p' in self.debug_mode:
                print(f"=== INI READ ({pat_name}) ===")
                for item in pat_regs.items():
                    print(item)
                print()
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

    # parser.add_argument('out_fmt', metavar='format_out', choices=['ini', 'hex', 'xlsx'], 
    #                                 help="output format (choices: ini/hex/xlsx)") 

    table_gparser = parser.add_mutually_exclusive_group(required=True)
    table_gparser.add_argument('-t', dest='txt_table_fp', metavar='<path>',
                                        help="use text-style reference table")
    # table_gparser.add_argument('-x', dest='xlsx_table_fp', metavar='<path>',
    #                                     help=textwrap.dedent("""\
    #                                     use excel-style reference table (current table append)"""))
    # table_gparser.add_argument('-X', dest='xlsx_table_fp2', metavar='<path>',
    #                                     help=textwrap.dedent("""\
    #                                     use excel-style reference table (new table create)"""))

    # parser.add_argument('-f', dest='is_force', action='store_true', 
    #                                 help="force write with custom pattern dump")

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

    if args.txt_table_fp:
        batch_gen = BatchPatGen(args.txt_table_fp, 'txt', debug_mode)
    elif args.xlsx_table_fp:
        batch_gen = BatchPatGen(args.xlsx_table_fp, 'xlsx', debug_mode)
    elif args.xlsx_table_fp2:
        batch_gen = BatchPatGen(args.xlsx_table_fp2, 'xlsx', debug_mode)

    bat_dir = Path('batch_pattern')
    if bat_dir.exists():
        shutil.rmtree(bat_dir) if bat_dir.is_dir() else bat_dir.unlink()

    for test_plan, is_active in pat_def.pat_grp:
        if is_active:
            ## Pattern generate
            mod_pat_list = test_plan.pat_gen()
            ref_dir = Path(test_plan.REF_DIR)
            ref_ini = ref_dir / test_plan.REF_INI
            batch_gen.ini_parser(ref_ini, mod_pat_list)

            ## Dump pattern
            pat_dir = Path('progp_out')
            if pat_dir.exists():
                shutil.rmtree(pat_dir) if pat_dir.is_dir() else pat_dir.unlink()
            pat_dir.mkdir()
            batch_gen.hex_dump(pat_dir, info_dump=False)

            for pat_name, _ in mod_pat_list:
                out_dir = bat_dir / pat_name
                shutil.copytree(ref_dir, out_dir)
                Path(out_dir, test_plan.REF_INI).unlink()
                shutil.copy(pat_dir / f"{pat_name}.pat", out_dir / test_plan.OUT_PAT)

            shutil.rmtree(pat_dir)

#}}}

if __name__ == '__main__':
    sys.exit(main())

