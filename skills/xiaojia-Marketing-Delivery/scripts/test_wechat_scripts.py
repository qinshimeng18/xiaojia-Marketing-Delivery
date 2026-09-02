#!/usr/bin/env python3
import unittest

from sync_wechat_draft import build_draft_payload


class WechatDraftScriptTests(unittest.TestCase):
    def test_build_draft_payload_reads_note_component(self):
        result = {
            "status": "completed",
            "conversation_id": "cvt_1",
            "result": {
                "components": [
                    {
                        "type": "note",
                        "data": {
                            "title": "文章标题",
                            "content": "正文",
                            "images": [
                                {"url": "https://img.example.com/cover.jpg"},
                                "https://img.example.com/body.jpg",
                            ],
                        },
                    }
                ]
            },
        }

        payload = build_draft_payload(result, authorizer_appid="wx_1", team_id=35)

        self.assertEqual(payload["title"], "文章标题")
        self.assertEqual(payload["cover_image"], "https://img.example.com/cover.jpg")
        self.assertEqual(payload["image_urls"], [
            "https://img.example.com/cover.jpg",
            "https://img.example.com/body.jpg",
        ])
        self.assertEqual(payload["conversation_id"], "cvt_1")
        self.assertEqual(payload["authorizer_appid"], "wx_1")
        self.assertEqual(payload["team_id"], 35)

    def test_build_draft_payload_supports_nested_result(self):
        result = {
            "conversation_id": "cvt_nested",
            "result": {
                "result": {
                    "components": [
                        {
                            "type": "note",
                            "data": {
                                "title": "嵌套文章",
                                "content": "正文",
                                "cover_image": "https://img.example.com/explicit.jpg",
                                "image_urls": [],
                            },
                        }
                    ]
                }
            },
        }

        payload = build_draft_payload(result)

        self.assertEqual(payload["title"], "嵌套文章")
        self.assertEqual(payload["cover_image"], "https://img.example.com/explicit.jpg")

    def test_build_draft_payload_selects_one_based_component(self):
        result = {
            "result": {
                "components": [
                    {"type": "note", "data": {"title": "第一篇", "content": "一", "images": ["https://a/1.jpg"]}},
                    {"type": "note", "data": {"title": "第二篇", "content": "二", "images": ["https://a/2.jpg"]}},
                ]
            }
        }

        payload = build_draft_payload(result, component_index=2)

        self.assertEqual(payload["title"], "第二篇")

    def test_build_draft_payload_rejects_missing_component(self):
        with self.assertRaisesRegex(ValueError, "没有可同步"):
            build_draft_payload({"result": {}})

    def test_build_draft_payload_rejects_out_of_range_index(self):
        result = {
            "result": {
                "components": [
                    {"type": "note", "data": {"title": "第一篇", "content": "一", "images": ["https://a/1.jpg"]}},
                ]
            }
        }
        with self.assertRaisesRegex(ValueError, "超出范围"):
            build_draft_payload(result, component_index=2)


if __name__ == "__main__":
    unittest.main()
