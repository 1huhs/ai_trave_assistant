"""
Agent 能力评估 Benchmark
========================
【阶段四】评测 Agent 的工具选择准确性、推理步数、任务完成率。

用法：
    python evaluation.py          → 跑完整评测
    python evaluation.py --quick  → 快速评测（5条）
"""
import os
import sys
import time
import json
import argparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from agent.langchain_agent import SmartAgent

# ═══════════════════════════════════════════════════════════
#  测试用例：覆盖单工具、多工具协同、跨领域等场景
# ═══════════════════════════════════════════════════════════

BENCHMARK_TASKS = [
    # ─── 单工具场景 ───
    {
        "id": "S001", "category": "单工具-天气",
        "input": "北京今天天气怎么样？",
        "expected_tools": ["get_weather"],
        "expected_keywords": ["天气", "度"],
    },
    {
        "id": "S002", "category": "单工具-汇率",
        "input": "100美元等于多少人民币？",
        "expected_tools": ["get_exchange_rate"],
        "expected_keywords": ["汇率", "CNY"],
    },
    {
        "id": "S003", "category": "单工具-时间",
        "input": "现在几点了？",
        "expected_tools": ["get_current_time"],
        "expected_keywords": ["202"],
    },
    {
        "id": "S004", "category": "单工具-计算",
        "input": "帮我算一下 1234 乘以 5678 等于多少？",
        "expected_tools": ["calculate"],
        "expected_keywords": ["700"],
    },
    {
        "id": "S005", "category": "单工具-知识库",
        "input": "Python 学习路线是什么？",
        "expected_tools": ["search_answer"],
        "expected_keywords": ["Python", "学习"],
    },
    {
        "id": "S006", "category": "单工具-健康",
        "input": "我身高175cm，体重160斤，帮我算一下BMI",
        "expected_tools": ["calculate_bmi"],
        "expected_keywords": ["BMI"],
    },

    # ─── 多工具协同场景 ───
    {
        "id": "M001", "category": "多工具-旅行规划",
        "input": "明天去香港旅游，帮我做一个两天一晚的计划，预算3000元",
        "expected_tools": ["get_weather", "search_answer"],
        "expected_keywords": ["香港", "行程"],
    },
    {
        "id": "M002", "category": "多工具-汇率旅行",
        "input": "我要去日本旅游，帮我查一下东京的天气和日元汇率",
        "expected_tools": ["get_weather", "get_exchange_rate"],
        "expected_keywords": ["天气", "汇率"],
    },
    {
        "id": "M003", "category": "多工具-健康综合",
        "input": "我190cm，230斤，帮我评估健康状况并制定减肥计划",
        "expected_tools": ["calculate_bmi", "search_answer"],
        "expected_keywords": ["BMI", "减肥", "饮食"],
    },
    {
        "id": "M004", "category": "多工具-学习规划",
        "input": "我想学编程，有什么建议？每天应该学多久？",
        "expected_tools": ["search_answer"],
        "expected_keywords": ["编程", "学习"],
    },

    # ─── 异常/边界场景 ───
    {
        "id": "E001", "category": "边界-闲聊",
        "input": "你好，你是谁？",
        "expected_tools": [],
        "expected_keywords": ["助手", "帮助"],
    },
    {
        "id": "E002", "category": "边界-模糊请求",
        "input": "帮我推荐一个旅游目的地",
        "expected_tools": ["search_answer"],
        "expected_keywords": ["旅游", "推荐"],
    },
]


def extract_tools_from_result(result) -> list:
    """
    从 Agent 返回结果中提取实际调用的工具名
    :param result: dict — agent.run() 的返回值
    :return: list[str] — 实际调用的工具名列表，如 ["get_weather", "search_answer"]
    """
    tools_called = []
    text = str(result)
    # 检查工具名关键词
    tool_names = [
        "get_weather", "get_exchange_rate", "get_current_time",
        "calculate", "search_answer", "calculate_bmi",
        "analyze_code", "optimize_code", "generate_tests",
        "plan_vacation", "generate_itinerary", "calculate_budget",
        "search_hotel", "search_attraction", "search_restaurant",
    ]
    for name in tool_names:
        if name in text.lower():
            tools_called.append(name)
    return tools_called


