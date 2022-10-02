# SPDX-License-Identifier: GPL-2.0-only
#
# Define pattern generator
#
# Copyright (C) 2022 Yeh, Hsin-Hsien <yhh76227@gmail.com>
#
class TestPlan1:
#{{{
    REF_DIR = "batch_cur1"
    REF_INI = "age_reg.ini"
    OUT_PAT = "age_reg.pat"
    UPD_MOD = True          # option

    @classmethod
    def pat_gen(cls) -> list:
        ## return: {pat_name: mod_regs, ...}
        ## mod_regs: {reg_name: value, ...}
        pat_name = "test_plan1"
        mod_pat_list = {}
        for idx in range(3):
            mod_regs = {}
            mod_regs['group1_var2_1'] = 200 + 10 * idx
            mod_regs['sys_var_flt2'] = 0.1 * idx
            mod_pat_list[f"{pat_name}-{idx}"] = mod_regs
        return mod_pat_list
#}}}

class TestPlan2:
#{{{
    REF_DIR = "batch_cur1"
    REF_INI = "age_reg.ini"
    OUT_PAT = "age_reg.pat"
    UPD_MOD = True          # option

    @classmethod
    def pat_gen(cls) -> list:
        ## return: {pat_name: mod_regs, ...}
        ## mod_regs: {reg_name: value, ...}
        pat_name = "test_plan2"
        mod_pat_list = {}
        for idx in range(1, 4):
            mod_regs = {}
            mod_regs['group1_var2_1'] = 300 + 10 * idx
            mod_regs['sys_var_int2'] = -10 * idx
            mod_pat_list[f"{pat_name}-{idx}"] = mod_regs
        return mod_pat_list
#}}}

## pat_grp = [(pattern_class, is_enable), ...]

pat_grp = [
    (TestPlan1, True),
    (TestPlan2, True)
]
