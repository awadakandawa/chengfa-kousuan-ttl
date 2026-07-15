"""
🎮 乘法口算天天练 - 桌面应用
系统播放器播视频 + 后台计时自动给复活
"""

import customtkinter as ctk
import tkinter as tk
import random
import os
import sys
import threading
import time
import json

# ─── 全局外观 ───
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

THEME_COLORS = {
    "暗色经典": {"mode": "dark", "accent": "#3B8ED0"},
    "亮色经典": {"mode": "light", "accent": "#3B8ED0"},
    "暗夜紫":   {"mode": "dark", "accent": "#9B59B6"},
    "森林绿":   {"mode": "dark", "accent": "#27AE60"},
    "夕阳橙":   {"mode": "light", "accent": "#E67E22"},
}

VIDEO_FILENAME = "微信视频2026-07-15_170709_015.mp4"


def _video_path():
    """获取视频文件路径（兼容开发环境和 PyInstaller 打包）"""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, VIDEO_FILENAME)


def _storage_path():
    """获取数据存储文件路径（持久化保存游戏记录）"""
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), "乘法口算天天练_data.json")
    else:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), "乘法口算天天练_data.json")


def _bind_tooltip(widget, text):
    """给控件绑定悬停提示"""
    tip_win = None

    def show(e):
        nonlocal tip_win
        if tip_win:
            return
        x = widget.winfo_rootx() + 16
        y = widget.winfo_rooty() + widget.winfo_height() + 4
        tip_win = tk.Toplevel(widget)
        tip_win.wm_overrideredirect(True)
        tip_win.wm_geometry(f"+{x}+{y}")
        tip_win.attributes("-topmost", True)
        tk.Label(tip_win, text=text, background="#FFFFDD", fg="#333",
                 font=("Microsoft YaHei", 10), padx=7, pady=3,
                 justify="left").pack()

    def hide(e):
        nonlocal tip_win
        if tip_win:
            tip_win.destroy()
            tip_win = None

    widget.bind("<Enter>", show, add="+")
    widget.bind("<Leave>", hide, add="+")


