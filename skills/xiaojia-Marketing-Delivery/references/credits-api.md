# 小加积分查询 API 接入文档

本文档描述 `xiaojia-Marketing-Delivery` 使用的积分余额和积分消耗明细查询接口。积分接口已经存在，本次只整理对外接入方式，不新增或修改积分业务逻辑。

## 1. 接口概览

| 接口 | 方法 | 说明 |
| --- | --- | --- |
| `/openapi/credits/balance` | `POST` | 查询当前账户的总积分、可用积分和预占积分 |
| `/openapi/credits/usage` | `POST` | 分页查询当前账户已经发生的扣费和退款明细 |

两个接口：

- 使用与 Agent Chat Stream 相同的 Bearer API Key。
- 只返回当前 API Key 所属账户的数据。
- 返回普通 JSON，不返回 SSE。
- 不需要 `Session-Id`。

默认生产地址为 `https://justailab.com`，推荐从 Skill 环境变量读取：

```bash
export JUSTAI_OPENAPI_BASE_URL="${JUSTAI_OPENAPI_BASE_URL:-https://justailab.com}"
export JUSTAI_OPENAPI_API_KEY="YOUR_API_KEY"
```

不要把 API Key 写进代码、日志、文档或提交记录。

## 2. 请求头

| Header | 必填 | 值 |
| --- | --- | --- |
| `Authorization` | 是 | `Bearer <API_KEY>` |
| `Content-Type` | 建议 | `application/json` |

## 3. 查询积分余额

### 3.1 请求

```http
POST /openapi/credits/balance
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

接口没有请求体参数。

```bash
curl -sS -X POST \
  "${JUSTAI_OPENAPI_BASE_URL}/openapi/credits/balance" \
  -H "Authorization: Bearer ${JUSTAI_OPENAPI_API_KEY}" \
  -H "Content-Type: application/json"
```

### 3.2 成功响应

```json
{
  "status": "ok",
  "total_credits": 1000,
  "available_credits": 850,
  "reserved_credits": 150
}
```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status` | string | 成功时固定为 `ok` |
| `total_credits` | integer | 当前未过期权益中的剩余积分总额 |
| `available_credits` | integer | 当前可立即使用的积分，等于 `max(total_credits - reserved_credits, 0)` |
| `reserved_credits` | integer | 已被处理中任务预占、但尚未完成结算或释放的积分 |

注意：

- `reserved_credits` 是实时预占值，不是已经完成的消费。
- 极端情况下，权益到期或降级可能导致 `reserved_credits > total_credits`；此时 `available_credits` 为 `0`，预占值仍按真实数据返回。
- 判断能否发起新的付费任务时优先使用 `available_credits`，不要只看 `total_credits`。

## 4. 查询积分消耗明细

### 4.1 请求

```http
POST /openapi/credits/usage
Authorization: Bearer YOUR_API_KEY
Content-Type: application/json
```

请求体必须是 JSON 对象，所有字段均可选：

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `start_date` | string | 不限 | 起始日期，格式 `YYYY-MM-DD`，包含当天 `00:00:00` |
| `end_date` | string | 不限 | 截止日期，格式 `YYYY-MM-DD`，包含当天 `23:59:59` |
| `conversation_id` | string | 不限 | 只查询指定会话关联的扣费和退款 |
| `page` | integer | `1` | 页码，从 1 开始，最大 `10000` |
| `page_size` | integer | `20` | 每页条数，最大 `100` |

日期规则：

- `start_date` 和 `end_date` 可以单独提供。
- 两者同时提供时，`start_date` 不能晚于 `end_date`。
- 两者同时提供时，日期跨度不能超过 90 天。

### 4.2 查询最近一段时间

```bash
curl -sS -X POST \
  "${JUSTAI_OPENAPI_BASE_URL}/openapi/credits/usage" \
  -H "Authorization: Bearer ${JUSTAI_OPENAPI_API_KEY}" \
  -H "Content-Type: application/json" \
  --data-raw '{
    "start_date": "2026-07-01",
    "end_date": "2026-07-30",
    "page": 1,
    "page_size": 20
  }'
```

### 4.3 按会话查询

Agent Chat Stream 返回 `conversation_id` 后，可以用它查询该会话已经完成结算的积分记录：

```bash
curl -sS -X POST \
  "${JUSTAI_OPENAPI_BASE_URL}/openapi/credits/usage" \
  -H "Authorization: Bearer ${JUSTAI_OPENAPI_API_KEY}" \
  -H "Content-Type: application/json" \
  --data-raw '{
    "conversation_id": "cvt_123",
    "page": 1,
    "page_size": 100
  }'
```

