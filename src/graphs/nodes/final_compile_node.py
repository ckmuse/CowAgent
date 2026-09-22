import logging
import os

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from coze_coding_dev_sdk.video_edit import VideoEditClient, OutputSync
from coze_coding_dev_sdk.s3 import S3SyncStorage

from graphs.state import FinalCompileInput, FinalCompileOutput
from utils.file.file import File

logger = logging.getLogger(__name__)


def _upload_to_storage(ctx: Context, url: str) -> str:
    """将视频转存到对象存储并返回长期可访问的签名URL"""
    storage = S3SyncStorage(
        endpoint_url=os.getenv("COZE_BUCKET_ENDPOINT_URL"),
        access_key="",
        secret_key="",
        bucket_name=os.getenv("COZE_BUCKET_NAME"),
        region="cn-beijing",
    )
    key = storage.upload_from_url(url=url, timeout=120)
    return storage.generate_presigned_url(key=key, expire_time=2592000)


def final_compile_node(
    state: FinalCompileInput,
    config: RunnableConfig,
    runtime: Runtime[Context],
) -> FinalCompileOutput:
    """
    title: 最终合成
    desc: 将配音合入已压制字幕的视频作为主音轨，再叠加背景音乐并做音视频同步衔接，最终上传对象存储返回成品视频URL。
    integrations: 视频编辑, 对象存储
    """
    ctx = runtime.context
    client = VideoEditClient(ctx=ctx)

    # 1. 将配音作为主音轨合成（丢弃原视频音频），并确保音视频同步
    narration_resp = client.compile_video_audio(
        video=state.video_with_subtitles_url,
        audio=state.voiceover_audio_url,
        is_video_audio_sync=True,
        output_sync=OutputSync(sync_method="speed", sync_mode="video"),
        is_audio_reserve=False,
    )
    # 转存到对象存储，供可能存在的背景音乐合成步骤读取
    narration_stored_url = _upload_to_storage(ctx, narration_resp.url)

    # 2. 若提供背景音乐，则叠加并确保音视频同步衔接（保留配音主音轨）
    final_video_url = narration_stored_url
    if state.background_music is not None and isinstance(
        state.background_music, File
    ) and state.background_music.url:
        bg_stored_url = _upload_to_storage(ctx, state.background_music.url)
        music_resp = client.compile_video_audio(
            video=narration_stored_url,
            audio=bg_stored_url,
            is_video_audio_sync=True,
            output_sync=OutputSync(sync_method="trim", sync_mode="video"),
            is_audio_reserve=True,
        )
        final_video_url = music_resp.url

    # 3. 转存最终成品到对象存储，返回长期可用URL
    stored_url = _upload_to_storage(ctx, final_video_url)
    logger.info("最终混剪视频已上传对象存储")
    return FinalCompileOutput(final_video_url=stored_url)