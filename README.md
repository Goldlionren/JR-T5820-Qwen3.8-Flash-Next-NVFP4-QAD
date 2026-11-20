# T5820 · Qwen3.8-Flash-Next FP4-Local

在一张 RTX 5060 Ti 16 GB 与 96 GB RAM 的 Dell Precision T5820 上运行 NVIDIA FP4-Local QAD。后端是 Strata 0.1.59.1 派生 CUDA 引擎，使用原生 HTTP Server、BF16 KV、原生 MTP 和 NVFP4 PLE。OpenAI 兼容接口支持 Hermes、SSE、Thinking、工具调用和图片输入。

| 从这里开始 | 内容 |
|---|---|
| [部署](docs/DEPLOY.md) | 从干净 Ubuntu 构建、下载、转换、校验、注册服务和验证 READY |
| [使用](docs/USE.md) | 认证、Hermes、流式请求、监控和多轮对话 |
| [维护](docs/OPERATIONS.md) | 启停、控制向量、参数、升级、备份、故障定位和回退 |
| [实装基线](docs/BASELINE.md) | 固定版本、关键开关、实测资源与性能、验收范围 |
| [发布验证](docs/VALIDATION.md) | 已执行的构建与协议测试、生产实测来源和异机验收范围 |

部署针对 Linux x86_64、SM120 和下文所列硬件条件。默认监听本机 127.0.0.1:10001。每台机器使用自己的密钥。权重由用户从固定源按原许可获取。[NVIDIA 官方权重](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-FP4-Local/tree/b9ce18a6887e18c089fdea8509a33e63429a3300) · [Strata 固定上游](https://github.com/Niko1221/Strata/tree/13eedf552417a6a791a7d13c6597e24300ee3a09)
