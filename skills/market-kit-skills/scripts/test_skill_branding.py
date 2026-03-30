#!/usr/bin/env python3
from pathlib import Path
import unittest


class SkillBrandingTests(unittest.TestCase):
    def test_skill_metadata_uses_market_kit_branding(self):
        skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
        openai_yaml = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"

        skill_text = skill_md.read_text(encoding="utf-8")
        yaml_text = openai_yaml.read_text(encoding="utf-8")

        self.assertIn("name: market-kit-skills", skill_text)
        self.assertIn("# Market Kit Skills", skill_text)
        self.assertIn('display_name: "Market Kit Skills"', yaml_text)
        self.assertIn("marketing", yaml_text.lower())
        self.assertIn("metadata:", skill_text)
        self.assertIn("openclaw:", skill_text)

    def test_user_facing_docs_focus_on_marketing_capabilities(self):
        skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
        readme = Path(__file__).resolve().parents[1] / "README.md"
        openai_yaml = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"

        skill_text = skill_md.read_text(encoding="utf-8")
        readme_text = readme.read_text(encoding="utf-8")
        yaml_text = openai_yaml.read_text(encoding="utf-8")

        self.assertIn("营销", skill_text)
        self.assertIn("营销", readme_text)
        self.assertIn("campaign", yaml_text.lower())
        self.assertIn("小红书", skill_text)
        self.assertIn("小红书", readme_text)

    def test_user_facing_docs_hide_login_and_payment_details(self):
        skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
        readme = Path(__file__).resolve().parents[1] / "README.md"
        openai_yaml = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"

        skill_text = skill_md.read_text(encoding="utf-8")
        readme_text = readme.read_text(encoding="utf-8")
        yaml_text = openai_yaml.read_text(encoding="utf-8")
        skill_body = skill_text.split("---", 2)[-1]

        for text in (skill_body, readme_text, yaml_text):
            self.assertNotIn("JUSTAI_OPENAPI_API_KEY", text)
            self.assertNotIn("login flow", text)
            self.assertNotIn("payment", text.lower())
            self.assertNotIn("营销页", text)

    def test_skill_docs_define_timeout_rules_for_slow_generation(self):
        skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
        readme = Path(__file__).resolve().parents[1] / "README.md"
        openai_yaml = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"

        skill_text = skill_md.read_text(encoding="utf-8")
        readme_text = readme.read_text(encoding="utf-8")
        yaml_text = openai_yaml.read_text(encoding="utf-8")

        self.assertIn("300", skill_text)
        self.assertIn("300", readme_text)
        self.assertIn("running", skill_text)
        self.assertIn("running", yaml_text)
        self.assertIn("不要把轮询超时当成任务失败", skill_text)
        self.assertIn("不要把轮询超时当成任务失败", readme_text)
        self.assertIn("timeout", yaml_text.lower())

    def test_skill_docs_forbid_fabricating_results_and_require_web_url(self):
        skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
        readme = Path(__file__).resolve().parents[1] / "README.md"
        openai_yaml = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"

        skill_text = skill_md.read_text(encoding="utf-8")
        readme_text = readme.read_text(encoding="utf-8")
        yaml_text = openai_yaml.read_text(encoding="utf-8")

        self.assertIn("不要自己擅自生成", skill_text)
        self.assertIn("不要自己擅自生成", readme_text)
        self.assertIn("still generating", yaml_text)
        self.assertIn("web_url", skill_text)
        self.assertIn("web_url", readme_text)
        self.assertIn("conversation_id", yaml_text)
        self.assertIn("https://justailab.com/marketing", skill_text)
        self.assertIn("https://justailab.com/marketing", readme_text)
        self.assertIn("https://justailab.com/marketing", yaml_text)

    def test_openclaw_metadata_declares_system_managed_envs(self):
        skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
        skill_text = skill_md.read_text(encoding="utf-8")

        self.assertIn("JUSTAI_OPENAPI_API_KEY", skill_text)
        self.assertIn("JUSTAI_OPENAPI_BASE_URL", skill_text)
        self.assertIn("JUSTAI_OPENAPI_TIMEOUT", skill_text)
        self.assertIn("System-managed JustAI API key created after login", skill_text)
        self.assertIn("required: false", skill_text)
        self.assertIn("sensitive: true", skill_text)

    def test_internal_prompt_uses_agent_market_not_agent_default(self):
        openai_yaml = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"
        yaml_text = openai_yaml.read_text(encoding="utf-8")

        self.assertIn("agent_market", yaml_text)
        self.assertNotIn("agent_default", yaml_text)

    def test_installation_guidance_requires_login_first(self):
        skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
        readme = Path(__file__).resolve().parents[1] / "README.md"
        openai_yaml = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"

        skill_text = skill_md.read_text(encoding="utf-8")
        readme_text = readme.read_text(encoding="utf-8")
        yaml_text = openai_yaml.read_text(encoding="utf-8")

        self.assertIn("如果已经登录，直接继续后续营销任务", skill_text)
        self.assertIn("如果已经登录，直接进入后续营销任务", readme_text)
        self.assertIn("confirm login is complete", yaml_text)
        self.assertIn("不要先收集需求", skill_text)
        self.assertIn("也不会急着让你填一堆需求", readme_text)
        self.assertIn("before asking for requirements", yaml_text)

    def test_login_guidance_explains_automatic_api_key_setup(self):
        skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
        readme = Path(__file__).resolve().parents[1] / "README.md"
        openai_yaml = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"

        skill_text = skill_md.read_text(encoding="utf-8")
        readme_text = readme.read_text(encoding="utf-8")
        yaml_text = openai_yaml.read_text(encoding="utf-8")

        self.assertIn("不需要自己准备任何环境变量", skill_text)
        self.assertIn("不需要自己准备任何环境变量", readme_text)
        self.assertIn("不需要自己准备 API key", skill_text)
        self.assertIn("不需要自己准备 API key", readme_text)
        self.assertIn("自动创建需要的 API key", skill_text)
        self.assertIn("自动帮你创建需要的 API key", readme_text)
        self.assertIn("放到用户环境变量中", skill_text)
        self.assertIn("放到用户环境变量中", readme_text)
        self.assertIn("does not affect the user's existing content or other variables", yaml_text)

    def test_login_guidance_uses_conditional_language(self):
        skill_md = Path(__file__).resolve().parents[1] / "SKILL.md"
        readme = Path(__file__).resolve().parents[1] / "README.md"
        openai_yaml = Path(__file__).resolve().parents[1] / "agents" / "openai.yaml"

        skill_text = skill_md.read_text(encoding="utf-8")
        readme_text = readme.read_text(encoding="utf-8")
        yaml_text = openai_yaml.read_text(encoding="utf-8")

        self.assertIn("如果用户已经登录，不要重复要求登录", skill_text)
        self.assertIn("如果你已经登录，就直接继续使用，不会再反复要求你登录", readme_text)
        self.assertIn("If the user is already logged in, do not ask them to log in again", yaml_text)
        self.assertIn("如果还没有登录，再引导用户完成登录", skill_text)
        self.assertIn("如果你还没有登录，我们才会引导你完成登录", readme_text)
        self.assertIn("If the user is not logged in or the login state is still unknown, guide them through login first", yaml_text)


if __name__ == "__main__":
    unittest.main()
