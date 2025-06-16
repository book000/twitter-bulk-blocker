"""
データベース管理モジュール（修正版）
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class DatabaseManager:
    """SQLiteデータベース管理クラス"""

    def __init__(self, db_file: str):
        self.db_file = db_file
        self.init_database()

    def init_database(self) -> None:
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

    def is_already_blocked(
        self, identifier: str, user_format: str = "screen_name"
    ) -> bool:
        """ユーザーが既にブロック済みかチェック"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        if user_format == "user_id":
            cursor.execute(
                """
                SELECT screen_name, user_id, blocked_at, status 
                FROM block_history 
                WHERE user_id = ? AND status = 'blocked'
            """,
                (str(identifier),),
            )
        else:
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

    def get_blocked_users_count(self) -> int:
        """ブロック済みユーザー数を取得"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM block_history WHERE status = 'blocked'")
        count = cursor.fetchone()[0]

        conn.close()
        return count

    def get_blocked_users_set(self, user_format: str) -> set:
        """ブロック済みユーザーの集合を取得"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        if user_format == "user_id":
            cursor.execute(
                "SELECT user_id FROM block_history WHERE status = 'blocked' AND user_id IS NOT NULL"
            )
        else:
            cursor.execute(
                "SELECT screen_name FROM block_history WHERE status = 'blocked' AND screen_name IS NOT NULL"
            )

        blocked_users = {row[0] for row in cursor.fetchall()}
        conn.close()

        return blocked_users

    def record_block_result(
        self,
        screen_name: Optional[str],
        user_id: Optional[str],
        display_name: Optional[str],
        success: bool,
        status_code: int,
        error_message: Optional[str] = None,
        user_status: Optional[str] = None,
        retry_count: int = 0,
    ) -> None:
        """ブロック結果をデータベースに記録"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        status = "blocked" if success else "failed"
        current_time = datetime.now().isoformat()

        cursor.execute(
            """
            INSERT OR REPLACE INTO block_history 
            (screen_name, user_id, display_name, status, response_code, error_message, user_status, retry_count, last_retry_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                screen_name,
                user_id,
                display_name,
                status,
                status_code,
                error_message,
                user_status,
                retry_count,
                current_time,
            ),
        )

        conn.commit()
        conn.close()

    def start_session(self, total_targets: int) -> int:
        """処理セッションを開始"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO process_log (total_targets)
            VALUES (?)
        """,
            (total_targets,),
        )

        session_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return session_id

    def update_session(
        self, session_id: int, processed: int, blocked: int, skipped: int, errors: int
    ) -> None:
        """処理セッションを更新"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE process_log 
            SET processed = ?, blocked = ?, skipped = ?, errors = ?
            WHERE id = ?
        """,
            (processed, blocked, skipped, errors, session_id),
        )

        conn.commit()
        conn.close()

    def complete_session(self, session_id: int) -> None:
        """処理セッションを完了"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE process_log 
            SET completed = TRUE
            WHERE id = ?
        """,
            (session_id,),
        )

        conn.commit()
        conn.close()

    def get_retry_candidates(self) -> List[Dict[str, Any]]:
        """リトライ候補のユーザーを取得"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT screen_name, user_id, display_name, status, response_code, 
                   error_message, user_status, retry_count, last_retry_at
            FROM block_history 
            WHERE status = 'failed' 
            AND retry_count < 3
            AND (
                user_status IN ('suspended', 'unavailable') OR
                response_code IN (429, 500, 502, 503, 504) OR
                error_message LIKE '%temporarily%' OR
                error_message LIKE '%rate limit%' OR
                error_message LIKE '%timeout%' OR
                error_message LIKE '%server error%'
            )
            ORDER BY last_retry_at ASC
        """
        )

        candidates = []
        current_time = datetime.now()

        for row in cursor.fetchall():
            (
                screen_name,
                user_id,
                display_name,
                status,
                response_code,
                error_message,
                user_status,
                retry_count,
                last_retry_str,
            ) = row

            # 最後のリトライから十分時間が経過しているかチェック
            if last_retry_str:
                last_retry = datetime.fromisoformat(last_retry_str)
                required_delay = self._get_retry_delay(retry_count)

                if (current_time - last_retry).total_seconds() >= required_delay:
                    candidates.append(
                        {
                            "screen_name": screen_name,
                            "user_id": user_id,
                            "display_name": display_name,
                            "retry_count": retry_count,
                            "user_status": user_status,
                            "last_error": error_message,
                        }
                    )

        conn.close()
        return candidates

    def get_detailed_stats(self) -> Dict[str, int]:
        """データベースから詳細統計を取得"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        stats = {
            "failed": 0,
            "follow_relationship": 0,
            "suspended": 0,
            "unavailable": 0,
        }

        try:
            # 失敗したユーザー数
            cursor.execute("SELECT COUNT(*) FROM block_history WHERE status = 'failed'")
            stats["failed"] = cursor.fetchone()[0]

            # フォロー関係でスキップしたユーザー数
            cursor.execute(
                "SELECT COUNT(*) FROM block_history WHERE error_message LIKE '%フォロー関係%'"
            )
            stats["follow_relationship"] = cursor.fetchone()[0]

            # suspendedユーザー数
            cursor.execute(
                "SELECT COUNT(*) FROM block_history WHERE user_status = 'suspended'"
            )
            stats["suspended"] = cursor.fetchone()[0]

            # 利用不可ユーザー数
            cursor.execute(
                "SELECT COUNT(*) FROM block_history WHERE user_status IN ('unavailable', 'not_found', 'deactivated')"
            )
            stats["unavailable"] = cursor.fetchone()[0]

        except sqlite3.OperationalError:
            # データベースにまだデータがない場合
            pass

        conn.close()
        return stats

    def _get_retry_delay(self, retry_count: int, base_delay: int = 30) -> int:
        """リトライ間隔を計算（指数バックオフ）"""
        return base_delay * (2**retry_count)