def evaluate_agent(agent: SmartAgent, tasks: list, verbose: bool = True):
    """
    逐条执行测试任务并计算评测指标
    :param agent: SmartAgent — 被测 Agent 实例
    :param tasks: list[dict] — BENCHMARK_TASKS 测试用例列表
    :param verbose: bool — 是否打印每条任务的结果
    :return: dict — 评测报告 {"total_tasks":12,"summary":{"overall_success_rate":"7/12 (58%)"},...}
    """
    results = []
    total_start = time.perf_counter()

    for i, task in enumerate(tasks):
        task_start = time.perf_counter()
        try:
            output = agent.run(task["input"])
            elapsed = (time.perf_counter() - task_start) * 1000
        except Exception as e:
            elapsed = (time.perf_counter() - task_start) * 1000
            output = {"error": str(e)}

        # 提取 AI 回答文本
        if isinstance(output, dict):
            answer = output.get("answer") or output.get("messages", [{}])[-1].content if "messages" in output else str(output)
        else:
            answer = str(output)

        # 分析工具调用
        tools_called = extract_tools_from_result(output)
        expected = task["expected_tools"]
        tools_recall = len(set(tools_called) & set(expected)) / len(expected) if expected else 1.0

        # 分析关键词
        keyword_hits = sum(1 for kw in task.get("expected_keywords", []) if kw.lower() in answer.lower())
        keyword_total = len(task.get("expected_keywords", []))
        keyword_score = keyword_hits / keyword_total if keyword_total else 1.0

        # 综合评分
        success = tools_recall >= 0.5 and keyword_score >= 0.5

        # 提取推理步数（从轨迹）
        steps = len([s for s in agent.execution_trace if s["step"] in ("ACTION",)]) if hasattr(agent, "execution_trace") else 1

        result = {
            "task_id": task["id"],
            "category": task["category"],
            "tools_expected": expected,
            "tools_called": tools_called,
            "tools_recall": round(tools_recall, 2),
            "keyword_score": round(keyword_score, 2),
            "steps": steps,
            "elapsed_ms": round(elapsed, 0),
            "success": success,
            "answer_preview": answer[:100],
        }
        results.append(result)

        if verbose:
            status = "✅" if success else "❌"
            print(f"  {status} {task['id']} [{task['category']}] "
                  f"工具={tools_called} vs {expected} | "
                  f"关键词={keyword_hits}/{keyword_total} | "
                  f"{elapsed:.0f}ms | {steps}步")

        # 确保数据库连接存在
        try:
            agent.memory.clear_conversations()
        except Exception:
            pass

    total_elapsed = (time.perf_counter() - total_start) * 1000

    # ── 汇总统计 ──
    successes = [r for r in results if r["success"]]
    single_tasks = [r for r in results if "单工具" in r["category"]]
    multi_tasks = [r for r in results if "多工具" in r["category"]]

    def avg(seq, key):
        vals = [r[key] for r in seq if key in r and r[key] is not None]
        return round(sum(vals) / len(vals), 2) if vals else 0

    report = {
        "total_tasks": len(results),
        "total_elapsed_ms": round(total_elapsed, 0),
        "summary": {
            "overall_success_rate": f"{len(successes)}/{len(results)} ({round(len(successes)/len(results)*100)}%)",
            "single_tool_accuracy": f"{len([r for r in single_tasks if r['success']])}/{len(single_tasks)}" if single_tasks else "N/A",
            "multi_tool_accuracy": f"{len([r for r in multi_tasks if r['success']])}/{len(multi_tasks)}" if multi_tasks else "N/A",
            "avg_tools_recall": avg(results, "tools_recall"),
            "avg_steps": avg(results, "steps"),
            "avg_elapsed_ms": avg(results, "elapsed_ms"),
        },
        "details": results,
    }

    return report


def print_report(report: dict):
    """打印格式化的评测报告"""
    s = report["summary"]
    print("\n" + "=" * 55)
    print("     Agent 能力评估报告")
    print("=" * 55)
    print(f"  测试任务数：      {report['total_tasks']}")
    print(f"  总耗时：          {report['total_elapsed_ms']:.0f}ms")
    print(f"  整体成功率：      {s['overall_success_rate']}")
    print(f"  单工具准确率：    {s['single_tool_accuracy']}")
    print(f"  多工具准确率：    {s['multi_tool_accuracy']}")
    print(f"  平均工具召回率：  {s['avg_tools_recall']:.0%}")
    print(f"  平均推理步数：    {s['avg_steps']:.1f}")
    print(f"  平均响应时间：    {s['avg_elapsed_ms']:.0f}ms")
    print("=" * 55)
    print()

    # 按分类汇总
    categories = {}
    for r in report["details"]:
        cat = r["category"].split("-")[0]
        if cat not in categories:
            categories[cat] = {"total": 0, "success": 0}
        categories[cat]["total"] += 1
        if r["success"]:
            categories[cat]["success"] += 1

    print("  按场景分类：")
    for cat, stats in sorted(categories.items()):
        pct = f"{stats['success']}/{stats['total']}"
        print(f"    {cat}: {pct}")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="快速评测（只测 5 条）")
    parser.add_argument("--output", type=str, default="", help="输出 JSON 报告路径")
    args = parser.parse_args()

    tasks = BENCHMARK_TASKS[:5] if args.quick else BENCHMARK_TASKS
    print(f"开始评测 {len(tasks)} 个任务...\n")
    agent = SmartAgent(user_id="benchmark")

    report = evaluate_agent(agent, tasks, verbose=True)
    print_report(report)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"JSON 报告已保存到 {args.output}")

    agent.memory.close()
