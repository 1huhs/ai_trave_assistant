"""自动生成 pytest 单元测试"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import config
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from pydantic import SecretStr


@tool
def generate_tests(filepath: str):
    """为 Python 文件生成 pytest 单元测试，传入文件路径"""
    if not os.path.exists(filepath):
        return f"文件不存在: {filepath}"
    with open(filepath, "r", encoding="utf-8") as f:
        code = f.read()
    llm = ChatOpenAI(
        model=config.DEEP_SEEK_MODEL, api_key=SecretStr(config.DEEP_SEEK_API_KEY),
        base_url=config.DEEP_SEEK_BASE_URL, temperature=0.2,
        model_kwargs={"extra_body": {"thinking": {"type": "disabled"}}}
    )
    prompt = f"""你是一个 Python 测试工程师。为以下代码生成 pytest 单元测试。
要求：只输出测试代码，使用 pytest 风格，覆盖正常和边界情况。

源代码：
```python
{code}
```"""
    try:
        response = llm.invoke(prompt)
        test_code = response.content.strip()
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        output_path = os.path.join(os.path.dirname(filepath), f"test_{base_name}.py")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(test_code)
        return f"测试文件已生成: {output_path}\n运行: pytest {output_path} -v"
    except Exception as e:
        return f"测试生成失败: {e}"
