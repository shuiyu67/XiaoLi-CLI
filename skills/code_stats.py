"""
代码统计 Skill - 统计项目代码行数、文件数等
"""
import os
from skills.base import Skill, SkillResult, SkillParameter, ParameterType


class CodeStatsSkill(Skill):
    """代码统计技能 - 统计目录中的代码行数、文件数、注释率等"""

    def __init__(self):
        super().__init__()
        self.name = "code_stats"
        self.description = "统计项目代码量：文件数、代码行、注释行、空行、注释率"
        self.version = "1.0.0"
        self.author = "mimo"
        self.tags = ["代码", "统计", "stats", "lines"]

    @property
    def parameters(self):
        return [
            SkillParameter(
                name="directory",
                param_type=ParameterType.STRING,
                description="要统计的目录路径",
                required=True
            ),
            SkillParameter(
                name="file_pattern",
                param_type=ParameterType.STRING,
                description="文件匹配模式，如 *.py",
                required=False,
                default="*.py"
            ),
        ]

    def execute(self, **kwargs) -> SkillResult:
        directory = kwargs.get("directory", ".")
        file_pattern = kwargs.get("file_pattern", "*.py")

        if not os.path.isdir(directory):
            return SkillResult(success=False, error=f"目录不存在: {directory}")

        # 确定文件扩展名
        if file_pattern.startswith("*."):
            ext = file_pattern[1:]
            file_filter = lambda f: f.endswith(ext)
        else:
            file_filter = lambda f: True

        total_files = 0
        total_lines = 0
        total_code = 0
        total_blank = 0
        total_comment = 0
        file_details = []

        skip_dirs = {'.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env'}

        for root, dirs, files in os.walk(directory):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith('.')]

            for filename in sorted(files):
                if not file_filter(filename):
                    continue

                filepath = os.path.join(root, filename)
                rel_path = os.path.relpath(filepath, directory)
                total_files += 1

                file_lines = 0
                file_code = 0
                file_blank = 0
                file_comment = 0

                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        for line in f:
                            total_lines += 1
                            file_lines += 1
                            stripped = line.strip()
                            if not stripped:
                                total_blank += 1
                                file_blank += 1
                            elif stripped.startswith('#'):
                                total_comment += 1
                                file_comment += 1
                            else:
                                total_code += 1
                                file_code += 1
                except (UnicodeDecodeError, PermissionError):
                    continue

                file_details.append({
                    "file": rel_path,
                    "lines": file_lines,
                    "code": file_code,
                    "comment": file_comment,
                    "blank": file_blank,
                })

        # 按代码行数排序
        file_details.sort(key=lambda x: x["code"], reverse=True)

        # 构建报告
        comment_rate = (total_comment / max(total_code, 1)) * 100

        report_lines = [
            f"📊 代码统计 ({directory})",
            f"{'─' * 40}",
            f"  文件数: {total_files}",
            f"  总行数: {total_lines}",
            f"  代码行: {total_code}",
            f"  注释行: {total_comment}",
            f"  空行:   {total_blank}",
            f"  注释率: {comment_rate:.1f}%",
        ]

        if file_details:
            report_lines.append(f"\n📄 文件明细 (按代码行数排序):")
            for fd in file_details[:20]:
                report_lines.append(
                    f"  {fd['file']:40} {fd['code']:5} 行代码"
                )
            if len(file_details) > 20:
                report_lines.append(f"  ... 还有 {len(file_details) - 20} 个文件")

        return SkillResult(
            success=True,
            message='\n'.join(report_lines),
            data={
                "total_files": total_files,
                "total_lines": total_lines,
                "total_code": total_code,
                "total_comment": total_comment,
                "total_blank": total_blank,
                "comment_rate": comment_rate,
                "files": file_details
            }
        )
