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

本地图片用下文的 COS 直传流程。确认返回的 `url` 放入 `image_urls`。`generate_image.py --image-file` 会自动申请、PUT 和确认；已有本服务 COS URL 时使用 `--image-url`。

## 原图直传

API Key 由小加后端签发并绑定真实用户。已有小加登录态时，可调用 `POST /openapi/key/create`（如 `{"name":"Creator Studio 接入"}`）创建常规 Key；也可通过 Skill / CLI 登录流程获取。该 Key 供客户后端调用 OpenAPI，不是腾讯云密钥；浏览器直传 COS 只使用服务端为本次文件签发的临时上传凭证。种草查询专用 Key 不支持此接口。同一账号的 Key 共用上传限流和素材归属，不会自动区分客户平台的终端用户。

客户后端持有 API Key，向 `POST /openapi/images/upload_url` 发送 JSON。文件支持 PNG、JPEG、WebP，单图上限 10 MiB，签名有效 300 秒。同一用户的所有 Key 共用每 60 秒 30 次签发配额。申请和确认不扣积分，生图和视频仍按各自规则计费。

```json
{"filename":"reference.png","content_type":"image/png","size_bytes":204800}
```

签发响应示例（URL 与时间仅为格式示意）：

```json
{
  "status": "ok",
  "upload_id": "c17314bb-93d5-496b-8b85-2d9fd359ef61",
  "upload_url": "https://<cos-upload-host>/openapi-images/staging/<key>?<signature>",
  "method": "PUT",
  "headers": {"Content-Type": "image/png", "x-cos-acl": "private"},
  "expires_in": 300,
  "expires_at": "2026-11-08T12:05:00+00:00"
}
```

浏览器只接收本次上传的凭证，按返回的 `headers` 用原始 `File` 上传：

```js
const response = await fetch(ticket.upload_url, {
  method: ticket.method,
  headers: ticket.headers,
  body: file,
  credentials: "omit",
});
if (!response.ok) throw new Error(`COS PUT failed (${response.status})`);
```

同一请求的 curl 示例，`UPLOAD_URL` 为签发响应中的临时地址：

```bash
curl --fail-with-body --upload-file ./reference.png \
  -H 'Content-Type: image/png' -H 'x-cos-acl: private' "$UPLOAD_URL"
```

浏览器和 curl 会根据原始文件生成 `Content-Length`，该值必须与申报大小相同。上传时不要用 FormData、Base64、API Key 或 Session-Id，也不要附加业务请求拦截器的额外请求头。

`https://justailab.com` 官方服务当前使用的 COS 上传桶已统一允许任意页面 Origin 对 `PUT` 发起 CORS 预检，并允许 `Content-Type` 与 `x-cos-acl`；客户无需单独登记页面域名。浏览器必须使用 `credentials: "omit"`，按响应原样使用 `upload_url` 和 `headers`，不要将签名地址替换为图片展示域名。其他环境或自建服务使用不同上传桶时，须由服务维护方独立配置 CORS。CLI / 服务端直接上传不受浏览器 CORS 限制，但仍须通过签名鉴权。

跨域放行不会授予匿名写权限，临时签名仍限定对象、文件大小和有效期。签名 URL 在有效期内可能重复使用，不能当作一次性凭证，也不能写入日志或转发给其他用户。浏览器预检成功只代表跨域条件满足，仍须完成 PUT 和下述确认流程才能取得可用图片。

PUT 成功后，客户后端带原 Bearer 鉴权调用 `POST /openapi/images/upload_complete`，请求体仅含 `{"upload_id":"…"}`。确认通过后返回 `{"status":"ok","upload_id":"…","url":"https://…/reference.png"}`。签发响应中只有写入地址，最终 URL 以确认响应为准。PUT 后即使浏览器没收到 COS 响应，客户后端也可用同一 ID 确认；临时对象尚未到达时返回 `upload_not_found`。确认最晚可在签名到期后 10 分钟内发起，审核拒绝或图片不符后须重新申请。已完成的确认可幂等重查。

确认后的 URL 可公开读取，服务端会在生成入口校验新上传资产归属。最终 URL 不受 PUT 签名有效期限制，当前不约定固定保留期限。不要把临时上传签名写入日志或转发给其他会话。

- 生图 `POST /openapi/images/generate` 使用确认返回的 `url`，放进 `image_urls`。
- 视频方案 `POST /openapi/agent/chat_stream` 或 `chat_submit` 使用确认返回的 `upload_id`，放进 `reference_image_upload_ids`。例如 `{"message":"用产品图做视频方案","video_plan":true,"stream":false,"reference_image_upload_ids":["…"]}`。最多 9 个 ID，实际参考图数量由选用模型决定。生成批准继续使用既有的 `pending_action`。


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
