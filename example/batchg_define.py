# SPDX-License-Identifier: GPL-2.0-only
#
# Define pattern generator
#
# Copyright (C) 2022 Yeh, Hsin-Hsien <yhh76227@gmail.com>
#
class TestPlan1:
#{{{
    PAT_NAME = "test_plan1"
    REF_DIR = "batchg_sample"
    REF_INI = "age_reg.ini"
    OUT_PAT = "age_reg.pat"

    @classmethod
    def pat_gen(cls) -> list:
        ## return: [(pat_name, mod_regs), ...]
        ## mod_regs: {reg_name: value, ...}

        mod_pat_list = []
        for idx in range(10):
            mod_regs = {}
            mod_regs['group1_var2_2'] = 100 + 10 * idx
            mod_pat_list.append((f"{cls.PAT_NAME}-{idx}", mod_regs))
        return mod_pat_list
#}}}

class TestPlan2:
#{{{
    PAT_NAME = "test_plan2"
    REF_DIR = "batchg_sample"
    REF_INI = "age_reg.ini"
    OUT_PAT = "age_reg.pat"

    @classmethod
    def pat_gen(cls) -> list:
        ## return: [(pat_name, mod_regs), ...]
        ## mod_regs: {reg_name: value, ...}

        mod_pat_list = []
        for idx in range(1, 11):
            mod_regs = {}
            mod_regs['group1_var2_1'] = 200 + 10 * idx
            mod_pat_list.append((f"{cls.PAT_NAME}-{idx}", mod_regs))
        return mod_pat_list
#}}}

## pat_grp = [(pattern_class, is_enable), ...]

pat_grp = [
    (TestPlan1, True),
    (TestPlan2, False)
]
