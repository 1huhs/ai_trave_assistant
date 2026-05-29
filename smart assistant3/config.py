"""
================================================================================
Smart Assistant v3 全局配置
================================================================================
AI Agent 框架配置：LLM 模型、内存、RAG、工具路径、日志。
"""
import os
from pathlib import Path
from dotenv import load_dotenv
import logging

load_dotenv(Path(__file__).parent / ".env")

# ────────────────── LLM 配置 ──────────────────
DEEP_SEEK_API_KEY = os.getenv("DEEP_SEEK_API_KEY", "")
DEEP_SEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEP_SEEK_MODEL = "deepseek-v4-flash"

ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY", "")
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4/"
ZHIPU_EMBEDDING_MODEL = "embedding-3"

# ────────────────── 路径配置 ──────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
knowledge_dir = os.path.join(BASE_DIR, "knowledge")
chroma_dir = os.path.join(BASE_DIR, "memory", "chroma_db")
sqlite_dir = os.path.join(BASE_DIR, "memory", "sqlite.db")

# ────────────────── RAG 切分配置 ──────────────────
Chunk_size = 300
Chunk_overlap = 50

# ────────────────── GUI 界面 ──────────────────
WINDOW_TITLE = "Smart Assistant v3"
WINDOW_WIDTH = 900
WINDOW_HEIGHT = 700

TOOL_COLORS = {
    "get_current_time": "#FFF3E0",
    "get_weather": "#E3F2FD",
    "get_exchange_rate": "#F3E5F5",
    "calculate": "#E8F5E9",
    "search_answer": "#E0F7FA",
    "analyze_code": "#F5F5F5",
    "optimize_code": "#F5F5F5",
    "generate_tests": "#F5F5F5",
    "travel_planner": "#E8EAF6",
}

# ────────────────── 第三方 API Key ──────────────────
GAODE_KEY = os.getenv("GAODE_KEY", "")

# ────────────────── 日志 ──────────────────
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S",
                    handlers=[
                        logging.StreamHandler(),
                        logging.FileHandler("agent.log", encoding="utf-8"),
                    ])


def get_logger(name, user_id="default"):
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, {"user_id": user_id})


import threading
_current_user = threading.local()


def set_current_user(user_id):
    _current_user.user_id = user_id


def get_current_user():
    return getattr(_current_user, "user_id", "unknown")
