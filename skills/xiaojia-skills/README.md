# xiaojia-skills

这是小加同学的营销能力 skill，可以安装到 Claude Code 或 Codex。

它的作用不是让你自己拼技术接口，而是直接帮你完成这些营销相关任务：

1. 生成营销方案
2. 生成小红书图文和笔记内容
3. 收集资料并整理确认卡片
4. 生成图片
5. 在需要购买、升级、开通时，把用户直接引导到统一营销页

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
cp -R /tmp/xiaojia-skills/skills/xiaojia-skills ~/.claude/skills/
```

项目级安装：

```bash
mkdir -p .claude/skills
git clone https://github.com/qinshimeng18/xiaojia-skills.git /tmp/xiaojia-skills
cp -R /tmp/xiaojia-skills/skills/xiaojia-skills .claude/skills/
```

安装后重启 Claude Code，skill 会以 `/xiaojia-skills` 的形式可用。

### Codex

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/qinshimeng18/xiaojia-skills.git /tmp/xiaojia-skills
cp -R /tmp/xiaojia-skills/skills/xiaojia-skills ~/.codex/skills/
```

安装后重启 Codex。

## 前置要求

默认会请求生产地址 `https://justailab.com`。

如果 `JUSTAI_OPENAPI_API_KEY` 已经存在，skill 会直接复用它。

If `JUSTAI_OPENAPI_API_KEY` is missing, the skill will start the login flow automatically, print a `/login?login_token=...` URL for the user to open, poll for login completion, and persist the returned API key into both the detected shell rc file and a local config file so later runs can reuse it without asking again。

你也可以手动预先配置：

```bash
export JUSTAI_OPENAPI_API_KEY="your-api-key"
```

也可以手动写一个本地配置文件作为兜底，默认会查这些位置：

```json
{
  "base_url": "https://justailab.com",
  "api_key": "your-api-key",
  "timeout": 300
}
```

- `~/.codex/justai-openapi-chat.json`
- `~/.claude/justai-openapi-chat.json`
- 或通过 `JUSTAI_OPENAPI_CONFIG` 指向自定义文件

可选覆盖：

```bash
export JUSTAI_OPENAPI_BASE_URL="https://justailab.com"
export JUSTAI_OPENAPI_TIMEOUT="300"
```

如果你要切到别的环境，再额外设置：

```bash
export JUSTAI_OPENAPI_BASE_URL="https://your-domain"
```

## 最短使用方式

如果当前没有 API key，也可以直接运行下面任意命令。脚本会自动进入登录流程，而不是先报错或要求用户手填 key。

先查看资料库：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/list_projects.py"
```

再查看可用 skill：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/list_skills.py"
```

如果只是需要给用户一个固定支付入口，可直接返回营销页链接：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/payment_link.py"
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

如果上一轮返回了 `form_id`，也可以直接带结构化表单继续：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --conversation-id "your-conversation-id" \
  --form-id "your-form-id" \
  --form-data-file "/tmp/form_data.json"
```

也可以同时补一句自然语言指令：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --conversation-id "your-conversation-id" \
  --form-id "your-form-id" \
  --form-data-json '{"title":"资料卡","form":[]}' \
  --message "请按更新后的表单继续生成方案"
```

## 说明

- `chat.py` 只负责 `/openapi/agent/chat_submit`
- `chat_result.py` 只负责 `/openapi/agent/chat_result`
- 缺少 `JUSTAI_OPENAPI_API_KEY` 时，脚本会自动发起登录桥接，并把拿到的 key 同时写回 shell rc 文件和本地配置文件
- `conversation_id` 需要自己保留，用于后续续聊
- `confirm_info` 返回 `form_id` 后，既可以继续发自然语言，也可以直接传 `form_id + form_data` 结构化续跑
- `chat_result.py` 在任务还没完成时，会把当前 `status/branch/content_type` 打到 `stderr`；最终 JSON 仍然只输出到 `stdout`
- 图文笔记图片通常在 `result.result.components[].data.images[].url`
- 在 Claude Code 中，`${CLAUDE_SKILL_DIR}` 会自动指向当前 skill 目录
