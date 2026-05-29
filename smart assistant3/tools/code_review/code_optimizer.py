"""代码优化建议 + diff 对比"""
import os, difflib, ast
from langchain_core.tools import tool


def _has_issues(tree):
    issues = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler) and node.type is None:
            issues.append((node.lineno, "使用了裸 except，建议精确捕获异常类型"))
    return issues


@tool
def optimize_code(filepath: str):
    """分析 Python 代码问题并生成优化建议和 diff 对比"""
    if not os.path.exists(filepath):
        return f"文件不存在: {filepath}"
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return f"语法错误: {e}"
    issues = _has_issues(tree) or [("—", "未检测到明显问题")]
    lines = []
    for l, m in issues:
        lines.append(f"  行{l}: {m}")
    return "代码优化报告 — " + os.path.basename(filepath) + "\n" + "\n".join(lines)
