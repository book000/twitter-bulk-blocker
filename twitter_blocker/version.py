"""
バージョン情報管理モジュール

Semantic Versioning (SemVer) に基づくバージョン管理を提供します。
Git情報、ビルド日時、Python環境情報を含む詳細なバージョン情報を管理します。
"""

import sys
import os
import subprocess
import datetime
import platform
from typing import Dict, Optional, Any

# セマンティックバージョニング
__version__ = "0.28.1"

# ビルド情報
__build_date__ = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
__python_version__ = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_git_info() -> Dict[str, Optional[str]]:
    """
    Git情報を取得
    
    Returns:
        Dict[str, Optional[str]]: Git情報 (commit_hash, branch, tag, dirty)
    """
    git_info = {
        "commit_hash": None,
        "commit_short": None,
        "branch": None,
        "tag": None,
        "dirty": False,
        "commit_date": None,
        "author": None
    }
    
    try:
        # Git リポジトリのルートディレクトリを取得
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # コミットハッシュ (フル)
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info["commit_hash"] = result.stdout.strip()
            git_info["commit_short"] = result.stdout.strip()[:8]
        
        # ブランチ名
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info["branch"] = result.stdout.strip()
        
        # タグ情報
        result = subprocess.run(
            ["git", "describe", "--tags", "--exact-match"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info["tag"] = result.stdout.strip()
        
        # ダーティチェック (uncommitted changes)
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info["dirty"] = bool(result.stdout.strip())
        
        # コミット日時
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ci"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info["commit_date"] = result.stdout.strip()
        
        # コミット作者
        result = subprocess.run(
            ["git", "log", "-1", "--format=%an"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            git_info["author"] = result.stdout.strip()
            
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
        # Git が利用できない場合やタイムアウトの場合は None のまま
        pass
    
    return git_info


def get_system_info() -> Dict[str, str]:
    """
    システム情報を取得
    
    Returns:
        Dict[str, str]: システム情報
    """
    return {
        "platform": platform.platform(),
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "processor": platform.processor(),
        "python_implementation": platform.python_implementation(),
        "python_version": __python_version__,
        "python_compiler": platform.python_compiler(),
    }


def get_version_info(include_git: bool = True, include_system: bool = False) -> Dict[str, Any]:
    """
    詳細なバージョン情報を取得
    
    Args:
        include_git (bool): Git情報を含めるかどうか
        include_system (bool): システム情報を含めるかどうか
        
    Returns:
        Dict[str, Any]: バージョン情報
    """
    version_info = {
        "version": __version__,
        "build_date": __build_date__,
        "python_version": __python_version__,
    }
    
    if include_git:
        version_info["git"] = get_git_info()
    
    if include_system:
        version_info["system"] = get_system_info()
    
    return version_info


def get_version_string(detailed: bool = False) -> str:
    """
    バージョン文字列を取得
    
    Args:
        detailed (bool): 詳細情報を含めるかどうか
        
    Returns:
        str: バージョン文字列
    """
    if not detailed:
        return f"Twitter Bulk Blocker v{__version__}"
    
    version_info = get_version_info(include_git=True, include_system=False)
    git_info = version_info.get("git", {})
    
    # 基本バージョン情報
    version_str = f"Twitter Bulk Blocker v{__version__}"
    
    # Git情報を追加
    if git_info.get("commit_short"):
        version_str += f" ({git_info['commit_short']}"
        if git_info.get("dirty"):
            version_str += "-dirty"
        version_str += ")"
    
    # ブランチ情報
    if git_info.get("branch") and git_info["branch"] != "HEAD":
        version_str += f" [{git_info['branch']}]"
    
    # タグ情報
    if git_info.get("tag"):
        version_str += f" (tag: {git_info['tag']})"
    
    # ビルド日時
    version_str += f" - Built: {__build_date__}"
    
    # Python バージョン
    version_str += f" - Python {__python_version__}"
    
    return version_str


def print_version_info(detailed: bool = False) -> None:
    """
    バージョン情報を出力
    
    Args:
        detailed (bool): 詳細情報を含めるかどうか
    """
    print(get_version_string(detailed=detailed))
    
    if detailed:
        version_info = get_version_info(include_git=True, include_system=True)
        git_info = version_info.get("git", {})
        system_info = version_info.get("system", {})
        
        print("\n=== Git Information ===")
        if git_info.get("commit_hash"):
            print(f"Commit: {git_info['commit_hash']}")
        if git_info.get("branch"):
            print(f"Branch: {git_info['branch']}")
        if git_info.get("tag"):
            print(f"Tag: {git_info['tag']}")
        if git_info.get("commit_date"):
            print(f"Commit Date: {git_info['commit_date']}")
        if git_info.get("author"):
            print(f"Author: {git_info['author']}")
        if git_info.get("dirty"):
            print("Status: Modified (uncommitted changes)")
        else:
            print("Status: Clean")
        
        print("\n=== System Information ===")
        print(f"Platform: {system_info.get('platform', 'Unknown')}")
        print(f"Python: {system_info.get('python_implementation', 'Unknown')} {system_info.get('python_version', 'Unknown')}")
        print(f"Compiler: {system_info.get('python_compiler', 'Unknown')}")


if __name__ == "__main__":
    # テスト実行
    print_version_info(detailed=True)