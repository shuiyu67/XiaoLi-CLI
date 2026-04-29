"""
插件市场 Mixin — 提供 /plugin 命令
支持: install, remove, list, search, info
"""

import os
import sys
import json
import importlib.util
from colorama import Fore, Style

try:
    from urllib.request import urlopen, Request
    HAS_URLLIB = True
except ImportError:
    HAS_URLLIB = False


class PluginMarketMixin:
    """插件市场功能"""

    def _get_project_dir(self):
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _get_plugins_dir(self):
        return os.path.join(self._get_project_dir(), "plugins")

    def _get_registry_path(self):
        return os.path.join(self._get_project_dir(), "plugin_registry.json")

    def _get_config_path(self):
        return os.path.join(self._get_project_dir(), "plugins_config.py")

    # ── 注册表操作 ──

    def _load_registry(self):
        """加载本地注册表"""
        path = self._get_registry_path()
        if not os.path.exists(path):
            return {"version": 1, "plugins": {}}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"{Fore.YELLOW}⚠ 读取注册表失败: {e}，使用空注册表{Style.RESET_ALL}")
            return {"version": 1, "plugins": {}}

    def _save_registry(self, registry):
        """保存注册表"""
        path = self._get_registry_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(registry, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"{Fore.RED}❌ 保存注册表失败: {e}{Style.RESET_ALL}")

    def _fetch_remote_registry(self):
        """拉取远程注册表并合并"""
        remote_urls = [
            "https://gitee.com/shuiyu1123/xiaoli-cli-plugins/raw/master/plugin_registry.json",
        ]
        registry = self._load_registry()
        merged_count = 0

        for url in remote_urls:
            try:
                req = Request(url, headers={"User-Agent": "xiaoli-cli/1.0"})
                resp = urlopen(req, timeout=10)
                remote = json.loads(resp.read().decode('utf-8'))
                remote_plugins = remote.get("plugins", {})
                for code, info in remote_plugins.items():
                    if code not in registry.get("plugins", {}):
                        registry.setdefault("plugins", {})[code] = info
                        merged_count += 1
                break  # 成功就不再尝试其他源
            except Exception:
                continue

        if merged_count > 0:
            self._save_registry(registry)
            print(f"{Fore.DIM}  (从远程同步了 {merged_count} 个插件){Style.RESET_ALL}")

        return registry

    # ── 配置文件操作 ──

    def _enable_plugin_in_config(self, plugin_name):
        """在 plugins_config.py 中启用插件"""
        config_path = self._get_config_path()
        enable_key = f"ENABLE_{plugin_name.upper()}"

        if not os.path.exists(config_path):
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(f"# 小狸插件配置\n\n{enable_key} = True\n")
            return True

        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 检查是否已存在
        if enable_key in content:
            # 替换为 True
            lines = content.split('\n')
            new_lines = []
            for line in lines:
                if line.strip().startswith(enable_key):
                    new_lines.append(f"{enable_key} = True")
                else:
                    new_lines.append(line)
            with open(config_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines))
        else:
            # 追加
            with open(config_path, 'a', encoding='utf-8') as f:
                f.write(f"\n{enable_key} = True\n")

        return True

    def _disable_plugin_in_config(self, plugin_name):
        """在 plugins_config.py 中禁用插件"""
        config_path = self._get_config_path()
        enable_key = f"ENABLE_{plugin_name.upper()}"

        if not os.path.exists(config_path):
            return False

        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()

        if enable_key not in content:
            return False

        lines = content.split('\n')
        new_lines = []
        for line in lines:
            if line.strip().startswith(enable_key):
                new_lines.append(f"{enable_key} = False")
            else:
                new_lines.append(line)
        with open(config_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(new_lines))
        return True

    # ── 下载安装 ──

    def _download_file(self, url, dest_path):
        """下载文件到指定路径"""
        if not HAS_URLLIB:
            return False, "缺少 urllib 模块"
        try:
            req = Request(url, headers={"User-Agent": "xiaoli-cli/1.0"})
            resp = urlopen(req, timeout=30)
            data = resp.read()
            with open(dest_path, 'wb') as f:
                f.write(data)
            return True, f"下载完成 ({len(data)} 字节)"
        except Exception as e:
            return False, str(e)

    def _install_deps(self, deps, optional=False):
        """提示安装依赖（不自动安装，遵守安全规则）"""
        if not deps:
            return
        label = "可选依赖" if optional else "依赖"
        print(f"{Fore.YELLOW}  📦 {label}：{', '.join(deps)}{Style.RESET_ALL}")
        print(f"{Fore.DIM}     运行: pip install {' '.join(deps)}{Style.RESET_ALL}")

    # ── /plugin 命令入口 ──

    def handle_plugin_command(self, args):
        """处理 /plugin 命令"""
        args = args.strip()
        if not args:
            return self._plugin_help()

        parts = args.split(maxsplit=1)
        sub = parts[0].lower()
        rest = parts[1] if len(parts) > 1 else ""

        if sub == "install":
            return self._plugin_install(rest.strip())
        elif sub in ("remove", "uninstall"):
            return self._plugin_remove(rest.strip())
        elif sub == "list":
            return self._plugin_list()
        elif sub == "search":
            return self._plugin_search(rest.strip())
        elif sub == "info":
            return self._plugin_info(rest.strip())
        elif sub == "update":
            return self._plugin_update(rest.strip())
        elif sub == "add-source":
            return self._plugin_add_source(rest.strip())
        else:
            return f"{Fore.RED}❌ 未知子命令: {sub}\n{self._plugin_help()}"

    def _plugin_help(self):
        """插件市场帮助"""
        return f"""{Fore.CYAN}🔌 插件市场{Style.RESET_ALL}

{Fore.WHITE}命令:{Style.RESET_ALL}
  /plugin list                    列出所有可用插件
  /plugin search <关键词>          搜索插件
  /plugin info <插件码>            查看插件详情
  /plugin install <插件码>         安装插件
  /plugin install <URL>           从 URL 安装插件
  /plugin remove <插件名>          卸载插件
  /plugin update <插件码>          更新已安装的插件
  /plugin add-source <URL>        添加远程插件源

{Fore.WHITE}示例:{Style.RESET_ALL}
  /plugin list                    查看可用插件
  /plugin install dglab           安装 DG-Lab 插件
  /plugin search 郊狼              搜索相关插件
  /plugin remove dglab_ws         卸载插件"""

    def _plugin_list(self):
        """列出所有可用插件"""
        registry = self._fetch_remote_registry()
        plugins = registry.get("plugins", {})

        if not plugins:
            return f"{Fore.YELLOW}📭 插件注册表为空，运行 /plugin install <URL> 从 URL 安装{Style.RESET_ALL}"

        # 检查已安装状态
        plugins_dir = self._get_plugins_dir()
        installed = set()
        if os.path.exists(plugins_dir):
            for f in os.listdir(plugins_dir):
                if f.endswith('.py') and f != '__init__.py':
                    installed.add(f[:-3])

        lines = [f"{Fore.CYAN}🔌 可用插件列表:{Style.RESET_ALL}\n"]
        for code, info in sorted(plugins.items()):
            name = info.get("name", code)
            desc = info.get("description", "")
            version = info.get("version", "")
            target_file = info.get("file", f"{code}.py")
            target_name = target_file[:-3] if target_file.endswith('.py') else target_file

            if target_name in installed:
                status = f"{Fore.GREEN}✓ 已安装{Style.RESET_ALL}"
            else:
                status = f"{Fore.DIM}○ 未安装{Style.RESET_ALL}"

            lines.append(f"  {Fore.WHITE}{code:<15}{Style.RESET_ALL} {status}  {name}")
            if desc:
                lines.append(f"  {Fore.DIM}{'':15}  {desc[:50]}{Style.RESET_ALL}")
            if version:
                lines.append(f"  {Fore.DIM}{'':15}  v{version}{Style.RESET_ALL}")

        lines.append(f"\n{Fore.DIM}使用 /plugin install <插件码> 安装{Style.RESET_ALL}")
        return "\n".join(lines)

    def _plugin_search(self, keyword):
        """搜索插件"""
        if not keyword:
            return f"{Fore.YELLOW}请提供搜索关键词: /plugin search <关键词>{Style.RESET_ALL}"

        registry = self._fetch_remote_registry()
        plugins = registry.get("plugins", {})
        keyword_lower = keyword.lower()

        matches = []
        for code, info in plugins.items():
            score = 0
            name = info.get("name", "").lower()
            desc = info.get("description", "").lower()
            keywords = [k.lower() for k in info.get("keywords", [])]

            if keyword_lower in code.lower():
                score += 100
            if keyword_lower in name:
                score += 50
            if keyword_lower in desc:
                score += 30
            for kw in keywords:
                if keyword_lower in kw:
                    score += 20

            if score > 0:
                matches.append((score, code, info))

        matches.sort(key=lambda x: x[0], reverse=True)

        if not matches:
            return f"{Fore.YELLOW}🔍 未找到与 '{keyword}' 相关的插件{Style.RESET_ALL}"

        lines = [f"{Fore.CYAN}🔍 搜索 '{keyword}' 的结果:{Style.RESET_ALL}\n"]
        for _, code, info in matches:
            name = info.get("name", code)
            desc = info.get("description", "")
            lines.append(f"  {Fore.WHITE}{code:<15}{Style.RESET_ALL} {name}")
            if desc:
                lines.append(f"  {Fore.DIM}{'':15}  {desc[:60]}{Style.RESET_ALL}")

        return "\n".join(lines)

    def _plugin_info(self, code):
        """查看插件详情"""
        if not code:
            return f"{Fore.YELLOW}请提供插件码: /plugin info <插件码>{Style.RESET_ALL}"

        registry = self._fetch_remote_registry()
        plugins = registry.get("plugins", {})

        if code not in plugins:
            return f"{Fore.RED}❌ 未找到插件 '{code}'，运行 /plugin list 查看可用插件{Style.RESET_ALL}"

        info = plugins[code]
        name = info.get("name", code)
        desc = info.get("description", "")
        author = info.get("author", "未知")
        version = info.get("version", "未知")
        deps = info.get("deps", [])
        opt_deps = info.get("optional_deps", [])
        url = info.get("url", "")
        docs = info.get("docs", "")
        keywords = info.get("keywords", [])

        lines = [
            f"{Fore.CYAN}📦 插件详情: {code}{Style.RESET_ALL}\n",
            f"  名称:     {name}",
            f"  版本:     {version}",
            f"  作者:     {author}",
        ]
        if desc:
            lines.append(f"  描述:     {desc}")
        if keywords:
            lines.append(f"  关键词:   {', '.join(keywords)}")
        if deps:
            lines.append(f"  依赖:     {', '.join(deps)}")
        if opt_deps:
            lines.append(f"  可选依赖: {', '.join(opt_deps)}")
        if url:
            lines.append(f"  下载地址: {url}")
        if docs:
            lines.append(f"  文档:     {docs}")

        lines.append(f"\n  {Fore.GREEN}/plugin install {code}{Style.RESET_ALL}  安装此插件")
        return "\n".join(lines)

    def _plugin_install(self, code):
        """安装插件"""
        if not code:
            return f"{Fore.YELLOW}请提供插件码或 URL: /plugin install <插件码|URL>{Style.RESET_ALL}"

        plugins_dir = self._get_plugins_dir()
        os.makedirs(plugins_dir, exist_ok=True)

        # 判断是 URL 还是插件码
        if code.startswith("http://") or code.startswith("https://"):
            return self._install_from_url(code)

        # 从注册表查找
        registry = self._fetch_remote_registry()
        plugins = registry.get("plugins", {})

        if code not in plugins:
            return (
                f"{Fore.RED}❌ 未找到插件 '{code}'\n"
                f"{Fore.YELLOW}运行 /plugin list 查看可用插件\n"
                f"或使用 /plugin install <URL> 从 URL 安装{Style.RESET_ALL}"
            )

        info = plugins[code]
        name = info.get("name", code)
        url = info.get("url", "")
        target_file = info.get("file", f"{code}.py")
        deps = info.get("deps", [])
        opt_deps = info.get("optional_deps", [])

        if not url:
            return f"{Fore.RED}❌ 插件 '{code}' 没有下载地址{Style.RESET_ALL}"

        dest = os.path.join(plugins_dir, target_file)

        # 检查是否已安装
        if os.path.exists(dest):
            print(f"{Fore.YELLOW}⚠ 插件 '{name}' 已存在，将覆盖更新{Style.RESET_ALL}")

        print(f"{Fore.CYAN}📥 正在安装: {name}{Style.RESET_ALL}")
        print(f"{Fore.DIM}   下载: {url}{Style.RESET_ALL}")

        ok, msg = self._download_file(url, dest)
        if not ok:
            return f"{Fore.RED}❌ 下载失败: {msg}{Style.RESET_ALL}"

        print(f"{Fore.GREEN}   ✓ 文件已保存到: {dest}{Style.RESET_ALL}")

        # 下载文档
        docs_url = info.get("docs", "")
        if docs_url:
            docs_dest = os.path.join(plugins_dir, target_file.replace('.py', '_README.md'))
            ok_docs, _ = self._download_file(docs_url, docs_dest)
            if ok_docs:
                print(f"{Fore.GREEN}   ✓ 文档已保存到: {docs_dest}{Style.RESET_ALL}")

        # 启用插件
        plugin_module_name = target_file[:-3] if target_file.endswith('.py') else target_file
        self._enable_plugin_in_config(plugin_module_name)
        print(f"{Fore.GREEN}   ✓ 已在配置中启用: ENABLE_{plugin_module_name.upper()} = True{Style.RESET_ALL}")

        # 提示依赖
        self._install_deps(deps, optional=False)
        self._install_deps(opt_deps, optional=True)

        # 尝试动态加载
        print(f"{Fore.CYAN}   🔄 尝试动态加载插件...{Style.RESET_ALL}")
        try:
            spec = importlib.util.spec_from_file_location(plugin_module_name, dest)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin_class = getattr(module, 'Liugin', None) or getattr(module, 'Plugin', None)
            if plugin_class:
                instance = plugin_class()
                tool_info = instance.get_tool_info()
                tool_info['handler'] = instance.handle
                if hasattr(instance, 'set_cli'):
                    instance.set_cli(self)
                self.liugin_manager.tools.append(tool_info)
                print(f"{Fore.GREEN}   ✓ 插件已加载: {tool_info.get('name', plugin_module_name)}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}   ⚠ 未找到 Liugin/Plugin 类，重启后自动加载{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}   ⚠ 动态加载失败: {e}，重启后自动加载{Style.RESET_ALL}")

        return f"\n{Fore.GREEN}🎉 插件 '{name}' 安装完成!{Style.RESET_ALL}"

    def _install_from_url(self, url):
        """从 URL 直接安装"""
        plugins_dir = self._get_plugins_dir()
        os.makedirs(plugins_dir, exist_ok=True)

        # 从 URL 提取文件名
        filename = url.split('/')[-1].split('?')[0]
        if not filename.endswith('.py'):
            return f"{Fore.RED}❌ URL 必须指向 .py 文件{Style.RESET_ALL}"

        dest = os.path.join(plugins_dir, filename)

        print(f"{Fore.CYAN}📥 正在从 URL 安装: {url}{Style.RESET_ALL}")

        ok, msg = self._download_file(url, dest)
        if not ok:
            return f"{Fore.RED}❌ 下载失败: {msg}{Style.RESET_ALL}"

        plugin_name = filename[:-3]
        self._enable_plugin_in_config(plugin_name)
        print(f"{Fore.GREEN}   ✓ 已保存到: {dest}{Style.RESET_ALL}")
        print(f"{Fore.GREEN}   ✓ 已启用: ENABLE_{plugin_name.upper()}{Style.RESET_ALL}")

        # 尝试动态加载
        try:
            spec = importlib.util.spec_from_file_location(plugin_name, dest)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            plugin_class = getattr(module, 'Liugin', None) or getattr(module, 'Plugin', None)
            if plugin_class:
                instance = plugin_class()
                tool_info = instance.get_tool_info()
                tool_info['handler'] = instance.handle
                if hasattr(instance, 'set_cli'):
                    instance.set_cli(self)
                self.liugin_manager.tools.append(tool_info)
                print(f"{Fore.GREEN}   ✓ 插件已加载: {tool_info.get('name', plugin_name)}{Style.RESET_ALL}")
        except Exception as e:
            print(f"{Fore.YELLOW}   ⚠ 动态加载失败: {e}，重启后自动加载{Style.RESET_ALL}")

        return f"\n{Fore.GREEN}🎉 插件安装完成!{Style.RESET_ALL}"

    def _plugin_remove(self, name):
        """卸载插件"""
        if not name:
            return f"{Fore.YELLOW}请提供插件名: /plugin remove <插件名>{Style.RESET_ALL}"

        plugins_dir = self._get_plugins_dir()

        # 查找插件文件
        target = None
        for f in os.listdir(plugins_dir):
            if f.endswith('.py') and f != '__init__.py':
                module_name = f[:-3]
                if module_name == name or f == name:
                    target = os.path.join(plugins_dir, f)
                    break

        if not target:
            return f"{Fore.RED}❌ 未找到已安装的插件 '{name}'{Style.RESET_ALL}"

        module_name = os.path.basename(target)[:-3]

        # 删除文件
        try:
            os.remove(target)
            print(f"{Fore.GREEN}   ✓ 已删除: {target}{Style.RESET_ALL}")
        except Exception as e:
            return f"{Fore.RED}❌ 删除失败: {e}{Style.RESET_ALL}"

        # 删除关联文档
        docs_file = target.replace('.py', '_README.md')
        if os.path.exists(docs_file):
            os.remove(docs_file)

        # 禁用插件
        self._disable_plugin_in_config(module_name)
        print(f"{Fore.GREEN}   ✓ 已禁用: ENABLE_{module_name.upper()} = False{Style.RESET_ALL}")

        # 从内存中移除
        self.liugin_manager.tools = [
            t for t in self.liugin_manager.tools
            if t.get('name') != module_name
        ]

        return f"\n{Fore.GREEN}🗑️ 插件 '{name}' 已卸载{Style.RESET_ALL}"

    def _plugin_update(self, code):
        """更新插件（重新下载）"""
        if not code:
            return f"{Fore.YELLOW}请提供插件码: /plugin update <插件码>{Style.RESET_ALL}"

        registry = self._load_registry()
        plugins = registry.get("plugins", {})

        if code not in plugins:
            return f"{Fore.RED}❌ 注册表中未找到 '{code}'，无法更新{Style.RESET_ALL}"

        # 检查是否已安装
        info = plugins[code]
        target_file = info.get("file", f"{code}.py")
        dest = os.path.join(self._get_plugins_dir(), target_file)

        if not os.path.exists(dest):
            return f"{Fore.YELLOW}⚠ 插件 '{code}' 未安装，使用 /plugin install {code} 安装{Style.RESET_ALL}"

        print(f"{Fore.CYAN}🔄 更新插件: {code}{Style.RESET_ALL}")
        return self._plugin_install(code)

    def _plugin_add_source(self, url):
        """添加远程插件源"""
        if not url:
            return f"{Fore.YELLOW}请提供注册表 URL: /plugin add-source <URL>{Style.RESET_ALL}"

        print(f"{Fore.CYAN}📡 正在同步插件源: {url}{Style.RESET_ALL}")

        try:
            req = Request(url, headers={"User-Agent": "xiaoli-cli/1.0"})
            resp = urlopen(req, timeout=15)
            remote = json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            return f"{Fore.RED}❌ 拉取失败: {e}{Style.RESET_ALL}"

        registry = self._load_registry()
        remote_plugins = remote.get("plugins", {})
        added = 0
        updated = 0

        for code, info in remote_plugins.items():
            if code in registry.get("plugins", {}):
                registry["plugins"][code] = info
                updated += 1
            else:
                registry.setdefault("plugins", {})[code] = info
                added += 1

        self._save_registry(registry)

        return (
            f"{Fore.GREEN}✓ 插件源同步完成: 新增 {added} 个，更新 {updated} 个{Style.RESET_ALL}"
        )
