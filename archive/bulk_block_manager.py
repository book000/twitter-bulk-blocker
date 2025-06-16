#!/usr/bin/env python3
"""
一括ブロック管理システム
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

    def get_user_info(self, screen_name):
        """スクリーンネームからユーザー情報を取得"""
        try:
            cookies = self.load_cookies()

            headers = {
                "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                "x-csrf-token": cookies.get("ct0", ""),
                "x-twitter-auth-type": "OAuth2Session",
                "x-twitter-active-user": "yes",
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
                "accept": "*/*",
                "accept-language": "ja,en-US;q=0.7,en;q=0.3",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "dnt": "1",
            }

            cookie_str = "; ".join(
                [f"{name}={value}" for name, value in cookies.items()]
            )
            headers["cookie"] = cookie_str

            url = "https://x.com/i/api/graphql/7mjxD3-C6BxitPMVQ6w0-Q/UserByScreenName"

            params = {
                "variables": json.dumps(
                    {
                        "screen_name": screen_name,
                        "withSafetyModeUserFields": True,
                        "withSuperFollowsUserFields": True,
                    }
                ),
                "features": json.dumps(
                    {
                        "hidden_profile_likes_enabled": True,
                        "responsive_web_graphql_exclude_directive_enabled": True,
                        "verified_phone_label_enabled": False,
                        "subscriptions_verification_info_is_identity_verified_enabled": True,
                        "subscriptions_verification_info_verified_since_enabled": True,
                        "highlights_tweets_tab_ui_enabled": True,
                        "creator_subscriptions_tweet_preview_api_enabled": True,
                        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                        "responsive_web_graphql_timeline_navigation_enabled": True,
                    }
                ),
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()

                if (
                    "data" in data
                    and "user" in data["data"]
                    and "result" in data["data"]["user"]
                ):
                    result = data["data"]["user"]["result"]

                    # ユーザーのTypeNameをチェック（suspended/deactivatedなどの検出）
                    typename = result.get("__typename", "User")
                    user_status = "active"

                    if typename == "UserUnavailable":
                        # ユーザーが利用不可（suspended, deactivated等）
                        user_status = "unavailable"
                        if "reason" in result:
                            user_status = result["reason"].lower()

                        return {
                            "id": result.get("rest_id"),
                            "screen_name": screen_name,
                            "name": None,
                            "user_status": user_status,
                            "following": False,
                            "followed_by": False,
                            "blocking": False,
                            "blocked_by": False,
                            "protected": False,
                            "unavailable": True,
                        }

                    if "legacy" in result:
                        legacy = result["legacy"]

                        return {
                            "id": legacy.get("id_str") or result.get("rest_id"),
                            "screen_name": legacy.get("screen_name"),
                            "name": legacy.get("name"),
                            "user_status": user_status,
                            "following": legacy.get("following", False),
                            "followed_by": legacy.get("followed_by", False),
                            "blocking": legacy.get("blocking", False),
                            "blocked_by": legacy.get("blocked_by", False),
                            "protected": legacy.get("protected", False),
                            "unavailable": False,
                        }
                elif "errors" in data:
                    # GraphQLエラーの場合
                    errors = data["errors"]
                    for error in errors:
                        if "User not found" in error.get("message", ""):
                            return {
                                "id": None,
                                "screen_name": screen_name,
                                "name": None,
                                "user_status": "not_found",
                                "following": False,
                                "followed_by": False,
                                "blocking": False,
                                "blocked_by": False,
                                "protected": False,
                                "unavailable": True,
                            }

            return None

        except Exception as e:
            print(f"ユーザー情報取得エラー ({screen_name}): {e}")
            return None

    def get_user_info_by_id(self, user_id):
        """ユーザーIDからユーザー情報を取得"""
        try:
            cookies = self.load_cookies()

            headers = {
                "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                "x-csrf-token": cookies.get("ct0", ""),
                "x-twitter-auth-type": "OAuth2Session",
                "x-twitter-active-user": "yes",
                "content-type": "application/json",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
                "accept": "*/*",
                "accept-language": "ja,en-US;q=0.7,en;q=0.3",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "dnt": "1",
            }

            cookie_str = "; ".join(
                [f"{name}={value}" for name, value in cookies.items()]
            )
            headers["cookie"] = cookie_str

            # UserByRestIdエンドポイントを使用
            url = "https://x.com/i/api/graphql/I5nvpI91ljifos1Y3Lltyg/UserByRestId"

            params = {
                "variables": json.dumps(
                    {
                        "userId": str(user_id),
                        "withSafetyModeUserFields": True,
                        "withSuperFollowsUserFields": True,
                    }
                ),
                "features": json.dumps(
                    {
                        "hidden_profile_likes_enabled": True,
                        "responsive_web_graphql_exclude_directive_enabled": True,
                        "verified_phone_label_enabled": False,
                        "subscriptions_verification_info_is_identity_verified_enabled": True,
                        "subscriptions_verification_info_verified_since_enabled": True,
                        "highlights_tweets_tab_ui_enabled": True,
                        "creator_subscriptions_tweet_preview_api_enabled": True,
                        "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
                        "responsive_web_graphql_timeline_navigation_enabled": True,
                    }
                ),
            }

            response = requests.get(url, headers=headers, params=params)

            if response.status_code == 200:
                data = response.json()

                if (
                    "data" in data
                    and "user" in data["data"]
                    and "result" in data["data"]["user"]
                ):
                    result = data["data"]["user"]["result"]

                    # ユーザーのTypeNameをチェック（suspended/deactivatedなどの検出）
                    typename = result.get("__typename", "User")
                    user_status = "active"

                    if typename == "UserUnavailable":
                        # ユーザーが利用不可（suspended, deactivated等）
                        user_status = "unavailable"
                        if "reason" in result:
                            user_status = result["reason"].lower()

                        return {
                            "id": str(user_id),
                            "screen_name": None,
                            "name": None,
                            "user_status": user_status,
                            "following": False,
                            "followed_by": False,
                            "blocking": False,
                            "blocked_by": False,
                            "protected": False,
                            "unavailable": True,
                        }

                    if "legacy" in result:
                        legacy = result["legacy"]

                        return {
                            "id": str(user_id),
                            "screen_name": legacy.get("screen_name"),
                            "name": legacy.get("name"),
                            "user_status": user_status,
                            "following": legacy.get("following", False),
                            "followed_by": legacy.get("followed_by", False),
                            "blocking": legacy.get("blocking", False),
                            "blocked_by": legacy.get("blocked_by", False),
                            "protected": legacy.get("protected", False),
                            "unavailable": False,
                        }
                elif "errors" in data:
                    # GraphQLエラーの場合
                    errors = data["errors"]
                    for error in errors:
                        if "User not found" in error.get("message", ""):
                            return {
                                "id": str(user_id),
                                "screen_name": None,
                                "name": None,
                                "user_status": "not_found",
                                "following": False,
                                "followed_by": False,
                                "blocking": False,
                                "blocked_by": False,
                                "protected": False,
                                "unavailable": True,
                            }

            return None

        except Exception as e:
            print(f"ユーザー情報取得エラー (ID: {user_id}): {e}")
            return None

    def block_user(self, user_id, screen_name):
        """REST APIでユーザーをブロック"""
        try:
            cookies = self.load_cookies()

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
                "Accept": "*/*",
                "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": "https://x.com/home",
                "x-twitter-auth-type": "OAuth2Session",
                "x-csrf-token": cookies.get("ct0", ""),
                "x-twitter-client-language": "ja",
                "x-twitter-active-user": "yes",
                "Origin": "https://x.com",
                "DNT": "1",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
                "Connection": "keep-alive",
            }

            cookie_str = "; ".join(
                [f"{name}={value}" for name, value in cookies.items()]
            )
            headers["Cookie"] = cookie_str

            url = "https://x.com/i/api/1.1/blocks/create.json"
            data = {"user_id": user_id}

            response = requests.post(url, headers=headers, data=data)

            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_data": (
                    response.json() if response.status_code == 200 else None
                ),
                "error_message": response.text if response.status_code != 200 else None,
            }

        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "response_data": None,
                "error_message": str(e),
            }

    def record_block_result(
        self,
        screen_name,
        user_id,
        display_name,
        success,
        status_code,
        error_message=None,
        user_status=None,
        retry_count=0,
    ):
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

    def start_session(self, total_targets):
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

    def update_session(self, session_id, processed, blocked, skipped, errors):
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

    def complete_session(self, session_id):
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

    def get_remaining_users(self):
        """未処理のユーザーリストを取得"""
        target_users = self.load_target_users()
        user_format = self.get_user_format()

        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        if user_format == "user_id":
            # ユーザーIDの場合：user_idで照合
            cursor.execute(
                "SELECT user_id FROM block_history WHERE status = 'blocked' AND user_id IS NOT NULL"
            )
            blocked_users = {row[0] for row in cursor.fetchall()}
        else:
            # スクリーンネームの場合：screen_nameで照合
            cursor.execute(
                "SELECT screen_name FROM block_history WHERE status = 'blocked' AND screen_name IS NOT NULL"
            )
            blocked_users = {row[0] for row in cursor.fetchall()}

        conn.close()

        # 未処理のユーザーのみを返す
        remaining_users = [
            user for user in target_users if str(user) not in blocked_users
        ]

        return remaining_users

    def should_retry(self, user_status, status_code, error_message, retry_count):
        """リトライすべきかどうかを判定"""
        max_retries = 3

        # リトライ回数上限チェック
        if retry_count >= max_retries:
            return False

        # 永続的な失敗（リトライ不要）
        permanent_failures = [
            "not_found",  # ユーザーが存在しない
            "deactivated",  # アカウント無効化
        ]

        if user_status in permanent_failures:
            return False

        # 一時的な失敗（リトライ対象）
        temporary_failures = [
            "suspended",  # アカウント凍結（解除される可能性あり）
            "unavailable",  # 一時的に利用不可
        ]

        if user_status in temporary_failures:
            return True

        # HTTPステータスコードによる判定
        retryable_status_codes = [
            429,  # Rate limit
            500,  # Internal server error
            502,  # Bad gateway
            503,  # Service unavailable
            504,  # Gateway timeout
        ]

        if status_code in retryable_status_codes:
            return True

        # エラーメッセージによる判定
        if error_message:
            retryable_messages = [
                "temporarily unavailable",
                "rate limit",
                "timeout",
                "server error",
            ]

            error_lower = error_message.lower()
            for msg in retryable_messages:
                if msg in error_lower:
                    return True

        return False

    def get_retry_delay(self, retry_count, base_delay=30):
        """リトライ間隔を計算（指数バックオフ）"""
        return base_delay * (2**retry_count)

    def get_retry_candidates(self):
        """リトライ候補のユーザーを取得"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()

        # 失敗したユーザーでリトライ可能なものを取得
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
                required_delay = self.get_retry_delay(retry_count)

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

    def process_bulk_block(self, max_users=None, delay=1.0):
        """一括ブロック処理を実行"""
        print("=== 一括ブロック処理開始 ===")

        # 処理対象ユーザーを取得
        remaining_users = self.get_remaining_users()
        total_targets = len(remaining_users)

        # ユーザーファイルの形式を取得
        user_format = self.get_user_format()
        print(f"ユーザーファイル形式: {user_format}")

        if max_users:
            remaining_users = remaining_users[:max_users]
            print(f"処理制限: 最大{max_users}人まで処理")

        print(f"全対象ユーザー: {len(self.load_target_users())}人")
        print(f"既にブロック済み: {self.get_blocked_users_count()}人")
        print(f"残り処理対象: {len(remaining_users)}人")

        if not remaining_users:
            print("✓ 全てのユーザーが既にブロック済みです")
            return

        # セッション開始
        session_id = self.start_session(total_targets)

        stats = {"processed": 0, "blocked": 0, "skipped": 0, "errors": 0}

        print(f"\n処理開始: {len(remaining_users)}人を処理します")
        print("-" * 50)

        for i, user_identifier in enumerate(remaining_users, 1):
            # ユーザー形式に応じて表示とキーを設定
            if user_format == "user_id":
                print(
                    f"[{i}/{len(remaining_users)}] ユーザーID {user_identifier} を処理中..."
                )
                lookup_key = str(user_identifier)
            else:
                print(f"[{i}/{len(remaining_users)}] @{user_identifier} を処理中...")
                lookup_key = str(user_identifier)

            try:
                # 重複チェック（念のため）
                if self.is_already_blocked(lookup_key, user_format):
                    print(f"  ℹ スキップ: 既にブロック済み")
                    stats["skipped"] += 1
                    continue

                # ユーザー情報を取得（形式に応じて適切なメソッドを使用）
                if user_format == "user_id":
                    user_info = self.get_user_info_by_id(user_identifier)
                else:
                    user_info = self.get_user_info(user_identifier)

                if not user_info:
                    print(f"  ✗ エラー: ユーザー情報取得失敗")
                    stats["errors"] += 1
                    # user_infoがNoneの場合の適切な処理
                    fallback_screen_name = (
                        str(user_identifier) if user_format == "screen_name" else None
                    )
                    self.record_block_result(
                        fallback_screen_name,
                        None,
                        None,
                        False,
                        404,
                        "ユーザー情報取得失敗",
                    )
                    continue

                # 適切なscreen_nameを取得
                screen_name = user_info.get("screen_name") or str(user_identifier)

                # ユーザーが利用不可の場合
                if user_info.get("unavailable", False):
                    user_status = user_info.get("user_status", "unavailable")
                    print(f"  ⚠ スキップ: ユーザー利用不可 ({user_status})")
                    stats["skipped"] += 1

                    # suspendedなど一時的な状態の場合はリトライ対象として記録
                    if self.should_retry(user_status, 0, f"User {user_status}", 0):
                        print(f"    → リトライ対象として記録")
                        self.record_block_result(
                            screen_name,
                            user_info.get("id"),
                            user_info.get("name"),
                            False,
                            0,
                            f"User {user_status}",
                            user_status,
                            0,
                        )
                    else:
                        self.record_block_result(
                            screen_name,
                            user_info.get("id"),
                            user_info.get("name"),
                            False,
                            0,
                            f"User {user_status} (permanent)",
                            user_status,
                            0,
                        )
                    continue

                # フォロー関係チェック
                if user_info["following"] or user_info["followed_by"]:
                    print(
                        f"  ⚠ スキップ: フォロー関係あり (フォロー中: {user_info['following']}, フォロワー: {user_info['followed_by']})"
                    )
                    stats["skipped"] += 1
                    self.record_block_result(
                        screen_name,
                        user_info["id"],
                        user_info["name"],
                        False,
                        0,
                        "フォロー関係あり",
                        user_info.get("user_status", "active"),
                    )
                    continue

                # 既にブロック済みかチェック
                if user_info["blocking"]:
                    print(f"  ℹ スキップ: 既にブロック済み")
                    stats["skipped"] += 1
                    self.record_block_result(
                        screen_name,
                        user_info["id"],
                        user_info["name"],
                        True,
                        200,
                        "既にブロック済み",
                        user_info.get("user_status", "active"),
                    )
                    continue

                # ブロック実行
                print(f"  → ブロック実行: {user_info['name']} (ID: {user_info['id']})")
                block_result = self.block_user(user_info["id"], screen_name)

                if block_result["success"]:
                    print(f"  ✓ ブロック成功")
                    stats["blocked"] += 1
                    self.record_block_result(
                        screen_name,
                        user_info["id"],
                        user_info["name"],
                        True,
                        block_result["status_code"],
                        None,
                        user_info.get("user_status", "active"),
                    )
                else:
                    error_msg = (
                        block_result["error_message"][:200]
                        if block_result["error_message"]
                        else "Unknown error"
                    )
                    print(
                        f"  ✗ ブロック失敗: {block_result['status_code']} - {error_msg}"
                    )

                    # リトライ判定
                    user_status = user_info.get("user_status", "active")
                    if self.should_retry(
                        user_status,
                        block_result["status_code"],
                        block_result["error_message"],
                        0,
                    ):
                        print(f"    → リトライ対象として記録")
                        stats["errors"] += 1
                        self.record_block_result(
                            screen_name,
                            user_info["id"],
                            user_info["name"],
                            False,
                            block_result["status_code"],
                            block_result["error_message"],
                            user_status,
                            0,
                        )
                    else:
                        print(f"    → 永続的な失敗として記録")
                        stats["errors"] += 1
                        self.record_block_result(
                            screen_name,
                            user_info["id"],
                            user_info["name"],
                            False,
                            block_result["status_code"],
                            f"{block_result['error_message']} (permanent)",
                            user_status,
                            0,
                        )

                stats["processed"] += 1

                # セッション更新
                self.update_session(
                    session_id,
                    stats["processed"],
                    stats["blocked"],
                    stats["skipped"],
                    stats["errors"],
                )

                # 進捗表示
                if i % 10 == 0:
                    print(
                        f"\n  進捗: {i}/{len(remaining_users)} 完了 (ブロック: {stats['blocked']}, スキップ: {stats['skipped']}, エラー: {stats['errors']})"
                    )

                # レート制限対策
                time.sleep(delay)

            except Exception as e:
                print(f"  ✗ 処理エラー: {e}")
                stats["errors"] += 1
                self.record_block_result(screen_name, None, None, False, 0, str(e))
                continue

        # セッション完了
        self.complete_session(session_id)

        print("\n" + "=" * 50)
        print("=== 一括ブロック処理完了 ===")
        print(f"処理対象: {len(remaining_users)}人")
        print(f"ブロック成功: {stats['blocked']}人")
        print(f"スキップ: {stats['skipped']}人")
        print(f"エラー: {stats['errors']}人")
        print(f"総ブロック数: {self.get_blocked_users_count()}人")

        remaining_after = len(self.get_remaining_users())
        print(f"残り未処理: {remaining_after}人")

        if remaining_after == 0:
            print("🎉 全ての対象ユーザーの処理が完了しました！")

    def process_retries(self, max_retries=None):
        """リトライ処理を実行"""
        print("=== リトライ処理開始 ===")

        retry_candidates = self.get_retry_candidates()

        if not retry_candidates:
            print("リトライ対象のユーザーがいません")
            return

        if max_retries:
            retry_candidates = retry_candidates[:max_retries]

        print(f"リトライ対象: {len(retry_candidates)}人")
        print("-" * 50)

        stats = {"processed": 0, "blocked": 0, "skipped": 0, "errors": 0}

        for i, candidate in enumerate(retry_candidates, 1):
            screen_name = candidate["screen_name"]
            user_id = candidate["user_id"]
            retry_count = candidate["retry_count"] + 1

            print(
                f"[{i}/{len(retry_candidates)}] @{screen_name} をリトライ中... (試行回数: {retry_count})"
            )

            try:
                # 最新のユーザー情報を再取得
                user_info = self.get_user_info(screen_name)

                if not user_info:
                    print(f"  ✗ ユーザー情報取得失敗")
                    stats["errors"] += 1
                    self.record_block_result(
                        screen_name,
                        user_id,
                        candidate["display_name"],
                        False,
                        404,
                        "ユーザー情報取得失敗 (リトライ)",
                        None,
                        retry_count,
                    )
                    continue

                # ユーザー状態が改善されているかチェック
                if user_info.get("unavailable", False):
                    user_status = user_info.get("user_status", "unavailable")
                    print(f"  ⚠ まだ利用不可: {user_status}")

                    # まだリトライ可能かチェック
                    if self.should_retry(
                        user_status, 0, f"User {user_status}", retry_count
                    ):
                        print(f"    → 次回リトライ対象として記録")
                        self.record_block_result(
                            screen_name,
                            user_info.get("id"),
                            user_info.get("name"),
                            False,
                            0,
                            f"User {user_status} (retry {retry_count})",
                            user_status,
                            retry_count,
                        )
                    else:
                        print(f"    → リトライ上限に達しました")
                        self.record_block_result(
                            screen_name,
                            user_info.get("id"),
                            user_info.get("name"),
                            False,
                            0,
                            f"User {user_status} (max retries)",
                            user_status,
                            retry_count,
                        )

                    stats["skipped"] += 1
                    continue

                # フォロー関係チェック（念のため）
                if user_info["following"] or user_info["followed_by"]:
                    print(f"  ⚠ スキップ: フォロー関係が発生")
                    stats["skipped"] += 1
                    self.record_block_result(
                        screen_name,
                        user_info["id"],
                        user_info["name"],
                        False,
                        0,
                        "フォロー関係あり (リトライ時)",
                        user_info.get("user_status", "active"),
                        retry_count,
                    )
                    continue

                # 既にブロック済みかチェック
                if user_info["blocking"]:
                    print(f"  ✓ 既にブロック済みでした")
                    stats["blocked"] += 1
                    self.record_block_result(
                        screen_name,
                        user_info["id"],
                        user_info["name"],
                        True,
                        200,
                        "既にブロック済み (リトライ時)",
                        user_info.get("user_status", "active"),
                        retry_count,
                    )
                    continue

                # ブロック実行
                print(f"  → ブロック実行")
                block_result = self.block_user(user_info["id"], screen_name)

                if block_result["success"]:
                    print(f"  ✓ ブロック成功")
                    stats["blocked"] += 1
                    self.record_block_result(
                        screen_name,
                        user_info["id"],
                        user_info["name"],
                        True,
                        block_result["status_code"],
                        "リトライ成功",
                        user_info.get("user_status", "active"),
                        retry_count,
                    )
                else:
                    error_msg = (
                        block_result["error_message"][:200]
                        if block_result["error_message"]
                        else "Unknown error"
                    )
                    print(
                        f"  ✗ ブロック失敗: {block_result['status_code']} - {error_msg}"
                    )

                    # 更なるリトライが可能かチェック
                    user_status = user_info.get("user_status", "active")
                    if self.should_retry(
                        user_status,
                        block_result["status_code"],
                        block_result["error_message"],
                        retry_count,
                    ):
                        print(f"    → 更なるリトライ対象として記録")
                        self.record_block_result(
                            screen_name,
                            user_info["id"],
                            user_info["name"],
                            False,
                            block_result["status_code"],
                            f"{block_result['error_message']} (retry {retry_count})",
                            user_status,
                            retry_count,
                        )
                    else:
                        print(f"    → 最終失敗として記録")
                        self.record_block_result(
                            screen_name,
                            user_info["id"],
                            user_info["name"],
                            False,
                            block_result["status_code"],
                            f"{block_result['error_message']} (final)",
                            user_status,
                            retry_count,
                        )

                    stats["errors"] += 1

                stats["processed"] += 1

                # リトライ間隔
                time.sleep(2.0)

            except Exception as e:
                print(f"  ✗ リトライ処理エラー: {e}")
                stats["errors"] += 1
                self.record_block_result(
                    screen_name,
                    user_id,
                    candidate["display_name"],
                    False,
                    0,
                    f"リトライ処理エラー: {str(e)}",
                    None,
                    retry_count,
                )
                continue

        print("\n" + "=" * 50)
        print("=== リトライ処理完了 ===")
        print(f"処理対象: {len(retry_candidates)}人")
        print(f"ブロック成功: {stats['blocked']}人")
        print(f"スキップ: {stats['skipped']}人")
        print(f"エラー: {stats['errors']}人")


def main():
    """メイン関数"""
    manager = BulkBlockManager()

    print("=== 一括ブロック管理システム ===")
    print()

    # 現在の状況を表示
    total_targets = len(manager.load_target_users())
    blocked_count = manager.get_blocked_users_count()
    remaining_count = len(manager.get_remaining_users())

    print(f"全対象ユーザー: {total_targets}人")
    print(f"既にブロック済み: {blocked_count}人")
    print(f"残り処理対象: {remaining_count}人")
    print()

    if remaining_count == 0:
        print("✓ 全てのユーザーが既にブロック済みです")
        return

    # テスト実行（最初の5人のみ）
    print("テスト実行: 最初の5人のみ処理します")
    manager.process_bulk_block(max_users=5, delay=2.0)

    # リトライ候補があるかチェック
    retry_candidates = manager.get_retry_candidates()
    if retry_candidates:
        print(f"\nリトライ候補が {len(retry_candidates)}人 います")
        print("リトライ処理を実行する場合: manager.process_retries()")
    else:
        print("\nリトライ候補はありません")


if __name__ == "__main__":
    main()