### 4.4 成功响应

```json
{
  "status": "ok",
  "total": 2,
  "page": 1,
  "page_size": 20,
  "records": [
    {
      "action_type": "capture",
      "biz_type": "image",
      "credits": -10,
      "remark": "生成一张封面图",
      "conversation_id": "cvt_123",
      "occurred_at": "2026-07-30 10:20:30"
    },
    {
      "action_type": "refund",
      "biz_type": "image",
      "credits": 10,
      "remark": "生成失败，退回积分",
      "conversation_id": "cvt_123",
      "occurred_at": "2026-07-30 10:21:10"
    }
  ]
}
```

顶层字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `status` | string | 成功时固定为 `ok` |
| `total` | integer | 符合筛选条件的记录总数，不是当前页数量 |
| `page` | integer | 当前页码 |
| `page_size` | integer | 当前每页条数 |
| `records` | array | 当前页记录，按账务记录 ID 倒序排列，通常为最新记录优先 |

`records[]` 字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `action_type` | string | `capture` 表示扣费结算，`refund` 表示退款 |
| `biz_type` | string | 业务类型；常见值包括 `image`、`llm`、`video`、`agent_tool` |
| `credits` | integer | 带正负号的积分变动；扣费为负数，退款为正数 |
| `remark` | string | 本次积分变动说明，可能为空字符串 |
| `conversation_id` | string | 关联会话 ID；非会话场景可能为空字符串 |
| `occurred_at` | string | 发生时间，格式 `YYYY-MM-DD HH:mm:ss` |

不要根据 `action_type` 再次改变 `credits` 的正负号，服务端返回的值已经是最终净变动。

## 5. 余额与明细的关系

| 数据 | 应使用的接口 | 说明 |
| --- | --- | --- |
| 当前还能使用多少积分 | `/credits/balance` 的 `available_credits` | 已扣除处理中任务的预占 |
| 当前有多少积分处于处理中 | `/credits/balance` 的 `reserved_credits` | 可能随后结算，也可能释放 |
| 已经实际扣除了多少 | `/credits/usage` 的 `capture` 记录 | `credits` 为负数 |
| 已经退回了多少 | `/credits/usage` 的 `refund` 记录 | `credits` 为正数 |
| 某次会话消耗多少 | `/credits/usage` + `conversation_id` | 对记录中的 `credits` 求和 |

`usage` 只展示已经完成的扣费和退款，不展示 `reserve`、`release` 等临时中间态。因此：

- 任务仍在运行时，余额可能已经出现 `reserved_credits`，但明细尚未出现 `capture`。
- 任务完成结算后，预占会减少，明细会出现 `capture`。
- 任务失败释放预占时，不一定产生退款记录；只有已经扣费后再退回才会出现 `refund`。

## 6. 错误响应

```json
{
  "status": "error",
  "code": "invalid_request",
  "message": "start_date 不能晚于 end_date"
}
```

| 错误码 | 含义 | 建议处理 |
| --- | --- | --- |
| `method_not_allowed` | 请求方法不是 `POST` | 改用 `POST` |
| `missing_api_key` | 缺少 Bearer API Key | 补充 API Key |
| `invalid_api_key` | API Key 不存在、格式错误或校验失败 | 重新登录或更换有效 Key |
| `disabled_api_key` | API Key 已停用 | 重新启用或更换 Key |
| `expired_api_key` | API Key 已过期 | 重新登录或申请新 Key |
| `invalid_request` | 日期、分页或 JSON 参数不合法 | 根据 `message` 修正请求 |
| `internal_error` | 服务端异常 | 稍后重试或联系技术支持 |

这些接口返回普通 JSON：

- 方法错误使用 HTTP 405。
- 其他错误可能使用 HTTP 200，并通过 `status=error` 和 `code` 表达失败。
- 调用方必须同时判断 HTTP 状态码和响应体 `status`。

## 7. AI/Skill 使用规则

- 用户询问当前积分时，调用 `/credits/balance`，不要根据历史明细自行估算余额。
- 用户询问某次 Agent 对话或生成任务消耗时，优先使用 `conversation_id` 查询 `/credits/usage`。
- 需要解释“为什么余额减少但明细暂时没有记录”时，同时检查 `reserved_credits`。
- 不要高频轮询积分接口；任务执行期间按关键状态节点查询即可。
- 不要向用户输出 API Key、内部账户 ID、数据库字段或账务实现细节。
- 不要因为积分不足自动创建订单、充值或重复发起付费生成。

## 8. 相关文档

- [Agent Chat Stream API](agent-chat-stream-api.md)
