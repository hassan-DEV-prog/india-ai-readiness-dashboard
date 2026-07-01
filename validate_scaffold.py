"""
Scaffold Validator
==================
Verifies that the project directory structure, configuration, and
module imports are correctly set up before any ETL pipeline runs.

Run this after cloning the repository or setting up a new environment:
    python validate_scaffold.py

Exit Codes
----------
0 : All checks passed
1 : One or more checks failed
"""

import sys
from pathlib import Path

# ── Expected Structure ────────────────────────────────────────────────────────
# Every path listed here MUST exist for the project to function.
REQUIRED_DIRS = [
    "config",
    "data/raw",
    "data/processed",
    "data/external",
    "src/etl",
    "src/features",
    "src/analysis",
    "src/visualization",
    "dashboard/pages",
    "notebooks",
    "tests",
    "logs",
    "docs",
    "images",
]

REQUIRED_FILES = [
    "config/settings.yaml",
    "config/config_loader.py",
    "config/__init__.py",
    "requirements.txt",
    "pyproject.toml",
    ".gitignore",
    ".env.example",
    "src/__init__.py",
    "src/logger.py",
    "src/etl/__init__.py",
    "src/features/__init__.py",
    "src/analysis/__init__.py",
    "src/visualization/__init__.py",
    "dashboard/__init__.py",
]


def check_structure(root: Path) -> list[str]:
    """Check all required directories and files exist."""
    failures: list[str] = []

    for d in REQUIRED_DIRS:
        path = root / d
        if not path.is_dir():
            failures.append(f"[MISSING DIR]  {d}/")

    for f in REQUIRED_FILES:
        path = root / f
        if not path.is_file():
            failures.append(f"[MISSING FILE] {f}")

    return failures


def check_config_parseable(root: Path) -> list[str]:
    """Verify settings.yaml is valid YAML and has required top-level keys."""
    failures: list[str] = []
    settings_path = root / "config" / "settings.yaml"

    if not settings_path.exists():
        return ["[CONFIG] settings.yaml not found — skipping parse check"]

    try:
        import yaml

        with settings_path.open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        required_keys = [
            "project", "paths", "data_files", "pillars",
            "weighting", "normalization", "missing_values",
            "state_name_mapping", "regions", "dashboard", "logging",
        ]
        for key in required_keys:
            if key not in cfg:
                failures.append(f"[CONFIG] Missing top-level key: '{key}'")

    except Exception as exc:
        failures.append(f"[CONFIG] Failed to parse settings.yaml: {exc}")

    return failures


def check_imports() -> list[str]:
    """Verify critical third-party packages are importable."""
    failures: list[str] = []
    packages = {
        "pandas": "pandas",
        "numpy": "numpy",
        "yaml": "PyYAML",
        "plotly": "plotly",
        "sklearn": "scikit-learn",
        "streamlit": "streamlit",
        "geopandas": "geopandas",
        "pdfplumber": "pdfplumber",
    }

    for module, pip_name in packages.items():
        try:
            __import__(module)
        except ImportError:
            failures.append(
                f"[IMPORT] Cannot import '{module}' — run: pip install {pip_name}"
            )

    return failures


def main() -> int:
    """Run all validation checks and print a summary report."""
    root = Path(__file__).parent
    all_failures: list[str] = []

    print("=" * 60)
    print("  India AI Readiness Dashboard — Scaffold Validator")
    print("=" * 60)

    # ── Check 1: Directory & File Structure ───────────────────
    print("\n[1/3] Checking project structure...")
    struct_failures = check_structure(root)
    if struct_failures:
        all_failures.extend(struct_failures)
        for f in struct_failures:
            print(f"  ✗ {f}")
    else:
        print("  ✓ All required directories and files present")

    # ── Check 2: Configuration ────────────────────────────────
    print("\n[2/3] Validating configuration...")
    config_failures = check_config_parseable(root)
    if config_failures:
        all_failures.extend(config_failures)
        for f in config_failures:
            print(f"  ✗ {f}")
    else:
        print("  ✓ settings.yaml is valid and complete")

    # ── Check 3: Package Imports ──────────────────────────────
    print("\n[3/3] Checking package imports...")
    import_failures = check_imports()
    if import_failures:
        all_failures.extend(import_failures)
        for f in import_failures:
            print(f"  ✗ {f}")
    else:
        print("  ✓ All required packages importable")

    # ── Summary ───────────────────────────────────────────────
    print("\n" + "=" * 60)
    if all_failures:
        print(f"  RESULT: {len(all_failures)} check(s) FAILED")
        print("  Fix the issues above before running the ETL pipeline.")
        print("=" * 60)
        return 1
    else:
        print("  RESULT: All checks PASSED ✓")
        print("  Project scaffold is ready. Proceed to Phase 2: ETL pipeline.")
        print("=" * 60)
        return 0


if __name__ == "__main__":
    sys.exit(main())
