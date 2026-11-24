# 使用与接入

在仓库根目录用 `python3 scripts/native.py status` 检查 loaded，`python3 scripts/native.py models` 查看模型 ID，`python3 scripts/native.py smoke` 发送一次短文本请求。status 和 models 不生成 token。

Hermes 中选择 OpenAI-compatible Chat Completions provider。Base URL 为 `http://<服务地址>:10001/v1`，API Key 从本机 secrets/api.key 交给受信任客户端。兼容 Model ID 为 `t5820-strata-qwen3.8-iq3s-bf16-256k`。正式主 ID 为 `t5820-strata-qwen3.8-fp4-local-qad-bf16-256k`。原有 IQ3_S、NVFP4 和 INT8 名称均保留为兼容别名。与原站点迁移时只有继续保留地址、端口和同一个密钥才能让现有客户端直接使用。

以下示例在服务机本地使用默认监听地址执行。密钥通过 curl 的标准输入传入，避免出现在命令行参数中。SSE 客户端分别处理 reasoning_content、content 和 tool_calls；流式工具参数须按调用索引拼接后再解析 JSON。

```bash
BASE=http://127.0.0.1:10001
printf 'Authorization: Bearer %s\n' "$(cat secrets/api.key)" | \
  curl --fail-with-body -sS -N -H @- -H 'Content-Type: application/json' \
  "$BASE/v1/chat/completions" -d '{
    "model":"t5820-strata-qwen3.8-iq3s-bf16-256k",
    "messages":[{"role":"user","content":"用一句话解释前缀缓存。"}],
    "reasoning_effort":"none","stream":true,"max_tokens":128
  }'
```

Thinking Off 使用 none，On 可传 low、medium、xhigh；具体思考量由原生 Server 和模型控制。思考和正文共享输出预算。工具按 OpenAI tools/function schema 发送，助手历史应保留 tool_calls、对应 tool_call_id 和原有 reasoning 字段。图片按 content 数组发送 text 与 image_url；本机小图可用 data URL。续聊保持历史前缀和模板稳定，原生服务会尽可能恢复 KV。引擎重载会清空内存快照。当前最多一条请求计算，最多四条等待。

监控用原生 /metrics 与 /health；已安装 Strata CLI 的机器可运行 `strata monitor --url http://127.0.0.1:10001`。只监听指定 LAN 地址时使用相应可达地址；需要本地转发时可通过 SSH 登录隧道将远端监听地址映射到客户端回环。将请求、日志或截图发给他人前去掉认证头、提示内容和机器标识。

如果当前只需要原生 Reading、吞吐或缓存数据，可直接在仓库根目录运行下面的只读命令；它复用安装时生成的地址和本机凭据：

```bash
python3 - <<'PY'
import sys
sys.path.insert(0, "scripts")
from native import api
m = api("/metrics")
print("live:", m.get("live"))
print("engine:", m.get("engine"))
PY
```
