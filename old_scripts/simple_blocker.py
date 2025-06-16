#!/usr/bin/env python3
"""
シンプルなTwitterブロック機能
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
        except sqlite3.Error as e:
            print(f"データベース接続エラー: {e}")
            print(f"データベースファイルパス: {self.db_file}")
            raise
        
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
            
    def get_current_user_id(self) -> Optional[str]:
        """ログイン中のユーザーIDを取得"""
        try:
            cookies = self.load_cookies()
            twid = cookies.get('twid', '')
            
            if twid.startswith('u%3D'):
                self.current_user_id = twid.replace('u%3D', '')
                return self.current_user_id
                
            return None
            
        except Exception as e:
            print(f"ユーザーID取得エラー: {e}")
            return None
            
    def save_candidates_to_db(self):
        """ブロック候補をデータベースに保存"""
        try:
            target_users = self.load_target_users()
            
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            for screen_name in target_users:
                cursor.execute("""
                    INSERT OR IGNORE INTO block_candidates 
                    (screen_name, status, notes) 
                    VALUES (?, 'pending', 'Loaded from JSON')
                """, (screen_name,))
                
            conn.commit()
            conn.close()
            
            print(f"データベースに{len(target_users)}人のユーザーを登録しました")
            
        except Exception as e:
            print(f"データベース保存エラー: {e}")
            
    def analyze_users(self):
        """ユーザー分析（現状では基本情報のみ）"""
        try:
            current_user_id = self.get_current_user_id()
            target_users = self.load_target_users()
            
            print("=== 分析結果 ===")
            print(f"ログイン中のユーザーID: {current_user_id}")
            print(f"ブロック対象ユーザー数: {len(target_users)}")
            
            # データベースに保存
            self.save_candidates_to_db()
            
            print("\n注意: 現在の実装では以下の制限があります:")
            print("1. Twitter内部APIへの直接アクセスが制限されています")
            print("2. ブロック機能は実装されていません")
            print("3. フォロー関係のチェックができません")
            
            print("\n推奨される次のステップ:")
            print("1. 別のライブラリやツールを検討")
            print("2. Twitter公式APIの利用を検討")
            print("3. ブラウザ自動化ツール（Selenium等）の利用を検討")
            
            return {
                'current_user_id': current_user_id,
                'target_count': len(target_users),
                'status': 'analysis_complete'
            }
            
        except Exception as e:
            print(f"分析エラー: {e}")
            return None
            
    def export_user_list(self, output_file: str = "block_candidates.txt"):
        """ブロック候補をテキストファイルに出力"""
        try:
            target_users = self.load_target_users()
            
            with open(output_file, 'w') as f:
                f.write("# Twitter Block Candidates\n")
                f.write(f"# Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"# Total users: {len(target_users)}\n\n")
                
                for user in target_users:
                    f.write(f"@{user}\n")
                    
            print(f"ユーザーリストを {output_file} に出力しました")
            
        except Exception as e:
            print(f"エクスポートエラー: {e}")


def main():
    """メイン関数"""
    blocker = SimpleTwitterBlocker()
    
    print("Twitter Simple Blocker")
    print("======================")
    
    # 基本分析を実行
    result = blocker.analyze_users()
    
    if result:
        print(f"\n分析完了: {result['target_count']}人のユーザーを確認しました")
        
        # ユーザーリストをテキストファイルに出力
        blocker.export_user_list()
        
        print("\n次の手順:")
        print("1. block_candidates.txt を確認")
        print("2. 手動でのブロック、または別のツールの検討")
        print("3. 必要に応じてblock_history.dbの内容を確認")
    else:
        print("分析に失敗しました")


if __name__ == "__main__":
    main()