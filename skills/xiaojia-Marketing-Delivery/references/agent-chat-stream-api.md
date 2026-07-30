# 小加 Agent Chat Stream API 接入文档

本文档描述 `xiaojia-Marketing-Delivery` 调用小加 Agent 的稳定流式接口。适用于 AI Agent、Skill、自动化宿主和能够消费 HTTP SSE 的服务端程序。

## 1. 接口定位

- 接口：`POST /openapi/agent/chat_stream`
- 鉴权：Bearer API Key
- 请求：JSON
- 流式响应：Server-Sent Events（SSE）
- 默认生产地址：`https://justailab.com`
- Skill 环境变量：`JUSTAI_OPENAPI_BASE_URL`

推荐始终从环境变量读取地址和 API Key：

```bash
export JUSTAI_OPENAPI_BASE_URL="${JUSTAI_OPENAPI_BASE_URL:-https://justailab.com}"
export JUSTAI_OPENAPI_API_KEY="YOUR_API_KEY"
```

不要把 API Key 写进代码、日志、Skill 文档或提交记录。

## 2. 最小可用请求

`curl` 必须使用 `-N` 或 `--no-buffer`，否则客户端缓冲可能让流式响应看起来像一次性返回。

```bash
curl -N --no-buffer \
  "${JUSTAI_OPENAPI_BASE_URL}/openapi/agent/chat_stream" \
  -H "Authorization: Bearer ${JUSTAI_OPENAPI_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  --data-raw '{
    "message": "帮我做一份咖啡店开业营销方案",
    "stream": true
  }'
```

典型响应：

```text
event: meta
data: {"conversation_id":"cvt_123"}

event: message
data: {"content":"下面是咖啡店开业营销方案。"}

: ping

event: result
data: {"content_type":"plan","data":{"pages":[]}}

event: done
data: {"finish_reason":"stop"}

```

`: ping` 是 SSE 注释心跳，不是业务事件，调用方应忽略。

## 3. 请求头

| Header | 必填 | 值 | 说明 |
| --- | --- | --- | --- |
| `Authorization` | 是 | `Bearer <API_KEY>` | API Key 由登录流程或运行环境注入 |
| `Content-Type` | 是 | `application/json` | 请求体必须是 JSON 对象 |
| `Accept` | 建议 | `text/event-stream` | 明确请求 SSE |

## 4. 请求参数

| 字段 | 类型 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- | --- |
| `message` | string | 条件必填 | `""` | 本轮用户输入；普通请求必填，提交表单时允许为空；首尾空白会被移除 |
| `conversation_id` | string | 否 | `""` | 续聊时传上一轮 `meta` 或 `input_required` 返回的会话 ID |
| `stream` | boolean | 否 | `true` | `true` 返回 SSE；必须传 JSON 布尔值，不能传字符串 `"true"` |
| `project_id` | string 或 string[] | 否 | `[]` | 限定一个或多个资料库项目 |
| `skill_id` | string 或 string[] | 否 | `[]` | 预加载一个或多个小加内部 Skill |
| `form_id` | string | 条件必填 | `""` | 回答 `input_required` 时传入 |
| `form_data` | object | 否 | `{}` | 表单字段值，采用扁平的 `字段 key -> 值` 结构；非空时必须同时提供 `form_id` |
| `reference_conversation_id` | string 或 string[] | 否 | `[]` | 引用当前用户有权访问的历史会话 |
| `reference_conversation_url` | string 或 string[] | 否 | `[]` | 通过小加会话 URL 引用历史会话 |

兼容字段 `project_ids`、`skill_ids`、`reference_conversation_ids`、`reference_conversation_urls` 仍接受字符串数组。新调用方优先使用上表中的字段名；多个值直接给对应字段传数组。

### 参数校验规则

- 请求体必须是 JSON 对象。
- `message` 必须是字符串。
- `conversation_id` 和 `form_id` 必须是字符串。
- `stream` 必须是 JSON 布尔值。
- ID/URL 数组中的每个元素都必须是字符串。
- `form_data` 必须是 JSON 对象。
- `form_data` 非空时必须同时提供 `form_id`。
- `message` 为空时必须提供 `form_id`。
- 续聊、表单和引用会话只能访问当前 API Key 所属用户有权访问的会话。

