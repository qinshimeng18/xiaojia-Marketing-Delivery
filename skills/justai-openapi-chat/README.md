# justai-openapi-chat

一个基于 JustAI OpenAPI 的 skill，可以安装到 Claude Code 或 Codex，用来调用线上 Agent 能力，而不是在本地直接推理。

目前主要支持：
- 查询可用资料库
- 查询可用 skill
- 提交异步对话任务
- 轮询查询已有 `conversation_id` 的结果

适合这些场景：
- 营销方案生成
- 小红书图文笔记生成
- 生图
- collect-info / confirm-info 后续推进

## 安装方式

### Claude Code

个人级安装：

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/qinshimeng18/xiaojia-skills.git /tmp/xiaojia-skills
cp -R /tmp/xiaojia-skills/skills/justai-openapi-chat ~/.claude/skills/
```

项目级安装：

```bash
mkdir -p .claude/skills
git clone https://github.com/qinshimeng18/xiaojia-skills.git /tmp/xiaojia-skills
cp -R /tmp/xiaojia-skills/skills/justai-openapi-chat .claude/skills/
```

安装后重启 Claude Code，skill 会以 `/justai-openapi-chat` 的形式可用。

### Codex

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/qinshimeng18/xiaojia-skills.git /tmp/xiaojia-skills
cp -R /tmp/xiaojia-skills/skills/justai-openapi-chat ~/.codex/skills/
```

安装后重启 Codex。

## 前置要求

使用前需要先配置环境变量：

```bash
export JUSTAI_OPENAPI_BASE_URL="https://your-domain"
export JUSTAI_OPENAPI_API_KEY="your-api-key"
```

可选：

```bash
export JUSTAI_OPENAPI_TIMEOUT="300"
```

## 最短使用方式

先查看资料库：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/list_projects.py"
```

再查看可用 skill：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/list_skills.py"
```

然后先发起一次对话任务：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" --message "帮我做一份小红书运营方案"
```

拿到 `conversation_id` 之后，再查询结果：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat_result.py" \
  --conversation-id "your-conversation-id"
```

如果要继续同一轮对话，还是重新调用 `chat.py`，但要带上原来的 `conversation_id` 和新的 `message`：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --conversation-id "your-conversation-id" \
  --message "继续"
```

如果要限制到某个资料库或指定 skill，在提交任务时继续传：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --project-id "fld_xxx" \
  --skill-id "skill_xxx" \
  --message "优先参考资料库并使用这个 skill"
```

## 说明

- `chat.py` 只负责 `/openapi/agent/chat_submit`
- `chat_result.py` 只负责 `/openapi/agent/chat_result`
- `conversation_id` 需要自己保留，用于后续续聊
- `confirm_info` 这类结果目前还是通过自然语言继续推进，不是结构化表单提交
- 在 Claude Code 中，`${CLAUDE_SKILL_DIR}` 会自动指向当前 skill 目录
