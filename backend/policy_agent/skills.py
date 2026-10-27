from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"

def list_skills():
    skills = []
    for path in sorted(SKILLS_DIR.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        skills.append({"name": path.stem, "path": str(path.relative_to(SKILLS_DIR.parent)), "description": path.read_text(encoding="utf-8")[:240]})
    return skills

def get_skill(name: str):
    safe = "".join(c for c in name if c.isalnum() or c in "-_ ")
    path = (SKILLS_DIR / f"{safe}.md").resolve()
    if SKILLS_DIR.resolve() not in path.parents or not path.exists():
        raise ValueError("Unknown skill. Use list_skills first.")
    return {"name": path.stem, "content": path.read_text(encoding="utf-8")}