## 5. 常用请求

### 5.1 新建会话

新会话不要自行生成 `conversation_id`，保存服务端 `meta` 事件返回的值。

```json
{
  "message": "帮我生成一份新品 campaign plan",
  "stream": true
}
```

### 5.2 自然语言续聊

```bash
curl -N --no-buffer \
  "${JUSTAI_OPENAPI_BASE_URL}/openapi/agent/chat_stream" \
  -H "Authorization: Bearer ${JUSTAI_OPENAPI_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  --data-raw '{
    "message": "把表达调整得更适合小红书种草",
    "conversation_id": "cvt_123",
    "stream": true
  }'
```

同一轮创作必须复用原 `conversation_id`，否则会创建新会话并丢失当前上下文。

### 5.3 指定资料库和 Skill

```json
{
  "message": "基于品牌资料生成三条小红书图文笔记",
  "project_id": ["fld_brand", "fld_product"],
  "skill_id": ["skill_xhs_notes"],
  "stream": true
}
```

`project_id` 和 `skill_id` 只影响本轮可用上下文或能力，不会在响应里暴露内部配置。

### 5.4 引用历史会话

```json
{
  "message": "沿用参考会话的品牌语气，生成本次新品内容",
  "reference_conversation_id": ["cvt_reference_1"],
  "reference_conversation_url": [
    "https://justailab.com/pages/agent/preview?conversation_id=cvt_reference_2"
  ],
  "stream": true
}
```

### 5.5 提交表单

当服务端返回 `input_required` 时，保存 `conversation_id`、`form_id` 和 `fields`。向用户收集答案后，把字段值按 `fields[].key` 组成扁平对象：

```bash
curl -N --no-buffer \
  "${JUSTAI_OPENAPI_BASE_URL}/openapi/agent/chat_stream" \
  -H "Authorization: Bearer ${JUSTAI_OPENAPI_API_KEY}" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  --data-raw '{
    "message": "",
    "conversation_id": "cvt_123",
    "form_id": "form_456",
    "form_data": {
      "shop_name": "梧桐咖啡",
      "budget": 5000
    },
    "stream": true
  }'
```

AI 宿主没有网页点击能力时，不需要模拟点击。宿主只需：

1. 把 `input_required` 中的字段转成自然语言问题。
2. 从用户回答中提取字段值。
3. 使用原 `conversation_id + form_id + form_data` 继续请求。
4. 无法可靠提取时继续向用户确认，不要猜测必填值。

## 6. SSE 帧格式

每个业务事件由 `event:` 和 `data:` 两行组成，以空行结束：

```text
event: message
data: {"content":"第一段内容"}

```

处理要求：

- 按空行组装完整 SSE 帧，不能假设一次网络读取就是一条事件。
- 同一帧可能跨多个 TCP/HTTP chunk。
- 一个 chunk 也可能包含多条事件。
- 同时兼容 `\n\n` 和 `\r\n\r\n`。
- `data` 是 JSON；解析后再按 `event` 分发。
- `: ping` 是注释心跳，直接忽略。
- 按到达顺序拼接所有 `message.content`，不要只保留最后一段。
- 收到 `done` 才结束本轮；HTTP 200 本身不代表业务成功。
- 每条流只会有一个公开 `done` 终态。

## 7. 公开事件

对外只公开六类事件：

| 事件 | 是否可能多次 | 用途 |
| --- | --- | --- |
| `meta` | 最多一次 | 返回 `conversation_id` |
| `message` | 可以多次 | 用户可见的文本增量 |
| `input_required` | 最多一次 | 本轮需要用户补充结构化信息 |
| `result` | 最多一次 | 最终结构化方案、笔记或图片 |
| `error` | 最多一次 | 本轮错误；部分成功时可能出现在 `result` 之后 |
| `done` | 恰好一次 | 唯一终态 |

