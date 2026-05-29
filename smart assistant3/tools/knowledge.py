"""知识库检索工具 — 混合检索 + 查询增强 + LLM 加工"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
from langchain_core.tools import tool
import logging
logger = logging.getLogger(__name__)

_llm_cache = None


def _get_llm():
    global _llm_cache
    if _llm_cache is None:
        from langchain_openai import ChatOpenAI
        from pydantic import SecretStr
        _llm_cache = ChatOpenAI(
            model=config.DEEP_SEEK_MODEL,
            api_key=SecretStr(config.DEEP_SEEK_API_KEY),
            base_url=config.DEEP_SEEK_BASE_URL,
        )
    return _llm_cache


@tool
def search_answer(query_txt: str):
    """通过查找 knowledge 里的内容，给出对用户问题的精准答案。用于需要背景知识时被 Agent 调用"""
    try:
        from rag.query_enhancer import expand_query
        from rag.hybrid_retriever import get_hybrid_retriever
        expanded = expand_query(query_txt)
        retriever = get_hybrid_retriever()
        all_docs, seen = [], set()
        for q in expanded:
            docs = retriever.search(q, k=3)
            for doc in docs:
                key = doc.page_content[:100]
                if key not in seen:
                    seen.add(key)
                    all_docs.append(doc)
        if not all_docs:
            return "知识库中未找到相关内容。"
        context = "\n----\n".join(d.page_content for d in all_docs[:5])
        llm = _get_llm()
        return llm.invoke(f"参考资料：{context}\n问题：{query_txt}\n请基于参考资料回答，如果不相关则自行回答。").content
    except Exception as e:
        logger.error("knowledge查询失败|error=%s", e)
        return f"知识库查询失败: {e}"
