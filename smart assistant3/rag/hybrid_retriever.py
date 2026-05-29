"""混合检索引擎 — Chroma 向量 + BM25 关键词双路召回"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config
import logging
logger = logging.getLogger(__name__)


class HybridRetriever:
    def __init__(self):
        self._vector_retriever = None
        self._bm25_retriever = None
        self._documents = None

    def _ensure_initialized(self):
        if self._vector_retriever is not None:
            return
        from langchain_openai import OpenAIEmbeddings
        from pydantic import SecretStr
        from langchain_chroma import Chroma
        from rag.load import load_knowledge
        self._documents = load_knowledge()

        embeddings = OpenAIEmbeddings(
            model=config.ZHIPU_EMBEDDING_MODEL,
            api_key=SecretStr(config.ZHIPU_API_KEY),
            base_url=config.ZHIPU_BASE_URL,
        )
        vector_store = Chroma(persist_directory=config.chroma_dir, embedding_function=embeddings)
        self._vector_retriever = vector_store.as_retriever(search_kwargs={"k": 5})
        try:
            from langchain_community.retrievers import BM25Retriever
            self._bm25_retriever = BM25Retriever.from_documents(self._documents, k=5)
        except ImportError:
            self._bm25_retriever = None

    def search(self, query, k=5):
        self._ensure_initialized()
        results, seen = [], set()
        vector_docs = self._vector_retriever.invoke(query)
        for doc in vector_docs:
            key = doc.page_content[:100]
            if key not in seen:
                seen.add(key)
                results.append(doc)
        if self._bm25_retriever:
            bm25_docs = self._bm25_retriever.invoke(query)
            for doc in bm25_docs:
                key = doc.page_content[:100]
                if key not in seen:
                    seen.add(key)
                    results.append(doc)
        return results[:k]


_hybrid_retriever = None


def get_hybrid_retriever():
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = HybridRetriever()
    return _hybrid_retriever
