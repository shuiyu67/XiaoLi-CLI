#!/usr/bin/env python3
"""
File Operations Script for file-manager skill
Provides file system operations as JSON output
"""

import os
import sys
import json
import shutil
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List


def json_response(success: bool, operation: str, data: Any = None, error: str = None) -> str:
    """Generate JSON response"""
    return json.dumps({
        "success": success,
        "operation": operation,
        "data": data,
        "error": error,
        "timestamp": datetime.now().isoformat()
    }, ensure_ascii=False, indent=2)


def list_directory(path: str, recursive: bool = False, pattern: str = None) -> str:
    """List directory contents"""
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return json_response(False, "list", error=f"Path not found: {path}")
        
        if not os.path.isdir(path):
            return json_response(False, "list", error=f"Not a directory: {path}")
        
        files = []
        directories = []
        
        if recursive:
            for root, dirs, filenames in os.walk(path):
                for d in dirs:
                    rel_path = os.path.relpath(os.path.join(root, d), path)
                    if pattern is None or Path(d).match(pattern):
                        directories.append(rel_path)
                for f in filenames:
                    rel_path = os.path.relpath(os.path.join(root, f), path)
                    if pattern is None or Path(f).match(pattern):
                        files.append(rel_path)
        else:
            for item in os.listdir(path):
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    if pattern is None or Path(item).match(pattern):
                        directories.append(item)
                else:
                    if pattern is None or Path(item).match(pattern):
                        files.append(item)
        
        return json_response(True, "list", {
            "path": path,
            "files": sorted(files),
            "directories": sorted(directories),
            "file_count": len(files),
            "dir_count": len(directories),
            "total_count": len(files) + len(directories)
        })
    except Exception as e:
        return json_response(False, "list", error=str(e))


def read_file(file_path: str, encoding: str = "utf-8", lines: int = None) -> str:
    """Read file content"""
    try:
        file_path = os.path.abspath(file_path)
        if not os.path.exists(file_path):
            return json_response(False, "read", error=f"File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            return json_response(False, "read", error=f"Not a file: {file_path}")
        
        file_size = os.path.getsize(file_path)
        
        with open(file_path, 'r', encoding=encoding) as f:
            if lines:
                content_lines = []
                for i, line in enumerate(f):
                    if i >= lines:
                        break
                    content_lines.append(line.rstrip('\n\r'))
                content = '\n'.join(content_lines)
                total_lines = sum(1 for _ in open(file_path, 'r', encoding=encoding))
            else:
                content = f.read()
                total_lines = content.count('\n') + 1
        
        return json_response(True, "read", {
            "path": file_path,
            "content": content,
            "size": file_size,
            "lines": total_lines,
            "displayed_lines": lines if lines else total_lines
        })
    except UnicodeDecodeError:
        return json_response(False, "read", error="Cannot decode file (binary or wrong encoding)")
    except Exception as e:
        return json_response(False, "read", error=str(e))


def write_file(file_path: str, content: str, append: bool = False) -> str:
    """Write or append to file"""
    try:
        file_path = os.path.abspath(file_path)
        
        # Create parent directory if needed
        parent = os.path.dirname(file_path)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        
        mode = 'a' if append else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(content)
        
        return json_response(True, "write" if not append else "append", {
            "path": file_path,
            "size": len(content.encode('utf-8')),
            "appended": append
        })
    except Exception as e:
        return json_response(False, "write", error=str(e))


def copy_path(source: str, destination: str) -> str:
    """Copy file or directory"""
    try:
        source = os.path.abspath(source)
        destination = os.path.abspath(destination)
        
        if not os.path.exists(source):
            return json_response(False, "copy", error=f"Source not found: {source}")
        
        # Create parent directory for destination
        parent = os.path.dirname(destination)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        
        if os.path.isfile(source):
            shutil.copy2(source, destination)
        else:
            shutil.copytree(source, destination, dirs_exist_ok=True)
        
        return json_response(True, "copy", {
            "source": source,
            "destination": destination,
            "type": "file" if os.path.isfile(source) else "directory"
        })
    except Exception as e:
        return json_response(False, "copy", error=str(e))


def move_path(source: str, destination: str) -> str:
    """Move or rename file or directory"""
    try:
        source = os.path.abspath(source)
        destination = os.path.abspath(destination)
        
        if not os.path.exists(source):
            return json_response(False, "move", error=f"Source not found: {source}")
        
        # Create parent directory for destination
        parent = os.path.dirname(destination)
        if parent and not os.path.exists(parent):
            os.makedirs(parent, exist_ok=True)
        
        shutil.move(source, destination)
        
        return json_response(True, "move", {
            "source": source,
            "destination": destination
        })
    except Exception as e:
        return json_response(False, "move", error=str(e))


def delete_path(path: str, recursive: bool = False) -> str:
    """Delete file or directory"""
    try:
        path = os.path.abspath(path)
        
        if not os.path.exists(path):
            return json_response(False, "delete", error=f"Path not found: {path}")
        
        if os.path.isfile(path):
            os.remove(path)
            item_type = "file"
        elif os.path.isdir(path):
            if recursive:
                shutil.rmtree(path)
            else:
                os.rmdir(path)  # Only works for empty directories
            item_type = "directory"
        
        return json_response(True, "delete", {
            "path": path,
            "type": item_type
        })
    except OSError as e:
        if "not empty" in str(e).lower():
            return json_response(False, "delete", error="Directory not empty. Use --recursive to delete.")
        return json_response(False, "delete", error=str(e))
    except Exception as e:
        return json_response(False, "delete", error=str(e))


def search_files(directory: str, pattern: str = None, content: str = None) -> str:
    """Search files by name pattern or content"""
    try:
        directory = os.path.abspath(directory)
        if not os.path.exists(directory):
            return json_response(False, "search", error=f"Directory not found: {directory}")
        
        results = []
        
        for root, dirs, files in os.walk(directory):
            for filename in files:
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, directory)
                
                # Pattern match
                if pattern and not Path(filename).match(pattern):
                    continue
                
                # Content search
                if content:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            file_content = f.read()
                            if content not in file_content:
                                continue
                            # Find matching lines
                            matches = []
                            for i, line in enumerate(file_content.split('\n'), 1):
                                if content in line:
                                    matches.append({"line": i, "text": line.strip()[:100]})
                            if matches:
                                results.append({
                                    "path": rel_path,
                                    "matches": matches[:5]  # Limit matches per file
                                })
                    except (UnicodeDecodeError, IOError):
                        continue
                else:
                    results.append({"path": rel_path})
        
        return json_response(True, "search", {
            "directory": directory,
            "pattern": pattern,
            "content_search": content,
            "results": results[:100],  # Limit results
            "total": len(results)
        })
    except Exception as e:
        return json_response(False, "search", error=str(e))


