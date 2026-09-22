import logging
import os

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from coze_coding_dev_sdk import TTSClient
from coze_coding_dev_sdk.video_edit import (
    VideoEditClient,
    SubtitleConfig,
    FontPosConfig,
)
from coze_coding_dev_sdk.s3 import S3SyncStorage

from graphs.state import SubtitleTTSInput, SubtitleTTSOutput

logger = logging.getLogger(__name__)


def _upload_to_storage(ctx: Context, url: str) -> str:
    """将视频或音频转存到对象存储并返回长期可访问的签名URL"""
    storage = S3SyncStorage(
        endpoint_url=os.getenv("COZE_BUCKET_ENDPOINT_URL"),
        access_key="",
        secret_key="",
        bucket_name=os.getenv("COZE_BUCKET_NAME"),
        region="cn-beijing",
    )
    key = storage.upload_from_url(url=url, timeout=120)
    return storage.generate_presigned_url(key=key, expire_time=2592000)


def subtitle_tts_node(
    state: SubtitleTTSInput,
    config: RunnableConfig,
    runtime: Runtime[Context],
) -> SubtitleTTSOutput:
    """
    title: 字幕压制与配音
    desc: 先将解说文案通过语音合成生成配音音频，再用语音识别从配音音频中提取精确时间轴字幕并压制到拼接视频上，确保字幕与配音严格同步。
    integrations: 音频, 视频编辑, 对象存储
    """
    ctx = runtime.context

    # 1. 生成配音音频（TTS）
    tts_client = TTSClient(ctx=ctx)
    voiceover_url, _ = tts_client.synthesize(uid="video_mix_user", text=state.copy_text)

    # 2. 转存配音音频到对象存储（供语音识别与后续合成读取，规避 URL 校验限制）
    voiceover_stored_url = _upload_to_storage(ctx, voiceover_url)

    # 3. 语音识别配音音频，生成与语音严格对应的 SRT 字幕
    video_client = VideoEditClient(ctx=ctx)
    srt_resp = video_client.audio_to_subtitle(
        source=voiceover_stored_url,
        subtitle_type="srt",
    )
    srt_stored_url = _upload_to_storage(ctx, srt_resp.url)

    # 4. 将字幕压制到拼接视频（调大字体，增强可读性）
    subtitle_config = SubtitleConfig(
        font_pos_config=FontPosConfig(
            pos_x="0", pos_y="88%", width="100%", height="12%"
        ),
        font_size=56,
        font_color="#FFFFFFFF",
        font_type="1525745",
        background_color="#00000000",
        background_border_width=0,
        border_width=2,
        border_color="#00000099",
    )

    sub_resp = video_client.add_subtitles(
        video=state.concat_video_url,
        subtitle_config=subtitle_config,
        subtitle_url=srt_stored_url,
    )

    # 5. 转存压制字幕后的视频到对象存储，供最终合成步骤读取
    subs_stored_url = _upload_to_storage(ctx, sub_resp.url)

    logger.info("字幕压制完成，字幕时间轴由配音音频语音识别生成")
    return SubtitleTTSOutput(
        video_with_subtitles_url=subs_stored_url,
        voiceover_audio_url=voiceover_stored_url,
    )