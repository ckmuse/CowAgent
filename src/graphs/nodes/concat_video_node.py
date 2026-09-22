import logging
import os
from typing import List

from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from coze_coding_dev_sdk.video_edit import VideoEditClient
from coze_coding_dev_sdk.s3 import S3SyncStorage

from graphs.state import ConcatVideoInput, ConcatVideoOutput
from utils.file.file import File

logger = logging.getLogger(__name__)


def _upload_to_storage(ctx: Context, url: str) -> str:
    """将视频转存到对象存储并返回长期可访问的签名URL（规避中间产物URL的HEAD校验问题）"""
    storage = S3SyncStorage(
        endpoint_url=os.getenv("COZE_BUCKET_ENDPOINT_URL"),
        access_key="",
        secret_key="",
        bucket_name=os.getenv("COZE_BUCKET_NAME"),
        region="cn-beijing",
    )
    key = storage.upload_from_url(url=url, timeout=120)
    return storage.generate_presigned_url(key=key, expire_time=2592000)


def concat_video_node(
    state: ConcatVideoInput,
    config: RunnableConfig,
    runtime: Runtime[Context],
) -> ConcatVideoOutput:
    """
    title: 视频拼接
    desc: 将首帧视频、多个中间视频与尾帧视频按顺序拼接为一段合成视频，并返回合成视频URL及总时长。
    integrations: 视频编辑, 对象存储
    """
    ctx = runtime.context

    # 组装拼接顺序：[首帧, 中间视频..., 尾帧]
    video_urls: List[str] = [state.first_frame_video.url]
    if isinstance(state.middle_videos, list):
        for mv in state.middle_videos:
            if isinstance(mv, File) and mv.url:
                video_urls.append(mv.url)
    video_urls.append(state.last_frame_video.url)

    if len(video_urls) < 1:
        raise Exception("拼接视频素材为空，无法进行混剪。")

    client = VideoEditClient(ctx=ctx)
    response = client.concat_videos(videos=video_urls, transitions=[])

    concat_url = response.url
    duration = getattr(response.video_meta, "duration", 0.0)

    # 转存到对象存储，确保后续视频编辑操作可正常读取
    stored_url = _upload_to_storage(ctx, concat_url)
    logger.info("视频拼接完成，时长 %.2f 秒", float(duration or 0))

    return ConcatVideoOutput(
        concat_video_url=stored_url,
        concat_duration=float(duration or 0),
    )