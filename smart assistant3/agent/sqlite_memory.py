"""
双层记忆系统 — SQLite 结构化存储 + Chroma 向量检索 + 工具上下文总线
=====================================================================
v3 新增：Tool Context Bus —— 请求级工具间数据共享机制。
  同一请求中，前一个工具的执行结果自动暴露给后续工具，
  Agent 不再需要在 prompt 中手动传递上下文。
"""
import sqlite3
import os
import logging
from config import sqlite_dir

logger = logging.getLogger(__name__)


class UserMemory:
    """用户记忆管理器"""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self._tool_context = {}   # [NEW] 请求级工具上下文缓存
        try:
            self.conn = sqlite3.connect(sqlite_dir)
            self.conn.execute("PRAGMA journal_mode=WAL")
            self.cursor = self.conn.cursor()
            self._init_tables()
            self.memory_data = {}
            self.load_memory()
        except Exception as e:
            logger.error("数据库连接失败|user_id=%s|error=%s", user_id, e)

    # ──────────── Tool Context Bus [NEW] ────────────

    def set_tool_result(self, tool_name: str, result: str):
        """写入工具上下文（工具执行完成后调用）"""
        self._tool_context[tool_name] = result[:500]  # 截断避免过长

    def get_tool_context(self) -> str:
        """读取当前请求中所有已执行工具的结果（格式化为文本）"""
        if not self._tool_context:
            return ""
        lines = []
        for name, result in self._tool_context.items():
            lines.append(f"[{name} 执行结果]: {result[:200]}")
        return "\n".join(lines)

    def clear_tool_context(self):
        """清空工具上下文（每次新请求开始时调用）"""
        self._tool_context = {}

    # ──────────── 建表 ────────────

    def _init_tables(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS memory (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                category TEXT,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, category, content)
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        self.cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conv_user_time
            ON conversation_history(user_id, created_at DESC)
        ''')
        self.conn.commit()

    # ──────────── 画像记忆 ────────────

    def load_memory(self):
        try:
            search = self.cursor.execute(
                "SELECT category,content FROM memory WHERE user_id=?", (self.user_id,))
            for category, content in search.fetchall():
                if category not in self.memory_data:
                    self.memory_data[category] = []
                self.memory_data[category].append(content)
        except Exception as e:
            logger.warning("加载记忆失败|user_id=%s|error=%s", self.user_id, e)

    def save_memory(self, memory_data):
        for key, value in memory_data.items():
            if not isinstance(value, list):
                value = [value]
            try:
                for j in value:
                    self.cursor.execute(
                        "INSERT OR IGNORE INTO memory (user_id,category,content) VALUES(?,?,?)",
                        (self.user_id, key, j))
                self.conn.commit()
                self.load_memory()
            except Exception as e:
                logger.warning("保存记忆失败|user_id=%s|error=%s", self.user_id, e)
        self.sync_user_memory_to_chroma()

    def clear(self):
        try:
            self.cursor.execute("DELETE FROM memory WHERE user_id=?", (self.user_id,))
            self.conn.commit()
            self.memory_data = {}
        except Exception as e:
            logger.warning("清空记忆失败|user_id=%s|error=%s", self.user_id, e)

    # ──────────── 对话历史 ────────────

    def save_conversation(self, role, content):
        try:
            self.cursor.execute(
                "INSERT INTO conversation_history (user_id, role, content) VALUES (?,?,?)",
                (self.user_id, role, content))
            self.conn.commit()
            self.sync_conversation_to_chroma(role, content)
        except Exception as e:
            logger.warning("保存对话失败|user_id=%s|error=%s", self.user_id, e)

    def load_conversations(self, limit=20):
        try:
            rows = self.cursor.execute(
                "SELECT role, content FROM conversation_history "
                "WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (self.user_id, limit)).fetchall()
            return [(r, c) for r, c in reversed(rows)]
        except Exception as e:
            logger.warning("加载对话失败|user_id=%s|error=%s", self.user_id, e)
            return []

    def clear_conversations(self):
        try:
            self.cursor.execute("DELETE FROM conversation_history WHERE user_id=?", (self.user_id,))
            self.conn.commit()
        except Exception as e:
            logger.warning("清空对话失败|user_id=%s|error=%s", self.user_id, e)

    # ──────────── Chroma 向量同步 ────────────

    def _get_chroma_store(self, collection_name):
        from langchain_openai import OpenAIEmbeddings
        from pydantic import SecretStr
        from langchain_chroma import Chroma
        import config
        embeddings = OpenAIEmbeddings(
            model=config.ZHIPU_EMBEDDING_MODEL,
            api_key=SecretStr(config.ZHIPU_API_KEY),
            base_url=config.ZHIPU_BASE_URL,
        )
        return Chroma(persist_directory=config.chroma_dir, embedding_function=embeddings,
                       collection_name=collection_name)

    def sync_user_memory_to_chroma(self):
        texts = self.get_memory_texts()
        if not texts:
            return
        try:
            store = self._get_chroma_store("user_memory")
            for i in range(0, len(texts), 16):
                batch = texts[i:i + 16]
                store.add_texts(texts=batch, metadatas=[{"user_id": self.user_id}] * len(batch))
            logger.info("用户画像已同步到 Chroma|user_id=%s|条数=%s", self.user_id, len(texts))
        except Exception as e:
            logger.warning("同步 Chroma 失败|user_id=%s|error=%s", self.user_id, e)

    def search_relevant_memory(self, query, k=3):
        texts = self.get_memory_texts()
        if not texts:
            return "（暂无历史记忆）"
        try:
            store = self._get_chroma_store("user_memory")
            results = store.similarity_search(query, k=k)
            if not results:
                return "（暂无相关记忆）"
            return "\n".join(f"  • {r.page_content}" for r in results)
        except Exception as e:
            logger.warning("检索记忆失败|user_id=%s|error=%s", self.user_id, e)
            return "（记忆检索出错）"

    def sync_conversation_to_chroma(self, role, content):
        try:
            store = self._get_chroma_store("conversation_memory")
            store.add_texts(texts=[content], metadatas=[{"user_id": self.user_id, "role": role}])
        except Exception as e:
            logger.warning("同步对话 Chroma 失败|user_id=%s|error=%s", self.user_id, e)

    def search_relevant_conversations(self, query, k=3):
        try:
            store = self._get_chroma_store("conversation_memory")
            results = store.similarity_search(query, k=k)
            return [r.page_content for r in results]
        except Exception as e:
            logger.warning("检索对话失败|user_id=%s|error=%s", self.user_id, e)
            return []

    def get_memory_texts(self):
        texts = []
        for category, items in self.memory_data.items():
            for item in items:
                texts.append(f"[{category}] {item}")
        return texts

    def close(self):
        try:
            if self.conn:
                self.conn.close()
        except Exception as e:
            logger.warning("关闭数据库失败|user_id=%s|error=%s", self.user_id, e)
