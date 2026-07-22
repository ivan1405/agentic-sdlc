"""Allows `python -m asdlc` — the no-install path for CI runners."""
from asdlc.cli import main

raise SystemExit(main())
