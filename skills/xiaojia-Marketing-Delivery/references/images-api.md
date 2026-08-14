# 小加图片生成 API

接口为兼容旧客户端，省略 `wait_for_completion` 时仍同步等待。小加、Coze 等有单次请求时限的调用方必须显式传 `wait_for_completion=false`，先提交，再用 `job_id` 轮询。

## 1. 提交任务

```http
POST /openapi/images/generate
Authorization: Bearer <API_KEY>
Content-Type: application/json

{
  "prompt": "一张咖啡店开业的小红书封面图",
  "model": "Image 2",
  "pic_scale": "3:4",
  "prompt_mode": "enhanced",
  "idempotency_key": "client-request-uuid",
  "wait_for_completion": false
}
```

图生图增加 `image_urls`。该字段必须是当前服务 COS 的 HTTPS 图片 URL 数组，支持 PNG、JPEG、WebP，最多 14 张：

```json
{
  "prompt": "保持人物和产品不变，把背景改成海边日落",
  "image_urls": [
    "https://cos.justailab.xyz/media/images/cos_only/openapi_image/reference.png"
  ],
  "model": "Image 2",
  "pic_scale": "3:4",
  "wait_for_completion": false
}
```

本地图片必须先调用 `POST /openapi/images/upload`，请求体使用 `image_base64`，再把返回的 `url` 放入 `image_urls`。`generate_image.py --image-file` 已自动完成这两步；已有本服务 COS URL 时使用 `--image-url`。

正常会在数秒内返回：

```json
{
  "status": "ok",
  "generation_status": "pending",
  "job_id": "job_xxx",
  "conversation_id": "conv_xxx"
}
```

## 2. 轮询结果

每 3～5 秒查询一次：

```http
POST /openapi/images/result
Authorization: Bearer <API_KEY>
Content-Type: application/json

{"job_id": "job_xxx"}
```

- `pending` / `running`：继续轮询。
- `completed`：读取 `picture_urls`。
- `failed`：读取 `err_msg`，停止轮询。

建议单次 HTTP 超时设为 10～20 秒，总轮询时间设为 300 秒。接口只允许查询当前 API Key 所属用户的任务。

`prompt_mode` 支持 `raw` 和 `enhanced`。OpenAPI 为兼容既有调用默认 `raw`；小加脚本默认明确发送 `enhanced`，先走线上同源的 AI 提示词增强。相同请求重试必须复用同一个 `idempotency_key`；相同 key 携带不同参数（包括不同参考图）会返回 `idempotency_conflict`。

生图复用系统 Wallet 的图片积分单价和预留/确认/释放链路：提交前预留，成功后扣除，失败后释放。积分不足返回 `insufficient_credits`，不会提交供应商任务。

总轮询时间包含 sleep 和结果查询；达到上限后脚本不会再发起请求。同步和异步提交都由同一个任务消费完整候选链，超时后也不会创建新的任务或更换 `job_id`。普通供应商失败按 `image-2 → image-flash → doubao-5.0` 降级；内容审核失败沿用项目通用策略，提前尝试豆包一次，豆包仍失败则终止。

TLS 必须使用系统信任的公开证书链；调用端不要用 `verify=False` 或 `curl -k` 绕过校验。
