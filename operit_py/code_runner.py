# METADATA
# {
#   "name": "code_runner",
#   "display_name": {"zh": "代码运行器", "en": "Code Runner"},
#   "description": {"zh": "提供多语言代码执行能力，支持JavaScript、Python、Ruby、Go、Rust、C和C++脚本的运行。可直接执行代码字符串或运行外部文件，适用于快速测试、自动化脚本和教学演示。", "en": "Multi-language code execution. Supports running JavaScript, Python, Ruby, Go, Rust, C and C++ scripts. You can execute code strings directly or run external files, useful for quick tests, automation, and demos."},
#   "enabledByDefault": True,
#   "category": "Development",
#   "tools": [
#     {"name": "run_javascript_es5", "description": {"zh": "运行自定义 JavaScript (ES5) 脚本。", "en": "Run custom JavaScript (ES5)."}, "parameters": [{"name": "script", "description": {"zh": "要执行的 JavaScript 脚本内容", "en": "JavaScript script content to execute."}, "type": "string", "required": True}]},
#     {"name": "run_javascript_file", "description": {"zh": "运行 JavaScript (ES5) 文件。", "en": "Run a JavaScript (ES5) file."}, "parameters": [{"name": "file_path", "description": {"zh": "JavaScript 文件路径", "en": "Path to the JavaScript file."}, "type": "string", "required": True}]},
#     {"name": "run_javascript_node", "description": {"zh": "使用 Node.js 运行 JavaScript 脚本。", "en": "Run JavaScript using Node.js."}, "parameters": [{"name": "script", "description": {"zh": "要执行的 JavaScript 脚本内容", "en": "JavaScript script content to execute."}, "type": "string", "required": True}, {"name": "node_flags", "description": {"zh": "Node.js 解释器选项", "en": "Node.js interpreter flags."}, "type": "string", "required": False}]},
#     {"name": "run_javascript_node_file", "description": {"zh": "使用 Node.js 运行 JavaScript 文件。", "en": "Run a JavaScript file using Node.js."}, "parameters": [{"name": "file_path", "description": {"zh": "JavaScript 文件路径", "en": "Path to the JavaScript file."}, "type": "string", "required": True}, {"name": "node_flags", "description": {"zh": "Node.js 解释器选项", "en": "Node.js interpreter flags."}, "type": "string", "required": False}]},
#     {"name": "install_node_packages", "description": {"zh": "在持久 Node 工作目录中安装 pnpm 包", "en": "Install packages with pnpm in the persistent Node workspace."}, "parameters": [{"name": "packages", "description": {"zh": "要安装的包名（用 | 分隔）", "en": "Package names to install, separated by |."}, "type": "string", "required": True}, {"name": "save_dev", "description": {"zh": "是否作为开发依赖安装", "en": "Whether to install as dev dependency."}, "type": "boolean", "required": False}]},
#     {"name": "install_python_packages", "description": {"zh": "在持久虚拟环境中安装 Python 包", "en": "Install Python packages in the persistent virtual environment using pip."}, "parameters": [{"name": "packages", "description": {"zh": "要安装的包名（用 | 分隔）", "en": "Package names to install, separated by |."}, "type": "string", "required": True}, {"name": "upgrade", "description": {"zh": "是否升级已安装的包", "en": "Whether to upgrade already installed packages."}, "type": "boolean", "required": False}]},
#     {"name": "run_python", "description": {"zh": "运行自定义 Python 脚本。", "en": "Run custom Python scripts."}, "parameters": [{"name": "script", "description": {"zh": "要执行的 Python 脚本内容", "en": "Python script content to execute."}, "type": "string", "required": True}, {"name": "python_flags", "description": {"zh": "Python 解释器选项", "en": "Python interpreter flags."}, "type": "string", "required": False}, {"name": "script_args", "description": {"zh": "传递给 Python 脚本的参数", "en": "Arguments passed to the Python script."}, "type": "string", "required": False}]},
#     {"name": "run_python_file", "description": {"zh": "运行 Python 文件。", "en": "Run a Python file."}, "parameters": [{"name": "file_path", "description": {"zh": "Python 文件路径", "en": "Path to the Python file."}, "type": "string", "required": True}, {"name": "python_flags", "description": {"zh": "Python 解释器选项", "en": "Python interpreter flags."}, "type": "string", "required": False}, {"name": "script_args", "description": {"zh": "传递给 Python 文件的参数", "en": "Arguments passed to the Python file."}, "type": "string", "required": False}]},
#     {"name": "run_ruby", "description": {"zh": "运行自定义 Ruby 脚本", "en": "Run custom Ruby scripts."}, "parameters": [{"name": "script", "description": {"zh": "要执行的 Ruby 脚本内容", "en": "Ruby script content to execute."}, "type": "string", "required": True}, {"name": "ruby_flags", "description": {"zh": "Ruby 解释器选项", "en": "Ruby interpreter flags."}, "type": "string", "required": False}]},
#     {"name": "run_ruby_file", "description": {"zh": "运行 Ruby 文件", "en": "Run a Ruby file."}, "parameters": [{"name": "file_path", "description": {"zh": "Ruby 文件路径", "en": "Path to the Ruby file."}, "type": "string", "required": True}, {"name": "ruby_flags", "description": {"zh": "Ruby 解释器选项", "en": "Ruby interpreter flags."}, "type": "string", "required": False}]},
#     {"name": "run_go", "description": {"zh": "运行自定义 Go 代码", "en": "Run custom Go code."}, "parameters": [{"name": "script", "description": {"zh": "要执行的 Go 代码内容", "en": "Go source code to execute."}, "type": "string", "required": True}, {"name": "build_flags", "description": {"zh": "Go 编译选项", "en": "Go build flags."}, "type": "string", "required": False}]},
#     {"name": "run_go_file", "description": {"zh": "运行 Go 文件", "en": "Run a Go file."}, "parameters": [{"name": "file_path", "description": {"zh": "Go 文件路径", "en": "Path to the Go file."}, "type": "string", "required": True}, {"name": "build_flags", "description": {"zh": "Go 编译选项", "en": "Go build flags."}, "type": "string", "required": False}]},
#     {"name": "run_rust", "description": {"zh": "运行自定义 Rust 代码", "en": "Run custom Rust code."}, "parameters": [{"name": "script", "description": {"zh": "要执行的 Rust 代码内容", "en": "Rust source code to execute."}, "type": "string", "required": True}, {"name": "cargo_flags", "description": {"zh": "Cargo 构建选项", "en": "Cargo build flags."}, "type": "string", "required": False}]},
#     {"name": "run_rust_file", "description": {"zh": "运行 Rust 文件", "en": "Run a Rust file."}, "parameters": [{"name": "file_path", "description": {"zh": "Rust 文件路径", "en": "Path to the Rust file."}, "type": "string", "required": True}, {"name": "cargo_flags", "description": {"zh": "Cargo 构建选项", "en": "Cargo build flags."}, "type": "string", "required": False}]},
#     {"name": "run_c", "description": {"zh": "运行自定义 C 代码", "en": "Run custom C code."}, "parameters": [{"name": "script", "description": {"zh": "要执行的 C 代码内容", "en": "C source code to execute."}, "type": "string", "required": True}, {"name": "compile_flags", "description": {"zh": "编译选项", "en": "Compile flags."}, "type": "string", "required": False}]},
#     {"name": "run_c_file", "description": {"zh": "运行 C 文件", "en": "Run a C file."}, "parameters": [{"name": "file_path", "description": {"zh": "C 文件路径", "en": "Path to the C file."}, "type": "string", "required": True}, {"name": "compile_flags", "description": {"zh": "编译选项", "en": "Compile flags."}, "type": "string", "required": False}]},
#     {"name": "run_cpp", "description": {"zh": "运行自定义 C++ 代码", "en": "Run custom C++ code."}, "parameters": [{"name": "script", "description": {"zh": "要执行的 C++ 代码内容", "en": "C++ source code to execute."}, "type": "string", "required": True}, {"name": "compile_flags", "description": {"zh": "编译选项", "en": "Compile flags."}, "type": "string", "required": False}]},
#     {"name": "run_cpp_file", "description": {"zh": "运行 C++ 文件", "en": "Run a C++ file."}, "parameters": [{"name": "file_path", "description": {"zh": "C++ 文件路径", "en": "Path to the C++ file."}, "type": "string", "required": True}, {"name": "compile_flags", "description": {"zh": "编译选项", "en": "Compile flags."}, "type": "string", "required": False}]}
#   ]
# }