内部思考、工作流进度、分支、Prompt、模型、provider、任务 ID、计费收尾和隐藏消息不会通过该接口公开。

### 7.1 `meta`

```text
event: meta
data: {"conversation_id":"cvt_123"}

```

收到后立即保存 `conversation_id`，后续续聊和表单提交都需要复用它。

### 7.2 `message`

```text
event: message
data: {"content":"这是第一段可见文本。"}

```

`content` 固定为字符串。调用方应按事件到达顺序追加：

```text
visible_text = visible_text + event.data.content
```

服务端不会把 `thinking`、`workflow_progress`、`guide`、`auto_hide` 或内部配置映射为公开 `message`。

### 7.3 `input_required`

```text
event: input_required
data: {
  "conversation_id": "cvt_123",
  "form_id": "form_456",
  "title": "资料确认",
  "description": "请补充以下信息",
  "fields": [
    {
      "key": "shop_name",
      "type": "input",
      "title": "门店名称",
      "required": true,
      "default": "",
      "placeholder": "请输入门店名称"
    }
  ]
}

event: done
data: {"finish_reason":"input_required"}

```

顶层字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `conversation_id` | string | 当前会话 ID |
| `form_id` | string | 下一次提交必须原样传回 |
| `title` | string | 表单标题，可能为空 |
| `description` | string | 表单说明，可能为空 |
| `fields` | array | 对外可填写字段 |

每个 `fields[]` 固定为：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `key` | string | 写入 `form_data` 时使用的键 |
| `type` | string | `input`、`upload`、`textarea`、`number` 之一 |
| `title` | string | 展示给用户的字段名 |
| `required` | boolean | 是否必填 |
| `default` | string/number/boolean/array/null | 默认值；不支持的内部值会投影为空字符串 |
| `placeholder` | string | 输入提示，可能为空 |

`input_required` 是已确认的最终表单，不是内部过程快照。调用方不要读取或依赖表格之外的字段。

### 7.4 `result`

```text
event: result
data: {
  "content_type": "notes",
  "data": {
    "components": []
  }
}

```

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `content_type` | string | `plan`、`notes`、`images` 之一 |
| `data` | object 或 array | 最终业务结果；具体组件可随业务能力扩展 |

类型含义：

- `plan`：营销方案、页面方案或 Markdown 方案。
- `notes`：小红书笔记、图文笔记等结构化内容。
- `images`：最终图片结果，通常是包含图片 URL 的对象或数组。

调用方应优先保留并交付完整 `data`，不要只从中提取一段摘要。服务端只提交最后一份已确认的结构化结果，中间草稿不会作为公开 `result` 返回。

图片示例：

```text
event: result
data: {
  "content_type": "images",
  "data": [
    {"url": "https://example.com/final.png"}
  ]
}

```

### 7.5 `error`

```text
event: error
data: {"code":"internal_error","message":"internal server error"}

event: done
data: {"finish_reason":"error"}

```

| 错误码 | 含义 | 建议处理 |
| --- | --- | --- |
| `method_not_allowed` | 请求方法不是 `POST` | 改用 `POST`，不要重试原请求 |
| `missing_api_key` | 缺少 Authorization Bearer Key | 补充 API Key |
| `invalid_api_key` | API Key 不存在、格式错误或校验失败 | 重新登录或更换有效 Key |
| `disabled_api_key` | API Key 已停用 | 重新启用或更换 Key |
| `expired_api_key` | API Key 已过期 | 重新登录或申请新 Key |
| `invalid_request` | JSON、字段类型或业务参数不合法 | 修正请求后再提交 |
| `internal_error` | 内部 Agent、模型或流式链路异常 | 先检查本轮是否已有结果，再按业务幂等策略决定是否重试 |

流式请求中，除方法错误可能使用 HTTP 405 外，鉴权、参数和业务错误也可能使用 HTTP 200 建立 SSE，再通过 `error + done(error)` 表达失败。因此不能只判断 HTTP 状态码。

### 7.6 `done`

成功结束：

