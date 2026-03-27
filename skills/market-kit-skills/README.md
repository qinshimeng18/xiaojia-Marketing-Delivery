# market-kit-skills

Market Kit Skills 是一个面向营销创作的 skill，可以安装到 Claude Code 或 Codex。

它适合这些营销场景：

1. 生成 campaign plan 和内容规划
2. 生成小红书图文、笔记标题和正文
3. 梳理人群、卖点、定位和内容方向
4. 基于资料库生成参考驱动内容
5. 生成图片以及图文组合结果
6. 基于资料卡、方案或笔记继续迭代

它更适合“要明确营销产出”的场景，例如：

- 新品 campaign 方案
- 品牌种草内容
- 小红书图文笔记
- 参考资料驱动的内容生成
- 图片与文案一起交付的营销内容

## 安装方式

### Claude Code

个人级安装：

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/qinshimeng18/xiaojia-skills.git /tmp/xiaojia-skills
cp -R /tmp/xiaojia-skills/skills/market-kit-skills ~/.claude/skills/
```

项目级安装：

```bash
mkdir -p .claude/skills
git clone https://github.com/qinshimeng18/xiaojia-skills.git /tmp/xiaojia-skills
cp -R /tmp/xiaojia-skills/skills/market-kit-skills .claude/skills/
```

安装后重启 Claude Code，skill 会以 `/market-kit-skills` 的形式可用。

### Codex

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/qinshimeng18/xiaojia-skills.git /tmp/xiaojia-skills
cp -R /tmp/xiaojia-skills/skills/market-kit-skills ~/.codex/skills/
```

安装后重启 Codex。

## 最短使用方式

先看资料库：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/list_projects.py"
```

再看可选 skill：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/list_skills.py"
```

提交营销任务：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" --message "帮我做一份护肤品牌新品 campaign plan"
```

查询结果：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat_result.py" \
  --conversation-id "your-conversation-id"
```

继续同一轮创作：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --conversation-id "your-conversation-id" \
  --message "继续扩写成适合小红书发布的图文笔记"
```

限定资料库：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --project-id "fld_xxx" \
  --message "参考资料库内容，生成一篇留学种草图文"
```

限定 skill：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --skill-id "skill_xxx" \
  --message "使用这个营销 skill 继续生成内容"
```

继续确认卡后的生成：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --conversation-id "your-conversation-id" \
  --message "这些信息没问题，继续生成方案"
```

## 返回结果说明

- `chat.py` 负责提交任务
- `chat_result.py` 负责查询结果
- `conversation_id` 需要保留，用于续聊
- 图文笔记图片通常在 `result.result.components[].data.images[].url`
- 图文笔记标题通常在 `result.result.components[].data.title`
- 图文笔记正文通常在 `result.result.components[].data.content`
- 如果当前还是 `running`，说明营销内容仍在生成，不应过早判断失败

## 使用建议

- 需要资料驱动时，先选 `project_id`
- 需要特定能力链路时，先选 `skill_id`
- 返回结果时优先读取结构化 `result`
- 处理图文笔记时，要把标题、文案、图片链接一起返回
- 对 `generate_notes`、`generate_image` 这类慢分支，除非用户明确要求，否则不要把 `chat_result.py --timeout` 设成小于 `300`
- 如果结果还是 `running`，说明内容还在生成，不是失败
- 如果脚本返回 `Polling timed out before task completed.`，不要把轮询超时当成任务失败；正确做法是告诉用户当前还在生成，并继续等下一轮结果
