import sys
import os
print os.environ.get(sys.argv[1], 'not set'),
