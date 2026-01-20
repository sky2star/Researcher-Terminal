# -*- coding: utf-8 -*-
"""
科研工作者终端 - 数据库操作层
Researcher Terminal - Database Layer

使用JSON文件作为轻量级数据存储

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

import json
import os
from datetime import datetime
from typing import Optional
from models import Task, SubTask, ExplorationNote, TaskStatus, TaskMode, TaskKnowledge


class Database:
    """JSON文件数据库管理器"""
    
    def __init__(self, db_path: str = "research_data.json"):
        self.db_path = db_path
        self.tasks: list[Task] = []
        self._load()
    
    def _load(self) -> None:
        """从文件加载数据"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.tasks = [self._dict_to_task(t) for t in data.get('tasks', [])]
            except (json.JSONDecodeError, IOError):
                self.tasks = []
        else:
            self.tasks = []
    
    def _save(self) -> None:
        """保存数据到文件"""
        data = {
            'tasks': [self._task_to_dict(t) for t in self.tasks],
            'last_updated': datetime.now().isoformat()
        }
        with open(self.db_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def _task_to_dict(self, task: Task) -> dict:
        """将任务对象转换为字典"""
        return {
            'id': task.id,
            'title': task.title,
            'description': task.description,
            'status': task.status.name,
            'mode': task.mode.name,
            'knowledge': task.knowledge.name,
            'subtasks': [
                {
                    'id': st.id,
                    'title': st.title,
                    'description': st.description,
                    'status': st.status.name,
                    'order': st.order,
                    'created_at': st.created_at.isoformat(),
                    'completed_at': st.completed_at.isoformat() if st.completed_at else None,
                    'notes': st.notes
                }
                for st in task.subtasks
            ],
            'exploration_notes': [
                {
                    'id': note.id,
                    'content': note.content,
                    'insight': note.insight,
                    'created_at': note.created_at.isoformat(),
                    'is_breakthrough': note.is_breakthrough
                }
                for note in task.exploration_notes
            ],
            'created_at': task.created_at.isoformat(),
            'updated_at': task.updated_at.isoformat(),
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'priority': task.priority,
            'tags': task.tags,
            'conclusion': task.conclusion
        }
    
    def _dict_to_task(self, data: dict) -> Task:
        """将字典转换为任务对象"""
        task = Task(
            id=data['id'],
            title=data['title'],
            description=data.get('description', ''),
            status=TaskStatus[data['status']],
            mode=TaskMode[data['mode']],
            knowledge=TaskKnowledge[data['knowledge']],
            created_at=datetime.fromisoformat(data['created_at']),
            updated_at=datetime.fromisoformat(data['updated_at']),
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            priority=data.get('priority', 0),
            tags=data.get('tags', []),
            conclusion=data.get('conclusion', '')
        )
        
        # 加载子任务
        for st_data in data.get('subtasks', []):
            subtask = SubTask(
                id=st_data['id'],
                title=st_data['title'],
                description=st_data.get('description', ''),
                status=TaskStatus[st_data['status']],
                order=st_data.get('order', 0),
                created_at=datetime.fromisoformat(st_data['created_at']),
                completed_at=datetime.fromisoformat(st_data['completed_at']) if st_data.get('completed_at') else None,
                notes=st_data.get('notes', '')
            )
            task.subtasks.append(subtask)
        
        # 加载探索笔记
        for note_data in data.get('exploration_notes', []):
            note = ExplorationNote(
                id=note_data['id'],
                content=note_data['content'],
                insight=note_data.get('insight', ''),
                created_at=datetime.fromisoformat(note_data['created_at']),
                is_breakthrough=note_data.get('is_breakthrough', False)
            )
            task.exploration_notes.append(note)
        
        return task
    
    # ==================== CRUD 操作 ====================
    
    def create_task(self, title: str, description: str = "", 
                   mode: TaskMode = TaskMode.PLANNING,
                   knowledge: TaskKnowledge = TaskKnowledge.KNOWN_WHAT_KNOWN_HOW,
                   priority: int = 0) -> Task:
        """创建新任务"""
        task = Task(
            title=title,
            description=description,
            mode=mode,
            knowledge=knowledge,
            priority=priority,
            status=TaskStatus.EXPLORING if mode == TaskMode.EXPLORING else TaskStatus.PENDING
        )
        self.tasks.append(task)
        self._save()
        return task
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """根据ID获取任务"""
        for task in self.tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_all_tasks(self) -> list[Task]:
        """获取所有任务"""
        return self.tasks.copy()
    
    def get_tasks_by_status(self, status: TaskStatus) -> list[Task]:
        """根据状态筛选任务"""
        return [t for t in self.tasks if t.status == status]
    
    def get_tasks_by_mode(self, mode: TaskMode) -> list[Task]:
        """根据模式筛选任务"""
        return [t for t in self.tasks if t.mode == mode]
    
    def update_task(self, task_id: str, **kwargs) -> Optional[Task]:
        """更新任务"""
        task = self.get_task(task_id)
        if task:
            for key, value in kwargs.items():
                if hasattr(task, key):
                    setattr(task, key, value)
            task.updated_at = datetime.now()
            self._save()
        return task
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        for i, task in enumerate(self.tasks):
            if task.id == task_id:
                self.tasks.pop(i)
                self._save()
                return True
        return False
    
    # ==================== 子任务操作 ====================
    
    def add_subtask(self, task_id: str, title: str, description: str = "") -> Optional[SubTask]:
        """添加子任务"""
        task = self.get_task(task_id)
        if task:
            subtask = task.add_subtask(title, description)
            # 如果任务已完成，添加新子任务后应该重新变为进行中
            if task.status == TaskStatus.COMPLETED:
                task.status = TaskStatus.IN_PROGRESS
                task.completed_at = None
            self._save()
            return subtask
        return None
    
    def update_subtask(self, task_id: str, subtask_id: str, **kwargs) -> Optional[SubTask]:
        """更新子任务"""
        task = self.get_task(task_id)
        if task:
            for st in task.subtasks:
                if st.id == subtask_id:
                    for key, value in kwargs.items():
                        if hasattr(st, key):
                            setattr(st, key, value)
                    task.updated_at = datetime.now()
                    
                    # 如果任务是已完成状态，但现在有子任务变成未完成，需要更新任务状态
                    if task.status == TaskStatus.COMPLETED:
                        has_incomplete = any(s.status != TaskStatus.COMPLETED for s in task.subtasks)
                        if has_incomplete:
                            task.status = TaskStatus.IN_PROGRESS
                            task.completed_at = None
                    
                    self._save()
                    return st
        return None
    
    def delete_subtask(self, task_id: str, subtask_id: str) -> bool:
        """删除子任务"""
        task = self.get_task(task_id)
        if task:
            for i, st in enumerate(task.subtasks):
                if st.id == subtask_id:
                    task.subtasks.pop(i)
                    # 重新排序剩余子任务
                    for j, remaining_st in enumerate(task.subtasks):
                        remaining_st.order = j
                    task.updated_at = datetime.now()
                    self._save()
                    return True
        return False
    
    def move_subtask(self, task_id: str, subtask_id: str, direction: int) -> bool:
        """移动子任务顺序 (direction: -1向上, 1向下)"""
        task = self.get_task(task_id)
        if task:
            # 按order排序获取当前顺序
            sorted_subtasks = sorted(task.subtasks, key=lambda x: x.order)
            current_index = None
            for i, st in enumerate(sorted_subtasks):
                if st.id == subtask_id:
                    current_index = i
                    break
            
            if current_index is not None:
                new_index = current_index + direction
                if 0 <= new_index < len(sorted_subtasks):
                    # 交换位置
                    sorted_subtasks[current_index].order = new_index
                    sorted_subtasks[new_index].order = current_index
                    task.updated_at = datetime.now()
                    self._save()
                    return True
        return False
    
    def move_task(self, task_id: str, direction: int) -> bool:
        """移动任务顺序 (direction: -1向上, 1向下)"""
        current_index = None
        for i, t in enumerate(self.tasks):
            if t.id == task_id:
                current_index = i
                break
        
        if current_index is not None:
            new_index = current_index + direction
            if 0 <= new_index < len(self.tasks):
                # 交换位置
                self.tasks[current_index], self.tasks[new_index] = self.tasks[new_index], self.tasks[current_index]
                self._save()
                return True
        return False
    
    def update_exploration_note(self, task_id: str, note_id: str, **kwargs) -> Optional[ExplorationNote]:
        """更新探索笔记"""
        task = self.get_task(task_id)
        if task:
            for note in task.exploration_notes:
                if note.id == note_id:
                    for key, value in kwargs.items():
                        if hasattr(note, key):
                            setattr(note, key, value)
                    task.updated_at = datetime.now()
                    self._save()
                    return note
        return None
    
    def clear_task_conclusion(self, task_id: str) -> Optional[Task]:
        """清除任务结论"""
        task = self.get_task(task_id)
        if task:
            task.conclusion = ""
            task.updated_at = datetime.now()
            self._save()
        return task
    
    def complete_subtask(self, task_id: str, subtask_id: str) -> bool:
        """完成子任务"""
        task = self.get_task(task_id)
        if task:
            result = task.complete_subtask(subtask_id)
            if result:
                self._save()
            return result
        return False
    
    # ==================== 探索笔记操作 ====================
    
    def add_exploration_note(self, task_id: str, content: str, 
                            insight: str = "", is_breakthrough: bool = False) -> Optional[ExplorationNote]:
        """添加探索笔记"""
        task = self.get_task(task_id)
        if task:
            note = task.add_exploration_note(content, insight, is_breakthrough)
            self._save()
            return note
        return None
    
    def delete_exploration_note(self, task_id: str, note_id: str) -> bool:
        """删除探索笔记"""
        task = self.get_task(task_id)
        if task:
            for i, note in enumerate(task.exploration_notes):
                if note.id == note_id:
                    task.exploration_notes.pop(i)
                    task.updated_at = datetime.now()
                    self._save()
                    return True
        return False
    
    # ==================== 模式切换 ====================
    
    def switch_task_mode(self, task_id: str, to_exploring: bool = True) -> Optional[Task]:
        """切换任务模式"""
        task = self.get_task(task_id)
        if task:
            if to_exploring:
                task.switch_to_exploring()
            else:
                task.switch_to_planning()
            self._save()
        return task
    
    def set_task_conclusion(self, task_id: str, conclusion: str) -> Optional[Task]:
        """设置任务结论（探索模式转规划模式时）"""
        task = self.get_task(task_id)
        if task:
            task.conclusion = conclusion
            task.updated_at = datetime.now()
            self._save()
        return task
    
    # ==================== 搜索功能 ====================
    
    def search_tasks(self, keyword: str) -> list[Task]:
        """搜索任务"""
        keyword = keyword.lower()
        results = []
        for task in self.tasks:
            if (keyword in task.title.lower() or 
                keyword in task.description.lower() or
                any(keyword in tag.lower() for tag in task.tags)):
                results.append(task)
        return results

