
"""
文件管理器插件 - 小狸自有协议版本
支持文件和目录的创建、读取、写入、删除、移动、复制、搜索等操作
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


class Liugin:
    """文件管理器插件"""
    
    def __init__(self):
        self.usage = """文件管理器使用方法：
file_manager <操作> <参数>

操作类型:
- list <路径> [-p "模式"]       - 列出目录内容（只列当前目录）
- read <文件路径> [-n 行数]     - 读取文件内容
- write <文件路径> -c "内容"    - 写入文件
- append <文件路径> -c "内容"   - 追加内容到文件
- copy <源路径> <目标路径>      - 复制文件或目录
- move <源路径> <目标路径>      - 移动或重命名
- delete <路径> [-r]            - 删除文件或目录
- search <目录> [-p "模式"] [-c "内容"] - 搜索文件（递归）
- info <路径>                   - 获取文件信息
- mkdir <路径>                  - 创建目录
- modify <文件路径> <行号> "新内容" - 修改指定行
- insert <文件路径> <行号> "内容"    - 在指定行插入内容
- delete-line <文件路径> <行号>     - 删除指定行
- replace <文件路径> "旧文本" "新文本" [--start 行号] [--end 行号] - 替换文本

示例:
- file_manager list .            - 列出当前目录
- file_manager list . -p "*.py"  - 列出所有Python文件
- file_manager read config.json  - 读取文件
- file_manager write test.txt -c "Hello World"  - 写入文件
- file_manager copy file1.txt file2.txt  - 复制文件
- file_manager move old.txt new.txt       - 重命名文件
- file_manager delete temp -r             - 递归删除目录
- file_manager search . -c "TODO"         - 搜索包含TODO的文件

