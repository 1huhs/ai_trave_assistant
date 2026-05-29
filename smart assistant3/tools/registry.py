"""
================================================================================
工具自动发现与注册（Tool Registry）
================================================================================
自动扫描 tools/ 目录下所有 @tool 装饰的函数，构建工具列表供 Agent 使用。
新增工具只需在 tools/ 或 tools/子目录/ 下创建 .py 文件并加 @tool 装饰器，
无需修改任何核心代码，实现插件化设计。

调用链：
  langchain_agent.py:SmartAgent.__init__() → auto_discover_tools()
  api.py:SmartAgent.__init__() → auto_discover_tools()
"""

import os
import importlib
from typing import List


def auto_discover_tools() -> List:
    """
    递归扫描 tools/ 目录，发现所有 LangChain @tool 函数
    :return: list[langchain_core.tools.BaseTool] — 所有发现的工具实例列表
             每个元素都有 name、description、invoke 属性
    :调用方: langchain_agent.py:SmartAgent.__init__() 中 self.tools = auto_discover_tools()
    :识别规则:
        - 跳过 patterns/子目录
        - 只检查 .py 文件
        - 跳过以 _ 开头的模块和属性
        - 只收集有 invoke/name/description 属性且非类实例的对象
    """
    tools_dir = os.path.dirname(__file__)
    discovered_tools = []  # list[Tool] — 收集到的工具列表

    print("🔍 开始扫描工具...")

    # 遍历 tools 目录及其所有子目录
    for root, dirs, files in os.walk(str(tools_dir)):
        rel_root = os.path.relpath(str(root), str(tools_dir))

        for filename in files:
            if not filename.endswith('.py') or filename.startswith('_'):
                continue

            # 构建模块路径（如 'code_review.code_analyzer'）
            if rel_root == '.':
                module_path = filename[:-3]  # "get_weather"
            else:
                module_path = os.path.join(rel_root, filename[:-3]).replace(os.sep, '.')

            if module_path == 'registry':
                continue

            try:
                module = importlib.import_module(f'.{module_path}', package='tools')

                for attr_name in dir(module):
                    if attr_name.startswith('_'):
                        continue
                    attr = getattr(module, attr_name)
                    # 判断：有 invoke/name/description 且不是类
                    if (hasattr(attr, 'invoke') and
                            hasattr(attr, 'name') and
                            hasattr(attr, 'description') and
                            not isinstance(attr, type)):
                        discovered_tools.append(attr)
                        print(f"  ✅ [{module_path}] {attr.name}")

            except Exception as e:
                print(f"  ️ 加载 {module_path} 失败: {str(e)[:80]}")

        # 跳过 __pycache__
        dirs[:] = [d for d in dirs if d != '__pycache__']

    print(f"\n共发现 {len(discovered_tools)} 个工具")
    return discovered_tools