from langchain_core.tools import tool
import datetime
@tool
def get_current_time():
    """获取当前时间"""
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
