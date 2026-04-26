import os
import threading
from colorama import Fore, Style


class Liugin:
    """音频播放插件"""
    
    def __init__(self):
        self.usage = """音频播放工具使用方法：
audio_player play - 播放音频文件
例如:
- audio_player play - 播放Ciallo～(∠・ω- )⌒-.mp3音频文件

使用工具的JSON格式示例:
{"action": "use_tool", "tool": "audio_player", "args": "play"} - 播放音频文件

直接命令:
- /ciallo - 播放音频文件
"""
        self.cli = None  # CLI实例引用
        self.audio_file = None  # 音频文件路径将在set_cli中设置
    
    def set_cli(self, cli):
        """设置CLI实例引用"""
        self.cli = cli
        # 获取主程序目录路径，通过CLI实例
        import os
        # 使用CLI实例中的项目目录信息
        self.audio_file = os.path.join(os.path.dirname(cli.chat_history_dir), "Ciallo～(∠・ω- )⌒-.mp3")
        # 注册插件命令
        self.cli.register_liugin_command('ciallo', self.play_command_handler)
    
    def get_tool_info(self):
            return {
                "name": "audio_player",
                "description": "音频播放工具，播放指定的音频文件",
                "keywords": ["音频", "播放", "audio", "play", "音乐", "声音"],
                "usage": """audio_player 工具使用说明：
    JSON格式示例：
    {"action": "use_tool", "tool": "audio_player", "args": "play"} - 播放音频文件
    直接命令：/ciallo - 播放音频文件"""
            }    

    def get_mcp_definition(self):
        return {
            "name": "audio_player",
            "description": "音频播放工具",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "file": {
                        "type": "string",
                        "description": "音频文件路径（可选）"
                    }
                }
            }
        }

    def convert_mcp_args(self, arguments):
        return arguments.get("file", "")

    def handle(self, args):
        """处理音频播放请求"""
        try:
            # 解析参数
            parts = args.strip().split()
            if len(parts) < 1:
                return "错误：请提供操作类型。支持的操作：play"
            
            operation = parts[0].lower()
            
            if operation == "play":
                return self._play_audio()
            else:
                return f"错误：不支持的操作 '{operation}'。支持的操作：play"
        
        except Exception as e:
            return f"音频播放错误: {str(e)}"
    
    def play_command_handler(self, args):
        """处理 /ciallo 命令"""
        # 在新线程中播放音频，避免阻塞主程序
        thread = threading.Thread(target=self._play_audio_internal)
        thread.daemon = True
        thread.start()
        return f"正在播放音频文件: {self.audio_file}"
    
    def _play_audio(self):
        """播放音频文件"""
        try:
            # 检查音频文件是否存在
            if not os.path.exists(self.audio_file):
                return f"错误：音频文件 '{self.audio_file}' 不存在。"
            
            # 使用多种方式尝试播放音频
            success = self._try_play_audio()
            
            if success:
                return f"音频文件 '{self.audio_file}' 播放成功！"
            else:
                return f"音频播放失败。请确保已安装相应的音频播放库。"
        
        except Exception as e:
            return f"播放音频时发生错误: {str(e)}"
    
    def _play_audio_internal(self):
        """在新线程中播放音频"""
        try:
            # 检查音频文件是否存在
            if not os.path.exists(self.audio_file):
                print(f"{Fore.RED}错误：音频文件 '{self.audio_file}' 不存在。{Style.RESET_ALL}")
                return
            
            # 使用多种方式尝试播放音频
            self._try_play_audio()
        
        except Exception as e:
            print(f"{Fore.RED}播放音频时发生错误: {str(e)}{Style.RESET_ALL}")
    
    def _try_play_audio(self):
        """尝试多种方式播放音频"""
        # 首先尝试使用pygame（如果已安装）
        try:
            import pygame
            pygame.mixer.init()
            pygame.mixer.music.load(self.audio_file)
            pygame.mixer.music.play()
            
            # 等待音频播放完成
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            pygame.mixer.quit()
            return True
        except ImportError:
            pass  # pygame未安装，尝试其他方式
        except Exception:
            pass  # 其他pygame相关错误，尝试其他方式
        
        # 尝试使用playsound库（如果已安装）
        try:
            from playsound import playsound
            playsound(self.audio_file)
            return True
        except ImportError:
            pass  # playsound未安装，尝试其他方式
        except Exception:
            pass  # 其他playsound相关错误，尝试其他方式
        
        # 尝试使用winsound（仅Windows）
        try:
            import winsound
            # 对于MP3文件，先尝试使用高级API
            import subprocess
            subprocess.run(["start", "", self.audio_file], shell=True)
            return True
        except Exception:
            pass  # winsound相关错误，尝试其他方式
        
        # 尝试使用os.startfile（仅Windows）
        try:
            os.startfile(self.audio_file)  # 这会使用默认程序打开文件
            return True
        except Exception:
            pass  # os.startfile相关错误
        
        # 如果所有方式都失败，返回False
        return False