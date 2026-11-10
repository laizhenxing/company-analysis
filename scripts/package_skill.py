#!/usr/bin/env python3
"""Validate and package the six-dimension research Skill using stdlib only."""
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL_DIR = ROOT / "a-share-six-dimension-research"
OUTPUT = ROOT / "dist" / f"{SKILL_DIR.name}.skill"


def validate():
    errors = []
    skill_md = SKILL_DIR / "SKILL.md"
    if not skill_md.is_file():
        return ["缺少 a-share-six-dimension-research/SKILL.md"]
    text = skill_md.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
    if not match:
        errors.append("SKILL.md 缺少有效的 YAML frontmatter")
    else:
        frontmatter = match.group(1)
        if not re.search(r"^name:\s*a-share-six-dimension-research\s*$", frontmatter, re.M):
            errors.append("frontmatter 中的 name 缺失或与目录不一致")
        if not re.search(r"^description:\s*", frontmatter, re.M):
            errors.append("frontmatter 缺少 description")
    for relative in re.findall(r"\]\((references/[^)]+)\)", text):
        if not (SKILL_DIR / relative).is_file():
            errors.append(f"引用了不存在的资源：{relative}")
    for path in SKILL_DIR.rglob("*"):
        if path.is_file() and path.name in {"README.md", "CHANGELOG.md"}:
            errors.append(f"技能包不应包含辅助文档：{path.relative_to(SKILL_DIR)}")
        if path.is_file() and "TODO" in path.read_text(encoding="utf-8"):
            errors.append(f"仍存在 TODO：{path.relative_to(SKILL_DIR)}")
    return errors


def main():
    errors = validate()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUTPUT, "w", zipfile.ZIP_DEFLATED) as bundle:
        for path in sorted(SKILL_DIR.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                bundle.write(path, path.relative_to(ROOT))
    with zipfile.ZipFile(OUTPUT) as bundle:
        bad = bundle.testzip()
        if bad:
            print(f"ERROR: 压缩包损坏：{bad}", file=sys.stderr)
            return 1
        if f"{SKILL_DIR.name}/SKILL.md" not in bundle.namelist():
            print("ERROR: 安装包缺少 SKILL.md", file=sys.stderr)
            return 1
    print(f"已生成 {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
