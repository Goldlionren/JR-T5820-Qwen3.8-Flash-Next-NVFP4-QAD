# FP4-Local 长文生产基线 · 2026-11-24

公开发行标签为 `t5820-fp4local-long-prefill-20261124`。本仓库以源码补丁重建。生产原二进制 SHA256 为 `fa89aba919bfa95ee6fed79e0778219e1f533e52d5d64845ba5a90264dbbed9d`；编译器、绝对路径和链接过程会影响新构建哈希。各台机器实际运行的二进制摘要保存在 bin/SHA256SUMS。

| 项目 | 冻结值 |
|---|---|
| Engine | 0.1.59.1 CUDA 派生；上游 13eedf552417a6a791a7d13c6597e24300ee3a09；本地派生源 b035c1e0ca959d02b0c34e4f32e3f2f476ae481e，依次应用 patches/engine.patch 和 patches/long-prefill.patch |
| Server | 同一上游原生 Server，附模型 ID 验证与 Hermes reasoning 历史兼容补丁；完整文件摘要见 manifests/source.sha256 |
| 转换 | 固定 llama.cpp 3cf03257f219afbe7334045ff7c6a06ac68c627d，NVIDIA checkpoint b9ce18a6887e18c089fdea8509a33e63429a3300 |
| 模型 | NVIDIA FP4-Local QAD，24,576 个 NVFP4 专家，原生 NVFP4 PLE Direct，同 checkpoint 的 Dense/Embedding、MTP，CJK 草稿词表 |
| GPU 和 KV | 单 RTX 5060 Ti 16 GB；BF16 KV；最大 262144；GPU resident 32768 |
| 调度 | 18 Workers；10 个完整物理核及其 SMT 范围，9 个物理核给 workers；CPUQuota 2000%；1 活跃、4 等待 |
| 专家、推测 | 全专家 RAM 驻留、GPU cache auto、VRAM reserve 1248 MiB；MTP spec=4、spec-min-p=0.65 |
| Reading / 快照 | Prefill auto、STRATA_PF_GROUP_SCRATCH=1、conversation-cache-mib 5120、最小 8192 tokens |
| 资源 | cgroup MemoryMax=85 GiB，MemorySwapMax=0；原生 memory-limit-mib=87040 |
| 控制向量与接口 | 默认 On，project、scale 1、4–44、per-layer；Strata 原生 API，端口 10001，Bearer 认证，默认 Thinking Off |

## 两个引擎的选用

默认 `b035c1e` 增加四个 query-head warp 分组、按路由过滤预取、下一层专家预暂存、95% 缓存借槽，以及 CPU 专家 Prefill 分流（输入阈值 8192、每组最多 64 行）。六个环境开关见[部署模板](../config/strata.template.json)。保留候选 `5488495` 的完整源码和配置在旧标签 `t5820-fp4local-prefill-20261121`，原机二进制 SHA256 为 `9d21ba8b74cdfcc412c3165989f3b780adb5d38c7f6c64787150b235edcabd73`。

同一台 T5820 的固定四轮长文任务（每版两次独立加载），客户端平均耗时从 93.05 秒降到 74.06 秒。独立的 256-token 热重放 Decode 从 45.25 降至 42.75 tok/s。实际 Hermes 会话各测一次，新版累计处理 13 个请求，用时 410.7 秒，旧版处理 16 个，用时 530.3 秒；生成量分别为 10,776 和 12,679 tokens。两条真实会话的工作量不同，不能据此承诺固定提速。

**以下是 2026-11-21 的历史基线观测。** 在 150,324 token 的同一冷读上，临时工作区按专家分组复用后，Reading 从 231.47 秒降至 214.37 秒（649.4 → 701.2 tok/s，各一次）。切换图片后返回 150,349 token 主会话，复用 150,319，只新读 30，首 token 1.303 秒。长测试期间 cgroup 峰值 79.95 GiB，最低采样宿主可用内存 9.62 GiB、空闲显存 944 MiB，OOM 和 Strata Swap 均为 0。这些是参考机测量；不同显存占用、上下文及路由会改变分块、吞吐和缓存命中率。
