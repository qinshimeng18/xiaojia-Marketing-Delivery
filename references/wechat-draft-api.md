# 微信公众号绑定与草稿箱 OpenAPI

所有接口使用 `Authorization: Bearer <JUSTAI_OPENAPI_API_KEY>`，请求体为 JSON，方法均为 `POST`。

仅联调个人国内开发环境时可额外设置 `JUSTAI_OPENAPI_X_ENV=tcw`；生产环境必须留空。

## 接口

| 路径 | 用途 |
| --- | --- |
| `/openapi/wechat/bindings/prepare` | 创建 15 分钟有效的绑定会话，返回 `authorize_url` |
| `/openapi/wechat/bindings/status` | 用 `bind_token` 查询 `pending/completed/expired` |
| `/openapi/wechat/bindings/list` | 查看当前个人或指定团队绑定的公众号 |
| `/openapi/wechat/drafts/sync` | 创建文章记录并提交异步草稿同步任务 |
| `/openapi/wechat/drafts/status` | 用 `job_id` 查询草稿同步状态 |

个人账号不传 `team_id`；团队账号显式传正整数 `team_id`。OpenAPI 不使用内部 `Session-Id`。

绑定状态在管理员尚未授权和授权回调失败时都可能暂时返回 `pending`。如果管理员已完成操作但状态仍未变化，应查看微信授权页面上的失败信息，然后重新发起绑定。

## 草稿同步请求

`sync_wechat_draft.py` 的会话输入必须来自已完成的 `generate_notes` 分支，并包含结构化 `note` 组件、标题、正文和至少一张图片。`common` / `generate_plan` 展示结果不能直接作为草稿同步输入。

```json
{
  "title": "文章标题",
  "content": "纯文本正文",
  "content_html": "可选的排版 HTML",
  "cover_image": "https://example.com/cover.jpg",
  "image_urls": ["https://example.com/body.jpg"],
  "conversation_id": "可选的小加会话 ID",
  "authorizer_appid": "绑定多个公众号时必传",
  "team_id": 35
}
```

标题必填；`content` 与 `content_html` 至少一个非空；至少需要一张 HTTP(S) 图片。只绑定一个公众号时可以省略 `authorizer_appid`。

提交成功返回 `note_id`、`job_id`、`authorizer_appid` 和 `sync_status=pending`。`sync` 与 `status` 接口的 `note_id` 均为带连字符的标准 UUID 字符串。继续调用状态接口，直到：

- `done`：草稿已进入公众号草稿箱。
- `failed`：确定失败，可以根据错误处理。
- `unknown`：微信是否创建草稿无法确认，必须人工检查草稿箱，不得自动重试。
- `pending/processing/submitting`：仍在处理。

草稿同步不等于正式发布。本 Skill 不调用 `freepublish/submit`。
