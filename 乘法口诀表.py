"""
🎮 乘法口诀表 - 桌面应用
CustomTkinter GUI + PyInstaller 打包 .exe
"""

import customtkinter as ctk
import random

# ─── 全局外观设置 ───
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# ─── 主题配色表 ───
THEME_COLORS = {
    "暗色经典": {"mode": "dark", "accent": "#3B8ED0"},
    "亮色经典": {"mode": "light", "accent": "#3B8ED0"},
    "暗夜紫":   {"mode": "dark", "accent": "#9B59B6"},
    "森林绿":   {"mode": "dark", "accent": "#27AE60"},
    "夕阳橙":   {"mode": "light", "accent": "#E67E22"},
}


class GameApp(ctk.CTk):
    """主应用窗口"""

    def __init__(self):
        super().__init__()

        # ── 窗口设置 ──
        self.title("🎮 乘法口诀表")
        self.geometry("800x600")
        self.minsize(700, 520)

        # ── 游戏状态 ──
        self.score = 5                # 当前分数
        self.highest_score = 0        # 历史最高
        self.time_left = 60           # 剩余秒数
        self.in_game = False          # 是否正在答题
        self.a = 0                    # 当前题：被乘数
        self.b = 0                    # 当前题：乘数
        self.timer_id = None          # 倒计时计时器 ID
        self.lose_timer_id = None     # 输了跳转计时器
        self.is_paused = False        # 是否暂停
        self.auto_play = False        # 是否自动答题
        self.auto_play_id = None      # 自动答题计时器 ID

        # ── 构建界面 ──
        self._build_ui()

        # ── 绑定全局快捷键 ──
        self.bind_all("<space>", self.toggle_pause)        # Space 暂停/继续
        self.bind_all("<Control-a>", self.toggle_auto_play) # Ctrl+A 自动答题
        self.bind("<Unmap>", self._on_window_unmap)        # 最小化 / 隐藏

        # ── 启动：显示口诀表 ──
        self.show_table()

    # ═══════════════════════════════════════════════════
    #  界面构建
    # ═══════════════════════════════════════════════════

    def _build_ui(self):
        """一次性创建所有控件"""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ─────── 标题栏 ───────
        self.title_bar = ctk.CTkFrame(self, height=48, corner_radius=0)
        self.title_bar.grid(row=0, column=0, sticky="ew")
        self.title_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.title_bar, text="📖  乘法口诀表",
            font=("Microsoft YaHei", 20, "bold"),
        ).pack(side="left", padx=20, pady=8)

        # 主题选择
        self.theme_menu = ctk.CTkOptionMenu(
            self.title_bar,
            values=list(THEME_COLORS.keys()),
            command=self.change_theme,
            width=110,
        )
        self.theme_menu.pack(side="right", padx=(0, 10), pady=8)

        # 最小化按钮
        ctk.CTkButton(
            self.title_bar, text="─", width=36, height=28,
            command=self.iconify,
        ).pack(side="right", padx=(0, 6), pady=8)

        # ─────── 倒计时区域 ───────
        self.timer_frame = ctk.CTkFrame(self, height=135, corner_radius=14)
        self.timer_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 5))
        self.timer_frame.grid_columnconfigure(0, weight=1)
        self.timer_frame.grid_propagate(False)

        # 倒计时数字（超大）
        self.timer_label = ctk.CTkLabel(
            self.timer_frame, text="⏱  60",
            font=("Arial", 54, "bold"),
        )
        self.timer_label.place(relx=0.5, rely=0.35, anchor="center")

        # 进度条
        self.progress_bar = ctk.CTkProgressBar(
            self.timer_frame, height=10, corner_radius=5,
        )
        self.progress_bar.place(relx=0.5, rely=0.78, anchor="center", relwidth=0.85)
        self.progress_bar.set(1.0)

        # ─────── 主内容区 ───────
        self.content = ctk.CTkFrame(self, corner_radius=14)
        self.content.grid(row=2, column=0, sticky="nsew", padx=20, pady=5)
        self.content.grid_columnconfigure(0, weight=1)
        self.content.grid_rowconfigure(0, weight=1)

        # 画面 1-5
        self._build_table_view()
        self._build_game_view()
        self._build_lose_view()
        self._build_result_view()
        self._build_pause_view()

        self._switch_view("table")

        # ─────── 底部状态栏 ───────
        self.status_bar = ctk.CTkFrame(self, height=34, corner_radius=0)
        self.status_bar.grid(row=3, column=0, sticky="ew")
        self.status_bar.grid_columnconfigure(0, weight=1)

        self.status_high = ctk.CTkLabel(
            self.status_bar, text="🏆  最高分：0",
            font=("Microsoft YaHei", 13),
        )
        self.status_high.pack(side="left", padx=18, pady=4)

        ctk.CTkLabel(
            self.status_bar,
            text="Enter 提交  |  Space 暂停  |  Ctrl+A 自动答题  |  ─ 最小化自动暂停",
            font=("Microsoft YaHei", 11),
        ).pack(side="right", padx=18, pady=4)

    # ─────── 子控件构建 ───────

    def _build_table_view(self):
        """口诀表页面（大字铺满）"""
        self.table_view = ctk.CTkFrame(self.content, corner_radius=10)
        self.table_view.grid(row=0, column=0, sticky="nsew")
        self.table_view.grid_columnconfigure(0, weight=1)
        self.table_view.grid_rowconfigure(0, weight=1)

        self.table_box = ctk.CTkTextbox(
            self.table_view,
            font=("Consolas", 24),
            wrap="none",
            state="disabled",
            corner_radius=8,
        )
        self.table_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.table_box.configure(state="normal")
        self.table_box.insert("end", "\n\n\n")
        self.table_box.insert("end", " " * 18 + "📖  乘法口诀表\n\n\n")
        for i in range(1, 10):
            line = "     "
            for j in range(1, i + 1):
                line += f"{j}×{i}={i * j:2d}   "
            self.table_box.insert("end", line + "\n\n")
        self.table_box.configure(state="disabled")

        self.ready_label = ctk.CTkLabel(
            self.table_view, text="⏳  即将开始答题...",
            font=("Microsoft YaHei", 18),
        )
        self.ready_label.place(relx=0.5, rely=0.92, anchor="center")

    def _build_game_view(self):
        """答题页面"""
        self.game_view = ctk.CTkFrame(self.content, corner_radius=10)
        self.game_view.grid(row=0, column=0, sticky="nsew")
        self.game_view.grid_columnconfigure(0, weight=1)
        self.game_view.grid_rowconfigure([0, 1, 2, 3], weight=1)

        # 自动答题指示器（右上角）
        self.auto_label = ctk.CTkLabel(
            self.game_view, text="",
            font=("Microsoft YaHei", 14),
            fg_color="transparent",
        )
        self.auto_label.place(relx=0.95, rely=0.05, anchor="ne")

        # 分数 & 爱心
        self.hearts_label = ctk.CTkLabel(
            self.game_view, text="❤️" * 5 + "   5 分",
            font=("Arial", 28),
        )
        self.hearts_label.grid(row=0, column=0, pady=(15, 5))

        # 题目
        self.question_label = ctk.CTkLabel(
            self.game_view, text="",
            font=("Arial", 38, "bold"),
        )
        self.question_label.grid(row=1, column=0, pady=5)

        # 输入区
        input_frame = ctk.CTkFrame(self.game_view, fg_color="transparent")
        input_frame.grid(row=2, column=0, pady=8)

        self.answer_entry = ctk.CTkEntry(
            input_frame, font=("Arial", 26), width=170,
            justify="center", placeholder_text="输入答案",
        )
        self.answer_entry.pack(side="left", padx=(0, 14))
        self.answer_entry.bind("<Return>", self.submit_answer)

        self.submit_btn = ctk.CTkButton(
            input_frame, text="提交", font=("Microsoft YaHei", 18),
            command=self.submit_answer, width=90, height=40,
        )
        self.submit_btn.pack(side="left")

        # 反馈
        self.feedback_label = ctk.CTkLabel(
            self.game_view, text="", font=("Arial", 22),
        )
        self.feedback_label.grid(row=3, column=0, pady=(5, 20))

    def _build_lose_view(self):
        """输了遮罩页面"""
        self.lose_view = ctk.CTkFrame(self.content, corner_radius=10, fg_color="#2B2B2B")
        self.lose_view.grid(row=0, column=0, sticky="nsew")
        self.lose_view.grid_columnconfigure(0, weight=1)
        self.lose_view.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(
            self.lose_view, text="💀  你输了！",
            font=("Arial", 64, "bold"),
            text_color="#FF2020",
        ).grid(row=0, column=0)

    def _build_result_view(self):
        """统计结果页面"""
        self.result_view = ctk.CTkFrame(self.content, corner_radius=10)
        self.result_view.grid(row=0, column=0, sticky="nsew")
        self.result_view.grid_columnconfigure(0, weight=1)
        self.result_view.grid_rowconfigure([0, 1, 2, 3], weight=1)

        ctk.CTkLabel(
            self.result_view, text="📊  本局统计",
            font=("Microsoft YaHei", 26, "bold"),
        ).grid(row=0, column=0, pady=(35, 5))

        self.final_score_label = ctk.CTkLabel(
            self.result_view, text="", font=("Arial", 28),
        )
        self.final_score_label.grid(row=1, column=0, pady=8)

        self.high_score_label = ctk.CTkLabel(
            self.result_view, text="", font=("Arial", 22),
        )
        self.high_score_label.grid(row=2, column=0, pady=8)

        self.next_btn = ctk.CTkButton(
            self.result_view, text="🔄  再来一把",
            font=("Microsoft YaHei", 20),
            command=self.start_next_round,
            width=200, height=45,
        )
        self.next_btn.grid(row=3, column=0, pady=15)

    def _build_pause_view(self):
        """暂停遮罩页面"""
        self.pause_view = ctk.CTkFrame(self.content, corner_radius=10, fg_color="#2B2B2B")
        self.pause_view.grid(row=0, column=0, sticky="nsew")
        self.pause_view.grid_columnconfigure(0, weight=1)
        self.pause_view.grid_rowconfigure([0, 1], weight=1)

        ctk.CTkLabel(
            self.pause_view, text="⏸  已暂停",
            font=("Arial", 56, "bold"),
        ).grid(row=0, column=0, pady=(60, 5))

        ctk.CTkLabel(
            self.pause_view, text="按  Space  继续答题",
            font=("Microsoft YaHei", 22),
        ).grid(row=1, column=0, pady=(5, 60))

    # ─────── 视图切换 ───────

    def _switch_view(self, name):
        """在 5 个页面间切换"""
        views = {
            "table":  self.table_view,
            "game":   self.game_view,
            "lose":   self.lose_view,
            "result": self.result_view,
            "pause":  self.pause_view,
        }
        views[name].tkraise()

    # ═══════════════════════════════════════════════════
    #  游戏流程
    # ═══════════════════════════════════════════════════

    def show_table(self):
        """阶段 1：显示乘法口诀表（3 秒后自动开始）"""
        self._switch_view("table")
        self.is_paused = False
        self.in_game = False
        self.ready_label.configure(text="⏳  即将开始答题...")
        self.after(3000, self.start_game)

    def start_game(self):
        """阶段 2：开始新一局答题"""
        self.score = 5
        self.time_left = 60
        self.in_game = True
        self.is_paused = False

        self.feedback_label.configure(text="")
        self.answer_entry.delete(0, "end")
        self.update_hearts()
        self.timer_label.configure(text="⏱  60")
        self.progress_bar.set(1.0)
        self.timer_label.configure(text_color=("black", "white"))

        self._switch_view("game")
        self.answer_entry.focus()

        # 出第一题
        self.next_question()

        # 启动倒计时
        if self.timer_id:
            self.after_cancel(self.timer_id)
        self.timer_id = self.after(1000, self.tick_timer)

    def tick_timer(self):
        """每秒更新倒计时"""
        if not self.in_game or self.is_paused:
            return
        self.time_left -= 1

        self.timer_label.configure(text=f"⏱  {self.time_left}")
        self.progress_bar.set(max(0, self.time_left / 60))

        if self.time_left <= 10:
            self.timer_label.configure(text_color="#FF4444")
        else:
            self.timer_label.configure(text_color=("black", "white"))

        if self.time_left <= 0:
            self.in_game = False
            self.on_time_up()
        else:
            self.timer_id = self.after(1000, self.tick_timer)

    def next_question(self):
        """生成下一道乘法题"""
        self.a = random.randint(1, 9)
        self.b = random.randint(1, self.a)
        self.question_label.configure(text=f"{self.a}  ×  {self.b}  =  ?")
        self.answer_entry.configure(state="normal")
        self.answer_entry.delete(0, "end")
        self.answer_entry.focus()

        # 自动答题模式：延迟极短时间后自动填写 + 提交
        if self.auto_play and self.in_game:
            self.auto_play_id = self.after(80, self._auto_play_submit)

    def submit_answer(self, event=None):
        """用户提交答案"""
        if not self.in_game or self.is_paused:
            return

        user_input = self.answer_entry.get().strip()
        if not user_input:
            return
        if not user_input.isdigit():
            self.feedback_label.configure(
                text="⚠️  请输入数字！", text_color="#F39C12"
            )
            return

        answer = int(user_input)
        correct = self.a * self.b

        if answer == correct:
            self.score += 1
            self.feedback_label.configure(
                text="✅  正确！  +1 分", text_color="#2ECC71"
            )
        else:
            self.score -= 1
            self.feedback_label.configure(
                text=f"❌  错误！  {self.a}×{self.b}={correct}  -1 分",
                text_color="#E74C3C",
            )

        self.update_hearts()
        self.answer_entry.delete(0, "end")

        if self.score <= 0:
            if self.timer_id:
                self.after_cancel(self.timer_id)
                self.timer_id = None
            self.in_game = False
            self.is_paused = False
            self.auto_play = False
            self.auto_label.configure(text="")
            self.on_lose()
        else:
            # 自动模式下反馈时间缩短
            delay = 120 if self.auto_play else 500
            self.answer_entry.configure(state="disabled")
            self.after(delay, self.next_question)

    # ─────── 自动答题 ───────

    def toggle_auto_play(self, event=None):
        """Ctrl+A 切换自动答题模式"""
        if not self.in_game:
            return "break"

        self.auto_play = not self.auto_play
        self.auto_label.configure(text="🤖  自动答题中" if self.auto_play else "")

        if self.auto_play:
            # 立即提交当前题目（如果有输入框没填）
            current = self.answer_entry.get().strip()
            if not current:
                # 还没输入 → 直接自动算
                self._auto_play_submit()
            else:
                self.submit_answer()

        return "break"

    def _auto_play_submit(self):
        """自动填写答案并提交"""
        if not self.auto_play or not self.in_game:
            return
        if self.is_paused:
            return

        answer = self.a * self.b
        self.answer_entry.configure(state="normal")
        self.answer_entry.delete(0, "end")
        self.answer_entry.insert(0, str(answer))
        self.submit_answer()

    # ─────── 暂停 / 继续 ───────

    def toggle_pause(self, event=None):
        """Space 键切换暂停/继续"""
        if not self.in_game and not self.is_paused:
            return "break"

        if self.is_paused:
            # 恢复
            self.is_paused = False
            self.in_game = True

            if self.timer_id:
                self.after_cancel(self.timer_id)
                self.timer_id = None

            self._switch_view("game")
            self.answer_entry.configure(state="normal")
            self.answer_entry.focus()

            self.tick_timer()

            # 自动答题模式：恢复后也自动触发
            if self.auto_play and self.in_game and not self.answer_entry.get():
                self.auto_play_id = self.after(150, self._auto_play_submit)
        else:
            # 暂停
            self.is_paused = True
            self.in_game = False

            if self.timer_id:
                self.after_cancel(self.timer_id)
                self.timer_id = None
            if self.auto_play_id:
                self.after_cancel(self.auto_play_id)
                self.auto_play_id = None

            self.answer_entry.configure(state="disabled")
            self._switch_view("pause")

        return "break"

    def _on_window_unmap(self, event):
        """窗口最小化/隐藏 → 自动暂停"""
        if event.widget != self:
            return
        self.after(100, self._auto_pause_on_minimize)

    def _auto_pause_on_minimize(self):
        """如果正在游戏中则自动暂停"""
        if self.state() == "iconic" and not self.is_paused and self.in_game:
            self.toggle_pause()

    # ─────── 结束条件 ───────

    def on_lose(self):
        """分数归零 → 显示巨大 '你输了'"""
        self._switch_view("lose")
        self.lose_timer_id = self.after(3000, self.show_result)

    def on_time_up(self):
        """时间到 → 统计结果"""
        self.in_game = False
        self.is_paused = False
        self.auto_play = False
        self.auto_label.configure(text="")
        self.answer_entry.configure(state="disabled")
        self.submit_btn.configure(state="disabled")
        self.show_result()

    def show_result(self):
        """阶段 3：显示本局统计"""
        self._switch_view("result")
        self.in_game = False
        self.is_paused = False
        self.submit_btn.configure(state="normal")

        self.final_score_label.configure(
            text=f"本局得分：{self.score} 分"
        )

        if self.score > self.highest_score:
            self.highest_score = self.score
            self.high_score_label.configure(
                text=f"🎉  新纪录！最高分：{self.highest_score}",
                text_color="#F1C40F",
            )
            self.status_high.configure(
                text=f"🏆  最高分：{self.highest_score}"
            )
        else:
            self.high_score_label.configure(
                text=f"历史最高分：{self.highest_score} 分",
            )

    def start_next_round(self):
        """阶段 4：再来一把 → 回到阶段 1"""
        if self.timer_id:
            self.after_cancel(self.timer_id)
            self.timer_id = None
        if self.lose_timer_id:
            self.after_cancel(self.lose_timer_id)
            self.lose_timer_id = None
        if self.auto_play_id:
            self.after_cancel(self.auto_play_id)
            self.auto_play_id = None

        self.is_paused = False
        self.submit_btn.configure(state="normal")
        self.show_table()

    # ─────── 辅助方法 ───────

    def update_hearts(self):
        """更新爱心显示"""
        hearts = max(0, self.score)
        empty = 5 - hearts
        self.hearts_label.configure(
            text="❤️" * hearts + "🖤" * empty + f"   {self.score} 分"
        )

    def change_theme(self, choice):
        """切换主题 / 配色"""
        cfg = THEME_COLORS[choice]
        ctk.set_appearance_mode(cfg["mode"])
        accent = cfg["accent"]

        for w in [self.theme_menu, self.submit_btn, self.next_btn]:
            try:
                w.configure(fg_color=accent)
            except Exception:
                pass


# ═══════════════════════════════════════════════════
#  入口
# ═══════════════════════════════════════════════════

if __name__ == "__main__":
    app = GameApp()
    app.mainloop()
