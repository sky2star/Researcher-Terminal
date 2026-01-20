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
from tkinter import messagebox
from datetime import datetime
from typing import Optional, Callable

from models import Task, SubTask, ExplorationNote, TaskStatus, TaskMode, TaskKnowledge
from database import Database


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


# ==================== 悬浮任务追踪窗口 ====================
class TaskTrackerWindow(ctk.CTkToplevel):
    """悬浮任务追踪窗口 - 类似游戏任务提醒"""
    
    def __init__(self, parent, db: 'Database'):
        super().__init__(parent)
        
        self.db = db
        self.parent = parent
        self._drag_data = {"x": 0, "y": 0}
        
        # 窗口配置
        self.title("📌 任务追踪")
        self.geometry("320x400+50+100")  # 默认放在屏幕左侧
        self.minsize(280, 200)
        self.attributes("-topmost", True)  # 始终置顶
        self.attributes("-alpha", 0.95)    # 轻微透明
        self.overrideredirect(False)       # 保留标题栏以便拖动
        
        # 配置颜色
        self.configure(fg_color=ThemeConfig.BG_PRIMARY)
        
        # 创建界面
        self._create_ui()
        self._refresh_tracker()
        
        # 绑定关闭事件
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_ui(self):
        """创建追踪窗口界面"""
        # 头部
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
        
        # 刷新按钮
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
        
        # 最小化按钮
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
        
        # 内容区域（可折叠）
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
        # 清空现有内容
        for widget in self.content_frame.winfo_children():
            widget.destroy()
        
        # 获取进行中的任务
        tasks = self.db.get_all_tasks()
        
        # 筛选活跃任务（非完成状态，或者虽然标记完成但仍有未完成子任务）
        active_tasks = []
        for t in tasks:
            if t.status in [TaskStatus.IN_PROGRESS, TaskStatus.EXPLORING, TaskStatus.PENDING]:
                active_tasks.append(t)
            elif t.status == TaskStatus.COMPLETED:
                # 检查是否有未完成的子任务（状态异常情况）
                has_incomplete = any(st.status != TaskStatus.COMPLETED for st in t.subtasks)
                if has_incomplete:
                    # 自动修复状态
                    t.status = TaskStatus.IN_PROGRESS
                    t.completed_at = None
                    self.db._save()
                    active_tasks.append(t)
        
        # 按状态排序：进行中 > 探索中 > 待处理
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
        
        # 显示任务
        for task in active_tasks[:5]:  # 最多显示5个任务
            self._create_task_tracker_item(task)
    
    def _create_task_tracker_item(self, task: Task):
        """创建任务追踪项"""
        # 确定颜色
        if task.mode == TaskMode.EXPLORING:
            accent_color = ThemeConfig.ACCENT_EXPLORING
            mode_icon = "🔍"
        else:
            accent_color = ThemeConfig.ACCENT_PLANNING
            mode_icon = "📊"
        
        # 任务卡片
        card = ctk.CTkFrame(
            self.content_frame,
            fg_color=ThemeConfig.BG_SECONDARY,
            corner_radius=10,
            border_width=1,
            border_color=accent_color
        )
        card.pack(fill="x", pady=4)
        
        # 任务标题行
        title_frame = ctk.CTkFrame(card, fg_color="transparent")
        title_frame.pack(fill="x", padx=10, pady=(10, 6))
        
        # 模式图标
        mode_label = ctk.CTkLabel(
            title_frame,
            text=mode_icon,
            font=ctk.CTkFont(size=14)
        )
        mode_label.pack(side="left", padx=(0, 6))
        
        # 任务标题
        title_text = task.title[:20] + "..." if len(task.title) > 20 else task.title
        title_label = ctk.CTkLabel(
            title_frame,
            text=title_text,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(side="left", fill="x", expand=True)
        
        # 显示下一步/当前状态
        if task.mode == TaskMode.PLANNING:
            if not task.subtasks:
                # 规划模式但没有子任务
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
                # 规划模式：显示下一个未完成的子任务
                next_subtask = None
                for st in sorted(task.subtasks, key=lambda x: x.order):
                    if st.status != TaskStatus.COMPLETED:
                        next_subtask = st
                        break
                
                if next_subtask:
                    # 下一步提示
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
                    
                    # 快速完成按钮
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
                    # 所有子任务都完成了
                    done_frame = ctk.CTkFrame(card, fg_color=ThemeConfig.BG_TERTIARY, corner_radius=6)
                    done_frame.pack(fill="x", padx=10, pady=(0, 6))
                    
                    done_label = ctk.CTkLabel(
                        done_frame,
                        text="✅ 所有步骤已完成！",
                        font=ctk.CTkFont(family="Microsoft YaHei", size=11),
                        text_color=ThemeConfig.ACCENT_SUCCESS
                    )
                    done_label.pack(anchor="w", padx=8, pady=8)
                
                # 进度条
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
            # 探索模式：显示探索状态
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
                # 显示最新的笔记摘要
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
        # 通知主窗口刷新
        if hasattr(self.parent, '_refresh_task_list'):
            self.parent._refresh_task_list()
            if self.parent.selected_task and self.parent.selected_task.id == task.id:
                updated_task = self.db.get_task(task.id)
                if updated_task:
                    self.parent._show_task_detail(updated_task)
    
    def _on_close(self):
        """关闭窗口"""
        self.withdraw()  # 隐藏而不是销毁
        if hasattr(self.parent, 'tracker_window_visible'):
            self.parent.tracker_window_visible = False


class ResearchTerminal(ctk.CTk):
    """科研工作者终端主窗口"""
    
    def __init__(self):
        super().__init__()
        
        self.db = Database()
        self.selected_task: Optional[Task] = None
        self.tracker_window: Optional[TaskTrackerWindow] = None
        self.tracker_window_visible = False
        
        # 拖拽排序相关状态
        self._drag_data = {
            "dragging": False,
            "widget": None,
            "task": None,
            "subtask": None,
            "start_y": 0,
            "original_index": 0,
            "items": [],
            "drop_indicator": None,
            "target_index": None,
            "ghost": None,  # 拖拽时的幽灵副本
            "animating": False,
            "card_positions": [],  # 记录每个卡片的原始位置
        }
        self._task_cards = []  # 存储任务卡片引用
        self._subtask_items = []  # 存储子任务项引用
        self._animation_speed = 150  # 动画速度（毫秒）
        
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
        
        # 拖拽提示
        drag_hint = ctk.CTkLabel(
            title_frame,
            text="(拖拽排序)",
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_MUTED
        )
        drag_hint.pack(side="left", padx=(8, 0))
        
        # 任务追踪悬浮窗按钮
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
        
        # 追踪按钮提示
        tracker_tip = ctk.CTkLabel(
            header,
            text="追踪",
            font=ctk.CTkFont(family="Microsoft YaHei", size=10),
            text_color=ThemeConfig.TEXT_MUTED
        )
        tracker_tip.pack(side="right", padx=(0, 4))
        
        # 搜索框
        search_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        search_frame.pack(fill="x", padx=20, pady=(0, 12))
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            placeholder_text="🔍 搜索任务...",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            text_color=ThemeConfig.TEXT_PRIMARY,
            placeholder_text_color=ThemeConfig.TEXT_MUTED,
            height=40,
            corner_radius=10
        )
        self.search_entry.pack(fill="x")
        self.search_entry.bind("<KeyRelease>", self._on_search)
        
        # 筛选按钮组
        filter_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        filter_frame.pack(fill="x", padx=20, pady=(0, 12))
        
        self.filter_var = ctk.StringVar(value="all")
        
        filters = [
            ("全部", "all"),
            ("规划中", "planning"),
            ("探索中", "exploring"),
            ("已完成", "completed")
        ]
        
        for text, value in filters:
            btn = ctk.CTkRadioButton(
                filter_frame,
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
        
        card = ctk.CTkFrame(
            self.task_list_frame,
            fg_color=ThemeConfig.BG_TERTIARY,
            corner_radius=12,
            border_width=2,
            border_color=accent_color if self.selected_task and self.selected_task.id == task.id else ThemeConfig.BORDER_DEFAULT,
            cursor="hand2"
        )
        card.pack(fill="x", pady=6, padx=4)
        
        # 存储卡片信息用于拖拽
        card._task = task
        card._index = index
        card._accent_color = accent_color
        card._is_selected = self.selected_task and self.selected_task.id == task.id
        self._task_cards.append(card)
        
        # 绑定拖拽事件到整个卡片
        card.bind("<Button-1>", lambda e, c=card, t=task, i=index: self._on_task_drag_start(e, c, t, i))
        card.bind("<B1-Motion>", lambda e, c=card: self._on_task_drag_motion(e, c))
        card.bind("<ButtonRelease-1>", lambda e, t=task: self._on_task_drag_end(e, t))
        
        # 内容区域
        content = ctk.CTkFrame(card, fg_color="transparent", cursor="hand2")
        content.pack(fill="x", padx=16, pady=12)
        content.bind("<Button-1>", lambda e, c=card, t=task, i=index: self._on_task_drag_start(e, c, t, i))
        content.bind("<B1-Motion>", lambda e, c=card: self._on_task_drag_motion(e, c))
        content.bind("<ButtonRelease-1>", lambda e, t=task: self._on_task_drag_end(e, t))
        
        # 辅助函数：绑定拖拽事件
        def bind_drag_events(widget):
            widget.bind("<Button-1>", lambda e, c=card, t=task, i=index: self._on_task_drag_start(e, c, t, i))
            widget.bind("<B1-Motion>", lambda e, c=card: self._on_task_drag_motion(e, c))
            widget.bind("<ButtonRelease-1>", lambda e, t=task: self._on_task_drag_end(e, t))
        
        # 第一行：标题和模式标签
        row1 = ctk.CTkFrame(content, fg_color="transparent", cursor="hand2")
        row1.pack(fill="x")
        bind_drag_events(row1)
        
        # 模式标签
        mode_icon = "🔍" if task.mode == TaskMode.EXPLORING else "📊"
        mode_label = ctk.CTkLabel(
            row1,
            text=mode_icon,
            font=ctk.CTkFont(size=14),
            cursor="hand2"
        )
        mode_label.pack(side="left", padx=(0, 8))
        bind_drag_events(mode_label)
        
        # 标题
        title_label = ctk.CTkLabel(
            row1,
            text=task.title[:25] + ("..." if len(task.title) > 25 else ""),
            font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY,
            anchor="w",
            cursor="hand2"
        )
        title_label.pack(side="left", fill="x", expand=True)
        bind_drag_events(title_label)
        
        # 第二行：状态和进度
        row2 = ctk.CTkFrame(content, fg_color="transparent", cursor="hand2")
        row2.pack(fill="x", pady=(8, 0))
        bind_drag_events(row2)
        
        # 状态
        status_label = ctk.CTkLabel(
            row2,
            text=task.status.value,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=status_colors.get(task.status, ThemeConfig.TEXT_SECONDARY),
            cursor="hand2"
        )
        status_label.pack(side="left")
        bind_drag_events(status_label)
        
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
                cursor="hand2"
            )
            notes_label.pack(side="right")
            bind_drag_events(notes_label)
        
        return card
    
    def _refresh_task_list(self):
        """刷新任务列表"""
        # 清空现有列表和卡片引用
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
        
        # 应用搜索
        search_text = self.search_entry.get().strip().lower()
        if search_text:
            tasks = [t for t in tasks if search_text in t.title.lower() or search_text in t.description.lower()]
        
        # 注意：不再自动排序，保留用户自定义的顺序
        # 如果需要按时间排序，可以取消下面的注释
        # tasks.sort(key=lambda t: t.updated_at, reverse=True)
        
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
    
    def _on_search(self, event=None):
        """搜索事件"""
        self._refresh_task_list()
    
    def _select_task(self, task: Task):
        """选择任务"""
        self.selected_task = task
        self._refresh_task_list()  # 刷新高亮状态
        self._show_task_detail(task)
    
    def _show_task_detail(self, task: Task):
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
        
        # 切换模式按钮
        if task.status != TaskStatus.COMPLETED:
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
        edit_title_btn = ctk.CTkButton(
            title_frame,
            text="✏️",
            font=ctk.CTkFont(size=14),
            fg_color="transparent",
            hover_color=ThemeConfig.BG_HOVER,
            width=32,
            height=32,
            command=lambda: self._edit_task_title(task)
        )
        edit_title_btn.pack(side="right")
        
        # 描述区域
        desc_frame = ctk.CTkFrame(scroll_container, fg_color="transparent")
        desc_frame.pack(fill="x", pady=(0, 20))
        
        if task.description:
            desc_label = ctk.CTkLabel(
                desc_frame,
                text=task.description,
                font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                text_color=ThemeConfig.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=660
            )
            desc_label.pack(side="left", fill="x", expand=True)
        else:
            desc_label = ctk.CTkLabel(
                desc_frame,
                text="（暂无描述）",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                text_color=ThemeConfig.TEXT_MUTED,
                anchor="w"
            )
            desc_label.pack(side="left", fill="x", expand=True)
        
        # 编辑描述按钮
        edit_desc_btn = ctk.CTkButton(
            desc_frame,
            text="✏️",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=ThemeConfig.BG_HOVER,
            width=28,
            height=28,
            command=lambda: self._edit_task_description(task)
        )
        edit_desc_btn.pack(side="right")
        
        # 分隔线
        separator = ctk.CTkFrame(scroll_container, fg_color=ThemeConfig.BORDER_DEFAULT, height=1)
        separator.pack(fill="x", pady=(0, 20))
        
        # 根据模式显示不同内容
        if task.mode == TaskMode.PLANNING:
            self._show_planning_content(scroll_container, task)
        else:
            self._show_exploring_content(scroll_container, task)
    
    def _show_planning_content(self, parent, task: Task):
        """显示规划模式内容"""
        # 清空子任务项引用
        self._subtask_items = []
        
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
        if task.subtasks:
            sorted_subtasks = sorted(task.subtasks, key=lambda x: x.order)
            total = len(sorted_subtasks)
            for index, subtask in enumerate(sorted_subtasks):
                self._create_subtask_item(parent, task, subtask, index, total)
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
            
            # 标题行（含操作按钮）
            conclusion_header = ctk.CTkFrame(conclusion_frame, fg_color="transparent")
            conclusion_header.pack(fill="x", padx=16, pady=(12, 8))
            
            conclusion_title = ctk.CTkLabel(
                conclusion_header,
                text="💡 探索结论",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"),
                text_color=ThemeConfig.ACCENT_EXPLORING
            )
            conclusion_title.pack(side="left")
            
            # 删除结论按钮
            delete_conclusion_btn = ctk.CTkButton(
                conclusion_header,
                text="✕",
                font=ctk.CTkFont(size=12),
                fg_color="transparent",
                hover_color=ThemeConfig.ACCENT_DANGER,
                text_color=ThemeConfig.TEXT_MUTED,
                width=24,
                height=24,
                command=lambda: self._delete_conclusion(task)
            )
            delete_conclusion_btn.pack(side="right", padx=2)
            
            # 编辑结论按钮
            edit_conclusion_btn = ctk.CTkButton(
                conclusion_header,
                text="✏️",
                font=ctk.CTkFont(size=11),
                fg_color="transparent",
                hover_color=ThemeConfig.BG_HOVER,
                text_color=ThemeConfig.TEXT_MUTED,
                width=24,
                height=24,
                command=lambda: self._edit_conclusion_dialog(task)
            )
            edit_conclusion_btn.pack(side="right", padx=2)
            
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
    
    def _create_subtask_item(self, parent, task: Task, subtask: SubTask, index: int, total: int):
        """创建子任务项"""
        is_completed = subtask.status == TaskStatus.COMPLETED
        
        item = ctk.CTkFrame(
            parent,
            fg_color=ThemeConfig.BG_TERTIARY,
            corner_radius=10,
            border_width=1,
            border_color=ThemeConfig.ACCENT_SUCCESS if is_completed else ThemeConfig.BORDER_DEFAULT,
            cursor="hand2"
        )
        item.pack(fill="x", pady=4)
        
        # 存储子任务项信息用于拖拽
        self._subtask_items.append({
            "widget": item,
            "task": task,
            "subtask": subtask,
            "index": index
        })
        
        # 绑定拖拽事件到整个 item
        item.bind("<Button-1>", lambda e, it=item, t=task, s=subtask, i=index: self._on_subtask_drag_start(e, it, t, s, i))
        item.bind("<B1-Motion>", lambda e, it=item, p=parent: self._on_subtask_drag_motion(e, it, p))
        item.bind("<ButtonRelease-1>", lambda e, s=subtask: self._on_subtask_drag_end(e, s))
        
        content = ctk.CTkFrame(item, fg_color="transparent", cursor="hand2")
        content.pack(fill="x", padx=12, pady=10)
        
        # 绑定拖拽事件到 content
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
            cursor="hand2"
        )
        title_label.pack(side="left", fill="x", expand=True)
        
        # 绑定拖拽事件到标题
        title_label.bind("<Button-1>", lambda e, it=item, t=task, s=subtask, i=index: self._on_subtask_drag_start(e, it, t, s, i))
        title_label.bind("<B1-Motion>", lambda e, it=item, p=parent: self._on_subtask_drag_motion(e, it, p))
        title_label.bind("<ButtonRelease-1>", lambda e, s=subtask: self._on_subtask_drag_end(e, s))
        
        # 操作按钮区域
        actions_frame = ctk.CTkFrame(content, fg_color="transparent")
        actions_frame.pack(side="right")
        
        # 编辑按钮
        edit_btn = ctk.CTkButton(
            actions_frame,
            text="✏️",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_MUTED,
            width=24,
            height=24,
            command=lambda: self._edit_subtask_dialog(task, subtask)
        )
        edit_btn.pack(side="left", padx=2)
        
        # 删除按钮
        delete_btn = ctk.CTkButton(
            actions_frame,
            text="✕",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=ThemeConfig.ACCENT_DANGER,
            text_color=ThemeConfig.TEXT_MUTED,
            width=24,
            height=24,
            command=lambda: self._delete_subtask(task, subtask)
        )
        delete_btn.pack(side="left", padx=2)
    
    def _show_exploring_content(self, parent, task: Task):
        """显示探索模式内容"""
        # 探索笔记区域
        notes_header = ctk.CTkFrame(parent, fg_color="transparent")
        notes_header.pack(fill="x", pady=(0, 16))
        
        notes_title = ctk.CTkLabel(
            notes_header,
            text="📝 探索笔记",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        notes_title.pack(side="left")
        
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
        add_note_btn.pack(side="right")
        
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
        found_solution_btn.pack(side="right", padx=(0, 8))
        
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
        if task.exploration_notes:
            for note in reversed(task.exploration_notes):  # 最新的在前
                self._create_note_item(parent, task, note)
        else:
            empty_label = ctk.CTkLabel(
                parent,
                text="暂无探索笔记\n记录你的尝试和发现",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                text_color=ThemeConfig.TEXT_MUTED,
                justify="center"
            )
            empty_label.pack(pady=30)
    
    def _create_note_item(self, parent, task: Task, note: ExplorationNote):
        """创建笔记项"""
        border_color = ThemeConfig.ACCENT_WARNING if note.is_breakthrough else ThemeConfig.BORDER_DEFAULT
        
        item = ctk.CTkFrame(
            parent,
            fg_color=ThemeConfig.BG_TERTIARY,
            corner_radius=12,
            border_width=2 if note.is_breakthrough else 1,
            border_color=border_color
        )
        item.pack(fill="x", pady=6)
        
        content = ctk.CTkFrame(item, fg_color="transparent")
        content.pack(fill="x", padx=16, pady=12)
        
        # 头部
        header = ctk.CTkFrame(content, fg_color="transparent")
        header.pack(fill="x")
        
        # 突破标记
        if note.is_breakthrough:
            breakthrough_label = ctk.CTkLabel(
                header,
                text="⭐ 突破性发现",
                font=ctk.CTkFont(family="Microsoft YaHei", size=11, weight="bold"),
                text_color=ThemeConfig.ACCENT_WARNING
            )
            breakthrough_label.pack(side="left", padx=(0, 8))
        
        # 时间
        time_str = note.created_at.strftime("%m-%d %H:%M")
        time_label = ctk.CTkLabel(
            header,
            text=time_str,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=ThemeConfig.TEXT_MUTED
        )
        time_label.pack(side="left")
        
        # 删除按钮
        delete_btn = ctk.CTkButton(
            header,
            text="✕",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            hover_color=ThemeConfig.ACCENT_DANGER,
            text_color=ThemeConfig.TEXT_MUTED,
            width=24,
            height=24,
            command=lambda: self._delete_note(task, note)
        )
        delete_btn.pack(side="right", padx=2)
        
        # 编辑按钮
        edit_note_btn = ctk.CTkButton(
            header,
            text="✏️",
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=ThemeConfig.BG_HOVER,
            text_color=ThemeConfig.TEXT_MUTED,
            width=24,
            height=24,
            command=lambda: self._edit_note_dialog(task, note)
        )
        edit_note_btn.pack(side="right", padx=2)
        
        # 内容
        content_label = ctk.CTkLabel(
            content,
            text=note.content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            text_color=ThemeConfig.TEXT_PRIMARY,
            anchor="w",
            justify="left",
            wraplength=640
        )
        content_label.pack(fill="x", pady=(10, 0), anchor="w")
        
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
                wraplength=620
            )
            insight_label.pack(padx=12, pady=8, anchor="w")
    
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
            self._refresh_tracker_if_visible()
        
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
        
        entry.bind("<Return>", lambda e: save())
    
    def _edit_task_description(self, task: Task):
        """编辑任务描述"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("编辑任务描述")
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
            text="✏️ 编辑任务描述",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(anchor="w", pady=(0, 16))
        
        entry = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            height=140,
            corner_radius=10
        )
        entry.pack(fill="x", pady=(0, 20))
        entry.insert("1.0", task.description)
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
            new_desc = entry.get("1.0", "end-1c").strip()
            self.db.update_task(task.id, description=new_desc)
            dialog.destroy()
            updated_task = self.db.get_task(task.id)
            if updated_task:
                self._refresh_task_list()
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
    
    def _edit_subtask_dialog(self, task: Task, subtask: SubTask):
        """编辑子任务对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("编辑子任务")
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
            text="✏️ 编辑子任务",
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
        entry.insert(0, subtask.title)
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
                self.db.update_subtask(task.id, subtask.id, title=new_title)
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
        
        entry.bind("<Return>", lambda e: save())
    
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
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            border_color=ThemeConfig.BORDER_DEFAULT,
            height=40,
            corner_radius=10
        )
        insight_entry.pack(fill="x", pady=(0, 12))
        insight_entry.insert(0, note.insight or "")
        
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
            text = content_entry.get("1.0", "end-1c").strip()
            if text:
                self.db.update_exploration_note(
                    task.id,
                    note.id,
                    content=text,
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
            fg_color=ThemeConfig.ACCENT_EXPLORING,
            hover_color="#D97A35",
            height=38,
            corner_radius=10,
            command=save
        )
        save_btn.pack(side="right", fill="x", expand=True)
    
    def _edit_conclusion_dialog(self, task: Task):
        """编辑探索结论对话框"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("编辑探索结论")
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
            text="✏️ 编辑探索结论",
            font=ctk.CTkFont(family="Microsoft YaHei", size=18, weight="bold"),
            text_color=ThemeConfig.ACCENT_EXPLORING
        )
        title_label.pack(anchor="w", pady=(0, 16))
        
        entry = ctk.CTkTextbox(
            content,
            font=ctk.CTkFont(family="Microsoft YaHei", size=13),
            fg_color=ThemeConfig.BG_TERTIARY,
            height=140,
            corner_radius=10
        )
        entry.pack(fill="x", pady=(0, 20))
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
            new_conclusion = entry.get("1.0", "end-1c").strip()
            if new_conclusion:
                self.db.set_task_conclusion(task.id, new_conclusion)
                dialog.destroy()
                updated_task = self.db.get_task(task.id)
                if updated_task:
                    self._show_task_detail(updated_task)
        
        save_btn = ctk.CTkButton(
            btn_frame,
            text="保存",
            font=ctk.CTkFont(family="Microsoft YaHei", size=13, weight="bold"),
            fg_color=ThemeConfig.ACCENT_EXPLORING,
            hover_color="#D97A35",
            height=38,
            corner_radius=10,
            command=save
        )
        save_btn.pack(side="right", fill="x", expand=True)
    
    def _delete_conclusion(self, task: Task):
        """删除探索结论"""
        if messagebox.askyesno("确认删除", "确定要删除探索结论吗？"):
            self.db.clear_task_conclusion(task.id)
            updated_task = self.db.get_task(task.id)
            if updated_task:
                self._show_task_detail(updated_task)
    
    def _move_subtask(self, task: Task, subtask: SubTask, direction: int):
        """移动子任务顺序"""
        self.db.move_subtask(task.id, subtask.id, direction)
        updated_task = self.db.get_task(task.id)
        if updated_task:
            self._show_task_detail(updated_task)
    
    # ==================== 操作方法 ====================
    
    def _toggle_task_mode(self, task: Task):
        """切换任务模式"""
        to_exploring = task.mode == TaskMode.PLANNING
        self.db.switch_task_mode(task.id, to_exploring)
        updated_task = self.db.get_task(task.id)
        if updated_task:
            self._refresh_task_list()
            self._select_task(updated_task)
    
    def _toggle_subtask(self, task: Task, subtask: SubTask, completed: bool):
        """切换子任务状态"""
        if completed:
            self.db.complete_subtask(task.id, subtask.id)
        else:
            self.db.update_subtask(task.id, subtask.id, status=TaskStatus.PENDING, completed_at=None)
        
        updated_task = self.db.get_task(task.id)
        if updated_task:
            # 使用 after_idle 延迟刷新，减少UI闪烁
            self.after_idle(lambda: self._smooth_refresh_detail(updated_task))
    
    def _smooth_refresh_detail(self, task: Task):
        """平滑刷新任务详情（减少闪烁）"""
        self._refresh_task_list()
        self._show_task_detail(task)
        self._refresh_tracker_if_visible()
    
    def _move_task(self, task: Task, direction: int):
        """移动任务顺序"""
        self.db.move_task(task.id, direction)
        self._refresh_task_list()
        # 重新选择该任务以刷新排序按钮状态
        updated_task = self.db.get_task(task.id)
        if updated_task:
            self._show_task_detail(updated_task)
    
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
    
    def _delete_note(self, task: Task, note: ExplorationNote):
        """删除笔记"""
        self.db.delete_exploration_note(task.id, note.id)
        updated_task = self.db.get_task(task.id)
        if updated_task:
            self._show_task_detail(updated_task)
    
    # ==================== 任务拖拽排序（高级动画版） ====================
    
    def _on_task_drag_start(self, event, card, task, index):
        """开始拖拽任务"""
        if self._drag_data.get("animating"):
            return
            
        self._drag_data["dragging"] = True
        self._drag_data["widget"] = card
        self._drag_data["task"] = task
        self._drag_data["start_y"] = event.y_root
        self._drag_data["start_x"] = event.x_root
        self._drag_data["original_index"] = index
        self._drag_data["current_index"] = index  # 当前逻辑位置
        self._drag_data["moved"] = False
        self._drag_data["drag_threshold"] = 5
        
        # 记录所有卡片的原始位置和高度
        self._drag_data["card_positions"] = []
        for i, c in enumerate(self._task_cards):
            self._drag_data["card_positions"].append({
                "card": c,
                "original_y": c.winfo_y(),
                "height": c.winfo_height(),
                "index": i
            })
    
    def _on_task_drag_motion(self, event, card):
        """拖拽任务移动中 - 实时预览交换效果"""
        if not self._drag_data["dragging"] or self._drag_data.get("animating"):
            return
        
        dy = abs(event.y_root - self._drag_data["start_y"])
        dx = abs(event.x_root - self._drag_data["start_x"])
        
        if not self._drag_data["moved"] and (dy > self._drag_data["drag_threshold"] or dx > self._drag_data["drag_threshold"]):
            self._drag_data["moved"] = True
            
            # 拖拽效果：高亮边框 + 提升层级 + 轻微放大效果
            card.configure(
                border_color=ThemeConfig.ACCENT_WARNING, 
                border_width=3,
                fg_color="#2d333b"  # 稍微变亮，表示被选中
            )
            card.lift()
            
            # 其他卡片变暗，形成视觉对比
            for other_card in self._task_cards:
                if other_card != card:
                    other_card.configure(fg_color="#14181e")  # 更暗的背景
        
        if not self._drag_data["moved"]:
            return
        
        try:
            mouse_y = event.y_root
            current_index = self._drag_data["current_index"]
            original_index = self._drag_data["original_index"]
            
            # 计算目标位置
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
                elif mouse_y > card_center and i > current_index:
                    new_index = i
            
            # 如果位置发生变化，执行动画交换
            if new_index != current_index:
                self._animate_card_swap(current_index, new_index, original_index)
                self._drag_data["current_index"] = new_index
            
        except Exception:
            pass
    
    def _animate_card_swap(self, from_index, to_index, dragged_index):
        """动画交换卡片位置 - 实时预览效果"""
        if from_index == to_index:
            return
        
        dragged_card = self._task_cards[dragged_index]
        dragged_height = dragged_card.winfo_height() + 12
        
        # 计算每个卡片应该在的位置
        for i, card in enumerate(self._task_cards):
            if i == dragged_index:
                continue
            
            # 计算这个卡片的目标偏移
            original_pos = i
            visual_pos = i
            
            if to_index <= i < from_index and i < dragged_index:
                # 卡片需要向下移动（给拖拽项让位）
                visual_pos = i + 1
            elif from_index < i <= to_index and i > dragged_index:
                # 卡片需要向上移动
                visual_pos = i - 1
            elif to_index < dragged_index and i >= to_index and i < dragged_index:
                visual_pos = i + 1
            elif to_index > dragged_index and i > dragged_index and i <= to_index:
                visual_pos = i - 1
            
            offset = (visual_pos - original_pos) * dragged_height
            self._smooth_move_card(card, offset, i)
    
    def _smooth_move_card(self, card, offset, index):
        """平滑移动卡片 - 使用弹性动画"""
        try:
            # 保存原始间距
            if not hasattr(card, '_original_pady'):
                card._original_pady = 6
            
            # 计算目标间距（模拟位移效果）
            target_top_pady = card._original_pady + offset * 0.15
            target_bottom_pady = card._original_pady - offset * 0.05
            
            # 限制范围
            target_top_pady = max(-20, min(40, target_top_pady))
            target_bottom_pady = max(2, min(20, target_bottom_pady))
            
            # 使用 after 实现平滑过渡
            def ease_animation(step=0, total_steps=4):
                if step <= total_steps:
                    progress = step / total_steps
                    # 缓动函数：ease-out
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
        """结束拖拽任务 - 执行最终交换动画"""
        if not self._drag_data["dragging"]:
            return
        
        card = self._drag_data["widget"]
        original_index = self._drag_data["original_index"]
        current_index = self._drag_data.get("current_index", original_index)
        moved = self._drag_data.get("moved", False)
        
        # 重置拖拽状态
        self._drag_data["dragging"] = False
        self._drag_data["widget"] = None
        self._drag_data["task"] = None
        self._drag_data["moved"] = False
        self._drag_data["card_positions"] = []
        
        # 恢复所有卡片样式
        for other_card in self._task_cards:
            if hasattr(other_card, '_task'):
                other_card.configure(fg_color=ThemeConfig.BG_TERTIARY)
                accent = other_card._accent_color
                is_selected = other_card._is_selected
                other_card.configure(
                    border_color=accent if is_selected else ThemeConfig.BORDER_DEFAULT,
                    border_width=2
                )
                # 恢复默认间距
                other_card.pack_configure(pady=6)
        
        # 如果没有真正移动，视为点击
        if not moved:
            self._select_task(task)
            return
        
        # 执行实际的数据移动
        if current_index != original_index:
            self._drag_data["animating"] = True
            
            # 计算移动方向和次数
            if current_index < original_index:
                for _ in range(original_index - current_index):
                    self.db.move_task(task.id, -1)
            else:
                for _ in range(current_index - original_index):
                    self.db.move_task(task.id, 1)
            
            # 延迟刷新，让动画完成
            self.after(50, lambda: self._finish_task_drag(task))
        else:
            self._refresh_task_list()
    
    def _finish_task_drag(self, task):
        """完成拖拽后的刷新"""
        self._drag_data["animating"] = False
        self._refresh_task_list()
        if self.selected_task and self.selected_task.id == task.id:
            self._show_task_detail(task)
    
    # ==================== 子任务拖拽排序（高级动画版） ====================
    
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
        self._drag_data["drag_threshold"] = 5
        self._drag_data["is_subtask"] = True
        
        # 记录所有子任务项的位置
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
        """拖拽子任务移动中 - 实时预览交换效果"""
        if not self._drag_data["dragging"] or not self._drag_data.get("is_subtask"):
            return
        
        if self._drag_data.get("animating"):
            return
        
        dy = abs(event.y_root - self._drag_data["start_y"])
        dx = abs(event.x_root - self._drag_data["start_x"])
        
        if not self._drag_data["moved"] and (dy > self._drag_data["drag_threshold"] or dx > self._drag_data["drag_threshold"]):
            self._drag_data["moved"] = True
            
            # 高亮被拖拽的项
            item.configure(
                border_color=ThemeConfig.ACCENT_WARNING, 
                border_width=2,
                fg_color="#2d333b"
            )
            item.lift()
            
            # 其他项变暗
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
                elif mouse_y > widget_center and i > current_index:
                    new_index = i
            
            if new_index != current_index:
                self._animate_subtask_swap(current_index, new_index, original_index)
                self._drag_data["current_index"] = new_index
            
        except Exception:
            pass
    
    def _animate_subtask_swap(self, from_index, to_index, dragged_index):
        """动画交换子任务位置 - 实时预览效果"""
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
        """平滑移动子任务项 - 使用弹性动画"""
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
        
        item = self._drag_data["widget"]
        task = self._drag_data["task"]
        original_index = self._drag_data["original_index"]
        current_index = self._drag_data.get("current_index", original_index)
        moved = self._drag_data.get("moved", False)
        
        # 重置拖拽状态
        self._drag_data["dragging"] = False
        self._drag_data["widget"] = None
        self._drag_data["task"] = None
        self._drag_data["subtask"] = None
        self._drag_data["is_subtask"] = False
        self._drag_data["moved"] = False
        self._drag_data["subtask_positions"] = []
        
        # 恢复所有项样式
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
        
        # 执行实际的数据移动
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
    
    # ==================== 任务追踪窗口 ====================
    
    def _toggle_tracker_window(self):
        """切换任务追踪悬浮窗"""
        if self.tracker_window is None:
            # 首次创建
            self.tracker_window = TaskTrackerWindow(self, self.db)
            self.tracker_window_visible = True
        elif self.tracker_window_visible:
            # 隐藏
            self.tracker_window.withdraw()
            self.tracker_window_visible = False
        else:
            # 显示
            self.tracker_window.deiconify()
            self.tracker_window._refresh_tracker()
            self.tracker_window_visible = True
    
    def _refresh_tracker_if_visible(self):
        """如果追踪窗口可见，刷新它"""
        if self.tracker_window and self.tracker_window_visible:
            self.tracker_window._refresh_tracker()


def main():
    """程序入口"""
    app = ResearchTerminal()
    app.mainloop()


if __name__ == "__main__":
    main()