import json
import re
import time
from urllib.parse import quote, unquote

Error = Exception

CARGO_MIRROR_ENV = 'export CARGO_REGISTRIES_CRATES_IO_REPLACE_WITH="ustc" && export CARGO_REGISTRIES_USTC_INDEX="https://mirrors.ustc.edu.cn/crates.io-index"'
CODE_RUNNER_HIDDEN_EXECUTOR_KEY = "code_runner_hidden_executor"
NODE_WORKSPACE_DIR = "$HOME/.code_runner/node"


async def executeTerminalCommand(command, timeoutMs=None):
    options = {"executorKey": CODE_RUNNER_HIDDEN_EXECUTOR_KEY}
    if timeoutMs is not None:
        options["timeoutMs"] = timeoutMs
    return await Tools.System.terminal.hiddenExec(command, options)


async def ensurePersistentVenv():
    venvDir = "~/.code_runner/py"
    pythonBin = f"{venvDir}/bin/python"
    pipBin = f"{venvDir}/bin/pip"

    exists = await executeTerminalCommand(f"[ -x {pythonBin} ] && echo OK || echo NO")
    if "OK" in (getattr(exists, "output", "") or ""):
        return {"pythonBin": pythonBin, "pipBin": pipBin}

    setup = await executeTerminalCommand(f"python3 -m venv {venvDir}")
    if getattr(setup, "exitCode", 1) != 0 or hasError(getattr(setup, "output", "") or ""):
        raise Error(f"创建持久 venv 失败：\n{getattr(setup, 'output', '')}")
    return {"pythonBin": pythonBin, "pipBin": pipBin}


async def install_python_packages(params):
    raw = (params.get("packages") or "").strip()
    pkgs = [s.strip() for s in raw.split("|") if s.strip()]
    if not pkgs:
        raise Error("请提供要安装的包列表（用 | 分隔）packages")

    upgradeFlag = "-U" if params.get("upgrade") else ""
    venv = await ensurePersistentVenv()
    pythonBin = venv["pythonBin"]

    r2 = await executeTerminalCommand(f"{pythonBin} -m pip install {upgradeFlag} {' '.join(pkgs)}".strip())
    if getattr(r2, "exitCode", 1) != 0 or hasError(getattr(r2, "output", "") or ""):
        raise Error(f"安装依赖失败：\n{getattr(r2, 'output', '')}")
    return f"Installed with pip:\n{getattr(r2, 'output', '')}".strip()


async def ensureNodeAvailable():
    nodeCheckResult = await executeTerminalCommand("node --version")
    if getattr(nodeCheckResult, "exitCode", 1) != 0 or hasError(getattr(nodeCheckResult, "output", "") or ""):
        raise Error("Node.js 不可用，请确保已安装 Node.js")


