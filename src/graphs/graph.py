from langgraph.graph import StateGraph, END

from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
)

from graphs.nodes.concat_video_node import concat_video_node
from graphs.nodes.copy_generation_node import copy_generation_node
from graphs.nodes.subtitle_tts_node import subtitle_tts_node
from graphs.nodes.final_compile_node import final_compile_node

# 主图：有向无环图（DAG）
# concat_video -> copy_generation -> subtitle_tts -> final_compile -> END
builder = StateGraph(
    GlobalState,
    input_schema=GraphInput,
    output_schema=GraphOutput,
)

builder.add_node("concat_video", concat_video_node)

# 文案生成节点为大语言模型节点，通过 metadata 注入模型配置文件
builder.add_node(
    "copy_generation",
    copy_generation_node,
    metadata={"type": "agent", "llm_cfg": "config/copy_generation_llm_cfg.json"},
)

builder.add_node("subtitle_tts", subtitle_tts_node)
builder.add_node("final_compile", final_compile_node)

builder.set_entry_point("concat_video")

builder.add_edge("concat_video", "copy_generation")
builder.add_edge("copy_generation", "subtitle_tts")
builder.add_edge("subtitle_tts", "final_compile")
builder.add_edge("final_compile", END)

main_graph = builder.compile()