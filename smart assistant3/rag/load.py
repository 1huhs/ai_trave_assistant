"""知识库文档加载器 — 扫描 knowledge/*.txt 返回 Document 列表"""
import os, sys, glob
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import knowledge_dir
from langchain_community.document_loaders import TextLoader


def load_knowledge():
    txt_files = glob.glob(os.path.join(knowledge_dir, "*.txt"))
    docs = []
    for path in txt_files:
        loader = TextLoader(path, encoding="utf-8")
        docs.extend(loader.load())
    return docs
