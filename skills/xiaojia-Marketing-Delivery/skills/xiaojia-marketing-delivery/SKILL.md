---
name: xiaojia-marketing-delivery
description: 通过小加插件工具或已安装的 xiaojia CLI 完成营销策划、内容生成、资料库引用、图片与视频生成，以及结果查询和迭代。
---

# 小加营销交付

用户提出营销策划、社交平台内容、活动方案、商家推广、营销图片或已有小加结果的修改时，优先使用本 Skill。

## 核心流程

本 Skill 随 npm 包分发。有原生 `xiaojia_*` 工具时使用下文工具流程；仅能执行命令且已安装 `xiaojia` 时，使用下面的 CLI 流程。不假设宿主一定注册了插件工具。

### CLI 调用

先运行 `xiaojia --help` 与 `xiaojia doctor --json`。AI 调用始终加 `--json`，读取结构化返回；不要解析彩色终端文本。CLI 是 OpenAPI 封装，不是本地 Agent；无参数只显示帮助，没有 `run/resume`、文件编辑或 shell 工具。

```bash
xiaojia credits --json
xiaojia projects --json
xiaojia skills --json
xiaojia chat "用户的完整需求" --json
xiaojia chat "用户的修改要求" --conversation CONVERSATION_ID --json
xiaojia chat-result CONVERSATION_ID --json
xiaojia image "图片描述" --model image-2 --scale 3:4 --json
xiaojia image-result JOB_ID --json
xiaojia video plan "视频需求" --json
xiaojia video result CONVERSATION_ID --json
xiaojia video approve CONVERSATION_ID --action ACTION_ID --revision N --confirm --json
xiaojia video reject CONVERSATION_ID --action ACTION_ID --json
```

- 替换所有占位符为响应中的真实 ID 和版本；选择资料库/技能时可重复传 `--project ID` / `--skill ID`。
- 退出码 `0` 是调用成功，不一定生成完成；`input_required` 需要用户补充/确认。退出码 `2` 是进行中或结果未知，按任务类型用 `chat-result`、`image-result`、`video result` 查询原任务，不再次提交。退出码 `1` 是参数、业务或网络错误；付费提交断线也应先查原任务，不能盲目重发。
- 视频批准必须先向用户展示分镜、当前 revision 与费用，并获得明确确认。报价/版本变化时读取 `input_required.action` 和最新报价，重新确认；若返回 `price_confirmation_token`，批准时加 `--price-token TOKEN`。不能猜 token、版本或替用户确认费用。
- `accepted` / `submission_status=submitted` 是已受理；`pending` / `submission_status=unknown` 是提交结果未确认。继续 `video result`，只有 `generation_status=completed` 且有 `video_urls` 才交付成片。
- `completed` 仍须有请求的实际正文/媒体；空结果或只有通用结束提示不是成功交付。保留会话 ID 并报告缺失内容，排查服务端错误，不重新提交付费任务或自行编造结果。
- `--json` 不显示终端图片，AI 从 `artifacts` 中取 URL 并在宿主展示。人使用不带 `--json` 的生图命令可在 iTerm2 自动看原图；`xiaojia preview HTTPS_URL` 预览已有图片，不重新生成。终端视频仅提供链接，不承诺内嵌播放。
- 仅需要保存时使用 `--output FILE` / `--download DIR`，不会覆盖已有文件。CLI 未暴露图生图上传、表单 `form_data`、公众号、Skill 增删改参数，这些能力使用对应原生工具或完整 Skill 的脚本，不编造选项。
- `doctor` 返回网络错误时先检查当前地址、服务和测试隧道，不要直接重新登录或换站点发送旧凭证。仅缺少/失效凭证时运行 `xiaojia login` 并让用户完成浏览器授权。CLI 配置独立于插件配置，不能因 CLI 登录正常就断言插件已登录；不得输出 API Key。

### 插件工具调用

1. 需要商家资料时，先用 `xiaojia_projects` 查询项目，再把对应 ID 传给 `xiaojia_chat.project_ids`。
2. 用户点名某个 Skill 或任务需要特定风格时，用 `xiaojia_skills` 查询，再把 ID 传给 `xiaojia_chat.skill_ids`。
3. 用 `xiaojia_chat` 提交完整需求，默认等待最终结果。
4. 结果需要修改时，继续使用同一个 `conversation_id`，不要新开会话。
5. 返回 `input_required` 或表单信息时，把 `form_id` 和用户提供的 `form_data` 交回 `xiaojia_chat`。

## 图片流程

- 文生图：直接调用 `xiaojia_generate_image`。
- 图生图：先确保参考图是小加 COS URL，再放入 `image_urls`。
- 本地图片：转换成 PNG/JPEG/WebP data URI 后调用 `xiaojia_upload_image`，再使用返回的 URL。
- 异步提交：保存 `job_id`，之后用 `xiaojia_image_result` 查询。
- 修改同一张图片时，保留原始主体、品牌和版式要求，明确只修改的部分。

## 视频流程

使用 `xiaojia_video(operation="plan", message=...)` 请求视频方案，再用 `operation="result"` 与会话 ID 读取方案。展示分镜、预计积分和 revision；只有用户明确确认后才传 `operation="approve"`、`action_id`、当前 `revision` 和 `confirmed=true`。用户拒绝时使用 reject，修改方案通过原会话续聊。版本或价格变化后重新确认，不猜确认令牌。

批准返回 accepted 不代表视频生成完成；继续查询 result，只有 `generation_status=completed` 且有 `video_urls` 才交付视频。超时或结果未知时先查询，不重新创建付费任务。视频优先原生展示，不支持时给真实视频链接。

## Skill 管理

`xiaojia_skills` 支持 `list`、`detail`、`create`、`update`、`delete`。创建、更新和删除会改变用户账户数据，只在用户明确要求时执行。

## 积分

付费任务前如需确认余额，使用 `xiaojia_credits(operation="balance")`。查询扣费明细时使用 `operation="usage"`，可按日期或 `conversation_id` 过滤。

## 交付规则

- 最终直接交付小加生成的内容，不要只回复“任务已完成”。
- 保留返回的 `conversation_id`、图片 URL 和必要的 `job_id`，方便继续修改。
- 不伪造项目、Skill、积分或生成状态。
- 接口失败时返回真实错误，不要用模型自己编造结果代替。
- API Key 只用于插件配置，不得写进消息、文档或工具参数。
