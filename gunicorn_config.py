# Gunicorn 配置文件
# 此文件为可选的高级配置，如需使用请在 manage.sh 中添加 --config gunicorn_config.py

import multiprocessing
import os

# 服务器套接字
bind = "0.0.0.0:8000"
backlog = 2048

# Worker进程
workers = multiprocessing.cpu_count() * 2 + 1  # CPU核心数 * 2 + 1
worker_class = "sync"  # 可选: sync, gevent, eventlet, tornado, gthread
worker_connections = 1000  # 仅用于 gevent/eventlet
timeout = 120  # Worker超时时间（秒）
keepalive = 5  # Keep-alive连接时间（秒）
graceful_timeout = 30  # 优雅关闭超时时间（秒）

# 日志
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# 进程命名
proc_name = "shigu_gunicorn"

# 服务器机制
daemon = False  # 由脚本控制，这里设为False
pidfile = "gunicorn.pid"
umask = 0
user = None  # 生产环境建议设置为非root用户
group = None  # 生产环境建议设置为非root组

# 防止内存泄漏
max_requests = 1000  # 每个worker处理的最大请求数
max_requests_jitter = 50  # 最大请求数的随机抖动

# 预加载应用（提高性能，但会增加内存使用）
preload_app = False  # 如果设置为True，需要确保应用是线程安全的

# 其他选项
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# SSL配置（如果使用HTTPS，取消注释并配置）
# keyfile = "/path/to/keyfile"
# certfile = "/path/to/certfile"

# 环境变量
raw_env = [
    "DJANGO_SETTINGS_MODULE=ShiGu.settings",
]

# 服务器钩子（可选）
def on_starting(server):
    """服务器启动时调用"""
    server.log.info("服务器正在启动...")

def on_reload(server):
    """重新加载时调用"""
    server.log.info("服务器正在重新加载...")

def when_ready(server):
    """服务器就绪时调用"""
    server.log.info("服务器已就绪，正在监听 %s:%s" % (server.address[0], server.address[1]))

def on_exit(server):
    """服务器退出时调用"""
    server.log.info("服务器正在关闭...")

