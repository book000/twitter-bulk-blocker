#!/usr/bin/env python3
"""
バージョン管理モジュール

Gitタグから動的にバージョンを取得し、Gitがない環境でもフォールバック
"""

import os
import subprocess
from pathlib import Path

# フォールバックバージョン（Gitタグが取得できない場合）
FALLBACK_VERSION = "1.0.0"


def get_git_version():
    """Gitタグからバージョンを取得"""
    try:
        # パッケージのルートディレクトリを特定
        package_dir = Path(__file__).parent.parent  # twitter_blocker の親ディレクトリ

        # git describe を実行
        result = subprocess.run(
            ["git", "describe", "--tags", "--always", "--dirty"],
            cwd=package_dir,
            capture_output=True,
            text=True,
            check=True,
        )

        version = result.stdout.strip()

        # "v" プレフィックスを削除
        if version.startswith("v"):
            version = version[1:]

        # 開発バージョンの場合（例: 0.29.2-3-g1234567-dirty）
        if "-" in version:
            parts = version.split("-")
            base_version = parts[0]

            # コミットハッシュのみの場合（タグがない場合）
            if "." not in base_version:
                return None

            commits_since = parts[1] if len(parts) > 1 else "0"

            # dirtyフラグを処理
            is_dirty = version.endswith("-dirty")
            if is_dirty:
                # dirtyを除去して処理
                parts = version.replace("-dirty", "").split("-")
                commits_since = parts[1] if len(parts) > 1 else "0"

            if commits_since != "0":
                # 開発バージョンとして.devNを追加
                version = f"{base_version}.dev{commits_since}"
            else:
                version = base_version

            if is_dirty:
                version += "+dirty"

        return version

    except (subprocess.CalledProcessError, FileNotFoundError):
        # Gitが利用できない場合
        return None


def get_app_version_file():
    """CI/CDで生成される.app-versionファイルからバージョンを取得"""
    try:
        # パッケージのルートディレクトリを特定
        package_dir = Path(__file__).parent.parent
        app_version_file = package_dir / ".app-version"
        
        if app_version_file.exists():
            version = app_version_file.read_text().strip()
            if version:
                return version
    except Exception:
        pass
    return None


def get_package_version():
    """
    パッケージバージョンを取得

    優先順位:
    1. 環境変数 TWITTER_BLOCKER_VERSION
    2. 環境変数 APPLICATION_VERSION（Docker/CI環境用）
    3. CI/CDで生成される.app-versionファイル
    4. Gitタグ
    5. フォールバックバージョン
    """
    # 環境変数から取得（アプリ専用）
    env_version = os.environ.get("TWITTER_BLOCKER_VERSION")
    if env_version:
        return env_version

    # 環境変数から取得（CI/CD・Docker環境用）
    app_env_version = os.environ.get("APPLICATION_VERSION")
    if app_env_version:
        return app_env_version

    # .app-versionファイルから取得（CI/CDで生成）
    app_version = get_app_version_file()
    if app_version:
        return app_version

    # Gitタグから取得
    git_version = get_git_version()
    if git_version:
        return git_version

    # フォールバック
    return FALLBACK_VERSION


# パッケージバージョン
__version__ = get_package_version()