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
import json
from pathlib import Path
from typing import Dict, Optional, Any

# セマンティックバージョニング
__version__ = "0.28.1"

# ビルド情報
__build_date__ = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
__python_version__ = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_docker_info() -> Dict[str, Optional[str]]:
    """
    Docker環境でのバージョン情報を取得
    
    Returns:
        Dict[str, Optional[str]]: Docker環境のバージョン情報
    """
    return {
        "version": os.getenv("DOCKER_VERSION"),
        "build_date": os.getenv("DOCKER_BUILD_DATE"),
        "commit_sha": os.getenv("DOCKER_COMMIT_SHA"),
        "commit_short": os.getenv("DOCKER_COMMIT_SHORT"),
    }


def get_github_actions_info() -> Dict[str, Optional[str]]:
    """
    GitHub Actions環境でのバージョン情報を取得
    
    Returns:
        Dict[str, Optional[str]]: GitHub Actions環境のバージョン情報
    """
    return {
        "version": os.getenv("GITHUB_RELEASE_VERSION"),
        "ref": os.getenv("GITHUB_REF"),
        "sha": os.getenv("GITHUB_SHA"),
        "repository": os.getenv("GITHUB_REPOSITORY"),
        "run_id": os.getenv("GITHUB_RUN_ID"),
        "run_number": os.getenv("GITHUB_RUN_NUMBER"),
    }


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


def get_package_json_version() -> Optional[str]:
    """
    package.jsonからバージョンを取得（GitHub Actionsで更新される）
    
    Returns:
        Optional[str]: package.jsonのバージョン
    """
    try:
        # プロジェクトルートのpackage.jsonを確認
        repo_root = Path(__file__).parent.parent
        package_json_path = repo_root / "package.json"
        
        if package_json_path.exists():
            with open(package_json_path, 'r', encoding='utf-8') as f:
                package_data = json.load(f)
                return package_data.get("version")
    except (json.JSONDecodeError, IOError, KeyError):
        pass
    
    return None


def get_effective_version() -> str:
    """
    実効バージョンを取得（優先順位: Docker > GitHub Actions > package.json > Git > Static）
    
    Returns:
        str: 実効バージョン
    """
    # Docker環境チェック
    docker_info = get_docker_info()
    if docker_info.get("version") and docker_info["version"] != "unknown":
        return docker_info["version"]
    
    # GitHub Actions環境チェック
    github_info = get_github_actions_info()
    if github_info.get("version"):
        return github_info["version"]
    
    # package.jsonからのバージョン取得（GitHub Actionsで更新される）
    package_version = get_package_json_version()
    if package_version and package_version != __version__:
        # package.jsonのバージョンが静的バージョンと異なる場合（更新済み）
        return package_version
    
    # Gitタグチェック
    git_info = get_git_info()
    if git_info.get("tag"):
        # タグがある場合はタグを使用（v プレフィックスを除去）
        tag = git_info["tag"]
        if tag.startswith("v"):
            return tag[1:]
        return tag
    
    # フォールバック: 静的バージョン + Git情報
    if git_info.get("commit_short"):
        version = f"{__version__}-{git_info['commit_short']}"
        if git_info.get("dirty"):
            version += "-dirty"
        return version
    
    return __version__


