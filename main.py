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


class ResearchTerminal(ctk.CTk):
    """科研工作者终端主窗口"""
    
    def __init__(self):
        super().__init__()
        
        self.db = Database()
        self.selected_task: Optional[Task] = None
        
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
        
        title_label = ctk.CTkLabel(
            header,
            text="📋 任务列表",
            font=ctk.CTkFont(family="Microsoft YaHei", size=22, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY
        )
        title_label.pack(side="left")
        
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
    
    def _create_task_card(self, task: Task) -> ctk.CTkFrame:
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
            border_color=accent_color if self.selected_task and self.selected_task.id == task.id else ThemeConfig.BORDER_DEFAULT
        )
        card.pack(fill="x", pady=6, padx=4)
        
        # 绑定点击事件
        card.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        # 内容区域
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=16, pady=12)
        content.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        # 第一行：标题和模式标签
        row1 = ctk.CTkFrame(content, fg_color="transparent")
        row1.pack(fill="x")
        row1.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        # 模式标签
        mode_icon = "🔍" if task.mode == TaskMode.EXPLORING else "📊"
        mode_label = ctk.CTkLabel(
            row1,
            text=mode_icon,
            font=ctk.CTkFont(size=14)
        )
        mode_label.pack(side="left", padx=(0, 8))
        mode_label.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        # 标题
        title_label = ctk.CTkLabel(
            row1,
            text=task.title[:25] + ("..." if len(task.title) > 25 else ""),
            font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"),
            text_color=ThemeConfig.TEXT_PRIMARY,
            anchor="w"
        )
        title_label.pack(side="left", fill="x", expand=True)
        title_label.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        # 第二行：状态和进度
        row2 = ctk.CTkFrame(content, fg_color="transparent")
        row2.pack(fill="x", pady=(8, 0))
        row2.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        # 状态
        status_label = ctk.CTkLabel(
            row2,
            text=task.status.value,
            font=ctk.CTkFont(family="Microsoft YaHei", size=11),
            text_color=status_colors.get(task.status, ThemeConfig.TEXT_SECONDARY)
        )
        status_label.pack(side="left")
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
                text_color=ThemeConfig.TEXT_MUTED
            )
            notes_label.pack(side="right")
            notes_label.bind("<Button-1>", lambda e, t=task: self._select_task(t))
        
        return card
    
    def _refresh_task_list(self):
        """刷新任务列表"""
        # 清空现有列表
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
        
        # 按更新时间排序
        tasks.sort(key=lambda t: t.updated_at, reverse=True)
        
        # 创建任务卡片
        if tasks:
            for task in tasks:
                self._create_task_card(task)
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
        
        # 描述
        if task.description:
            desc_label = ctk.CTkLabel(
                scroll_container,
                text=task.description,
                font=ctk.CTkFont(family="Microsoft YaHei", size=14),
                text_color=ThemeConfig.TEXT_SECONDARY,
                anchor="w",
                justify="left",
                wraplength=700
            )
            desc_label.pack(fill="x", pady=(0, 20))
        
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
            for subtask in sorted(task.subtasks, key=lambda x: x.order):
                self._create_subtask_item(parent, task, subtask)
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
            
            conclusion_title = ctk.CTkLabel(
                conclusion_frame,
                text="💡 探索结论",
                font=ctk.CTkFont(family="Microsoft YaHei", size=14, weight="bold"),
                text_color=ThemeConfig.ACCENT_EXPLORING
            )
            conclusion_title.pack(anchor="w", padx=16, pady=(12, 8))
            
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
    
    def _create_subtask_item(self, parent, task: Task, subtask: SubTask):
        """创建子任务项"""
        is_completed = subtask.status == TaskStatus.COMPLETED
        
        item = ctk.CTkFrame(
            parent,
            fg_color=ThemeConfig.BG_TERTIARY,
            corner_radius=10,
            border_width=1,
            border_color=ThemeConfig.ACCENT_SUCCESS if is_completed else ThemeConfig.BORDER_DEFAULT
        )
        item.pack(fill="x", pady=4)
        
        content = ctk.CTkFrame(item, fg_color="transparent")
        content.pack(fill="x", padx=12, pady=10)
        
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
            anchor="w"
        )
        title_label.pack(side="left", fill="x", expand=True)
        
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
            width=28,
            height=28,
            command=lambda: self._delete_note(task, note)
        )
        delete_btn.pack(side="right")
        
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
            self._refresh_task_list()
            self._show_task_detail(updated_task)
    
    def _delete_task(self, task: Task):
        """删除任务"""
        if messagebox.askyesno("确认删除", f"确定要删除任务 \"{task.title}\" 吗？"):
            self.db.delete_task(task.id)
            self.selected_task = None
            self._refresh_task_list()
            self._show_welcome_screen()
    
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


def main():
    """程序入口"""
    app = ResearchTerminal()
    app.mainloop()


if __name__ == "__main__":
    main()

