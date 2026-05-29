"""
执行轨迹可视化（HTML）
======================
【阶段三-3】将 Agent 的 execution_trace 渲染为 HTML 时间线图。
可直接截图放入简历/README。
"""


def generate_trace_html(trace: list, title: str = "Agent 推理轨迹") -> str:
    """
    根据 execution_trace 列表生成 HTML 可视化时间线图
    :param trace: list[dict] — SmartAgent.execution_trace
    :param title: str — HTML 页面标题
    :return: str — 完整 HTML 字符串，可直接写文件或浏览器打开
    :调用方: 手动调用，用于生成截图放 README
    """

    if not trace:
        return "<html><body><p>（无执行轨迹）</p></body></html>"

    steps_html = []
    colors = {
        "INPUT":       "#6B7280",
        "THOUGHT":     "#8B5CF6",
        "MEMORY":      "#10B981",
        "ACTION":      "#F59E0B",
        "OBSERVATION": "#3B82F6",
        "ANSWER":      "#059669",
    }
    icons = {
        "INPUT":       "💬", "THOUGHT":     "💭",
        "MEMORY":      "🧠", "ACTION":      "🔧",
        "OBSERVATION": "📋", "ANSWER":      "✅",
    }
    labels = {
        "INPUT":       "用户输入", "THOUGHT":     "Agent 思考",
        "MEMORY":      "记忆召回", "ACTION":      "调用工具",
        "OBSERVATION": "工具返回", "ANSWER":      "最终回答",
    }

    for i, step in enumerate(trace):
        step_type = step.get("step", "unknown")
        color = colors.get(step_type, "#9CA3AF")
        icon = icons.get(step_type, "❓")
        label = labels.get(step_type, step_type)

        # 构建内容
        content = ""
        if step_type == "ACTION":
            tool_name = step.get("tool", "?")
            args = step.get("args", {})
            content = f"<b>{tool_name}</b>"
            if args:
                content += f"<br><small>{_format_args(args)}</small>"
        elif step_type == "OBSERVATION":
            result = step.get("result", "")[:200]
            content = result
        else:
            content = step.get("content", "")[:200]
            if step_type == "THOUGHT" and len(step.get("content", "")) > 200:
                content += "..."

        steps_html.append(f"""
        <div class="step" style="border-left: 4px solid {color};">
            <div class="step-header">
                <span class="step-icon">{icon}</span>
                <span class="step-label" style="color:{color};">{label}</span>
                <span class="step-num">Step {i}</span>
            </div>
            <div class="step-content">{content}</div>
        </div>
        """)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
    font-family: "Microsoft YaHei", "PingFang SC", sans-serif;
    background: #F8FAFC;
    padding: 40px 20px;
    color: #1E293B;
}}
.container {{
    max-width: 720px;
    margin: 0 auto;
}}
h2 {{
    font-size: 22px;
    text-align: center;
    margin-bottom: 32px;
    color: #0F172A;
}}
.timeline {{
    position: relative;
    padding-left: 0;
}}
.step {{
    background: #FFFFFF;
    border-radius: 10px;
    padding: 16px 20px;
    margin-bottom: 14px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
}}
.step:hover {{
    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
}}
.step-header {{
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 8px;
}}
.step-icon {{ font-size: 18px; }}
.step-label {{
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}
.step-num {{
    margin-left: auto;
    font-size: 11px;
    color: #94A3B8;
}}
.step-content {{
    font-size: 14px;
    line-height: 1.7;
    color: #334155;
    white-space: pre-wrap;
    word-break: break-word;
}}
.step-content b {{ color: #1E293B; }}
.step-content small {{ color: #94A3B8; font-size:12px; }}
.footer {{
    text-align: center;
    margin-top: 24px;
    font-size: 12px;
    color: #94A3B8;
}}
</style>
</head>
<body>
<div class="container">
    <h2>{title}</h2>
    <div class="timeline">
        {''.join(steps_html)}
    </div>
    <p class="footer">Smart Assistant · Agent 推理过程可视化</p>
</div>
</body>
</html>"""


def _format_args(args: dict) -> str:
    """格式化工具参数为简短字符串"""
    items = []
    for k, v in args.items():
        v_str = str(v)
        if len(v_str) > 30:
            v_str = v_str[:30] + "..."
        items.append(f"{k}={v_str}")
    return ", ".join(items)


if __name__ == "__main__":
    # 测试数据
    sample_trace = [
        {"step": "INPUT", "content": "明天去香港旅游，预算3000元"},
        {"step": "MEMORY", "content": "[profile] 喜欢美食 [interest] 旅行"},
        {"step": "THOUGHT", "content": "用户需要旅游规划，应先查天气再查汇率"},
        {"step": "ACTION", "tool": "get_weather", "args": {"city": "香港"}},
        {"step": "OBSERVATION", "tool": "get_weather", "result": "香港的天气是晴，温度是28度"},
        {"step": "ACTION", "tool": "get_exchange_rate", "args": {"base": "CNY", "target": "HKD"}},
        {"step": "OBSERVATION", "tool": "get_exchange_rate", "result": "CNY兑换HKD的汇率为1.09"},
        {"step": "ANSWER", "content": "明天香港天气晴好，建议带防晒..."},
    ]
    html = generate_trace_html(sample_trace)
    print(html[:500])