async def ensurePersistentNodeWorkspace():
    await ensureNodeAvailable()

    createDirResult = await executeTerminalCommand(f"mkdir -p {NODE_WORKSPACE_DIR}")
    if getattr(createDirResult, "exitCode", 1) != 0 or hasError(getattr(createDirResult, "output", "") or ""):
        raise Error(f"创建 Node 工作目录失败:\n{getattr(createDirResult, 'output', '')}")

    hasPackageJson = await executeTerminalCommand(f"[ -f {NODE_WORKSPACE_DIR}/package.json ] && echo OK || echo NO")
    if "OK" not in (getattr(hasPackageJson, "output", "") or ""):
        initResult = await executeTerminalCommand(
            f"cat <<'EOF' > {NODE_WORKSPACE_DIR}/package.json\n{{\n  \"name\": \"code-runner-node-workspace\",\n  \"private\": true\n}}\nEOF"
        )
        if getattr(initResult, "exitCode", 1) != 0 or hasError(getattr(initResult, "output", "") or ""):
            raise Error(f"初始化 Node 工作目录失败:\n{getattr(initResult, 'output', '')}")

    return {"workspaceDir": NODE_WORKSPACE_DIR}


async def install_node_packages(params):
    raw = (params.get("packages") or "").strip()
    pkgs = [s.strip() for s in raw.split("|") if s.strip()]
    if not pkgs:
        raise Error("请提供要安装的包列表（用 | 分隔）packages")

    ws = await ensurePersistentNodeWorkspace()
    workspaceDir = ws["workspaceDir"]
    saveFlag = "-D" if params.get("save_dev") else "--save"
    packageArgs = " ".join([f"'{escapeForShell(p)}'" for p in pkgs])
    result = await executeTerminalCommand(f"cd {workspaceDir} && pnpm add {saveFlag} {packageArgs}")
    if getattr(result, "exitCode", 1) != 0 or hasError(getattr(result, "output", "") or ""):
        raise Error(f"安装 pnpm 依赖失败:\n{getattr(result, 'output', '')}")
    return f"Installed with pnpm in {workspaceDir}:\n{getattr(result, 'output', '')}".strip()


def escapeForShell(s):
    return str(s).replace("'", "'\\''")


def buildPipeSeparatedShellArgs(raw):
    if not raw or raw.strip() == "":
        return ""
    parts = [p.strip() for p in raw.split("|") if p.strip()]
    return " ".join([f"'{escapeForShell(p)}'" for p in parts])


async def executeJavaScript(script):
    # 注意：原 TypeScript 使用 new Function() 在内置 JS 引擎中执行。
    # Python 运行时无内置 JS 引擎，此处降级为通过 Node.js 执行。
    ws = await ensurePersistentNodeWorkspace()
    workspaceDir = ws["workspaceDir"]
    tempFileName = f"temp_script_es5_{int(time.time() * 1000)}.js"
    tempFilePath = f"{workspaceDir}/{tempFileName}"
    try:
        await executeTerminalCommand(f"cat <<'EOF' > {tempFilePath}\n{script}\nEOF")
        result = await executeTerminalCommand(f"cd {workspaceDir} && NODE_PATH={workspaceDir}/node_modules node {tempFileName}")
        if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
            return (getattr(result, "output", "") or "").strip()
        else:
            raise Error(f"JavaScript (ES5) 脚本执行失败:\n{getattr(result, 'output', '')}")
    finally:
        try:
            await executeTerminalCommand(f"rm -f {tempFilePath}")
        except Exception as err:
            console.error(f"删除临时文件失败: {str(err)}")


def hasError(output):
    errorPatterns = [
        "command not found", "No such file or directory",
        "error:", "Error:", "failed", "Failed", "unable", "Unable",
    ]
    lowercasedOutput = (output or "").lower()
    return any(pattern.lower() in lowercasedOutput for pattern in errorPatterns)


async def main():
    await executeTerminalCommand("mkdir -p /tmp")

    results = {
        "javascript": await testJavaScript(),
        "python": await testPython(),
        "ruby": await testRuby(),
        "go": await testGo(),
        "rust": await testRust(),
        "c": await testC(),
        "cpp": await testCpp(),
    }

    summary = "代码执行器功能测试结果：\n"
    for lang, result in results.items():
        summary += f"{lang}: {'✅ 成功' if result.get('success') else '❌ 失败'} - {result.get('message')}\n"

    return summary


async def testJavaScript():
    try:
        script = "console.log('JavaScript 运行正常'); const testVar = 42; console.log('测试值: ' + testVar);"
        result = await executeJavaScript(script)
        if "JavaScript 运行正常" in result:
            return {"success": True, "message": "JavaScript执行器测试成功"}
        return {"success": False, "message": f"JavaScript执行器测试失败: 实际 \"{result}\""}
    except Exception as error:
        return {"success": False, "message": f"JavaScript执行器测试失败: {str(error)}"}


async def testPython():
    try:
        pythonCheckResult = await executeTerminalCommand("python3 --version")
        if getattr(pythonCheckResult, "exitCode", 1) != 0 or hasError(getattr(pythonCheckResult, "output", "") or ""):
            return {"success": False, "message": "Python不可用，请确保已安装Python"}

        script = "print('Python运行正常')"
        tempPyFile = "/tmp/test_python.py"
        await executeTerminalCommand(f"cat <<'EOF' > {tempPyFile}\n{script}\nEOF")
        runResult = await executeTerminalCommand(f"python3 {tempPyFile}")
        await executeTerminalCommand(f"rm -f {tempPyFile}")

        if getattr(runResult, "exitCode", 1) != 0 or hasError(getattr(runResult, "output", "") or "") or "Python运行正常" not in (getattr(runResult, "output", "") or ""):
            return {"success": False, "message": f"Python执行器测试失败: {getattr(runResult, 'output', '')}"}
        return {"success": True, "message": "Python执行器测试成功"}
    except Exception as error:
        return {"success": False, "message": f"Python执行器测试失败: {str(error)}"}


