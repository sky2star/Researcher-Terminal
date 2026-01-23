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
from models import Task, SubTask, ExplorationNote, ExplorationNoteSearchResult, TaskStatus, TaskMode, TaskKnowledge


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
                    self.tasks = [self._dict_to_task(t, index) for index, t in enumerate(data.get('tasks', []))]
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
            'order': task.order,
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
                    'updated_at': note.updated_at.isoformat(),
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
    
    def _dict_to_task(self, data: dict, default_order: int) -> Task:
        """将字典转换为任务对象"""
        task = Task(
            id=data['id'],
            title=data['title'],
            description=data.get('description', ''),
            order=data.get('order', default_order),
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
                updated_at=datetime.fromisoformat(note_data.get('updated_at', note_data['created_at'])),
                is_breakthrough=note_data.get('is_breakthrough', False)
            )
            task.exploration_notes.append(note)

        # 兼容旧数据：将exploration_history合并到exploration_notes
        history_data = data.get('exploration_history')
        if history_data:
            for note_data in history_data:
                note = ExplorationNote(
                    id=note_data['id'],
                    content=note_data['content'],
                    insight=note_data.get('insight', ''),
                    created_at=datetime.fromisoformat(note_data['created_at']),
                    updated_at=datetime.fromisoformat(note_data.get('updated_at', note_data['created_at'])),
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
            order=len(self.tasks),
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
                    for j, remaining in enumerate(task.subtasks):
                        remaining.order = j
                    task.updated_at = datetime.now()
                    self._save()
                    return True
        return False

    def move_subtask(self, task_id: str, subtask_id: str, direction: int) -> bool:
        """移动子任务顺序 (direction: -1向上, 1向下)"""
        task = self.get_task(task_id)
        if task:
            ordered = sorted(task.subtasks, key=lambda x: x.order)
            current_index = None
            for i, st in enumerate(ordered):
                if st.id == subtask_id:
                    current_index = i
                    break
            if current_index is None:
                return False
            new_index = current_index + direction
            if 0 <= new_index < len(ordered):
                ordered[current_index], ordered[new_index] = ordered[new_index], ordered[current_index]
                for i, st in enumerate(ordered):
                    st.order = i
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
        if current_index is None:
            return False
        new_index = current_index + direction
        if 0 <= new_index < len(self.tasks):
            self.tasks[current_index], self.tasks[new_index] = self.tasks[new_index], self.tasks[current_index]
            for i, t in enumerate(self.tasks):
                t.order = i
            self._save()
            return True
        return False
    
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

    def update_exploration_note(self, task_id: str, note_id: str, **kwargs) -> Optional[ExplorationNote]:
        """更新探索笔记"""
        task = self.get_task(task_id)
        if task:
            for note in task.exploration_notes:
                if note.id == note_id:
                    for key, value in kwargs.items():
                        if hasattr(note, key):
                            setattr(note, key, value)
                    note.updated_at = datetime.now()  # 更新修改时间
                    task.updated_at = datetime.now()
                    self._save()
                    return note
        return None

    def move_exploration_note_order(self, task_id: str, note_id: str, direction: int) -> bool:
        """移动探索笔记顺序 (direction: -1向上, 1向下)"""
        task = self.get_task(task_id)
        if not task:
            return False
        current_index = None
        for i, note in enumerate(task.exploration_notes):
            if note.id == note_id:
                current_index = i
                break
        if current_index is None:
            return False
        new_index = current_index + direction
        if 0 <= new_index < len(task.exploration_notes):
            task.exploration_notes[current_index], task.exploration_notes[new_index] = (
                task.exploration_notes[new_index],
                task.exploration_notes[current_index],
            )
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

    def clear_task_conclusion(self, task_id: str) -> Optional[Task]:
        """清除任务结论"""
        task = self.get_task(task_id)
        if task:
            task.conclusion = ""
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

    def _match_note_keyword(self, note: ExplorationNote, keyword: str) -> bool:
        needle = keyword.lower()
        return needle in note.content.lower() or needle in note.insight.lower()

    def search_exploration_notes_global(self, keyword: str) -> list[ExplorationNoteSearchResult]:
        """全局搜索探索笔记"""
        keyword = keyword.strip().lower()
        if not keyword:
            return []
        results = []
        for task in self.tasks:
            for note in task.exploration_notes:
                if self._match_note_keyword(note, keyword):
                    results.append(ExplorationNoteSearchResult(task.id, task.title, task.mode, note, False))
        return results

    def search_exploration_notes_in_task(self, task_id: str, keyword: str) -> list[ExplorationNoteSearchResult]:
        """任务内搜索探索笔记"""
        task = self.get_task(task_id)
        if not task:
            return []
        keyword = keyword.strip().lower()
        if not keyword:
            return []
        results = []
        for note in task.exploration_notes:
            if self._match_note_keyword(note, keyword):
                results.append(ExplorationNoteSearchResult(task.id, task.title, task.mode, note, False))
        return results

    # ==================== 探索笔记管理 ====================

    def move_exploration_note(self, source_task_id: str, target_task_id: str, note_id: str) -> bool:
        """将探索笔记从一个任务移动到另一个任务"""
        source_task = self.get_task(source_task_id)
        target_task = self.get_task(target_task_id)

        if not source_task or not target_task:
            return False

        # 查找并移除笔记
        note_to_move = None
        for i, note in enumerate(source_task.exploration_notes):
            if note.id == note_id:
                note_to_move = source_task.exploration_notes.pop(i)
                break

        if not note_to_move:
            return False

        # 添加到目标任务
        target_task.exploration_notes.append(note_to_move)

        # 更新时间戳
        source_task.updated_at = datetime.now()
        target_task.updated_at = datetime.now()

        self._save()
        return True

    def batch_delete_exploration_notes(self, task_id: str, note_ids: list[str]) -> bool:
        """批量删除探索笔记（仅可编辑笔记）"""
        task = self.get_task(task_id)
        if not task or not note_ids:
            return False

        note_ids_set = set(note_ids)
        before = len(task.exploration_notes)
        task.exploration_notes = [note for note in task.exploration_notes if note.id not in note_ids_set]
        if len(task.exploration_notes) == before:
            return False

        task.updated_at = datetime.now()
        self._save()
        return True

    def batch_move_exploration_notes(self, source_task_id: str, target_task_id: str,
                                     note_ids: list[str]) -> bool:
        """批量移动探索笔记（仅可编辑笔记）"""
        source_task = self.get_task(source_task_id)
        target_task = self.get_task(target_task_id)

        if not source_task or not target_task or not note_ids:
            return False

        note_ids_set = set(note_ids)
        notes_to_move = [note for note in source_task.exploration_notes if note.id in note_ids_set]
        if not notes_to_move:
            return False

        source_task.exploration_notes = [
            note for note in source_task.exploration_notes if note.id not in note_ids_set
        ]
        target_task.exploration_notes.extend(notes_to_move)

        source_task.updated_at = datetime.now()
        target_task.updated_at = datetime.now()

        self._save()
        return True

    def copy_exploration_note(self, source_task_id: str, target_task_id: str, note_id: str) -> Optional[ExplorationNote]:
        """将探索笔记复制到另一个任务"""
        source_task = self.get_task(source_task_id)
        target_task = self.get_task(target_task_id)

        if not source_task or not target_task:
            return None

        # 查找笔记
        source_note = None
        for note in source_task.exploration_notes:
            if note.id == note_id:
                source_note = note
                break

        if not source_note:
            return None

        # 创建新笔记（使用新ID）
        new_note = ExplorationNote(
            content=source_note.content,
            insight=source_note.insight,
            is_breakthrough=source_note.is_breakthrough
        )

        # 添加到目标任务
        target_task.exploration_notes.append(new_note)
        target_task.updated_at = datetime.now()

        self._save()
        return new_note

    def merge_tasks_exploration_notes(self, source_task_ids: list[str], target_task_id: str,
                                    new_task_title: str = "") -> bool:
        """合并多个任务的探索笔记到新任务或现有任务"""
        if not source_task_ids:
            return False

        # 获取源任务
        source_tasks = [self.get_task(task_id) for task_id in source_task_ids]
        if not all(source_tasks):
            return False

        target_task = None
        if new_task_title:
            # 创建新任务
            target_task = self.create_task(
                title=new_task_title,
                mode=TaskMode.EXPLORING,
                knowledge=TaskKnowledge.KNOWN_WHAT_UNKNOWN_HOW
            )
        else:
            # 使用现有任务
            target_task = self.get_task(target_task_id)
            if not target_task:
                return False

        # 收集所有探索笔记
        all_notes = []
        for task in source_tasks:
            all_notes.extend(task.exploration_notes)

        # 按创建时间排序，确保合并后时间顺序正确
        all_notes.sort(key=lambda note: note.created_at)

        # 添加所有笔记到目标任务（过滤重复的）
        existing_note_ids = {note.id for note in target_task.exploration_notes}
        for note in all_notes:
            if note.id not in existing_note_ids:
                target_task.exploration_notes.append(note)

        target_task.updated_at = datetime.now()
        self._save()
        return target_task.id if new_task_title else True