class GameApp(ctk.CTk):
    """主应用窗口"""

    def __init__(self):
        super().__init__()

        self.title("🎮 乘法口算天天练")
        self.geometry("800x600")
        self.minsize(700, 520)

        # ── 游戏状态 ──
        self.score = 3
        self.highest_score = 0
        self.time_left = 60
        self.in_game = False
        self.a = 0
        self.b = 0
        self.timer_id = None
        self.lose_timer_id = None
        self.is_paused = False
        self.auto_play = False
        self.auto_play_id = None

        # ── 复活系统 ──
        self.revive_count = 0
        # (视频播放使用系统播放器 + 后台线程，无需维护状态)

        # ── 持久化状态 ──
        self.top_scores = []       # [{"score": N, "time": "YYYY-MM-DD HH:MM:SS"}, ...]
        self.countdown_time = 60

        # ── 设置状态 ──
        self.show_table_during_game = False
        self._table_popup = None
        self._settings_win = None

        self._build_ui()

        self.bind_all("<space>", self.toggle_pause)
        self.bind_all("<Control-a>", self.toggle_auto_play)
        self.bind("<Unmap>", self._on_window_unmap)
        self.bind_all("<Control-q>", lambda e: self._on_closing())
        self.bind_all("<Control-Q>", lambda e: self._on_closing())
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        self._table_row = 0

        # 加载持久化数据
        self._load_data()
        self._update_revive_display()
        self.status_high.configure(text=f"🏆  最高分：{self.highest_score}")

        self.show_table()

    # ═══════════════════════════════════════════════════
    #  界面构建
    # ═══════════════════════════════════════════════════

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ─────── 标题栏 ───────
        self.title_bar = ctk.CTkFrame(self, height=48, corner_radius=0)
        self.title_bar.grid(row=0, column=0, sticky="ew")
        self.title_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            self.title_bar, text="📖  乘法口算天天练",
            font=("Microsoft YaHei", 20, "bold"),
        ).pack(side="left", padx=20, pady=8)

        # 复活按钮
        self.revive_frame = ctk.CTkFrame(self.title_bar, fg_color="transparent")
        self.revive_frame.pack(side="right", padx=(0, 4), pady=8)

        self.revive_btn = ctk.CTkButton(
            self.revive_frame, text="📺", width=42, height=28,
            command=self._open_revive_dialog,
            font=("Arial", 16),
        )
        self.revive_btn.pack()
        _bind_tooltip(self.revive_btn, "看视频获得复活机会\n当前可用：" + ("0 次" if self.revive_count == 0 else f"{self.revive_count} 次"))

        self.revive_badge = ctk.CTkLabel(
            self.revive_frame, text="",
            font=("Arial", 11, "bold"),
            text_color="#FFFFFF", fg_color="#FF4444",
            width=18, height=18, corner_radius=9,
        )
        self.revive_badge.place(relx=0.85, rely=-0.15, anchor="ne")

        # 设置按钮
        self.settings_btn = ctk.CTkButton(
            self.title_bar, text="⚙️", width=42, height=28,
            command=self._open_settings,
            font=("Arial", 16),
        )
        self.settings_btn.pack(side="right", padx=(0, 4), pady=8)
        _bind_tooltip(self.settings_btn, "设置：主题颜色 / 浮窗 / 自动答题 / 倒计时")

        # 历史记录按钮
        self.record_btn = ctk.CTkButton(
            self.title_bar, text="🏆", width=42, height=28,
            command=self._open_records,
            font=("Arial", 16),
        )
        self.record_btn.pack(side="right", padx=(0, 4), pady=8)
        _bind_tooltip(self.record_btn, "历史记录：查看最高 5 条成绩排行")

        # 关闭按钮
        self.close_btn = ctk.CTkButton(
            self.title_bar, text="✕", width=36, height=28,
            command=self._on_closing,
            font=("Arial", 16),
            fg_color="#CC3333", hover_color="#AA2222",
        )
        self.close_btn.pack(side="right", padx=(0, 8), pady=8)
        _bind_tooltip(self.close_btn, "关闭程序")

        # ─────── 倒计时区域 ───────
        self.timer_frame = ctk.CTkFrame(self, height=135, corner_radius=14)
        self.timer_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 5))
        self.timer_frame.grid_columnconfigure(0, weight=1)
        self.timer_frame.grid_propagate(False)

        self.timer_label = ctk.CTkLabel(
            self.timer_frame, text="⏱  60",
            font=("Arial", 54, "bold"),
        )
        self.timer_label.place(relx=0.5, rely=0.35, anchor="center")

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
            self.status_bar, text="Enter 提交  |  Space 暂停  |  🏆 历史记录",
            font=("Microsoft YaHei", 11),
        ).pack(side="right", padx=18, pady=4)

    # ─────── 子控件 ───────

    def _build_table_view(self):
        self.table_view = ctk.CTkFrame(self.content, corner_radius=10)
        self.table_view.grid(row=0, column=0, sticky="nsew")
        self.table_view.grid_columnconfigure(0, weight=1)
        self.table_view.grid_rowconfigure(0, weight=1)

        self.table_box = ctk.CTkTextbox(
            self.table_view, font=("Consolas", 24),
            wrap="none", state="disabled", corner_radius=8,
        )
        self.table_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.ready_label = ctk.CTkLabel(
            self.table_view, text="",
            font=("Microsoft YaHei", 18),
        )
        self.ready_label.place(relx=0.5, rely=0.92, anchor="center")

    def _build_game_view(self):
        self.game_view = ctk.CTkFrame(self.content, corner_radius=10)
        self.game_view.grid(row=0, column=0, sticky="nsew")
        self.game_view.grid_columnconfigure(0, weight=1)
        self.game_view.grid_rowconfigure([0, 1, 2, 3], weight=1)

        # 左上复活 + 口诀表入口
        self.game_tl = ctk.CTkFrame(self.game_view, fg_color="transparent")
        self.game_tl.place(relx=0.02, rely=0.02, anchor="nw")

        self.game_revive_label = ctk.CTkLabel(
            self.game_tl, text="", font=("Microsoft YaHei", 13),
        )
        self.game_revive_label.pack(side="left", padx=(0, 6))

        self.game_table_btn = ctk.CTkButton(
            self.game_tl, text="📖", width=28, height=24,
            command=self._toggle_table_popup, font=("Arial", 13),
        )
        _bind_tooltip(self.game_table_btn, "查看乘法口诀表（计时不停止）")

        # 右上自动答题指示
        self.auto_label = ctk.CTkLabel(
            self.game_view, text="",
            font=("Microsoft YaHei", 13),
        )
        self.auto_label.place(relx=0.95, rely=0.03, anchor="ne")

        # 分数
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

        # 输入
        input_frame = ctk.CTkFrame(self.game_view, fg_color="transparent")
        input_frame.grid(row=2, column=0, pady=8)

        self.answer_entry = ctk.CTkEntry(
            input_frame, font=("Arial", 26), width=170,
            justify="center", placeholder_text="输入答案",
        )
        self.answer_entry.pack(side="left", padx=(0, 14))
        self.answer_entry.bind("<Return>", self.submit_answer)
        _bind_tooltip(self.answer_entry, "输入数字答案，按 Enter 提交")

        self.submit_btn = ctk.CTkButton(
            input_frame, text="提交", font=("Microsoft YaHei", 18),
            command=self.submit_answer, width=90, height=40,
        )
        self.submit_btn.pack(side="left")
        _bind_tooltip(self.submit_btn, "提交当前答案")

        # 反馈
        self.feedback_label = ctk.CTkLabel(
            self.game_view, text="", font=("Arial", 22),
        )
        self.feedback_label.grid(row=3, column=0, pady=(5, 5))

        # 底部复活次数（可点击）
        self.bottom_revive_label = ctk.CTkLabel(
            self.game_view, text="", font=("Microsoft YaHei", 14),
            cursor="hand2", text_color="#E67E22",
        )
        self.bottom_revive_label.grid(row=4, column=0, pady=(0, 10))
        self.bottom_revive_label.bind("<Button-1>", lambda e: self._open_revive_dialog())

    def _build_lose_view(self):
        self.lose_view = ctk.CTkFrame(self.content, corner_radius=10)
        self.lose_view.grid(row=0, column=0, sticky="nsew")
        self.lose_view.grid_columnconfigure(0, weight=1)
        self.lose_view.grid_rowconfigure([0, 1, 2], weight=1)

        ctk.CTkLabel(
            self.lose_view, text="💀  你输了！",
            font=("Arial", 56, "bold"), text_color="#FF2020",
        ).grid(row=0, column=0, pady=(30, 10))

        self.lose_btn_frame = ctk.CTkFrame(self.lose_view, fg_color="transparent")
        self.lose_btn_frame.grid(row=1, column=0, pady=10)

        self.lose_revive_btn = ctk.CTkButton(
            self.lose_btn_frame, text="💊  使用复活", font=("Microsoft YaHei", 18),
            command=self._use_revive, width=160, height=40,
            fg_color="#E67E22", hover_color="#D35400",
        )
        self.lose_revive_btn.pack(side="left", padx=8)
        _bind_tooltip(self.lose_revive_btn, "消耗一次复活机会，从 1 分继续游戏")

        self.lose_restart_btn = ctk.CTkButton(
            self.lose_btn_frame, text="🔄  重新开始", font=("Microsoft YaHei", 18),
            command=lambda: self.start_next_round(), width=160, height=40,
        )
        self.lose_restart_btn.pack(side="left", padx=8)
        _bind_tooltip(self.lose_restart_btn, "放弃本局，重新开始")

        self.lose_watch_btn = ctk.CTkButton(
            self.lose_btn_frame, text="📺  看视频得复活", font=("Microsoft YaHei", 18),
            command=self._play_video, width=160, height=40,
            fg_color="#E74C3C", hover_color="#C0392B",
        )
        _bind_tooltip(self.lose_watch_btn, "观看完整视频获得一次复活机会")

        self.lose_no_revive_label = ctk.CTkLabel(
            self.lose_view, text="", font=("Microsoft YaHei", 16),
        )
        self.lose_no_revive_label.grid(row=2, column=0, pady=(5, 30))

    def _build_result_view(self):
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
        _bind_tooltip(self.next_btn, "开始新的一局")

    def _build_pause_view(self):
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
        views = {
            "table":  self.table_view,
            "game":   self.game_view,
            "lose":   self.lose_view,
            "result": self.result_view,
            "pause":  self.pause_view,
        }
        if name in views:
            views[name].tkraise()

    # ═══════════════════════════════════════════════════
    #  口诀表 · 逐行动画
    # ═══════════════════════════════════════════════════

    def show_table(self):
        self._switch_view("table")
        self.is_paused = False
        self.in_game = False
        self.ready_label.configure(text="")

        self.table_box.configure(state="normal")
        self.table_box.delete("1.0", "end")
        self.table_box.insert("end", "\n\n\n")
        self.table_box.insert("end", " " * 18 + "📖  乘法口诀表\n\n\n")
        self.table_box.configure(state="disabled")

        self._table_row = 1
        self._animate_table()

    def _animate_table(self):
        if self._table_row > 9:
            self.ready_label.configure(text="⏳  即将开始答题...")
            self.after(1500, self.start_game)
            return
        i = self._table_row
        line = "     "
        for j in range(1, i + 1):
            line += f"{j}×{i}={i * j:2d}   "
        self.table_box.configure(state="normal")
        self.table_box.insert("end", line + "\n\n")
        self.table_box.see("end")
        self.table_box.configure(state="disabled")
        self._table_row += 1
        self.after(1000, self._animate_table)

    # ═══════════════════════════════════════════════════
    #  游戏流程
    # ═══════════════════════════════════════════════════

    def start_game(self):
        self.score = 3
        self.time_left = self.countdown_time
        self.in_game = True
        self.is_paused = False

        self.feedback_label.configure(text="")
        self.answer_entry.delete(0, "end")
        self._update_hearts()
        self.timer_label.configure(text=f"⏱  {self.countdown_time}")
        self.progress_bar.set(1.0)
        self.timer_label.configure(text_color=("black", "white"))

        self._update_revive_display()
        self._update_table_btn()

        self._switch_view("game")
        self.answer_entry.focus()
        self.next_question()

        if self.timer_id:
            self.after_cancel(self.timer_id)
        self.timer_id = self.after(1000, self.tick_timer)

    def tick_timer(self):
        if not self.in_game or self.is_paused:
            return
        self.time_left -= 1
        self.timer_label.configure(text=f"⏱  {self.time_left}")
        self.progress_bar.set(max(0, self.time_left / self.countdown_time))
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
        self.a = random.randint(1, 9)
        self.b = random.randint(1, self.a)
        self.question_label.configure(text=f"{self.a}  ×  {self.b}  =  ?")
        self.answer_entry.configure(state="normal")
        self.answer_entry.delete(0, "end")
        self.answer_entry.focus()
        if self.auto_play and self.in_game:
            self.auto_play_id = self.after(80, self._auto_play_submit)

    def submit_answer(self, event=None):
        if not self.in_game or self.is_paused:
            return
        user_input = self.answer_entry.get().strip()
        if not user_input:
            return
        if not user_input.isdigit():
            self.feedback_label.configure(text="⚠️  请输入数字！", text_color="#F39C12")
            return

        answer = int(user_input)
        correct = self.a * self.b

        if answer == correct:
            self.score += 1
            self.feedback_label.configure(text="✅  正确！  +1 分", text_color="#2ECC71")
        else:
            self.score -= 1
            self.feedback_label.configure(
                text=f"❌  错误！  {self.a}×{self.b}={correct}  -1 分",
                text_color="#E74C3C",
            )

        self._update_hearts()
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
            delay = 120 if self.auto_play else 500
            self.answer_entry.configure(state="disabled")
            self.after(delay, self.next_question)

    # ═══════════════════════════════════════════════════
    #  自动答题
    # ═══════════════════════════════════════════════════

    def toggle_auto_play(self, event=None):
        if not self.in_game:
            return "break"
        self.auto_play = not self.auto_play
        self.auto_label.configure(text="🤖  自动答题中" if self.auto_play else "")
        if self.auto_play:
            cur = self.answer_entry.get().strip()
            if not cur:
                self._auto_play_submit()
            else:
                self.submit_answer()
        return "break"

    def _auto_play_submit(self):
        if not self.auto_play or not self.in_game or self.is_paused:
            return
        ans = self.a * self.b
        self.answer_entry.configure(state="normal")
        self.answer_entry.delete(0, "end")
        self.answer_entry.insert(0, str(ans))
        self.submit_answer()

    # ═══════════════════════════════════════════════════
    #  暂停
    # ═══════════════════════════════════════════════════

    def toggle_pause(self, event=None):
        if not self.in_game and not self.is_paused:
            return "break"
        if self.is_paused:
            self.is_paused = False
            self.in_game = True
            if self.timer_id:
                self.after_cancel(self.timer_id)
                self.timer_id = None
            self._switch_view("game")
            self.answer_entry.configure(state="normal")
            self.answer_entry.focus()
            self.tick_timer()
            if self.auto_play and not self.answer_entry.get():
                self.auto_play_id = self.after(150, self._auto_play_submit)
        else:
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
        if event.widget != self:
            return
        self.after(100, self._auto_pause_on_minimize)

    def _auto_pause_on_minimize(self):
        if self.state() == "iconic" and not self.is_paused and self.in_game:
            self.toggle_pause()

    # ═══════════════════════════════════════════════════
    #  复活系统
    # ═══════════════════════════════════════════════════

    def _update_revive_display(self):
        cnt = self.revive_count
        self.revive_badge.configure(text=str(cnt) if cnt > 0 else "")
        self.game_revive_label.configure(
            text=f"💊 × {cnt}" if cnt > 0 else ""
        )
        self.bottom_revive_label.configure(
            text=f"💊  复活次数：{cnt}  （点击看视频获取）" if cnt >= 0 else ""
        )
        _bind_tooltip(self.revive_btn,
            "看视频获得复活机会\n当前可用：" + (f"{cnt} 次" if cnt > 0 else "0 次"))

    def _open_revive_dialog(self):
        """标题栏 📺 按钮 → 弹出复活对话框"""
        dlg = ctk.CTkToplevel(self)
        dlg.title("📺 复活")
        dlg.geometry("320x180")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.attributes("-topmost", True)

        ctk.CTkLabel(
            dlg, text=f"当前复活次数：{self.revive_count}",
            font=("Microsoft YaHei", 18),
        ).pack(pady=(20, 15))

        ctk.CTkButton(
            dlg, text="📺  看视频得 1 次复活",
            font=("Microsoft YaHei", 16),
            command=lambda: [dlg.destroy(), self._play_video()],
            fg_color="#E74C3C", hover_color="#C0392B",
            width=220, height=40,
        ).pack(pady=5)

        ctk.CTkButton(
            dlg, text="关闭", font=("Microsoft YaHei", 14),
            command=dlg.destroy, width=100,
        ).pack(pady=8)

    def _play_video(self):
        """打开系统播放器 + 后台计时，等待后自动给复活"""
        path = _video_path()
        if not os.path.exists(path):
            self._show_tip("❌  视频文件未找到", "请确保视频已正确打包")
            return

        wait_sec = 6  # 固定等待 6 秒

        # 通知用户
        tip = ctk.CTkToplevel(self)
        tip.title("")
        tip.geometry("350x150")
        tip.resizable(False, False)
        tip.transient(self)
        tip.grab_set()
        tip.attributes("-topmost", True)
        tip.update_idletasks()
        sw, sh = tip.winfo_screenwidth(), tip.winfo_screenheight()
        tip.geometry(f"+{(sw-350)//2}+{(sh-150)//2}")

        ctk.CTkLabel(
            tip, text="📺  正在播放视频", font=("Microsoft YaHei", 20, "bold"),
        ).pack(pady=(20, 5))
        ctk.CTkLabel(
            tip, text="播放完成后自动获得复活机会\n（可最小化此窗口）",
            font=("Microsoft YaHei", 13),
        ).pack()

        # 打开系统默认播放器
        os.startfile(path)

        # 后台线程等待
        def _wait():
            time.sleep(wait_sec)
            try:
                tip.destroy()
            except:
                pass
            self.after(0, self._grant_revive)

        threading.Thread(target=_wait, daemon=True).start()

    def _close_player(self):  # 保留但不再使用（兼容引用）
        pass

    def _grant_revive(self):
        """授予一次复活机会"""
        self.revive_count += 1
        self._update_revive_display()
        self._save_data()
        self._show_tip("✅  获得一次复活机会！",
                       f"当前共 {self.revive_count} 次，可在失败时使用")

        # 如果当前在输了界面，刷新按钮状态
        self._update_lose_buttons()

    def _update_lose_buttons(self):
        """根据复活次数更新输了界面的按钮"""
        if self.revive_count > 0:
            self.lose_revive_btn.configure(
                text=f"💊  使用复活 ({self.revive_count})", state="normal")
            self.lose_watch_btn.pack_forget()
            self.lose_no_revive_label.configure(text="")
        else:
            self.lose_revive_btn.configure(state="disabled")
            self.lose_watch_btn.pack(before=self.lose_no_revive_label,
                                      in_=self.lose_btn_frame,
                                      side="left", padx=8)
            self.lose_no_revive_label.configure(
                text="没有复活次数了", text_color="#95A5A6")

    def _auto_popup_revive_video(self):
        """自动弹出看视频复活对话框"""
        dlg = ctk.CTkToplevel(self)
        dlg.title("📺 没有复活次数了")
        dlg.geometry("340x200")
        dlg.resizable(False, False)
        dlg.transient(self)
        dlg.grab_set()
        dlg.attributes("-topmost", True)
        dlg.update_idletasks()
        sw, sh = dlg.winfo_screenwidth(), dlg.winfo_screenheight()
        dlg.geometry(f"+{(sw-340)//2}+{(sh-200)//2}")

        ctk.CTkLabel(
            dlg, text="💀  没有复活次数了！",
            font=("Microsoft YaHei", 20, "bold"),
        ).pack(pady=(20, 8))
        ctk.CTkLabel(
            dlg, text="看一个视频可以获得一次复活机会",
            font=("Microsoft YaHei", 14),
        ).pack(pady=(0, 15))

        btn_frame = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_frame.pack()

        ctk.CTkButton(
            btn_frame, text="📺  看视频得复活",
            font=("Microsoft YaHei", 16),
            command=lambda: [dlg.destroy(), self._play_video()],
            fg_color="#E74C3C", hover_color="#C0392B",
            width=170, height=38,
        ).pack(side="left", padx=6)

        ctk.CTkButton(
            btn_frame, text="关闭", font=("Microsoft YaHei", 14),
            command=dlg.destroy, width=80,
        ).pack(side="left", padx=6)

    def _use_revive(self):
        """使用一次复活"""
        if self.revive_count <= 0:
            return
        self.revive_count -= 1
        self._update_revive_display()
        self._save_data()

        self.score = 1
        self._update_hearts()
        self.in_game = True
        self.is_paused = False
        self.auto_label.configure(text="")

        self._switch_view("game")
        self.answer_entry.configure(state="normal")
        self.answer_entry.focus()
        self.feedback_label.configure(text="💊  已复活！从 1 分继续！", text_color="#E67E22")

        if self.timer_id:
            self.after_cancel(self.timer_id)
        self.timer_id = self.after(1000, self.tick_timer)
        self.answer_entry.configure(state="disabled")
        self.after(800, self.next_question)

    # ═══════════════════════════════════════════════════
    #  结束条件
    # ═══════════════════════════════════════════════════

    def on_lose(self):
        self._switch_view("lose")
        self._update_lose_buttons()

        if self.revive_count > 0:
            self.lose_revive_btn.configure(state="normal")
            self.lose_watch_btn.pack_forget()
        else:
            self.lose_revive_btn.configure(state="disabled")
            self.lose_watch_btn.pack(
                before=self.lose_no_revive_label,
                in_=self.lose_btn_frame,
                side="left", padx=8)
            # 没复活机会时自动弹出看视频对话框
            self.after(200, self._auto_popup_revive_video)

    def on_time_up(self):
        self.in_game = False
        self.is_paused = False
        self.auto_play = False
        self.auto_label.configure(text="")
        self.answer_entry.configure(state="disabled")
        self.submit_btn.configure(state="disabled")
        self.show_result()

    def show_result(self):
        self._switch_view("result")
        self.in_game = False
        self.is_paused = False
        self.submit_btn.configure(state="normal")

        self.final_score_label.configure(text=f"本局得分：{self.score} 分")
        if self.score > self.highest_score:
            self.highest_score = self.score
            self.high_score_label.configure(
                text=f"🎉  新纪录！最高分：{self.highest_score}",
                text_color="#F1C40F")
            self.status_high.configure(text=f"🏆  最高分：{self.highest_score}")
        else:
            self.high_score_label.configure(text=f"历史最高分：{self.highest_score} 分")

        # 保存到排行榜（记录当前时刻）
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.top_scores.append({"score": self.score, "time": now})
        self.top_scores.sort(key=lambda x: x["score"], reverse=True)
        self.top_scores = self.top_scores[:5]
        self._save_data()

    def start_next_round(self):
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
        self._table_row = 0
        self.show_table()

    # ═══════════════════════════════════════════════════
    #  口诀表浮窗
    # ═══════════════════════════════════════════════════

    def _update_table_btn(self):
        if self.show_table_during_game:
            self.game_table_btn.pack(side="left")
        else:
            self.game_table_btn.pack_forget()

    def _toggle_table_popup(self):
        if self._table_popup and self._table_popup.winfo_exists():
            self._table_popup.destroy()
            self._table_popup = None
            return
        self._table_popup = ctk.CTkToplevel(self)
        self._table_popup.title("📖 乘法口诀表")
        self._table_popup.geometry("400x360")

        box = ctk.CTkTextbox(
            self._table_popup, font=("Consolas", 18),
            wrap="none", state="disabled", corner_radius=8,
        )
        box.pack(expand=True, fill="both", padx=10, pady=10)
        box.configure(state="normal")
        box.insert("end", " " * 10 + "📖  乘法口诀表\n\n")
        for i in range(1, 10):
            line = "  "
            for j in range(1, i + 1):
                line += f"{j}×{i}={i * j:2d}   "
            box.insert("end", line + "\n\n")
        box.configure(state="disabled")
        self._table_popup.protocol("WM_DELETE_WINDOW", self._close_table_popup)

    def _close_table_popup(self):
        if self._table_popup:
            self._table_popup.destroy()
            self._table_popup = None

    # ═══════════════════════════════════════════════════
    #  持久化存储
    # ═══════════════════════════════════════════════════

    def _load_data(self):
        """从 JSON 文件加载持久化数据"""
        path = _storage_path()
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.highest_score = data.get("highest_score", 0)
                self.revive_count = data.get("revive_count", 0)
                self.top_scores = data.get("top_scores", [])
                self.countdown_time = data.get("countdown_time", 60)
            except Exception:
                pass

    def _save_data(self):
        """保存持久化数据到 JSON 文件"""
        path = _storage_path()
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({
                    "highest_score": self.highest_score,
                    "revive_count": self.revive_count,
                    "top_scores": self.top_scores,
                    "countdown_time": self.countdown_time,
                }, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════
    #  历史记录
    # ═══════════════════════════════════════════════════

    def _open_records(self):
        """打开历史最高分排行窗口"""
        win = ctk.CTkToplevel(self)
        win.title("🏆 历史记录")
        win.geometry("420x400")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()
        win.attributes("-topmost", True)
        win.update_idletasks()
        sw, sh = win.winfo_screenwidth(), win.winfo_screenheight()
        win.geometry(f"+{(sw-420)//2}+{(sh-400)//2}")

        ctk.CTkLabel(
            win, text="🏆  历史最高分排行",
            font=("Microsoft YaHei", 22, "bold"),
        ).pack(pady=(20, 15))

        if not self.top_scores:
            ctk.CTkLabel(
                win, text="暂无记录", font=("Microsoft YaHei", 16),
                text_color="#95A5A6",
            ).pack(pady=40)
        else:
            frame = ctk.CTkFrame(win, fg_color="transparent")
            frame.pack(padx=20, pady=5, fill="both", expand=True)

            hdr = ctk.CTkFrame(frame, fg_color="transparent")
            hdr.pack(fill="x", pady=(5, 0))
            for txt, w in [("排名", 50), ("分数", 70), ("记录时间", 220)]:
                ctk.CTkLabel(hdr, text=txt, font=("Microsoft YaHei", 13, "bold"),
                             width=w).pack(side="left", padx=5)

            medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
            for i, entry in enumerate(self.top_scores):
                row = ctk.CTkFrame(frame, fg_color="transparent")
                row.pack(fill="x", pady=3)
                ctk.CTkLabel(row, text=medals[i] if i < 5 else str(i + 1),
                             font=("Arial", 16), width=50).pack(side="left", padx=5)
                ctk.CTkLabel(row, text=str(entry["score"]),
                             font=("Arial", 18, "bold"), width=70,
                             text_color="#F1C40F").pack(side="left", padx=5)
                ctk.CTkLabel(row, text=entry["time"],
                             font=("Microsoft YaHei", 13), width=220).pack(side="left", padx=5)

        ctk.CTkButton(win, text="关闭", command=win.destroy, width=100).pack(pady=15)

    # ═══════════════════════════════════════════════════
    #  设置
    # ═══════════════════════════════════════════════════

    def _open_settings(self):
        if self._settings_win and self._settings_win.winfo_exists():
            self._settings_win.lift()
            return
        self._settings_win = ctk.CTkToplevel(self)
        self._settings_win.title("⚙️ 设置")
        self._settings_win.geometry("360x320")
        self._settings_win.resizable(False, False)
        self._settings_win.transient(self)
        self._settings_win.grab_set()
        self._settings_win.protocol("WM_DELETE_WINDOW", self._close_settings)

        ctk.CTkLabel(self._settings_win, text="🎨 主题颜色",
                     font=("Microsoft YaHei", 16, "bold")).pack(pady=(20, 5))
        theme_menu = ctk.CTkOptionMenu(
            self._settings_win, values=list(THEME_COLORS.keys()),
            command=self.change_theme, width=200)
        theme_menu.pack(pady=(0, 10))
        ctk.CTkFrame(self._settings_win, height=1).pack(fill="x", padx=30, pady=5)

        self._st_var = ctk.BooleanVar(value=self.show_table_during_game)
        ctk.CTkSwitch(self._settings_win,
            text="📖  答题时显示口诀表入口",
            variable=self._st_var,
            command=self._on_st_setting,
            font=("Microsoft YaHei", 14)).pack(pady=10)
        ctk.CTkLabel(self._settings_win,
            text="开启后答题界面左上角出现 📖 按钮\n点击可查看口诀表（计时不停止）",
            font=("Microsoft YaHei", 11), text_color="#95A5A6").pack()
        ctk.CTkFrame(self._settings_win, height=1).pack(fill="x", padx=30, pady=5)

        self._ap_var = ctk.BooleanVar(value=self.auto_play)
        ctk.CTkSwitch(self._settings_win,
            text="🤖  自动答题（Ctrl+A）",
            variable=self._ap_var,
            command=self._on_ap_setting,
            font=("Microsoft YaHei", 14)).pack(pady=10)
        ctk.CTkFrame(self._settings_win, height=1).pack(fill="x", padx=30, pady=5)

        # ⏱ 倒计时时间设置
        ctk.CTkLabel(self._settings_win, text="⏱  倒计时时间（秒）",
                     font=("Microsoft YaHei", 14, "bold")).pack(pady=(10, 5))
        time_frame = ctk.CTkFrame(self._settings_win, fg_color="transparent")
        time_frame.pack()
        self._ct_var = ctk.StringVar(value=str(self.countdown_time))
        ctk.CTkEntry(
            time_frame, textvariable=self._ct_var,
            font=("Arial", 18), width=120, justify="center",
        ).pack(side="left", padx=(0, 10))
        ctk.CTkButton(
            time_frame, text="确认", font=("Microsoft YaHei", 14),
            command=self._save_countdown_time, width=60,
        ).pack(side="left")

    def _close_settings(self):
        self._settings_win.destroy()
        self._settings_win = None

    def _on_st_setting(self):
        self.show_table_during_game = self._st_var.get()
        if self.in_game:
            self._update_table_btn()

    def _on_ap_setting(self):
        val = self._ap_var.get()
        if val != self.auto_play:
            self.toggle_auto_play()

    def _save_countdown_time(self):
        """保存用户自定义倒计时时间"""
        val = self._ct_var.get().strip()
        if val.isdigit() and int(val) >= 10:
            self.countdown_time = int(val)
            self._save_data()
            self._show_tip("✅  设置已保存", f"倒计时改为 {self.countdown_time} 秒\n下一局生效")
        else:
            self._show_tip("⚠️  输入无效", "请输一个 ≥10 的整数")

    # ═══════════════════════════════════════════════════
    #  提示弹窗
    # ═══════════════════════════════════════════════════

    def _show_tip(self, title, msg=""):
        tip = ctk.CTkToplevel(self)
        tip.title("")
        tip.geometry("300x140")
        tip.resizable(False, False)
        tip.transient(self)
        tip.grab_set()
        tip.attributes("-topmost", True)
        tip.update_idletasks()
        sw, sh = tip.winfo_screenwidth(), tip.winfo_screenheight()
        tip.geometry(f"+{(sw-300)//2}+{(sh-140)//2}")

        ctk.CTkLabel(tip, text=title, font=("Microsoft YaHei", 18, "bold")).pack(pady=(20, 5))
        if msg:
            ctk.CTkLabel(tip, text=msg, font=("Microsoft YaHei", 13)).pack()
        ctk.CTkButton(tip, text="好的", command=tip.destroy, width=100).pack(pady=12)

    # ═══════════════════════════════════════════════════
    #  辅助
    # ═══════════════════════════════════════════════════

    def _update_hearts(self):
        hearts = max(0, self.score)
        empty = 5 - hearts
        self.hearts_label.configure(
            text="❤️" * hearts + "🖤" * empty + f"   {self.score} 分")

    def change_theme(self, choice):
        cfg = THEME_COLORS[choice]
        ctk.set_appearance_mode(cfg["mode"])
        accent = cfg["accent"]
        for w in [self.submit_btn, self.next_btn, self.lose_revive_btn,
                  self.lose_watch_btn]:
            try:
                w.configure(fg_color=accent)
            except:
                pass

    def _on_closing(self):
        """关闭窗口时清理资源"""
        # 取消所有定时器
        for tid in [self.timer_id, self.lose_timer_id, self.auto_play_id]:
            if tid:
                try:
                    self.after_cancel(tid)
                except:
                    pass
        self.destroy()


if __name__ == "__main__":
    app = GameApp()
    app.mainloop()
