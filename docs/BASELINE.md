# FP4-Local Reading 生产基线 · 2026-11-21

公开发行标签为 `t5820-fp4local-prefill-20261121`。本仓库以源码补丁重建。生产原二进制 SHA256 为 `9d21ba8b74cdfcc412c3165989f3b780adb5d38c7f6c64787150b235edcabd73`；编译器、绝对路径和链接过程会影响新构建哈希。各台机器实际运行的二进制摘要保存在 bin/SHA256SUMS。

| 项目 | 冻结值 |
|---|---|
| Engine | 0.1.59.1 CUDA 派生；上游 13eedf552417a6a791a7d13c6597e24300ee3a09；本地派生源 5488495912e19dbe29afb6832f4a0dac45361828，差异随 patches/engine.patch 提供 |
| Server | 同一上游原生 Server，附模型 ID 验证与 Hermes reasoning 历史兼容补丁；完整文件摘要见 manifests/source.sha256 |
| 转换 | 固定 llama.cpp 3cf03257f219afbe7334045ff7c6a06ac68c627d，NVIDIA checkpoint b9ce18a6887e18c089fdea8509a33e63429a3300 |
| 模型 | NVIDIA FP4-Local QAD，24,576 个 NVFP4 专家，原生 NVFP4 PLE Direct，同 checkpoint 的 Dense/Embedding、MTP，CJK 草稿词表 |
| GPU 和 KV | 单 RTX 5060 Ti 16 GB；BF16 KV；最大 262144；GPU resident 32768 |
| 调度 | 18 Workers；10 个完整物理核及其 SMT 范围，9 个物理核给 workers；CPUQuota 2000%；1 活跃、4 等待 |
| 专家、推测 | 全专家 RAM 驻留、GPU cache auto、VRAM reserve 1248 MiB；MTP spec=4、spec-min-p=0.65 |
| Reading / 快照 | Prefill auto、STRATA_PF_GROUP_SCRATCH=1、conversation-cache-mib 5120、最小 8192 tokens |
| 资源 | cgroup MemoryMax=85 GiB，MemorySwapMax=0；原生 memory-limit-mib=87040 |
| 控制向量与接口 | 默认 On，project、scale 1、4–44、per-layer；Strata 原生 API，端口 10001，Bearer 认证，默认 Thinking Off |

**生产机观测。** 在 150,324 token 的同一冷读上，临时工作区按专家分组复用后，Reading 从 231.47 秒降至 214.37 秒（649.4 → 701.2 tok/s，各一次）。切换图片后返回 150,349 token 主会话，复用 150,319，只新读 30，首 token 1.303 秒。长测试期间 cgroup 峰值 79.95 GiB，最低采样宿主可用内存 9.62 GiB、空闲显存 944 MiB，OOM 和 Strata Swap 均为 0。这些是参考机测量；不同显存占用、上下文及路由会改变分块、吞吐和缓存命中率。
