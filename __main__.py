import os
import sys

from progparser import progparser
from progparser.progparser import main

sys.argv[0] = os.path.basename(progparser.__file__)
sys.exit(main())