async def testRuby():
    try:
        rubyCheckResult = await executeTerminalCommand("ruby --version")
        if getattr(rubyCheckResult, "exitCode", 1) != 0 or hasError(getattr(rubyCheckResult, "output", "") or ""):
            return {"success": False, "message": "Ruby不可用，请确保已安装Ruby"}

        script = "puts 'Ruby运行正常'"
        tempRbFile = "/tmp/test_ruby.rb"
        await executeTerminalCommand(f"cat <<'EOF' > {tempRbFile}\n{script}\nEOF")
        runResult = await executeTerminalCommand(f"ruby {tempRbFile}")
        await executeTerminalCommand(f"rm -f {tempRbFile}")

        if getattr(runResult, "exitCode", 1) != 0 or hasError(getattr(runResult, "output", "") or "") or "Ruby运行正常" not in (getattr(runResult, "output", "") or ""):
            return {"success": False, "message": f"Ruby执行器测试失败: {getattr(runResult, 'output', '')}"}
        return {"success": True, "message": "Ruby执行器测试成功"}
    except Exception as error:
        return {"success": False, "message": f"Ruby执行器测试失败: {str(error)}"}


async def testGo():
    try:
        goCheckResult = await executeTerminalCommand("go version")
        if getattr(goCheckResult, "exitCode", 1) != 0 or hasError(getattr(goCheckResult, "output", "") or ""):
            return {"success": False, "message": "Go不可用，请确保已安装Go"}

        script = 'package main\nimport "fmt"\nfunc main() {\n  fmt.Println("Go运行正常")\n}'
        tempGoDir = "/tmp/test_go_project"
        tempGoFile = f"{tempGoDir}/main.go"
        tempGoExec = f"{tempGoDir}/main"
        await executeTerminalCommand(f"mkdir -p {tempGoDir}")
        await executeTerminalCommand(f"cat <<'EOF' > {tempGoFile}\n{script}\nEOF")

        compileResult = await executeTerminalCommand(f"cd {tempGoDir} && go build -o main main.go")
        if getattr(compileResult, "exitCode", 1) != 0 or hasError(getattr(compileResult, "output", "") or ""):
            await executeTerminalCommand(f"rm -rf {tempGoDir}")
            return {"success": False, "message": f"Go 编译失败: {getattr(compileResult, 'output', '')}"}

        runResult = await executeTerminalCommand(tempGoExec)
        await executeTerminalCommand(f"rm -rf {tempGoDir}")

        if getattr(runResult, "exitCode", 1) != 0 or hasError(getattr(runResult, "output", "") or "") or "Go运行正常" not in (getattr(runResult, "output", "") or ""):
            return {"success": False, "message": f"Go 执行失败: {getattr(runResult, 'output', '')}"}
        return {"success": True, "message": "Go执行器测试成功"}
    except Exception as error:
        return {"success": False, "message": f"Go执行器测试失败: {str(error)}"}


async def ensureRustConfigured():
    rustCheckResult = await executeTerminalCommand("cd /tmp && rustc --version")

    if getattr(rustCheckResult, "exitCode", 1) == 0 and not hasError(getattr(rustCheckResult, "output", "") or ""):
        return {"success": True, "message": "Rust环境已配置"}

    if "no default is configured" in (getattr(rustCheckResult, "output", "") or ""):
        setupResult = await executeTerminalCommand('export RUSTUP_DIST_SERVER="https://mirrors.ustc.edu.cn/rust-static" && export RUSTUP_UPDATE_ROOT="https://mirrors.ustc.edu.cn/rust-static/rustup" && rustup default stable')
        if getattr(setupResult, "exitCode", 1) != 0 or hasError(getattr(setupResult, "output", "") or ""):
            return {"success": False, "message": f"运行 'rustup default stable' 失败: {getattr(setupResult, 'output', '')}"}

        rustCheckResult = await executeTerminalCommand("cd /tmp && rustc --version")
        if getattr(rustCheckResult, "exitCode", 1) == 0 and not hasError(getattr(rustCheckResult, "output", "") or ""):
            return {"success": True, "message": "Rust环境已自动配置"}

    return {"success": False, "message": f"Rust环境检查失败: {getattr(rustCheckResult, 'output', '')}"}


async def testRust():
    try:
        rustConfig = await ensureRustConfigured()
        if not rustConfig["success"]:
            return {"success": False, "message": rustConfig["message"]}

        script = 'fn main() {\n  println!("Rust运行正常");\n}'
        tempRustDir = "/tmp/test_rust_project"
        tempRustSrcDir = f"{tempRustDir}/src"
        tempRustFile = f"{tempRustSrcDir}/main.rs"
        cargoToml = '[package]\nname = "test_rust"\nversion = "0.1.0"\nedition = "2021"\n[dependencies]\n'
        await executeTerminalCommand(f"mkdir -p {tempRustSrcDir}")
        await executeTerminalCommand(f"cat <<'EOF' > {tempRustDir}/Cargo.toml\n{cargoToml}\nEOF")
        await executeTerminalCommand(f"cat <<'EOF' > {tempRustFile}\n{script}\nEOF")

        compileResult = await executeTerminalCommand(f"cd {tempRustDir} && {CARGO_MIRROR_ENV} && cargo build --release")
        if getattr(compileResult, "exitCode", 1) != 0 or hasError(getattr(compileResult, "output", "") or ""):
            await executeTerminalCommand(f"rm -rf {tempRustDir}")
            return {"success": False, "message": f"Rust 编译失败: {getattr(compileResult, 'output', '')}"}

        execPath = f"{tempRustDir}/target/release/test_rust"
        runResult = await executeTerminalCommand(execPath)
        await executeTerminalCommand(f"rm -rf {tempRustDir}")

        if getattr(runResult, "exitCode", 1) != 0 or hasError(getattr(runResult, "output", "") or "") or "Rust运行正常" not in (getattr(runResult, "output", "") or ""):
            return {"success": False, "message": f"Rust 执行失败: {getattr(runResult, 'output', '')}"}
        return {"success": True, "message": "Rust执行器测试成功"}
    except Exception as error:
        return {"success": False, "message": f"Rust执行器测试失败: {str(error)}"}


