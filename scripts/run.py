"""Run project modules using local dependencies (also supports isolated embedded Python)."""
from pathlib import Path
import runpy
import sys
root = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(root), str(root / 'linking_antigravity')]
if sys.version_info < (3, 10):
    sys.path.insert(0, str(root / '.runtime/python-deps'))
module = sys.argv.pop(1)
runpy.run_module(module, run_name='__main__')
