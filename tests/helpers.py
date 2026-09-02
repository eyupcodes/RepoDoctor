def make_healthy_repository(root):
    (root / "README.md").write_text("# Example", encoding="utf-8")
    (root / "LICENSE").write_text("Example license", encoding="utf-8")
    (root / ".gitignore").write_text(".env\n", encoding="utf-8")
    (root / "tests").mkdir()
    workflows = root / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "ci.yml").write_text("name: CI", encoding="utf-8")
