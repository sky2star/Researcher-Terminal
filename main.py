# -*- coding: utf-8 -*-
"""
科研工作者终端 - Researcher Terminal
主程序入口与UI界面

支持两种工作模式：
- 规划模式：明确目标和方法，进行任务拆解
- 探索模式：明确目标但不知方法，记录探索过程

Copyright 2026 Researcher Terminal

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import customtkinter as ctk
from tkinter import messagebox, filedialog
from datetime import datetime
from typing import Optional, Callable

from models import Task, SubTask, ExplorationNote, TaskStatus, TaskMode, TaskKnowledge
from database import Database
import tkinter as tk


# ==================== 悬浮任务追踪窗口 ====================
class TaskTrackerWindow(ctk.CTkToplevel):
    """悬浮任务追踪窗口 - 类似游戏任务提醒"""

    def __init__(self, parent, db: 'Database'):
        super().__init__(parent)

        self.db = db
        self.parent = parent

        # 窗口配置
        self.title("📌 任务追踪")
        self.geometry("320x400+50+100")
        self.minsize(280, 200)
        self.attributes("-topmost", True)
        self.attributes("-alpha", 0.95)
        self.overrideredirect(False)

        self.configure(fg_color=ThemeConfig.BG_PRIMARY)

        self._create_ui()
        self._refresh_tracker()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_ui(self):
        """创建追踪窗口界面"""
        header = ctk.CTkFrame(self, fg_color=ThemeConfig.BG_SECONDARY, corner_radius=0, height=40)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_label = ctk.CTkLabel(
            header,
            text="📌 当前任务",
            font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(side="left", padx=12, pady=8)

        refresh_btn = ctk.CTkButton(
            header,
            text="🔄",
            width=30,
            height=26,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=ThemeConfig.BG_HOVER,
            command=self._refresh_tracker
        )
        refresh_btn.pack(side="right", padx=4)

        minimize_btn = ctk.CTkButton(
            header,
            text="—",
            width=30,
            height=26,
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=ThemeConfig.BG_HOVER,
            command=self._toggle_minimize
        )
        minimize_btn.pack(side="right", padx=4)

        self.content_frame = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=ThemeConfig.BG_TERTIARY,
            scrollbar_button_hover_color=ThemeConfig.BG_HOVER
        )
        self.content_frame.pack(fill="both", expand=True, padx=8, pady=8)

        self._is_minimized = False

    def _toggle_minimize(self):
        """切换最小化状态"""
        if self._is_minimized:
            self.content_frame.pack(fill="both", expand=True, padx=8, pady=8)
            self.geometry(f"320x400+{self.winfo_x()}+{self.winfo_y()}")
            self._is_minimized = False
        else:
            self.content_frame.pack_forget()
            self.geometry(f"320x45+{self.winfo_x()}+{self.winfo_y()}")
            self._is_minimized = True

    def _refresh_tracker(self):
        """刷新追踪内容"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        tasks = self.db.get_all_tasks()
        active_tasks = []
        for t in tasks:
            if t.status in [TaskStatus.IN_PROGRESS, TaskStatus.EXPLORING, TaskStatus.PENDING]:
                active_tasks.append(t)
            elif t.status == TaskStatus.COMPLETED:
                has_incomplete = any(st.status != TaskStatus.COMPLETED for st in t.subtasks)
                if has_incomplete:
                    t.status = TaskStatus.IN_PROGRESS
                    t.completed_at = None
                    self.db._save()
                    active_tasks.append(t)

        status_order = {TaskStatus.IN_PROGRESS: 0, TaskStatus.EXPLORING: 1, TaskStatus.PENDING: 2}
        active_tasks.sort(key=lambda t: status_order.get(t.status, 3))

        if not active_tasks:
            empty_label = ctk.CTkLabel(
                self.content_frame,
                text="✨ 暂无进行中的任务\n\n去主窗口创建一个吧！",
                font=ctk.CTkFont(family="Microsoft YaHei", size=13),
                text_color=ThemeConfig.TEXT_MUTED,
                justify="center"
            )
            empty_label.pack(pady=40)
            return

        for task in active_tasks[:5]:
            self._create_task_tracker_item(task)

    def _create_task_tracker_item(self, task: Task):
        """创建任务追踪项"""
        if task.mode == TaskMode.EXPLORING:
            accent_color = ThemeConfig.ACCENT_EXPLORING
            mode_icon = "🔍"
        else:
            accent_color = ThemeConfig.ACCENT_PLANNING
            mode_icon = "📊"

        card = ctk.CTkFrame(
            self.content_frame,
            fg_color=ThemeConfig.BG_SECONDARY,
            corner_radius=10,
            border_width=1,
            border_color=accent_color
        )
        card.pack(fill="x", pady=4)

        title_frame = ctk.CTkFrame(card, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(10, 6))

        mode_label = ctk.CTkLabel(
            title_frame,
            text=mode_icon,
            font=ctk.CTkFont(size=14)
        )
        mode_label.pack(side="left", padx=(0, 6))

        title_text = task.title[:20] + "..." if len(task.title) > 20 else task.title
        title_label = ctk.CTkLabel(
            title_frame,
            text=title_text,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(side="left", fill="x", expand=True)

        if task.mode == TaskMode.PLANNING:
            if not task.subtasks:
                hint_frame = ctk.CTkFrame(card, fg_color=ThemeConfig.BG_TERTIARY, corner_radius=6)
                hint_frame.pack(fill="x", padx=10, pady=(0, 10))

                hint_label = ctk.CTkLabel(
                    hint_frame,
                    text="💡 去主窗口添加子任务吧",
                    font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                    text_color=ThemeConfig.TEXT_MUTED
                )
                hint_label.pack(anchor="w", padx=8, pady=8)
            else:
                next_subtask = None
                for st in sorted(task.subtasks, key=lambda x: x.order):
                    if st.status != TaskStatus.COMPLETED:
                        next_subtask = st
                        break

                if next_subtask:
                    next_frame = ctk.CTkFrame(card, fg_color=ThemeConfig.BG_TERTIARY, corner_radius=6)
                    next_frame.pack(fill="x", padx=10, pady=(0, 6))

                    next_label = ctk.CTkLabel(
                        next_frame,
                        text="▶ 下一步:",
                        font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                        text_color=ThemeConfig.ACCENT_PLANNING
                    )
                    next_label.pack(anchor="w", padx=8, pady=(6, 2))

                    step_text = next_subtask.title[:25] + "..." if len(next_subtask.title) > 25 else next_subtask.title
                    step_label = ctk.CTkLabel(
                        next_frame,
                        text=step_text,
                        font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                        text_color=ThemeConfig.TEXT_PRIMARY
                    )
                    step_label.pack(anchor="w", padx=8, pady=(0, 6))

                    complete_btn = ctk.CTkButton(
                        next_frame,
                        text="✓ 完成此步骤",
                        font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                        fg_color=ThemeConfig.ACCENT_SUCCESS,
                        hover_color="#2D9142",
                        height=26,
                        corner_radius=6,
                        command=lambda t=task, s=next_subtask: self._complete_step(t, s)
                    )
                    complete_btn.pack(anchor="w", padx=8, pady=(0, 8))
                else:
                    done_frame = ctk.CTkFrame(card, fg_color=ThemeConfig.BG_TERTIARY, corner_radius=6)
                    done_frame.pack(fill="x", padx=10, pady=(0, 6))

                    done_label = ctk.CTkLabel(
                        done_frame,
                        text="✅ 所有步骤已完成！",
                        font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                        text_color=ThemeConfig.ACCENT_SUCCESS
                    )
                    done_label.pack(anchor="w", padx=8, pady=8)

                progress = task.get_progress()
                progress_frame = ctk.CTkFrame(card, fg_color="transparent")
                progress_frame.pack(fill="x", padx=10, pady=(0, 10))

                progress_bar = ctk.CTkProgressBar(
                    progress_frame,
                    width=200,
                    height=6,
                    fg_color=ThemeConfig.BG_HOVER,
                    progress_color=ThemeConfig.ACCENT_SUCCESS
                )
                progress_bar.pack(side="left", fill="x", expand=True)
                progress_bar.set(progress)

                progress_text = ctk.CTkLabel(
                    progress_frame,
                    text=f"{int(progress * 100)}%",
                    font=ctk.CTkFont(family="Microsoft YaHei", size=10),
                    text_color=ThemeConfig.TEXT_MUTED
                )
                progress_text.pack(side="right", padx=(8, 0))

        elif task.mode == TaskMode.EXPLORING:
            explore_frame = ctk.CTkFrame(card, fg_color=ThemeConfig.BG_TERTIARY, corner_radius=6)
            explore_frame.pack(fill="x", padx=10, pady=(0, 10))

            explore_label = ctk.CTkLabel(
                explore_frame,
                text=f"🔍 探索中... ({len(task.exploration_notes)}条笔记)",
                font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                text_color=ThemeConfig.ACCENT_EXPLORING
            )
            explore_label.pack(anchor="w", padx=8, pady=6)

            if task.exploration_notes:
                latest_note = task.exploration_notes[-1]
                note_text = latest_note.content[:30] + "..." if len(latest_note.content) > 30 else latest_note.content
                note_label = ctk.CTkLabel(
                    explore_frame,
                    text=f"📝 {note_text}",
                    font=ctk.CTkFont(family="Microsoft YaHei", size=10),
                    text_color=ThemeConfig.TEXT_MUTED
                )
                note_label.pack(anchor="w", padx=8, pady=(0, 6))

    def _complete_step(self, task: Task, subtask: SubTask):
        """快速完成步骤"""
        self.db.complete_subtask(task.id, subtask.id)
        self._refresh_tracker()
        if hasattr(self.parent, '_refresh_task_list'):
            self.parent._refresh_task_list()
            if self.parent.selected_task and self.parent.selected_task.id == task.id:
                updated_task = self.db.get_task(task.id)
                if updated_task:
                    self.parent._show_task_detail(updated_task)

    def _on_close(self):
        """关闭窗口"""
        self.withdraw()
        if hasattr(self.parent, 'tracker_window_visible'):
            self.parent.tracker_window_visible = False


# ==================== 主题配置 ====================
class ThemeConfig:
    """主题配置"""
    # 深色学术风格配色
    BG_PRIMARY = "#0D1117"      # 主背景 - 深邃夜空
    BG_SECONDARY = "#161B22"    # 次级背景
    BG_TERTIARY = "#21262D"     # 卡片背景
    BG_HOVER = "#30363D"        # 悬停背景
    
    ACCENT_PLANNING = "#58A6FF"  # 规划模式 - 蓝色
    ACCENT_EXPLORING = "#F0883E" # 探索模式 - 琥珀色
    ACCENT_SUCCESS = "#3FB950"   # 成功/完成
    ACCENT_WARNING = "#D29922"   # 警告
    ACCENT_DANGER = "#F85149"    # 危险/删除
    
    TEXT_PRIMARY = "#E6EDF3"     # 主文字
    TEXT_SECONDARY = "#8B949E"   # 次级文字
    TEXT_MUTED = "#6E7681"       # 淡化文字
    
    BORDER_DEFAULT = "#30363D"   # 默认边框
    BORDER_ACCENT = "#388BFD"    # 高亮边框


# 设置CustomTkinter主题
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ResearchTerminal(ctk.CTk):
    """科研工作者终端主窗口"""
    
    def __init__(self):
        super().__init__()

        self.db = Database()
        self.selected_task: Optional[Task] = None
        self.batch_mode = False
        self.selected_note_ids: set[str] = set()
        self.tracker_window: Optional[TaskTrackerWindow] = None
        self.tracker_window_visible = False

        # 拖拽排序相关状态
        self._drag_data = {
            "dragging": False,
            "widget": None,
            "task": None,
            "subtask": None,
            "start_y": 0,
            "start_x": 0,
            "original_index": 0,
            "current_index": 0,
            "moved": False,
            "drag_threshold": 5,
            "card_positions": [],
            "subtask_positions": [],
            "animating": False,
            "is_subtask": False,
        }
        self._task_cards = []
        self._subtask_items = []
        self._note_items = []
        
        # 窗口配置
        self.title("🔬 科研工作者终端 - Researcher Terminal")
        self.geometry("1400x900")
        self.minsize(1200, 700)
        
        # 配置颜色
        self.configure(fg_color=ThemeConfig.BG_PRIMARY)
        
        # 创建主布局
        self._create_layout()
        self._refresh_task_list()
    
    def _create_layout(self):
        """创建主布局"""
        # 主容器
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 左侧边栏 - 任务列表
        self._create_sidebar()
        
        # 右侧主区域 - 任务详情
        self._create_main_area()
    
    def _create_sidebar(self):
        """创建左侧边栏"""
        self.sidebar = ctk.CTkFrame(
            self.main_container,
            fg_color=ThemeConfig.BG_SECONDARY,
            corner_radius=16,
            width=380
        )
        self.sidebar.pack(side="left", fill="y", padx=(0, 16))
        self.sidebar.pack_propagate(False)
        
        # 标题区域
        header = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(20, 16))
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left")

        title_label = ctk.CTkLabel(
            title_frame,
            text="📋 任务列表",
            font=ctk.CTkFont(family="Microsoft YaHei", size=22, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(side="left")

        self.tracker_btn = ctk.CTkButton(
            header,
            text="📌",
            width=36,
            height=36,
            font=ctk.CTkFont(size=16),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.ACCENT_PLANNING,
            corner_radius=8,
            command=self._toggle_tracker_window
        )
        self.tracker_btn.pack(side="right")

        tracker_tip = ctk.CTkLabel(
            header,
            text="追踪",
            font=ctk.CTkFont(family="Microsoft YaHei", size=10),
            text_color=ThemeConfig.TEXT_MUTED
        )
        tracker_tip.pack(side="right", padx=(0, 4))
        
        # 搜索框和模式切换
        search_container = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        search_container.pack(fill="x", padx=20, pady=(0, 12))
        
        self.search_mode_var = ctk.StringVar(value="task")
        
        # 搜索模式标签
        mode_label = ctk.CTkLabel(
            search_container,
            text="🔍 任务搜索",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.ACCENT_PLANNING
        )
        mode_label.pack(side="left", padx=(0, 8))
        self.search_mode_label = mode_label
        
        # 模式切换按钮
        def toggle_search_mode():
            if self.search_mode_var.get() == "task":
                self.search_mode_var.set("note")
                self.search_mode_label.configure(text="📝 笔记搜索", text_color=ThemeConfig.ACCENT_EXPLORING)
            else:
                self.search_mode_var.set("task")
                self.search_mode_label.configure(text="🔍 任务搜索", text_color=ThemeConfig.ACCENT_PLANNING)
            self.search_entry.delete(0, "end")
            self._on_search()
        
        toggle_btn = ctk.CTkButton(
            search_container,
            text="切换",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            width=50,
            height=30,
            corner_radius=8,
            command=toggle_search_mode
        )
        toggle_btn.pack(side="right")

        # 搜索框
        self.search_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.search_frame.pack(fill="x", padx=20, pady=(0, 12))

        # 搜索框（移除了模式选择按钮）
        self.search_var = tk.StringVar()
        self.search_var.trace("w", lambda *args: self._on_search())
        
        self.search_entry = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="🔍 搜索任务...",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            text_color=ThemeConfig.TEXT_PRIMARY,
            placeholder_text_color=ThemeConfig.TEXT_MUTED,
            height=40,
            corner_radius=10,
            textvariable=self.search_var
        )
        self.search_entry.pack(fill="x")
        
        # 任务筛选按钮组（仅在搜索任务时显示）
        self.filter_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.filter_frame.pack(fill="x", padx=20, pady=(0, 12))
        
        self.filter_var = ctk.StringVar(value="all")
        
        task_filters = [
            ("全部", "all"),
            ("规划中", "planning"),
            ("探索中", "exploring"),
            ("已完成", "completed")
        ]
        
        self.task_filter_buttons = []
        for text, value in task_filters:
            btn = ctk.CTkRadioButton(
                self.filter_frame,
                text=text,
                variable=self.filter_var,
                value=value,
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                text_color=ThemeConfig.TEXT_SECONDARY,
                fg_color=ThemeConfig.ACCENT_PLANNING,
                hover_color=ThemeConfig.BG_HOVER,
                command=self._refresh_task_list
            )
            btn.pack(side="left", padx=(0, 12))
            self.task_filter_buttons.append(btn)
        
        # 任务排序模式（先于排序控件）
        self.task_sort_mode_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.task_sort_mode_frame.pack(fill="x", padx=20, pady=(0, 12))

        mode_label = ctk.CTkLabel(
            self.task_sort_mode_frame,
            text="模式:",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        mode_label.pack(side="left", padx=(0, 8))

        self._task_sort_mode_var = ctk.StringVar(value="auto")
        auto_btn = ctk.CTkRadioButton(
            self.task_sort_mode_frame,
            text="自动排序",
            variable=self._task_sort_mode_var,
            value="auto",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_SECONDARY,
            fg_color=ThemeConfig.ACCENT_PLANNING,
            command=self._on_task_sort_mode_change
        )
        auto_btn.pack(side="left", padx=(0, 12))

        manual_btn = ctk.CTkRadioButton(
            self.task_sort_mode_frame,
            text="手动排序",
            variable=self._task_sort_mode_var,
            value="manual",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_SECONDARY,
            fg_color=ThemeConfig.ACCENT_PLANNING,
            command=self._on_task_sort_mode_change
        )
        manual_btn.pack(side="left")

        self.task_sort_manual_hint = ctk.CTkLabel(
            self.task_sort_mode_frame,
            text="(拖拽排序)",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_MUTED
        )

        # 任务排序选择器
        self.task_sort_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.task_sort_frame.pack(fill="x", padx=20, pady=(0, 12))
        
        sort_label = ctk.CTkLabel(
            self.task_sort_frame,
            text="排序:",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        sort_label.pack(side="left", padx=(0, 8))
        
        # 初始化任务排序变量
        self._task_sort_field_var = ctk.StringVar(value="updated_at")
        self._task_sort_order_var = ctk.StringVar(value="desc")
        self._task_sort_field_buttons = []
        
        # 排序字段选择
        task_sort_field_options = [
            ("⏱️ 创建时间", "created_at"),
            ("✏️ 修改时间", "updated_at")
        ]
        
        for text, value in task_sort_field_options:
            radio = ctk.CTkRadioButton(
                self.task_sort_frame,
                text=text,
                variable=self._task_sort_field_var,
                value=value,
                font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                text_color=ThemeConfig.TEXT_SECONDARY,
                fg_color=ThemeConfig.ACCENT_PLANNING,
                command=self._refresh_task_list
            )
            radio.pack(side="left", padx=(0, 12))
            self._task_sort_field_buttons.append(radio)
        
        # 排序方向切换按钮
        self.task_sort_order_btn = ctk.CTkButton(
            self.task_sort_frame,
            text="🔽 降序",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.ACCENT_PLANNING,
            text_color=ThemeConfig.TEXT_SECONDARY,
            width=80,
            height=28,
            corner_radius=6,
            command=self._toggle_task_sort_order
        )
        self.task_sort_order_btn.pack(side="left", padx=(0, 0))


        
        # 笔记筛选按钮组（仅在搜索笔记时显示）
        self.note_filter_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        self.note_filter_frame.pack(fill="x", padx=20, pady=(0, 12))
        
        self.note_filter_var = ctk.StringVar(value="all_notes")
        
        note_filters = [
            ("全部笔记", "all_notes"),
            ("突破性发现", "breakthrough"),
            ("包含洞察", "with_insight")
        ]
        
        self.note_filter_buttons = []
        for text, value in note_filters:
            btn = ctk.CTkRadioButton(
                self.note_filter_frame,
                text=text,
                variable=self.note_filter_var,
                value=value,
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                text_color=ThemeConfig.TEXT_SECONDARY,
                fg_color=ThemeConfig.ACCENT_EXPLORING,
                hover_color=ThemeConfig.BG_HOVER,
                command=self._on_search
            )
            btn.pack(side="left", padx=(0, 12))
            self.note_filter_buttons.append(btn)
        
        # 初始化隐藏笔记筛选框
        self.note_filter_frame.pack_forget()
        
        # 新建任务按钮
        self.new_task_btn = ctk.CTkButton(
            self.sidebar,
            text="➕ 新建任务",
            font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"),
            fg_color=ThemeConfig.ACCENT_PLANNING,
            hover_color="#4A90D9",
            height=44,
            corner_radius=10,
            command=self._show_new_task_dialog
        )
        self.new_task_btn.pack(fill="x", padx=20, pady=(0, 16))
        
        # 任务列表滚动区域
        self.task_list_frame = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            scrollbar_button_color=ThemeConfig.BG_TERTIARY,
            scrollbar_button_hover_color=ThemeConfig.BG_HOVER
        )
        self.task_list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 16))
        
        # 初始化搜索模式为任务搜索，显示任务筛选框
        self.search_mode_var.set("task")
        self.filter_frame.pack(fill="x", padx=20, pady=(0, 12))
        self._on_task_sort_mode_change()

    def _is_manual_sort_mode(self) -> bool:
        return getattr(self, "_task_sort_mode_var", None) is not None and self._task_sort_mode_var.get() == "manual"

    def _on_task_sort_mode_change(self):
        is_manual = self._is_manual_sort_mode()
        if is_manual:
            self.task_sort_frame.pack_forget()
            if hasattr(self, "task_sort_manual_hint"):
                self.task_sort_manual_hint.pack(side="left", padx=(8, 0))
        else:
            if not self.task_sort_frame.winfo_manager():
                self.task_sort_frame.pack(fill="x", padx=20, pady=(0, 12), after=self.task_sort_mode_frame)
            if hasattr(self, "task_sort_manual_hint"):
                self.task_sort_manual_hint.pack_forget()
        self._refresh_task_list()
        if self.selected_task:
            updated_task = self.db.get_task(self.selected_task.id)
            if updated_task:
                self._show_task_detail(updated_task)

    def _set_sort_controls_enabled(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        for btn in getattr(self, "_task_sort_field_buttons", []):
            btn.configure(state=state)
        if hasattr(self, "task_sort_order_btn"):
            self.task_sort_order_btn.configure(state=state)

    def _is_note_manual_sort_mode(self) -> bool:
        return getattr(self, "_note_sort_mode_var", None) is not None and self._note_sort_mode_var.get() == "manual"

    def _on_note_sort_mode_change(self):
        if self.selected_task:
            updated_task = self.db.get_task(self.selected_task.id)
            if updated_task:
                self._show_task_detail(updated_task)

    def _set_note_sort_mode(self, mode: str):
        if hasattr(self, "_note_sort_mode_var"):
            self._note_sort_mode_var.set(mode)
        self._on_note_sort_mode_change()
    
    def _create_main_area(self):
        """创建右侧主区域"""
        self.main_area = ctk.CTkFrame(
            self.main_container,
            fg_color=ThemeConfig.BG_SECONDARY,
            corner_radius=16
        )
        self.main_area.pack(side="right", fill="both", expand=True)
        
        # 初始状态显示欢迎界面
        self._show_welcome_screen()
    
    def _show_welcome_screen(self):
        """显示欢迎界面"""
        # 清空主区域
        for widget in self.main_area.winfo_children():
            widget.destroy()
        
        welcome_frame = ctk.CTkFrame(self.main_area, fg_color="transparent")
        welcome_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # 图标
        icon_label = ctk.CTkLabel(
            welcome_frame,
            text="🔬",
            font=ctk.CTkFont(size=80)
        )
        icon_label.pack(pady=(0, 20))
        
        # 标题
        title = ctk.CTkLabel(
            welcome_frame,
            text="科研工作者终端",
            font=ctk.CTkFont(family="Microsoft YaHei", size=32, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title.pack(pady=(0, 12))
        
        # 副标题
        subtitle = ctk.CTkLabel(
            welcome_frame,
            text="规划你的研究，探索未知领域",
            font=ctk.CTkFont(family="Microsoft YaHei", size=16),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        subtitle.pack(pady=(0, 40))
        
        # 模式说明
        modes_frame = ctk.CTkFrame(welcome_frame, fg_color="transparent")
        modes_frame.pack()
        
        # 规划模式卡片
        planning_card = self._create_mode_card(
            modes_frame,
            "📊 规划模式",
            "明确目标 → 拆解任务 → 逐步完成",
            ThemeConfig.ACCENT_PLANNING,
            "适用于：知道做什么，也知道怎么做的任务"
        )
        planning_card.pack(side="left", padx=12)
        
        # 探索模式卡片
        exploring_card = self._create_mode_card(
            modes_frame,
            "🔍 探索模式",
            "记录尝试 → 收集洞察 → 获得方法",
            ThemeConfig.ACCENT_EXPLORING,
            "适用于：知道做什么，但不知道怎么做的任务"
        )
        exploring_card.pack(side="left", padx=12)
        
        # 提示
        tip = ctk.CTkLabel(
            welcome_frame,
            text="👈 点击左侧 \"新建任务\" 开始你的科研之旅",
            font=ctk.CTkFont(family="Microsoft YaHei", size=14),
            text_color=ThemeConfig.TEXT_MUTED
        )
        tip.pack(pady=(40, 0))
    
    def _create_mode_card(self, parent, title: str, description: str, color: str, tip: str) -> ctk.CTkFrame:
        """创建模式说明卡片"""
        card = ctk.CTkFrame(
            parent,
            fg_color=ThemeConfig.BG_TERTIARY,
            corner_radius=12,
            width=280,
            height=180
        )
        card.pack_propagate(False)
        
        # 标题
        title_label = ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=color
        )
        title_label.pack(pady=(24, 12))
        
        # 描述
        desc_label = ctk.CTkLabel(
            card,
            text=description,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        desc_label.pack(pady=(0, 12))
        
        # 提示
        tip_label = ctk.CTkLabel(
            card,
            text=tip,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_MUTED,
            wraplength=240
        )
        tip_label.pack(pady=(0, 16))
        
        return card
    
    def _create_task_card(self, task: Task, index: int) -> ctk.CTkFrame:
        """创建任务卡片"""
        # 根据模式选择颜色
        accent_color = ThemeConfig.ACCENT_EXPLORING if task.mode == TaskMode.EXPLORING else ThemeConfig.ACCENT_PLANNING
        
        # 状态颜色
        status_colors = {
            TaskStatus.PENDING: ThemeConfig.TEXT_MUTED,
            TaskStatus.IN_PROGRESS: ThemeConfig.ACCENT_PLANNING,
            TaskStatus.EXPLORING: ThemeConfig.ACCENT_EXPLORING,
            TaskStatus.COMPLETED: ThemeConfig.ACCENT_SUCCESS,
            TaskStatus.PAUSED: ThemeConfig.ACCENT_WARNING
        }
        
        drag_cursor = "hand2" if self._is_manual_sort_mode() else "arrow"
        card = ctk.CTkFrame(
            self.task_list_frame,
            fg_color=ThemeConfig.BG_TERTIARY,
            corner_radius=12,
            border_width=2,
            border_color=accent_color if self.selected_task and self.selected_task.id == task.id else ThemeConfig.BORDER_DEFAULT,
            cursor=drag_cursor
        )
        card.pack(fill="x", pady=6, padx=4)
        card._task = task
        card._index = index
        card._accent_color = accent_color
        card._is_selected = self.selected_task and self.selected_task.id == task.id
        self._task_cards.append(card)

        if self._is_manual_sort_mode():
            card.bind("<Button-1>", lambda e, c=card, t=task, i=index: self._on_task_drag_start(e, c, t, i))
            card.bind("<B1-Motion>", lambda e, c=card: self._on_task_drag_motion(e, c))
            card.bind("<ButtonRelease-1>", lambda e, t=task: self._on_task_drag_end(e, t))
        else:
            card.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        # 内容区域
        content = ctk.CTkFrame(card, fg_color="transparent", cursor=drag_cursor)
        content.pack(fill="x", padx=16, pady=12)
        if self._is_manual_sort_mode():
            content.bind("<Button-1>", lambda e, c=card, t=task, i=index: self._on_task_drag_start(e, c, t, i))
            content.bind("<B1-Motion>", lambda e, c=card: self._on_task_drag_motion(e, c))
            content.bind("<ButtonRelease-1>", lambda e, t=task: self._on_task_drag_end(e, t))
        else:
            content.bind("<Button-1>", lambda e, t=task: self._select_task(t))

        def bind_drag_events(widget):
            widget.bind("<Button-1>", lambda e, c=card, t=task, i=index: self._on_task_drag_start(e, c, t, i))
            widget.bind("<B1-Motion>", lambda e, c=card: self._on_task_drag_motion(e, c))
            widget.bind("<ButtonRelease-1>", lambda e, t=task: self._on_task_drag_end(e, t))
        
        # 第一行：标题和模式标签
        row1 = ctk.CTkFrame(content, fg_color="transparent", cursor=drag_cursor)
        row1.pack(fill="x")
        if self._is_manual_sort_mode():
            bind_drag_events(row1)
        else:
            row1.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        # 模式标签
        mode_icon = "🔍" if task.mode == TaskMode.EXPLORING else "📊"
        mode_label = ctk.CTkLabel(
            row1,
            text=mode_icon,
            font=ctk.CTkFont(size=14),
            cursor=drag_cursor
        )
        mode_label.pack(side="left", padx=(0, 8))
        if self._is_manual_sort_mode():
            bind_drag_events(mode_label)
        else:
            mode_label.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        # 标题
        title_label = ctk.CTkLabel(
            row1,
            text=task.title[:25] + ("..." if len(task.title) > 25 else ""),
            font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY,
            anchor="w",
            cursor=drag_cursor
        )
        title_label.pack(side="left", fill="x", expand=True)
        if self._is_manual_sort_mode():
            bind_drag_events(title_label)
        else:
            title_label.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        # 第二行：状态和进度
        row2 = ctk.CTkFrame(content, fg_color="transparent", cursor=drag_cursor)
        row2.pack(fill="x", pady=(8, 0))
        if self._is_manual_sort_mode():
            bind_drag_events(row2)
        else:
            row2.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        # 状态
        status_label = ctk.CTkLabel(
            row2,
            text=task.status.value,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=status_colors.get(task.status, ThemeConfig.TEXT_SECONDARY),
            cursor=drag_cursor
        )
        status_label.pack(side="left")
        if self._is_manual_sort_mode():
            bind_drag_events(status_label)
        else:
            status_label.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        # 进度条（规划模式显示）
        if task.mode == TaskMode.PLANNING and task.subtasks:
            progress = task.get_progress()
            progress_bar = ctk.CTkProgressBar(
                row2,
                width=80,
                height=6,
                fg_color=ThemeConfig.BG_HOVER,
                progress_color=ThemeConfig.ACCENT_SUCCESS
            )
            progress_bar.pack(side="right")
            progress_bar.set(progress)
        
        # 探索模式显示笔记数量
        if task.mode == TaskMode.EXPLORING and task.exploration_notes:
            notes_label = ctk.CTkLabel(
                row2,
                text=f"📝 {len(task.exploration_notes)}条笔记",
                font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                text_color=ThemeConfig.TEXT_MUTED,
                cursor=drag_cursor
            )
            notes_label.pack(side="right")
            if self._is_manual_sort_mode():
                bind_drag_events(notes_label)
            else:
                notes_label.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        return card
    
    def _refresh_task_list(self):
        """刷新任务列表"""
        # 清空现有列表
        self._task_cards = []
        for widget in self.task_list_frame.winfo_children():
            widget.destroy()
        
        # 获取任务
        tasks = self.db.get_all_tasks()
        
        # 应用筛选
        filter_value = self.filter_var.get()
        if filter_value == "planning":
            tasks = [t for t in tasks if t.mode == TaskMode.PLANNING and t.status != TaskStatus.COMPLETED]
        elif filter_value == "exploring":
            tasks = [t for t in tasks if t.mode == TaskMode.EXPLORING]
        elif filter_value == "completed":
            tasks = [t for t in tasks if t.status == TaskStatus.COMPLETED]
        
        # 应用搜索（仅任务模式）
        search_text = self.search_entry.get().strip().lower()
        if getattr(self, "search_mode_var", None) and self.search_mode_var.get() == "task":
            if search_text:
                tasks = [t for t in tasks if search_text in t.title.lower() or search_text in t.description.lower()]
        
        # 按排序设置排序
        if self._is_manual_sort_mode():
            tasks.sort(key=lambda t: t.order)
        else:
            sort_field = self._task_sort_field_var.get()
            sort_order = self._task_sort_order_var.get()
            is_reverse = (sort_order == "desc")

            if sort_field == "created_at":
                tasks.sort(key=lambda t: t.created_at, reverse=is_reverse)
            else:
                tasks.sort(key=lambda t: t.updated_at, reverse=is_reverse)
        
        # 创建任务卡片
        if tasks:
            for index, task in enumerate(tasks):
                self._create_task_card(task, index)
        else:
            # 空状态
            empty_label = ctk.CTkLabel(
                self.task_list_frame,
                text="暂无任务\n点击上方按钮创建",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                text_color=ThemeConfig.TEXT_MUTED,
                justify="center"
            )
            empty_label.pack(pady=40)
    
    def _on_search(self):
        """搜索事件"""
        search_text = self.search_var.get().strip()
        
        # 根据搜索模式显示/隐藏筛选器
        if self.search_mode_var.get() == "note":
            self.filter_frame.pack_forget()
            # 使用after参数确保笔记筛选框显示在搜索框下方
            self.note_filter_frame.pack(fill="x", padx=20, pady=(0, 12), after=self.search_frame)
            self.search_entry.configure(placeholder_text="🔍 搜索探索笔记...")
            
            if search_text:
                # 应用笔记筛选
                results = self.db.search_exploration_notes_global(search_text)
                note_filter = self.note_filter_var.get()
                
                if note_filter == "breakthrough":
                    results = [r for r in results if r.note.is_breakthrough]
                elif note_filter == "with_insight":
                    results = [r for r in results if r.note.insight]
                
                self._show_note_search_results(results)
            else:
                self._refresh_task_list()
                if self.selected_task:
                    self._show_task_detail(self.selected_task)
                else:
                    self._show_welcome_screen()
            return
        
        # 任务模式
        self.note_filter_frame.pack_forget()
        # 使用after参数确保任务筛选框显示在搜索框下方
        self.filter_frame.pack(fill="x", padx=20, pady=(0, 12), after=self.search_frame)
        self.search_entry.configure(placeholder_text="🔍 搜索任务...")
        self._refresh_task_list()

    def _show_note_search_results(self, results):
        """显示探索笔记搜索结果"""
        for widget in self.main_area.winfo_children():
            widget.destroy()

        container = ctk.CTkScrollableFrame(
            self.main_area,
            fg_color="transparent",
            scrollbar_button_color=ThemeConfig.BG_TERTIARY,
            scrollbar_button_hover_color=ThemeConfig.BG_HOVER
        )
        container.pack(fill="both", expand=True, padx=24, pady=24)

        if not results:
            empty = ctk.CTkLabel(
                container,
                text="无匹配探索笔记",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                text_color=ThemeConfig.TEXT_MUTED
            )
            empty.pack(pady=30)
            return

        results = sorted(results, key=lambda r: r.note.created_at, reverse=True)

        def bind_click(widget, task_id, note_id):
            widget.bind("<Button-1>", lambda e: self._open_note_result(task_id, note_id))

        for res in results:
            item = ctk.CTkFrame(container, fg_color=ThemeConfig.BG_TERTIARY, corner_radius=10)
            item.pack(fill="x", pady=6)

            content = ctk.CTkFrame(item, fg_color="transparent")
            content.pack(fill="x", padx=16, pady=12)

            header = ctk.CTkFrame(content, fg_color="transparent")
            header.pack(fill="x")

            title_label = ctk.CTkLabel(
                header,
                text=f"📝 {res.task_title}",
                font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
                text_color=ThemeConfig.TEXT_PRIMARY
            )
            title_label.pack(side="left")

            time_str = res.note.created_at.strftime("%m-%d %H:%M")
            time_label = ctk.CTkLabel(
                header,
                text=time_str,
                font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                text_color=ThemeConfig.TEXT_MUTED
            )
            time_label.pack(side="right")

            snippet = res.note.content.strip().replace("\n", " ")
            if len(snippet) > 120:
                snippet = snippet[:120] + "..."
            snippet_label = ctk.CTkLabel(
                content,
                text=snippet,
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                text_color=ThemeConfig.TEXT_SECONDARY,
                justify="left",
                wraplength=680
            )
            snippet_label.pack(fill="x", pady=(8, 0))

            if res.is_history:
                history_label = ctk.CTkLabel(
                    content,
                    text="📖 历史",
                    font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                    text_color=ThemeConfig.TEXT_MUTED
                )
                history_label.pack(anchor="w", pady=(6, 0))

            for w in (item, content, header, title_label, time_label, snippet_label):
                bind_click(w, res.task_id, res.note.id)

    def _open_note_result(self, task_id: str, note_id: str):
        task = self.db.get_task(task_id)
        if task:
            self._select_task(task, highlight_note_id=note_id)
    
    def _select_task(self, task: Task, highlight_note_id: Optional[str] = None):
        """选择任务"""
        self.selected_task = task
        self.batch_mode = False
        self.selected_note_ids = set()
        self._refresh_task_list()  # 刷新高亮状态
        self._show_task_detail(task, highlight_note_id=highlight_note_id)
    
    def _show_task_detail(self, task: Task, highlight_note_id: Optional[str] = None):
        """显示任务详情"""
        # 清空主区域
        for widget in self.main_area.winfo_children():
            widget.destroy()
        
        # 滚动容器
        scroll_container = ctk.CTkScrollableFrame(
            self.main_area,
            fg_color="transparent",
            scrollbar_button_color=ThemeConfig.BG_TERTIARY,
            scrollbar_button_hover_color=ThemeConfig.BG_HOVER
        )
        scroll_container.pack(fill="both", expand=True, padx=24, pady=24)
        
        # 头部区域
        header = ctk.CTkFrame(scroll_container, fg_color="transparent")
        header.pack(fill="x", pady=(0, 20))
        
        # 模式标签
        mode_color = ThemeConfig.ACCENT_EXPLORING if task.mode == TaskMode.EXPLORING else ThemeConfig.ACCENT_PLANNING
        mode_text = "🔍 探索模式" if task.mode == TaskMode.EXPLORING else "📊 规划模式"
        
        mode_badge = ctk.CTkLabel(
            header,
            text=mode_text,
            font=ctk.CTkFont(family="Microsoft YaHei", size=12, weight="bold"),
            text_color=mode_color,
            fg_color=ThemeConfig.BG_TERTIARY,
            corner_radius=6,
            padx=12,
            pady=4
        )
        mode_badge.pack(side="left")
        
        # 知识状态
        knowledge_label = ctk.CTkLabel(
            header,
            text=task.knowledge.value,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_MUTED
        )
        knowledge_label.pack(side="left", padx=(12, 0))
        
        # 操作按钮
        actions_frame = ctk.CTkFrame(header, fg_color="transparent")
        actions_frame.pack(side="right")
        
        if task.status != TaskStatus.COMPLETED:
            # 未完成任务显示切换模式按钮
            switch_text = "切换到规划模式" if task.mode == TaskMode.EXPLORING else "切换到探索模式"
            switch_btn = ctk.CTkButton(
                actions_frame,
                text=switch_text,
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                fg_color=ThemeConfig.BG_TERTIARY,
                hover_color=ThemeConfig.BG_HOVER,
                text_color=ThemeConfig.TEXT_SECONDARY,
                height=32,
                corner_radius=8,
                command=lambda: self._toggle_task_mode(task)
            )
            switch_btn.pack(side="left", padx=(0, 8))
        
        # 删除按钮
        delete_btn = ctk.CTkButton(
            actions_frame,
            text="🗑️",
            font=ctk.CTkFont(size=14),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.ACCENT_DANGER,
            width=40,
            height=32,
            corner_radius=8,
            command=lambda: self._delete_task(task)
        )
        delete_btn.pack(side="left")
        
        # 标题
        title_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        title_frame.pack(fill="x", pady=(0, 8))
        
        title_label = ctk.CTkLabel(
            title_frame,
            text=task.title,
            font=ctk.CTkFont(family="Microsoft YaHei", size=26, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY,
            anchor="w",
            wraplength=700
        )
        title_label.pack(side="left", fill="x", expand=True)
        
        # 编辑标题按钮
        edit_menu_btn = ctk.CTkButton(
            title_frame,
            text="📝",
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            hover_color=ThemeConfig.BG_HOVER,
            width=32,
            height=32,
            command=lambda: self._edit_task_dialog(task)
        )
        edit_menu_btn.pack(side="right")
        
        # 描述
        desc_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        desc_frame.pack(fill="x", pady=(0, 20))

        desc_text = task.description if task.description else "（无描述）"
        desc_color = ThemeConfig.TEXT_SECONDARY if task.description else ThemeConfig.TEXT_MUTED

        desc_label = ctk.CTkLabel(
            desc_frame,
            text=desc_text,
            font=ctk.CTkFont(family="Microsoft YaHei", size=14),
            text_color=desc_color,
            anchor="w",
            justify="left",
            wraplength=700
        )
        desc_label.pack(side="left", fill="x", expand=True)

        
        # 分隔线
        separator = ctk.CTkFrame(scroll_container, fg_color=ThemeConfig.BORDER_DEFAULT, height=1)
        separator.pack(fill="x", pady=(0, 20))
        
        # 根据模式显示不同内容
        if task.mode == TaskMode.PLANNING:
            self._show_planning_content(scroll_container, task, highlight_note_id=highlight_note_id)
        else:
            self._show_exploring_content(scroll_container, task, highlight_note_id=highlight_note_id)
    
    def _show_planning_content(self, parent, task: Task, highlight_note_id: Optional[str] = None):
        """显示规划模式内容"""
        # 子任务区域
        subtask_header = ctk.CTkFrame(parent, fg_color="transparent")
        subtask_header.pack(fill="x", pady=(0, 16))
        
        subtask_title = ctk.CTkLabel(
            subtask_header,
            text="📋 子任务拆解",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        subtask_title.pack(side="left")

        subtask_drag_hint = ctk.CTkLabel(
            subtask_header,
            text="(拖拽排序)",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_MUTED
        )
        subtask_drag_hint.pack(side="left", padx=(8, 0))

        # 添加子任务按钮
        add_subtask_btn = ctk.CTkButton(
            subtask_header,
            text="➕ 添加子任务",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            fg_color=ThemeConfig.ACCENT_PLANNING,
            hover_color="#4A90D9",
            height=32,
            corner_radius=8,
            command=lambda: self._add_subtask_dialog(task)
        )
        add_subtask_btn.pack(side="right")

        next_subtask = None
        if task.subtasks:
            for st in sorted(task.subtasks, key=lambda x: x.order):
                if st.status != TaskStatus.COMPLETED:
                    next_subtask = st
                    break
        if next_subtask:
            quick_complete_btn = ctk.CTkButton(
                subtask_header,
                text="✓ 完成此步骤",
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                fg_color=ThemeConfig.ACCENT_SUCCESS,
                hover_color="#2D9142",
                height=32,
                corner_radius=8,
                command=lambda: self._quick_complete_subtask(task, next_subtask)
            )
            quick_complete_btn.pack(side="right", padx=(0, 8))
        
        # 进度信息
        if task.subtasks:
            completed = sum(1 for st in task.subtasks if st.status == TaskStatus.COMPLETED)
            progress_text = f"已完成 {completed}/{len(task.subtasks)}"
            progress_label = ctk.CTkLabel(
                subtask_header,
                text=progress_text,
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                text_color=ThemeConfig.TEXT_MUTED
            )
            progress_label.pack(side="right", padx=(0, 16))
        
        # 子任务列表
        self._subtask_items = []
        if task.subtasks:
            for index, subtask in enumerate(sorted(task.subtasks, key=lambda x: x.order)):
                self._create_subtask_item(parent, task, subtask, index)
        else:
            empty_label = ctk.CTkLabel(
                parent,
                text="暂无子任务，点击上方按钮添加",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                text_color=ThemeConfig.TEXT_MUTED
            )
            empty_label.pack(pady=30)
        
        # 如果有探索笔记（从探索模式转换过来），显示结论
        if task.conclusion:
            conclusion_frame = ctk.CTkFrame(parent, fg_color=ThemeConfig.BG_TERTIARY, corner_radius=12)
            conclusion_frame.pack(fill="x", pady=(24, 0))

            conclusion_header = ctk.CTkFrame(conclusion_frame, fg_color="transparent")
            conclusion_header.pack(fill="x", padx=16, pady=(12, 8))

            conclusion_title = ctk.CTkLabel(
                conclusion_header,
                text="💡 探索结论",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"),
                text_color=ThemeConfig.ACCENT_EXPLORING
            )
            conclusion_title.pack(side="left")

            clear_conclusion_btn = ctk.CTkButton(
                conclusion_header,
                text="清除",
                font=ctk.CTkFont(size=12),
                fg_color=ThemeConfig.BG_TERTIARY,
                hover_color=ThemeConfig.BG_HOVER,
                text_color=ThemeConfig.TEXT_SECONDARY,
                height=26,
                corner_radius=6,
                command=lambda: self._clear_conclusion(task)
            )
            clear_conclusion_btn.pack(side="right")

            edit_conclusion_btn = ctk.CTkButton(
                conclusion_header,
                text="✏️",
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                hover_color=ThemeConfig.BG_HOVER,
                width=28,
                height=26,
                command=lambda: self._edit_conclusion_dialog(task)
            )
            edit_conclusion_btn.pack(side="right", padx=(0, 6))

            conclusion_text = ctk.CTkLabel(
                conclusion_frame,
                text=task.conclusion,
                font=ctk.CTkFont(family="Microsoft YaHei", size=13),
                text_color=ThemeConfig.TEXT_PRIMARY,
                anchor="w",
                justify="left",
                wraplength=660
            )
            conclusion_text.pack(anchor="w", padx=16, pady=(0, 12))

    def _create_subtask_item(self, parent, task: Task, subtask: SubTask, index: int):
        """创建子任务项"""
        is_completed = subtask.status == TaskStatus.COMPLETED
        drag_cursor = "hand2"
        
        item = ctk.CTkFrame(
            parent,
            fg_color=ThemeConfig.BG_TERTIARY,
            corner_radius=10,
            border_width=1,
            border_color=ThemeConfig.ACCENT_SUCCESS if is_completed else ThemeConfig.BORDER_DEFAULT,
            cursor=drag_cursor
        )
        item.pack(fill="x", pady=4)
        self._subtask_items.append({"widget": item, "subtask": subtask})

        item.bind("<Button-1>", lambda e, it=item, t=task, s=subtask, i=index: self._on_subtask_drag_start(e, it, t, s, i))
        item.bind("<B1-Motion>", lambda e, it=item, p=parent: self._on_subtask_drag_motion(e, it, p))
        item.bind("<ButtonRelease-1>", lambda e, s=subtask: self._on_subtask_drag_end(e, s))
        
        content = ctk.CTkFrame(item, fg_color="transparent", cursor=drag_cursor)
        content.pack(fill="x", padx=12, pady=10)
        content.bind("<Button-1>", lambda e, it=item, t=task, s=subtask, i=index: self._on_subtask_drag_start(e, it, t, s, i))
        content.bind("<B1-Motion>", lambda e, it=item, p=parent: self._on_subtask_drag_motion(e, it, p))
        content.bind("<ButtonRelease-1>", lambda e, s=subtask: self._on_subtask_drag_end(e, s))
        
        # 复选框
        checkbox_var = ctk.BooleanVar(value=is_completed)
        checkbox = ctk.CTkCheckBox(
            content,
            text="",
            variable=checkbox_var,
            width=24,
            fg_color=ThemeConfig.ACCENT_SUCCESS,
            hover_color=ThemeConfig.ACCENT_SUCCESS,
            border_color=ThemeConfig.BORDER_DEFAULT,
            command=lambda: self._toggle_subtask(task, subtask, checkbox_var.get())
        )
        checkbox.pack(side="left", padx=(0, 12))
        
        # 标题
        title_label = ctk.CTkLabel(
            content,
            text=subtask.title,
            font=ctk.CTkFont(
                family="Microsoft YaHei", 
                size=14,
                overstrike=is_completed
            ),
            text_color=ThemeConfig.TEXT_MUTED if is_completed else ThemeConfig.TEXT_PRIMARY,
            anchor="w",
            cursor=drag_cursor
        )
        title_label.pack(side="left", fill="x", expand=True)
        title_label.bind("<Button-1>", lambda e, it=item, t=task, s=subtask, i=index: self._on_subtask_drag_start(e, it, t, s, i))
        title_label.bind("<B1-Motion>", lambda e, it=item, p=parent: self._on_subtask_drag_motion(e, it, p))
        title_label.bind("<ButtonRelease-1>", lambda e, s=subtask: self._on_subtask_drag_end(e, s))

        edit_btn = ctk.CTkButton(
            content,
            text="✏️",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_MUTED,
            width=28,
            height=28,
            command=lambda: self._edit_subtask_dialog(task, subtask)
        )
        edit_btn.pack(side="right", padx=(4, 0))
        
        # 删除按钮
        delete_btn = ctk.CTkButton(
            content,
            text="✕",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=ThemeConfig.ACCENT_DANGER,
            text_color=ThemeConfig.TEXT_MUTED,
            width=28,
            height=28,
            command=lambda: self._delete_subtask(task, subtask)
        )
        delete_btn.pack(side="right")
    
    def _show_exploring_content(self, parent, task: Task, highlight_note_id: Optional[str] = None):
        """显示探索模式内容"""
        # 探索笔记区域
        notes_header = ctk.CTkFrame(parent, fg_color="transparent")
        notes_header.pack(fill="x", pady=(0, 8))
        
        notes_title = ctk.CTkLabel(
            notes_header,
            text="📝 探索笔记",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        notes_title.pack(side="left", padx=(0, 10))

        # 笔记排序模式（放在标题栏右侧）
        if not hasattr(self, "_note_sort_mode_var"):
            self._note_sort_mode_var = ctk.StringVar(value="auto")

        note_mode_frame = ctk.CTkFrame(notes_header, fg_color="transparent")
        note_mode_frame.pack(side="right", padx=(20, 0))

        note_mode_label = ctk.CTkLabel(
            note_mode_frame,
            text="笔记排序:",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        note_mode_label.pack(side="left", padx=(0, 8))

        note_auto_btn = ctk.CTkRadioButton(
            note_mode_frame,
            text="自动",
            variable=self._note_sort_mode_var,
            value="auto",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_SECONDARY,
            fg_color=ThemeConfig.ACCENT_EXPLORING,
            command=self._on_note_sort_mode_change
        )
        note_auto_btn.pack(side="left", padx=(0, 12))

        note_manual_btn = ctk.CTkRadioButton(
            note_mode_frame,
            text="手动",
            variable=self._note_sort_mode_var,
            value="manual",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_SECONDARY,
            fg_color=ThemeConfig.ACCENT_EXPLORING,
            command=self._on_note_sort_mode_change
        )
        note_manual_btn.pack(side="left")

        if self._is_note_manual_sort_mode():
            note_drag_hint = ctk.CTkLabel(
                note_mode_frame,
                text="(拖拽排序)",
                font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                text_color=ThemeConfig.TEXT_MUTED
            )
            note_drag_hint.pack(side="left", padx=(8, 0))
        
        # 排序选择器（仅自动模式显示）
        if not self._is_note_manual_sort_mode():
            sort_row = ctk.CTkFrame(parent, fg_color="transparent")
            sort_row.pack(fill="x", pady=(0, 12))

            sort_frame = ctk.CTkFrame(sort_row, fg_color="transparent")
            sort_frame.pack(side="right")

            sort_label = ctk.CTkLabel(
                sort_frame,
                text="排序:",
                font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                text_color=ThemeConfig.TEXT_SECONDARY
            )
            sort_label.pack(side="left", padx=(0, 8))

            # 初始化排序变量（如果不存在）
            if not hasattr(self, '_sort_field_var'):
                self._sort_field_var = ctk.StringVar(value="created_at")
            if not hasattr(self, '_sort_order_var'):
                self._sort_order_var = ctk.StringVar(value="desc")

            # 排序字段选择
            sort_field_options = [
                ("⏱️ 创建时间", "created_at"),
                ("✏️ 修改时间", "updated_at")
            ]

            for text, value in sort_field_options:
                radio = ctk.CTkRadioButton(
                    sort_frame,
                    text=text,
                    variable=self._sort_field_var,
                    value=value,
                    font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                    text_color=ThemeConfig.TEXT_SECONDARY,
                    fg_color=ThemeConfig.ACCENT_EXPLORING,
                    command=lambda: self._refresh_task_detail(task)
                )
                radio.pack(side="left", padx=(0, 16))

            # 排序方向切换按钮
            self.note_sort_order_btn = ctk.CTkButton(
                sort_frame,
                text="🔽 降序" if self._sort_order_var.get() == "desc" else "🔼 升序",
                font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                fg_color=ThemeConfig.BG_TERTIARY,
                hover_color=ThemeConfig.ACCENT_EXPLORING,
                text_color=ThemeConfig.TEXT_SECONDARY,
                width=80,
                height=28,
                corner_radius=6,
                command=lambda: self._toggle_sort_order(task)
            )
            self.note_sort_order_btn.pack(side="left", padx=(0, 0))
        
        # 批量管理按钮（已完成的任务也可以使用）
        batch_btn = ctk.CTkButton(
            notes_header,
            text="📦 批量管理" if not self.batch_mode else "✅ 完成批量",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.ACCENT_EXPLORING,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=32,
            corner_radius=8,
            command=lambda: self._toggle_batch_mode(task)
        )
        batch_btn.pack(side="right", padx=(0, 12))

        # 以下按钮仅在未完成状态显示
        if task.status != TaskStatus.COMPLETED:
            # 找到解决方案按钮
            found_solution_btn = ctk.CTkButton(
                notes_header,
                text="💡 找到解决方案",
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                fg_color=ThemeConfig.ACCENT_SUCCESS,
                hover_color="#2D9142",
                height=32,
                corner_radius=8,
                command=lambda: self._found_solution_dialog(task)
            )
            found_solution_btn.pack(side="right", padx=(0, 12))
            
            # 添加笔记按钮
            add_note_btn = ctk.CTkButton(
                notes_header,
                text="➕ 记录探索",
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                fg_color=ThemeConfig.ACCENT_EXPLORING,
                hover_color="#D97A35",
                height=32,
                corner_radius=8,
                command=lambda: self._add_note_dialog(task)
            )
            add_note_btn.pack(side="right", padx=(0, 12))

        # 批量操作框（在进入批量模式时显示）
        batch_frame = ctk.CTkFrame(parent, fg_color=ThemeConfig.BG_TERTIARY, corner_radius=10)
        
        if self.batch_mode:
            batch_frame.pack(fill="x", pady=(0, 16))

            delete_btn = ctk.CTkButton(
                batch_frame,
                text="🗑️ 批量删除",
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                fg_color=ThemeConfig.ACCENT_DANGER,
                hover_color="#E5534B",
                height=32,
                corner_radius=8,
                command=lambda: self._batch_delete_notes(task)
            )
            delete_btn.pack(side="left", padx=12, pady=8)

            move_btn = ctk.CTkButton(
                batch_frame,
                text="➡️ 批量移动",
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                fg_color=ThemeConfig.ACCENT_SUCCESS,
                hover_color="#2D9142",
                height=32,
                corner_radius=8,
                command=lambda: self._show_batch_move_dialog(task)
            )
            move_btn.pack(side="left", padx=12, pady=8)

            export_btn = ctk.CTkButton(
                batch_frame,
                text="📤 导出 Markdown",
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                fg_color=ThemeConfig.ACCENT_PLANNING,
                hover_color="#4A90D9",
                height=32,
                corner_radius=8,
                command=lambda: self._export_selected_notes(task)
            )
            export_btn.pack(side="left", padx=12, pady=8)
        
        # 探索说明
        hint_frame = ctk.CTkFrame(parent, fg_color=ThemeConfig.BG_TERTIARY, corner_radius=10)
        hint_frame.pack(fill="x", pady=(0, 16))
        
        hint_text = ctk.CTkLabel(
            hint_frame,
            text="💭 在探索模式下，记录你的尝试、发现和思考。当找到解决方案后，可以切换到规划模式进行任务拆解。",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=ThemeConfig.TEXT_SECONDARY,
            wraplength=660,
            justify="left"
        )
        hint_text.pack(padx=16, pady=12)
        
        # 笔记列表
        self._note_items = []
        if task.exploration_notes:
            if self._is_note_manual_sort_mode():
                sorted_notes = list(task.exploration_notes)
            else:
                # 根据排序选项排序笔记
                sort_field = self._sort_field_var.get()
                sort_order = self._sort_order_var.get()
                is_reverse = (sort_order == "desc")

                if sort_field == "updated_at":
                    # 按修改时间排序（如果没有updated_at，使用created_at）
                    sorted_notes = sorted(
                        task.exploration_notes,
                        key=lambda n: getattr(n, 'updated_at', n.created_at),
                        reverse=is_reverse
                    )
                else:
                    # 按创建时间排序
                    sorted_notes = sorted(
                        task.exploration_notes,
                        key=lambda n: n.created_at,
                        reverse=is_reverse
                    )
            
            for index, note in enumerate(sorted_notes):
                self._create_note_item(
                    parent,
                    task,
                    note,
                    index,
                    highlight_note_id=highlight_note_id,
                    selectable=self.batch_mode
                )
        else:
            empty_label = ctk.CTkLabel(
                parent,
                text="暂无探索笔记\n记录你的尝试和发现",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                text_color=ThemeConfig.TEXT_MUTED,
                justify="center"
            )
            empty_label.pack(pady=30)
    
    def _create_note_item(
        self,
        parent,
        task: Task,
        note: ExplorationNote,
        index: int,
        highlight_note_id: Optional[str] = None,
        selectable: bool = False
    ):
        """创建笔记项"""
        if highlight_note_id and note.id == highlight_note_id:
            border_color = ThemeConfig.ACCENT_SUCCESS
        else:
            border_color = ThemeConfig.ACCENT_WARNING if note.is_breakthrough else ThemeConfig.BORDER_DEFAULT
        drag_cursor = "hand2" if self._is_note_manual_sort_mode() else "arrow"
        
        item = ctk.CTkFrame(
            parent,
            fg_color=ThemeConfig.BG_TERTIARY,
            corner_radius=12,
            border_width=2 if note.is_breakthrough else 1,
            border_color=border_color,
            cursor=drag_cursor
        )
        item.pack(fill="x", pady=6)
        self._note_items.append({"widget": item, "note": note})
        def bind_note_drag(widget):
            widget.bind("<Button-1>", lambda e, it=item, t=task, n=note, i=index: self._on_note_drag_start(e, it, t, n, i))
            widget.bind("<B1-Motion>", lambda e, it=item: self._on_note_drag_motion(e, it))
            widget.bind("<ButtonRelease-1>", lambda e, n=note: self._on_note_drag_end(e, n))
        if self._is_note_manual_sort_mode():
            bind_note_drag(item)
        
        content = ctk.CTkFrame(item, fg_color="transparent", cursor=drag_cursor)
        content.pack(fill="x", padx=16, pady=12)
        if self._is_note_manual_sort_mode():
            bind_note_drag(content)
        
        # 头部
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x")
        if self._is_note_manual_sort_mode():
            bind_note_drag(header)

        if selectable:
            checkbox_var = ctk.BooleanVar(value=note.id in self.selected_note_ids)
            checkbox = ctk.CTkCheckBox(
                header,
                text="",
                variable=checkbox_var,
                width=24,
                fg_color=ThemeConfig.ACCENT_SUCCESS,
                hover_color=ThemeConfig.ACCENT_SUCCESS,
                border_color=ThemeConfig.BORDER_DEFAULT,
                command=lambda: self._toggle_note_selection(note.id, checkbox_var.get())
            )
            checkbox.pack(side="left", padx=(0, 8))
        
        # 突破标记
        if note.is_breakthrough:
            breakthrough_label = ctk.CTkLabel(
                header,
                text="⭐ 突破性发现",
                font=ctk.CTkFont(family="Microsoft YaHei", size=11, weight="bold"),
                text_color=ThemeConfig.ACCENT_WARNING,
                cursor=drag_cursor
            )
            breakthrough_label.pack(side="left", padx=(0, 8))
            if self._is_note_manual_sort_mode():
                bind_note_drag(breakthrough_label)
        
        # 时间
        time_str = note.created_at.strftime("%m-%d %H:%M")
        time_label = ctk.CTkLabel(
            header,
            text=time_str,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_MUTED,
            cursor=drag_cursor
        )
        time_label.pack(side="left")
        if self._is_note_manual_sort_mode():
            bind_note_drag(time_label)
        
        # 删除按钮
        delete_btn = ctk.CTkButton(
            header,
            text="✕",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=ThemeConfig.ACCENT_DANGER,
            text_color=ThemeConfig.TEXT_MUTED,
            width=28,
            height=28,
            command=lambda: self._delete_note(task, note)
        )
        delete_btn.pack(side="right")

        # 编辑按钮
        edit_btn = ctk.CTkButton(
            header,
            text="✏️",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=ThemeConfig.ACCENT_PLANNING,
            text_color=ThemeConfig.TEXT_MUTED,
            width=28,
            height=28,
            command=lambda: self._edit_note_dialog(task, note)
        )
        edit_btn.pack(side="right", padx=(0, 8))

        # 移动按钮
        move_btn = ctk.CTkButton(
            header,
            text="➡️",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=ThemeConfig.ACCENT_SUCCESS,
            text_color=ThemeConfig.TEXT_MUTED,
            width=28,
            height=28,
            command=lambda: self._show_move_note_dialog(task, note)
        )
        move_btn.pack(side="right", padx=(0, 8))

        # 复制按钮
        copy_btn = ctk.CTkButton(
            header,
            text="📋",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=ThemeConfig.ACCENT_PLANNING,
            text_color=ThemeConfig.TEXT_MUTED,
            width=28,
            height=28,
            command=lambda: self._show_copy_note_dialog(task, note)
        )
        copy_btn.pack(side="right", padx=(0, 8))
        
        # 内容
        content_label = ctk.CTkLabel(
            content,
            text=note.content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_PRIMARY,
            anchor="w",
            justify="left",
            cursor=drag_cursor,
            wraplength=640
        )
        content_label.pack(fill="x", pady=(10, 0), anchor="w")
        if self._is_note_manual_sort_mode():
            bind_note_drag(content_label)
        
        # 洞察
        if note.insight:
            insight_frame = ctk.CTkFrame(content, fg_color=ThemeConfig.BG_HOVER, corner_radius=8)
            insight_frame.pack(fill="x", pady=(10, 0))
            
            insight_label = ctk.CTkLabel(
                insight_frame,
                text=f"💡 {note.insight}",
                font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                text_color=ThemeConfig.ACCENT_PLANNING,
                anchor="w",
                justify="left",
                cursor=drag_cursor,
                wraplength=620
            )
            insight_label.pack(padx=12, pady=8, anchor="w")
            if self._is_note_manual_sort_mode():
                bind_note_drag(insight_frame)
                bind_note_drag(insight_label)

    def _toggle_batch_mode(self, task: Task):
        self.batch_mode = not self.batch_mode
        if not self.batch_mode:
            self.selected_note_ids = set()
        self._show_task_detail(task)

    def _toggle_sort_order(self, task: Task):
        """切换探索笔记排序方向"""
        current_order = self._sort_order_var.get()
        new_order = "asc" if current_order == "desc" else "desc"
        self._sort_order_var.set(new_order)
        # 更新按钮文字
        if hasattr(self, 'note_sort_order_btn') and self.note_sort_order_btn.winfo_exists():
            self.note_sort_order_btn.configure(
                text="🔽 降序" if new_order == "desc" else "🔼 升序"
            )
        self._refresh_task_detail(task)
    
    def _toggle_task_sort_order(self):
        """切换任务列表排序方向"""
        current_order = self._task_sort_order_var.get()
        new_order = "asc" if current_order == "desc" else "desc"
        self._task_sort_order_var.set(new_order)
        # 更新按钮文字
        self.task_sort_order_btn.configure(
            text="🔽 降序" if new_order == "desc" else "🔼 升序"
        )
        self._refresh_task_list()
    
    def _refresh_task_detail(self, task: Task):
        """刷新任务详情显示（保持批量模式状态）"""
        self._show_task_detail(task)

    def _toggle_note_selection(self, note_id: str, selected: bool):
        if selected:
            self.selected_note_ids.add(note_id)
        else:
            self.selected_note_ids.discard(note_id)

    def _batch_delete_notes(self, task: Task):
        if not self.selected_note_ids:
            messagebox.showwarning("提示", "请选择要删除的笔记")
            return
        confirm = messagebox.askyesno("确认删除", "确定删除选中的探索笔记吗？")
        if not confirm:
            return
        success = self.db.batch_delete_exploration_notes(task.id, list(self.selected_note_ids))
        if success:
            self.selected_note_ids = set()
            self._show_task_detail(task)

    def _show_batch_move_dialog(self, current_task: Task):
        if not self.selected_note_ids:
            messagebox.showwarning("提示", "请选择要移动的笔记")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("批量移动探索笔记")
        dialog_width, dialog_height = 520, 480
        dialog.geometry(f"{dialog_width}x{dialog_height}")
        dialog.minsize(dialog_width, 420)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - dialog_width) // 2
        y = self.winfo_y() + (self.winfo_height() - dialog_height) // 2
        dialog.geometry(f"+{x}+{y}")

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(2, weight=1)  # 让列表区域伸展，占满中间空间

        title_label = ctk.CTkLabel(
            content,
            text="➡️ 批量移动探索笔记",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 16))

        target_frame = ctk.CTkFrame(content, fg_color="transparent")
        target_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        target_label = ctk.CTkLabel(
            target_frame,
            text="选择目标任务",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        target_label.pack(anchor="w", pady=(0, 12))

        tasks = [t for t in self.db.get_all_tasks() if t.id != current_task.id]

        list_frame = ctk.CTkFrame(content, fg_color="transparent")
        list_frame.grid(row=2, column=0, sticky="nsew")

        scrollable = ctk.CTkScrollableFrame(
            list_frame,
            fg_color=ThemeConfig.BG_TERTIARY,
            corner_radius=10,
            height=160,
            width=460
        )
        scrollable.pack(fill="both", expand=True, pady=(0, 8))

        self._batch_target_task_id = ctk.StringVar(value="")

        selected_label = ctk.CTkLabel(
            content,
            text="已选择：无",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=ThemeConfig.TEXT_MUTED
        )
        selected_label.grid(row=3, column=0, sticky="w", pady=(4, 0))

        def select_target(task: Task):
            self._batch_target_task_id.set(task.id)
            selected_label.configure(text=f"已选择：{task.title}")

        if tasks:
            for task in tasks:
                btn = ctk.CTkButton(
                    scrollable,
                    text=f"📝 {task.title}",
                    font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                    text_color=ThemeConfig.TEXT_PRIMARY,
                    fg_color=ThemeConfig.BG_HOVER,
                    hover_color=ThemeConfig.ACCENT_PLANNING,
                    height=32,
                    corner_radius=8,
                    command=lambda t=task: select_target(t)
                )
                btn.pack(fill="x", padx=12, pady=6)
        else:
            empty_label = ctk.CTkLabel(
                scrollable,
                text="暂无可移动的目标任务",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                text_color=ThemeConfig.TEXT_MUTED
            )
            empty_label.pack(pady=30)

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.grid(row=4, column=0, sticky="ew", pady=(20, 0))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def move():
            print("DEBUG: move() 函数被调用")  # 调试信息
            target_id = self._batch_target_task_id.get()
            print(f"DEBUG: target_id = {target_id}")  # 调试信息
            print(f"DEBUG: selected_note_ids = {self.selected_note_ids}")  # 调试信息
            
            if not target_id:
                messagebox.showwarning("提示", "请选择目标任务")
                return
            
            try:
                moved_count = len(self.selected_note_ids)
                note_ids_list = list(self.selected_note_ids)
                
                print(f"DEBUG: 准备移动 {moved_count} 条笔记")  # 调试信息
                
                success = self.db.batch_move_exploration_notes(
                    current_task.id,
                    target_id,
                    note_ids_list
                )
                
                print(f"DEBUG: 移动结果 = {success}")  # 调试信息
                
                if success:
                    self.selected_note_ids = set()
                    self.batch_mode = False
                    dialog.destroy()
                    
                    # 刷新任务列表
                    self._refresh_task_list()
                    
                    # 跳转到目标任务
                    target_task = self.db.get_task(target_id)
                    if target_task:
                        self._select_task(target_task)
                    
                    messagebox.showinfo("成功", f"已移动 {moved_count} 条笔记")
                else:
                    messagebox.showerror("失败", "移动笔记失败")
            except Exception as e:
                print(f"DEBUG: 异常 = {e}")  # 调试信息
                import traceback
                traceback.print_exc()
                messagebox.showerror("错误", f"移动过程中出错：{str(e)}")

        move_btn = ctk.CTkButton(
            btn_frame,
            text="移动",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_SUCCESS,
            hover_color="#2D9142",
            height=38,
            corner_radius=10,
            command=move
        )
        move_btn.pack(side="right", fill="x", expand=True)
        print(f"DEBUG: 移动按钮已创建")  # 调试信息

    def _export_selected_notes(self, task: Task):
        if not self.selected_note_ids:
            messagebox.showwarning("提示", "请选择要导出的笔记")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".md",
            filetypes=[("Markdown", "*.md")],
            title="导出探索笔记"
        )
        if not path:
            return

        selected_notes = [n for n in task.exploration_notes if n.id in self.selected_note_ids]
        selected_notes.sort(key=lambda n: n.created_at)

        lines = [f"# 任务：{task.title}", ""]
        for note in selected_notes:
            time_str = note.created_at.strftime("%Y-%m-%d %H:%M")
            lines.append(f"- {time_str} {note.content}")
            if note.insight:
                lines.append(f"  - 洞察：{note.insight}")
            lines.append(f"  - 突破：{'是' if note.is_breakthrough else '否'}")

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except OSError:
            messagebox.showwarning("提示", "保存失败，请检查路径权限")
    
    # ==================== 对话框 ====================
    
    def _show_new_task_dialog(self):
        """显示新建任务对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("新建任务")
        dialog.geometry("520x480")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)
        
        # 居中显示
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 480) // 2
        dialog.geometry(f"+{x}+{y}")
        
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)
        
        # 标题
        title_label = ctk.CTkLabel(
            content,
            text="📋 创建新任务",
            font=ctk.CTkFont(family="Microsoft YaHei", size=20, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(anchor="w", pady=(0, 20))
        
        # 任务标题
        name_label = ctk.CTkLabel(
            content,
            text="任务标题",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        name_label.pack(anchor="w", pady=(0, 6))
        
        title_entry = ctk.CTkEntry(
            content,
            placeholder_text="输入任务标题...",
            font=ctk.CTkFont(family="Microsoft YaHei", size=14),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            height=42,
            corner_radius=10
        )
        title_entry.pack(fill="x", pady=(0, 16))
        
        # 任务描述
        desc_label = ctk.CTkLabel(
            content,
            text="任务描述（可选）",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        desc_label.pack(anchor="w", pady=(0, 6))
        
        desc_entry = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            height=80,
            corner_radius=10
        )
        desc_entry.pack(fill="x", pady=(0, 16))
        
        # 工作模式选择
        mode_label = ctk.CTkLabel(
            content,
            text="选择工作模式",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        mode_label.pack(anchor="w", pady=(0, 10))
        
        mode_var = ctk.StringVar(value="planning")
        
        mode_frame = ctk.CTkFrame(content, fg_color="transparent")
        mode_frame.pack(fill="x", pady=(0, 16))
        
        # 规划模式
        planning_radio = ctk.CTkRadioButton(
            mode_frame,
            text="📊 规划模式 - 我知道怎么做",
            variable=mode_var,
            value="planning",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_PRIMARY,
            fg_color=ThemeConfig.ACCENT_PLANNING
        )
        planning_radio.pack(anchor="w", pady=(0, 8))
        
        # 探索模式
        exploring_radio = ctk.CTkRadioButton(
            mode_frame,
            text="🔍 探索模式 - 我需要探索方法",
            variable=mode_var,
            value="exploring",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_PRIMARY,
            fg_color=ThemeConfig.ACCENT_EXPLORING
        )
        exploring_radio.pack(anchor="w")
        
        # 按钮
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(16, 0))
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=14),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=40,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        def create_task():
            title = title_entry.get().strip()
            if not title:
                messagebox.showwarning("提示", "请输入任务标题")
                return
            
            mode = TaskMode.EXPLORING if mode_var.get() == "exploring" else TaskMode.PLANNING
            knowledge = TaskKnowledge.KNOWN_WHAT_UNKNOWN_HOW if mode == TaskMode.EXPLORING else TaskKnowledge.KNOWN_WHAT_KNOWN_HOW
            
            task = self.db.create_task(
                title=title,
                description=desc_entry.get("1.0", "end-1c").strip(),
                mode=mode,
                knowledge=knowledge
            )
            
            dialog.destroy()
            self._refresh_task_list()
            self._select_task(task)
        
        create_btn = ctk.CTkButton(
            btn_frame,
            text="创建任务",
            font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"),
            fg_color=ThemeConfig.ACCENT_PLANNING,
            hover_color="#4A90D9",
            height=40,
            corner_radius=10,
            command=create_task
        )
        create_btn.pack(side="right", fill="x", expand=True)
    
    def _add_subtask_dialog(self, task: Task):
        """添加子任务对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("添加子任务")
        dialog.geometry("450x240")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)
        
        # 居中
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 450) // 2
        y = self.winfo_y() + (self.winfo_height() - 240) // 2
        dialog.geometry(f"+{x}+{y}")
        
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)
        
        title_label = ctk.CTkLabel(
            content,
            text="📋 添加子任务",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(anchor="w", pady=(0, 16))
        
        entry = ctk.CTkEntry(
            content,
            placeholder_text="输入子任务内容...",
            font=ctk.CTkFont(family="Microsoft YaHei", size=14),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            height=42,
            corner_radius=10
        )
        entry.pack(fill="x", pady=(0, 20))
        entry.focus()
        
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        def add():
            title = entry.get().strip()
            if title:
                self.db.add_subtask(task.id, title)
                dialog.destroy()
                self._show_task_detail(task)
                self._refresh_tracker_if_visible()
        
        add_btn = ctk.CTkButton(
            btn_frame,
            text="添加",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_PLANNING,
            hover_color="#4A90D9",
            height=38,
            corner_radius=10,
            command=add
        )
        add_btn.pack(side="right", fill="x", expand=True)
        
        entry.bind("<Return>", lambda e: add())
    
    def _add_note_dialog(self, task: Task):
        """添加探索笔记对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("记录探索")
        dialog.geometry("520x420")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)

        # 居中
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 420) // 2
        dialog.geometry(f"+{x}+{y}")

        # 绑定窗口事件
        dialog.bind("<Configure>", lambda e: self._on_dialog_configure(dialog))

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)
        
        title_label = ctk.CTkLabel(
            content,
            text="📝 记录探索",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(anchor="w", pady=(0, 16))
        
        # 探索内容
        content_label = ctk.CTkLabel(
            content,
            text="你尝试了什么？发现了什么？",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        content_label.pack(anchor="w", pady=(0, 6))
        
        content_entry = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            height=100,
            corner_radius=10
        )
        content_entry.pack(fill="x", pady=(0, 16))
        content_entry.focus()
        
        # 洞察
        insight_label = ctk.CTkLabel(
            content,
            text="获得的洞察/启发（可选）",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        insight_label.pack(anchor="w", pady=(0, 6))
        
        insight_entry = ctk.CTkEntry(
            content,
            placeholder_text="这次尝试给你带来了什么启发？",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            height=40,
            corner_radius=10
        )
        insight_entry.pack(fill="x", pady=(0, 12))
        
        # 突破性发现
        breakthrough_var = ctk.BooleanVar(value=False)
        breakthrough_cb = ctk.CTkCheckBox(
            content,
            text="⭐ 这是一个突破性发现！",
            variable=breakthrough_var,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.ACCENT_WARNING,
            fg_color=ThemeConfig.ACCENT_WARNING,
            hover_color=ThemeConfig.ACCENT_WARNING
        )
        breakthrough_cb.pack(anchor="w", pady=(0, 20))
        
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        def add():
            text = content_entry.get("1.0", "end-1c").strip()
            if text:
                self.db.add_exploration_note(
                    task.id,
                    text,
                    insight_entry.get().strip(),
                    breakthrough_var.get()
                )
                dialog.destroy()
                self._show_task_detail(task)
        
        add_btn = ctk.CTkButton(
            btn_frame,
            text="记录",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_EXPLORING,
            hover_color="#D97A35",
            height=38,
            corner_radius=10,
            command=add
        )
        add_btn.pack(side="right", fill="x", expand=True)
    
    def _found_solution_dialog(self, task: Task):
        """找到解决方案对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("找到解决方案")
        dialog.geometry("520x320")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)
        
        # 居中
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 320) // 2
        dialog.geometry(f"+{x}+{y}")
        
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)
        
        title_label = ctk.CTkLabel(
            content,
            text="💡 找到解决方案",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.ACCENT_SUCCESS
        )
        title_label.pack(anchor="w", pady=(0, 8))
        
        hint_label = ctk.CTkLabel(
            content,
            text="记录你的解决方案，然后可以切换到规划模式进行任务拆解",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=ThemeConfig.TEXT_MUTED
        )
        hint_label.pack(anchor="w", pady=(0, 16))
        
        solution_entry = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            height=120,
            corner_radius=10
        )
        solution_entry.pack(fill="x", pady=(0, 20))
        solution_entry.focus()
        
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        def save():
            solution = solution_entry.get("1.0", "end-1c").strip()
            if solution:
                self.db.set_task_conclusion(task.id, solution)
                self.db.switch_task_mode(task.id, to_exploring=False)
                dialog.destroy()
                # 重新获取更新后的任务
                updated_task = self.db.get_task(task.id)
                if updated_task:
                    self._refresh_task_list()
                    self._select_task(updated_task)
                    self._refresh_tracker_if_visible()
        
        save_btn = ctk.CTkButton(
            btn_frame,
            text="保存并切换到规划模式",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_SUCCESS,
            hover_color="#2D9142",
            height=38,
            corner_radius=10,
            command=save
        )
        save_btn.pack(side="right", fill="x", expand=True)
    
    def _edit_task_title(self, task: Task):
        """编辑任务标题"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("编辑任务")
        dialog.geometry("450x200")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)
        
        # 居中
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 450) // 2
        y = self.winfo_y() + (self.winfo_height() - 200) // 2
        dialog.geometry(f"+{x}+{y}")
        
        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)
        
        title_label = ctk.CTkLabel(
            content,
            text="✏️ 编辑任务标题",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(anchor="w", pady=(0, 16))
        
        entry = ctk.CTkEntry(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=14),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            height=42,
            corner_radius=10
        )
        entry.pack(fill="x", pady=(0, 20))
        entry.insert(0, task.title)
        entry.focus()
        entry.select_range(0, "end")
        
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        def save():
            new_title = entry.get().strip()
            if new_title:
                self.db.update_task(task.id, title=new_title)
                dialog.destroy()
                updated_task = self.db.get_task(task.id)
                if updated_task:
                    self._refresh_task_list()
                    self._show_task_detail(updated_task)
                    self._refresh_tracker_if_visible()
        
        save_btn = ctk.CTkButton(
            btn_frame,
            text="保存",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_PLANNING,
            hover_color="#4A90D9",
            height=38,
            corner_radius=10,
            command=save
        )
        save_btn.pack(side="right", fill="x", expand=True)

    def _edit_task_dialog(self, task: Task):
        """编辑任务标题与描述"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("编辑任务")
        dialog.geometry("520x420")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 420) // 2
        dialog.geometry(f"+{x}+{y}")

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)

        title_label = ctk.CTkLabel(
            content,
            text="📝 编辑任务",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(anchor="w", pady=(0, 16))

        title_entry = ctk.CTkEntry(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=14),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            height=40,
            corner_radius=10
        )
        title_entry.pack(fill="x", pady=(0, 12))
        title_entry.insert(0, task.title)

        desc_entry = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            height=180,
            corner_radius=10
        )
        desc_entry.pack(fill="x", pady=(0, 20))
        if task.description:
            desc_entry.insert("1.0", task.description)

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def save():
            new_title = title_entry.get().strip()
            new_desc = desc_entry.get("1.0", "end-1c").strip()
            if new_title:
                self.db.update_task(task.id, title=new_title, description=new_desc)
                dialog.destroy()
                updated_task = self.db.get_task(task.id)
                if updated_task:
                    self._refresh_task_list()
                    self._show_task_detail(updated_task)
                    self._refresh_tracker_if_visible()

        save_btn = ctk.CTkButton(
            btn_frame,
            text="保存",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_PLANNING,
            hover_color="#4A90D9",
            height=38,
            corner_radius=10,
            command=save
        )
        save_btn.pack(side="right", fill="x", expand=True)

    def _edit_task_description(self, task: Task):
        """编辑任务描述"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("编辑任务描述")
        dialog.geometry("520x360")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 360) // 2
        dialog.geometry(f"+{x}+{y}")

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)

        title_label = ctk.CTkLabel(
            content,
            text="✏️ 编辑任务描述",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(anchor="w", pady=(0, 16))

        desc_entry = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            height=160,
            corner_radius=10
        )
        desc_entry.pack(fill="x", pady=(0, 20))
        if task.description:
            desc_entry.insert("1.0", task.description)
        desc_entry.focus()

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def save():
            new_desc = desc_entry.get("1.0", "end-1c").strip()
            self.db.update_task(task.id, description=new_desc)
            dialog.destroy()
            updated_task = self.db.get_task(task.id)
            if updated_task:
                self._refresh_task_list()
                self._show_task_detail(updated_task)
                self._refresh_tracker_if_visible()

        save_btn = ctk.CTkButton(
            btn_frame,
            text="保存",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_PLANNING,
            hover_color="#4A90D9",
            height=38,
            corner_radius=10,
            command=save
        )
        save_btn.pack(side="right", fill="x", expand=True)

    def _edit_subtask_dialog(self, task: Task, subtask: SubTask):
        """编辑子任务对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("编辑子任务")
        dialog.geometry("520x420")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 420) // 2
        dialog.geometry(f"+{x}+{y}")

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)

        title_label = ctk.CTkLabel(
            content,
            text="✏️ 编辑子任务",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(anchor="w", pady=(0, 16))

        title_entry = ctk.CTkEntry(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=14),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            height=40,
            corner_radius=10
        )
        title_entry.pack(fill="x", pady=(0, 12))
        title_entry.insert(0, subtask.title)

        desc_entry = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            height=120,
            corner_radius=10
        )
        desc_entry.pack(fill="x", pady=(0, 12))
        if subtask.description:
            desc_entry.insert("1.0", subtask.description)

        notes_entry = ctk.CTkEntry(
            content,
            placeholder_text="备注（可选）",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            height=36,
            corner_radius=10
        )
        notes_entry.pack(fill="x", pady=(0, 20))
        if subtask.notes:
            notes_entry.insert(0, subtask.notes)

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def save():
            new_title = title_entry.get().strip()
            new_desc = desc_entry.get("1.0", "end-1c").strip()
            new_notes = notes_entry.get().strip()
            if new_title:
                self.db.update_subtask(
                    task.id,
                    subtask.id,
                    title=new_title,
                    description=new_desc,
                    notes=new_notes
                )
                dialog.destroy()
                updated_task = self.db.get_task(task.id)
                if updated_task:
                    self._show_task_detail(updated_task)
                    self._refresh_tracker_if_visible()
                    self._refresh_tracker_if_visible()

        save_btn = ctk.CTkButton(
            btn_frame,
            text="保存",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_PLANNING,
            hover_color="#4A90D9",
            height=38,
            corner_radius=10,
            command=save
        )
        save_btn.pack(side="right", fill="x", expand=True)

    def _edit_conclusion_dialog(self, task: Task):
        """编辑探索结论对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("编辑探索结论")
        dialog.geometry("520x360")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)

        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 360) // 2
        dialog.geometry(f"+{x}+{y}")

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)

        title_label = ctk.CTkLabel(
            content,
            text="✏️ 编辑探索结论",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(anchor="w", pady=(0, 16))

        entry = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            height=160,
            corner_radius=10
        )
        entry.pack(fill="x", pady=(0, 20))
        if task.conclusion:
            entry.insert("1.0", task.conclusion)
        entry.focus()

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def save():
            new_text = entry.get("1.0", "end-1c").strip()
            if new_text:
                self.db.set_task_conclusion(task.id, new_text)
                dialog.destroy()
                updated_task = self.db.get_task(task.id)
                if updated_task:
                    self._show_task_detail(updated_task)
                    self._refresh_tracker_if_visible()

        save_btn = ctk.CTkButton(
            btn_frame,
            text="保存",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_PLANNING,
            hover_color="#4A90D9",
            height=38,
            corner_radius=10,
            command=save
        )
        save_btn.pack(side="right", fill="x", expand=True)

    def _clear_conclusion(self, task: Task):
        """清除探索结论"""
        confirm = messagebox.askyesno("确认清除", "确定要清除当前结论吗？")
        if not confirm:
            return
        self.db.clear_task_conclusion(task.id)
        updated_task = self.db.get_task(task.id)
        if updated_task:
            self._show_task_detail(updated_task)
            self._refresh_tracker_if_visible()

    # ==================== 任务追踪窗口 ====================

    def _toggle_tracker_window(self):
        """切换任务追踪悬浮窗"""
        if self.tracker_window is None:
            self.tracker_window = TaskTrackerWindow(self, self.db)
            self.tracker_window_visible = True
        elif self.tracker_window_visible:
            self.tracker_window.withdraw()
            self.tracker_window_visible = False
        else:
            self.tracker_window.deiconify()
            self.tracker_window._refresh_tracker()
            self.tracker_window_visible = True

    def _refresh_tracker_if_visible(self):
        """如果追踪窗口可见，刷新它"""
        if self.tracker_window and self.tracker_window_visible:
            self.tracker_window._refresh_tracker()

    def _show_move_note_dialog(self, current_task: Task, note: ExplorationNote):
        """显示移动笔记对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("移动探索笔记")
        dialog.geometry("520x480")  # 增加高度
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)

        # 居中
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 480) // 2
        dialog.geometry(f"+{x}+{y}")

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(2, weight=1)

        title_label = ctk.CTkLabel(
            content,
            text="➡️ 移动探索笔记",
            font=ctk.CTkFont(family="Microsoft YaHei", size=20, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 16))

        # 笔记预览
        preview_frame = ctk.CTkFrame(content, fg_color=ThemeConfig.BG_TERTIARY, corner_radius=10)
        preview_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        preview_label = ctk.CTkLabel(
            preview_frame,
            text=f"'{note.content[:100]}{'...' if len(note.content) > 100 else ''}'",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=ThemeConfig.TEXT_MUTED,
            wraplength=460,
            justify="left"
        )
        preview_label.pack(padx=16, pady=12)

        # 目标选择
        target_frame = ctk.CTkFrame(content, fg_color="transparent")
        target_frame.grid(row=2, column=0, sticky="nsew")

        target_label = ctk.CTkLabel(
            target_frame,
            text="选择目标任务",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        target_label.pack(anchor="w", pady=(0, 12))

        # 初始化目标任务ID变量（必须在使用前定义）
        target_task_id = ctk.StringVar(value="")

        # 任务列表（排除当前任务）
        all_tasks = self.db.get_all_tasks()
        tasks = [t for t in all_tasks if t.id != current_task.id]

        # 任务列表滚动容器
        scrollable = ctk.CTkScrollableFrame(
            target_frame,
            fg_color=ThemeConfig.BG_TERTIARY,
            corner_radius=10,
            height=140,
            width=460
        )
        scrollable.pack(fill="both", expand=True, pady=(0, 8))

        # 选择状态标签（放在scrollable之后）
        selected_label = ctk.CTkLabel(
            content,
            text="已选择：无",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=ThemeConfig.TEXT_MUTED
        )
        selected_label.grid(row=3, column=0, sticky="w", pady=(4, 0))

        def select_target(task: Task):
            target_task_id.set(task.id)
            selected_label.configure(text=f"已选择：{task.title}")

        if tasks:
            for task in tasks:
                btn = ctk.CTkButton(
                    scrollable,
                    text=f"📝 {task.title}",
                    font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                    text_color=ThemeConfig.TEXT_PRIMARY,
                    fg_color=ThemeConfig.BG_HOVER,
                    hover_color=ThemeConfig.ACCENT_PLANNING,
                    height=32,
                    corner_radius=8,
                    command=lambda t=task: select_target(t)
                )
                btn.pack(fill="x", padx=12, pady=6)
        else:
            empty_label = ctk.CTkLabel(
                scrollable,
                text="暂无可移动的目标任务",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                text_color=ThemeConfig.TEXT_MUTED
            )
            empty_label.pack(pady=30)

        # 按钮
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.grid(row=4, column=0, sticky="ew", pady=(20, 0))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def move():
            target_id = target_task_id.get()
            if not target_id:
                messagebox.showwarning("提示", "请选择目标任务")
                return

            try:
                success = self.db.move_exploration_note(current_task.id, target_id, note.id)

                if success:
                    dialog.destroy()
                    self._refresh_task_list()

                    # 跳转到目标任务
                    target_task = self.db.get_task(target_id)
                    if target_task:
                        self._select_task(target_task)
                    
                    messagebox.showinfo("成功", "笔记已移动")
                else:
                    messagebox.showerror("失败", "移动笔记失败")
            except Exception as e:
                messagebox.showerror("错误", f"移动过程中出错：{str(e)}")

        move_btn = ctk.CTkButton(
            btn_frame,
            text="移动",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_SUCCESS,
            hover_color="#2D9142",
            height=38,
            corner_radius=10,
            command=move
        )
        move_btn.pack(side="right", fill="x", expand=True)

    def _show_edit_history_note_dialog(self, task: Task, note: ExplorationNote):
        """编辑探索记录笔记对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("编辑探索记录笔记")
        dialog.geometry("520x480")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)

        # 居中
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 480) // 2
        dialog.geometry(f"+{x}+{y}")

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)

        title_label = ctk.CTkLabel(
            content,
            text="✏️ 编辑探索笔记",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(anchor="w", pady=(0, 16))

        # 探索内容
        content_label = ctk.CTkLabel(
            content,
            text="笔记内容",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        content_label.pack(anchor="w", pady=(0, 6))

        content_entry = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            height=100,
            corner_radius=10
        )
        content_entry.pack(fill="x", pady=(0, 16))
        content_entry.insert("1.0", note.content)
        content_entry.focus()

        # 洞察
        insight_label = ctk.CTkLabel(
            content,
            text="获得的洞察/启发（可选）",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        insight_label.pack(anchor="w", pady=(0, 6))

        insight_entry = ctk.CTkEntry(
            content,
            placeholder_text="这次尝试给你带来了什么启发？",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            height=40,
            corner_radius=10
        )
        insight_entry.pack(fill="x", pady=(0, 12))
        if note.insight:
            insight_entry.insert(0, note.insight)

        # 突破性发现
        breakthrough_var = ctk.BooleanVar(value=note.is_breakthrough)
        breakthrough_cb = ctk.CTkCheckBox(
            content,
            text="⭐ 这是一个突破性发现！",
            variable=breakthrough_var,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.ACCENT_WARNING,
            fg_color=ThemeConfig.ACCENT_WARNING,
            hover_color=ThemeConfig.ACCENT_WARNING
        )
        breakthrough_cb.pack(anchor="w", pady=(0, 20))

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")

        def save():
            new_content = content_entry.get("1.0", "end").strip()
            new_insight = insight_entry.get().strip()
            new_breakthrough = breakthrough_var.get()

            if not new_content:
                messagebox.showwarning("提示", "笔记内容不能为空")
                return

            # 更新笔记
            note.content = new_content
            note.insight = new_insight
            note.is_breakthrough = new_breakthrough
            note.updated_at = datetime.now()

            # 保存到数据库
            success = self.db.update_task(task.id, updated_at=datetime.now())
            if success:
                messagebox.showinfo("成功", "笔记已更新")
                dialog.destroy()
                # 刷新显示
                self._show_task_detail(task)
            else:
                messagebox.showerror("错误", "保存失败，请重试")

        save_btn = ctk.CTkButton(
            btn_frame,
            text="💾 保存修改",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.ACCENT_SUCCESS,
            hover_color="#2D9142",
            height=38,
            corner_radius=10,
            command=save
        )
        save_btn.pack(side="right", fill="x", expand=True, padx=(8, 0))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

    def _show_copy_note_dialog(self, current_task: Task, note: ExplorationNote):
        """显示复制笔记对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("复制探索笔记")
        dialog.geometry("520x480")  # 增加高度
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)

        # 居中
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 480) // 2
        dialog.geometry(f"+{x}+{y}")

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(2, weight=1)

        title_label = ctk.CTkLabel(
            content,
            text="📋 复制探索笔记",
            font=ctk.CTkFont(family="Microsoft YaHei", size=20, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.grid(row=0, column=0, sticky="w", pady=(0, 16))

        # 笔记预览
        preview_frame = ctk.CTkFrame(content, fg_color=ThemeConfig.BG_TERTIARY, corner_radius=10)
        preview_frame.grid(row=1, column=0, sticky="ew", pady=(0, 16))

        preview_label = ctk.CTkLabel(
            preview_frame,
            text=f"'{note.content[:100]}{'...' if len(note.content) > 100 else ''}'",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=ThemeConfig.TEXT_MUTED,
            wraplength=460,
            justify="left"
        )
        preview_label.pack(padx=16, pady=12)

        # 目标选择
        target_frame = ctk.CTkFrame(content, fg_color="transparent")
        target_frame.grid(row=2, column=0, sticky="nsew")

        target_label = ctk.CTkLabel(
            target_frame,
            text="选择目标任务",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        target_label.pack(anchor="w", pady=(0, 12))

        # 初始化目标任务ID变量（必须在使用前定义）
        copy_target_task_id = ctk.StringVar(value="")

        # 任务列表（排除当前任务）
        tasks = [t for t in self.db.get_all_tasks() if t.id != current_task.id]

        # 任务列表滚动容器
        scrollable = ctk.CTkScrollableFrame(
            target_frame,
            fg_color=ThemeConfig.BG_TERTIARY,
            corner_radius=10,
            height=140,
            width=460
        )
        scrollable.pack(fill="both", expand=True, pady=(0, 8))

        # 选择状态标签（放在scrollable之后）
        selected_label = ctk.CTkLabel(
            content,
            text="已选择：无",
            font=ctk.CTkFont(family="Microsoft YaHei", size=12),
            text_color=ThemeConfig.TEXT_MUTED
        )
        selected_label.grid(row=3, column=0, sticky="w", pady=(4, 0))

        def select_target(task: Task):
            copy_target_task_id.set(task.id)
            selected_label.configure(text=f"已选择：{task.title}")

        if tasks:
            for task in tasks:
                btn = ctk.CTkButton(
                    scrollable,
                    text=f"📝 {task.title}",
                    font=ctk.CTkFont(family="Microsoft YaHei", size=12),
                    text_color=ThemeConfig.TEXT_PRIMARY,
                    fg_color=ThemeConfig.BG_HOVER,
                    hover_color=ThemeConfig.ACCENT_PLANNING,
                    height=32,
                    corner_radius=8,
                    command=lambda t=task: select_target(t)
                )
                btn.pack(fill="x", padx=12, pady=6)
        else:
            empty_label = ctk.CTkLabel(
                scrollable,
                text="暂无可复制的目标任务",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                text_color=ThemeConfig.TEXT_MUTED
            )
            empty_label.pack(pady=30)

        # 按钮
        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.grid(row=4, column=0, sticky="ew", pady=(20, 0))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def copy():
            if not copy_target_task_id.get():
                from tkinter import messagebox
                messagebox.showwarning("提示", "请选择目标任务")
                return

            new_note = self.db.copy_exploration_note(current_task.id, copy_target_task_id.get(), note.id)

            if new_note:
                dialog.destroy()
                self._refresh_task_list()

                # 仍然留在当前任务，只是刷新
                updated_task = self.db.get_task(current_task.id)
                if updated_task:
                    self._select_task(updated_task)

        copy_btn = ctk.CTkButton(
            btn_frame,
            text="复制",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_PLANNING,
            hover_color="#4A90D9",
            height=38,
            corner_radius=10,
            command=copy
        )
        copy_btn.pack(side="right", fill="x", expand=True)
    
    # ==================== 操作方法 ====================
    
    def _toggle_task_mode(self, task: Task):
        """切换任务模式"""
        to_exploring = task.mode == TaskMode.PLANNING
        self.db.switch_task_mode(task.id, to_exploring)
        updated_task = self.db.get_task(task.id)
        if updated_task:
            self._refresh_task_list()
            self._select_task(updated_task)
        self._refresh_tracker_if_visible()
    
    def _toggle_subtask(self, task: Task, subtask: SubTask, completed: bool):
        """切换子任务状态"""
        if completed:
            self.db.complete_subtask(task.id, subtask.id)
        else:
            self.db.update_subtask(task.id, subtask.id, status=TaskStatus.PENDING, completed_at=None)
        
        updated_task = self.db.get_task(task.id)
        if updated_task:
            self._refresh_task_list()
            self._show_task_detail(updated_task)
        self._refresh_tracker_if_visible()

    def _quick_complete_subtask(self, task: Task, subtask: SubTask):
        """快速完成子任务"""
        self.db.complete_subtask(task.id, subtask.id)
        updated_task = self.db.get_task(task.id)
        if updated_task:
            self._refresh_task_list()
            self._show_task_detail(updated_task)
        self._refresh_tracker_if_visible()
    
    def _delete_task(self, task: Task):
        """删除任务"""
        if messagebox.askyesno("确认删除", f"确定要删除任务 \"{task.title}\" 吗？"):
            self.db.delete_task(task.id)
            self.selected_task = None
            self._refresh_task_list()
            self._show_welcome_screen()
            self._refresh_tracker_if_visible()
    
    def _delete_subtask(self, task: Task, subtask: SubTask):
        """删除子任务"""
        self.db.delete_subtask(task.id, subtask.id)
        updated_task = self.db.get_task(task.id)
        if updated_task:
            self._show_task_detail(updated_task)
            self._refresh_tracker_if_visible()
    
    def _delete_note(self, task: Task, note: ExplorationNote):
        """删除笔记"""
        confirm = messagebox.askyesno(
            "确认删除",
            f"确定要删除这条笔记吗?\n\n'{note.content[:100]}{'...' if len(note.content) > 100 else ''}'"
        )
        if not confirm:
            return
        self.db.delete_exploration_note(task.id, note.id)
        updated_task = self.db.get_task(task.id)
        if updated_task:
            self._show_task_detail(updated_task)

    # ==================== 任务拖拽排序 ====================

    def _on_task_drag_start(self, event, card, task, index):
        """开始拖拽任务"""
        if not self._is_manual_sort_mode() or self._drag_data.get("animating"):
            return

        self._drag_data["dragging"] = True
        self._drag_data["widget"] = card
        self._drag_data["task"] = task
        self._drag_data["start_y"] = event.y_root
        self._drag_data["start_x"] = event.x_root
        self._drag_data["original_index"] = index
        self._drag_data["current_index"] = index
        self._drag_data["moved"] = False
        self._drag_data["drag_threshold"] = 3

        self._drag_data["card_positions"] = []
        for i, c in enumerate(self._task_cards):
            self._drag_data["card_positions"].append({
                "card": c,
                "original_y": c.winfo_y(),
                "height": c.winfo_height(),
                "index": i
            })

    def _on_task_drag_motion(self, event, card):
        """拖拽任务移动中"""
        if not self._drag_data["dragging"] or self._drag_data.get("animating"):
            return

        dy = abs(event.y_root - self._drag_data["start_y"])
        dx = abs(event.x_root - self._drag_data["start_x"])

        if not self._drag_data["moved"] and (dy > self._drag_data["drag_threshold"] or dx > self._drag_data["drag_threshold"]):
            self._drag_data["moved"] = True
            card.configure(
                border_color=ThemeConfig.ACCENT_WARNING,
                border_width=3,
                fg_color="#2d333b"
            )
            card.lift()
            for other_card in self._task_cards:
                if other_card != card:
                    other_card.configure(fg_color="#14181e")

        if not self._drag_data["moved"]:
            return

        try:
            mouse_y = event.y_root
            current_index = self._drag_data["current_index"]
            original_index = self._drag_data["original_index"]
            new_index = current_index

            for i, pos_data in enumerate(self._drag_data["card_positions"]):
                if i == original_index:
                    continue
                other_card = pos_data["card"]
                card_top = other_card.winfo_rooty()
                card_height = pos_data["height"]
                card_center = card_top + card_height / 2

                if mouse_y < card_center and i < current_index:
                    new_index = i
                    break
                if mouse_y > card_center and i > current_index:
                    new_index = i

            if new_index != current_index:
                self._animate_card_swap(current_index, new_index, original_index)
                self._drag_data["current_index"] = new_index
        except Exception:
            pass

    def _animate_card_swap(self, from_index, to_index, dragged_index):
        """动画交换卡片位置"""
        if from_index == to_index:
            return

        dragged_card = self._task_cards[dragged_index]
        dragged_height = dragged_card.winfo_height() + 12

        for i, card in enumerate(self._task_cards):
            if i == dragged_index:
                continue
            original_pos = i
            visual_pos = i
            if to_index <= i < from_index and i < dragged_index:
                visual_pos = i + 1
            elif from_index < i <= to_index and i > dragged_index:
                visual_pos = i - 1
            elif to_index < dragged_index and i >= to_index and i < dragged_index:
                visual_pos = i + 1
            elif to_index > dragged_index and i > dragged_index and i <= to_index:
                visual_pos = i - 1

            offset = (visual_pos - original_pos) * dragged_height
            self._smooth_move_card(card, offset)

    def _smooth_move_card(self, card, offset):
        """平滑移动卡片"""
        try:
            if not hasattr(card, '_original_pady'):
                card._original_pady = 6

            target_top_pady = card._original_pady + offset * 0.15
            target_bottom_pady = card._original_pady - offset * 0.05
            target_top_pady = max(-20, min(40, target_top_pady))
            target_bottom_pady = max(2, min(20, target_bottom_pady))

            def ease_animation(step=0, total_steps=4):
                if step <= total_steps:
                    progress = step / total_steps
                    eased = 1 - (1 - progress) ** 2

                    current_top = card._original_pady + (target_top_pady - card._original_pady) * eased
                    current_bottom = card._original_pady + (target_bottom_pady - card._original_pady) * eased
                    try:
                        card.pack_configure(pady=(current_top, current_bottom))
                    except Exception:
                        pass
                    if step < total_steps:
                        self.after(12, lambda: ease_animation(step + 1, total_steps))

            ease_animation()
        except Exception:
            pass

    def _on_task_drag_end(self, event, task):
        """结束拖拽任务"""
        if not self._drag_data["dragging"]:
            return

        card = self._drag_data["widget"]
        original_index = self._drag_data["original_index"]
        current_index = self._drag_data.get("current_index", original_index)
        moved = self._drag_data.get("moved", False)

        self._drag_data["dragging"] = False
        self._drag_data["widget"] = None
        self._drag_data["task"] = None
        self._drag_data["moved"] = False
        self._drag_data["card_positions"] = []

        for other_card in self._task_cards:
            if hasattr(other_card, '_task'):
                other_card.configure(fg_color=ThemeConfig.BG_TERTIARY)
                accent = other_card._accent_color
                is_selected = other_card._is_selected
                other_card.configure(
                    border_color=accent if is_selected else ThemeConfig.BORDER_DEFAULT,
                    border_width=2
                )
                other_card.pack_configure(pady=6)

        if not moved:
            self._select_task(task)
            return

        if current_index != original_index:
            self._drag_data["animating"] = True
            if current_index < original_index:
                for _ in range(original_index - current_index):
                    self.db.move_task(task.id, -1)
            else:
                for _ in range(current_index - original_index):
                    self.db.move_task(task.id, 1)
            self.after(50, lambda: self._finish_task_drag(task))
        else:
            self._refresh_task_list()

    def _finish_task_drag(self, task):
        """完成拖拽后的刷新"""
        self._drag_data["animating"] = False
        self._refresh_task_list()
        if self.selected_task and self.selected_task.id == task.id:
            self._show_task_detail(task)

    # ==================== 子任务拖拽排序 ====================

    def _on_subtask_drag_start(self, event, item, task, subtask, index):
        """开始拖拽子任务"""
        if self._drag_data.get("animating"):
            return

        self._drag_data["dragging"] = True
        self._drag_data["widget"] = item
        self._drag_data["task"] = task
        self._drag_data["subtask"] = subtask
        self._drag_data["start_y"] = event.y_root
        self._drag_data["start_x"] = event.x_root
        self._drag_data["original_index"] = index
        self._drag_data["current_index"] = index
        self._drag_data["moved"] = False
        self._drag_data["drag_threshold"] = 3
        self._drag_data["is_subtask"] = True

        self._drag_data["subtask_positions"] = []
        for i, item_data in enumerate(self._subtask_items):
            widget = item_data["widget"]
            self._drag_data["subtask_positions"].append({
                "widget": widget,
                "original_y": widget.winfo_y(),
                "height": widget.winfo_height(),
                "index": i
            })

    def _on_subtask_drag_motion(self, event, item, parent_frame):
        """拖拽子任务移动中"""
        if not self._drag_data["dragging"] or not self._drag_data.get("is_subtask"):
            return
        if self._drag_data.get("animating"):
            return

        dy = abs(event.y_root - self._drag_data["start_y"])
        dx = abs(event.x_root - self._drag_data["start_x"])

        if not self._drag_data["moved"] and (dy > self._drag_data["drag_threshold"] or dx > self._drag_data["drag_threshold"]):
            self._drag_data["moved"] = True
            item.configure(
                border_color=ThemeConfig.ACCENT_WARNING,
                border_width=2,
                fg_color="#2d333b"
            )
            item.lift()
            for other_item in self._subtask_items:
                if other_item["widget"] != item:
                    other_item["widget"].configure(fg_color="#14181e")

        if not self._drag_data["moved"]:
            return

        try:
            mouse_y = event.y_root
            current_index = self._drag_data["current_index"]
            original_index = self._drag_data["original_index"]
            new_index = current_index

            for i, pos_data in enumerate(self._drag_data.get("subtask_positions", [])):
                if i == original_index:
                    continue
                widget = pos_data["widget"]
                widget_top = widget.winfo_rooty()
                widget_height = pos_data["height"]
                widget_center = widget_top + widget_height / 2

                if mouse_y < widget_center and i < current_index:
                    new_index = i
                    break
                if mouse_y > widget_center and i > current_index:
                    new_index = i

            if new_index != current_index:
                self._animate_subtask_swap(current_index, new_index, original_index)
                self._drag_data["current_index"] = new_index
        except Exception:
            pass

    def _animate_subtask_swap(self, from_index, to_index, dragged_index):
        """动画交换子任务位置"""
        if from_index == to_index or not self._subtask_items:
            return

        dragged_widget = self._subtask_items[dragged_index]["widget"]
        dragged_height = dragged_widget.winfo_height() + 8

        for i, item_data in enumerate(self._subtask_items):
            if i == dragged_index:
                continue
            widget = item_data["widget"]
            original_pos = i
            visual_pos = i
            if to_index < dragged_index and i >= to_index and i < dragged_index:
                visual_pos = i + 1
            elif to_index > dragged_index and i > dragged_index and i <= to_index:
                visual_pos = i - 1
            offset = (visual_pos - original_pos) * dragged_height
            self._smooth_move_subtask(widget, offset)

    def _smooth_move_subtask(self, widget, offset):
        """平滑移动子任务项"""
        try:
            if not hasattr(widget, '_original_pady'):
                widget._original_pady = 4

            target_top = widget._original_pady + offset * 0.12
            target_bottom = widget._original_pady - offset * 0.04
            target_top = max(-15, min(30, target_top))
            target_bottom = max(2, min(15, target_bottom))

            def ease_animation(step=0, total_steps=4):
                if step <= total_steps:
                    progress = step / total_steps
                    eased = 1 - (1 - progress) ** 2
                    current_top = widget._original_pady + (target_top - widget._original_pady) * eased
                    current_bottom = widget._original_pady + (target_bottom - widget._original_pady) * eased
                    try:
                        widget.pack_configure(pady=(current_top, current_bottom))
                    except Exception:
                        pass
                    if step < total_steps:
                        self.after(12, lambda: ease_animation(step + 1, total_steps))

            ease_animation()
        except Exception:
            pass

    def _on_subtask_drag_end(self, event, subtask):
        """结束拖拽子任务"""
        if not self._drag_data["dragging"] or not self._drag_data.get("is_subtask"):
            return

        task = self._drag_data["task"]
        original_index = self._drag_data["original_index"]
        current_index = self._drag_data.get("current_index", original_index)
        moved = self._drag_data.get("moved", False)

        self._drag_data["dragging"] = False
        self._drag_data["widget"] = None
        self._drag_data["task"] = None
        self._drag_data["subtask"] = None
        self._drag_data["is_subtask"] = False
        self._drag_data["moved"] = False
        self._drag_data["subtask_positions"] = []

        for other_item in self._subtask_items:
            is_completed = other_item["subtask"].status == TaskStatus.COMPLETED
            other_item["widget"].configure(
                fg_color=ThemeConfig.BG_TERTIARY,
                border_color=ThemeConfig.ACCENT_SUCCESS if is_completed else ThemeConfig.BORDER_DEFAULT,
                border_width=1
            )
            other_item["widget"].pack_configure(pady=4)

        if not moved:
            return

        if current_index != original_index:
            self._drag_data["animating"] = True
            if current_index < original_index:
                for _ in range(original_index - current_index):
                    self.db.move_subtask(task.id, subtask.id, -1)
            else:
                for _ in range(current_index - original_index):
                    self.db.move_subtask(task.id, subtask.id, 1)
            self.after(50, lambda: self._finish_subtask_drag(task))

    def _finish_subtask_drag(self, task):
        """完成子任务拖拽后的刷新"""
        self._drag_data["animating"] = False
        updated_task = self.db.get_task(task.id)
        if updated_task:
            self._show_task_detail(updated_task)

    def _edit_note_dialog(self, task: Task, note: ExplorationNote):
        """编辑探索笔记对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("编辑探索笔记")
        dialog.geometry("520x420")
        dialog.transient(self)
        dialog.grab_set()
        dialog.configure(fg_color=ThemeConfig.BG_SECONDARY)

        # 居中
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 520) // 2
        y = self.winfo_y() + (self.winfo_height() - 420) // 2
        dialog.geometry(f"+{x}+{y}")

        content = ctk.CTkFrame(dialog, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=24, pady=24)

        title_label = ctk.CTkLabel(
            content,
            text="✏️ 编辑探索笔记",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(anchor="w", pady=(0, 16))

        # 探索内容
        content_label = ctk.CTkLabel(
            content,
            text="你尝试了什么？发现了什么？",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        content_label.pack(anchor="w", pady=(0, 6))

        content_entry = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            height=100,
            corner_radius=10
        )
        content_entry.pack(fill="x", pady=(0, 16))
        content_entry.insert("1.0", note.content)
        content_entry.focus()

        # 洞察
        insight_label = ctk.CTkLabel(
            content,
            text="获得的洞察/启发（可选）",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_SECONDARY
        )
        insight_label.pack(anchor="w", pady=(0, 6))

        insight_entry = ctk.CTkEntry(
            content,
            placeholder_text="这次尝试给你带来了什么启发？",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            height=40,
            corner_radius=10
        )
        insight_entry.pack(fill="x", pady=(0, 12))
        insight_entry.insert(0, note.insight)

        # 突破性发现
        breakthrough_var = ctk.BooleanVar(value=note.is_breakthrough)
        breakthrough_cb = ctk.CTkCheckBox(
            content,
            text="⭐ 这是一个突破性发现！",
            variable=breakthrough_var,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.ACCENT_WARNING,
            fg_color=ThemeConfig.ACCENT_WARNING,
            hover_color=ThemeConfig.ACCENT_WARNING
        )
        breakthrough_cb.pack(anchor="w", pady=(0, 20))

        btn_frame = ctk.CTkFrame(content, fg_color="transparent")
        btn_frame.pack(fill="x")

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="取消",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_SECONDARY,
            height=38,
            corner_radius=10,
            command=dialog.destroy
        )
        cancel_btn.pack(side="left", fill="x", expand=True, padx=(0, 8))

        def save():
            content_text = content_entry.get("1.0", "end-1c").strip()
            if content_text:
                self.db.update_exploration_note(
                    task.id,
                    note.id,
                    content=content_text,
                    insight=insight_entry.get().strip(),
                    is_breakthrough=breakthrough_var.get()
                )
                dialog.destroy()
                updated_task = self.db.get_task(task.id)
                if updated_task:
                    self._show_task_detail(updated_task)

        save_btn = ctk.CTkButton(
            btn_frame,
            text="保存",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_PLANNING,
            hover_color="#4A90D9",
            height=38,
            corner_radius=10,
            command=save
        )
        save_btn.pack(side="right", fill="x", expand=True)

    # ==================== 探索笔记拖拽排序 ====================

    def _on_note_drag_start(self, event, item, task, note, index):
        """开始拖拽探索笔记"""
        if not self._is_note_manual_sort_mode() or self._drag_data.get("animating"):
            return
        self._drag_data["dragging"] = True
        self._drag_data["widget"] = item
        self._drag_data["task"] = task
        self._drag_data["note"] = note
        self._drag_data["start_y"] = event.y_root
        self._drag_data["start_x"] = event.x_root
        self._drag_data["original_index"] = index
        self._drag_data["current_index"] = index
        self._drag_data["moved"] = False
        self._drag_data["drag_threshold"] = 3
        self._drag_data["note_positions"] = []
        for i, item_data in enumerate(self._note_items):
            widget = item_data["widget"]
            self._drag_data["note_positions"].append({
                "widget": widget,
                "height": widget.winfo_height(),
                "index": i
            })

    def _on_note_drag_motion(self, event, item):
        """拖拽探索笔记移动中"""
        if not self._drag_data["dragging"] or self._drag_data.get("animating"):
            return
        dy = abs(event.y_root - self._drag_data["start_y"])
        dx = abs(event.x_root - self._drag_data["start_x"])
        if not self._drag_data["moved"] and (dy > self._drag_data["drag_threshold"] or dx > self._drag_data["drag_threshold"]):
            self._drag_data["moved"] = True
            item.configure(border_color=ThemeConfig.ACCENT_WARNING, border_width=2, fg_color="#2d333b")
            item.lift()
            for other_item in self._note_items:
                if other_item["widget"] != item:
                    other_item["widget"].configure(fg_color="#14181e")
        if not self._drag_data["moved"]:
            return
        try:
            mouse_y = event.y_root
            current_index = self._drag_data["current_index"]
            original_index = self._drag_data["original_index"]
            new_index = current_index
            for i, pos_data in enumerate(self._drag_data.get("note_positions", [])):
                if i == original_index:
                    continue
                widget = pos_data["widget"]
                widget_top = widget.winfo_rooty()
                widget_center = widget_top + pos_data["height"] / 2
                if mouse_y < widget_center and i < current_index:
                    new_index = i
                    break
                if mouse_y > widget_center and i > current_index:
                    new_index = i
            if new_index != current_index:
                self._drag_data["current_index"] = new_index
        except Exception:
            pass

    def _on_note_drag_end(self, event, note):
        """结束拖拽探索笔记"""
        if not self._drag_data["dragging"]:
            return
        task = self._drag_data["task"]
        original_index = self._drag_data["original_index"]
        current_index = self._drag_data.get("current_index", original_index)
        moved = self._drag_data.get("moved", False)
        self._drag_data["dragging"] = False
        self._drag_data["widget"] = None
        self._drag_data["task"] = None
        self._drag_data["note"] = None
        self._drag_data["moved"] = False
        self._drag_data["note_positions"] = []
        for other_item in self._note_items:
            other_item["widget"].configure(
                fg_color=ThemeConfig.BG_TERTIARY,
                border_color=ThemeConfig.BORDER_DEFAULT if not other_item["note"].is_breakthrough else ThemeConfig.ACCENT_WARNING,
                border_width=2 if other_item["note"].is_breakthrough else 1
            )
        if not moved:
            return
        if current_index != original_index:
            self._drag_data["animating"] = True
            if current_index < original_index:
                for _ in range(original_index - current_index):
                    self.db.move_exploration_note_order(task.id, note.id, -1)
            else:
                for _ in range(current_index - original_index):
                    self.db.move_exploration_note_order(task.id, note.id, 1)
            self.after(50, lambda: self._finish_note_drag(task))

    def _finish_note_drag(self, task):
        """完成探索笔记拖拽后的刷新"""
        self._drag_data["animating"] = False
        updated_task = self.db.get_task(task.id)
        if updated_task:
            self._show_task_detail(updated_task)

def main():
    """程序入口"""
    app = ResearchTerminal()
    app.mainloop()


if __name__ == "__main__":
    main()
