# 从干净环境部署

## 机器和依赖

参考平台为单路 i9-10940X（14 核/28 线程）、96 GB RAM、单张 RTX 5060 Ti **16 GB**、Ubuntu 26.04 x86_64、cgroup v2、systemd user manager、NVIDIA 驱动 595.99.02。生产驱动支持 CUDA Driver API 13.2，构建用 CUDA Toolkit 13.0.2，目标架构 SM120。请预先装好兼容驱动和 Toolkit，脚本不会替换驱动。CPU 配置器需要 14 对可用 SMT 核心，自动保留四个物理核心给系统。其他 GPU、低内存或不同 CPU 拓扑需要另行适配。

建议为首次部署预留 **至少 230 GiB 空闲 SSD 空间，另留宿主机日常空间**。参考 checkpoint 约 95.24 GiB，转换后目录约 99 GiB；还需存放构建目录、Python 依赖和中间文件。转换的实测进程 RSS 峰值约 7.27 GiB。生产服务整个 cgroup 上限 85 GiB，SwapMax=0；先确定宿主机及其他工作负载能保留足够物理内存。单卡同时只加载一个完整模型。

以下命令以有 systemd 用户会话的普通用户执行。系统包和 Toolkit 的安装需要机器管理员权限。Ubuntu 软件包示例：

```bash
sudo apt install git build-essential g++-15 cmake ninja-build python3.14-venv curl
nvidia-smi -L
export CUDA_HOME=/usr/local/cuda-13.0
"$CUDA_HOME/bin/nvcc" --version
systemctl --user status
stat -fc %T /sys/fs/cgroup   # cgroup2fs
df -h "$HOME"
```

若 Toolkit 在其他位置，改 CUDA_HOME。使用 CMake 4.2、Ninja、GCC/G++ 15 和 Python 3.14 的组合完成发布检查。在受信任的本地持久目录部署，安装后保留该路径；systemd、venv 和 CUDA 动态库使用绝对路径。以下均从仓库根目录执行：

```bash
git clone https://github.com/Goldlionren/JR-T5820-Qwen3.8-Flash-Next-NVFP4-QAD.git strata-fp4-local
cd strata-fp4-local
git checkout t5820-fp4local-long-prefill-20261124
./scripts/source.sh
./scripts/python-env.sh
BUILD_JOBS=2 ./scripts/build.sh
ldd bin/strata        # 每个动态库都应解析成功
ldd bin/strata-vision
```

source.sh 取回两个精确 Git 提交，应用 Engine/Server 补丁并检查运行所需源码摘要。build.sh 在本机生成 CUDA Engine 和 CPU 视觉编码器。上游提供专家 profile、控制向量和 MTP 词表。仅本地生成的二进制及其 SHA256 写入 bin/。

## 模型与转换

```bash
.venv/bin/python scripts/models.py
systemd-run --user --wait --pipe --collect -p MemoryMax=32G -p MemorySwapMax=0 \
  -p CPUQuota=800% "$PWD/scripts/prepare.sh"
```

models.py 使用 Hugging Face 的本地目录下载和断点续传，核对 33 个源文件的大小及 Git blob 或 SHA256，再核对视觉 projector 的 SHA256。中断后在同一目录重新运行。prepare.sh 从同一个 NVIDIA checkpoint 建立 Dense GGUF、Embedding、Tokenizer、NVFP4 原生专家、压缩 PLE 和 Q2_0 MTP，补齐 CJK 草稿词表。上游的完成标记可跳过已完成阶段；最终校验以 manifests/pack.sha256 为准。保留 checkpoint、prepared 和缓存文件供复核。校验失败时先定位失败文件；不要手动写完成标记。只需复核现有产物时运行 `python3 scripts/assets.py record`。

[固定 NVIDIA checkpoint](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-FP4-Local/tree/b9ce18a6887e18c089fdea8509a33e63429a3300) · [固定视觉 projector](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/resolve/ed59f92082b1e93c0e96d60a8b11aab089b52f09/mmproj-Qwen3.8-Flash-Next-BF16.gguf) · [上游转换说明](https://github.com/Niko1221/Strata/blob/13eedf552417a6a791a7d13c6597e24300ee3a09/docs/NVFP4.md)

## 生成配置并启动

```bash
python3 scripts/configure.py
mkdir -p "$HOME/.config/systemd/user"
ln -s "$PWD/strata-fp4-local.service" "$HOME/.config/systemd/user/strata-fp4-local.service"
systemd-analyze --user verify "$PWD/strata-fp4-local.service"
systemctl --user daemon-reload
systemctl --user enable --now strata-fp4-local.service
python3 scripts/native.py status
python3 scripts/native.py models
python3 scripts/native.py smoke
```

局域网使用时，在首次生成配置的那一步改用 `python3 scripts/configure.py --host 本机已分配的IPv4地址`。多 GPU 主机可用 `--gpu` 显式指定本机 RTX 5060 Ti 的 UUID。默认首次创建权限 0600 的 secrets/api.key；如需迁移原客户端密钥，在 configure 前将已有 key 安装到此路径（目录 0700，文件 0600）。该文件只存放于本机。注册单元的 ln 如提示已存在，先识别原服务，按维护文档备份，避免覆盖其他安装。请求使用 Bearer 认证；通过不可信网络时请用 SSH 隧道或 TLS。

在允许无人登录开机运行的主机上，以管理员账户执行一次 `sudo loginctl enable-linger "$USER"`（若当前是管理员代操，请指定运行服务的普通用户）。用 `loginctl show-user "$USER" -p Linger` 和 `systemctl --user is-enabled strata-fp4-local.service` 检查。systemd 的 active 表示 API 进程启动，**/health 的 loaded=true** 表示模型已完成预加载。显存或 RAM 不足时查看 `journalctl --user -u strata-fp4-local.service -b -n 100` 和 runtime/engine.log；资源恢复后可用 `python3 scripts/native.py preload` 重试加载。不要启动第二份 Engine。

也可在自己的 GitHub 仓库 Actions 中手动触发 “Build the SM120 engine and CPU vision encoder”，在独立 CUDA 容器从零编译两项。该工作流只检查编译和产物摘要，无 GPU 推理或权重下载。生产机繁忙时可以在另一台兼容的 x86_64 Linux 主机构建；搬运 bin/ 时保留 SHA256SUMS，在目标机使用兼容的 glibc、libstdc++ 和 CUDA 13 运行库，再用 ldd 与 sha256sum -c 检查。
