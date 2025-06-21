"""
データベース管理モジュール
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
            AND retry_count < 10
            AND (
                user_status IN ('unavailable') OR
                response_code IN (429, 500, 502, 503, 504) OR
                response_code IS NULL OR
                error_message LIKE '%temporarily%' OR
                error_message LIKE '%rate limit%' OR
                error_message LIKE '%timeout%' OR
                error_message LIKE '%server error%' OR
                error_message LIKE '%ユーザー情報取得失敗%'
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
            "failed_max_retries": 0,  # リトライ上限に達した失敗
            "failed_retryable": 0,    # まだリトライ可能な失敗
            "follow_relationship": 0,
            "suspended": 0,
            "unavailable": 0,
        }

        try:
            # 失敗したユーザー数
            cursor.execute("SELECT COUNT(*) FROM block_history WHERE status = 'failed'")
            stats["failed"] = cursor.fetchone()[0]

            # リトライ上限に達した失敗
            cursor.execute("SELECT COUNT(*) FROM block_history WHERE status = 'failed' AND retry_count >= 10")
            stats["failed_max_retries"] = cursor.fetchone()[0]

            # まだリトライ可能な失敗（suspended除く）
            cursor.execute(
                """
                SELECT COUNT(*) FROM block_history 
                WHERE status = 'failed' 
                AND retry_count < 10
                AND (
                    user_status IN ('unavailable') OR
                    response_code IN (429, 500, 502, 503, 504) OR
                    error_message LIKE '%temporarily%' OR
                    error_message LIKE '%rate limit%' OR
                    error_message LIKE '%timeout%' OR
                    error_message LIKE '%server error%'
                )
                """
            )
            stats["failed_retryable"] = cursor.fetchone()[0]

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

    def get_failure_breakdown(self) -> Dict[str, Any]:
        """失敗の詳細内訳を取得"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        breakdown = {
            "by_status": {},
            "by_response_code": {},
            "by_error_type": {},
        }

        try:
            # ユーザーステータス別の失敗数
            cursor.execute(
                """
                SELECT user_status, COUNT(*) 
                FROM block_history 
                WHERE status = 'failed' AND user_status IS NOT NULL 
                GROUP BY user_status
                """
            )
            for status, count in cursor.fetchall():
                breakdown["by_status"][status] = count

            # HTTPステータスコード別の失敗数
            cursor.execute(
                """
                SELECT response_code, COUNT(*) 
                FROM block_history 
                WHERE status = 'failed' AND response_code IS NOT NULL 
                GROUP BY response_code
                """
            )
            for code, count in cursor.fetchall():
                breakdown["by_response_code"][code] = count

            # エラータイプ別の失敗数
            cursor.execute(
                """
                SELECT 
                    CASE 
                        WHEN error_message LIKE '%フォロー関係%' OR error_message LIKE '%follow%' THEN 'follow_relationship'
                        WHEN error_message LIKE '%rate limit%' OR error_message LIKE '%レート制限%' OR error_message LIKE '%429%' THEN 'rate_limit'
                        WHEN error_message LIKE '%timeout%' OR error_message LIKE '%タイムアウト%' OR error_message LIKE '%timed out%' THEN 'timeout'
                        WHEN error_message LIKE '%server error%' OR error_message LIKE '%サーバーエラー%' OR error_message LIKE '%500%' OR error_message LIKE '%502%' OR error_message LIKE '%503%' OR error_message LIKE '%504%' THEN 'server_error'
                        WHEN error_message LIKE '%temporarily%' OR error_message LIKE '%一時的%' OR error_message LIKE '%temporary%' THEN 'temporary'
                        WHEN error_message LIKE '%network%' OR error_message LIKE '%ネットワーク%' OR error_message LIKE '%connection%' THEN 'network_error'
                        WHEN error_message LIKE '%unauthorized%' OR error_message LIKE '%認証%' OR error_message LIKE '%401%' THEN 'auth_error'
                        WHEN error_message LIKE '%forbidden%' OR error_message LIKE '%403%' THEN 'forbidden'
                        WHEN error_message LIKE '%not found%' OR error_message LIKE '%404%' OR error_message LIKE '%見つからない%' THEN 'not_found_error'
                        ELSE 'other'
                    END as error_type,
                    COUNT(*)
                FROM block_history 
                WHERE status = 'failed' AND error_message IS NOT NULL 
                GROUP BY error_type
                """
            )
            for error_type, count in cursor.fetchall():
                breakdown["by_error_type"][error_type] = count

        except sqlite3.OperationalError:
            # データベースにまだデータがない場合
            pass

        conn.close()
        return breakdown

    def get_error_message_samples(self, limit: int = 10) -> List[str]:
        """実際のエラーメッセージのサンプルを取得（デバッグ用）"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT DISTINCT error_message
            FROM block_history 
            WHERE status = 'failed' AND error_message IS NOT NULL 
            ORDER BY last_retry_at DESC
            LIMIT ?
            """,
            (limit,)
        )

        samples = [row[0] for row in cursor.fetchall()]
        conn.close()
        return samples

    def reset_retry_counts(self) -> int:
        """全ての失敗ユーザーのリトライ回数をリセット"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        cursor.execute(
            """
            UPDATE block_history 
            SET retry_count = 0, last_retry_at = NULL
            WHERE status = 'failed'
            """
        )

        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected_rows

    def clear_error_messages(self, identifiers: Optional[List[str]] = None, user_format: str = "screen_name") -> int:
        """エラーメッセージをクリア
        
        Args:
            identifiers: 特定のユーザーのみクリアする場合の識別子リスト（Noneで全て）
            user_format: 識別子の形式 ("screen_name" または "user_id")
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        if identifiers:
            placeholders = ",".join("?" * len(identifiers))
            str_identifiers = [str(id_) for id_ in identifiers]
            
            if user_format == "user_id":
                query = f"""
                    UPDATE block_history 
                    SET error_message = NULL
                    WHERE status = 'failed' AND user_id IN ({placeholders})
                """
            else:
                query = f"""
                    UPDATE block_history 
                    SET error_message = NULL
                    WHERE status = 'failed' AND screen_name IN ({placeholders})
                """
            cursor.execute(query, str_identifiers)
        else:
            cursor.execute(
                """
                UPDATE block_history 
                SET error_message = NULL
                WHERE status = 'failed'
                """
            )

        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected_rows

    def reset_failed_users(self, identifiers: Optional[List[str]] = None, user_format: str = "screen_name", 
                          reset_error_message: bool = True, reset_retry_count: bool = True,
                          reset_response_code: bool = True, reset_user_status: bool = True) -> int:
        """失敗ユーザーの状態をリセット
        
        Args:
            identifiers: 特定のユーザーのみリセットする場合の識別子リスト（Noneで全て）
            user_format: 識別子の形式 ("screen_name" または "user_id")
            reset_error_message: エラーメッセージをリセットするか
            reset_retry_count: リトライ回数をリセットするか
            reset_response_code: レスポンスコードをリセットするか
            reset_user_status: ユーザーステータスをリセットするか
        """
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # リセットする項目を構築
        reset_fields = []
        if reset_error_message:
            reset_fields.append("error_message = NULL")
        if reset_retry_count:
            reset_fields.append("retry_count = 0")
            reset_fields.append("last_retry_at = NULL")
        if reset_response_code:
            reset_fields.append("response_code = NULL")
        if reset_user_status:
            reset_fields.append("user_status = NULL")
        
        if not reset_fields:
            conn.close()
            return 0
        
        set_clause = ", ".join(reset_fields)

        if identifiers:
            placeholders = ",".join("?" * len(identifiers))
            str_identifiers = [str(id_) for id_ in identifiers]
            
            if user_format == "user_id":
                query = f"""
                    UPDATE block_history 
                    SET {set_clause}
                    WHERE status = 'failed' AND user_id IN ({placeholders})
                """
            else:
                query = f"""
                    UPDATE block_history 
                    SET {set_clause}
                    WHERE status = 'failed' AND screen_name IN ({placeholders})
                """
            cursor.execute(query, str_identifiers)
        else:
            cursor.execute(
                f"""
                UPDATE block_history 
                SET {set_clause}
                WHERE status = 'failed'
                """
            )

        affected_rows = cursor.rowcount
        conn.commit()
        conn.close()
        
        return affected_rows

    def is_permanent_failure(self, identifier: str, user_format: str = "screen_name") -> bool:
        """永続的失敗アカウントかどうかをチェック"""
        from .retry import RetryManager
        
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            if user_format == "user_id":
                cursor.execute(
                    """
                    SELECT user_status, response_code, error_message, retry_count
                    FROM block_history 
                    WHERE user_id = ? AND status = 'failed'
                """,
                    (str(identifier),),
                )
            else:
                cursor.execute(
                    """
                    SELECT user_status, response_code, error_message, retry_count
                    FROM block_history 
                    WHERE screen_name = ? AND status = 'failed'
                """,
                    (str(identifier),),
                )

            result = cursor.fetchone()

        if not result:
            return False

        user_status, response_code, error_message, retry_count = result
        
        # RetryManagerで永続的失敗かどうかを判定
        retry_manager = RetryManager()
        return not retry_manager.should_retry(
            user_status or "unknown",
            response_code or 0,
            error_message or "",
            retry_count or 0
        )

    def get_permanent_failure_info(self, identifier: str, user_format: str = "screen_name") -> Optional[Dict[str, Any]]:
        """永続的失敗アカウントの詳細情報を取得"""
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()

            if user_format == "user_id":
                cursor.execute(
                    """
                    SELECT screen_name, user_id, display_name, user_status, 
                           response_code, error_message, retry_count, blocked_at
                    FROM block_history 
                    WHERE user_id = ? AND status = 'failed'
                """,
                    (str(identifier),),
                )
            else:
                cursor.execute(
                    """
                    SELECT screen_name, user_id, display_name, user_status, 
                           response_code, error_message, retry_count, blocked_at
                    FROM block_history 
                    WHERE screen_name = ? AND status = 'failed'
                """,
                    (str(identifier),),
                )

            result = cursor.fetchone()

        if not result:
            return None

        (screen_name, user_id, display_name, user_status, 
         response_code, error_message, retry_count, blocked_at) = result

        return {
            "screen_name": screen_name,
            "user_id": user_id,
            "display_name": display_name,
            "user_status": user_status or "unknown",
            "response_code": response_code,
            "error_message": error_message,
            "retry_count": retry_count,
            "blocked_at": blocked_at,
            "permanent_failure": True
        }

    def get_permanent_failures_batch(self, identifiers: List[str], user_format: str = "screen_name") -> Dict[str, Dict[str, Any]]:
        """複数の永続的失敗アカウントを一括取得"""
        from .retry import RetryManager
        
        if not identifiers:
            return {}
        
        retry_manager = RetryManager()
        results = {}
        
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            
            # プレースホルダーを準備
            placeholders = ",".join("?" * len(identifiers))
            str_identifiers = [str(id_) for id_ in identifiers]
            
            if user_format == "user_id":
                query = f"""
                    SELECT user_id, screen_name, display_name, user_status, 
                           response_code, error_message, retry_count, blocked_at
                    FROM block_history 
                    WHERE user_id IN ({placeholders}) AND status = 'failed'
                """
            else:
                query = f"""
                    SELECT screen_name, user_id, display_name, user_status, 
                           response_code, error_message, retry_count, blocked_at
                    FROM block_history 
                    WHERE screen_name IN ({placeholders}) AND status = 'failed'
                """
            
            cursor.execute(query, str_identifiers)
            rows = cursor.fetchall()
        
        # 結果を処理
        for row in rows:
            if user_format == "user_id":
                user_id, screen_name, display_name, user_status, response_code, error_message, retry_count, blocked_at = row
                key = user_id
            else:
                screen_name, user_id, display_name, user_status, response_code, error_message, retry_count, blocked_at = row
                key = screen_name
            
            # RetryManagerで永続的失敗かどうかを判定
            is_permanent = not retry_manager.should_retry(
                user_status or "unknown",
                response_code or 0,
                error_message or "",
                retry_count or 0
            )
            
            if is_permanent:
                results[key] = {
                    "screen_name": screen_name,
                    "user_id": user_id,
                    "display_name": display_name,
                    "user_status": user_status or "unknown",
                    "response_code": response_code,
                    "error_message": error_message,
                    "retry_count": retry_count,
                    "blocked_at": blocked_at,
                    "permanent_failure": True
                }
        
        return results

    def _get_retry_delay(self, retry_count: int, base_delay: int = 30) -> int:
        """リトライ間隔を計算（指数バックオフ）"""
        return base_delay * (2**retry_count)
