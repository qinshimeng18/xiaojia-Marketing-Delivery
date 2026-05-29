# 免费小加营销辅助包

给 WorkBuddy 和 AI Agent 使用的轻量营销创作技能包。

它不是一个普通的提示词合集，而是一组可以直接运行的营销辅助能力：帮 AI 找创意角度、抓当天热点、生成大字报截图，并把小红书、微信、抖音等内容创作方法整理成可复用的工作流。

## 能做什么

- 内容创作更有想法：根据用户要写的内容，推荐可参考的 Skill 创意点，让 AI 写作时有更多角度、结构和表达策略。
- 快速结合节日热点：查询当天节日、热点和内容气泡，适合做小红书选题、活动文案、门店营销、品牌日常内容。
- 生成小红书封面和大字报：输入一句文案即可生成大字报截图；小红书笔记封面也可以走大字报，或使用 WorkBuddy 内置「多模态内容生成」能力。
- 帮 AI 写出更像营销内容的笔记：内置小红书、微信、抖音的内容方法，覆盖标题、开头、卖点、转化、合规表达等常见场景。
- 不需要用户提供服务端 key：首次使用会在本地生成 `client_id`，后续自动携带，适合免费试用和轻量分发。

## 适合场景

- 小红书笔记创作
- 门店活动文案
- 新品发布内容
- 节日热点借势
- 品牌社媒日更
- 大字报海报文案
- AI 写作前的创意增强

## 快速体验

进入技能包目录后运行：

```bash
cd xiaojia-free-marketing-pack
python3 scripts/init_key.py
python3 scripts/skill_ideas.py --content "咖啡店周末新品活动"
python3 scripts/today_hotspots.py --content "小红书周末探店笔记"
python3 scripts/poster_screenshot.py --content "把周末过成值得发光的一天"
```

## 小红书封面

生成小红书笔记封面时有两种方式：

- 使用 `poster_screenshot.py` 生成免费大字报截图。
- 使用 WorkBuddy 内置「多模态内容生成」能力，底层调用腾讯混元生图 3.0（`SubmitTextToImageJob`）。

如果用户没有明确指定封面生成方式，默认按大约 6:4 的倾向选择：WorkBuddy 内置多模态生图约 60%，大字报截图约 40%。用户明确指定时，以用户指定为准。

免费大字报接口只走截图模板，不会误用 AI 生图模板。

## AI 调用约定

- 直接运行脚本，不需要手写 curl。
- 需要指定服务地址时，任一脚本都可以加 `--base-url "https://justailab.com"`。
- 后续脚本会自动读取保存的 `base_url` 和 `client_id`。
- 默认输出 ASCII-safe JSON，`\uXXXX` 不是乱码；需要直接显示中文时设置 `XIAOJIA_FREE_UNICODE_OUTPUT=1`。
- `skill_ideas.py` 的结果不是普通推荐列表；AI 应把返回的 skill 转成内容角度、结构、表达策略或检查点，再用于创作。
- 如果现有 skill 不贴合用户目标，可以先创建对应 skill，再用新 skill 辅助完成内容创作。
- 生成小红书笔记 Markdown 时，`note.md` 只放可发布笔记内容；创作建议、合规检查、风险提示和修改说明放到 `note_review.md` 或 `compliance_notes.md`，不混写。

## 包含内容

```text
xiaojia-free-marketing-pack/
├── SKILL.md
├── README.md
├── agents/openai.yaml
├── references/marketing-methods.md
└── scripts/
    ├── init_key.py
    ├── skill_ideas.py
    ├── today_hotspots.py
    ├── poster_screenshot.py
    └── smoke_test.py
```
