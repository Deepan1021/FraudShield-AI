"""Static project validation: required files, syntax, JSON, forbidden constructs and frontend/backend contract."""
import _bootstrap  # noqa: F401
import json
import py_compile
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
problems = []

REQUIRED = [
    "README.md", "ARCHITECTURE.md", "API.md", "SECURITY.md", "TESTING.md", "DEPLOYMENT.md", "LICENSE", ".gitignore", ".env.example",
    "requirements.txt", "Dockerfile", "docker-compose.yml", ".dockerignore", "run.bat", "setup.bat", "run.sh",
    "backend/requirements.txt", "backend/app/main.py", "backend/app/pipeline.py",
    "backend/app/expert_system/rules/rulebase_v1.json", "backend/app/database/migrations.py",
    "frontend/package.json", "frontend/vite.config.ts", "frontend/tailwind.config.js", "frontend/index.html",
    "frontend/src/main.tsx", "frontend/src/App.tsx", "frontend/playwright.config.ts", "frontend/e2e/fraudshield.spec.ts",
    "data/sample_transactions.csv", "data/user_baselines.json", "docs/ai-engine.md", "docs/database.md",
    "scripts/init_db.py", "scripts/seed_demo.py", "scripts/reset_dev_db.py", "scripts/generate_sample_data.py",
]
for rel in REQUIRED:
    if not (ROOT / rel).is_file():
        problems.append(f"missing file: {rel}")

# Python syntax
for p in list((ROOT / "backend").rglob("*.py")) + list((ROOT / "scripts").glob("*.py")):
    try:
        py_compile.compile(str(p), doraise=True, cfile=str(Path("/tmp") / "pyc_check.pyc"))
    except py_compile.PyCompileError as exc:
        problems.append(f"syntax error: {p}: {exc.msg}")

# JSON
for p in [ROOT / "frontend/package.json", ROOT / "frontend/tsconfig.json", ROOT / "data/user_baselines.json",
          ROOT / "backend/app/expert_system/rules/rulebase_v1.json"]:
    try:
        json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        problems.append(f"invalid JSON {p}: {exc}")

# Forbidden constructs / placeholders
skip = {"verify_project.py", "test_expert_system.py"}
for p in list((ROOT / "backend").rglob("*.py")) + list((ROOT / "frontend/src").rglob("*.ts*")) + list((ROOT / "scripts").glob("*.py")):
    if p.name in skip:
        continue
    text = p.read_text(encoding="utf-8")
    if re.search(r"\b(TODO|FIXME|XXX)\b", text):
        problems.append(f"placeholder marker in {p.relative_to(ROOT)}")
    if p.suffix == ".py" and re.search(r"\b(eval|exec)\s*\(", text):
        problems.append(f"eval/exec in {p.relative_to(ROOT)}")
    if re.search(r"[A-Za-z]:\\\\Users|/home/claude", text):
        problems.append(f"machine-specific path in {p.relative_to(ROOT)}")

# Frontend <-> backend endpoint contract
api_ts = (ROOT / "frontend/src/services/api.ts").read_text(encoding="utf-8")
front = set()
for m in re.finditer(r"request<[^>]*>\('(GET|POST)',\s*[`']([^`']+)[`']", api_ts):
    path = re.sub(r"\$\{[^}]+\}", "{}", m.group(2))
    front.add((m.group(1), path))
back = set()
routes_dir = ROOT / "backend/app/api/routes"
for f in routes_dir.glob("*.py"):
    text = f.read_text(encoding="utf-8")
    prefix = (re.search(r'APIRouter\(prefix="([^"]*)"', text) or [None, ""])[1]
    for m in re.finditer(r'@router\.(get|post)\("([^"]*)"', text):
        path = "/" + (prefix + m.group(2)).strip("/")
        path = re.sub(r"\{[^}]+\}", "{}", path)
        back.add((m.group(1).upper(), path or "/"))
for method, path in sorted(front):
    norm = "/" + path.strip("/")
    if (method, norm) not in back:
        problems.append(f"frontend calls {method} {norm} but the backend has no such route")

if problems:
    print("PROJECT VALIDATION FAILED")
    for p in problems:
        print(" -", p)
    sys.exit(1)
print(f"PROJECT VALIDATION PASSED ({len(REQUIRED)} required files, {len(front)} frontend endpoints matched to backend routes)")
