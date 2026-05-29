"""代码结构分析与复杂度计算"""
import ast
import os
from langchain_core.tools import tool


def _extract_structure(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
        tree = ast.parse(code)
    functions, classes = [], []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            functions.append({"name": node.name, "line": node.lineno, "args": [a.arg for a in node.args.args]})
        elif isinstance(node, ast.ClassDef):
            methods = [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
            classes.append({"name": node.name, "line": node.lineno, "methods": methods})
    return {"functions": functions, "classes": classes, "total_lines": len(code.splitlines())}


def _calc_complexity(filepath):
    try:
        from radon.complexity import ComplexityVisitor
    except ImportError:
        return "需要安装 radon：pip install radon"
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
    visitor = ComplexityVisitor.from_code(code)
    results = []
    for item in visitor.functions:
        level = "简单" if item.complexity <= 5 else "中等" if item.complexity <= 10 else "复杂"
        results.append(f"  {item.name}(行{item.lineno}): 复杂度 {item.complexity} - {level}")
    return "\n".join(results) if results else "未检测到函数"


@tool
def analyze_code(filepath: str):
    """分析 Python 文件的代码结构和圈复杂度，传入文件路径"""
    if not os.path.exists(filepath):
        return f"文件不存在: {filepath}"
    try:
        structure = _extract_structure(filepath)
        complexity = _calc_complexity(filepath)
        report = f"代码分析报告 — {os.path.basename(filepath)}\n"
        report += f"━━━━━━━━━━━━━━━━━━━━\n"
        report += f"文件: {structure['total_lines']} 行 | 函数: {len(structure['functions'])} | 类: {len(structure['classes'])}\n\n"
        report += f"函数列表:\n"
        for f in structure["functions"]:
            report += f"  {f['name']}(行{f['line']}) 参数: {', '.join(f['args'])}\n"
        report += f"\n复杂度:\n{complexity}"
        return report
    except SyntaxError as e:
        return f"Python 语法错误: {e}"
    except Exception as e:
        return f"分析失败: {e}"
