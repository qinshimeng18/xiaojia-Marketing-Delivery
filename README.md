# xiaojia-skills

这个仓库用于分发可安装的 AI skill。

当前包含：

- `skills/justai-openapi-chat`

## Claude Code 安装

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

## Codex 安装

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/qinshimeng18/xiaojia-skills.git /tmp/xiaojia-skills
cp -R /tmp/xiaojia-skills/skills/justai-openapi-chat ~/.codex/skills/
```

安装后重启 Codex。

## 前置环境变量

```bash
export JUSTAI_OPENAPI_BASE_URL="https://your-domain"
export JUSTAI_OPENAPI_API_KEY="your-api-key"
export JUSTAI_OPENAPI_TIMEOUT="300"
```

更具体的用法见：

- `skills/justai-openapi-chat/README.md`
- `skills/justai-openapi-chat/SKILL.md`
