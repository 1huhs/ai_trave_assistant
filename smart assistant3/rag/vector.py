"""知识库向量化 — Chroma 向量数据库，智谱 Embedding"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from . import load
import config
from langchain_openai import OpenAIEmbeddings
from pydantic import SecretStr
from langchain_chroma import Chroma


class KnowledgeVector:
    store = None

    @classmethod
    def get_store(cls):
        if cls.store is None:
            cls.store = cls.load()
        return cls.store

    @classmethod
    def load(cls):
        if not config.ZHIPU_API_KEY:
            raise ValueError("请设置 ZHIPU_API_KEY 环境变量")
        embeddings = OpenAIEmbeddings(
            model=config.ZHIPU_EMBEDDING_MODEL,
            api_key=SecretStr(config.ZHIPU_API_KEY),
            base_url=config.ZHIPU_BASE_URL,
        )
        if os.path.exists(config.chroma_dir) and os.listdir(config.chroma_dir):
            return Chroma(persist_directory=config.chroma_dir, embedding_function=embeddings)
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        documents = load.load_knowledge()
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=config.Chunk_size, chunk_overlap=config.Chunk_overlap)
        chunks = splitter.split_documents(documents)
        store = Chroma.from_documents(documents=chunks, embedding=embeddings, persist_directory=config.chroma_dir)
        print(f"[RAG] 向量库构建完成，共 {len(chunks)} 个片段")
        return store
