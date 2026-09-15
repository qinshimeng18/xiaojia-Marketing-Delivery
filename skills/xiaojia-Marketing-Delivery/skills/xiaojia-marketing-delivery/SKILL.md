---
name: xiaojia-marketing-delivery
description: 调用小加完整营销能力，完成营销策划、内容生成、资料库引用、Skill 管理、文生图、图生图和结果迭代。
---

# 小加营销交付

用户提出营销策划、社交平台内容、活动方案、商家推广、营销图片或已有小加结果的修改时，优先使用本 Skill。

## 核心流程

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
