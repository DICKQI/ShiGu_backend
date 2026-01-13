#!/bin/bash

# Django项目生产环境管理脚本
# 使用 Gunicorn 作为 WSGI 服务器

# ==================== 配置区域 ====================
# 项目根目录（包含manage.py的目录）
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# WSGI应用路径
WSGI_APP="ShiGu.wsgi:application"
# Gunicorn配置
BIND_ADDR="0.0.0.0:8000"          # 绑定地址和端口
WORKERS=4                         # Worker进程数（建议：CPU核心数 * 2 + 1）
WORKER_CLASS="sync"               # Worker类型：sync/gevent/eventlet
TIMEOUT=120                       # Worker超时时间（秒）
KEEPALIVE=5                       # Keep-alive连接时间（秒）
MAX_REQUESTS=1000                 # 每个worker处理的最大请求数（防止内存泄漏）
MAX_REQUESTS_JITTER=50            # 最大请求数的随机抖动
# 日志配置
LOG_DIR="${PROJECT_DIR}/logs"
ACCESS_LOG="${LOG_DIR}/gunicorn_access.log"
ERROR_LOG="${LOG_DIR}/gunicorn_error.log"
# PID文件
PID_FILE="${PROJECT_DIR}/gunicorn.pid"
# 环境变量
DJANGO_SETTINGS_MODULE="ShiGu.settings"
# ================================================

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        print_error "$1 未安装，请先安装：pip install $1"
        exit 1
    fi
}

# 检查gunicorn是否安装
check_gunicorn() {
    if ! python -c "import gunicorn" 2>/dev/null; then
        print_error "Gunicorn 未安装，请先安装：pip install gunicorn"
        exit 1
    fi
}

# 创建日志目录
create_log_dir() {
    if [ ! -d "$LOG_DIR" ]; then
        mkdir -p "$LOG_DIR"
        print_info "创建日志目录: $LOG_DIR"
    fi
}

# 检查进程是否运行
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        else
            # PID文件存在但进程不存在，清理PID文件
            rm -f "$PID_FILE"
            return 1
        fi
    else
        return 1
    fi
}

# 启动服务
start() {
    print_info "正在启动 Django 服务..."
    
    # 检查gunicorn
    check_gunicorn
    
    # 检查是否已运行
    if is_running; then
        PID=$(cat "$PID_FILE")
        print_warn "服务已在运行中 (PID: $PID)"
        return 1
    fi
    
    # 创建日志目录
    create_log_dir
    
    # 切换到项目目录
    cd "$PROJECT_DIR" || exit 1
    
    # 设置环境变量
    export DJANGO_SETTINGS_MODULE="$DJANGO_SETTINGS_MODULE"
    
    # 启动gunicorn
    print_info "使用配置: Workers=$WORKERS, Bind=$BIND_ADDR"
    
    gunicorn "$WSGI_APP" \
        --bind "$BIND_ADDR" \
        --workers "$WORKERS" \
        --worker-class "$WORKER_CLASS" \
        --timeout "$TIMEOUT" \
        --keep-alive "$KEEPALIVE" \
        --max-requests "$MAX_REQUESTS" \
        --max-requests-jitter "$MAX_REQUESTS_JITTER" \
        --pid "$PID_FILE" \
        --daemon \
        --access-logfile "$ACCESS_LOG" \
        --error-logfile "$ERROR_LOG" \
        --log-level info \
        --capture-output \
        --enable-stdio-inheritance
    
    # 等待一下，检查是否启动成功
    sleep 2
    
    if is_running; then
        PID=$(cat "$PID_FILE")
        print_info "服务启动成功！"
        print_info "PID: $PID"
        print_info "访问地址: http://$BIND_ADDR"
        print_info "访问日志: $ACCESS_LOG"
        print_info "错误日志: $ERROR_LOG"
    else
        print_error "服务启动失败，请检查错误日志: $ERROR_LOG"
        return 1
    fi
}

# 停止服务
stop() {
    print_info "正在停止 Django 服务..."
    
    if ! is_running; then
        print_warn "服务未运行"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    # 优雅停止
    print_info "发送 TERM 信号到进程 $PID..."
    kill -TERM "$PID" 2>/dev/null
    
    # 等待进程结束
    for i in {1..30}; do
        if ! ps -p "$PID" > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    # 如果还在运行，强制杀死
    if ps -p "$PID" > /dev/null 2>&1; then
        print_warn "进程未响应，强制终止..."
        kill -9 "$PID" 2>/dev/null
        sleep 1
    fi
    
    # 清理PID文件
    if [ -f "$PID_FILE" ]; then
        rm -f "$PID_FILE"
    fi
    
    if ! ps -p "$PID" > /dev/null 2>&1; then
        print_info "服务已停止"
    else
        print_error "停止服务失败"
        return 1
    fi
}

