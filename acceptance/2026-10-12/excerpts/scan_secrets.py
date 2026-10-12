"""Compare files with actual configured credential values without printing them."""
import json
import os
import subprocess
from pathlib import Path
from goalsift.config import load_env

load_env()
proof = Path(__file__).resolve().parent
root = proof.parents[2]
keys = [os.environ.get(name, '') for name in ('DEEPSEEK_API_KEY', 'EXA_API_KEY')]
assert all(len(key) > 8 for key in keys), 'Actual credential configuration is needed for the exact-match scan'
names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=root).decode().split('\0')
paths = {root / name for name in names if name}
paths.update(proof.rglob('*'))
paths.update(root.glob('goalsift/*.py'))
paths.update(root.glob('frontend/src/*.tsx'))
paths.update(root.glob('frontend/src/*.ts'))
paths.update(root.glob('tests/*.py'))
files = sorted(path for path in paths if path.is_file() and path.name not in ('secret-scan.json', 'manifest.sha256'))
matches = [str(path.relative_to(root)) for path in files if any(key.encode() in path.read_bytes() for key in keys)]
result = {'verdict': 'FAIL' if matches else 'PASS', 'configured_credentials_checked': len(keys),
          'files_scanned': len(files), 'matched_files': matches,
          'scope': 'current tracked workspace files, new source files and this acceptance directory; excludes Git history and recovery archives'}
(proof / 'secret-scan.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
print(json.dumps(result, ensure_ascii=False))
assert not matches
