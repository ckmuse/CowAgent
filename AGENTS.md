## 项目概述
- **名称**: 多视频混剪与文案生成工作流
- **功能**: 支持上传首帧、尾帧及多个中间视频，根据文案提示词生成解说文案与字幕，自动完成视频混剪、字幕压制、TTS 配音与背景音乐叠加，最终输出合成视频 URL。

### 节点清单
| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| concat_video | `nodes/concat_video_node.py` | task | 将首帧+中间+尾帧视频拼接并转存对象存储 | - | - |
| copy_generation | `nodes/copy_generation_node.py` | agent | 根据提示词与时长生成解说文案 | - | `config/copy_generation_llm_cfg.json` |
| subtitle_tts | `nodes/subtitle_tts_node.py` | task | TTS 配音、语音识别(ASR)生成精确时间轴字幕并压制到视频（大字号） | - | - |
| final_compile | `nodes/final_compile_node.py` | task | 合成配音主音轨、叠加背景音乐同步并上传成品 | - | - |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支) / looparray(列表循环) / loopcond(条件循环)

## 技能使用
- 节点 `copy_generation` 使用大语言模型技能（豆包 doubao-seed-2-0-pro-260215）
- 节点 `subtitle_tts` 使用音频(TTS)与视频编辑技能
- 节点 `concat_video` / `subtitle_tts` / `final_compile` 使用对象存储技能转存中间产物，规避中间 URL 的 HEAD 校验限制

## 关键实现说明
- 所有链式视频编辑的中间产物（拼接/字幕/配音/旁白）均先转存到 S3 对象存储并生成长期签名 URL，再作为下一步视频编辑输入，确保 SDK 的 URL 可达性（HEAD）校验通过。