import json
import os
from typing import Any

from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import SystemMessage, HumanMessage

from graphs.state import CopyGenerationInput, CopyGenerationOutput


def _load_llm_cfg(runtime: Runtime[Context], config: RunnableConfig) -> dict:
    cfg_path = os.path.join(
        os.getenv("COZE_WORKSPACE_PATH", ""), config["metadata"]["llm_cfg"]
    )
    with open(cfg_path, "r", encoding="utf-8") as fd:
        return json.load(fd)


def copy_generation_node(
    state: CopyGenerationInput,
    config: RunnableConfig,
    runtime: Runtime[Context],
) -> CopyGenerationOutput:
    """
    title: 文案生成
    desc: 根据用户提供的文案提示词与合成视频总时长，生成有节奏、适合配音与字幕展示的解说文案。
    integrations: 大语言模型
    """
    ctx = runtime.context
    cfg = _load_llm_cfg(runtime, config)
    llm_cfg = cfg.get("config", {})
    sp = cfg.get("sp", "")
    up = cfg.get("up", "")

    up_tpl = Template(up)
    user_prompt = up_tpl.render(
        {"copy_prompt": state.copy_prompt, "duration": state.concat_duration}
    )

    client = LLMClient(ctx=ctx)
    messages = [
        SystemMessage(content=sp),
        HumanMessage(content=user_prompt),
    ]

    response = client.invoke(
        messages=messages,
        model=llm_cfg.get("model", "doubao-seed-2-0-pro-260215"),
        temperature=llm_cfg.get("temperature", 0.8),
        thinking=llm_cfg.get("thinking", "disabled"),
        max_completion_tokens=llm_cfg.get("max_completion_tokens", 2000),
    )

    copy_text = _extract_text(response.content)
    return CopyGenerationOutput(copy_text=copy_text)


def _extract_text(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(item.get("text", ""))
        return "".join(parts).strip()
    return str(content or "").strip()