JSON调用格式:
{"action": "use_tool", "tool": "file_manager", "args": "list ."}
{"action": "use_tool", "tool": "file_manager", "args": "read config.json -n 50"}
{"action": "use_tool", "tool": "file_manager", "args": "write test.txt -c Hello World"}
"""
        self.cli = None
    
    def set_cli(self, cli):
        """设置CLI实例引用"""
        self.cli = cli
    
    def get_tool_info(self):
        return {
            "name": "file_manager",
            "description": "文件和目录管理工具，支持创建、读取、写入、删除、移动、复制、搜索文件等操作",
            "keywords": ["文件", "目录", "管理", "file", "manager", "读写", "复制", "删除", "搜索", "mkdir"],
            "usage": self.usage
        }
    
    def get_mcp_definition(self) -> Dict[str, Any]:
        """返回符合 MCP 标准的工具定义"""
        return {
            "name": "file_manager",
            "description": "文件和目录管理工具，支持创建、读取、写入、删除、移动、复制、搜索文件等操作。操作类型: list(列出目录), read(读取文件), write(写入文件), append(追加内容), copy(复制), move(移动/重命名), delete(删除), search(搜索), info(文件信息), mkdir(创建目录), modify(修改行), insert(插入行), delete-line(删除行), replace(替换文本)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["list", "read", "write", "append", "copy", "move", "delete", "search", "info", "mkdir", "modify", "insert", "delete-line", "replace"],
                        "description": "操作类型"
                    },
                    "path": {
                        "type": "string",
                        "description": "文件或目录路径"
                    },
                    "content": {
                        "type": "string",
                        "description": "文件内容（用于 write/append 操作）"
                    },
                    "destination": {
                        "type": "string",
                        "description": "目标路径（用于 copy/move 操作）"
                    },
                    "pattern": {
                        "type": "string",
                        "description": "文件匹配模式（用于 list/search 操作）"
                    },
                    "line_number": {
                        "type": "integer",
                        "description": "行号（用于 modify/insert/delete-line 操作）"
                    },
                    "old_text": {
                        "type": "string",
                        "description": "旧文本（用于 replace 操作）"
                    },
                    "new_text": {
                        "type": "string",
                        "description": "新文本（用于 replace/modify 操作）"
                    },
                    "recursive": {
                        "type": "boolean",
                        "description": "是否递归（用于 delete/search 操作）",
                        "default": False
                    }
                },
                "required": ["operation"]
            }
        }
    
    def convert_mcp_args(self, arguments: Dict[str, Any]) -> str:
        """将 MCP 参数转换为命令行格式"""
        op = arguments.get("operation", "")
        parts = [op]
        
        if "path" in arguments:
            parts.append(arguments["path"])
        
        if "destination" in arguments:
            parts.append(arguments["destination"])
        
        if "content" in arguments:
            parts.extend(["-c", f'"{arguments["content"]}"'])
        
        if "pattern" in arguments:
            parts.extend(["-p", f'"{arguments["pattern"]}"'])
        
        if "line_number" in arguments:
            parts.append(str(arguments["line_number"]))
        
        if "old_text" in arguments:
            parts.append(f'"{arguments["old_text"]}"')
        
        if "new_text" in arguments:
            parts.append(f'"{arguments["new_text"]}"')
        
        if arguments.get("recursive"):
            parts.append("-r")
        
        return " ".join(parts)
    
    def handle(self, args: str) -> str:
        """处理文件管理请求"""
        try:
            # 解析参数
            parts = self._parse_args(args)
            if not parts:
                return "错误：请提供操作类型。\n可用操作: list, read, write, append, copy, move, delete, search, info, mkdir, modify, insert, delete-line, replace"
            
            operation = parts[0].lower()
            
            handlers = {
                "list": self._op_list,
                "read": self._op_read,
                "write": self._op_write,
                "append": self._op_append,
                "copy": self._op_copy,
                "move": self._op_move,
                "delete": self._op_delete,
                "search": self._op_search,
                "info": self._op_info,
                "mkdir": self._op_mkdir,
                "modify": self._op_modify_line,
                "insert": self._op_insert_line,
                "delete-line": self._op_delete_line,
                "replace": self._op_replace_text,
            }
            
            handler = handlers.get(operation)
            if not handler:
                return f"错误：不支持的操作 '{operation}'。\n支持的操作: {', '.join(handlers.keys())}"
            
            return handler(parts[1:])
            
        except Exception as e:
            return f"文件操作错误: {str(e)}"
    
    def _parse_args(self, args: str) -> List[str]:
        """解析命令行参数，支持引号"""
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
    
    def _op_list(self, args: List[str]) -> str:
        """列出目录内容 - 默认只列出当前目录，不递归"""
        path = "."
        pattern = None
        
        i = 0
        while i < len(args):
            if args[i] == "-p" and i + 1 < len(args):
                pattern = args[i + 1]
                i += 1
            elif not args[i].startswith("-"):
                path = args[i]
            i += 1
        
        path = os.path.abspath(path)
        
        if not os.path.exists(path):
            return f"错误：路径不存在: {path}"
        
        if not os.path.isdir(path):
            return f"错误：不是目录: {path}"
        
        items = []
        
        try:
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                if pattern and not Path(item).match(pattern):
                    continue
                if os.path.isdir(full_path):
                    items.append(('dir', item, ''))
                else:
                    size = os.path.getsize(full_path)
                    if size < 1024:
                        size_str = f"{size}B"
                    elif size < 1024 * 1024:
                        size_str = f"{size/1024:.1f}KB"
                    else:
                        size_str = f"{size/1024/1024:.1f}MB"
                    items.append(('file', item, size_str))
            
            # 排序：文件夹优先
            items.sort(key=lambda x: (0 if x[0] == 'dir' else 1, x[1].lower()))
            
            result = [f"📁 {path}"]
            result.append("─" * 50)
            
            dir_count = sum(1 for x in items if x[0] == 'dir')
            file_count = len(items) - dir_count
            
            for item_type, name, size in items[:100]:
                if item_type == 'dir':
                    result.append(f"  📁 {name}/")
                else:
                    result.append(f"  📄 {name}  ({size})")
            
            if len(items) > 100:
                result.append(f"  ... 还有 {len(items) - 100} 项")
            
            result.append("─" * 50)
            result.append(f"共 {dir_count} 个文件夹, {file_count} 个文件")
            
            return '\n'.join(result)
            
        except Exception as e:
            return f"列出目录失败: {e}"
    
    def _op_read(self, args: List[str]) -> str:
        """读取文件内容"""
        if not args:
            return "错误：请提供文件路径"
        
        file_path = args[0]
        lines = None
        
        i = 1
        while i < len(args):
            if args[i] == "-n" and i + 1 < len(args):
                try:
                    lines = int(args[i + 1])
                except ValueError:
                    return "错误：行数必须是整数"
                i += 1
            i += 1
        
        file_path = os.path.abspath(file_path)
        
        if not os.path.exists(file_path):
            return f"错误：文件不存在: {file_path}"
        
        if not os.path.isfile(file_path):
            return f"错误：不是文件: {file_path}"
        
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            return f"警告：文件过大 ({file_size / 1024 / 1024:.1f}MB)，请使用 -n 参数限制行数"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if lines:
                    content_lines = []
                    line_count = 0
                    for i, line in enumerate(f):
                        line_count = i + 1
                        if i < lines:
                            content_lines.append(f"{i+1:4d} | {line.rstrip()}")
                    content = '\n'.join(content_lines)
                    total_lines = line_count
                else:
                    all_lines = f.readlines()
                    content = '\n'.join(f"{i+1:4d} | {line.rstrip()}" for i, line in enumerate(all_lines))
                    total_lines = len(all_lines)
            
            result = [f"文件: {file_path}"]
            result.append(f"大小: {file_size} 字节")
            result.append(f"行数: {total_lines}")
            if lines:
                result.append(f"显示: 前 {min(lines, total_lines)} 行")
            result.append(f"\n{'─' * 50}")
            result.append(content)
            
            return '\n'.join(result)
            
        except UnicodeDecodeError:
            return f"错误：无法解码文件（可能是二进制文件或编码不正确）"
        except Exception as e:
            return f"读取文件失败: {e}"
    
    def _op_write(self, args: List[str]) -> str:
        """写入文件"""
        if len(args) < 2:
            return "错误：请提供文件路径和内容"
        
        file_path = args[0]
        content = None
        
        i = 1
        while i < len(args):
            if args[i] == "-c" and i + 1 < len(args):
                content = args[i + 1]
                i += 1
            i += 1
        
        if content is None:
            return "错误：请使用 -c 参数提供内容"
        
        file_path = os.path.abspath(file_path)
        
        try:
            # 创建父目录
            parent = os.path.dirname(file_path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return f"✅ 文件已写入: {file_path}\n大小: {len(content.encode('utf-8'))} 字节"
            
        except Exception as e:
            return f"写入文件失败: {e}"
    
    def _op_append(self, args: List[str]) -> str:
        """追加内容到文件"""
        if len(args) < 2:
            return "错误：请提供文件路径和内容"
        
        file_path = args[0]
        content = None
        
        i = 1
        while i < len(args):
            if args[i] == "-c" and i + 1 < len(args):
                content = args[i + 1]
                i += 1
            i += 1
        
        if content is None:
            return "错误：请使用 -c 参数提供内容"
        
        file_path = os.path.abspath(file_path)
        
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(content)
            
            return f"✅ 内容已追加: {file_path}"
            
        except Exception as e:
            return f"追加内容失败: {e}"
    
    def _op_copy(self, args: List[str]) -> str:
        """复制文件或目录"""
        if len(args) < 2:
            return "错误：请提供源路径和目标路径"
        
        source = os.path.abspath(args[0])
        destination = os.path.abspath(args[1])
        
        if not os.path.exists(source):
            return f"错误：源路径不存在: {source}"
        
        try:
            parent = os.path.dirname(destination)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            
            if os.path.isfile(source):
                shutil.copy2(source, destination)
                item_type = "文件"
            else:
                shutil.copytree(source, destination, dirs_exist_ok=True)
                item_type = "目录"
            
            return f"✅ {item_type}已复制:\n  源: {source}\n  目标: {destination}"
            
        except Exception as e:
            return f"复制失败: {e}"
    
    def _op_move(self, args: List[str]) -> str:
        """移动或重命名文件或目录"""
        if len(args) < 2:
            return "错误：请提供源路径和目标路径"
        
        source = os.path.abspath(args[0])
        destination = os.path.abspath(args[1])
        
        if not os.path.exists(source):
            return f"错误：源路径不存在: {source}"
        
        try:
            parent = os.path.dirname(destination)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            
            shutil.move(source, destination)
            
            return f"✅ 已移动/重命名:\n  源: {source}\n  目标: {destination}"
            
        except Exception as e:
            return f"移动失败: {e}"
    
    def _op_delete(self, args: List[str]) -> str:
        """删除文件或目录"""
        if not args:
            return "错误：请提供路径"
        
        path = os.path.abspath(args[0])
        recursive = "-r" in args
        
        if not os.path.exists(path):
            return f"错误：路径不存在: {path}"
        
        try:
            if os.path.isfile(path):
                os.remove(path)
                item_type = "文件"
            elif os.path.isdir(path):
                if recursive:
                    shutil.rmtree(path)
                    item_type = "目录"
                else:
                    # 检查是否为空
                    if os.listdir(path):
                        return f"错误：目录不为空。使用 -r 参数递归删除。"
                    os.rmdir(path)
                    item_type = "空目录"
            
            return f"✅ 已删除 {item_type}: {path}"
            
        except Exception as e:
            return f"删除失败: {e}"
    
    def _op_search(self, args: List[str]) -> str:
        """搜索文件"""
        if not args:
            return "错误：请提供搜索目录"
        
        directory = args[0]
        pattern = None
        content_search = None
        
        i = 1
        while i < len(args):
            if args[i] == "-p" and i + 1 < len(args):
                pattern = args[i + 1]
                i += 1
            elif args[i] == "-c" and i + 1 < len(args):
                content_search = args[i + 1]
                i += 1
            i += 1
        
        directory = os.path.abspath(directory)
        
        if not os.path.exists(directory):
            return f"错误：目录不存在: {directory}"
        
        results = []
        
        try:
            for root, dirs, files in os.walk(directory):
                for filename in files:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, directory)
                    
                    # 模式匹配
                    if pattern and not Path(filename).match(pattern):
                        continue
                    
                    # 内容搜索
                    if content_search:
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                file_content = f.read()
                                if content_search not in file_content:
                                    continue
                                # 找到匹配行
                                for i, line in enumerate(file_content.split('\n'), 1):
                                    if content_search in line:
                                        results.append(f"{rel_path}:{i}: {line.strip()[:80]}")
                                        if len(results) >= 50:
                                            break
                        except (UnicodeDecodeError, IOError):
                            continue
                    else:
                        results.append(rel_path)
                    
                    if len(results) >= 100:
                        break
                
                if len(results) >= 100:
                    break
            
            if not results:
                return "未找到匹配的文件"
            
            result_text = [f"搜索结果 (共 {len(results)} 个):"]
            result_text.append(f"目录: {directory}")
            if pattern:
                result_text.append(f"模式: {pattern}")
            if content_search:
                result_text.append(f"内容: {content_search}")
            result_text.append("")
            result_text.extend(results[:100])
            
            if len(results) > 100:
                result_text.append(f"... 还有 {len(results) - 100} 个结果")
            
            return '\n'.join(result_text)
            
        except Exception as e:
            return f"搜索失败: {e}"
    
    def _op_info(self, args: List[str]) -> str:
        """获取文件信息"""
        if not args:
            return "错误：请提供路径"
        
        path = os.path.abspath(args[0])
        
        if not os.path.exists(path):
            return f"错误：路径不存在: {path}"
        
        try:
            stat_info = os.stat(path)
            
            result = [f"路径: {path}"]
            result.append(f"名称: {os.path.basename(path)}")
            result.append(f"类型: {'目录' if os.path.isdir(path) else '文件'}")
            result.append(f"大小: {stat_info.st_size:,} 字节 ({stat_info.st_size / 1024:.1f} KB)")
            result.append(f"创建时间: {datetime.fromtimestamp(stat_info.st_ctime).strftime('%Y-%m-%d %H:%M:%S')}")
            result.append(f"修改时间: {datetime.fromtimestamp(stat_info.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            result.append(f"访问时间: {datetime.fromtimestamp(stat_info.st_atime).strftime('%Y-%m-%d %H:%M:%S')}")
            
            if os.path.isfile(path):
                ext = os.path.splitext(path)[1]
                result.append(f"扩展名: {ext if ext else '无'}")
                
                # 尝试检测编码
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        f.read(1024)
                    result.append("编码: UTF-8 (文本文件)")
                except UnicodeDecodeError:
                    result.append("编码: 二进制文件")
            
            return '\n'.join(result)
            
        except Exception as e:
            return f"获取信息失败: {e}"
    
    def _op_mkdir(self, args: List[str]) -> str:
        """创建目录"""
        if not args:
            return "错误：请提供目录路径"
        
        path = os.path.abspath(args[0])
        
        if os.path.exists(path):
            return f"错误：路径已存在: {path}"
        
        try:
            os.makedirs(path, exist_ok=True)
            return f"✅ 目录已创建: {path}"
        except Exception as e:
            return f"创建目录失败: {e}"
    
    def _op_modify_line(self, args: List[str]) -> str:
        """修改指定行"""
        if len(args) < 3:
            return "错误：请提供文件路径、行号和新内容"
        
        file_path = os.path.abspath(args[0])
        try:
            line_number = int(args[1])
        except ValueError:
            return "错误：行号必须是整数"
        
        new_content = args[2]
        
        if not os.path.exists(file_path):
            return f"错误：文件不存在: {file_path}"
        
        if line_number < 1:
            return "错误：行号必须 >= 1"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if line_number > len(lines):
                return f"错误：文件只有 {len(lines)} 行，无法修改第 {line_number} 行"
            
            old_content = lines[line_number - 1].rstrip('\n\r')
            lines[line_number - 1] = new_content + '\n'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return f"✅ 第 {line_number} 行已修改:\n  旧: {old_content}\n  新: {new_content}"
            
        except Exception as e:
            return f"修改行失败: {e}"
    
    def _op_insert_line(self, args: List[str]) -> str:
        """插入行"""
        if len(args) < 3:
            return "错误：请提供文件路径、行号和内容"
        
        file_path = os.path.abspath(args[0])
        try:
            line_number = int(args[1])
        except ValueError:
            return "错误：行号必须是整数"
        
        content = args[2]
        
        if not os.path.exists(file_path):
            return f"错误：文件不存在: {file_path}"
        
        if line_number < 1:
            return "错误：行号必须 >= 1"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            insert_pos = min(line_number - 1, len(lines))
            lines.insert(insert_pos, content + '\n')
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return f"✅ 已在第 {line_number} 行插入内容: {content}"
            
        except Exception as e:
            return f"插入行失败: {e}"
    
    def _op_delete_line(self, args: List[str]) -> str:
        """删除指定行"""
        if len(args) < 2:
            return "错误：请提供文件路径和行号"
        
        file_path = os.path.abspath(args[0])
        try:
            line_number = int(args[1])
        except ValueError:
            return "错误：行号必须是整数"
        
        if not os.path.exists(file_path):
            return f"错误：文件不存在: {file_path}"
        
        if line_number < 1:
            return "错误：行号必须 >= 1"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            if line_number > len(lines):
                return f"错误：文件只有 {len(lines)} 行，无法删除第 {line_number} 行"
            
            deleted = lines[line_number - 1].rstrip('\n\r')
            del lines[line_number - 1]
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            return f"✅ 已删除第 {line_number} 行: {deleted}"
            
        except Exception as e:
            return f"删除行失败: {e}"
    
    def _op_replace_text(self, args: List[str]) -> str:
        """替换文本"""
        if len(args) < 3:
            return "错误：请提供文件路径、旧文本和新文本"
        
        file_path = os.path.abspath(args[0])
        old_text = args[1]
        new_text = args[2]
        
        start_line = None
        end_line = None
        
        i = 3
        while i < len(args):
            if args[i] == "--start" and i + 1 < len(args):
                start_line = int(args[i + 1])
                i += 1
            elif args[i] == "--end" and i + 1 < len(args):
                end_line = int(args[i + 1])
                i += 1
            i += 1
        
        if not os.path.exists(file_path):
            return f"错误：文件不存在: {file_path}"
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            total_lines = len(lines)
            replacements = []
            
            start = max(0, (start_line or 1) - 1)
            end = min(total_lines, end_line or total_lines)
            
            for i in range(start, end):
                if old_text in lines[i]:
                    count = lines[i].count(old_text)
                    lines[i] = lines[i].replace(old_text, new_text)
                    replacements.append(f"第 {i+1} 行: 替换了 {count} 处")
            
            if not replacements:
                return f"未找到匹配文本: {old_text}"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(lines)
            
            result = [f"✅ 文本替换完成"]
            result.append(f"文件: {file_path}")
            result.append(f"'{old_text}' -> '{new_text}'")
            if start_line or end_line:
                result.append(f"范围: 第 {start+1} 行到第 {end} 行")
            result.append(f"修改了 {len(replacements)} 行:")
            result.extend(replacements[:20])
            if len(replacements) > 20:
                result.append(f"... 还有 {len(replacements) - 20} 行")
            
            return '\n'.join(result)
            
        except Exception as e:
            return f"文本替换失败: {e}"


# 测试
if __name__ == "__main__":
    plugin = Plugin()
    print("文件管理器插件测试:")
    print(plugin.get_tool_info())
    print("\n测试 list 操作:")
    print(plugin.handle("list . -p *.py"))