def get_version_info(include_git: bool = True, include_system: bool = False, include_docker: bool = True, include_github: bool = True, include_package: bool = True) -> Dict[str, Any]:
    """
    詳細なバージョン情報を取得
    
    Args:
        include_git (bool): Git情報を含めるかどうか
        include_system (bool): システム情報を含めるかどうか
        include_docker (bool): Docker情報を含めるかどうか
        include_github (bool): GitHub Actions情報を含めるかどうか
        include_package (bool): package.json情報を含めるかどうか
        
    Returns:
        Dict[str, Any]: バージョン情報
    """
    version_info = {
        "version": __version__,
        "effective_version": get_effective_version(),
        "build_date": __build_date__,
        "python_version": __python_version__,
    }
    
    if include_package:
        package_version = get_package_json_version()
        if package_version:
            version_info["package_json"] = {
                "version": package_version,
                "updated_by_ci": package_version != __version__
            }
    
    if include_docker:
        docker_info = get_docker_info()
        if any(v for v in docker_info.values() if v and v != "unknown"):
            version_info["docker"] = docker_info
    
    if include_github:
        github_info = get_github_actions_info()
        if any(github_info.values()):
            version_info["github_actions"] = github_info
    
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
    effective_version = get_effective_version()
    
    if not detailed:
        return f"Twitter Bulk Blocker v{effective_version}"
    
    version_info = get_version_info(include_git=True, include_system=False, include_docker=True, include_github=True, include_package=True)
    git_info = version_info.get("git", {})
    docker_info = version_info.get("docker", {})
    github_info = version_info.get("github_actions", {})
    package_info = version_info.get("package_json", {})
    
    # 基本バージョン情報
    version_str = f"Twitter Bulk Blocker v{effective_version}"
    
    # バージョンソースの表示
    if docker_info:
        version_str += " [Docker]"
        if docker_info.get("commit_short"):
            version_str += f" ({docker_info['commit_short']})"
    elif github_info:
        version_str += " [GitHub Actions]"
        if github_info.get("sha"):
            version_str += f" ({github_info['sha'][:8]})"
    elif package_info and package_info.get("updated_by_ci"):
        version_str += " [package.json/CI]"
    elif git_info.get("commit_short"):
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
    build_date = docker_info.get("build_date") or __build_date__
    version_str += f" - Built: {build_date}"
    
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
        version_info = get_version_info(include_git=True, include_system=True, include_docker=True, include_github=True, include_package=True)
        git_info = version_info.get("git", {})
        docker_info = version_info.get("docker", {})
        github_info = version_info.get("github_actions", {})
        package_info = version_info.get("package_json", {})
        system_info = version_info.get("system", {})
        
        # package.json情報
        if package_info:
            print("\n=== Package.json Information ===")
            print(f"Version: {package_info.get('version', 'Unknown')}")
            if package_info.get('updated_by_ci'):
                print("Status: Updated by CI/CD (GitHub Actions)")
            else:
                print("Status: Matches static version")
        
        # Docker情報
        if docker_info:
            print("\n=== Docker Information ===")
            if docker_info.get("version"):
                print(f"Version: {docker_info['version']}")
            if docker_info.get("build_date"):
                print(f"Build Date: {docker_info['build_date']}")
            if docker_info.get("commit_sha"):
                print(f"Commit SHA: {docker_info['commit_sha']}")
            if docker_info.get("commit_short"):
                print(f"Commit Short: {docker_info['commit_short']}")
        
        # GitHub Actions情報
        if github_info:
            print("\n=== GitHub Actions Information ===")
            if github_info.get("version"):
                print(f"Release Version: {github_info['version']}")
            if github_info.get("ref"):
                print(f"Ref: {github_info['ref']}")
            if github_info.get("sha"):
                print(f"SHA: {github_info['sha']}")
            if github_info.get("repository"):
                print(f"Repository: {github_info['repository']}")
            if github_info.get("run_id"):
                print(f"Run ID: {github_info['run_id']}")
            if github_info.get("run_number"):
                print(f"Run Number: {github_info['run_number']}")
        
        # Git情報
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
        
        # システム情報
        print("\n=== System Information ===")
        print(f"Platform: {system_info.get('platform', 'Unknown')}")
        print(f"Python: {system_info.get('python_implementation', 'Unknown')} {system_info.get('python_version', 'Unknown')}")
        print(f"Compiler: {system_info.get('python_compiler', 'Unknown')}")
        
        # 実効バージョン情報
        print(f"\n=== Version Resolution ===")
        print(f"Effective Version: {version_info.get('effective_version', 'Unknown')}")
        print(f"Static Version: {version_info.get('version', 'Unknown')}")
        if package_info:
            print(f"Package.json Version: {package_info.get('version', 'Unknown')}")
        
        # バージョン優先順位の説明
        print("\n=== Version Priority ===")
        print("1. Docker environment variables (highest)")
        print("2. GitHub Actions environment variables")
        print("3. package.json (updated by CI/CD)")
        print("4. Git tags")
        print("5. Static version + Git commit (lowest)")


if __name__ == "__main__":
    # テスト実行
    print_version_info(detailed=True)