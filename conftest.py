"""
Root conftest for pytest-django.

Ensures the inner simulador_examenes package is on sys.path so that
'config.settings' and 'apps.*' are importable when running pytest
from the project root.
"""

import sys
from pathlib import Path

# The inner package lives at <project_root>/simulador_examenes/
_inner_package = str(Path(__file__).resolve().parent / "simulador_examenes")

if _inner_package not in sys.path:
    sys.path.insert(0, _inner_package)
