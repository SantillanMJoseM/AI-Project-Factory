import json
import os
from pathlib import Path

def detect(root):
    root = Path(root)
    techs = set()
    if (root / "backend" / "app.py").exists() or list(root.rglob("*.py")):
        techs.add("python")
    if list(root.rglob("*.html")):
        techs.add("html")
    if list(root.rglob("*.sql")):
        techs.add("sql")
    if (root / "package.json").exists():
        techs.add("node")
    return sorted(techs)

if __name__ == "__main__":
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else "."
    print(json.dumps(detect(root)))