async def testC():
    try:
        gccCheckResult = await executeTerminalCommand("gcc --version")
        if getattr(gccCheckResult, "exitCode", 1) != 0 or hasError(getattr(gccCheckResult, "output", "") or ""):
            return {"success": False, "message": "GCC不可用，请确保已安装gcc"}

        script = '#include <stdio.h>\nint main() {\n  printf("C运行正常\\n");\n  return 0;\n}'
        tempCFile = "/tmp/test_c.c"
        tempCExec = "/tmp/test_c"
        await executeTerminalCommand(f"cat <<'EOF' > {tempCFile}\n{script}\nEOF")

        compileResult = await executeTerminalCommand(f"gcc -O3 -march=native -fopenmp {tempCFile} -o {tempCExec}")
        if getattr(compileResult, "exitCode", 1) != 0 or hasError(getattr(compileResult, "output", "") or ""):
            await executeTerminalCommand(f"rm -f {tempCFile} {tempCExec}")
            return {"success": False, "message": f"C 编译失败: {getattr(compileResult, 'output', '')}"}

        runResult = await executeTerminalCommand(tempCExec)
        await executeTerminalCommand(f"rm -f {tempCFile} {tempCExec}")

        if getattr(runResult, "exitCode", 1) != 0 or hasError(getattr(runResult, "output", "") or "") or "C运行正常" not in (getattr(runResult, "output", "") or ""):
            return {"success": False, "message": f"C 执行失败: {getattr(runResult, 'output', '')}"}
        return {"success": True, "message": "C执行器测试成功"}
    except Exception as error:
        return {"success": False, "message": f"C执行器测试失败: {str(error)}"}


async def testCpp():
    try:
        gppCheckResult = await executeTerminalCommand("g++ --version")
        if getattr(gppCheckResult, "exitCode", 1) != 0 or hasError(getattr(gppCheckResult, "output", "") or ""):
            return {"success": False, "message": "G++不可用，请确保已安装g++"}

        script = '#include <iostream>\nint main() {\n  std::cout << "C++运行正常" << std::endl;\n  return 0;\n}'
        tempCppFile = "/tmp/test_cpp.cpp"
        tempCppExec = "/tmp/test_cpp"
        await executeTerminalCommand(f"cat <<'EOF' > {tempCppFile}\n{script}\nEOF")

        compileResult = await executeTerminalCommand(f"g++ -O3 -march=native -fopenmp {tempCppFile} -o {tempCppExec}")
        if getattr(compileResult, "exitCode", 1) != 0 or hasError(getattr(compileResult, "output", "") or ""):
            await executeTerminalCommand(f"rm -f {tempCppFile} {tempCppExec}")
            return {"success": False, "message": f"C++ 编译失败: {getattr(compileResult, 'output', '')}"}

        runResult = await executeTerminalCommand(tempCppExec)
        await executeTerminalCommand(f"rm -f {tempCppFile} {tempCppExec}")

        if getattr(runResult, "exitCode", 1) != 0 or hasError(getattr(runResult, "output", "") or "") or "C++运行正常" not in (getattr(runResult, "output", "") or ""):
            return {"success": False, "message": f"C++ 执行失败: {getattr(runResult, 'output', '')}"}
        return {"success": True, "message": "C++执行器测试成功"}
    except Exception as error:
        return {"success": False, "message": f"C++执行器测试失败: {str(error)}"}


async def run_javascript_es5(params):
    script = params.get("script")
    if not script or script.strip() == "":
        raise Error("请提供要执行的脚本内容")
    return await executeJavaScript(script)


async def run_javascript_file(params):
    filePath = params.get("file_path")
    if not filePath or filePath.strip() == "":
        raise Error("请提供要执行的 JavaScript 文件路径")

    fileResult = await Tools.Files.read(filePath)
    if not fileResult or not getattr(fileResult, "content", None):
        raise Error(f"无法读取文件: {filePath}")

    return await executeJavaScript(fileResult.content)


async def run_javascript_node(params):
    script = params.get("script")
    if not script or script.strip() == "":
        raise Error("请提供要执行的 JavaScript 脚本内容")

    ws = await ensurePersistentNodeWorkspace()
    workspaceDir = ws["workspaceDir"]
    nodeFlags = params.get("node_flags") or ""
    tempFileName = f"temp_script_node_{int(time.time() * 1000)}.js"
    tempFilePath = f"{workspaceDir}/{tempFileName}"
    try:
        await executeTerminalCommand(f"cat <<'EOF' > {tempFilePath}\n{script}\nEOF")
        result = await executeTerminalCommand(f"cd {workspaceDir} && NODE_PATH={workspaceDir}/node_modules node {nodeFlags} {tempFileName}".strip())
        if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
            return (getattr(result, "output", "") or "").strip()
        else:
            raise Error(f"JavaScript (Node.js) 脚本执行失败:\n{getattr(result, 'output', '')}")
    finally:
        try:
            await executeTerminalCommand(f"rm -f {tempFilePath}")
        except Exception as err:
            console.error(f"删除临时文件失败: {str(err)}")


