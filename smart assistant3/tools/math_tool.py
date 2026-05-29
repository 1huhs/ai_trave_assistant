import ast
import operator
from langchain_core.tools import tool
import logging
logger = logging.getLogger(__name__)

_SAFE_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub,
    ast.Mult: operator.mul, ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
    ast.Pow: operator.pow, ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class _MathEvaluator(ast.NodeVisitor):
    def visit_Constant(self, node): return node.value
    def visit_Num(self, node): return node.n
    def visit_UnaryOp(self, node): return _SAFE_OPS[type(node.op)](self.visit(node.operand))
    def visit_BinOp(self, node): return _SAFE_OPS[type(node.op)](self.visit(node.left), self.visit(node.right))
    def visit_Expression(self, node): return self.visit(node.body)
    def generic_visit(self, node): raise ValueError(f"不支持的语法: {type(node).__name__}")


def _safe_eval(expression):
    tree = ast.parse(expression.strip(), mode='eval')
    return _MathEvaluator().visit(tree)


@tool
def calculate(expression: str):
    """计算数学表达式，支持 + - * / // % ** 和括号，使用 AST 安全求值"""
    try:
        result = _safe_eval(expression)
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return str(result)
    except (SyntaxError, ValueError) as e:
        return f"请输入正确的数学表达式。错误：{e}"
    except ZeroDivisionError:
        return "数学错误：不能除以零"
    except Exception as e:
        return f"计算出错：{e}"
