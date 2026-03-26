#!/usr/bin/env python3
from pathlib import Path
import unittest


class SkillBrandingTests(unittest.TestCase):
    def test_skill_metadata_uses_xiaojia_branding(self):
        skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
        openai_yaml = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"

        skill_text = skill_md.read_text(encoding="utf-8")
        yaml_text = openai_yaml.read_text(encoding="utf-8")

        self.assertIn("name: xiaojia-skills", skill_text)
        self.assertIn("# Xiaojia Skills", skill_text)
        self.assertIn('display_name: "Xiaojia Skills"', yaml_text)
        self.assertNotIn("justai-openapi-chat", skill_text)


if __name__ == "__main__":
    unittest.main()
