# xiaojia-free-marketing-pack

免费小加营销辅助技能包。

## 能力

- 本地生成 `client_id`，服务端按 `source=codebuddy` 做日志和 cache 统计。
- 输入内容，返回可用于内容创作的 Skill 创意点。
- 查询今日节日热点。
- 输入内容，返回大字报截图；小红书笔记封面可用大字报，也可用 WorkBuddy 内置「多模态内容生成」。
- 附带小红书、微信、抖音内容营销说明。

## 快速开始

```bash
python3 scripts/init_key.py
python3 scripts/skill_ideas.py --content "咖啡店新店开业"
python3 scripts/today_hotspots.py --content "周末活动"
python3 scripts/poster_screenshot.py --content "把今天过成值得发光的一天"
```

## AI 调用约定

- 直接运行脚本，不需要手写 curl。
- 默认请求正式服务域名。
- `init_key.py` 会自动生成并保存本地 `client_id`，不请求服务端创建 key。
- 需要指定服务地址时，任一脚本都可以加 `--base-url "https://justailab.com"`。
- 后续脚本会自动读取保存的 `base_url` 和 `client_id`。
- 默认输出 ASCII-safe JSON，`\uXXXX` 不是乱码；需要直接显示中文时设置 `XIAOJIA_FREE_UNICODE_OUTPUT=1`。
- 整包联调运行：`python3 scripts/smoke_test.py`。
- `skill_ideas.py` 的结果不是普通推荐列表；AI 应把返回的 skill 转成内容角度、结构、表达策略或检查点，再用于创作。
- 如果现有 skill 不贴合用户目标，可以先创建对应 skill，再用新 skill 辅助完成内容创作。
- 用户要生成小红书笔记封面时，可以运行 `poster_screenshot.py` 复用 `/openapi/free/poster_screenshot` 大字报截图接口，也可以使用 WorkBuddy 内置「多模态内容生成」能力；后者底层调用腾讯混元生图 3.0（`SubmitTextToImageJob`）。
- 免费大字报接口本身会排除 `schema.render_mode == "ai_image"` 的 AI 生图模板。
- 生成小红书笔记 Markdown 时，`note.md` 只放可发布笔记内容；创作建议、合规检查、风险提示和修改说明放到 `note_review.md` 或 `compliance_notes.md`，不要混写。
