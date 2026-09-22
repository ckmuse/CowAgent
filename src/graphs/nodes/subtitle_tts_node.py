import logging
import os
import re
from typing import List

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from coze_coding_dev_sdk import TTSClient
from coze_coding_dev_sdk.video_edit import (
    VideoEditClient,
    SubtitleConfig,
    FontPosConfig,
    TextItem,
)
from coze_coding_dev_sdk.s3 import S3SyncStorage

from graphs.state import SubtitleTTSInput, SubtitleTTSOutput

logger = logging.getLogger(__name__)

_SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?.；;])")


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


def _split_copy(copy_text: str) -> List[str]:
    """将文案按标点拆分为短句片段"""
    text = copy_text.strip()
    if not text:
        return []
    pieces: List[str] = [p.strip() for p in _SENTENCE_SPLIT.split(text) if p and p.strip()]
    if pieces:
        return pieces
    # 没有标点时按固定长度切分
    return [text[i : i + 20] for i in range(0, len(text), 20)]


def _build_timed_segments(copy_text: str, duration: float) -> List[dict]:
    sentences = _split_copy(copy_text)
    if not sentences:
        return []
    duration = float(duration or 0)
    if duration <= 0:
        duration = max(len(sentences) * 4.0, 12.0)

    n = len(sentences)
    seg_dur = duration / n
    segments: List[dict] = []
    for i, sent in enumerate(sentences):
        start = round(i * seg_dur, 2)
        end = round((i + 1) * seg_dur, 2)
        segments.append({"start": start, "end": end, "text": sent})
    return segments


def subtitle_tts_node(
    state: SubtitleTTSInput,
    config: RunnableConfig,
    runtime: Runtime[Context],
) -> SubtitleTTSOutput:
    """
    title: 字幕压制与配音
    desc: 将生成的解说文案拆分为带时间轴的字幕并压制到拼接视频上，同时通过语音合成生成对应配音音频。
    integrations: 音频, 视频编辑, 对象存储
    """
    ctx = runtime.context

    segments = _build_timed_segments(state.copy_text, state.concat_duration)

    # 1. 生成配音音频（TTS）
    tts_client = TTSClient(ctx=ctx)
    voiceover_url, _ = tts_client.synthesize(uid="video_mix_user", text=state.copy_text)

    # 2. 组装字幕时间轴并压制到视频
    text_list = [
        TextItem(start_time=seg["start"], end_time=seg["end"], text=seg["text"])
        for seg in segments
    ]

    subtitle_config = SubtitleConfig(
        font_pos_config=FontPosConfig(
            pos_x="0", pos_y="90%", width="100%", height="10%"
        ),
        font_size=40,
        font_color="#FFFFFFFF",
        font_type="1525745",
        background_color="#00000000",
        background_border_width=0,
        border_width=1,
        border_color="#00000066",
    )

    video_client = VideoEditClient(ctx=ctx)
    sub_resp = video_client.add_subtitles(
        video=state.concat_video_url,
        subtitle_config=subtitle_config,
        text_list=text_list,
    )

    # 3. 转存配音与压制字幕后的视频到对象存储，供后续合成步骤读取
    subs_stored_url = _upload_to_storage(ctx, sub_resp.url)
    voiceover_stored_url = _upload_to_storage(ctx, voiceover_url)

    logger.info("字幕压制完成，共 %d 条字幕", len(segments))
    return SubtitleTTSOutput(
        video_with_subtitles_url=subs_stored_url,
        voiceover_audio_url=voiceover_stored_url,
        subtitle_segments=segments,
    )