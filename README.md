# Market Kit Skills

这个仓库用于分发可安装的营销 AI skill。

当前包含：

- `skills/market-kit-skills`

它适合这些场景：

- campaign plan
- 小红书图文与笔记
- 人群、卖点、定位梳理
- 资料驱动的营销内容生成
- 营销图片和图文组合内容

## Claude Code 安装

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

## Codex 安装

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/qinshimeng18/xiaojia-skills.git /tmp/xiaojia-skills
cp -R /tmp/xiaojia-skills/skills/market-kit-skills ~/.codex/skills/
```

安装后重启 Codex。

更具体的用法见：

- `skills/market-kit-skills/README.md`
- `skills/market-kit-skills/SKILL.md`
