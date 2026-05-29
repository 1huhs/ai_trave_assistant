from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import AsyncGenerator
import asyncio
from agent.langchain_agent import SmartAgent
import logging
import time
logger = logging.getLogger(__name__)


# 创建 FastAPI 应用
app = FastAPI(
    title="Smart Assistant API",
    description="智能生活助手 API 服务",
    version="1.0.0"
)

# 用户 Agent 缓存（简单实现，生产环境应该用 Redis）
agent_cache = {}


def get_or_create_agent(user_id: str) -> SmartAgent:
    """获取或创建用户的 Agent 实例"""
    if user_id not in agent_cache:
        agent_cache[user_id] = SmartAgent(user_id=user_id)
    return agent_cache[user_id]


# 请求模型
class ChatRequest(BaseModel):
    message: str = Field(..., description="用户输入的消息", min_length=1)
    user_id: str = Field(default="default", description="用户 ID")
    stream: bool = Field(default=False, description="是否使用流式输出")


# 响应模型
class ChatResponse(BaseModel):
    response: str
    user_id: str
    stream: bool = False


# 健康检查接口
@app.get("/")
async def root():
    return {
        "message": "Smart Assistant API 服务正在运行",
        "version": "1.0.0",
        "endpoints": {
            "/chat": "POST - 聊天接口",
            "/health": "GET - 健康检查"
        }
    }


@app.get("/health")
async def health_check():
    return {"status": "ok"}


# 聊天接口（非流式）
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    聊天接口 - 接收用户消息，返回 AI 回复

    - **message**: 用户输入的消息
    - **user_id**: 用户 ID（用于区分不同用户的记忆）
    - **stream**: 是否使用流式输出（默认 False）
    """
    try:
        # 获取或创建用户的 Agent
        agent = get_or_create_agent(request.user_id)

        result = agent.run(request.message)

        # 提取 AI 回复
        answer = result.get("answer") or result["messages"][-1].content

        return ChatResponse(
            response=answer,
            user_id=request.user_id,
            stream=False
        )
    except Exception as e:
        logger.error(f"API请求失败|user_id=%s|error=%s",request.user_id,e,exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理消息时出错: {str(e)}")


# 流式聊天接口
@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    流式聊天接口 - 实时返回 AI 生成的内容

    返回格式：Server-Sent Events (SSE)
    """
    try:
        agent = get_or_create_agent(request.user_id)

        # 创建异步生成器
        async def generate_stream() -> AsyncGenerator[str, None]:
            try:
                async for chunk in agent.astream(request.message):
                    yield f"data: {chunk}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                logger.error(f"流式API请求失败|user_id=%s|error=%s",request.user_id,e,exc_info=True)
                yield f"data: {agent.fallback_message}\n\n"
                yield "data: [DONE]\n\n"
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"流式处理时出错: {str(e)}")


# 获取用户信息接口
@app.get("/user/{user_id}")
async def get_user_info(user_id: str):
    """获取用户的记忆信息"""
    try:
        agent = get_or_create_agent(user_id)
        return {
            "user_id": user_id,
            "memory_data": agent.memory.memory_data,
            "conversation_count": len(agent.history_message)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取用户信息时出错: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
