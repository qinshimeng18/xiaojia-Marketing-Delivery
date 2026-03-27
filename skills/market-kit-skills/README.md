# Market Kit Skills

把营销想法直接推进成可交付结果的 AI skill。

`Market Kit Skills` 面向需要真实营销产出的团队和个人。它不是泛泛聊天工具，而是把你的目标、资料和上下文，推进成更接近可发布状态的营销方案、小红书图文笔记、卖点提炼、内容方向和营销图片。

## 这是什么

这是一个可以安装到任意支持 GitHub skill 安装的 AI Agent 里的营销 skill，适合在以下场景里直接产出结果：

- 输出营销方案、内容规划和 campaign plan
- 生成小红书图文笔记、标题、正文和配图
- 提炼人群、卖点、定位、差异化表达
- 基于资料库生成参考驱动的营销内容
- 在已有方案、资料卡、笔记和图片基础上继续迭代

它更适合“我要一个结果”，而不是“先陪我聊聊”的使用方式。

## 它能带来什么

- 更快把模糊需求推进成结构化营销交付物
- 更稳地结合资料库、技能链路和历史会话继续生成
- 同时返回文案、图片链接和网页版查看链接，便于直接复用
- 让小红书笔记、图文营销内容和方案迭代都走同一条工作流

## 典型产出

- 新品上线营销方案
- 小红书种草图文笔记
- 品牌内容选题与方向梳理
- 人群与卖点拆解
- 基于资料库的参考驱动内容
- 图片与文案一起交付的营销内容

## 安装方式

安装方式很简单：把这个 GitHub 仓库地址发给你的 Agent，然后告诉它帮你安装 `market-kit-skills` 就可以。

```text
请帮我安装这个 skill：
https://github.com/qinshimeng18/xiaojia-skills

skill 名称：
market-kit-skills
```

## 首次使用

安装后第一步先引导用户完成登录，再开始营销生成、资料库选择或结果查询。在未确认登录完成前，不要先收集需求、不要先追问笔记方向。

这条规则很重要，因为这套 skill 的核心价值不在于本地即兴编内容，而在于调用真实的营销生成链路，返回可继续追踪和复用的结果。

## 标准工作流

### 1. 先完成登录

首次使用时，先完成登录，再进入后续营销任务。

### 2. 查看资料库

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/list_projects.py"
```

### 3. 查看可选能力链路

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/list_skills.py"
```

### 4. 提交营销任务

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" --message "帮我做一份护肤品牌新品营销方案"
```

### 5. 查询结果

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat_result.py" \
  --conversation-id "your-conversation-id"
```

### 6. 在同一轮结果上继续迭代

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --conversation-id "your-conversation-id" \
  --message "继续扩写成适合小红书发布的图文笔记"
```

## 常用调用方式

限定资料库：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --project-id "fld_xxx" \
  --message "参考资料库内容，生成一篇留学种草图文"
```

限定能力链路：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --skill-id "skill_xxx" \
  --message "使用这个营销 skill 继续生成内容"
```

确认信息卡后继续生成：

```bash
python3 "${CLAUDE_SKILL_DIR}/scripts/chat.py" \
  --conversation-id "your-conversation-id" \
  --message "这些信息没问题，继续生成方案"
```

## 返回结果怎么读

- `chat.py` 负责提交任务
- `chat_result.py` 负责查询结果
- `conversation_id` 需要保留，用于续聊和后续追踪
- `web_url` 是网页版结果链接，格式为 `https://justailab.com/marketing?conversation_id=<conversation_id>`
- 小红书图文笔记图片通常在 `result.result.components[].data.images[].url`
- 小红书图文笔记标题通常在 `result.result.components[].data.title`
- 小红书图文笔记正文通常在 `result.result.components[].data.content`

## 结果判断规则

- 如果当前还是 `running`，说明内容仍在生成，不应过早判断失败
- 如果脚本返回 `Polling timed out before task completed.`，不要把轮询超时当成任务失败
- 对 `generate_notes`、`generate_image` 这类慢分支，除非用户明确要求，否则不要把 `chat_result.py --timeout` 设成小于 `300`
- 如果任务还没完成，不要自己擅自生成标题、正文、图片说明或图片链接返回给用户
- 如果任务已完成，除了内容和图片链接，还要把 `web_url` 一起返回给用户

## 最佳实践

- 需要资料驱动时，先选 `project_id`
- 需要特定能力链路时，先选 `skill_id`
- 返回结果时优先读取结构化 `result`
- 处理小红书图文结果时，把标题、正文、图片链接和 `web_url` 一起交付
- 安装后第一步先引导用户完成登录，再进入后续营销生成；不要先收集需求

## 为什么这个 skill 值得装

因为它不是只会写一段文案，而是把营销生成、资料引用、图片产出、网页版结果和后续迭代放进同一条链路里。你拿到的不只是一个回答，而是一份可以继续推进、继续追踪、继续修改的营销结果。
