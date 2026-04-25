---
name: file-manager
description: File and directory management tool for creating, reading, writing, deleting, moving, copying, and searching files. Use this skill when the user needs to perform file operations, list directories, search by pattern or content, or get file metadata like size and modification time.
license: MIT
version: 1.0.0
author: Xiaoli Team (based on openakita/openakita)
tools:
  - read_file
  - write_file
  - bash
---

# File Manager Skill

A comprehensive file and directory management toolset for AI agents.

## Capabilities

- **Create**: Files and directories
- **Read**: File contents with encoding support
- **Write**: Create or overwrite files
- **Append**: Add content to existing files
- **Delete**: Remove files or directories
- **Move**: Move or rename files and directories
- **Copy**: Duplicate files or directories
- **Search**: Find files by pattern or content
- **List**: Browse directory contents
- **Info**: Get file metadata (size, dates, permissions)

## Script Usage

This skill includes a Python script for structured JSON output:

```bash
python scripts/file_ops.py list <path> [--recursive] [--pattern "*.py"]
python scripts/file_ops.py read <file_path> [--encoding utf-8] [--lines N]
python scripts/file_ops.py write <file_path> --content "内容" [--append]
python scripts/file_ops.py copy <source> <destination>
python scripts/file_ops.py move <source> <destination>
python scripts/file_ops.py delete <path> [--recursive]
python scripts/file_ops.py search <directory> --pattern "*.py" [--content "搜索词"]
python scripts/file_ops.py info <path>
```

## Direct Shell Commands

### List Directory Contents

When asked to show files in a directory:

```bash
# List current directory
ls -la

# List specific directory
ls -la /path/to/directory

# Recursive listing (Unix)
find /path -type f -name "*.py"

# Windows
dir /s /b C:\path\*.py
```

### Read File

When asked to read a file:

```bash
# Read entire file
cat filename.txt

# Read with line numbers
cat -n filename.txt

# Read first N lines
head -n 50 filename.txt

# Read last N lines
tail -n 50 filename.txt
```

### Write File

When asked to create or write a file:

```bash
# Write content to file (overwrites)
echo "content" > filename.txt

# Write multiple lines
cat > filename.txt << 'EOF'
Line 1
Line 2
Line 3
EOF

# Windows PowerShell
Set-Content -Path filename.txt -Value "content"
```

### Append to File

When asked to add content to an existing file:

```bash
# Append to file
echo "new line" >> filename.txt

# Append multiple lines
cat >> filename.txt << 'EOF'
Additional line 1
Additional line 2
EOF
```

### Create Directory

When asked to create a folder:

```bash
# Create single directory
mkdir directory_name

# Create nested directories
mkdir -p path/to/nested/directories

# Windows
mkdir path\to\nested\directories
```

### Delete File or Directory

When asked to delete:

```bash
# Delete a file
rm filename.txt

# Delete empty directory
rmdir directory_name

# Delete directory and contents
rm -rf directory_name

# Windows
del filename.txt
rmdir /s /q directory_name
```

⚠️ **Warning**: Deletion is permanent. Always confirm before deleting.

### Copy File or Directory

When asked to copy:

```bash
# Copy file
cp source.txt destination.txt

# Copy directory recursively
cp -r source_dir/ destination_dir/

# Windows
copy source.txt destination.txt
xcopy /E /I source_dir destination_dir
```

### Move or Rename

When asked to move or rename:

```bash
# Move file
mv source.txt /new/location/source.txt

# Rename file
mv oldname.txt newname.txt

# Windows
move source.txt destination.txt
ren oldname.txt newname.txt
```

### Search Files

When asked to find files:

```bash
# Find by name pattern
find /path -name "*.py"
find /path -iname "*.PY"  # case-insensitive

# Find by content (grep)
grep -r "search_term" /path
grep -rl "search_term" /path  # filenames only

# Windows PowerShell
Get-ChildItem -Path C:\path -Filter *.py -Recurse
Select-String -Path C:\path\*.py -Pattern "search_term"
```

### Get File Information

When asked about file details:

```bash
# File metadata (Unix)
ls -la filename.txt
stat filename.txt

# File size only
du -h filename.txt

# Windows
dir filename.txt
```

## JSON Output Format

All operations should return structured results:

```json
{
  "success": true,
  "operation": "list",
  "path": "/home/user/project",
  "data": {
    "files": ["main.py", "config.json", "README.md"],
    "directories": ["src", "tests", "docs"],
    "total_count": 6
  },
  "timestamp": "2026-03-21T10:30:00Z"
}
```

## Safety Rules

1. **Always validate paths**: Reject paths containing `..` that escape the working directory
2. **Confirm destructive operations**: Ask before delete, move, or overwrite
3. **Handle encoding**: Default to UTF-8, detect and handle other encodings
4. **Large file warning**: Alert for files > 10MB
5. **Binary file detection**: Cannot read binary files as text

## Protected Directories

Never allow operations on:
- System directories: `/etc`, `/root`, `C:\Windows`, `C:\Program Files`
- Hidden files starting with `.` (unless explicitly requested)
- Files with sensitive names: `.env`, `credentials`, `secrets`

## Error Handling

| Error | Response |
|-------|----------|
| File not found | Suggest similar filenames or check path |
| Permission denied | Explain required permissions |
| Disk full | Warn user and suggest cleanup |
| Invalid path | Show correct path format |

## Examples

### Example 1: List Project Files

User: "Show me the project structure"

```bash
find . -type f -name "*.py" | head -20
tree -L 2 -I '__pycache__|*.pyc'
```

### Example 2: Search and Replace

User: "Replace 'old_func' with 'new_func' in all Python files"

```bash
# Find and preview
grep -r "old_func" --include="*.py" .

# Replace (with backup)
find . -name "*.py" -exec sed -i.bak 's/old_func/new_func/g' {} \;
```

### Example 3: Safe Delete

User: "Delete the temp folder"

Before executing:
1. Check if path exists
2. List contents to show what will be deleted
3. Ask for confirmation
4. Execute if confirmed

## Cross-Platform Notes

| Operation | Unix | Windows |
|-----------|------|---------|
| List | `ls -la` | `dir` |
| Copy | `cp` | `copy` |
| Move | `mv` | `move` |
| Delete | `rm -rf` | `rmdir /s /q` |
| Find | `find` | `Get-ChildItem` |
| Grep | `grep` | `Select-String` |

Always detect the OS and use appropriate commands.