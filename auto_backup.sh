#!/bin/bash
# 自动备份脚本：定时提交 research_data.json 到本地 git
# 使用方法：
#   1. chmod +x auto_backup.sh
#   2. 添加到 crontab: crontab -e
#   3. 添加: 0 2 * * * /path/to/auto_backup.sh

set -e  # 遇到错误立即退出

# 脚本目录（自动检测）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 日志文件
LOG_FILE=".git-backup.log"

# 输出日志函数
log() {
    local level=$1
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# Git 用户配置（使用本地配置）
if ! git config user.email &> /dev/null; then
    log "ERROR" "Git 用户邮箱未配置，请先运行："
    log "ERROR" "  git config user.email \"your-email@example.com\""
    log "ERROR" "  git config user.name \"Your Name\""
    exit 1
fi

# 检查是否有未提交的 research_data.json 变更
log "INFO" "开始检查文件变更..."
if git diff --quiet research_data.json 2>/dev/null; then
    log "INFO" "数据文件无变化，跳过提交"
    exit 0
fi

# 获取文件大小
FILE_SIZE=$(wc -c < research_data.json)
FILE_SIZE_MB=$(echo "scale=2; $FILE_SIZE / 1024 / 1024" | bc)

# 检查大小是否合理（超过 10MB 警告）
if [ $(echo "$FILE_SIZE_MB > 10" | bc) -eq 1 ]; then
    log "WARN" "数据文件较大: ${FILE_SIZE_MB}MB，可能需要清理"
fi

# 提交变更
log "INFO" "检测到数据变更，开始提交..."
git add .

# 获取变更统计
CHANGES=$(git diff --stat --cached research_data.json 2>/dev/null || echo "Unknown changes")

# 提交消息（带时间戳）
COMMIT_MESSAGE="[Auto-Backup] $(date '+%Y-%m-%d %H:%M:%S')
文件变更: ${CHANGES}
变更时间: $(date)
文件大小: ${FILE_SIZE_MB}MB"

# 执行提交（使用 GitHub API 风格的格式，不推送）
git commit -m "$COMMIT_MESSAGE" --no-verify

# 记录提交哈希
COMMIT_HASH=$(git rev-parse --short HEAD)
log "INFO" "提交成功: $COMMIT_HASH"
log "INFO" "提交说明: $COMMIT_MESSAGE"

# 可选：给今天的最后一次提交打标签
TODAY=$(date '+%Y-%m-%d')
git tag -f "backup-$TODAY" HEAD

log "INFO" "今日标签已更新: backup-$TODAY"

# 建议最多保留 30 天标签
log "INFO" "提示：如需清理旧备份，运行: git tag | grep backup- | tail -n +30 | xargs git tag -d"

# 输出备份成功信息
echo ""
echo "✅ 自动备份完成！"
echo "📊 文件大小: ${FILE_SIZE_MB}MB"
echo "🔖 提交哈希: $COMMIT_HASH"
echo "🏷️  今日标签: backup-$TODAY"
echo "📝 日志位置: $SCRIPT_DIR/$LOG_FILE"