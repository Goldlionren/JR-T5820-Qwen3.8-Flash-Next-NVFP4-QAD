# 日常维护

所有 systemctl 和 journalctl 命令以安装此服务的普通用户运行，并带 --user。运行命令前进入安装仓库。切换配置、引擎或模型前先让客户端暂停提交，从 /metrics 的 live.state、queued 和 /v1/status 的 activity.in_flight 确认空闲。重启会删除内存中的对话前缀和快照。

| 操作 | 命令 |
|---|---|
| 状态、PID、近日日志 | `systemctl --user status strata-fp4-local.service` |
| 模型是否已加载 | `python3 scripts/native.py status` |
| 启动 / 停止 / 重启 | `systemctl --user start strata-fp4-local.service` / `systemctl --user stop strata-fp4-local.service` / `systemctl --user restart strata-fp4-local.service` |
| 自动启动状态 | `systemctl --user is-enabled strata-fp4-local.service`、`loginctl show-user "$USER" -p Linger` |
| 取消自动启动并停止 | `systemctl --user disable --now strata-fp4-local.service` |
| 查看启动参数与限制 | `systemctl --user cat strata-fp4-local.service`、`systemctl --user show strata-fp4-local.service -p MemoryMax -p MemorySwapMax -p CPUQuotaPerSecUSec` |
| 实时日志 | `journalctl --user -fu strata-fp4-local.service`、`tail -f runtime/engine.log` |
| 验证当前模型及程序 | `python3 scripts/assets.py check`；全量重算 `python3 scripts/assets.py record` |

## 修改参数和控制向量

生成后的 strata.json 是本站点的运行配置。args 中每个选项和值分别占一个 JSON 数组元素；env 是 Engine 的环境，sampling 是原生采样默认值。参考模板为 config/strata.template.json。原生参数的完整说明可用 `bin/strata --help` 和固定版本的 src/docs/DETAILS.md 查阅。备份配置并检查语法：

```bash
mkdir -m 700 -p runtime/backups
cp -p strata.json "runtime/backups/strata.$(date +%Y%m%d-%H%M%S).json"
cp -p strata-fp4-local.service "runtime/backups/unit.$(date +%Y%m%d-%H%M%S)"
# 编辑 strata.json；如改 cgroup、CPU 或 Prefill 开关也编辑已链接的 unit。
python3 -m json.tool strata.json >/dev/null
systemd-analyze --user verify "$PWD/strata-fp4-local.service"
systemctl --user daemon-reload
systemctl --user restart strata-fp4-local.service
python3 scripts/native.py status
```

- **线程**：--pool-workers 和 --pool-cores 成对修改，worker 数等于列表长度，排除 Host Core。保持 unit 的 CPUAffinity 覆盖 host 及所有 workers。CPUQuota 控制 CPU 时间，后者与亲和性分别生效。
- **上下文**：--max-context 为最大 token 数，--kv-resident 为 GPU 驻留窗口，--kv bf16 为主 KV 格式。--conversation-cache-mib 和 --conversation-cache-min-tokens 控制多会话快照容量与准入，原生内存预算仍可能拒绝保存。
- **专家**：--resident-experts 请求全 RAM 驻留，--expert-cache auto 和 --vram-reserve-mib 控制 GPU 缓存与余量。--ple-io direct 使用原生 PLE 文件。观察 engine.log 中的驻留量、GPU 槽数和专家文件读取。
- **推测解码**：--draft mtp、--mtp 指向本模型生成的 MTP；窗口 --spec 与置信阈值 --spec-min-p 一起影响延迟和接受率。
- **内存/Reading**：--memory-limit-mib 是原生预算，unit 的 MemoryMax 是内核硬上限，MemorySwapMax=0。STRATA_PF_GROUP_SCRATCH=1 位于 unit。只回退这项时移除这条 Environment，daemon-reload、restart 并检查 loaded。--prefill auto 由可借用显存决定每块实际大小。
- **访问**：host 位于 strata.json；端口 10001 由 scripts/native.py 的启动及客户端共用。更改端口需要同步客户端与该脚本中的两个位置。API Key 使用 LoadCredential 从 secrets/api.key 装入，只允许服务用户读取；轮换时同时更新客户端并重载服务。
- **并发与多模态**：parallel、max_queue、queue_timeout、vision、最长静默等待和采样均为原生 Server 字段。增加并发会改变 KV 和显存预算。
- **控制向量**：`scripts/strata-cvec status`、`scripts/strata-cvec off`、`scripts/strata-cvec on`。On 加载上游固定向量（project，1.0，4–44 层）；Off 卸载向量。开关保存其他已编辑参数，按原生状态检查 READY；失败时恢复切换前配置。客户端需在切换期间保持暂停。切换前的配置位于 runtime/before-cvec.json。若只想对单个请求切换已加载的向量，可用原生 `experimental_speed_projection` 布尔字段。

## 诊断与回退

```bash
cg=$(systemctl --user show strata-fp4-local.service -p ControlGroup --value)
cat "/sys/fs/cgroup$cg"/memory.{current,peak,max,events,swap.current,swap.max}
grep MemAvailable /proc/meminfo
nvidia-smi
```

memory.events.max 表示遇到 cgroup 上限，oom 与 oom_kill 才是 OOM 事件。重载后核对实际 KV、Workers、MTP 和专家驻留，API 的 loaded=true、Bearer 认证和模型别名。若新配置不能 READY，停止服务，复制刚才保存的 JSON 和 unit，daemon-reload、启动及检查 READY。密钥、真实资产和日志由操作者单独备份，不写入 Git。升级发布版时使用独立目录重新构建，核验资产，保留旧目录与 unit，以便把 unit 链接切回；两套模型应串行加载。

更大内存安装后先核实 /proc/meminfo 的实际 MemTotal、MemAvailable，再分别规划 cgroup、--memory-limit-mib、快照及 OS 预留。Swap 不计入物理容量。更换其他模型时先确认冻结引擎明确支持该模型架构、专家格式、Tokenizer、PLE、Vision 和 MTP；单个普通 GGUF 不能直接充当此基线的 native Pack。在独立目录用该模型固定版本及相应上游转换器生成整套资产，重建该版本的已验证清单及配置，保留原模型回退。新模型需要小上下文 READY、认证、短输出和资源验收后再扩大上下文。
