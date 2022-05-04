# SPDX-License-Identifier: GPL-2.0-only
#
# Define pattern generator
#
# Copyright (C) 2022 Yeh, Hsin-Hsien <yhh76227@gmail.com>
#
class TestPlan1:
    """Test Plan 1"""  #{{{
    REF_DIR = "batchgen"
    REF_INI = "age_reg.ini"
    OUT_PAT = "age_reg.pat"

    def pat_gen() -> list:
        """Pattern Generation"""
        # return: [(pat_name, mod_regs), ...]
        # mod_regs: {reg_name: value, ...}
        mod_pat_list = []
        for idx in range(1, 11):
            mod_regs = {}
            mod_regs['group1_var2_2'] = 100 + 10 * idx
            mod_pat_list.append((f"test_plan1-{idx}", mod_regs))
        return mod_pat_list
#}}}

class TestPlan2:
    """Test Plan 2"""  #{{{
    REF_DIR = "batchgen"
    REF_INI = "age_reg.ini"
    OUT_PAT = "age_reg.pat"

    def pat_gen() -> list:
        """Pattern Generation"""
        # return: [(pat_name, mod_regs), ...]
        # mod_regs: {reg_name: value, ...}
        mod_pat_list = []
        for idx in range(1, 11):
            mod_regs = {}
            mod_regs['group1_var2_1'] = 200 + 10 * idx
            mod_pat_list.append((f"test_plan2-{idx}", mod_regs))
        return mod_pat_list
#}}}

# pat_grp = [(pattern_class, is_enable), ...]

pat_grp = [
    (TestPlan1, True),
    (TestPlan2, True)
]
