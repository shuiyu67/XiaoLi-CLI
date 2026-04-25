"""
NapCat QQ 机器人插件 - OneBot 11 协议
通过 NapCat 框架接入 QQ，支持消息收发、群管理等操作

集成功能:
- 自动下载安装 NapCat 到插件目录
- 启动/停止服务
- 消息收发
- 群管理
"""

import os
import json
import subprocess
import requests
import threading
import time
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict, Any, List

# NapCat 版本
NAPCAT_VERSION = "v4.17.52"
NAPCAT_DOWNLOAD_URL = f"https://github.com/NapNeko/NapCatQQ/releases/download/{NAPCAT_VERSION}/NapCat.Shell.Windows.OneKey.zip"


class Liugin:
    """NapCat QQ 机器人插件"""
    
    def __init__(self):
        # 获取插件目录
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.napcat_dir = os.path.join(self.plugin_dir, "napcat")
        
        # NapCat 连接配置
        self.host = "127.0.0.1"
        self.port = 3000
        self.token = ""
        self.timeout = 10
        self._process = None
        
        # 消息监听配置
        self.listen_port = 3100  # 消息监听端口
        self.listen_server = None
        self.listen_thread = None
        self.login_user_id = None  # 当前登录的QQ号
        self._monitor_running = False  # 监控线程运行标志
        
        # 自动加载配置
        self._load_config()
        
        # 启动后台监控线程
        self._start_monitor_thread()
        
        self.usage = """NapCat QQ机器人使用方法：
napcat_qq <操作> <参数>

【重要】发送群消息流程:
1. 先用 group_list 获取群列表和群号
2. 再用 send_group <群号> <消息> 发送

【自动回复】监听@消息:
1. start_listen [端口]    - 启动消息监听（默认3100端口）
2. 在 WebUI 配置 HTTP 上报地址: http://127.0.0.1:3100
3. 群内有人@机器人时，消息自动转发给AI

安装管理:
- install                      - 下载安装 NapCat
- start                        - 启动 NapCat
- stop                         - 停止 NapCat
- status                       - 查看运行状态

信息获取:
- group_list                   - 获取群列表(包含群号)
- friend_list                  - 获取好友列表
- login_info                   - 获取登录号信息
- group_notice <群号>          - 获取群公告
- get_msg <消息ID>             - 获取消息详情
- get_chat_history <群号>      - 获取群聊天记录

消息操作:
- send_group <群号> <消息>     - 发送群消息
- send_private <QQ号> <消息>   - 发送私聊消息
- send_image <群号/QQ号> <图片路径> [true/false] - 发送图片
- recall <消息ID>              - 撤回消息
- send_forward <群号> <消息>   - 发送合并转发消息
- get_forward_msg <消息ID>     - 获取合并转发消息内容

群管理:
- ban <群号> <QQ号> [时长]     - 禁言成员
- kick <群号> <QQ号>           - 踢出群成员
- set_admin <群号> <QQ号>      - 设置群管理员
- unset_admin <群号> <QQ号>    - 取消群管理员
- set_title <群号> <QQ号> <头衔> - 设置群专属头衔
- whole_ban <群号> [true/false] - 全群禁言/解除
- leave <群号>                 - 退出群聊

请求处理:
- set_friend <flag> [accept/reject] - 处理好友请求
- set_group <flag> [accept/reject]  - 处理群邀请

系统功能:
- version                      - 获取 OneBot 版本信息
- restart                      - 重启 OneBot 实现

示例:
- napcat_qq start_listen               # 启动监听
- napcat_qq group_list                 # 获取群号
- napcat_qq send_group 987654321 大家好 # 发群消息
- napcat_qq set_admin 987654321 123456 # 设置管理员
- napcat_qq whole_ban 987654321 true   # 开启全群禁言
"""
        self.cli = None
        
    def set_cli(self, cli):
        self.cli = cli
        # 后台监控线程会自动检测 NapCat 并启动监听
    
    def _load_config(self):
        """自动加载 NapCat OneBot11 配置"""
        try:
            # 查找 onebot11 配置文件
            config_dir = os.path.join(self.napcat_dir, "NapCat.44498.Shell", "versions")
            if not os.path.exists(config_dir):
                return
            
            # 查找版本目录
            for item in os.listdir(config_dir):
                version_dir = os.path.join(config_dir, item)
                if os.path.isdir(version_dir):
                    napcat_config = os.path.join(version_dir, "resources", "app", "napcat", "config")
                    if os.path.exists(napcat_config):
                        # 查找 onebot11_*.json
                        for f in os.listdir(napcat_config):
                            if f.startswith("onebot11_") and f.endswith(".json"):
                                config_path = os.path.join(napcat_config, f)
                                with open(config_path, 'r', encoding='utf-8') as fp:
                                    config = json.load(fp)
                                
                                network = config.get("network", {})
                                http_servers = network.get("httpServers", [])
                                for server in http_servers:
                                    if server.get("enable"):
                                        self.host = server.get("host", "127.0.0.1")
                                        self.port = server.get("port", 3000)
                                        self.token = server.get("token", "")
                                        print(f"[NapCat] 已加载配置: {self.host}:{self.port}, token={self.token[:8]}...")
                                        return
        except Exception as e:
            print(f"[NapCat] 加载配置失败: {e}")
    
    def _start_monitor_thread(self):
        """启动后台监控线程，定期检查 NapCat 状态并启动监听"""
        def monitor_loop():
            while self._monitor_running:
                try:
                    # 检查 NapCat API 是否可用
                    result = self._call_api("get_status")
                    if result.get("success"):
                        # 获取登录信息
                        if not self.login_user_id:
                            login_result = self._call_api("get_login_info")
                            if login_result.get("success"):
                                self.login_user_id = str(login_result["data"].get("user_id", ""))
                                print(f"[NapCat] 已登录账号: {self.login_user_id}")
                        
                        # 如果监听服务未启动，启动它
                        if not self.listen_server:
                            self.start_listener(self.listen_port)
                            print(f"[NapCat] 监听服务已启动，端口: {self.listen_port}")
                except Exception as e:
                    # 静默处理监控循环中的错误，避免刷屏
                    pass
                
                # 每5秒检查一次
                time.sleep(5)
        
        self._monitor_running = True
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        print(f"[NapCat] 后台监控线程已启动")
    
    def get_tool_info(self):
        return {
            "name": "napcat_qq",
            "description": "NapCat QQ机器人插件，通过OneBot协议接入QQ，支持自动安装、消息收发、群管理等操作",
            "keywords": ["qq", "机器人", "bot", "napcat", "onebot", "消息", "群管理"],
            "usage": self.usage
        }
    
    def get_mcp_definition(self):
        return {
            "name": "napcat_qq",
            "description": "NapCat QQ机器人插件，通过OneBot协议接入QQ，支持消息收发、群管理、图片发送、@消息自动转发AI等功能",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["install", "start", "stop", "status", "webui",
                                 "send_private", "send_group", "send_image", "recall",
                                 "login_info", "friend_list", "group_list", 
                                 "group_members", "group_notice", "get_msg", "get_chat_history",
                                 "ban", "unban", "kick", "set", "start_listen", "stop_listen"],
                        "description": "操作类型"
                    },
                    "user_id": {"type": "string", "description": "QQ号"},
                    "group_id": {"type": "string", "description": "群号"},
                    "message": {"type": "string", "description": "消息内容"},
                    "message_id": {"type": "string", "description": "消息ID"},
                    "image_path": {"type": "string", "description": "图片文件路径"},
                    "is_group": {"type": "boolean", "description": "是否群聊(发送图片时)"},
                    "duration": {"type": "integer", "description": "时长(秒)"},
                    "port": {"type": "integer", "description": "监听端口"},
                    "host": {"type": "string", "description": "服务地址"},
                    "token": {"type": "string", "description": "访问令牌"}
                },
                "required": ["operation"]
            }
        }
    
    def convert_mcp_args(self, arguments: Dict[str, Any]) -> str:
        op = arguments.get("operation", "")
        parts = [op]
        if op == "set":
            parts.extend([arguments.get("host", ""), str(arguments.get("port", 3000)), arguments.get("token", "")])
        elif op == "send_private":
            parts.extend([arguments.get("user_id", ""), arguments.get("message", "")])
        elif op == "send_group":
            parts.extend([arguments.get("group_id", ""), arguments.get("message", "")])
        elif op == "send_image":
            parts.extend([arguments.get("group_id", "") or arguments.get("user_id", ""),
                         arguments.get("image_path", ""),
                         "true" if arguments.get("is_group") else "false"])
        elif op in ("ban", "unban", "kick"):
            parts.extend([arguments.get("group_id", ""), arguments.get("user_id", "")])
            if op == "ban" and "duration" in arguments:
                parts.append(str(arguments["duration"]))
        elif op == "group_members":
            parts.append(arguments.get("group_id", ""))
        elif op == "group_notice":
            parts.append(arguments.get("group_id", ""))
        elif op == "get_msg":
            parts.append(arguments.get("message_id", ""))
        elif op == "get_chat_history":
            parts.append(arguments.get("group_id", ""))
        elif op == "start_listen":
            if "port" in arguments:
                parts.append(str(arguments["port"]))
        return " ".join(filter(None, parts))
    
    def handle(self, args: str) -> str:
        try:
            parts = self._parse_args(args)
            if not parts:
                return "错误：请提供操作类型。\n可用操作: install, start, stop, status, webui, send_private, send_group, ..."
            
            operation = parts[0].lower()
            
            handlers = {
                "install": self._op_install,
                "start": self._op_start,
                "stop": self._op_stop,
                "status": self._op_status,
                "webui": self._op_webui,
                "set": self._op_set,
                "test": self._op_status,
                "send_private": self._op_send_private,
                "send_group": self._op_send_group,
                "send_image": self._op_send_image,
                "recall": self._op_recall,
                "login_info": self._op_login_info,
                "friend_list": self._op_friend_list,
                "group_list": self._op_group_list,
                "group_info": self._op_group_info,
                "group_members": self._op_group_members,
                "group_notice": self._op_group_notice,
                "get_msg": self._op_get_msg,
                "get_chat_history": self._op_get_chat_history,
                "user_info": self._op_user_info,
                "ban": self._op_ban,
                "unban": self._op_unban,
                "kick": self._op_kick,
                "set_card": self._op_set_card,
                "set_group_name": self._op_set_group_name,
                "like": self._op_like,
                "poke": self._op_poke,
                # 新增群管理功能
                "set_admin": self._op_set_admin,
                "unset_admin": self._op_unset_admin,
                "set_group_special_title": self._op_set_special_title,
                "set_whole_ban": self._op_set_whole_ban,
                "leave_group": self._op_leave_group,
                # 新增请求处理功能
                "set_friend_add_request": self._op_set_friend_add_request,
                "set_group_add_request": self._op_set_group_add_request,
                # 新增消息功能
                "send_forward": self._op_send_forward,
                "get_forward_msg": self._op_get_forward_msg,
                # 新增系统功能
                "version": self._op_version,
                "restart": self._op_restart,
                # 监听
                "start_listen": self._op_start_listen,
                "stop_listen": self._op_stop_listen,
            }
            
            if operation in handlers:
                return handlers[operation](parts[1:])
            else:
                return f"错误：未知操作 '{operation}'\n可用操作: " + ", ".join(handlers.keys())
                
        except Exception as e:
            return f"处理请求失败: {e}"
    
    def _parse_args(self, args: str) -> List[str]:
        parts = []
        current = ""
        in_quotes = False
        quote_char = None
        for char in args:
            if char in ('"', "'") and not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char and in_quotes:
                in_quotes = False
                quote_char = None
            elif char == ' ' and not in_quotes:
                if current:
                    parts.append(current)
                    current = ""
            else:
                current += char
        if current:
            parts.append(current)
        return parts
    
    # ==================== 安装管理 ====================
    
    def _op_install(self, args: List[str]) -> str:
        """下载并安装 NapCat 到插件目录"""
        zip_path = os.path.join(self.plugin_dir, "NapCat.Shell.Windows.OneKey.zip")
        
        # 检查是否已安装 - 更新路径检测
        installer_exe = os.path.join(self.napcat_dir, "NapCatInstaller.exe")
        boot_exe = os.path.join(self.napcat_dir, "NapCat.44498.Shell", "NapCatWinBootMain.exe")
        boot_exe_alt = os.path.join(self.napcat_dir, "bootmain", "NapCatWinBootMain.exe")
        
        if os.path.exists(installer_exe) or os.path.exists(boot_exe) or os.path.exists(boot_exe_alt):
            return f"✅ NapCat 已安装于: {self.napcat_dir}\n运行 'napcat_qq start' 启动服务"
        
        try:
            # 创建目录
            os.makedirs(self.napcat_dir, exist_ok=True)
            
            # 下载
            print(f"正在下载 NapCat {NAPCAT_VERSION}...")
            print(f"下载地址: {NAPCAT_DOWNLOAD_URL}")
            print(f"保存到: {zip_path}")
            
            import urllib.request
            urllib.request.urlretrieve(NAPCAT_DOWNLOAD_URL, zip_path)
            print("下载完成")
            
            # 解压
            print(f"正在解压到: {self.napcat_dir}")
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(self.napcat_dir)
            
            # 清理zip
            os.remove(zip_path)
            
            return f"✅ NapCat 安装完成!\n安装目录: {self.napcat_dir}\n\n下一步:\n1. 运行 'napcat_qq start' 启动服务\n2. 在弹出的窗口中登录 QQ\n3. 访问 WebUI (http://127.0.0.1:6099) 配置 OneBot"
            
        except Exception as e:
            return f"❌ 安装失败: {e}\n请手动下载: {NAPCAT_DOWNLOAD_URL}\n解压到: {self.napcat_dir}"
    
    def _op_start(self, args: List[str]) -> str:
        """启动 NapCat"""
        # 查找启动程序 - 优先查找 NapCat.44498.Shell 目录
        boot_exe = os.path.join(self.napcat_dir, "NapCat.44498.Shell", "NapCatWinBootMain.exe")
        boot_exe_alt = os.path.join(self.napcat_dir, "bootmain", "NapCatWinBootMain.exe")
        installer_exe = os.path.join(self.napcat_dir, "NapCatInstaller.exe")
        
        if os.path.exists(boot_exe):
            exe_path = boot_exe
            work_dir = os.path.dirname(boot_exe)
        elif os.path.exists(boot_exe_alt):
            exe_path = boot_exe_alt
            work_dir = os.path.dirname(boot_exe_alt)
        elif os.path.exists(installer_exe):
            exe_path = installer_exe
            work_dir = os.path.dirname(installer_exe)
        else:
            return f"❌ 未找到 NapCat，请先运行 'napcat_qq install' 安装\n预期路径: {self.napcat_dir}"
        
        try:
            # 后台启动
            self._process = subprocess.Popen(
                [exe_path],
                cwd=work_dir,
                creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
            )
            
            # 等待几秒后检查是否成功启动并尝试启动监听
            time.sleep(3)
            self._try_start_listener()
            
            return f"✅ NapCat 已启动!\n- PID: {self._process.pid}\n- 安装目录: {self.napcat_dir}\n- WebUI: http://127.0.0.1:6099\n- HTTP API: http://127.0.0.1:3000\n\n请在弹出的窗口中登录 QQ"
        except Exception as e:
            return f"❌ 启动失败: {e}"
    
    def _try_start_listener(self):
        """尝试启动监听服务（后台线程中重试）"""
        def _retry_start():
            for i in range(10):  # 尝试 10 次
                try:
                    time.sleep(2)  # 等待 2 秒
                    result = self._call_api("get_status")
                    if result.get("success"):
                        # 获取登录信息
                        login_result = self._call_api("get_login_info")
                        if login_result.get("success"):
                            self.login_user_id = str(login_result["data"].get("user_id", ""))
                        
                        # 启动监听
                        if not self.listen_server:
                            if self.start_listener(self.listen_port):
                                print(f"[NapCat] 监听服务启动成功，端口: {self.listen_port}")
                                return
                except Exception as e:
                    print(f"[NapCat] 尝试启动监听 ({i+1}/10): {e}")
            print("[NapCat] 监听服务启动失败，请手动运行 napcat_qq start_listen")
        
        # 在后台线程中启动
        thread = threading.Thread(target=_retry_start, daemon=True)
        thread.start()
    
    def _op_stop(self, args: List[str]) -> str:
        """停止 NapCat"""
        try:
            if os.name == 'nt':
                subprocess.run(["taskkill", "/F", "/IM", "NapCatWinBootMain.exe"], 
                             capture_output=True, check=False)
                subprocess.run(["taskkill", "/F", "/IM", "QQ.exe"], 
                             capture_output=True, check=False)
            return "✅ NapCat 已停止"
        except Exception as e:
            return f"❌ 停止失败: {e}"
    
    def _op_status(self, args: List[str]) -> str:
        """查看运行状态"""
        # 检查安装状态 - 更新路径检测
        installer_exe = os.path.join(self.napcat_dir, "NapCatInstaller.exe")
        boot_exe = os.path.join(self.napcat_dir, "NapCat.44498.Shell", "NapCatWinBootMain.exe")
        boot_exe_alt = os.path.join(self.napcat_dir, "bootmain", "NapCatWinBootMain.exe")
        installed = os.path.exists(installer_exe) or os.path.exists(boot_exe) or os.path.exists(boot_exe_alt)
        
        # 检查进程
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq NapCatWinBootMain.exe"],
                capture_output=True, text=True, check=False
            )
            running = "NapCatWinBootMain.exe" in result.stdout
        except:
            running = False
        
        # 测试 API 连接
        try:
            resp = requests.get(f"http://{self.host}:{self.port}/get_status", timeout=3)
            api_ok = resp.status_code == 200
            data = resp.json().get("data", {})
        except:
            api_ok = False
            data = {}
        
        lines = ["📊 NapCat 状态"]
        lines.append(f"- 安装: {'✅ 已安装' if installed else '❌ 未安装'}")
        if installed:
            lines.append(f"- 目录: {self.napcat_dir}")
        lines.append(f"- 进程: {'✅ 运行中' if running else '❌ 未运行'}")
        lines.append(f"- API: {'✅ 可用' if api_ok else '❌ 不可用'} ({self.host}:{self.port})")
        
        if api_ok and data:
            lines.append(f"- 在线: {'是' if data.get('online') else '否'}")
            lines.append(f"- 状态: {data.get('status', '未知')}")
        
        return "\n".join(lines)
    
    def _op_webui(self, args: List[str]) -> str:
        """打开 WebUI"""
        import webbrowser
        webbrowser.open("http://127.0.0.1:6099")
        return "✅ 已打开 WebUI: http://127.0.0.1:6099\n密码请在 NapCat 控制台中查看"
    
    # ==================== 消息监听 ====================
    
    def start_listener(self, port: int = 3100):
        """启动消息监听服务"""
        self.listen_port = port
        
        # 获取当前登录的QQ号
        result = self._call_api("get_login_info")
        if result["success"]:
            self.login_user_id = str(result["data"].get("user_id", ""))
        
        # 创建HTTP请求处理器
        plugin = self
        class EventHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                pass  # 禁用默认日志
            
            def do_POST(self):
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else ""
                
                # 打印原始请求便于调试
                print(f"[NapCat] 收到请求: length={content_length}, body={body[:200] if body else 'empty'}")
                
                # 始终返回 200，避免 NapCat 重试
                self.send_response(200)
                self.end_headers()
                
                # 空请求体直接返回
                if not body.strip():
                    self.wfile.write(b'{"status":"empty"}')
                    return
                
                try:
                    event = json.loads(body)
                    print(f"[NapCat] 事件类型: {event.get('post_type', 'unknown')}")
                    plugin._handle_event(event)
                    self.wfile.write(b'{"status":"ok"}')
                except json.JSONDecodeError as e:
                    print(f"[NapCat] JSON解析错误: {e}")
                    self.wfile.write(b'{"status":"json_error"}')
                except Exception as e:
                    print(f"[NapCat] 处理事件错误: {e}")
                    self.wfile.write(f'{{"status":"error"}}'.encode())
        
        try:
            self.listen_server = HTTPServer(('0.0.0.0', port), EventHandler)
            self.listen_thread = threading.Thread(target=self.listen_server.serve_forever, daemon=True)
            self.listen_thread.start()
            print(f"[NapCat] 消息监听服务已启动，端口: {port}")
            return True
        except Exception as e:
            print(f"[NapCat] 启动监听服务失败: {e}")
            return False
    
    def stop_listener(self):
        """停止消息监听服务"""
        if self.listen_server:
            self.listen_server.shutdown()
            self.listen_server = None
            print("[NapCat] 消息监听服务已停止")
    
    def _handle_event(self, event: Dict):
        """处理上报事件"""
        try:
            post_type = event.get("post_type", "")
            
            # 只处理消息事件
            if post_type != "message":
                return
            
            message_type = event.get("message_type", "")
            
            # 只处理群消息
            if message_type != "group":
                return
            
            group_id = str(event.get("group_id", ""))
            user_id = str(event.get("user_id", ""))
            sender = event.get("sender", {})
            nickname = sender.get("nickname", sender.get("card", "未知"))
            message = event.get("message", [])
            
            print(f"[NapCat] 群消息: 群={group_id}, 用户={nickname}({user_id})")
            
            # 检查是否@了机器人
            is_at_me = False
            text_content = ""
            
            for msg_part in message:
                if isinstance(msg_part, dict):
                    msg_type = msg_part.get("type", "")
                    msg_data = msg_part.get("data", {})
                    
                    # 检查@消息
                    if msg_type == "at":
                        at_qq = str(msg_data.get("qq", ""))
                        print(f"[NapCat] @消息: at_qq={at_qq}, login_user_id={self.login_user_id}")
                        if at_qq == self.login_user_id:
                            is_at_me = True
                    
                    # 提取文本内容（忽略文件）
                    elif msg_type == "text":
                        text_content += msg_data.get("text", "")
                    
                    # 忽略文件、图片等
                    elif msg_type in ("file", "image", "video", "audio", "record"):
                        continue
            
            print(f"[NapCat] is_at_me={is_at_me}, text={text_content[:50] if text_content else 'empty'}")
            
            # 如果@了机器人，转发给AI
            if is_at_me and text_content.strip():
                self._forward_to_ai(group_id, user_id, nickname, text_content.strip())
        except Exception as e:
            print(f"[NapCat] _handle_event 错误: {e}")
    
    def _forward_to_ai(self, group_id: str, user_id: str, nickname: str, content: str):
        """转发消息给AI"""
        try:
            print(f"[NapCat] 转发消息给AI: 群={group_id}, 内容={content[:30]}...")
            
            # 获取群名
            group_name = "未知群"
            try:
                result = self._call_api("get_group_info", params={"group_id": int(group_id)})
                if result["success"]:
                    group_name = result["data"].get("group_name", "未知群")
            except:
                pass
            
            # 构建转发消息
            forward_msg = f"[QQ群消息转发]\n群名: {group_name}\n群号: {group_id}\n发送者: {nickname}\nQQ号: {user_id}\n内容: {content}"
            
            print(f"[NapCat] 转发内容:\n{forward_msg}")
            
            # 直接调用 CLI 的接口发送给 AI
            reply = None
            if self.cli and hasattr(self.cli, 'handle_plugin_message'):
                try:
                    reply = self.cli.handle_plugin_message(forward_msg, group_id=group_id, user_id=user_id)
                    print(f"[NapCat] AI回复: {reply[:50] if reply else 'None'}...")
                except Exception as e:
                    print(f"[NapCat] AI处理失败: {e}")
                    reply = None
            else:
                print(f"[NapCat] CLI 不可用: cli={self.cli is not None}, has_handle={hasattr(self.cli, 'handle_plugin_message') if self.cli else False}")
            
            # 如果AI返回了回复，发送到群里
            if reply:
                send_result = self._call_api("send_group_msg", data={
                    "group_id": int(group_id),
                    "message": reply
                })
                if send_result["success"]:
                    print(f"[NapCat] 已发送回复到群 {group_id}")
                else:
                    print(f"[NapCat] 发送回复失败: {send_result.get('error')}")
        except Exception as e:
            print(f"[NapCat] _forward_to_ai 错误: {e}")
    
    # ==================== API 调用 ====================
    
    def _get_base_url(self) -> str:
        return f"http://{self.host}:{self.port}"
    
    def _call_api(self, endpoint: str, params: Dict = None, data: Dict = None) -> Dict:
        url = f"{self._get_base_url()}/{endpoint}"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        
        try:
            if data:
                response = requests.post(url, json=data, headers=headers, timeout=self.timeout)
            else:
                response = requests.get(url, params=params, headers=headers, timeout=self.timeout)
            
            result = response.json()
            if result.get("status") == "failed":
                return {"success": False, "error": result.get("wording", "未知错误")}
            return {"success": True, "data": result.get("data", result)}
            
        except requests.exceptions.ConnectionError:
            return {"success": False, "error": f"无法连接到 NapCat ({self.host}:{self.port})，请确认服务已启动"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _op_set(self, args: List[str]) -> str:
        if len(args) < 2:
            return f"当前配置:\n- 地址: {self.host}:{self.port}\n- Token: {self.token or '无'}"
        self.host = args[0]
        self.port = int(args[1]) if len(args) > 1 else 3000
        self.token = args[2] if len(args) > 2 else ""
        return f"已设置: {self.host}:{self.port}"
    
    def _op_send_private(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供 QQ号 和 消息内容"
        result = self._call_api("send_private_msg", data={
            "user_id": int(args[0]),
            "message": " ".join(args[1:])
        })
        if result["success"]:
            return f"✅ 私聊已发送到 {args[0]}"
        return f"❌ 发送失败: {result['error']}"
    
    def _op_send_group(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供 群号 和 消息内容"
        result = self._call_api("send_group_msg", data={
            "group_id": int(args[0]),
            "message": " ".join(args[1:])
        })
        if result["success"]:
            return f"✅ 群消息已发送到 {args[0]}"
        return f"❌ 发送失败: {result['error']}"
    
    def _op_recall(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供消息ID"
        result = self._call_api("delete_msg", data={"message_id": int(args[0])})
        return f"✅ 消息已撤回" if result["success"] else f"❌ 撤回失败: {result['error']}"
    
    def _op_login_info(self, args: List[str]) -> str:
        result = self._call_api("get_login_info")
        if result["success"]:
            d = result["data"]
            return f"📱 QQ号: {d.get('user_id')}\n昵称: {d.get('nickname')}"
        return f"❌ 获取失败: {result['error']}"
    
    def _op_friend_list(self, args: List[str]) -> str:
        result = self._call_api("get_friend_list")
        if result["success"]:
            friends = result["data"]
            lines = [f"📋 好友列表 (共 {len(friends)} 人)"]
            for f in friends[:15]:
                lines.append(f"  - {f.get('nickname')} ({f.get('user_id')})")
            if len(friends) > 15:
                lines.append(f"  ... 还有 {len(friends)-15} 人")
            return "\n".join(lines)
        return f"❌ 获取失败: {result['error']}"
    
    def _op_group_list(self, args: List[str]) -> str:
        result = self._call_api("get_group_list")
        if not result["success"]:
            return f"❌ 获取失败: {result['error']}"
        
        groups = result.get("data", [])
        if not isinstance(groups, list):
            groups = []
        
        if not groups:
            return "📭 没有加入任何群"
        
        lines = [f"📋 群列表 (共 {len(groups)} 个)", "格式: 群号 | 群名"]
        for g in groups[:20]:
            gid = g.get("group_id", "")
            gname = g.get("group_name", "未知")
            lines.append(f"  {gid} | {gname}")
        if len(groups) > 20:
            lines.append(f"  ... 还有 {len(groups)-20} 个群")
        lines.append("\n使用 send_group <群号> <消息> 发送群消息")
        return "\n".join(lines)
    
    def _op_group_info(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供群号"
        result = self._call_api("get_group_info", params={"group_id": int(args[0])})
        if result["success"]:
            d = result["data"]
            return f"📊 群信息\n- 群号: {d.get('group_id')}\n- 群名: {d.get('group_name')}\n- 成员: {d.get('member_count')}"
        return f"❌ 获取失败: {result['error']}"
    
    def _op_group_members(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供群号"
        result = self._call_api("get_group_member_list", params={"group_id": int(args[0])})
        if result["success"]:
            members = result["data"]
            lines = [f"📋 群成员 (共 {len(members)} 人)"]
            for m in members[:15]:
                role = {"owner": "群主", "admin": "管理"}.get(m.get("role"), "")
                lines.append(f"  - [{role}] {m.get('nickname')} ({m.get('user_id')})")
            return "\n".join(lines)
        return f"❌ 获取失败: {result['error']}"
    
    def _op_user_info(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供QQ号"
        result = self._call_api("get_stranger_info", params={"user_id": int(args[0])})
        if result["success"]:
            d = result["data"]
            return f"👤 QQ号: {d.get('user_id')}\n昵称: {d.get('nickname')}"
        return f"❌ 获取失败: {result['error']}"
    
    def _op_ban(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供 群号 和 QQ号"
        result = self._call_api("set_group_ban", data={
            "group_id": int(args[0]),
            "user_id": int(args[1]),
            "duration": int(args[2]) if len(args) > 2 else 1800
        })
        return f"✅ 已禁言" if result["success"] else f"❌ 禁言失败: {result['error']}"
    
    def _op_unban(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供 群号 和 QQ号"
        result = self._call_api("set_group_ban", data={
            "group_id": int(args[0]),
            "user_id": int(args[1]),
            "duration": 0
        })
        return f"✅ 已解除禁言" if result["success"] else f"❌ 解除失败: {result['error']}"
    
    def _op_kick(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供 群号 和 QQ号"
        result = self._call_api("set_group_kick", data={
            "group_id": int(args[0]),
            "user_id": int(args[1])
        })
        return f"✅ 已踢出" if result["success"] else f"❌ 踢出失败: {result['error']}"
    
    def _op_set_card(self, args: List[str]) -> str:
        if len(args) < 3:
            return "错误：请提供 群号、QQ号 和 名片"
        result = self._call_api("set_group_card", data={
            "group_id": int(args[0]),
            "user_id": int(args[1]),
            "card": " ".join(args[2:])
        })
        return f"✅ 已设置名片" if result["success"] else f"❌ 设置失败: {result['error']}"
    
    def _op_set_group_name(self, args: List[str]) -> str:
        if len(args) < 2:
            return "错误：请提供 群号 和 名称"
        result = self._call_api("set_group_name", data={
            "group_id": int(args[0]),
            "group_name": " ".join(args[1:])
        })
        return f"✅ 已设置群名" if result["success"] else f"❌ 设置失败: {result['error']}"
    
    def _op_like(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供QQ号"
        result = self._call_api("send_like", data={
            "user_id": int(args[0]),
            "times": int(args[1]) if len(args) > 1 else 1
        })
        return f"✅ 已点赞" if result["success"] else f"❌ 点赞失败: {result['error']}"
    
    def _op_poke(self, args: List[str]) -> str:
        if not args:
            return "错误：请提供QQ号或群号"
        is_group = "-g" in args
        target = args[0]
        if is_group:
            result = self._call_api("group_poke", data={"group_id": int(target)})
        else:
            result = self._call_api("friend_poke", data={"user_id": int(target)})
        return f"✅ 已戳一戳" if result["success"] else f"❌ 失败: {result['error']}"
    
    # ==================== 新增功能 ====================
    
    def _op_group_notice(self, args: List[str]) -> str:
        """获取群公告"""
        if not args:
            return "错误：请提供群号"
        result = self._call_api("_get_group_notice", params={"group_id": int(args[0])})
        if not result["success"]:
            return f"❌ 获取失败: {result['error']}"
        
        notices = result.get("data", [])
        if not isinstance(notices, list):
            notices = [notices] if notices else []
        
        if not notices:
            return "📭 该群暂无公告"
        
        lines = [f"📢 群公告 (共 {len(notices)} 条)"]
        for i, n in enumerate(notices[:5], 1):
            content = n.get("notice_text", n.get("content", ""))
            sender = n.get("sender_id", "未知")
            lines.append(f"\n--- 公告 {i} ---")
            lines.append(f"发布者: {sender}")
            lines.append(f"内容: {content[:200]}{'...' if len(content) > 200 else ''}")
        
        return "\n".join(lines)
    
    def _op_get_msg(self, args: List[str]) -> str:
        """获取消息详情"""
        if not args:
            return "错误：请提供消息ID"
        result = self._call_api("get_msg", params={"message_id": int(args[0])})
        if not result["success"]:
            return f"❌ 获取失败: {result['error']}"
        
        msg = result.get("data", {})
        lines = ["📨 消息详情"]
        lines.append(f"- 消息ID: {msg.get('message_id')}")
        lines.append(f"- 发送者: {msg.get('sender', {}).get('nickname', '未知')} ({msg.get('sender', {}).get('user_id', '')})")
        lines.append(f"- 时间: {msg.get('time', '')}")
        
        # 解析消息内容
        content = msg.get("message", "")
        if isinstance(content, list):
            text_parts = []
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_parts.append(part.get("data", {}).get("text", ""))
                    elif part.get("type") == "image":
                        text_parts.append("[图片]")
                    elif part.get("type") == "at":
                        text_parts.append(f"@{part.get('data', {}).get('qq', '')}")
                elif isinstance(part, str):
                    text_parts.append(part)
            content = "".join(text_parts)
        
        lines.append(f"- 内容: {content}")
        return "\n".join(lines)
    
    def _op_get_chat_history(self, args: List[str]) -> str:
        """获取群聊天记录"""
        if not args:
            return "错误：请提供群号"
        
        group_id = int(args[0])
        
        # 先获取群成员列表来获取消息序号
        members_result = self._call_api("get_group_member_list", params={"group_id": group_id})
        if not members_result["success"]:
            return f"❌ 获取群成员失败: {members_result['error']}"
        
        # 尝试获取聊天记录
        result = self._call_api("get_group_msg_history", params={"group_id": group_id})
        if not result["success"]:
            return f"❌ 获取聊天记录失败: {result['error']}\n提示: 此功能可能需要特殊权限"
        
        messages = result.get("data", {}).get("messages", [])
        if not messages:
            return "📭 没有获取到聊天记录"
        
        lines = [f"💬 群聊天记录 (最近 {len(messages)} 条)"]
        for msg in messages[-15:]:
            sender = msg.get("sender", {})
            nickname = sender.get("nickname", sender.get("card", "未知"))
            
            # 解析消息内容
            content = msg.get("message", "")
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict):
                        if part.get("type") == "text":
                            text_parts.append(part.get("data", {}).get("text", ""))
                        elif part.get("type") == "image":
                            text_parts.append("[图片]")
                        elif part.get("type") == "at":
                            text_parts.append(f"@{part.get('data', {}).get('qq', '')}")
                    elif isinstance(part, str):
                        text_parts.append(part)
                content = "".join(text_parts)
            
            lines.append(f"[{nickname}]: {content[:100]}")
        
        return "\n".join(lines)
    
    def _op_send_image(self, args: List[str]) -> str:
        """发送图片"""
        if len(args) < 2:
            return "错误：请提供 目标ID 和 图片路径\n用法: send_image <群号/QQ号> <图片路径> [true/false是否群聊]"
        
        target_id = args[0]
        image_path = args[1]
        is_group = len(args) > 2 and args[2].lower() in ("true", "1", "yes", "群")
        
        # 检查图片文件
        if not os.path.exists(image_path):
            # 尝试相对路径
            full_path = os.path.abspath(image_path)
            if not os.path.exists(full_path):
                return f"❌ 图片文件不存在: {image_path}"
            image_path = full_path
        
        # 使用 file:// 协议或 base64
        try:
            import base64
            with open(image_path, "rb") as f:
                img_data = base64.b64encode(f.read()).decode("utf-8")
            
            # 获取图片格式
            ext = os.path.splitext(image_path)[1].lower().replace(".", "")
            if ext == "jpg":
                ext = "jpeg"
            
            image_url = f"base64://{img_data}"
            
        except Exception as e:
            return f"❌ 读取图片失败: {e}"
        
        # 构建消息
        message = [
            {
                "type": "image",
                "data": {"file": image_url}
            }
        ]
        
        if is_group:
            result = self._call_api("send_group_msg", data={
                "group_id": int(target_id),
                "message": message
            })
            target_type = "群"
        else:
            result = self._call_api("send_private_msg", data={
                "user_id": int(target_id),
                "message": message
            })
            target_type = "用户"
        
        if result["success"]:
            return f"✅ 图片已发送到{target_type} {target_id}"
        return f"❌ 发送失败: {result['error']}"
    
    def _op_start_listen(self, args: List[str]) -> str:
        """启动消息监听"""
        port = int(args[0]) if args else 3100
        
        # 首先需要在 NapCat 配置中添加 HTTP 上报
        # 检查是否已配置上报
        result = self._call_api("get_status")
        if not result["success"]:
            return f"❌ NapCat 服务未连接，请先启动"
        
        if self.listen_server:
            return f"⚠️ 监听服务已在运行，端口: {self.listen_port}"
        
        # 启动监听
        if self.start_listener(port):
            # 提示用户需要在 WebUI 配置 HTTP 上报
            return f"""✅ 消息监听服务已启动!
- 监听端口: {port}
- 登录账号: {self.login_user_id}

【重要】请在 NapCat WebUI 中配置 HTTP 上报:
1. 打开 http://127.0.0.1:6099
2. 进入「网络配置」->「HTTP 上报」
3. 添加上报地址: http://127.0.0.1:{port}
4. 保存配置

当群内有人 @{self.login_user_id} 时，消息会自动转发给AI处理"""
        return f"❌ 启动监听失败"
    
    def _op_stop_listen(self, args: List[str]) -> str:
        """停止消息监听"""
        self.stop_listener()
        return "✅ 消息监听服务已停止"
    
    # ==================== 群管理扩展功能 ====================
    
    def _op_set_admin(self, args: List[str]) -> str:
        """设置群管理员"""
        if len(args) < 2:
            return "错误：请提供群号和QQ号\n用法: set_admin <群号> <QQ号>"
        result = self._call_api("set_group_admin", data={
            "group_id": int(args[0]),
            "user_id": int(args[1]),
            "enable": True
        })
        return f"✅ 已设置为管理员" if result["success"] else f"❌ 失败: {result['error']}"
    
    def _op_unset_admin(self, args: List[str]) -> str:
        """取消群管理员"""
        if len(args) < 2:
            return "错误：请提供群号和QQ号\n用法: unset_admin <群号> <QQ号>"
        result = self._call_api("set_group_admin", data={
            "group_id": int(args[0]),
            "user_id": int(args[1]),
            "enable": False
        })
        return f"✅ 已取消管理员" if result["success"] else f"❌ 失败: {result['error']}"
    
    def _op_set_special_title(self, args: List[str]) -> str:
        """设置群头衔"""
        if len(args) < 3:
            return "错误：请提供群号、QQ号和头衔\n用法: set_group_special_title <群号> <QQ号> <头衔>"
        result = self._call_api("set_group_special_title", data={
            "group_id": int(args[0]),
            "user_id": int(args[1]),
            "special_title": " ".join(args[2:])
        })
        return f"✅ 已设置头衔" if result["success"] else f"❌ 失败: {result['error']}"
    
    def _op_set_whole_ban(self, args: List[str]) -> str:
        """设置全员禁言"""
        if len(args) < 2:
            return "错误：请提供群号和开关(on/off)\n用法: set_whole_ban <群号> <on/off>"
        enable = args[1].lower() in ("on", "true", "1", "yes")
        result = self._call_api("set_group_whole_ban", data={
            "group_id": int(args[0]),
            "enable": enable
        })
        status = "开启" if enable else "关闭"
        return f"✅ 已{status}全员禁言" if result["success"] else f"❌ 失败: {result['error']}"
    
    def _op_leave_group(self, args: List[str]) -> str:
        """退出群"""
        if not args:
            return "错误：请提供群号\n用法: leave_group <群号>"
        result = self._call_api("set_group_leave", data={
            "group_id": int(args[0])
        })
        return f"✅ 已退出群" if result["success"] else f"❌ 失败: {result['error']}"
    
    # ==================== 请求处理功能 ====================
    
    def _op_set_friend_add_request(self, args: List[str]) -> str:
        """处理好友请求"""
        if len(args) < 2:
            return "错误：请提供请求标识和操作\n用法: set_friend_add_request <flag> <accept/reject> [备注]"
        flag = args[0]
        approve = args[1].lower() == "accept"
        remark = args[2] if len(args) > 2 else ""
        result = self._call_api("set_friend_add_request", data={
            "flag": flag,
            "approve": approve,
            "remark": remark
        })
        action = "已同意" if approve else "已拒绝"
        return f"✅ {action}好友请求" if result["success"] else f"❌ 失败: {result['error']}"
    
    def _op_set_group_add_request(self, args: List[str]) -> str:
        """处理加群请求"""
        if len(args) < 2:
            return "错误：请提供请求标识和操作\n用法: set_group_add_request <flag> <accept/reject> [理由]"
        flag = args[0]
        approve = args[1].lower() == "accept"
        reason = " ".join(args[2:]) if len(args) > 2 else ""
        result = self._call_api("set_group_add_request", data={
            "flag": flag,
            "approve": approve,
            "reason": reason
        })
        action = "已同意" if approve else "已拒绝"
        return f"✅ {action}加群请求" if result["success"] else f"❌ 失败: {result['error']}"
    
    # ==================== 消息扩展功能 ====================
    
    def _op_send_forward(self, args: List[str]) -> str:
        """发送合并转发消息"""
        if len(args) < 2:
            return "错误：请提供群号和消息内容\n用法: send_forward <群号> <消息内容>"
        group_id = int(args[0])
        content = " ".join(args[1:])
        # 构建转发消息
        messages = [{
            "type": "node",
            "data": {
                "name": "消息",
                "uin": self.login_user_id or "0",
                "content": content
            }
        }]
        result = self._call_api("send_group_forward_msg", data={
            "group_id": group_id,
            "messages": messages
        })
        return f"✅ 合并转发消息已发送" if result["success"] else f"❌ 失败: {result['error']}"
    
    def _op_get_forward_msg(self, args: List[str]) -> str:
        """获取合并转发消息内容"""
        if not args:
            return "错误：请提供消息ID\n用法: get_forward_msg <消息ID>"
        result = self._call_api("get_forward_msg", params={"message_id": args[0]})
        if not result["success"]:
            return f"❌ 获取失败: {result['error']}"
        messages = result.get("data", [])
        if isinstance(messages, list):
            lines = ["📜 合并转发消息内容:"]
            for msg in messages:
                sender = msg.get("sender", {}).get("nickname", "未知")
                content = msg.get("content", "")
                lines.append(f"[{sender}] {content}")
            return "\n".join(lines)
        return f"消息内容: {messages}"
    
    # ==================== 系统功能 ====================
    
    def _op_version(self, args: List[str]) -> str:
        """获取版本信息"""
        result = self._call_api("get_version_info")
        if not result["success"]:
            return f"❌ 获取失败: {result['error']}"
        data = result.get("data", {})
        lines = ["📋 版本信息:"]
        if isinstance(data, dict):
            for key, value in data.items():
                lines.append(f"- {key}: {value}")
        else:
            lines.append(str(data))
        return "\n".join(lines)
    
    def _op_restart(self, args: List[str]) -> str:
        """重启 NapCat"""
        delay = int(args[0]) if args else 0
        result = self._call_api("set_restart", data={"delay": delay})
        if result["success"]:
            return f"✅ NapCat 将在 {delay} 毫秒后重启"
        return f"❌ 重启失败: {result.get('error', '未知错误')}"


if __name__ == "__main__":
    plugin = Plugin()
    print("NapCat QQ机器人插件")
    print(f"插件目录: {plugin.plugin_dir}")