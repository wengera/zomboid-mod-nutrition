import os
import sys

if __package__ in (None, ""):
    # `python testing/pzt <cmd>`: make the package importable, then dispatch.
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from pzt.cli import main
else:
    from .cli import main

sys.exit(main())
