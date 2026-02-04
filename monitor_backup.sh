#!/bin/bash
# research_data.json 变更监控脚本（守护进程模式）
# 使用方法：
#   chmod +x monitor_backup.sh
#   ./monitor_backup.sh &
# 或在 tmux/screen 中运行以便随时监控

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

LOG_FILE=".git-backup.log"
LOCK_FILE=".backup.lock"

# 如果脚本在运行，退出
if [ -f "$LOCK_FILE" ]; then
    PID=$(cat "$LOCK_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "监控脚本已在运行 (PID: $PID)"
        exit 1
    fi
fi

echo "启动文件监控..."
echo $$ > "$LOCK_FILE"

# 定义日志函数
log() {
    local level=$1
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

# 设置文件修改时间检查（5秒间隔检查）
CHECK_INTERVAL=5

# 设置修改等待时间（避免频繁提交）
WAIT_AFTER_MODIFY=30  # 文件修改后等待30秒再提交

LAST_MODIFY=$(stat -f%m research_data.json 2>/dev/null || stat -c%Y research_data.json 2>/dev/null)
declare -i last_check_time=0
declare -i wait_until=$WAIT_AFTER_MODIFY

log "INFO" "监控脚本启动（PID: $$）"
log "INFO" "监控5秒检查一次，文件修改后等待${WAIT_AFTER_MODIFY}秒提交"

while true; do
    sleep $CHECK_INTERVAL

    # 检查文件是否有修改
    CURRENT_MODIFY=$(stat -f%m research_data.json 2>/dev/null || stat -c%Y research_data.json 2>&1)
    if [[ "$CURRENT_MODIFY" != "$LAST_MODIFY" ]]; then
        # 文件有修改
        LAST_MODIFY=$CURRENT_MODIFY
        wait_until=$WAIT_AFTER_MODIFY
        log "INFO" "检测到 research_data.json 修改，等待${WAIT_AFTER_MODIFY}秒后提交..."
    fi

    # 倒计时并提交
    if [[ $wait_until -gt 0 ]]; then
        ((wait_until -= CHECK_INTERVAL))

        if [[ $wait_until -le 0 ]]; then
            # 倒计时结束，开始提交
            if [ -f "$PROJECT_DIR/auto_backup.sh" ]; then
                bash "$PROJECT_DIR/auto_backup.sh" || log "ERROR" "提交失败"
            else
                log "ERROR" "未找到 auto_backup.sh，无法提交"
            fi

            # 重置倒计时
            wait_until=0
        fi
    fi

    # 可选的长时间无修改自动tag（每小时）
    # 每小时给最后一次提交打标签
    if [ $(($(date +%s) - $(stat -f%m ".git/logs/HEAD" 2>/dev/null || echo 0))) -gt 3600 ]; then
        log "INFO" "每小时自动标签检查..."
        TODAY=$(date '+%Y-%m-%d_%H')
        git tag -f "snapshot-$TODAY" HEAD 2>&1 | tee -a "$LOG_FILE" || true
    fi
done

# 清理（通常不会运行到这里）
rm -f "$LOCK_FILE"
log "INFO" "监控脚本退出"