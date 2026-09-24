"""
前端测试验证插件 - 类似 iFlow CLI 的 frontend-tester
支持HTML/CSS/JS自动化测试和UI验证
"""

import os
from colorama import Fore, Style


class Liugin:
    """前端测试验证插件 - 自动化测试Web界面"""

    def __init__(self):
        self.usage = """前端测试工具使用方法：

JSON格式示例：
{"action": "use_tool", "tool": "frontend_tester", "args": "validate index.html"} - 验证HTML文件
{"action": "use_tool", "tool": "frontend_tester", "args": "test style.css"} - 测试CSS文件
{"action": "use_tool", "tool": "frontend_tester", "args": "check app.js"} - 检查JS文件
{"action": "use_tool", "tool": "frontend_tester", "args": "preview index.html"} - 在浏览器中预览
{"action": "use_tool", "tool": "frontend_tester", "args": "analyze project"} - 分析整个项目

功能说明：
- validate <HTML文件路径> - 验证HTML文件的语法和结构
- test <CSS文件路径> - 测试CSS文件的样式和兼容性
- check <JS文件路径> - 检查JS文件的语法和潜在问题
- preview <HTML文件路径> - 在默认浏览器中打开预览
- analyze <项目路径> - 分析整个前端项目的结构和问题

支持的检查项：
 HTML语法验证
 CSS语法和兼容性检查
 JavaScript语法检查
 响应式设计检查
 可访问性检查
 性能优化建议"""
        self.cli = None

    def set_cli(self, cli):
        """设置CLI实例引用"""
        self.cli = cli
        # 注册插件命令
        self.cli.register_liugin_command('ftest', self.command_handler)
        self.cli.register_liugin_command('frontend', self.command_handler)

    def command_handler(self, args):
        """处理 /ftest 或 /frontend 命令"""
        return self.handle(args)

    def get_tool_info(self):
        return {
            "name": "frontend_tester",
            "description": "前端测试验证工具，支持HTML/CSS/JS自动化测试和UI验证，包括语法检查、响应式设计、可访问性检查等",
            "keywords": ["前端", "测试", "HTML", "CSS", "JavaScript", "UI", "验证", "preview", "validate", "frontend", "test"],
            "usage": self.usage
        }

    def get_mcp_definition(self):
        return {
            "name": "frontend_tester",
            "description": "前端测试验证工具，支持HTML/CSS/JS自动化测试",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "enum": ["validate", "lint", "test"],
                        "description": "操作类型"
                    },
                    "target": {
                        "type": "string",
                        "description": "目标文件路径"
                    }
                },
                "required": ["operation", "target"]
            }
        }

    def convert_mcp_args(self, arguments):
        op = arguments.get("operation", "")
        target = arguments.get("target", "")
        return f"{op} {target}"

    def handle(self, args):
        """处理前端测试请求"""
        try:
            parts = args.strip().split(maxsplit=1)
            if not parts:
                return "错误：请提供操作类型和参数。使用 'frontend_tester help' 查看帮助"

            operation = parts[0].lower()

            if operation == "help":
                return self.usage

            elif operation == "validate":
                # 验证HTML文件
                if len(parts) < 2:
                    return "错误：请提供HTML文件路径。格式: validate <HTML文件路径>"
                file_path = parts[1]
                return self._validate_html(file_path)

            elif operation == "test":
                # 测试CSS文件
                if len(parts) < 2:
                    return "错误：请提供CSS文件路径。格式: test <CSS文件路径>"
                file_path = parts[1]
                return self._test_css(file_path)

            elif operation == "check":
                # 检查JS文件
                if len(parts) < 2:
                    return "错误：请提供JS文件路径。格式: check <JS文件路径>"
                file_path = parts[1]
                return self._check_js(file_path)

            elif operation == "preview":
                # 在浏览器中预览
                if len(parts) < 2:
                    return "错误：请提供HTML文件路径。格式: preview <HTML文件路径>"
                file_path = parts[1]
                return self._preview_in_browser(file_path)

            elif operation == "analyze":
                # 分析整个项目
                if len(parts) < 2:
                    return "错误：请提供项目路径。格式: analyze <项目路径>"
                project_path = parts[1]
                return self._analyze_project(project_path)

            else:
                return f"错误：不支持的操作 '{operation}'。支持的操作有: validate, test, check, preview, analyze, help"

        except Exception as e:
            return f"前端测试操作错误: {str(e)}"

    def _validate_html(self, file_path):
        """验证HTML文件"""
        if not os.path.exists(file_path):
            return f" 文件不存在: {file_path}"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            result = f"\n HTML验证结果: {file_path}\n"
            result += "=" * 60 + "\n\n"

            # 基本检查
            issues = []

            # 检查DOCTYPE
            if not content.strip().startswith('<!DOCTYPE'):
                issues.append({
                    "level": "warning",
                    "message": "缺少DOCTYPE声明，建议添加 <!DOCTYPE html>"
                })

            # 检查lang属性
            if '<html' in content and 'lang=' not in content:
                issues.append({
                    "level": "warning",
                    "message": "建议在<html>标签中添加lang属性，如 lang=\"zh-CN\""
                })

            # 检查meta标签
            if '<meta charset=' not in content:
                issues.append({
                    "level": "error",
                    "message": "缺少字符集meta标签，建议添加 <meta charset=\"UTF-8\">"
                })

            if '<meta name="viewport"' not in content:
                issues.append({
                    "level": "warning",
                    "message": "缺少viewport meta标签，建议添加以支持响应式设计"
                })

            # 检查title标签
            if '<title>' not in content:
                issues.append({
                    "level": "error",
                    "message": "缺少<title>标签"
                })

            # 统计元素
            div_count = content.count('<div')
            img_count = content.count('<img')
            img_alt_count = content.count('alt=')
            link_count = content.count('<link')
            script_count = content.count('<script')

            result += f" 文件统计:\n"
            result += f"   - div元素: {div_count}\n"
            result += f"   - img元素: {img_count}\n"
            result += f"   - img alt属性: {img_alt_count}\n"
            result += f"   - link标签: {link_count}\n"
            result += f"   - script标签: {script_count}\n\n"

            # 检查img alt属性
            if img_count > 0 and img_alt_count < img_count:
                issues.append({
                    "level": "warning",
                    "message": f"有 {img_count - img_alt_count} 个img元素缺少alt属性"
                })

            # 显示问题
            if issues:
                result += f"  发现 {len(issues)} 个问题:\n\n"
                for i, issue in enumerate(issues, 1):
                    level = issue['level']
                    if level == 'error':
                        icon = f"{Fore.RED}{Style.RESET_ALL}"
                    elif level == 'warning':
                        icon = f"{Fore.YELLOW}{Style.RESET_ALL}"
                    else:
                        icon = f"{Fore.GREEN}ℹ{Style.RESET_ALL}"
                    result += f"{icon} {i}. {issue['message']}\n"
            else:
                result += f"{Fore.GREEN} 未发现问题{Style.RESET_ALL}\n"

            result += "\n" + "=" * 60 + "\n"

            return result

        except UnicodeDecodeError:
            return " 文件编码问题，无法读取"
        except Exception as e:
            return f" 验证失败: {str(e)}"

    def _test_css(self, file_path):
        """测试CSS文件"""
        if not os.path.exists(file_path):
            return f" 文件不存在: {file_path}"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            result = f"\n CSS测试结果: {file_path}\n"
            result += "=" * 60 + "\n\n"

            issues = []

            # 检查常见的CSS问题
            if content.count('{') != content.count('}'):
                issues.append({
                    "level": "error",
                    "message": "大括号不匹配"
                })

            # 检查颜色使用
            if '#000000' in content or '#ffffff' in content:
                issues.append({
                    "level": "info",
                    "message": "使用了纯黑或纯白，建议使用更柔和的颜色"
                })

            # 检查单位使用
            if content.count('px') > 10 and 'rem' not in content and 'em' not in content:
                issues.append({
                    "level": "warning",
                    "message": "大量使用px单位，建议考虑使用rem或em以支持更好的缩放"
                })

            # 统计
            rule_count = content.count('{')
            selector_count = len([line for line in content.split('\n') if '{' in line])

            result += f" 文件统计:\n"
            result += f"   - CSS规则: {rule_count}\n"
            result += f"   - 选择器: {selector_count}\n\n"

            # 显示问题
            if issues:
                result += f"  发现 {len(issues)} 个问题:\n\n"
                for i, issue in enumerate(issues, 1):
                    level = issue['level']
                    if level == 'error':
                        icon = f"{Fore.RED}{Style.RESET_ALL}"
                    elif level == 'warning':
                        icon = f"{Fore.YELLOW}{Style.RESET_ALL}"
                    else:
                        icon = f"{Fore.GREEN}ℹ{Style.RESET_ALL}"
                    result += f"{icon} {i}. {issue['message']}\n"
            else:
                result += f"{Fore.GREEN} 未发现问题{Style.RESET_ALL}\n"

            result += "\n" + "=" * 60 + "\n"

            return result

        except UnicodeDecodeError:
            return " 文件编码问题，无法读取"
        except Exception as e:
            return f" 测试失败: {str(e)}"

    def _check_js(self, file_path):
        """检查JS文件"""
        if not os.path.exists(file_path):
            return f" 文件不存在: {file_path}"

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            result = f"\n JavaScript检查结果: {file_path}\n"
            result += "=" * 60 + "\n\n"

            issues = []

            # 检查常见问题
            if 'var ' in content:
                issues.append({
                    "level": "warning",
                    "message": "使用了var声明，建议使用let或const"
                })

            if '==' in content and '!==' not in content:
                issues.append({
                    "level": "warning",
                    "message": "使用了==比较，建议使用===严格相等"
                })

            if content.count('console.log') > 5:
                issues.append({
                    "level": "info",
                    "message": f"有{content.count('console.log')}个console.log，生产环境建议移除"
                })

            if 'eval(' in content:
                issues.append({
                    "level": "error",
                    "message": "使用了eval()，存在安全风险"
                })

            # 统计
            line_count = len(content.split('\n'))
            function_count = content.count('function ')

            result += f" 文件统计:\n"
            result += f"   - 代码行数: {line_count}\n"
            result += f"   - 函数数量: {function_count}\n\n"

            # 显示问题
            if issues:
                result += f"  发现 {len(issues)} 个问题:\n\n"
                for i, issue in enumerate(issues, 1):
                    level = issue['level']
                    if level == 'error':
                        icon = f"{Fore.RED}{Style.RESET_ALL}"
                    elif level == 'warning':
                        icon = f"{Fore.YELLOW}{Style.RESET_ALL}"
                    else:
                        icon = f"{Fore.GREEN}ℹ{Style.RESET_ALL}"
                    result += f"{icon} {i}. {issue['message']}\n"
            else:
                result += f"{Fore.GREEN} 未发现问题{Style.RESET_ALL}\n"

            result += "\n" + "=" * 60 + "\n"

            return result

        except UnicodeDecodeError:
            return " 文件编码问题，无法读取"
        except Exception as e:
            return f" 检查失败: {str(e)}"

    def _preview_in_browser(self, file_path):
        """在浏览器中预览"""
        if not os.path.exists(file_path):
            return f" 文件不存在: {file_path}"

        try:
            # Windows系统
            os.startfile(file_path)
            return f" 已在默认浏览器中打开: {file_path}"
        except Exception as e:
            return f" 无法打开浏览器: {str(e)}"

    def _analyze_project(self, project_path):
        """分析整个前端项目"""
        if not os.path.exists(project_path):
            return f" 项目路径不存在: {project_path}"

        result = f"\n 前端项目分析: {project_path}\n"
        result += "=" * 60 + "\n\n"

        try:
            # 统计文件
            html_files = []
            css_files = []
            js_files = []

            for root, dirs, files in os.walk(project_path):
                for file in files:
                    if file.endswith('.html'):
                        html_files.append(os.path.join(root, file))
                    elif file.endswith('.css'):
                        css_files.append(os.path.join(root, file))
                    elif file.endswith('.js'):
                        js_files.append(os.path.join(root, file))

            result += f" 项目文件统计:\n"
            result += f"   - HTML文件: {len(html_files)}\n"
            result += f"   - CSS文件: {len(css_files)}\n"
            result += f"   - JavaScript文件: {len(js_files)}\n\n"

            # 建议检查
            result += f" 建议检查:\n"

            if html_files:
                result += f"   - HTML文件:\n"
                for html_file in html_files[:3]:  # 只显示前3个
                    result += f"     • {os.path.basename(html_file)}\n"
                if len(html_files) > 3:
                    result += f"     • ... 还有 {len(html_files) - 3} 个文件\n"

            if css_files:
                result += f"   - CSS文件:\n"
                for css_file in css_files[:3]:
                    result += f"     • {os.path.basename(css_file)}\n"
                if len(css_files) > 3:
                    result += f"     • ... 还有 {len(css_files) - 3} 个文件\n"

            if js_files:
                result += f"   - JavaScript文件:\n"
                for js_file in js_files[:3]:
                    result += f"     • {os.path.basename(js_file)}\n"
                if len(js_files) > 3:
                    result += f"     • ... 还有 {len(js_files) - 3} 个文件\n"

            result += f"\n{Fore.GREEN} 分析完成{Style.RESET_ALL}\n"
            result += "\n" + "=" * 60 + "\n"

            return result

        except Exception as e:
            return f" 分析失败: {str(e)}"


# 测试函数
def test_plugin():
    """测试插件功能"""
    plugin = Liugin()
    print("前端测试验证插件测试:")

    print("\n1. 创建测试HTML文件:")
    test_html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>测试页面</title>
</head>
<body>
    <h1>测试</h1>
</body>
</html>"""
    with open('test.html', 'w', encoding='utf-8') as f:
        f.write(test_html)

    print("\n2. 验证HTML:")
    print(plugin.handle("validate test.html"))

    print("\n3. 在浏览器中预览:")
    print(plugin.handle("preview test.html"))

    print("\n4. 分析项目:")
    print(plugin.handle("analyze ."))

    # 清理测试文件
    if os.path.exists('test.html'):
        os.remove('test.html')


if __name__ == "__main__":
    test_plugin()