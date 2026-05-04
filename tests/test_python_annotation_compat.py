"""Guard Python 3.8/3.9 imports from eager annotation evaluation."""
from __future__ import annotations

import ast
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_ROOTS = [REPO_ROOT / "src"]
RISKY_ANNOTATION_RE = re.compile(
    r"(?::|->)\s*[^#\n]*(?:\|\s*None|None\s*\||\b(?:list|dict|tuple|set)\[)"
)
FSTRING_BACKSLASH_EXPR_RE = re.compile(r"f[\"'][^\n{}]*\{[^\n{}]*\\")


def _has_future_annotations(tree: ast.Module) -> bool:
    body = tree.body
    if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant):
        if isinstance(body[0].value.value, str):
            body = body[1:]
    return bool(
        body
        and isinstance(body[0], ast.ImportFrom)
        and body[0].module == "__future__"
        and any(alias.name == "annotations" for alias in body[0].names)
    )


def test_pep604_or_builtin_generics_are_postponed_for_py39_imports():
    offenders: list[str] = []
    for root in PRODUCTION_ROOTS:
        for path in sorted(root.rglob("*.py")):
            text = path.read_text(encoding="utf-8-sig")
            if not RISKY_ANNOTATION_RE.search(text):
                continue
            tree = ast.parse(text, filename=str(path))
            if not _has_future_annotations(tree):
                offenders.append(str(path.relative_to(REPO_ROOT)))

    assert not offenders, "missing `from __future__ import annotations`: " + ", ".join(offenders)


def test_f_strings_do_not_require_python312_expression_parsing():
    offenders: list[str] = []
    for root in PRODUCTION_ROOTS:
        for path in sorted(root.rglob("*.py")):
            text = path.read_text(encoding="utf-8-sig")
            if FSTRING_BACKSLASH_EXPR_RE.search(text):
                offenders.append(str(path.relative_to(REPO_ROOT)))

    assert not offenders, "f-string expressions with backslashes require Python 3.12+: " + ", ".join(offenders)
