#!/usr/bin/env python3
"""
一括ブロック管理システム（修正版）
SQLiteデータベースで履歴管理し、重複ブロックを防止
"""

import json
import sqlite3
import time
from datetime import datetime
from pathlib import Path

import requests


class BulkBlockManager:
    def __init__(
        self,
        cookies_file="cookies.json",
        users_file="video_misuse_detecteds.json",
        db_file="block_history.db",
    ):
        self.cookies_file = cookies_file
        self.users_file = users_file
        self.db_file = db_file
        self.init_database()

    def init_database(self):
        """データベースを初期化"""
        try:
            # データベースファイルのディレクトリを確保
            db_path = Path(self.db_file)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # データベース接続を試行
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()

            # ブロック履歴テーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS block_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    screen_name TEXT NOT NULL,
                    user_id TEXT,
                    display_name TEXT,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'blocked',
                    response_code INTEGER,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    last_retry_at TIMESTAMP,
                    user_status TEXT,
                    UNIQUE(user_id)
                )
            """
            )

            # 処理ログテーブル
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS process_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_targets INTEGER,
                    processed INTEGER DEFAULT 0,
                    blocked INTEGER DEFAULT 0,
                    skipped INTEGER DEFAULT 0,
                    errors INTEGER DEFAULT 0,
                    completed BOOLEAN DEFAULT FALSE
                )
            """
            )

            conn.commit()
            conn.close()
            print(f"データベース初期化完了: {self.db_file}")
        except Exception as e:
            if 'conn' in locals():
                conn.close()
            print(f"データベース初期化エラー: {e}")
            raise

    def load_cookies(self):
        """クッキーファイルを読み込み"""
        with open(self.cookies_file, "r") as f:
            cookies_list = json.load(f)

        cookies_dict = {}
        for cookie in cookies_list:
            domain = cookie.get("domain", "")
            if domain in [".x.com", ".twitter.com", "x.com", "twitter.com"]:
                cookies_dict[cookie["name"]] = cookie["value"]

        return cookies_dict

    def load_target_users(self):
        """ブロック対象ユーザーリストを読み込み（提案1スキーマ対応）"""
        with open(self.users_file, "r") as f:
            data = json.load(f)

        # 提案1スキーマ: {"format": "user_id|screen_name", "users": [...]}
        if isinstance(data, dict):
            # 必須フィールドの確認
            if "format" not in data:
                raise ValueError(
                    f"不正なスキーマ: 'format' フィールドが必要です。期待値: {{'format': 'user_id|screen_name', 'users': [...]}}"
                )

            if "users" not in data:
                raise ValueError(
                    f"不正なスキーマ: 'users' フィールドが必要です。期待値: {{'format': 'user_id|screen_name', 'users': [...]}}"
                )

            # formatフィールドの検証
            format_value = data["format"]
            if format_value not in ["user_id", "screen_name"]:
                raise ValueError(
                    f"不正なformat値: '{format_value}'。有効値: 'user_id' または 'screen_name'"
                )

            # usersフィールドの検証
            users = data["users"]
            if not isinstance(users, list):
                raise ValueError(
                    f"不正なusers値: リストである必要があります。取得値: {type(users)}"
                )

            if not users:
                raise ValueError("users リストが空です")

            # formatとして保存
            self._user_format = format_value
            return users
        else:
            raise ValueError(
                f"不正なユーザーファイル形式: {type(data)}。期待値: {{'format': 'user_id|screen_name', 'users': [...]}}"
            )

    def get_user_format(self):
        """ユーザーファイルで指定されたformat値を取得"""
        if not hasattr(self, "_user_format"):
            # まだロードされていない場合はロードして形式を取得
            self.load_target_users()
        return self._user_format

    def is_already_blocked(self, identifier, user_format="screen_name"):
        """ユーザーが既にブロック済みかチェック（スクリーンネーム or ユーザーID）"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        if user_format == "user_id":
            # ユーザーIDで検索
            cursor.execute(
                """
                SELECT screen_name, user_id, blocked_at, status 
                FROM block_history 
                WHERE user_id = ? AND status = 'blocked'
            """,
                (str(identifier),),
            )
        else:
            # スクリーンネームで検索
            cursor.execute(
                """
                SELECT screen_name, user_id, blocked_at, status 
                FROM block_history 
                WHERE screen_name = ? AND status = 'blocked'
            """,
                (str(identifier),),
            )

        result = cursor.fetchone()
        conn.close()

        return result is not None

    def get_blocked_users_count(self):
        """ブロック済みユーザー数を取得"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM block_history WHERE status = 'blocked'")
        count = cursor.fetchone()[0]

        conn.close()
        return count