def get_info(path: str) -> str:
    """Get file/directory information"""
    try:
        path = os.path.abspath(path)
        if not os.path.exists(path):
            return json_response(False, "info", error=f"Path not found: {path}")
        
        stat_info = os.stat(path)
        
        info = {
            "path": path,
            "name": os.path.basename(path),
            "type": "directory" if os.path.isdir(path) else "file",
            "size": stat_info.st_size,
            "created": datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat_info.st_atime).isoformat(),
            "permissions": oct(stat_info.st_mode)[-3:]
        }
        
        if os.path.isfile(path):
            info["extension"] = os.path.splitext(path)[1]
            # Try to detect if text file
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    f.read(1024)
                info["encoding"] = "utf-8"
            except UnicodeDecodeError:
                info["encoding"] = "binary"
        
        return json_response(True, "info", info)
    except Exception as e:
        return json_response(False, "info", error=str(e))


def modify_line(file_path: str, line_number: int, new_content: str) -> str:
    """Modify a specific line in a file"""
    try:
        file_path = os.path.abspath(file_path)
        
        if not os.path.exists(file_path):
            return json_response(False, "modify_line", error=f"File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            return json_response(False, "modify_line", error=f"Not a file: {file_path}")
        
        if line_number < 1:
            return json_response(False, "modify_line", error="Line number must be >= 1")
        
        # Read all lines
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        if line_number > total_lines:
            return json_response(False, "modify_line", 
                error=f"File has only {total_lines} lines, cannot modify line {line_number}")
        
        # Get old content for reporting
        old_content = lines[line_number - 1].rstrip('\n\r')
        
        # Modify the line (preserve newline if existed)
        has_newline = lines[line_number - 1].endswith('\n')
        lines[line_number - 1] = new_content + ('\n' if has_newline else '')
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return json_response(True, "modify_line", {
            "path": file_path,
            "line_number": line_number,
            "old_content": old_content,
            "new_content": new_content,
            "total_lines": total_lines
        })
    except UnicodeDecodeError:
        return json_response(False, "modify_line", error="Cannot modify binary file")
    except Exception as e:
        return json_response(False, "modify_line", error=str(e))


def insert_line(file_path: str, line_number: int, content: str) -> str:
    """Insert a new line at specified position"""
    try:
        file_path = os.path.abspath(file_path)
        
        if not os.path.exists(file_path):
            return json_response(False, "insert_line", error=f"File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            return json_response(False, "insert_line", error=f"Not a file: {file_path}")
        
        if line_number < 1:
            return json_response(False, "insert_line", error="Line number must be >= 1")
        
        # Read all lines
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        # Insert at position (can be after last line)
        insert_pos = min(line_number - 1, total_lines)
        lines.insert(insert_pos, content + '\n')
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return json_response(True, "insert_line", {
            "path": file_path,
            "line_number": line_number,
            "inserted_content": content,
            "total_lines": len(lines)
        })
    except Exception as e:
        return json_response(False, "insert_line", error=str(e))


def delete_line(file_path: str, line_number: int) -> str:
    """Delete a specific line from a file"""
    try:
        file_path = os.path.abspath(file_path)
        
        if not os.path.exists(file_path):
            return json_response(False, "delete_line", error=f"File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            return json_response(False, "delete_line", error=f"Not a file: {file_path}")
        
        if line_number < 1:
            return json_response(False, "delete_line", error="Line number must be >= 1")
        
        # Read all lines
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        
        if line_number > total_lines:
            return json_response(False, "delete_line", 
                error=f"File has only {total_lines} lines, cannot delete line {line_number}")
        
        # Get deleted content
        deleted_content = lines[line_number - 1].rstrip('\n\r')
        
        # Remove the line
        del lines[line_number - 1]
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return json_response(True, "delete_line", {
            "path": file_path,
            "line_number": line_number,
            "deleted_content": deleted_content,
            "total_lines": len(lines)
        })
    except Exception as e:
        return json_response(False, "delete_line", error=str(e))


def modify_lines(file_path: str, modifications: Dict[int, str]) -> str:
    """
    Modify multiple lines at once
    
    Args:
        file_path: Path to the file
        modifications: Dict mapping line numbers (1-based) to new content
                      Example: {2: "new line 2", 5: "new line 5"}
    """
    try:
        file_path = os.path.abspath(file_path)
        
        if not os.path.exists(file_path):
            return json_response(False, "modify_lines", error=f"File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            return json_response(False, "modify_lines", error=f"Not a file: {file_path}")
        
        # Read all lines
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        results = []
        
        # Sort modifications by line number (descending to avoid index shift issues)
        for line_number in sorted(modifications.keys()):
            if line_number < 1:
                results.append({"line": line_number, "success": False, "error": "Line number must be >= 1"})
                continue
            
            if line_number > total_lines:
                results.append({"line": line_number, "success": False, 
                    "error": f"File has only {total_lines} lines"})
                continue
            
            # Get old content
            old_content = lines[line_number - 1].rstrip('\n\r')
            new_content = modifications[line_number]
            
            # Modify the line
            has_newline = lines[line_number - 1].endswith('\n')
            lines[line_number - 1] = new_content + ('\n' if has_newline else '')
            
            results.append({
                "line": line_number,
                "success": True,
                "old_content": old_content,
                "new_content": new_content
            })
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return json_response(True, "modify_lines", {
            "path": file_path,
            "total_lines": total_lines,
            "modifications_count": len(modifications),
            "results": results
        })
    except Exception as e:
        return json_response(False, "modify_lines", error=str(e))


def replace_text(file_path: str, old_text: str, new_text: str, start_line: int = None, end_line: int = None) -> str:
    """
    Replace all occurrences of text in a file (optionally within a line range)
    
    Args:
        file_path: Path to the file
        old_text: Text to find and replace
        new_text: Replacement text
        start_line: Optional start line (1-based, inclusive)
        end_line: Optional end line (1-based, inclusive)
    """
    try:
        file_path = os.path.abspath(file_path)
        
        if not os.path.exists(file_path):
            return json_response(False, "replace_text", error=f"File not found: {file_path}")
        
        if not os.path.isfile(file_path):
            return json_response(False, "replace_text", error=f"Not a file: {file_path}")
        
        # Read all lines
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        total_lines = len(lines)
        replacements = []
        
        # Determine range
        start = max(0, (start_line or 1) - 1)
        end = min(total_lines, end_line or total_lines)
        
        for i in range(start, end):
            line = lines[i]
            if old_text in line:
                count = line.count(old_text)
                lines[i] = line.replace(old_text, new_text)
                replacements.append({
                    "line": i + 1,
                    "count": count,
                    "old_line": line.rstrip('\n\r'),
                    "new_line": lines[i].rstrip('\n\r')
                })
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        return json_response(True, "replace_text", {
            "path": file_path,
            "old_text": old_text,
            "new_text": new_text,
            "line_range": [start + 1, end] if start_line or end_line else None,
            "total_replacements": sum(r["count"] for r in replacements),
            "lines_modified": len(replacements),
            "details": replacements
        })
    except Exception as e:
        return json_response(False, "replace_text", error=str(e))


def main():
    parser = argparse.ArgumentParser(description="File operations for file-manager skill")
    subparsers = parser.add_subparsers(dest="operation", help="Operation to perform")
    
    # List
    list_parser = subparsers.add_parser("list", help="List directory contents")
    list_parser.add_argument("path", help="Directory path")
    list_parser.add_argument("-r", "--recursive", action="store_true", help="Recursive listing")
    list_parser.add_argument("-p", "--pattern", help="File pattern (e.g., *.py)")
    
    # Read
    read_parser = subparsers.add_parser("read", help="Read file content")
    read_parser.add_argument("path", help="File path")
    read_parser.add_argument("-e", "--encoding", default="utf-8", help="File encoding")
    read_parser.add_argument("-n", "--lines", type=int, help="Number of lines to read")
    
    # Write
    write_parser = subparsers.add_parser("write", help="Write to file")
    write_parser.add_argument("path", help="File path")
    write_parser.add_argument("-c", "--content", required=True, help="Content to write")
    write_parser.add_argument("-a", "--append", action="store_true", help="Append to file")
    
    # Copy
    copy_parser = subparsers.add_parser("copy", help="Copy file or directory")
    copy_parser.add_argument("source", help="Source path")
    copy_parser.add_argument("destination", help="Destination path")
    
    # Move
    move_parser = subparsers.add_parser("move", help="Move file or directory")
    move_parser.add_argument("source", help="Source path")
    move_parser.add_argument("destination", help="Destination path")
    
    # Delete
    delete_parser = subparsers.add_parser("delete", help="Delete file or directory")
    delete_parser.add_argument("path", help="Path to delete")
    delete_parser.add_argument("-r", "--recursive", action="store_true", help="Recursive delete")
    
    # Search
    search_parser = subparsers.add_parser("search", help="Search files")
    search_parser.add_argument("directory", help="Directory to search")
    search_parser.add_argument("-p", "--pattern", help="File pattern")
    search_parser.add_argument("-c", "--content", help="Content to search for")
    
    # Info
    info_parser = subparsers.add_parser("info", help="Get file info")
    info_parser.add_argument("path", help="File or directory path")
    
    # Modify line
    modify_parser = subparsers.add_parser("modify-line", help="Modify a specific line")
    modify_parser.add_argument("path", help="File path")
    modify_parser.add_argument("line", type=int, help="Line number (1-based)")
    modify_parser.add_argument("content", help="New line content")
    
    # Insert line
    insert_parser = subparsers.add_parser("insert-line", help="Insert a new line")
    insert_parser.add_argument("path", help="File path")
    insert_parser.add_argument("line", type=int, help="Line number to insert at (1-based)")
    insert_parser.add_argument("content", help="Line content to insert")
    
    # Delete line
    del_line_parser = subparsers.add_parser("delete-line", help="Delete a specific line")
    del_line_parser.add_argument("path", help="File path")
    del_line_parser.add_argument("line", type=int, help="Line number to delete (1-based)")
    
    # Modify multiple lines (JSON format)
    multi_parser = subparsers.add_parser("modify-lines", help="Modify multiple lines at once")
    multi_parser.add_argument("path", help="File path")
    multi_parser.add_argument("-m", "--modifications", required=True, 
        help='JSON dict of line numbers to content, e.g. \'{"2": "new line 2", "5": "new line 5"}\'')
    
    # Replace text
    replace_parser = subparsers.add_parser("replace", help="Replace text in file")
    replace_parser.add_argument("path", help="File path")
    replace_parser.add_argument("old", help="Text to find and replace")
    replace_parser.add_argument("new", help="Replacement text")
    replace_parser.add_argument("--start", type=int, help="Start line (optional)")
    replace_parser.add_argument("--end", type=int, help="End line (optional)")
    
    args = parser.parse_args()
    
    if args.operation == "list":
        print(list_directory(args.path, args.recursive, args.pattern))
    elif args.operation == "read":
        print(read_file(args.path, args.encoding, args.lines))
    elif args.operation == "write":
        print(write_file(args.path, args.content, args.append))
    elif args.operation == "copy":
        print(copy_path(args.source, args.destination))
    elif args.operation == "move":
        print(move_path(args.source, args.destination))
    elif args.operation == "delete":
        print(delete_path(args.path, args.recursive))
    elif args.operation == "search":
        print(search_files(args.directory, args.pattern, args.content))
    elif args.operation == "info":
        print(get_info(args.path))
    elif args.operation == "modify-line":
        print(modify_line(args.path, args.line, args.content))
    elif args.operation == "insert-line":
        print(insert_line(args.path, args.line, args.content))
    elif args.operation == "delete-line":
        print(delete_line(args.path, args.line))
    elif args.operation == "modify-lines":
        mods = json.loads(args.modifications)
        mods_int = {int(k): v for k, v in mods.items()}
        print(modify_lines(args.path, mods_int))
    elif args.operation == "replace":
        print(replace_text(args.path, args.old, args.new, args.start, args.end))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
