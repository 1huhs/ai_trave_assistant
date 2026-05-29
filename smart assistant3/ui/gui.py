"""
tkinter GUI 图形界面 — 连接 gui 和 agent
========================================
改动：在聊天窗显示 Agent 执行轨迹（调了什么工具、返回了什么）
"""
import tkinter as tk
import config
from tkinter import scrolledtext
import logging

logger = logging.getLogger(__name__)

# 轨迹消息颜色
TRACE_TAG_STYLE = {"foreground": "#666666", "font": ("Microsoft YaHei", 9)}


class AgentGui:
    """GUI设置"""

    def __init__(self, agent):
        self.agent = agent
        self.root = tk.Tk()
        self.root.title(config.WINDOW_TITLE)
        self.root.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.root.configure(bg="#FAFAFA")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.build_ui()

    def build_ui(self):
        # 顶部标题栏
        frame = tk.Frame(self.root, bg="#534AB7", height=50)
        frame.pack(fill=tk.X)
        frame.pack_propagate(False)

        tk.Label(
            frame, text="智能助手",
            font=("Microsoft YaHei", 16),
            bg="#534AB7", fg="white"
        ).pack(side=tk.LEFT)

        self.status_label = tk.Label(
            frame, text="就绪",
            font=("Microsoft YaHei", 12),
            bg="#534AB7", fg="#00FF00",
        )
        self.status_label.pack(side=tk.RIGHT, padx=20)

        # 聊天显示区
        chat_frame = tk.Frame(self.root, bg="#FAFAFA")
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.chat_display = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD,
            font=("Microsoft YaHei", 11),
            bg="#FFFFFF", fg="#333333",
            padx=10, pady=10,
            state=tk.DISABLED
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        self.chat_display.tag_config(
            "user", foreground="#333333",
            font=("Microsoft YaHei", 11, "bold"))
        self.chat_display.tag_config("agent", foreground="#333333")
        self.chat_display.tag_config("tool", foreground="#4A90D9",  # 蓝色工具消息
                                     font=("Microsoft YaHei", 9))
        self.chat_display.tag_config("thought", foreground="#888888",  # 灰色思考
                                     font=("Microsoft YaHei", 9, "italic"))

        # 输入框
        input_frame = tk.Frame(self.root, bg="#FAFAFA")
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        self.input_entry = tk.Entry(
            input_frame, font=("Microsoft YaHei", 12),
            bg="#FFFFFF", relief=tk.SOLID, bd=1
        )
        self.input_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8)
        self.input_entry.bind("<Return>", lambda e: self._on_send())

        send_btn = tk.Button(
            input_frame, text="发送",
            font=("Microsoft YaHei", 11, "bold"),
            bg="#534AB7", fg="white",
            activebackground="#3C3489", activeforeground="white",
            relief=tk.FLAT, cursor="hand2",
            command=self._on_send
        )
        send_btn.pack(side=tk.RIGHT, padx=(10, 0), ipadx=15, ipady=5)

        # 快捷按钮
        quick_frame = tk.Frame(self.root, bg="#FAFAFA")
        quick_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        quick_texts = [
            "帮我算一下 BMI", "深圳天气怎么样？",
            "1美元等于多少人民币？", "香港旅游预算建议",
        ]
        for text in quick_texts:
            btn = tk.Button(
                quick_frame, text=text,
                command=lambda t=text: self._quick_send(t),
            )
            btn.pack(side=tk.LEFT, padx=3, ipadx=5, ipady=2)

        self.root.mainloop()

    def _on_send(self):
        text = self.input_entry.get().strip()
        if not text:
            return
        self.input_entry.delete(0, tk.END)

        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"\n你：{text}\n", "user")
        self.chat_display.config(state=tk.DISABLED)

        self.status_label.config(text="AI 正在思考...")
        self.root.update()

        import threading
        thread = threading.Thread(target=self._run_agent, args=(text,))
        thread.daemon = True
        thread.start()

    def _run_agent(self, text):
        try:
            reply = self.agent.run(text)
            # 【新增】提取执行轨迹用于展示
            trace = self.agent.get_trace_summary()
            self.root.after(0, self._show_reply, reply, trace)
        except Exception as e:
            logger.error("GUI Agent执行异常|error=%s", e, exc_info=True)
            self.root.after(0, self._show_reply, f"出错了：{str(e)}", "")

    def _quick_send(self, text):
        self.input_entry.delete(0, tk.END)
        self.input_entry.insert(0, text)
        self._on_send()

    def _show_reply(self, reply, trace=""):
        """显示回复 + 执行轨迹"""
        self.chat_display.config(state=tk.NORMAL)

        # ── 先显示轨迹（工具调用过程）──
        if trace:
            # 只展示 ACTION 和 OBSERVATION 步骤
            for line in trace.split("\n"):
                stripped = line.strip()
                if stripped.startswith("Step"):
                    continue  # 跳过分隔线
                if "调用工具" in stripped or "工具返回" in stripped:
                    self.chat_display.insert(
                        tk.END, f" {stripped}\n", "tool")
                elif "思考" in stripped:
                    # 思考内容太长则截断
                    self.chat_display.insert(
                        tk.END, f" {stripped[:150]}\n", "thought")

        # ── 再显示 AI 最终回复 ──
        if isinstance(reply, str):
            self.chat_display.insert(tk.END, f"AI：{reply}\n\n", "agent")
        elif "answer" in reply and "messages" not in reply:
            self.chat_display.insert(tk.END, f"AI：{reply['answer']}\n\n", "agent")
        else:
            self.chat_display.insert(
                tk.END, f"AI：{reply['messages'][-1].content}\n\n", "agent")

        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        self.status_label.config(text="就绪")

    def on_closing(self):
        logger.info("GUI 关闭窗口")
        try:
            if hasattr(self.agent, "memory") and hasattr(self.agent.memory, "close"):
                self.agent.memory.close()
        except Exception:
            pass
        self.root.destroy()
