import threading
import time
from colorama import Fore, Style

from .constants import CLAWLI_SERVER_AVAILABLE, WEBSOCKET_AVAILABLE
from .tool_result import normalize_tool_text

try:
    import clawli_server
except ImportError:
    clawli_server = None

try:
    import websocket_server
except ImportError:
    websocket_server = None


class ClawliMixin:
    """Clawli 远程模式相关方法"""

    def _start_clawli_monitor(self):
        """启动 Clawli 消息监控线程"""
        if self._clawli_monitor_running:
            return

        self._clawli_monitor_running = True
        print(f"{Fore.CYAN}[Clawli] 消息监控线程已启动{Style.RESET_ALL}")

        def monitor_loop():
            while self._clawli_monitor_running and self.is_clawli_mode:
                try:
                    if CLAWLI_SERVER_AVAILABLE and clawli_server:
                        messages = clawli_server.get_messages()
                        if messages:
                            print(f"[Clawli Monitor] 收到 {len(messages)} 条消息")
                        for msg in messages:
                            self._handle_clawli_message(msg)
                    time.sleep(0.1)  # 100ms 检查间隔
                except Exception as e:
                    print(f"[Clawli Monitor] 错误: {e}")

        self._clawli_monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._clawli_monitor_thread.start()

    def _stop_clawli_monitor(self):
        """停止 Clawli 消息监控线程"""
        self._clawli_monitor_running = False
        if self._clawli_monitor_thread:
            self._clawli_monitor_thread.join(timeout=1)
            self._clawli_monitor_thread = None

    def _handle_clawli_message(self, msg: dict):
        """处理来自手机端的消息"""
        try:
            msg_type = msg.get("type", "")

            if msg_type == "message":
                content = msg.get("content", "")
                self._process_clawli_user_message(content)

            elif msg_type == "file":
                file_path = msg.get("path", "")
                text = msg.get("text", "")
                category = msg.get("category", "file")

                if category == "image":
                    self._process_clawli_image(file_path, text)
                else:
                    self._process_clawli_user_message(f"@{file_path}\n{text}")

        except Exception as e:
            print(f"[Clawli] 处理消息错误: {e}")

    def _process_clawli_user_message(self, content: str):
        """处理 Clawli 用户消息"""
        if not self.current_engine:
            return

        full_content = f"{content}\n\n[此消息由 Clawli 手机端发送]"

        self.shared_conversation_history.append({
            "role": "user",
            "content": full_content
        })

        system_prompt = self._build_system_prompt(self.get_liugin_usage_prompts())
        response = self.current_engine.generate_response(full_content, system_prompt=system_prompt)

        self._process_clawli_response(response)

    def _process_clawli_response(self, response: str):
        """处理 Clawli AI 响应"""
        text_content, json_data = self._parse_mixed_response(response)

        if json_data:
            tool_calls = self._extract_tool_calls(json_data)

            if tool_calls:
                result_texts = []
                for tool_data in tool_calls:
                    tool_name = tool_data.get('tool', '未知工具')
                    tool_args = tool_data.get('args', '')

                    if CLAWLI_SERVER_AVAILABLE and clawli_server:
                        clawli_server.send_tool_status(tool_name, tool_args, "calling")

                    result = self.process_tool_call(tool_data)
                    result_text = normalize_tool_text(result)
                    result_texts.append(result_text)

                    if CLAWLI_SERVER_AVAILABLE and clawli_server:
                        clawli_server.send_tool_status(tool_name, tool_args, "success", result_text)

                self.shared_conversation_history.append({
                    "role": "assistant",
                    "content": response
                })

                # 汇总全部工具结果（此前只回传了最后一个）
                tool_result_str = "\n".join([f"工具执行结果: {r}" for r in result_texts])
                self._process_clawli_user_message(f"{tool_result_str}\n请根据工具执行结果继续回答。")
                return

        final_response = text_content if text_content else response

        self.shared_conversation_history.append({
            "role": "assistant",
            "content": final_response
        })

        if CLAWLI_SERVER_AVAILABLE and clawli_server:
            clawli_server.send_message(final_response)

    def _process_clawli_image(self, image_path: str, text: str):
        """处理 Clawli 图片消息"""
        try:
            image_engine = getattr(self, 'image_engine', None)
            if not image_engine:
                try:
                    from image_engine import get_image_engine
                    image_engine = get_image_engine()
                except Exception:
                    image_engine = None

            if image_engine:
                with open(image_path, 'rb') as f:
                    image_data = f.read()

                result = image_engine.analyze(image_data, text or "请描述这张图片")
                self._process_clawli_user_message(f"@{image_path}\n图片内容: {result}\n\n{text}")
            else:
                self._process_clawli_user_message(f"@{image_path}\n{text}")

        except Exception as e:
            self._process_clawli_user_message(f"@{image_path}\n图片处理失败: {e}\n{text}")

    def _handle_remote_command(self, args):
        """处理远程连接命令"""
        if not WEBSOCKET_AVAILABLE:
            print(f"{Fore.RED}错误: websockets 库未安装{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}请运行: pip install websockets{Style.RESET_ALL}")
            return

        args = args.strip()

        if not args or args == '':
            print(f"\n{Fore.CYAN}{'='*55}{Style.RESET_ALL}")
            print(f"{Fore.CYAN}  远程连接命令帮助{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*55}{Style.RESET_ALL}")
            print(f"\n{Fore.WHITE}本地模式 (局域网直连):{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  /remote start <端口> <密码>{Style.RESET_ALL}")
            print(f"{Fore.WHITE}    端口: 监听端口 (默认9079){Style.RESET_ALL}")
            print(f"{Fore.WHITE}    密码: PC密码 (安卓端需要输入){Style.RESET_ALL}")
            print(f"\n{Fore.WHITE}代理模式 (无公网IP，通过中继服务器):{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  /remote proxy <服务器> <服务器密码> <PC端口> <PC密码>{Style.RESET_ALL}")
            print(f"{Fore.WHITE}    服务器: 中继服务器地址:端口{Style.RESET_ALL}")
            print(f"{Fore.WHITE}    服务器密码: 连接中继服务器的密码{Style.RESET_ALL}")
            print(f"{Fore.WHITE}    PC端口: 在服务器上使用的端口{Style.RESET_ALL}")
            print(f"{Fore.WHITE}    PC密码: 安卓端连接时需要验证{Style.RESET_ALL}")
            print(f"\n{Fore.WHITE}其他命令:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  /remote stop     - 停止服务{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  /remote status   - 查看状态{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  /remote ip       - 查看本机IP{Style.RESET_ALL}")
            print(f"\n{Fore.CYAN}{'='*55}{Style.RESET_ALL}")
            print(f"\n{Fore.GREEN}示例:{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  /remote start 9079 mypassword{Style.RESET_ALL}")
            print(f"{Fore.WHITE}  /remote proxy relay.example.com:9079 serverpwd 12345 pcpwd{Style.RESET_ALL}")
            print(f"{Fore.CYAN}{'='*55}{Style.RESET_ALL}\n")
            return

        parts = args.split()
        cmd = parts[0].lower()

        if cmd == 'start':
            port = 9079
            password = ""

            if len(parts) == 2:
                arg = parts[1]
                if arg.isdigit():
                    port = int(arg)
                    print(f"{Fore.RED}错误: 请设置PC密码{Style.RESET_ALL}")
                    print(f"{Fore.YELLOW}用法: /remote start {port} <密码>{Style.RESET_ALL}")
                    return
                else:
                    password = arg
            elif len(parts) >= 3:
                try:
                    port = int(parts[1])
                    password = parts[2]
                except ValueError:
                    password = parts[1]

            if not password:
                print(f"{Fore.RED}错误: 请设置PC密码{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}用法: /remote start <端口> <密码>{Style.RESET_ALL}")
                return

            if len(password) < 4:
                print(f"{Fore.RED}错误: 密码至少4个字符{Style.RESET_ALL}")
                return

            if CLAWLI_SERVER_AVAILABLE and clawli_server:
                success = clawli_server.start_server("0.0.0.0", port, password)
                if success:
                    self.is_clawli_mode = True
                    self._start_clawli_monitor()
            elif websocket_server:
                websocket_server.start_local_server(self, port, password)

        elif cmd == 'proxy':
            if len(parts) < 5:
                print(f"{Fore.RED}参数不足{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}用法: /remote proxy <服务器> <服务器密码> <PC端口> <PC密码>{Style.RESET_ALL}")
                print(f"{Fore.WHITE}示例: /remote proxy relay.example.com:9079 serverpwd 12345 pcpwd{Style.RESET_ALL}")
                return

            server_addr = parts[1]
            server_password = parts[2]
            pc_port = 0
            pc_password = parts[4] if len(parts) > 4 else ""

            try:
                pc_port = int(parts[3])
                if pc_port < 10000 or pc_port > 19999:
                    print(f"{Fore.YELLOW}建议端口范围: 10000-19999{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED}无效的端口号: {parts[3]}{Style.RESET_ALL}")
                return

            if not pc_password:
                print(f"{Fore.RED}错误: 请设置PC密码{Style.RESET_ALL}")
                return

            if len(pc_password) < 4:
                print(f"{Fore.RED}错误: PC密码至少4个字符{Style.RESET_ALL}")
                return

            if ':' in server_addr:
                server_host, port_str = server_addr.rsplit(':', 1)
                try:
                    server_port = int(port_str)
                except ValueError:
                    print(f"{Fore.RED}无效的服务器端口: {port_str}{Style.RESET_ALL}")
                    return
            else:
                server_host = server_addr
                server_port = 9079

            print(f"{Fore.CYAN}正在连接中继服务器...{Style.RESET_ALL}")
            if websocket_server:
                websocket_server.start_proxy_client(
                    self, server_host, server_port,
                    server_password, pc_port, pc_password
                )

        elif cmd == 'stop':
            if CLAWLI_SERVER_AVAILABLE and clawli_server:
                clawli_server.stop_server()
                self.is_clawli_mode = False
            elif websocket_server:
                websocket_server.stop_all()
            print(f"{Fore.GREEN}远程服务已停止{Style.RESET_ALL}")

        elif cmd == 'status':
            if CLAWLI_SERVER_AVAILABLE and clawli_server:
                status = clawli_server.get_status()
            elif websocket_server:
                status = websocket_server.get_status()
            else:
                status = {}

            if status.get('running'):
                mode = status.get('mode', 'local')
                if mode == 'proxy':
                    print(f"{Fore.GREEN}远程服务状态: 运行中 (代理模式){Style.RESET_ALL}")
                    print(f"{Fore.WHITE}服务器: {Fore.YELLOW}{status.get('server', '未知')}{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}PC端口: {Fore.YELLOW}{status.get('port', '未知')}{Style.RESET_ALL}")
                else:
                    print(f"{Fore.GREEN}远程服务状态: 运行中 (本地模式){Style.RESET_ALL}")
                    print(f"{Fore.WHITE}本机IP: {Fore.YELLOW}{status.get('local_ip', '未知')}{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}端口: {Fore.YELLOW}{status.get('port', 9079)}{Style.RESET_ALL}")
                    print(f"{Fore.WHITE}已连接客户端: {Fore.YELLOW}{status.get('connected_clients', 0)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}远程服务状态: 未启动{Style.RESET_ALL}")
                print(f"{Fore.WHITE}使用 {Fore.CYAN}/remote start <端口> <密码>{Fore.WHITE} 启动本地服务{Style.RESET_ALL}")
                print(f"{Fore.WHITE}使用 {Fore.CYAN}/remote proxy ...{Fore.WHITE} 连接代理服务器{Style.RESET_ALL}")

        elif cmd == 'ip':
            import socket
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
                print(f"{Fore.GREEN}本机IP地址: {Fore.YELLOW}{local_ip}{Style.RESET_ALL}")
                print(f"{Fore.WHITE}在 Clawli 应用中输入此IP即可连接 (仅限局域网){Style.RESET_ALL}")
            except Exception as e:
                print(f"{Fore.RED}获取IP失败: {e}{Style.RESET_ALL}")

        else:
            print(f"{Fore.RED}未知命令: {cmd}{Style.RESET_ALL}")
            print(f"{Fore.WHITE}可用命令: start, proxy, stop, status, ip{Style.RESET_ALL}")
