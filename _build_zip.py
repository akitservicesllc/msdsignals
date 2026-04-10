"""Build deploy.zip for Azure deployment of MSDSignals."""
import os
import zipfile

EXCLUDE_DIRS = {
    ".venv", "__pycache__", ".pytest_cache", ".git",
    "tests", "docs", ".claude", "node_modules",
    "PythonLibs", "pythonlibs", "site-packages",
}
EXCLUDE_FILES = {
    ".env", "deploy.zip", ".gitignore", "_build_zip.py",
}

root = "."
with zipfile.ZipFile("deploy.zip", "w", zipfile.ZIP_DEFLATED) as zf:
    for dirpath, dirnames, filenames in os.walk(root):
        rel_root = os.path.relpath(dirpath, root).replace("\\", "/")
        if rel_root == ".":
            rel_root = ""

        parts = rel_root.split("/") if rel_root else []
        if any(p in EXCLUDE_DIRS for p in parts):
            continue
        # Skip top-level data/ (SQLite DBs live in /home/data/ on Azure)
        if rel_root == "data":
            continue

        dirnames[:] = [
            d for d in dirnames
            if d not in EXCLUDE_DIRS and not (rel_root == "" and d == "data")
        ]

        for f in filenames:
            if f in EXCLUDE_FILES:
                continue
            if f.endswith((".pyc", ".pyo", ".db", ".db-wal", ".db-shm", ".log")):
                continue
            filepath = os.path.join(dirpath, f)
            arcname = os.path.relpath(filepath, root).replace("\\", "/")
            try:
                zf.write(filepath, arcname)
            except (ValueError, OSError) as e:
                print(f"  SKIP: {filepath} ({e})")
                continue

    names = zf.namelist()
    print(f"Created deploy.zip with {len(names)} files")
    for n in sorted(names):
        print(f"  {n}")
