# -*- coding: utf-8 -*-
"""
科研工作者终端 - 数据模型
Researcher Terminal - Data Models

定义任务、子任务和探索笔记的数据结构

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

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional
import uuid


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "待处理"
    IN_PROGRESS = "进行中"
    EXPLORING = "探索中"
    COMPLETED = "已完成"
    PAUSED = "已暂停"


class TaskMode(Enum):
    """任务模式"""
    PLANNING = "规划模式"  # 知道做什么，知道怎么做
    EXPLORING = "探索模式"  # 知道做什么，但不知道怎么做


class TaskKnowledge(Enum):
    """任务认知状态"""
    KNOWN_WHAT_KNOWN_HOW = "明确目标·明确方法"
    KNOWN_WHAT_UNKNOWN_HOW = "明确目标·探索方法"
    UNKNOWN_WHAT = "待明确目标"


@dataclass
class ExplorationNote:
    """探索笔记 - 记录探索过程中的发现和思路"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    insight: str = ""  # 获得的洞察/启发
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)  # 最后修改时间
    is_breakthrough: bool = False  # 是否是突破性发现


@dataclass
class ExplorationNoteSearchResult:
    """探索笔记搜索结果"""
    task_id: str
    task_title: str
    task_mode: TaskMode
    note: ExplorationNote
    is_history: bool = False


@dataclass
class SubTask:
    """子任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    order: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    notes: str = ""


@dataclass
class Task:
    """主任务"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    description: str = ""
    order: int = 0
    status: TaskStatus = TaskStatus.PENDING
    mode: TaskMode = TaskMode.PLANNING
    knowledge: TaskKnowledge = TaskKnowledge.KNOWN_WHAT_KNOWN_HOW
    
    # 规划模式下的子任务
    subtasks: list[SubTask] = field(default_factory=list)
    
    # 探索模式下的笔记
    exploration_notes: list[ExplorationNote] = field(default_factory=list)
    
    # 时间记录
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    
    # 其他元数据
    priority: int = 0  # 0-低, 1-中, 2-高
    tags: list[str] = field(default_factory=list)
    conclusion: str = ""  # 探索模式的最终结论/解决方案
    
    def add_subtask(self, title: str, description: str = "") -> SubTask:
        """添加子任务"""
        subtask = SubTask(
            title=title,
            description=description,
            order=len(self.subtasks)
        )
        self.subtasks.append(subtask)
        self.updated_at = datetime.now()
        return subtask
    
    def add_exploration_note(self, content: str, insight: str = "", is_breakthrough: bool = False) -> ExplorationNote:
        """添加探索笔记"""
        note = ExplorationNote(
            content=content,
            insight=insight,
            is_breakthrough=is_breakthrough
        )
        self.exploration_notes.append(note)
        self.updated_at = datetime.now()
        return note
    
    def get_progress(self) -> float:
        """获取任务进度 (0.0 - 1.0)"""
        if not self.subtasks:
            return 1.0 if self.status == TaskStatus.COMPLETED else 0.0
        completed = sum(1 for st in self.subtasks if st.status == TaskStatus.COMPLETED)
        return completed / len(self.subtasks)
    
    def complete_subtask(self, subtask_id: str) -> bool:
        """完成子任务"""
        for st in self.subtasks:
            if st.id == subtask_id:
                st.status = TaskStatus.COMPLETED
                st.completed_at = datetime.now()
                self.updated_at = datetime.now()
                # 检查是否所有子任务都完成
                if all(s.status == TaskStatus.COMPLETED for s in self.subtasks):
                    self.status = TaskStatus.COMPLETED
                    self.completed_at = datetime.now()
                return True
        return False
    
    def switch_to_exploring(self) -> None:
        """切换到探索模式"""
        self.mode = TaskMode.EXPLORING
        self.status = TaskStatus.EXPLORING
        self.knowledge = TaskKnowledge.KNOWN_WHAT_UNKNOWN_HOW
        self.updated_at = datetime.now()
    
    def switch_to_planning(self) -> None:
        """切换到规划模式（当找到解决方案后）"""
        self.mode = TaskMode.PLANNING
        self.status = TaskStatus.IN_PROGRESS
        self.knowledge = TaskKnowledge.KNOWN_WHAT_KNOWN_HOW
        # 保留探索笔记，不再移动到单独的历史字段
        self.updated_at = datetime.now()
