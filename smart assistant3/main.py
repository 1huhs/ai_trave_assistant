"""Smart Assistant v3 — 入口"""
from agent.langchain_agent import SmartAgent

if __name__ == "__main__":
    agent = SmartAgent()
    print("Smart Assistant v3 已启动。输入 'exit' 退出。\n")
    while True:
        user_input = input("你: ")
        if user_input.lower() in ("exit", "quit"):
            break
        result = agent.run(user_input)
        answer = result.get("messages", [None])[-1]
        if answer:
            print(f"\nAI: {answer.content}\n")
            print(agent.get_trace_summary())