async def run_javascript_node_file(params):
    filePath = params.get("file_path")
    if not filePath or filePath.strip() == "":
        raise Error("请提供要执行的 JavaScript 文件路径")

    ws = await ensurePersistentNodeWorkspace()
    workspaceDir = ws["workspaceDir"]
    escapedPath = escapeForShell(filePath)
    fileExistsResult = await executeTerminalCommand(f"test -f '{escapedPath}'")
    if getattr(fileExistsResult, "exitCode", 1) != 0 or hasError(getattr(fileExistsResult, "output", "") or ""):
        raise Error(f"JavaScript 文件不存在或路径错误: {filePath}")

    nodeFlags = params.get("node_flags") or ""
    result = await executeTerminalCommand(f"cd {workspaceDir} && NODE_PATH={workspaceDir}/node_modules node {nodeFlags} '{escapedPath}'".strip())
    if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
        return (getattr(result, "output", "") or "").strip()
    else:
        raise Error(f"JavaScript (Node.js) 文件执行失败:\n{getattr(result, 'output', '')}")


async def run_python(params):
    script = params.get("script")
    if not script or script.strip() == "":
        raise Error("请提供要执行的 Python 脚本内容")

    venv = await ensurePersistentVenv()
    pythonBin = venv["pythonBin"]
    pythonFlags = params.get("python_flags") or ""
    scriptArgs = buildPipeSeparatedShellArgs(params.get("script_args"))
    tempFilePath = "/tmp/temp_script.py"
    escapedTempFilePath = escapeForShell(tempFilePath)
    try:
        await executeTerminalCommand(f"cat <<'EOF' > {tempFilePath}\n{script}\nEOF")
        result = await executeTerminalCommand(f"{pythonBin} {pythonFlags} '{escapedTempFilePath}' {scriptArgs}".strip())
        if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
            return (getattr(result, "output", "") or "").strip()
        else:
            raise Error(f"Python 脚本执行失败:\n{getattr(result, 'output', '')}")
    finally:
        try:
            await executeTerminalCommand(f"rm -f {tempFilePath}")
        except Exception as err:
            console.error(f"删除临时文件失败: {str(err)}")


async def run_python_file(params):
    filePath = params.get("file_path")
    if not filePath or filePath.strip() == "":
        raise Error("请提供要执行的 Python 文件路径")

    escapedPath = escapeForShell(filePath)
    fileExistsResult = await executeTerminalCommand(f"test -f '{escapedPath}'")
    if getattr(fileExistsResult, "exitCode", 1) != 0 or hasError(getattr(fileExistsResult, "output", "") or ""):
        raise Error(f"Python 文件不存在或路径错误: {filePath}")

    venv = await ensurePersistentVenv()
    pythonBin = venv["pythonBin"]
    pythonFlags = params.get("python_flags") or ""
    scriptArgs = buildPipeSeparatedShellArgs(params.get("script_args"))
    result = await executeTerminalCommand(f"{pythonBin} {pythonFlags} '{escapedPath}' {scriptArgs}".strip())
    if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
        return (getattr(result, "output", "") or "").strip()
    else:
        raise Error(f"Python 文件执行失败:\n{getattr(result, 'output', '')}")


async def run_ruby(params):
    script = params.get("script")
    if not script or script.strip() == "":
        raise Error("请提供要执行的 Ruby 脚本内容")

    rubyFlags = params.get("ruby_flags") or ""
    tempFilePath = "/tmp/temp_script.rb"
    try:
        await executeTerminalCommand(f"cat <<'EOF' > {tempFilePath}\n{script}\nEOF")
        result = await executeTerminalCommand(f"ruby {rubyFlags} {tempFilePath}")
        if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
            return (getattr(result, "output", "") or "").strip()
        else:
            raise Error(f"Ruby 脚本执行失败:\n{getattr(result, 'output', '')}")
    finally:
        try:
            await executeTerminalCommand(f"rm -f {tempFilePath}")
        except Exception as err:
            console.error(f"删除临时文件失败: {str(err)}")


async def run_ruby_file(params):
    filePath = params.get("file_path")
    if not filePath or filePath.strip() == "":
        raise Error("请提供要执行的 Ruby 文件路径")

    fileExistsResult = await executeTerminalCommand(f"test -f {filePath}")
    if getattr(fileExistsResult, "exitCode", 1) != 0 or hasError(getattr(fileExistsResult, "output", "") or ""):
        raise Error(f"Ruby 文件不存在或路径错误: {filePath}")

    rubyFlags = params.get("ruby_flags") or ""
    result = await executeTerminalCommand(f"ruby {rubyFlags} {filePath}")
    if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
        return (getattr(result, "output", "") or "").strip()
    else:
        raise Error(f"Ruby 文件执行失败:\n{getattr(result, 'output', '')}")


async def run_go(params):
    script = params.get("script")
    if not script or script.strip() == "":
        raise Error("请提供要执行的 Go 代码内容")

    buildFlags = params.get("build_flags") or ""
    tempDirPath = "/tmp/temp_go"
    tempFilePath = f"{tempDirPath}/main.go"

    try:
        await executeTerminalCommand(f"mkdir -p {tempDirPath}")
        await executeTerminalCommand(f"cat <<'EOF' > {tempFilePath}\n{script}\nEOF")

        compileResult = await executeTerminalCommand(f"cd {tempDirPath} && go build {buildFlags} -o main main.go")
        if getattr(compileResult, "exitCode", 1) != 0 or hasError(getattr(compileResult, "output", "") or ""):
            raise Error(f"Go 代码编译失败:\n{getattr(compileResult, 'output', '')}")

        result = await executeTerminalCommand(f"{tempDirPath}/main")
        if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
            return (getattr(result, "output", "") or "").strip()
        else:
            raise Error(f"Go 代码执行失败:\n{getattr(result, 'output', '')}")
    finally:
        try:
            await executeTerminalCommand(f"rm -rf {tempDirPath}")
        except Exception as err:
            console.error(f"删除临时目录失败: {str(err)}")


