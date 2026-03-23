---
name: justai-openapi-chat
description: Call the JustAI openapi async chat endpoints and return structured JSON results. Use when Codex needs to invoke the deployed JustAI agent for marketing plans, Xiaohongshu notes, image generation, collect-info turns, confirm-info card generation, or follow-up turns through `/openapi/agent/chat_submit` and `/openapi/agent/chat_result` instead of reasoning locally.
allowed-tools: Bash
---

# JustAI OpenAPI Chat

Use the bundled scripts to inspect available projects and skills, then call the deployed JustAI openapi endpoint in two steps:

1. `list_projects.py` lists your available资料库 folders/projects
2. `list_skills.py` lists your available skill IDs
3. `chat.py` submits the task and returns `conversation_id`
4. `chat_result.py` polls `chat_result` until the task is `completed` or `failed`

This keeps the interface stable for slower branches such as card generation, plan generation, notes generation, and image generation.

When running inside Claude Code, `${CLAUDE_SKILL_DIR}` resolves to this skill directory. Use that path when invoking the bundled scripts. In Codex or a plain shell, run the same scripts from the installed skill directory.

## Workflow

1. Ensure these environment variables are set before using the script:
   - `JUSTAI_OPENAPI_BASE_URL`
   - `JUSTAI_OPENAPI_API_KEY`
   - Optional: `JUSTAI_OPENAPI_TIMEOUT`
2. If the task should be scoped to a specific资料库, run `scripts/list_projects.py` first and choose one or more `project_id`.
3. If the task should preload a specific skill, run `scripts/list_skills.py` first and choose one or more `skill_id`.
4. Run `scripts/chat.py` with `--message`, optional `--conversation-id`, optional repeated `--project-id`, and optional repeated `--skill-id`.
5. Preserve the returned `conversation_id`.
6. Run `scripts/chat_result.py --conversation-id ...` to poll the task result.
7. Read the returned JSON and use it directly:
   - `branch` tells which real path ran, such as `collect_info`, `confirm_info`, `generate_plan`, `generate_notes`, or `generate_image`
   - `result` is the primary payload
   - `text` is the human-readable summary or fallback text
   - `conversation_id` must be preserved for follow-up turns
8. If the user asks to continue an existing conversation, pass the previous `conversation_id` back into `scripts/chat.py` together with the new `--message`.
9. For `confirm_info` results:
   - To accept the card and continue, send a natural-language follow-up such as `这些信息没问题，继续生成方案`.
   - To revise the card, send a natural-language correction such as `预算改成3万，目标用户改成25到30岁女性，请更新资料卡片`.
   - Do not attempt structured form submission yet; the openapi layer currently supports message-based continuation only.

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
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" --message "帮我做一份小红书运营方案"
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
  --message "继续展开第二部分"
```

Continue after a confirmation card:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --conversation-id "existing-conversation-id" \
  --message "这些信息没问题，继续生成方案"
```

Revise a confirmation card in natural language:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --conversation-id "existing-conversation-id" \
  --message "预算改成3万，目标用户改成25到30岁女性，其他不变，请更新资料卡片"
```

Run a turn scoped to a selected project/folder:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --project-id "fld_demo" \
  --message "请参考这个资料库里的内容，帮我写一篇港理工校园生活图文笔记"
```

Run a turn with a manually selected skill:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --skill-id "skill_demo" \
  --message "使用这个技能继续分析"
```

Run a turn with both selected project and skill:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --project-id "fld_demo" \
  --skill-id "skill_demo" \
  --message "优先参考这个资料库并使用这个 skill 帮我生成方案"
```

Override the timeout for slower branches:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --message "我是做敏感肌护肤的品牌，先帮我整理资料卡片"
```

Control polling interval:

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat_result.py" \
  --conversation-id "existing-conversation-id" \
  --poll-interval 2 \
  --timeout 300
```

## Guardrails

- Prefer the scripts over hand-written `curl` so submit and polling stay consistent.
- When the task depends on a specific资料库 or手动技能, list them first and pass the exact IDs. The openapi request now统一使用 `project_id` 和 `skill_id` 两个字段，值都是字符串数组。
- Keep `conversation_id` from the last successful submit response and reuse it for polling and follow-up requests.
- Treat `result` as the primary machine-readable payload. Use `text` only as fallback when `result` is plain text.
- `confirm_info` currently continues through natural-language follow-up on the same `conversation_id`; there is no structured `form_data` submission path in openapi yet.
- If the endpoint returns `status=failed`, surface `message` directly instead of retrying blindly.
