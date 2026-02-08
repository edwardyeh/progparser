# SPDX-License-Identifier: GPL-2.0-only
#
# Copyright (C) 2022 Yeh, Hsin-Hsien <yhh76227@gmail.com>
#
import os
import sys

from progparser import progparser
from progparser.progparser import main

sys.argv[0] = os.path.basename(progparser.__file__)
sys.exit(main())