async def run_go_file(params):
    filePath = params.get("file_path")
    if not filePath or filePath.strip() == "":
        raise Error("请提供要执行的 Go 文件路径")

    fileExistsResult = await executeTerminalCommand(f"test -f {filePath}")
    if getattr(fileExistsResult, "exitCode", 1) != 0 or hasError(getattr(fileExistsResult, "output", "") or ""):
        raise Error(f"Go 文件不存在或路径错误: {filePath}")

    buildFlags = params.get("build_flags") or ""
    tempExecPath = "/tmp/temp_go_exec"
    try:
        compileResult = await executeTerminalCommand(f"go build {buildFlags} -o {tempExecPath} {filePath}")
        if getattr(compileResult, "exitCode", 1) != 0 or hasError(getattr(compileResult, "output", "") or ""):
            raise Error(f"Go 文件编译失败:\n{getattr(compileResult, 'output', '')}")

        result = await executeTerminalCommand(tempExecPath)
        if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
            return (getattr(result, "output", "") or "").strip()
        else:
            raise Error(f"Go 文件执行失败:\n{getattr(result, 'output', '')}")
    finally:
        try:
            await executeTerminalCommand(f"rm -f {tempExecPath}")
        except Exception as err:
            console.error(f"删除临时文件失败: {str(err)}")


async def run_rust(params):
    script = params.get("script")
    if not script or script.strip() == "":
        raise Error("请提供要执行的 Rust 代码内容")

    rustConfig = await ensureRustConfigured()
    if not rustConfig["success"]:
        raise Error(rustConfig["message"])

    cargoFlags = params.get("cargo_flags") or "--release"
    buildMode = "release" if "--release" in cargoFlags else "debug"
    tempDirPath = "/tmp/temp_rust_project"
    try:
        cargoToml = '[package]\nname = "temp_rust_script"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\n'
        await executeTerminalCommand(f"mkdir -p {tempDirPath}/src", 10000)
        await executeTerminalCommand(f"cat <<'EOF' > {tempDirPath}/Cargo.toml\n{cargoToml}\nEOF")
        await executeTerminalCommand(f"cat <<'EOF' > {tempDirPath}/src/main.rs\n{script}\nEOF")

        compileResult = await executeTerminalCommand(f"cd {tempDirPath} && {CARGO_MIRROR_ENV} && cargo build {cargoFlags}")
        if getattr(compileResult, "exitCode", 1) != 0 or hasError(getattr(compileResult, "output", "") or ""):
            raise Error(f"Rust 代码编译失败:\n{getattr(compileResult, 'output', '')}")

        execPath = f"{tempDirPath}/target/{buildMode}/temp_rust_script"
        result = await executeTerminalCommand(execPath, 30000)
        if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
            return (getattr(result, "output", "") or "").strip()
        else:
            raise Error(f"Rust 代码执行失败:\n{getattr(result, 'output', '')}")
    finally:
        try:
            await executeTerminalCommand(f"rm -rf {tempDirPath}")
        except Exception as err:
            console.error(f"删除临时目录失败: {str(err)}")


async def run_rust_file(params):
    filePath = params.get("file_path")
    if not filePath or filePath.strip() == "":
        raise Error("请提供要执行的 Rust 文件路径")
    fileExistsResult = await executeTerminalCommand(f"test -f {filePath}")
    if getattr(fileExistsResult, "exitCode", 1) != 0 or hasError(getattr(fileExistsResult, "output", "") or ""):
        raise Error(f"Rust 文件不存在或路径错误: {filePath}")

    rustConfig = await ensureRustConfigured()
    if not rustConfig["success"]:
        raise Error(rustConfig["message"])

    cargoFlags = params.get("cargo_flags") or "--release"
    buildMode = "release" if "--release" in cargoFlags else "debug"
    tempDirPath = "/tmp/temp_rust_project"
    try:
        cargoToml = '[package]\nname = "temp_rust_script"\nversion = "0.1.0"\nedition = "2021"\n\n[dependencies]\n'
        await executeTerminalCommand(f"mkdir -p {tempDirPath}/src", 10000)
        await executeTerminalCommand(f"cat <<'EOF' > {tempDirPath}/Cargo.toml\n{cargoToml}\nEOF")

        readResult = await executeTerminalCommand(f"cat {filePath}")
        if getattr(readResult, "exitCode", 1) != 0 or hasError(getattr(readResult, "output", "") or ""):
            raise Error(f"无法读取文件: {filePath}")
        fileContent = getattr(readResult, "output", "")
        await executeTerminalCommand(f"cat <<'EOF' > {tempDirPath}/src/main.rs\n{fileContent}\nEOF")

        compileResult = await executeTerminalCommand(f"cd {tempDirPath} && {CARGO_MIRROR_ENV} && cargo build {cargoFlags}")
        if getattr(compileResult, "exitCode", 1) != 0 or hasError(getattr(compileResult, "output", "") or ""):
            raise Error(f"Rust 文件编译失败:\n{getattr(compileResult, 'output', '')}")

        execPath = f"{tempDirPath}/target/{buildMode}/temp_rust_script"
        result = await executeTerminalCommand(execPath, 30000)
        if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
            return (getattr(result, "output", "") or "").strip()
        else:
            raise Error(f"Rust 项目执行失败:\n{getattr(result, 'output', '')}")
    finally:
        try:
            await executeTerminalCommand(f"rm -rf {tempDirPath}")
        except Exception as err:
            console.error(f"删除临时目录失败: {str(err)}")


async def run_c(params):
    script = params.get("script")
    if not script or script.strip() == "":
        raise Error("请提供要执行的 C 代码内容")

    compileFlags = params.get("compile_flags") or "-O3 -march=native -fopenmp"
    tempFilePath = "/tmp/temp_script.c"
    tempExecPath = "/tmp/temp_script_c_exec"
    try:
        await executeTerminalCommand(f"cat <<'EOF' > {tempFilePath}\n{script}\nEOF")

        compileResult = await executeTerminalCommand(f"gcc {compileFlags} {tempFilePath} -o {tempExecPath}")
        if getattr(compileResult, "exitCode", 1) != 0 or hasError(getattr(compileResult, "output", "") or ""):
            raise Error(f"C 代码编译失败:\n{getattr(compileResult, 'output', '')}")

        result = await executeTerminalCommand(tempExecPath)
        if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
            return (getattr(result, "output", "") or "").strip()
        else:
            raise Error(f"C 代码执行失败:\n{getattr(result, 'output', '')}")
    finally:
        try:
            await executeTerminalCommand(f"rm -f {tempFilePath} {tempExecPath}")
        except Exception as err:
            console.error(f"删除临时文件失败: {str(err)}")


