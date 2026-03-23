# justai-openapi-chat

一个基于 JustAI OpenAPI 的 Codex skill，用来调用线上 Agent 能力，而不是在本地直接推理。

目前主要支持：
- 查询可用资料库
- 查询可用 skill
- 发起异步对话
- 继续已有 `conversation_id`

适合这些场景：
- 营销方案生成
- 小红书图文笔记生成
- 生图
- collect-info / confirm-info 后续推进

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
python3 scripts/list_projects.py
```

再查看可用 skill：

```bash
python3 scripts/list_skills.py
```

然后发起一次对话：

```bash
python3 scripts/chat.py --message "帮我做一份小红书运营方案"
```

如果要继续同一轮对话，带上原来的 `conversation_id`：

```bash
python3 scripts/chat.py \
  --conversation-id "your-conversation-id" \
  --message "继续"
```

如果要限制到某个资料库或指定 skill，可以继续传：

```bash
python3 scripts/chat.py \
  --project-id "fld_xxx" \
  --skill-id "skill_xxx" \
  --message "优先参考资料库并使用这个 skill"
```

## 说明

- 这个 skill 走的是 `/openapi/agent/chat_submit` + `/openapi/agent/chat_result`
- `conversation_id` 需要自己保留，用于后续续聊
- `confirm_info` 这类结果目前还是通过自然语言继续推进，不是结构化表单提交
