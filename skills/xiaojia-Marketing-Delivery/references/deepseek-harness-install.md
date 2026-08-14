# DeepSeek Harness 安装与凭证配置

本文档面向需要直接管理 DSH profile 的开发者。普通用户已有小加 Skill 登录凭证时，无需进行本页配置，插件会自动读取本地登录配置。

## 公开入口

- npm 包：[`dsh-xiaojia-marketing-delivery`](https://www.npmjs.com/package/dsh-xiaojia-marketing-delivery)
- GitHub 源码：[`qinshimeng18/xiaojia-Marketing-Delivery`](https://github.com/qinshimeng18/xiaojia-Marketing-Delivery)

DeepSeek Harness 用户优先从 npm 安装；需要查看完整 Skill、Python 脚本或其他 Agent 安装方式时使用 GitHub 仓库。

## npm 安装

```bash
dsh plugin --profile web add dsh-xiaojia-marketing-delivery
dsh web
```

确认公开版本：

```bash
npm view dsh-xiaojia-marketing-delivery version
```

无界面调用使用 `headless` profile：

```bash
dsh plugin --profile headless add dsh-xiaojia-marketing-delivery
dsh --profile headless "调用小加生成一套新品营销图文"
```

## 凭证读取顺序

插件按以下优先级读取凭证：

1. DSH 插件配置中的 `apiKey`。
2. 当前进程的 `JUSTAI_OPENAPI_API_KEY`。
3. 现有小加 Skill 登录配置文件。
4. 当前 shell 配置文件中的既有变量。

只为当前终端配置时可执行：

```bash
export JUSTAI_OPENAPI_API_KEY="your-api-key"
```

不要把真实 Key 写入仓库、npm 包、公开文档、DSH 对话或工具参数。插件只在 HTTP `Authorization` 请求头中使用凭证，并会从服务端错误信息中脱敏当前 Key。

## 本地 checkout 安装

```bash
git clone https://github.com/qinshimeng18/xiaojia-Marketing-Delivery.git
python3 ./xiaojia-Marketing-Delivery/skills/xiaojia-Marketing-Delivery/scripts/list_projects.py
dsh plugin --profile web add ./xiaojia-Marketing-Delivery/skills/xiaojia-Marketing-Delivery
dsh web
```

如果 Python 登录脚本已经生成本地配置，Node 插件会直接复用，不需要重开终端。
