# T5820 · Qwen3.8-Flash-Next FP4-Local

这是为 **Hermes Agent 长时间处理复杂任务**维护的本地推理后端。参考机器是一套纯“二手”非主流generation的硬件组合，包括:Dell Precision T5820，配备 i9-10940X（从二手市场淘的）、96 GB RAM（7条不同大小的混插内存，没有一条是一样的，5条16G+2条8G） 和一张 RTX 5060 Ti 16 GB（中规中矩的二线品牌）。典型任务是让 Agent 参考并读完若干份长案例，调用工具核对资料，中途查看若干张图（考研多模态能力），再回到原始材料继续推理。对使用者而言，关键是回到主会话要等多久、前文能否接上，以及这项任务能否在主机的内存预算内正常结束。整个项目的适用场景是处理复杂的长链综合性任务，上下文设置为256K（也就是Qwen3.8-Flash-Next官方支持的最大值），只求尽量高的质量和能够接受的速度来处理真实的复杂任务并返回高质量的尽量不需要返工的输出结果，不追求哗众取宠的傻鸟骑车，也不追求所谓的极致速度和光速思考。

模型采用 NVIDIA Qwen3.8-Flash-Next FP4-Local QAD。权重转换、NVFP4 PLE、MTP、会话缓存以及支持 SSE、Thinking、工具和图片的原生 API 来自 Strata。下面的引擎和协议改动以本仓库锁定的上游提交 `13eedf55` 为对照。[上游源码](https://github.com/Niko1221/Strata/tree/13eedf552417a6a791a7d13c6597e24300ee3a09)

## 这个派生版改了什么

- **长上下文的真 BF16 KV。** 我们补上了 FP32 直接舍入到 BF16 的写入路径，以及 CUDA Attention、主存与显存之间的分页传输和会话快照对 BF16 的支持。解码时，多个 CUDA 线程块并行读取选中的 KV，再用 FP32 合并结果。主模型和 MTP 都能使用这条路径。补丁附有 BF16 原始位模式与分页回归测试。[引擎补丁](patches/engine.patch)
- **为 Cascade Lake 补上 NVFP4 专家内核。** i9-10940X 支持 AVX-512 VNNI，但缺少 VBMI。我们给 CPU 专家计算增加了无需 VBMI 的 VNNI 路径，并保留 AVX2 回退。这样，显卡缓存之外的专家也能利用这颗 CPU 的指令集，继续执行完整的专家计算。[CPU 与 CUDA 实现](patches/engine.patch)
- **让 Hermes 续聊能接回原来的思考历史。** 某些客户端把上一轮 Thinking 放在 `reasoning`，而原生模板读取 `reasoning_content`。我们在原生 Server 接受这个别名，保留标准字段的优先级。在同一组两轮请求中，修复前续轮重读 13,047 个 token；修复后复用 13,034 个，只补读 20 个，首 token 从 22.679 秒降到 0.572 秒。[历史兼容补丁](patches/server-history.patch)

## 如何配合 T5820 的硬件

- **CPU 与单卡分工。** 在 14 核 28 线程中，18 个专家 Worker 使用 9 个完整物理核及其 SMT 线程，另留一个物理核给主线程，余下 4 核留给 Ubuntu 和其他服务。非 GPU 驻留专家放在 RAM，显卡按可用空间自动缓存专家；RTX 5060 Ti 在这台机器上使用 PCIe 3.0 ×8。长会话实测中，常规专家文件读取为零，PLE 仍使用 Direct I/O。
- **把显存留给长输入。** 在 16 GB 显存上启用上游已有的专家分组临时区复用，让 Prefill 能一次处理更大的分块。同一份 150,324-token 材料，启用前后各做一次冷读，耗时从 231.47 秒降至 214.37 秒，节省 17.10 秒。这项收益发生在读取阶段。[实装参数与测量](docs/BASELINE.md)

## 一次生产场景验证

在“长文本 → 看图 → 回到长文本”验收中，返回主会话时输入共 **150,349 tokens**，引擎从快照复用 **150,319**，只补读 **30**。模型在 **1.303 秒**后给出首个 token，并成功召回先前埋入材料的标记。这组测试的 cgroup 内存峰值为 **79.95 GiB**，Strata Swap 和 OOM 均为零。该次实测长度约 150K，服务配置的上下文上限为 262,144。[实装基线](docs/BASELINE.md)

生产验收同时关注回答能否完成、工具调用能否解析、上下文能否续接，以及进程异常后能否恢复。Decode tok/s 是其中一项指标。部署包提供带密钥认证的原生接口、单实例 systemd 服务、85 GiB 内存硬限制、零 Swap、资产校验及版本回退步骤。[维护与回退](docs/OPERATIONS.md) · [验证范围](docs/VALIDATION.md)

## 部署与使用

| 从这里开始 | 内容 |
|---|---|
| [部署](docs/DEPLOY.md) | 从干净 Ubuntu 构建、下载、转换、校验、注册服务和验证 READY |
| [使用](docs/USE.md) | 认证、Hermes、流式请求、监控和多轮对话 |
| [维护](docs/OPERATIONS.md) | 启停、控制向量、参数、升级、备份、故障定位和回退 |
| [实装基线](docs/BASELINE.md) | 固定版本、关键开关、实测资源与性能、验收范围 |
| [发布验证](docs/VALIDATION.md) | 已执行的构建与协议测试、生产实测来源和异机验收范围 |

部署针对 Linux x86_64、SM120 和上述参考硬件。默认监听本机 127.0.0.1:10001。每台机器使用自己的密钥。权重由用户从固定源按原许可获取。[NVIDIA 官方权重](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-FP4-Local/tree/b9ce18a6887e18c089fdea8509a33e63429a3300) · [Strata 固定上游](https://github.com/Niko1221/Strata/tree/13eedf552417a6a791a7d13c6597e24300ee3a09)
