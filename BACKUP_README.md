# Git 自动备份文档

本项目提供两种备份策略：

## 1. 🕐 定时备份（推荐Crontab）

配置系统定时任务，每天在指定时间自动提交。

### 使用步骤

```bash
# 1. 给脚本添加执行权限
chmod +x auto_backup.sh

# 2. 配置每天凌晨2点自动备份
crontab -e

# 添加这行（记得替换 /path/to/your/project）:
0 2 * * * /path/to/your/project/auto_backup.sh

# 保存退出
```

**示例路径**：
```bash
30 10 * * * /Users/tarl/Desktop/CodeField/CODE_Python/Researcher-Terminal/auto_backup.sh
```

**Crontab 格式说明**：
- `0 2 * * *` = 每天凌晨2点
- `30 23 * * *` = 每天晚上11点半
- `0 */6 * * *` = 每6小时

### 高级配置

```bash
# 每小时2点+周末双倍备份
0 2 * * 1-5 /path/to/auto_backup.sh
0 2 * * 6,7 /path/to/auto_backup.sh

# 每天多时间点备份
0 0,6,12,18 * * * /path/to/auto_backup.sh

# 只在工作时间备份（周一到周五，8-18点）
0 8-18 * * 1-5 /path/to/auto_backup.sh
```

## 2. 📁 文件监控备份（实时检测）

当 `research_data.json` 有修改时，立即检测并在30秒后自动提交。

### 启动监控

```bash
# 直接在当前终端运行（关闭终端会停止）
./monitor_backup.sh

# 在后台运行（推荐）
nohup ./monitor_backup.sh &

# 或使用 tmux / screen 持久化运行
tmux new -s backup
./monitor_backup.sh
# Ctrl+B, D 分离（进程继续运行）

# 查看监控日志
tail -f .git-backup.log
```

### 停止监控

```bash
# 查找进程
ps aux | grep monitor_backup

# 杀死进程
kill PID    # 替换 PID 为实际进程ID
```

## 日志查看

```bash
# 实时查看备份日志
tail -f .git-backup.log

# 查看最近10次提交
git log --oneline -10

# 查看文件和标签
git log --oneline --decorate --all
```

## 数据恢复

### 从最近的备份恢复

```bash
# 查看所有备份点
git log --oneline

# 恢复到今天的备份
git checkout backup-$(date '+%Y-%m-%d') -- research_data.json

# 恢复到最后一次修改前
git checkout HEAD~2 -- research_data.json

# 恢复后重新复制到工作目录
cp .git/... research_data.json  # 如果 git checkout 失败时
```

### 对比当前和历史版本

```bash
# 对比当前和一天前
git diff backup-$(date -v-1d '+%Y-%m-%d') -- research_data.json

# 对比具体某次提交
git show COMMIT_HASH:research_data.json
```

## 注意事项

1. **脚本不会推送到远程**，所有备份都在本地。想推送需要手动执行 `git push`
2. **备份只会跟踪 `research_data.json`**，不会影响其他文件
3. **安全性考虑**：
   - `.git` 目录要保持安全
   - 备份脚本可以定期复制到外部存储或云盘
4. **性能优化**：
   - 脚本会检测文件大小，超过10MB会提醒
   - 建议每周或每月整理一次历史备份
5. **并发安全**：
   - `monitor_backup.sh` 使用锁文件防止多实例冲突
   - 程序异常退出时会清理锁文件

## 路径配置示例

```bash
# Auto-Backup.sh 的第一行应该已经自动检测路径
# 如果是手动配置，记得修改为绝对路径：
PROJECT_DIR="/Users/YOUR_USERNAME/Desktop/CodeField/CODE_Python/Researcher-Terminal"
```

## 故障排查

```bash
# 查看备份是否执行
grep "Auto-Backup" .git-backup.log

# 确认 crontab 是否运行
crontab -l

# 查看系统日志检查 cron
grep CRON /var/log/syslog
grep cron /var/log/messages

# 手动运行脚本测试
./auto_backup.sh
```

## 高级：Git Hooks 触发备份

.git/hooks/post-commit（自动在每次手动提交后备份数据）：
```bash
#!/bin/bash
git add research_data.json
git commit --amend --no-edit --no-verify
```
记得 `chmod +x .git/hooks/post-commit`

## 清理旧备份

```bash
# 删除超过30天的标签
git tag | grep backup- | awk -F '-' '{
  if (NR % 30 == 0) print
}' | xargs git tag -d

# 删除无用的旧日志（只保留10MB以内）
tail -c 10M .git-backup.log > .git-backup.log.tmp
mv .git-backup.log.tmp .git-backup.log
```

---

## 常见问题

**Q: 怎么知道备份是否成功？**
A: 查看 `.git-backup.log` 或运行 `git log --oneline` 查看提交记录

**Q: Windows 上可以用吗？**
A: Windows 用户可以改为 PowerShell 脚本，或用 WSL 运行

**Q: 可以备份到多个位置吗？**
A: 可以，创建 `copy_to_safety.sh` 脚本，定时复制 `.git` 目录到其他位置

**Q: 如何手动触发一次备份？**
A: 直接运行 `./auto_backup.sh` 或 `git add research_data.json && git commit -m "手动备份"`

**Q: 需要.gitignore保护吗？**
A: research_data.json 已经追踪，不需要额外配置。保持只备份数据文件即可。

---

## 推荐的最简化方案（懒人版）

```bash
# 只设置 crontab
crontab -e

# 添加这一行
@daily cd /path/to/your/project && git add research_data.json && git commit -m "[Auto-Backup] $(date)" 2>&1 >> .git-backup.log

# macOS 上可能需要用 gdate
brew install coreutils
crontab -e
@daily cd /path/to/your/project && CDATE=$(gdate) && git add research_data.json && git commit -m "[Auto-Backup] $CDATE" 2>&1 >> .git-backup.log
```

这样最简洁，但灵活度低一些。用脚本形式支持日志和错误处理更好。