# SPDX-License-Identifier: GPL-2.0-only
#
# Batch patterns gen & run
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

from .utils.general import PROG_VERSION
from .progparser import Pat, PatternList

### Class Definition ###

class BatchPatRun(PatternList):
    """Batch Pattern Gen & Run"""  #{{{

    def __init__(self, table_fp: str, table_type: str, debug_mode: set=None):
        super().__init__(table_fp, table_type, debug_mode)

    def run_group_pat(self, test_plan, bat_dir, only_type: str) -> bool:
        """Pattern parser for INI format and run"""  #{{{
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

        ## Pattern dump & run

        tmp_dir = Path('batchrun_tmp')
        pat_dir = tmp_dir / 'progp_out'
        err_dir = tmp_dir / 'error'
        cur_dir = tmp_dir / 'current'

        if tmp_dir.exists():
            Show.rmtree(tmp_dir) if tmp_dir.is_dir() else tmp_dir.unlink()
        tmp_dir.mkdir()
        pat_dir.mkdir()
        err_dir.mkdir()
        shutil.copytree(ref_dir, cur_dir, symlinks=True)

        self.ini_dump(pat_dir, info_dump=False)
        self.hex_dump(pat_dir, info_dump=False)

        out_ini_fp = Path(test_plan.OUT_PAT).stem + '.ini'
        for pat_name in mod_pat_list.keys():
            shtil.copy(pat_dir / f'{pat_name}.ini', cur_dir / out_ini_fp)
            shtil.copy(pat_dir / f'{pat_name}.pat', cur_dir / test_plan.OUT_PAT)

            is_pass = cmd_for_run(cur_dir)
            if not is_pass:
                shutil.copytree(cur_dir, err_dir / pat_name)
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
#}}}

if __name__ == '__main__':
    sys.exit(main())

