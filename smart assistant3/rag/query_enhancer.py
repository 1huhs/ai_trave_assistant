"""查询增强 — LLM 驱动的意图扩展，提升 RAG 召回命中率"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
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
            temperature=0,
        )
    return _llm_cache


def expand_query(user_query: str) -> list:
    """将用户问题扩展为多个检索角度，提升 RAG 召回覆盖"""
    try:
        llm = _get_llm()
        prompt = f"""将以下问题扩展为 3-5 个不同角度的检索查询，用分号分隔，不要编号，不要解释。
用户问题：{user_query}
扩展查询："""
        response = llm.invoke(prompt)
        queries = [q.strip() for q in response.content.split(";") if q.strip()]
        seen = {user_query}
        results = [user_query]
        for q in queries:
            if q not in seen:
                seen.add(q)
                results.append(q)
        return results[:6]
    except Exception as e:
        logger.warning("查询扩展失败|error=%s", e)
        return [user_query]
