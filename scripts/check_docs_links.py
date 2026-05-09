from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote


REPO_ROOT = Path(__file__).resolve().parents[1]
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)|!\[[^\]]*\]\(([^)]+)\)")
FENCE_RE = re.compile(r"```.*?```", re.DOTALL)


def main() -> int:
    files = sorted(REPO_ROOT.glob("README*.md"))
    files.extend(sorted((REPO_ROOT / "docs").glob("**/*.md")))
    files.extend(sorted((REPO_ROOT / "examples").glob("**/*.md")))

    failures: list[str] = []
    for path in files:
        if not path.exists():
            failures.append(f"Missing scanned file: {relative(path)}")
            continue
        text = FENCE_RE.sub("", path.read_text(encoding="utf-8"))
        for match in LINK_RE.finditer(text):
            target = (match.group(1) or match.group(2) or "").strip()
            target = target.split()[0] if target.startswith("<") else target
            target = target.strip("<>")
            if should_ignore(target):
                continue
            link_path = unquote(target.split("#", 1)[0])
            resolved = (path.parent / link_path).resolve()
            try:
                resolved.relative_to(REPO_ROOT)
            except ValueError:
                failures.append(f"{relative(path)} links outside repo: {target}")
                continue
            if not resolved.exists():
                failures.append(f"{relative(path)} has broken link: {target}")

    if failures:
        for failure in failures:
            print(failure)
        return 1
    print(f"Checked {len(files)} Markdown files; all relative links resolve.")
    return 0


def should_ignore(target: str) -> bool:
    if not target or target.startswith("#"):
        return True
    lowered = target.casefold()
    if lowered.startswith(("http://", "https://", "mailto:", "tel:")):
        return True
    if re.match(r"^[a-z][a-z0-9+.-]*:", lowered):
        return True
    return False


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


if __name__ == "__main__":
    raise SystemExit(main())
