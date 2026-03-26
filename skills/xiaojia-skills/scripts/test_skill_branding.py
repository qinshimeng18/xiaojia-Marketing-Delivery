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

    def test_skill_instructions_describe_login_bridge_when_api_key_missing(self):
        skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
        readme = Path(__file__).resolve().parents[1] / "README.md"
        openai_yaml = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"

        skill_text = skill_md.read_text(encoding="utf-8")
        readme_text = readme.read_text(encoding="utf-8")
        yaml_text = openai_yaml.read_text(encoding="utf-8")

        self.assertIn("If `JUSTAI_OPENAPI_API_KEY` is missing, treat that as not logged in", skill_text)
        self.assertIn("If `JUSTAI_OPENAPI_API_KEY` is missing, the skill will start the login flow", readme_text)
        self.assertIn("start the login flow instead of asking the user to paste an API key", yaml_text)


if __name__ == "__main__":
    unittest.main()