```text
event: done
data: {"finish_reason":"stop"}

```

等待用户输入：

```text
event: done
data: {"finish_reason":"input_required"}

```

错误结束：

```text
event: done
data: {"finish_reason":"error"}

```

| `finish_reason` | 处理 |
| --- | --- |
| `stop` | 本轮正常结束，交付累计文本和最终结果 |
| `input_required` | 展示表单问题，等待用户回答后续聊 |
| `error` | 展示安全错误；如果之前收到 `result`，仍需保留并交付该部分结果 |

## 8. 部分成功和异常终止

批量生图等任务可能先成功生成部分已计费内容，随后因积分不足或其他原因停止：

```text
event: result
data: {"content_type":"images","data":[{"url":"https://example.com/paid.png"}]}

event: error
data: {"code":"internal_error","message":"积分不足，剩余图片生成已暂停。"}

event: done
data: {"finish_reason":"error"}

```

调用方必须同时处理结果和错误：

- 不要因为最终是 `done(error)` 就丢弃前面的 `result`。
- 向用户交付已生成内容，同时说明剩余任务未完成。
- 不要自动重放整轮请求，否则可能重复生成和重复扣费。

如果内部流在完成前断开，服务端会丢弃尚未确认的结构化候选，返回：

```text
event: error
data: {"code":"internal_error","message":"internal server error"}

event: done
data: {"finish_reason":"error"}

```

此前已经公开发送的 `message` 文本可能仍存在，但不能把未收到的 `result` 当成完成结果。

## 9. 推荐消费状态机

```text
初始化:
  conversation_id = ""
  messages = []
  final_result = null
  input_required = null
  terminal_error = null

逐帧消费:
  注释帧 ": ping"       -> 忽略
  meta                   -> 保存 conversation_id
  message                -> messages 追加 content
  input_required         -> 保存表单
  result                 -> 保存完整结构化结果
  error                  -> 保存错误，但不要清空 final_result
  done(stop)             -> 交付 messages + final_result
  done(input_required)   -> 向用户收集表单字段
  done(error)            -> 交付已有 final_result，再报告错误
```

连接结束但没有收到 `done` 时，按异常终止处理，不要自行补造成功终态。

## 10. AI/Skill 宿主边界

OpenAPI 会逐块发送 SSE，但用户能否实时看到增量内容取决于 AI 宿主是否支持 Tool/Skill 的流式结果。

- 宿主支持工具流式输出：边收 `message` 边展示。
- 宿主能消费长连接但不能增量展示：完整消费 SSE，收到 `done` 后一次性交付聚合结果。
- 宿主不适合维护长连接：继续使用 Skill 现有的 `chat.py`/`chat_result.py`，即 `chat_submit + chat_result` 流程。

本接口不要求网页按钮，也不要求官方 CLI。遇到 `input_required` 时，AI Agent 可通过自然语言向用户收集答案，再提交结构化 `form_data`。

## 11. 超时、断线和重试

- 生成方案、笔记和图片可能持续数分钟，客户端读取超时建议不低于 300 秒。
- 心跳只用于保持连接，不表示业务有新进展。
- 收到 `done` 前不要主动关闭连接。
- 客户端断线不等于服务端任务已经取消。
- 当前请求没有公开的幂等键。收到任何 `meta`、`message` 或 `result` 后，不要自动重放整轮请求。
- `invalid_request` 和 API Key 错误应先修正，不要指数重试。
- `internal_error` 只有在调用方能保证业务幂等、并确认不会重复生成或扣费时才重试。

## 12. Skill 结果交付

完成态应按以下优先级交付：

1. 完整保留 `result.data`。
2. 按顺序拼接并返回所有 `message.content`。
3. `result` 中有图片时直接展示图片，并保留原始 URL。
4. 返回网页版结果链接：

```text
https://justailab.com/pages/agent/preview?conversation_id=<conversation_id>
```

5. 部分成功时先交付已生成结果，再说明 `error.message`。

不要把内部 SSE、心跳、错误堆栈、API Key 或未公开工作流字段直接返回给用户。
