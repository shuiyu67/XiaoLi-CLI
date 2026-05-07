"""
语音识别插件 - 弹窗录音界面
AI 触发后弹出独立录音窗口
"""

import os
import json
import subprocess
import sys
import time
from typing import Optional, Dict, Any, List

# 结果保存路径
RESULT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "speech_temp", "last_result.txt")
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "speech_temp")


class Liugin:
    """语音识别插件"""
    
    def __init__(self):
        self.plugin_dir = os.path.dirname(os.path.abspath(__file__))
        self.temp_dir = TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.usage = """语音识别插件使用方法：
speech_recognition <操作> [参数]

录音识别:
- record                     - 弹出录音窗口，录音并识别

文件识别:
- file <音频文件路径>        - 识别音频文件内容

其他:
- status                     - 查看状态
- result                     - 获取上次识别结果

支持的音频格式: wav, mp3, m4a, flac, ogg
"""
        self.cli = None
        
    def set_cli(self, cli):
        self.cli = cli
    
    def get_tool_info(self):
        return {
            "name": "speech_recognition",
            "description": "语音识别插件，弹出录音窗口进行语音识别，将语音转换为文字",
            "keywords": ["语音", "识别", "录音", "转文字", "speech", "voice", "recognition"],
            "usage": self.usage
        }
    
    def get_mcp_definition(self):
        return {
            "name": "speech_recognition",
            "description": "语音识别插件，弹出录音窗口进行语音识别",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["record", "file", "status", "result"],
                        "description": "操作类型"
                    },
                    "file_path": {"type": "string", "description": "音频文件路径"}
                },
                "required": ["operation"]
            }
        }
    
    def convert_mcp_args(self, arguments: Dict[str, Any]) -> str:
        op = arguments.get("operation", "")
        parts = [op]
        if op == "file":
            parts.append(arguments.get("file_path", ""))
        return " ".join(filter(None, parts))
    
    def handle(self, args: str) -> str:
        try:
            parts = self._parse_args(args)
            if not parts:
                return "错误：请提供操作类型。\n" + self.usage
            
            operation = parts[0].lower()
            
            handlers = {
                "record": self._op_record,
                "file": self._op_file,
                "status": self._op_status,
                "result": self._op_result,
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
    
    # ==================== 弹窗录音 ====================
    
    def _op_record(self, args: List[str]) -> str:
        """弹出录音窗口"""
        
        # 创建录音窗口脚本
        recorder_script = os.path.join(self.temp_dir, "recorder_gui.py")
        
        gui_code = f'''import tkinter as tk
from tkinter import messagebox
import os
import sys
import threading
import time

RESULT_FILE = r"{RESULT_FILE}"
TEMP_DIR = r"{TEMP_DIR}"

class VoiceRecorder:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("语音识别录音")
        self.root.geometry("450x350")
        self.root.resizable(False, False)
        
        # 居中显示
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() - 450) // 2
        y = (self.root.winfo_screenheight() - 350) // 2
        self.root.geometry(f"450x350+{{x}}+{{y}}")
        
        # 录音状态
        self.is_recording = False
        self.record_file = None
        self.frames = []
        self.start_time = None
        self.p = None
        self.stream = None
        
        # 创建界面
        self._create_ui()
        
        # 检查 pyaudio
        self.has_pyaudio = self._check_pyaudio()
        if not self.has_pyaudio:
            self.status_label.config(text="请安装 pyaudio: pip install pyaudio", fg="red")
    
    def _check_pyaudio(self):
        try:
            import pyaudio
            return True
        except:
            return False
    
    def _create_ui(self):
        # 标题
        title_label = tk.Label(self.root, text=" 语音识别录音", font=("Arial", 18, "bold"))
        title_label.pack(pady=15)
        
        # 状态标签
        self.status_label = tk.Label(self.root, text="点击开始录音", font=("Arial", 11))
        self.status_label.pack(pady=5)
        
        # 时间标签
        self.time_label = tk.Label(self.root, text="00:00", font=("Arial", 28, "bold"), fg="#2196F3")
        self.time_label.pack(pady=10)
        
        # 按钮框架
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=15)
        
        # 开始/停止按钮
        self.record_btn = tk.Button(
            btn_frame, text=" 开始录音", font=("Arial", 12),
            width=12, height=2, command=self.toggle_record,
            bg="#4CAF50", fg="white", cursor="hand2"
        )
        self.record_btn.pack(side=tk.LEFT, padx=10)
        
        # 识别按钮
        self.recognize_btn = tk.Button(
            btn_frame, text=" 识别", font=("Arial", 12),
            width=12, height=2, command=self.recognize,
            bg="#2196F3", fg="white", cursor="hand2", state=tk.DISABLED
        )
        self.recognize_btn.pack(side=tk.LEFT, padx=10)
        
        # 结果显示
        result_frame = tk.LabelFrame(self.root, text="识别结果", font=("Arial", 10))
        result_frame.pack(pady=10, padx=15, fill=tk.BOTH, expand=True)
        
        self.result_text = tk.Text(result_frame, height=5, width=50, font=("Arial", 10))
        self.result_text.pack(pady=5, padx=5, fill=tk.BOTH, expand=True)
    
    def toggle_record(self):
        if not self.has_pyaudio:
            messagebox.showerror("错误", "请先安装 pyaudio:\npip install pyaudio")
            return
            
        if self.is_recording:
            self.stop_record()
        else:
            self.start_record()
    
    def start_record(self):
        import pyaudio
        
        self.is_recording = True
        self.frames = []
        self.start_time = time.time()
        self.record_btn.config(text=" 停止录音", bg="#f44336")
        self.status_label.config(text=" 正在录音...", fg="red")
        self.recognize_btn.config(state=tk.DISABLED)
        
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(
            format=FORMAT, channels=CHANNELS, rate=RATE,
            input=True, frames_per_buffer=CHUNK
        )
        
        # 更新时间
        self._update_time()
        
        # 录音线程
        def record_loop():
            while self.is_recording:
                try:
                    data = self.stream.read(CHUNK, exception_on_overflow=False)
                    self.frames.append(data)
                except:
                    break
        
        self.record_thread = threading.Thread(target=record_loop, daemon=True)
        self.record_thread.start()
    
    def stop_record(self):
        self.is_recording = False
        self.record_btn.config(text=" 开始录音", bg="#4CAF50")
        self.status_label.config(text="录音完成，可以识别", fg="green")
        self.recognize_btn.config(state=tk.NORMAL)
        
        # 停止录音
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.p:
            self.p.terminate()
        
        # 保存文件
        import wave
        import pyaudio
        self.record_file = os.path.join(TEMP_DIR, f"record_{{int(time.time())}}.wav")
        wf = wave.open(self.record_file, "wb")
        wf.setnchannels(1)
        wf.setsampwidth(pyaudio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(16000)
        wf.writeframes(b"".join(self.frames))
        wf.close()
        
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, " 录音已保存\n点击 [识别] 按钮进行语音识别")
    
    def _update_time(self):
        if self.is_recording:
            elapsed = int(time.time() - self.start_time)
            mins = elapsed // 60
            secs = elapsed % 60
            self.time_label.config(text=f"{{mins:02d}}:{{secs:02d}}")
            self.root.after(100, self._update_time)
    
    def recognize(self):
        if not self.record_file or not os.path.exists(self.record_file):
            messagebox.showerror("错误", "没有录音文件，请先录音")
            return
        
        self.status_label.config(text="正在识别...", fg="blue")
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, " 识别中，请稍候...")
        self.root.update()
        
        # 尝试识别
        result = self._do_recognize()
        
        self.result_text.delete(1.0, tk.END)
        if result:
            self.result_text.insert(tk.END, result)
            self.status_label.config(text="识别完成", fg="green")
            # 保存结果
            with open(RESULT_FILE, "w", encoding="utf-8") as f:
                f.write(result)
        else:
            self.result_text.insert(tk.END, " 识别失败\n\n请安装识别引擎:\n• pip install openai-whisper\n• pip install SpeechRecognition")
            self.status_label.config(text="识别失败", fg="red")
    
    def _do_recognize(self):
        # 尝试 Whisper
        try:
            import whisper
            self.status_label.config(text="使用 Whisper 识别...", fg="blue")
            self.root.update()
            model = whisper.load_model("base")
            result = model.transcribe(self.record_file, language="zh")
            text = result.get("text", "").strip()
            if text:
                return f" {{text}}"
        except Exception as e:
            print(f"Whisper error: {{e}}")
        
        # 尝试 SpeechRecognition
        try:
            import speech_recognition as sr
            self.status_label.config(text="使用 Google 识别...", fg="blue")
            self.root.update()
            r = sr.Recognizer()
            with sr.AudioFile(self.record_file) as source:
                audio = r.record(source)
            text = r.recognize_google(audio, language="zh-CN")
            if text:
                return f" {{text}}"
        except Exception as e:
            print(f"SpeechRecognition error: {{e}}")
        
        return None

    def run(self):
        self.root.mainloop()
        
        # 清理
        if self.is_recording:
            self.is_recording = False
            if self.stream:
                self.stream.close()
            if self.p:
                self.p.terminate()

if __name__ == "__main__":
    app = VoiceRecorder()
    app.run()
'''
        
        # 写入脚本
        with open(recorder_script, "w", encoding="utf-8") as f:
            f.write(gui_code)
        
        # 启动录音窗口
        try:
            subprocess.Popen([sys.executable, recorder_script], 
                           creationflags=subprocess.CREATE_NEW_CONSOLE)
            return " 已弹出录音窗口，请在窗口中进行录音和识别\n\n使用方法：\n1. 点击「开始录音」\n2. 对着麦克风说话\n3. 点击「停止录音」\n4. 点击「识别」获取文字结果"
        except Exception as e:
            return f" 启动录音窗口失败: {e}"
    
    # ==================== 文件识别 ====================
    
    def _op_file(self, args: List[str]) -> str:
        """识别音频文件"""
        if not args:
            return "错误：请提供音频文件路径"
        
        file_path = args[0]
        
        if not os.path.exists(file_path):
            return f" 文件不存在: {file_path}"
        
        return self._recognize_file(file_path)
    
    def _recognize_file(self, file_path: str) -> str:
        """识别音频文件内容"""
        
        # 尝试使用 whisper（本地）
        result = self._try_whisper(file_path)
        if result:
            self._save_result(result)
            return result
        
        # 尝试使用 speech_recognition 库
        result = self._try_speech_recognition(file_path)
        if result:
            self._save_result(result)
            return result
        
        return " 语音识别失败：未安装识别引擎\n\n安装方法:\n1. Whisper (推荐): pip install openai-whisper\n2. SpeechRecognition: pip install SpeechRecognition\n3. PyAudio (录音): pip install pyaudio"
    
    def _save_result(self, result: str):
        """保存识别结果"""
        try:
            with open(RESULT_FILE, "w", encoding="utf-8") as f:
                f.write(result)
        except:
            pass
    
    def _try_whisper(self, file_path: str) -> Optional[str]:
        """使用 Whisper 识别"""
        try:
            import whisper
            
            print(f"[语音识别] 使用 Whisper 识别中...")
            model = whisper.load_model("base")
            result = model.transcribe(file_path, language="zh")
            
            text = result.get("text", "").strip()
            if text:
                return f" 识别结果:\n{text}"
            return None
            
        except ImportError:
            return None
        except Exception as e:
            print(f"[语音识别] Whisper 错误: {e}")
            return None
    
    def _try_speech_recognition(self, file_path: str) -> Optional[str]:
        """使用 SpeechRecognition 库识别"""
        wav_file = file_path
        try:
            import speech_recognition as sr
            
            print(f"[语音识别] 使用 SpeechRecognition 识别中...")
            r = sr.Recognizer()
            
            # 转换为 wav 格式
            wav_file = self._convert_to_wav(file_path)
            
            with sr.AudioFile(wav_file) as source:
                audio = r.record(source)
            
            # 尝试 Google 语音识别
            try:
                text = r.recognize_google(audio, language="zh-CN")
                if text:
                    return f" 识别结果:\n{text}"
            except:
                pass
            
            return None
            
        except ImportError:
            return None
        except Exception as e:
            print(f"[语音识别] SpeechRecognition 错误: {e}")
            return None
        finally:
            # 清理转换的临时文件
            if wav_file != file_path and os.path.exists(wav_file):
                try:
                    os.remove(wav_file)
                except:
                    pass
    
    def _convert_to_wav(self, file_path: str) -> str:
        """转换音频为 wav 格式"""
        if file_path.lower().endswith('.wav'):
            return file_path
        
        try:
            wav_file = os.path.join(self.temp_dir, f"convert_{int(time.time())}.wav")
            
            # 使用 ffmpeg 转换
            subprocess.run([
                'ffmpeg', '-y', '-i', file_path,
                '-acodec', 'pcm_s16le',
                '-ar', '16000',
                '-ac', '1',
                wav_file
            ], capture_output=True, check=True)
            
            return wav_file
            
        except Exception as e:
            print(f"[语音识别] 转换错误: {e}")
            return file_path
    
    # ==================== 其他 ====================
    
    def _op_status(self, args: List[str]) -> str:
        """查看状态"""
        lines = [" 语音识别插件状态"]
        
        # 检查可用引擎
        engines = []
        
        try:
            import whisper
            engines.append("whisper ")
        except:
            engines.append("whisper  (pip install openai-whisper)")
        
        try:
            import speech_recognition
            engines.append("speech_recognition ")
        except:
            engines.append("speech_recognition  (pip install SpeechRecognition)")
        
        try:
            import pyaudio
            engines.append("pyaudio  (录音支持)")
        except:
            engines.append("pyaudio  (pip install pyaudio)")
        
        lines.append("\n可用引擎:")
        for e in engines:
            lines.append(f"  - {e}")
        
        return "\n".join(lines)
    
    def _op_result(self, args: List[str]) -> str:
        """获取上次识别结果"""
        if os.path.exists(RESULT_FILE):
            try:
                with open(RESULT_FILE, "r", encoding="utf-8") as f:
                    return f.read()
            except:
                pass
        return "暂无识别结果"


if __name__ == "__main__":
    plugin = Liugin()
    print("语音识别插件")
    print(f"临时目录: {plugin.temp_dir}")
    print("\n" + plugin.usage)
