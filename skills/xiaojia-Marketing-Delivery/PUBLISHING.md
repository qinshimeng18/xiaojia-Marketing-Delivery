# DeepSeek Harness 插件发布

本目录同时是 `dsh-xiaojia-marketing-delivery` npm 包。公开发布只包含 JavaScript 运行时、`cordis.patch.yml` 和内置 Harness Skill，不包含测试、Python 脚本或任何本地凭证。

## 发布前检查

```bash
npm ci
npm test
npm pack --dry-run
```

再使用一个隔离的 DSH home 安装生成的 tarball，确认 profile 能组合配置：

```bash
npm pack
export DSH_HOME="$(mktemp -d)"
dsh plugin --profile web add ./dsh-xiaojia-marketing-delivery-*.tgz
dsh --profile web --dump-config
```

检查结果中应包含 `# == dsh-xiaojia-marketing-delivery` 和 `xiaojia-marketing-delivery`。发布包、测试输出和文档中不得包含真实 API Key。

## 发布

1. 更新 `package.json` 与 `client.js` 中的版本号。
2. 更新仓库根目录 `CHANGELOG.md`。
3. 确认 npm 包名尚未被其他账户占用。
4. 使用拥有发布权限的 npm 账户执行：

```bash
npm publish --access public
```

5. 给 GitHub 仓库添加 `dsh-plugin` Topic，让 DSH 用户可以通过官方推荐的 GitHub Topic 发现插件。
