#!/usr/bin/env python3
import base64
import io
import json
import os
from pathlib import Path
from types import SimpleNamespace
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import _common
import create_skill
import generate_image as generate_image_script
import list_skills
import update_skill


PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n"
    b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfeA\xdc"
    b"\xb48\x00\x00\x00\x00IEND\xaeB`\x82"
)
WEBP_BYTES = b"RIFF\x18\x00\x00\x00WEBPVP8 \x0c\x00\x00\x00/\x00\x00\x00\x10\x07\x10\x11\x11\x88\x88"


class SkillCrudScriptTests(unittest.TestCase):
    def test_resolve_prompt_content_reads_prompt_file(self):
        with TemporaryDirectory() as tmp_dir:
            prompt_path = Path(tmp_dir) / "prompt.md"
            prompt_path.write_text("# 测试 prompt\n", encoding="utf-8")

            content = _common.resolve_prompt_content(prompt_file=str(prompt_path), required=True)

        self.assertEqual(content, "# 测试 prompt\n")

    def test_resolve_prompt_content_rejects_two_prompt_sources(self):
        with self.assertRaises(SystemExit):
            _common.resolve_prompt_content(prompt_content="a", prompt_file="b")

    def test_create_skill_builds_payload(self):
        args = SimpleNamespace(
            name="自动化测试",
            description="desc",
            prompt_content="prompt",
            prompt_file="",
            thumbnail="",
            category="note",
            keywords="测试,skill",
            market_status="off",
            market_prompt_visible="false",
            load_strategy="manual",
            applicable_stage=["free_chat"],
            priority=12,
            enabled="true",
        )

        payload = create_skill.build_payload(args)

        self.assertEqual(payload["name"], "自动化测试")
        self.assertEqual(payload["prompt_content"], "prompt")
        self.assertEqual(payload["category"], "note")
        self.assertEqual(payload["applicable_stages"], ["free_chat"])
        self.assertEqual(payload["priority"], 12)
        self.assertTrue(payload["enabled"])
        self.assertFalse(payload["market_prompt_visible"])

    def test_create_skill_sends_thumbnail_file_with_create(self):
        captured = []

        def fake_open_json(request, timeout):
            body = json.loads(request.data.decode("utf-8"))
            captured.append({"url": request.full_url, "timeout": timeout, "body": body})
            return {"status": 0, "data": {"skill_id": "skill_cli_thumbnail"}}

        with TemporaryDirectory() as tmp_dir:
            thumbnail_path = Path(tmp_dir) / "cover.png"
            thumbnail_path.write_bytes(PNG_BYTES)

            argv = [
                "create_skill.py",
                "--name",
                "本地封面 Skill",
                "--description",
                "desc",
                "--prompt-content",
                "prompt",
                "--thumbnail-file",
                str(thumbnail_path),
                "--timeout",
                "300",
            ]
            with patch.dict(
                os.environ,
                {
                    "JUSTAI_OPENAPI_BASE_URL": "https://example.com",
                    "JUSTAI_OPENAPI_API_KEY": "demo-key",
                },
                clear=True,
            ), patch.object(_common, "open_json", side_effect=fake_open_json), patch.object(
                sys, "argv", argv
            ), patch(
                "builtins.print"
            ):
                exit_code = create_skill.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual([item["url"] for item in captured], ["https://example.com/openapi/skills/create"])
        create_body = captured[0]["body"]
        encoded = str(create_body["thumbnail_file_data"]).split(",", 1)[-1]
        self.assertEqual(base64.b64decode(encoded, validate=True), PNG_BYTES)
        self.assertEqual(create_body["thumbnail_file_name"], "cover.png")
        self.assertEqual(create_body["thumbnail_content_type"], "image/png")
        self.assertNotIn("thumbnail", create_body)
        self.assertEqual(create_body["prompt_content"], "prompt")
        self.assertEqual([item["timeout"] for item in captured], [300])

    def test_create_skill_sends_webp_thumbnail_file_with_create(self):
        captured = []

        def fake_open_json(request, timeout):
            body = json.loads(request.data.decode("utf-8"))
            captured.append({"url": request.full_url, "timeout": timeout, "body": body})
            return {"status": 0, "data": {"skill_id": "skill_cli_webp_thumbnail"}}

        with TemporaryDirectory() as tmp_dir:
            thumbnail_path = Path(tmp_dir) / "cover.webp"
            thumbnail_path.write_bytes(WEBP_BYTES)

            argv = [
                "create_skill.py",
                "--name",
                "本地 WebP 封面 Skill",
                "--description",
                "desc",
                "--prompt-content",
                "prompt",
                "--thumbnail-file",
                str(thumbnail_path),
                "--timeout",
                "300",
            ]
            with patch.dict(
                os.environ,
                {
                    "JUSTAI_OPENAPI_BASE_URL": "https://example.com",
                    "JUSTAI_OPENAPI_API_KEY": "demo-key",
                },
                clear=True,
            ), patch.object(_common, "open_json", side_effect=fake_open_json), patch.object(
                sys, "argv", argv
            ), patch(
                "builtins.print"
            ):
                exit_code = create_skill.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual([item["url"] for item in captured], ["https://example.com/openapi/skills/create"])
        create_body = captured[0]["body"]
        self.assertEqual(create_body["thumbnail_file_name"], "cover.webp")
        self.assertEqual(create_body["thumbnail_content_type"], "image/webp")
        self.assertTrue(create_body["thumbnail_file_data"].startswith("data:image/webp;base64,"))
        encoded = str(create_body["thumbnail_file_data"]).split(",", 1)[-1]
        self.assertEqual(base64.b64decode(encoded, validate=True), WEBP_BYTES)
        self.assertNotIn("thumbnail", create_body)
        self.assertEqual(create_body["prompt_content"], "prompt")
        self.assertEqual([item["timeout"] for item in captured], [300])

    def test_create_skill_rejects_thumbnail_url_and_file_together(self):
        with TemporaryDirectory() as tmp_dir:
            thumbnail_path = Path(tmp_dir) / "cover.png"
            thumbnail_path.write_bytes(PNG_BYTES)
            argv = [
                "create_skill.py",
                "--name",
                "互斥封面",
                "--description",
                "desc",
                "--prompt-content",
                "prompt",
                "--thumbnail",
                "https://cdn.example.com/old.png",
                "--thumbnail-file",
                str(thumbnail_path),
            ]

            stderr = io.StringIO()
            with patch.object(sys, "argv", argv), patch("sys.stderr", stderr), self.assertRaises(SystemExit):
                create_skill.main()

        self.assertRegex(stderr.getvalue(), r"--thumbnail.*--thumbnail-file|--thumbnail-file.*--thumbnail")

    def test_update_skill_requires_a_field_besides_skill_id(self):
        args = SimpleNamespace(
            skill_id="skill_x",
            name="",
            description="",
            prompt_content="",
            prompt_file="",
            thumbnail="",
            category="",
            keywords="",
            market_status="",
            review_status="",
            load_strategy="",
            applicable_stage=[],
            priority=None,
            share_prompt_visible="",
            market_prompt_visible="",
        )

        with self.assertRaises(SystemExit):
            update_skill.build_payload(args)

    def test_list_skills_builds_full_internal_query_payload(self):
        args = SimpleNamespace(
            source="personal",
            enabled="all",
            keyword="自动化",
            category="note",
            sort_by="latest",
            page=2,
            page_size=10,
            include_details=True,
            is_featured="false",
        )

        payload = list_skills.build_payload(args)

        self.assertEqual(
            payload,
            {
                "source": "personal",
                "enabled": "all",
                "keyword": "自动化",
                "category": "note",
                "sort_by": "latest",
                "page": 2,
                "page_size": 10,
                "include_details": True,
                "is_featured": False,
            },
        )

    def test_generate_image_builds_payload(self):
        self.assertEqual(generate_image_script.DEFAULT_MODEL, "image-2")

        args = SimpleNamespace(
            prompt="咖啡店开业封面",
            prompt_file="",
            model="image-2",
            pic_scale="1:1",
            template_id=2,
            req_key="",
            conversation_id="img_c1",
            negative_prompt="低清",
            max_wait_time=120,
            poll_interval=3,
            no_wait=True,
            image_url=["https://cos.justailab.xyz/media/images/reference.png"],
        )

        payload = generate_image_script.build_payload(args)

        self.assertEqual(payload["prompt"], "咖啡店开业封面")
        self.assertEqual(payload["model"], "image-2")
        self.assertEqual(payload["req_key"], "apimart-gpt-image-2")
        self.assertEqual(payload["pic_scale"], "1:1")
        self.assertEqual(payload["template_id"], 2)
        self.assertEqual(payload["conversation_id"], "img_c1")
        self.assertEqual(payload["negative_prompt"], "低清")
        self.assertFalse(payload["wait_for_completion"])
        self.assertEqual(payload["prompt_mode"], "enhanced")
        self.assertTrue(payload["idempotency_key"])
        self.assertEqual(
            payload["image_urls"],
            ["https://cos.justailab.xyz/media/images/reference.png"],
        )

    def test_generate_image_requires_prompt(self):
        args = SimpleNamespace(
            prompt="",
            prompt_file="",
            model="image-flash",
            pic_scale="3:4",
            template_id=1,
            req_key="",
            conversation_id="",
            negative_prompt="",
            max_wait_time=300,
            poll_interval=5,
            no_wait=False,
            image_url=[],
        )

        with self.assertRaises(SystemExit):
            generate_image_script.build_payload(args)

    def test_generate_image_main_submits_then_polls(self):
        argv = [
            "generate_image.py",
            "--prompt",
            "咖啡店封面",
            "--poll-interval",
            "1",
            "--timeout",
            "60",
        ]
        with patch.object(sys, "argv", argv), patch.object(
            generate_image_script,
            "openapi_generate_image",
            return_value={"status": "ok", "generation_status": "pending", "job_id": "job_x"},
        ) as submit, patch.object(
            generate_image_script,
            "openapi_image_result",
            return_value={"status": "ok", "generation_status": "completed", "job_id": "job_x"},
        ) as poll, patch.object(generate_image_script.time, "sleep"):
            exit_code = generate_image_script.main()

        self.assertEqual(exit_code, 0)
        self.assertFalse(submit.call_args.args[0]["wait_for_completion"])
        self.assertEqual(submit.call_args.kwargs["timeout"], 20)
        poll.assert_called_once_with("job_x", timeout=20)

    def test_generate_image_main_uploads_local_reference_before_submit(self):
        with TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "reference.png"
            image_path.write_bytes(PNG_BYTES)
            argv = [
                "generate_image.py",
                "--prompt",
                "保持主体不变，把背景改成海边",
                "--image-file",
                str(image_path),
                "--no-wait",
            ]
            with patch.object(sys, "argv", argv), patch.object(
                generate_image_script,
                "openapi_upload_image",
                return_value={
                    "status": "ok",
                    "url": "https://cos.justailab.xyz/media/images/reference.png",
                },
            ) as upload, patch.object(
                generate_image_script,
                "openapi_generate_image",
                return_value={
                    "status": "ok",
                    "generation_status": "pending",
                    "job_id": "job_img2img",
                },
            ) as submit:
                exit_code = generate_image_script.main()

        self.assertEqual(exit_code, 0)
        self.assertTrue(upload.call_args.args[0]["image_base64"].startswith("data:image/png;base64,"))
        self.assertEqual(
            submit.call_args.args[0]["image_urls"],
            ["https://cos.justailab.xyz/media/images/reference.png"],
        )

    def test_generate_image_main_stops_when_reference_upload_fails(self):
        with TemporaryDirectory() as tmp_dir:
            image_path = Path(tmp_dir) / "reference.png"
            image_path.write_bytes(PNG_BYTES)
            argv = [
                "generate_image.py",
                "--prompt",
                "修改背景",
                "--image-file",
                str(image_path),
            ]
            with patch.object(sys, "argv", argv), patch.object(
                generate_image_script,
                "openapi_upload_image",
                return_value={"status": "error", "message": "upload failed"},
            ), patch.object(
                generate_image_script,
                "openapi_generate_image",
            ) as submit:
                with self.assertRaisesRegex(SystemExit, "upload failed"):
                    generate_image_script.main()

        submit.assert_not_called()

    def test_generate_image_main_never_polls_after_total_deadline(self):
        argv = [
            "generate_image.py",
            "--prompt",
            "咖啡店封面",
            "--max-wait-time",
            "1",
            "--poll-interval",
            "5",
            "--timeout",
            "60",
        ]
        monotonic_values = iter([10.0, 10.0, 11.0])
        with patch.object(sys, "argv", argv), patch.object(
            generate_image_script,
            "openapi_generate_image",
            return_value={"status": "ok", "generation_status": "pending", "job_id": "job_x"},
        ), patch.object(generate_image_script, "openapi_image_result") as poll, patch.object(
            generate_image_script.time,
            "monotonic",
            side_effect=lambda: next(monotonic_values),
        ), patch.object(generate_image_script.time, "sleep") as sleep:
            exit_code = generate_image_script.main()

        self.assertEqual(exit_code, 1)
        sleep.assert_called_once_with(1.0)
        poll.assert_not_called()

    def test_generate_image_poll_timeout_is_capped_by_remaining_budget(self):
        argv = [
            "generate_image.py",
            "--prompt",
            "咖啡店封面",
            "--max-wait-time",
            "10",
            "--poll-interval",
            "3",
            "--timeout",
            "60",
        ]
        monotonic_values = iter([10.0, 10.0, 13.0])
        with patch.object(sys, "argv", argv), patch.object(
            generate_image_script,
            "openapi_generate_image",
            return_value={"status": "ok", "generation_status": "pending", "job_id": "job_x"},
        ), patch.object(
            generate_image_script,
            "openapi_image_result",
            return_value={"status": "ok", "generation_status": "completed", "job_id": "job_x"},
        ) as poll, patch.object(
            generate_image_script.time,
            "monotonic",
            side_effect=lambda: next(monotonic_values),
        ), patch.object(generate_image_script.time, "sleep"):
            exit_code = generate_image_script.main()

        self.assertEqual(exit_code, 0)
        poll.assert_called_once_with("job_x", timeout=7.0)

    def test_openapi_skill_helpers_use_expected_endpoints(self):
        captured = []

        def fake_open_json(request, timeout):
            captured.append(
                {
                    "url": request.full_url,
                    "timeout": timeout,
                    "body": json.loads(request.data.decode("utf-8")),
                    "authorization": request.headers.get("Authorization"),
                }
            )
            return {"status": 0}

        with patch.dict(
            os.environ,
            {
                "JUSTAI_OPENAPI_BASE_URL": "https://example.com",
                "JUSTAI_OPENAPI_API_KEY": "demo-key",
            },
            clear=True,
        ), patch.object(_common, "open_json", side_effect=fake_open_json):
            _common.openapi_create_skill({"name": "n"}, timeout=11)
            _common.openapi_update_skill({"skill_id": "skill_x"}, timeout=12)
            _common.openapi_get_skill("skill_x", timeout=13)
            _common.openapi_delete_skill("skill_x", timeout=14)
            _common.openapi_generate_image({"prompt": "画一张图"}, timeout=15)
            _common.openapi_upload_image({"image_base64": "data:image/png;base64,eA=="}, timeout=16)
            _common.openapi_image_result("job_x", timeout=17)

        self.assertEqual(
            [item["url"] for item in captured],
            [
                "https://example.com/openapi/skills/create",
                "https://example.com/openapi/skills/update",
                "https://example.com/openapi/skills/detail",
                "https://example.com/openapi/skills/delete",
                "https://example.com/openapi/images/generate",
                "https://example.com/openapi/images/upload",
                "https://example.com/openapi/images/result",
            ],
        )
        self.assertEqual(captured[0]["authorization"], "Bearer demo-key")
        self.assertEqual(captured[2]["body"], {"skill_id": "skill_x"})
        self.assertEqual(captured[4]["body"], {"prompt": "画一张图"})
        self.assertEqual(captured[5]["body"], {"image_base64": "data:image/png;base64,eA=="})
        self.assertEqual(captured[6]["body"], {"job_id": "job_x"})
        self.assertEqual([item["timeout"] for item in captured], [11, 12, 13, 14, 15, 16, 17])


if __name__ == "__main__":
    unittest.main()
