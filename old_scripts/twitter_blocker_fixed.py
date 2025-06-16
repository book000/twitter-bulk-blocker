#!/usr/bin/env python3
"""
Twitter一括ブロック機能（修正版）
video_misuse_detecteds.json に記載されているユーザーを一括でブロックします
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
import requests


class TwitterBlocker:
    def __init__(self, cookies_file: str = "cookies.json", 
                 users_file: str = "video_misuse_detecteds.json",
                 db_file: str = "block_history.db"):
        self.cookies_file = cookies_file
        self.users_file = users_file
        self.db_file = db_file
        self.client = None
        self.current_user = None
        
        # データベース初期化
        self._init_database()
        
    def _init_database(self):
        """SQLiteデータベースを初期化"""
        try:
            # データベースファイルのディレクトリを確保
            db_path = Path(self.db_file)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # データベース接続を試行
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
        
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS block_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    screen_name TEXT NOT NULL,
                    user_id TEXT,
                    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'blocked',
                    UNIQUE(screen_name, user_id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS follow_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    screen_name TEXT NOT NULL,
                    user_id TEXT,
                    following BOOLEAN DEFAULT FALSE,
                    followed_by BOOLEAN DEFAULT FALSE,
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(screen_name, user_id)
                )
            """)
            
            conn.commit()
            conn.close()
            print(f"データベース初期化完了: {self.db_file}")
        except Exception as e:
            if 'conn' in locals():
                conn.close()
            print(f"データベース初期化エラー: {e}")
            raise
        
    def load_cookies(self) -> Dict[str, Any]:
        """クッキーファイルを読み込み"""
        with open(self.cookies_file, 'r') as f:
            cookies_list = json.load(f)
            
        # リスト形式のクッキーを辞書形式に変換
        cookies_dict = {}
        for cookie in cookies_list:
            domain = cookie.get('domain', '')
            if domain in ['.x.com', '.twitter.com', 'x.com', 'twitter.com']:
                cookies_dict[cookie['name']] = cookie['value']
                
        print("読み込まれたクッキー:")
        for name, value in cookies_dict.items():
            print(f"  {name}: {value[:50]}...")
                
        return cookies_dict
        
    def load_target_users(self) -> List[str]:
        """ブロック対象ユーザーリストを読み込み"""
        with open(self.users_file, 'r') as f:
            return json.load(f)