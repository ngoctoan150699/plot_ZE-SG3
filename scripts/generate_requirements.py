import ast
import os
from pathlib import Path
import importlib.util
import importlib.metadata as md

ROOT = Path(__file__).resolve().parents[1]

exclude_dirs = {'.git', '__pycache__', 'venv', 'env', '.venv'}

modules = set()

for py in ROOT.rglob('*.py'):
    if any(part in exclude_dirs for part in py.parts):
        continue
    try:
        src = py.read_text(encoding='utf-8')
    except Exception:
        continue
    try:
        tree = ast.parse(src)
    except Exception:
        continue
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for n in node.names:
                top = n.name.split('.')[0]
                modules.add(top)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                top = node.module.split('.')[0]
                modules.add(top)

# filter builtins / stdlib by attempting to locate their spec and checking origin
third_party = set()
not_found = set()
for mod in sorted(modules):
    if mod in {'__future__'}:
        continue
    try:
        spec = importlib.util.find_spec(mod)
    except Exception:
        spec = None
    if spec is None:
        not_found.add(mod)
        continue
    origin = getattr(spec, 'origin', '') or ''
    # likely third-party if installed under site-packages or dist-packages
    is_third = False
    if origin and ('site-packages' in origin or 'dist-packages' in origin):
        is_third = True
    else:
        try:
            pdict = md.packages_distributions()
            if mod in pdict:
                is_third = True
        except Exception:
            pass

    if is_third:
        dists = []
        try:
            pdict = md.packages_distributions()
            dists = pdict.get(mod, []) if pdict else []
        except Exception:
            dists = []

        if not dists:
            guesses = [mod, mod.lower()]
            for g in guesses:
                try:
                    _v = md.version(g)
                    dists = [g]
                    break
                except Exception:
                    pass

        if dists:
            for d in dists:
                try:
                    ver = md.version(d)
                    third_party.add(f"{d}=={ver}")
                except Exception:
                    third_party.add(d)
        else:
            third_party.add(mod)

req_file = ROOT / 'requirements.txt'
with req_file.open('w', encoding='utf-8') as f:
    for pkg in sorted(third_party):
        f.write(pkg + '\n')

print('Wrote', req_file)
print('Imports scanned:', len(modules))
print('Third-party packages found:', len(third_party))
print('Some modules not resolved:', sorted(list(not_found))[:50])
