from typing import Literal, Optional, List
from pydantic import BaseModel, Field
from utils.file.file import File


class GlobalState(BaseModel):
    """多视频混剪与文案生成工作流的全局状态"""
    first_frame_video: File = Field(..., description="首帧视频素材")
    last_frame_video: File = Field(..., description="尾帧视频素材")
    middle_videos: List[File] = Field(default=[], description="多个中间视频素材列表")
    copy_prompt: str = Field(..., description="文案生成提示词")
    background_music: Optional[File] = Field(default=None, description="背景音乐文件（可选）")
    concat_video_url: str = Field(default="", description="拼接后的合成视频URL")
    concat_duration: float = Field(default=0.0, description="合成视频总时长（秒）")
    copy_text: str = Field(default="", description="生成的解说文案内容")
    video_with_subtitles_url: str = Field(default="", description="已压制字幕的视频URL")
    voiceover_audio_url: str = Field(default="", description="文案生成的配音音频URL")
    final_video_url: str = Field(default="", description="最终混剪成品视频URL")


class GraphInput(BaseModel):
    """工作流输入"""
    first_frame_video: File = Field(..., description="首帧视频素材")
    last_frame_video: File = Field(..., description="尾帧视频素材")
    middle_videos: List[File] = Field(default=[], description="多个中间视频素材列表")
    copy_prompt: str = Field(..., description="文案生成提示词")
    background_music: Optional[File] = Field(default=None, description="背景音乐文件（可选）")


class GraphOutput(BaseModel):
    """工作流输出"""
    final_video_url: str = Field(..., description="最终混剪成品视频URL")
    copy_text: str = Field(..., description="生成的解说文案内容")


# ---------- 节点1：视频拼接 ----------
class ConcatVideoInput(BaseModel):
    """视频拼接节点输入"""
    first_frame_video: File = Field(..., description="首帧视频素材")
    last_frame_video: File = Field(..., description="尾帧视频素材")
    middle_videos: List[File] = Field(default=[], description="多个中间视频素材列表")


class ConcatVideoOutput(BaseModel):
    """视频拼接节点输出"""
    concat_video_url: str = Field(..., description="拼接后的合成视频URL")
    concat_duration: float = Field(..., description="合成视频总时长（秒）")


# ---------- 节点2：文案生成 ----------
class CopyGenerationInput(BaseModel):
    """文案生成节点输入"""
    copy_prompt: str = Field(..., description="文案生成提示词")
    concat_duration: float = Field(..., description="合成视频总时长（秒）")


class CopyGenerationOutput(BaseModel):
    """文案生成节点输出"""
    copy_text: str = Field(..., description="生成的解说文案内容")


# ---------- 节点3：字幕压制与TTS配音 ----------
class SubtitleTTSInput(BaseModel):
    """字幕压制与配音节点输入"""
    concat_video_url: str = Field(..., description="拼接后的合成视频URL")
    concat_duration: float = Field(..., description="合成视频总时长（秒）")
    copy_text: str = Field(..., description="生成的解说文案内容")


class SubtitleTTSOutput(BaseModel):
    """字幕压制与配音节点输出"""
    video_with_subtitles_url: str = Field(..., description="已压制字幕的视频URL")
    voiceover_audio_url: str = Field(..., description="文案生成的配音音频URL")


# ---------- 节点4：最终合成 ----------
class FinalCompileInput(BaseModel):
    """最终合成节点输入"""
    video_with_subtitles_url: str = Field(..., description="已压制字幕的视频URL")
    voiceover_audio_url: str = Field(..., description="文案生成的配音音频URL")
    background_music: Optional[File] = Field(default=None, description="背景音乐文件（可选）")


class FinalCompileOutput(BaseModel):
    """最终合成节点输出"""
    final_video_url: str = Field(..., description="最终混剪成品视频URL")