# 重启服务
restart() {
    print_info "正在重启 Django 服务..."
    stop
    sleep 2
    start
}

# 重新加载配置（优雅重启，不中断连接）
reload() {
    print_info "正在重新加载配置..."
    
    if ! is_running; then
        print_warn "服务未运行，尝试启动..."
        start
        return $?
    fi
    
    PID=$(cat "$PID_FILE")
    
    # 发送HUP信号给主进程，触发优雅重启
    print_info "发送 HUP 信号到进程 $PID..."
    kill -HUP "$PID" 2>/dev/null
    
    if [ $? -eq 0 ]; then
        print_info "配置重新加载成功"
    else
        print_error "重新加载失败"
        return 1
    fi
}

# 查看服务状态
status() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        print_info "服务运行中"
        print_info "PID: $PID"
        print_info "绑定地址: $BIND_ADDR"
        print_info "Workers: $WORKERS"
        
        # 显示进程信息
        echo ""
        print_info "进程信息:"
        ps aux | grep -E "gunicorn.*$WSGI_APP" | grep -v grep
        
        # 显示端口监听情况
        echo ""
        print_info "端口监听情况:"
        PORT=$(echo "$BIND_ADDR" | cut -d':' -f2)
        if command -v netstat &> /dev/null; then
            netstat -tlnp 2>/dev/null | grep ":$PORT " || echo "未找到监听端口 $PORT"
        elif command -v ss &> /dev/null; then
            ss -tlnp 2>/dev/null | grep ":$PORT " || echo "未找到监听端口 $PORT"
        else
            echo "无法检查端口监听情况（需要安装 netstat 或 ss）"
        fi
    else
        print_warn "服务未运行"
        return 1
    fi
}

# 查看日志
logs() {
    local log_type="${1:-error}"
    
    case "$log_type" in
        access)
            if [ -f "$ACCESS_LOG" ]; then
                tail -f "$ACCESS_LOG"
            else
                print_error "访问日志不存在: $ACCESS_LOG"
            fi
            ;;
        error|*)
            if [ -f "$ERROR_LOG" ]; then
                tail -f "$ERROR_LOG"
            else
                print_error "错误日志不存在: $ERROR_LOG"
            fi
            ;;
    esac
}

# 显示帮助信息
show_help() {
    cat << EOF
Django 项目生产环境管理脚本

用法: $0 {start|stop|restart|reload|status|logs|help}

命令说明:
    start      启动服务（后台运行）
    stop       停止服务
    restart    重启服务（先停止再启动）
    reload     重新加载配置（优雅重启，不中断连接）
    status     查看服务状态
    logs       查看错误日志（实时）
    logs access 查看访问日志（实时）
    help       显示此帮助信息

配置说明:
    编辑脚本顶部的配置区域可以修改以下参数:
    - BIND_ADDR: 绑定地址和端口（默认: 0.0.0.0:8000）
    - WORKERS: Worker进程数（默认: 4）
    - WORKER_CLASS: Worker类型（默认: sync）
    - TIMEOUT: Worker超时时间（默认: 120秒）
    - 日志文件位置: logs/gunicorn_*.log

示例:
    $0 start          # 启动服务
    $0 stop           # 停止服务
    $0 restart        # 重启服务
    $0 reload         # 重新加载配置
    $0 status         # 查看状态
    $0 logs           # 查看错误日志
    $0 logs access    # 查看访问日志

注意事项:
    1. 确保已安装 gunicorn: pip install gunicorn
    2. 生产环境建议使用 Nginx 作为反向代理
    3. 建议使用 systemd 或 supervisor 管理服务
    4. 定期检查日志文件大小，必要时进行日志轮转

EOF
}

# 主函数
main() {
    case "${1:-help}" in
        start)
            start
            ;;
        stop)
            stop
            ;;
        restart)
            restart
            ;;
        reload)
            reload
            ;;
        status)
            status
            ;;
        logs)
            logs "$2"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"

