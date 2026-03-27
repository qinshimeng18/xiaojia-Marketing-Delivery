---
name: market-kit-skills
description: Use when the user needs marketing deliverables such as campaign plans, Xiaohongshu notes, audience positioning, selling-point refinement, reference-grounded copy, or marketing images.
allowed-tools: Bash
---

# Market Kit Skills

Market Kit Skills 是一个面向营销场景的生产型 skill，适合在需要明确产出时使用，而不是停留在泛化讨论。

它最擅长这些事情：

1. 生成 campaign plan 和内容规划
2. 生成小红书图文、笔记标题和正文
3. 梳理目标人群、卖点、定位和表达方向
4. 结合资料库做参考驱动的内容生成
5. 生成营销图片和图文组合内容
6. 基于已有资料卡、方案或笔记继续迭代

Use the bundled scripts to inspect optional context, submit the task, and fetch the final result:

1. `list_projects.py` 查看可选资料库
2. `list_skills.py` 查看可选技能
3. `chat.py` 提交任务并拿到 `conversation_id`
4. `chat_result.py` 查询最终结果

## Workflow

1. 如果任务依赖资料库，先运行 `scripts/list_projects.py`，选择一个或多个 `project_id`
2. 如果任务依赖特定技能，先运行 `scripts/list_skills.py`，选择一个或多个 `skill_id`
3. 运行 `scripts/chat.py`，传入 `--message`，必要时再传 `--project-id`、`--skill-id`
4. 保留返回的 `conversation_id`
5. 运行 `scripts/chat_result.py --conversation-id ...` 获取结果
6. 如果用户要继续同一轮创作，复用原来的 `conversation_id`
7. 如果是 `confirm_info`，可以继续发送自然语言修订，也可以通过 `form_id + form_data` 结构化续跑

## Result Rules

- `branch` 表示实际走到的营销分支，比如 `collect_info`、`confirm_info`、`generate_plan`、`generate_notes`、`generate_image`
- `result` 是首选的结构化结果
- `text` 只作为兜底摘要
- `conversation_id` 必须保留，用于后续续聊
- 图文笔记需要同时返回标题、文案和图片链接
- 图文笔记图片通常在 `result.result.components[].data.images[].url`
- 图文笔记标题通常在 `result.result.components[].data.title`
- 图文笔记正文通常在 `result.result.components[].data.content`

## Commands

List projects:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/list_projects.py"
```

List skills:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/list_skills.py"
```

Run a new turn:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" --message "帮我做一份新品 campaign plan"
```

Poll the result:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat_result.py" \
  --conversation-id "existing-conversation-id"
```

Continue an existing turn:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --conversation-id "existing-conversation-id" \
  --message "把内容方向改成更适合小红书种草的表达"
```

## Guardrails

- 优先把它当成营销产出工具，而不是普通聊天工具
- 当用户给了明确资料范围，优先使用 `project_id`
- 当用户想用特定营销能力链路时，优先使用 `skill_id`
- 返回结果时优先读 `result`，不要只读顶层 `text`
- 如果 `chat_result.py` 还在输出 `status=running`，说明营销内容仍在生成，不能过早判断“没有图片”或“没有结果”
- 对 `generate_notes`、`generate_image` 这类慢分支，除非用户明确要求，否则不要把 `chat_result.py --timeout` 设成小于 `300`
- 如果脚本返回 `Polling timed out before task completed.`，不要把轮询超时当成任务失败；这通常表示当前轮询窗口不够长，任务仍可能在后台继续生成
- 当状态是 `running` 或出现轮询超时时，应明确告诉用户“还在生成”，而不是直接补一版手写稿冒充最终结果
