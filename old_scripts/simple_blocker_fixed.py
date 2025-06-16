#!/usr/bin/env python3
"""
シンプルなTwitterブロック機能（修正版）
現状のライブラリ制限を踏まえた最小限の実装
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Optional


class SimpleTwitterBlocker:
    def __init__(self, cookies_file: str = "cookies.json", 
                 users_file: str = "video_misuse_detecteds.json",
                 db_file: str = "block_history.db"):
        self.cookies_file = cookies_file
        self.users_file = users_file
        self.db_file = db_file
        self.current_user_id = None
        
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
                CREATE TABLE IF NOT EXISTS block_candidates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    screen_name TEXT NOT NULL UNIQUE,
                    status TEXT DEFAULT 'pending',
                    checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
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
        
    def load_cookies(self) -> Dict[str, str]:
        """クッキーファイルを読み込み"""
        with open(self.cookies_file, 'r') as f:
            cookies_list = json.load(f)
            
        # リスト形式のクッキーを辞書形式に変換
        cookies_dict = {}
        for cookie in cookies_list:
            domain = cookie.get('domain', '')
            if domain in ['.x.com', '.twitter.com', 'x.com', 'twitter.com']:
                cookies_dict[cookie['name']] = cookie['value']
                
        return cookies_dict
        
    def load_target_users(self) -> List[str]:
        """ブロック対象ユーザーリストを読み込み"""
        with open(self.users_file, 'r') as f:
            return json.load(f)