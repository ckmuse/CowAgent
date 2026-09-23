# 多视频混剪与文案生成工作流 —— 接收方部署说明

本工作流支持：上传首帧/尾帧/多个中间视频 + 文案提示词 + 背景音乐，自动完成「视频拼接 → 文案生成 → 字幕+配音 → 背景音乐合成」，输出一条带字幕、带旁白、带背景乐的混剪视频。

> ⚠️ 关键前提：本工作流运行在 **扣子 Coding 环境**。必须在你自己的扣子 Coding 工作区里导入并运行，这样大模型 / TTS / ASR / 视频编辑 / 对象存储的费用与凭证才会走**你自己账户的积分**，与原作者无关。

---

## 一、目录说明

```
项目根目录/
├── src/                          # 工作流源码
│   ├── main.py                   # 服务入口（HTTP）
│   ├── graphs/
│   │   ├── graph.py              # 主图编排（4 节点 DAG）
│   │   ├── state.py              # 状态/出入参定义
│   │   └── nodes/                # 各节点实现
│   ├── storage/                  # 对象存储(S3)/数据库封装
│   ├── utils/                    # 工具类
│   └── tools/
├── config/copy_generation_llm_cfg.json  # 文案生成大模型配置
├── scripts/                      # 构建/运行脚本
├── pyproject.toml + uv.lock      # 依赖声明与锁定
├── .coze                         # 项目配置（入口、脚本）
├── assets/mock/                  # （可选）测试素材
├── README_DEPLOY.md              # 本文档
└── AGENTS.md                     # 结构索引
```

---

## 二、环境要求

- Python >= 3.12
- uv（依赖管理工具）
- 必须是扣子 Coding 工作区环境（用于注入平台凭证与积分）

---

## 三、接收与解压

方式A：拿到的是**目录** → 直接放到你的工作目录即可。

方式B：拿到的是 **tar.gz 压缩包**：
```bash
tar xzf coze-video-mix.tar.gz
cd coze-video-mix
```

---

## 四、安装依赖

```bash
uv sync
```
（`pyproject.toml` 已配置阿里云镜像源，缺省即可直接安装；`uv.lock` 保证版本一致。）

如依赖缺失或版本异常，可强制重装：
```bash
uv sync --reinstall
```

---

## 五、环境变量（重要）

在**自己的扣子 Coding 工作区**运行时会自动注入以下变量，无需手动设置：

| 变量 | 作用 |
|------|------|
| `COZE_WORKSPACE_PATH` | 工作区根目录（默认当前目录） |
| `COZE_BUCKET_ENDPOINT_URL` | 对象存储 S3 端点 |
| `COZE_BUCKET_NAME` | 对象存储桶名 |
| `COZE_WORKLOAD_IDENTITY_TOKEN` | 工作负载身份令牌（S3 凭证） |

> 若需在**标准服务器**上脱离扣子 Coding 运行，请自行用环境变量或 `.env` 提供上述值，并确保大模型/语音/视频服务可用；否则将无法注入平台凭证。

---

## 六、启动服务

```bash
# 构建（首次可选）
bash scripts/setup.sh

# 启动 HTTP 服务（端口可改）
bash scripts/http_run.sh -p 5000
```

或在扣子 Coding 工作区直接点击 **运行/部署**。

---

## 七、工作流入参与结果

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `first_frame_video` | 视频 File | ✅ | 首帧视频 |
| `last_frame_video` | 视频 File | ✅ | 尾帧视频 |
| `middle_videos` | 视频 File[] | 可选 | 一个或多个中间视频 |
| `copy_prompt` | 文本 | ✅ | 文案提示词 |
| `background_music` | 音频 File | 可选 | 背景音乐 |

| 输出 | 说明 |
|------|------|
| `final_video_url` | 最终混剪视频 URL |
| `copy_text` | 自动生成的解说文案 |

---

## 八、积分 / 费用说明

- 文案生成（大模型）、TTS 配音、ASR 语音转字幕、视频编辑、对象存储统一按**扣子平台积分**结算。
- 只要在**你自己的工作区**运行，全部积分计入你的账户。
- 单条 30–60 秒成片的消耗主要集中在大模型 / 视频编辑环节，建议在控制台查看用量明细核对。

---

## 九、常见问题

| 现象 | 处理 |
|------|------|
| `URL is not reachable: HTTP 403` | 中间产物已内置转存对象存储逻辑，正常不会出现；如出现请确认 `COZE_BUCKET_*` 已注入。 |
| 字幕与配音对不上 | 本版已用 ASR 提取真实时间轴，字幕严格跟随配音；若仍偏移，可调整 `src/graphs/nodes/subtitle_tts_node.py` 中字幕偏移量/字号。 |
| `uv` 不存在 | 先安装 uv：`pip install uv` 或按官方文档安装。 |

---

如需二次开发（改模型、改文案风格、改字幕字号等），见 `AGENTS.md` 中的节点清单定位对应文件。