async def run_c_file(params):
    filePath = params.get("file_path")
    if not filePath or filePath.strip() == "":
        raise Error("请提供要执行的 C 文件路径")

    fileExistsResult = await executeTerminalCommand(f"test -f {filePath}")
    if getattr(fileExistsResult, "exitCode", 1) != 0 or hasError(getattr(fileExistsResult, "output", "") or ""):
        raise Error(f"C 文件不存在或路径错误: {filePath}")

    compileFlags = params.get("compile_flags") or "-O3 -march=native -fopenmp"
    tempExecPath = "/tmp/temp_c_exec"
    try:
        compileResult = await executeTerminalCommand(f"gcc {compileFlags} {filePath} -o {tempExecPath}")
        if getattr(compileResult, "exitCode", 1) != 0 or hasError(getattr(compileResult, "output", "") or ""):
            raise Error(f"C 文件编译失败:\n{getattr(compileResult, 'output', '')}")

        result = await executeTerminalCommand(tempExecPath)
        if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
            return (getattr(result, "output", "") or "").strip()
        else:
            raise Error(f"C 文件执行失败:\n{getattr(result, 'output', '')}")
    finally:
        try:
            await executeTerminalCommand(f"rm -f {tempExecPath}")
        except Exception as err:
            console.error(f"删除临时文件失败: {str(err)}")


async def run_cpp(params):
    script = params.get("script")
    if not script or script.strip() == "":
        raise Error("请提供要执行的 C++ 代码内容")

    compileFlags = params.get("compile_flags") or "-O3 -march=native -fopenmp"
    tempFilePath = "/tmp/temp_script.cpp"
    tempExecPath = "/tmp/temp_script_cpp_exec"
    try:
        await executeTerminalCommand(f"cat <<'EOF' > {tempFilePath}\n{script}\nEOF")

        compileResult = await executeTerminalCommand(f"g++ {compileFlags} {tempFilePath} -o {tempExecPath}")
        if getattr(compileResult, "exitCode", 1) != 0 or hasError(getattr(compileResult, "output", "") or ""):
            raise Error(f"C++ 代码编译失败:\n{getattr(compileResult, 'output', '')}")

        result = await executeTerminalCommand(tempExecPath)
        if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
            return (getattr(result, "output", "") or "").strip()
        else:
            raise Error(f"C++ 代码执行失败:\n{getattr(result, 'output', '')}")
    finally:
        try:
            await executeTerminalCommand(f"rm -f {tempFilePath} {tempExecPath}")
        except Exception as err:
            console.error(f"删除临时文件失败: {str(err)}")


async def run_cpp_file(params):
    filePath = params.get("file_path")
    if not filePath or filePath.strip() == "":
        raise Error("请提供要执行的 C++ 文件路径")

    fileExistsResult = await executeTerminalCommand(f"test -f {filePath}")
    if getattr(fileExistsResult, "exitCode", 1) != 0 or hasError(getattr(fileExistsResult, "output", "") or ""):
        raise Error(f"C++ 文件不存在或路径错误: {filePath}")

    compileFlags = params.get("compile_flags") or "-O3 -march=native -fopenmp"
    tempExecPath = "/tmp/temp_cpp_exec"
    try:
        compileResult = await executeTerminalCommand(f"g++ {compileFlags} {filePath} -o {tempExecPath}")
        if getattr(compileResult, "exitCode", 1) != 0 or hasError(getattr(compileResult, "output", "") or ""):
            raise Error(f"C++ 文件编译失败:\n{getattr(compileResult, 'output', '')}")

        result = await executeTerminalCommand(tempExecPath)
        if getattr(result, "exitCode", 1) == 0 and not hasError(getattr(result, "output", "") or ""):
            return (getattr(result, "output", "") or "").strip()
        else:
            raise Error(f"C++ 文件执行失败:\n{getattr(result, 'output', '')}")
    finally:
        try:
            await executeTerminalCommand(f"rm -f {tempExecPath}")
        except Exception as err:
            console.error(f"删除临时文件失败: {str(err)}")


def wrap(func):
    async def wrapped(params):
        try:
            result = await func(params)
            complete({"success": True, "data": result})
        except Exception as error:
            import traceback
            complete({"success": False, "message": str(error), "error_stack": traceback.format_exc()})
    return wrapped


exports.main = wrap(main)
exports.run_javascript_es5 = wrap(run_javascript_es5)
exports.run_javascript_file = wrap(run_javascript_file)
exports.run_javascript_node = wrap(run_javascript_node)
exports.run_javascript_node_file = wrap(run_javascript_node_file)
exports.install_node_packages = wrap(install_node_packages)
exports.install_python_packages = wrap(install_python_packages)
exports.run_python = wrap(run_python)
exports.run_python_file = wrap(run_python_file)
exports.run_ruby = wrap(run_ruby)
exports.run_ruby_file = wrap(run_ruby_file)
exports.run_go = wrap(run_go)
exports.run_go_file = wrap(run_go_file)
exports.run_rust = wrap(run_rust)
exports.run_rust_file = wrap(run_rust_file)
exports.run_c = wrap(run_c)
exports.run_c_file = wrap(run_c_file)
exports.run_cpp = wrap(run_cpp)
exports.run_cpp_file = wrap(run_cpp_file)
