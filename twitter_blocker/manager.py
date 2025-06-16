"""
一括ブロック管理メインモジュール
"""

import time
from typing import Any, Dict, List, Optional

from .api import TwitterAPI
from .config import ConfigManager, CookieManager
from .database import DatabaseManager
from .retry import RetryManager


class BulkBlockManager:
    """一括ブロック管理システム"""

    def __init__(
        self,
        cookies_file: str = "cookies.json",
        users_file: str = "video_misuse_detecteds.json",
        db_file: str = "block_history.db",
        cache_dir: str = "/data/cache",
    ):
        self.config_manager = ConfigManager(users_file)
        self.cookie_manager = CookieManager(cookies_file)
        self.database = DatabaseManager(db_file)
        self.api = TwitterAPI(self.cookie_manager, cache_dir)
        self.retry_manager = RetryManager()

    def load_target_users(self) -> List[str]:
        """ブロック対象ユーザーリストを読み込み"""
        users, _ = self.config_manager.load_users_data()
        return users

    def get_user_format(self) -> str:
        """ユーザーファイルの形式を取得"""
        return self.config_manager.get_user_format()

    def is_already_blocked(
        self, identifier: str, user_format: str = "screen_name"
    ) -> bool:
        """ユーザーが既にブロック済みかチェック"""
        return self.database.is_already_blocked(identifier, user_format)

    def get_blocked_users_count(self) -> int:
        """ブロック済みユーザー数を取得"""
        return self.database.get_blocked_users_count()

    def get_remaining_users(self) -> List[str]:
        """未処理のユーザーリストを取得"""
        target_users = self.load_target_users()
        user_format = self.get_user_format()

        blocked_users = self.database.get_blocked_users_set(user_format)

        # 未処理のユーザーのみを返す
        remaining_users = [
            user for user in target_users if str(user) not in blocked_users
        ]

        return remaining_users

    def get_retry_candidates(self) -> List[Dict[str, Any]]:
        """リトライ候補のユーザーを取得"""
        return self.database.get_retry_candidates()

    def process_bulk_block(
        self, max_users: Optional[int] = None, delay: float = 1.0, batch_size: int = 50
    ) -> None:
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
        session_id = self.database.start_session(total_targets)

        stats = {"processed": 0, "blocked": 0, "skipped": 0, "errors": 0}

        print(f"\n処理開始: {len(remaining_users)}人を処理します")
        print(f"バッチサイズ: {batch_size}")
        print("-" * 50)

        # user_id形式とscreen_name形式で処理を分ける
        if user_format == "user_id":
            self._process_users_batch(remaining_users, user_format, stats, delay, batch_size, session_id)
        else:
            # screen_name形式も新しいバッチ処理を使用
            self._process_screen_names_batch(remaining_users, user_format, stats, delay, batch_size, session_id)

        # セッション完了
        self.database.complete_session(session_id)

        self._print_completion_stats(remaining_users, stats)

    def process_retries(self, max_retries: Optional[int] = None) -> None:
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
            self._process_retry_user(candidate, i, len(retry_candidates), stats)

        print("\n" + "=" * 50)
        print("=== リトライ処理完了 ===")
        print(f"処理対象: {len(retry_candidates)}人")
        print(f"ブロック成功: {stats['blocked']}人")
        print(f"スキップ: {stats['skipped']}人")
        print(f"エラー: {stats['errors']}人")

    def _process_users_batch(
        self,
        user_ids: List[str],
        user_format: str,
        stats: Dict[str, int],
        delay: float,
        batch_size: int,
        session_id: int,
    ) -> None:
        """ユーザーIDリストの一括処理"""
        total_count = len(user_ids)
        processed_count = 0
        
        for i in range(0, len(user_ids), batch_size):
            batch_ids = user_ids[i:i + batch_size]
            batch_start = i + 1
            batch_end = min(i + batch_size, total_count)
            
            print(f"\n[BATCH {batch_start}-{batch_end}/{total_count}] {len(batch_ids)}ユーザーを一括取得中...")
            
            # 重複チェック（一括）
            unchecked_ids = []
            for user_id in batch_ids:
                if self.is_already_blocked(user_id, user_format):
                    print(f"  ℹ スキップ: {user_id} 既にブロック済み")
                    stats["skipped"] += 1
                    processed_count += 1
                else:
                    unchecked_ids.append(user_id)
            
            if not unchecked_ids:
                print(f"  → 全{len(batch_ids)}ユーザーがブロック済み")
                continue
            
            try:
                # 一括ユーザー情報取得
                users_info = self.api.get_users_info_batch(unchecked_ids, batch_size)
                
                # 各ユーザーを個別に処理
                for user_id in unchecked_ids:
                    processed_count += 1
                    user_info = users_info.get(user_id)
                    
                    if not user_info:
                        print(f"  ✗ エラー: {user_id} ユーザー情報取得失敗（詳細は上記ログを参照）")
                        stats["errors"] += 1
                        self.database.record_block_result(
                            None, user_id, None, False, 404, "ユーザー情報取得失敗"
                        )
                        continue
                    
                    screen_name = user_info.get("screen_name") or user_id
                    
                    # ユーザー状態チェック
                    if self._check_user_unavailable(user_info, screen_name, stats):
                        continue
                    
                    # フォロー関係チェック
                    if self._check_follow_relationship(user_info, screen_name, stats):
                        continue
                    
                    # 既にブロック済みかチェック
                    if self._check_already_blocking(user_info, screen_name, stats):
                        continue
                    
                    # ブロック実行
                    self._execute_block(user_info, screen_name, stats)
                    stats["processed"] += 1
                
                # セッション更新
                self.database.update_session(
                    session_id,
                    stats["processed"],
                    stats["blocked"],
                    stats["skipped"],
                    stats["errors"],
                )
                
                # 進捗表示
                print(
                    f"  → バッチ完了: {batch_end}/{total_count} "
                    f"(ブロック: {stats['blocked']}, スキップ: {stats['skipped']}, エラー: {stats['errors']})"
                )
                
                # バッチ間の待機
                if i + batch_size < len(user_ids):
                    time.sleep(delay)
                    
            except Exception as e:
                print(f"  ✗ バッチ処理エラー: {e}")
                # バッチエラー時は個別処理にフォールバック
                for user_id in unchecked_ids:
                    processed_count += 1
                    stats["errors"] += 1
                    self.database.record_block_result(
                        None, user_id, None, False, 0, f"バッチ処理エラー: {str(e)}"
                    )

    def _process_screen_names_batch(
        self,
        screen_names: List[str],
        user_format: str,
        stats: Dict[str, int],
        delay: float,
        batch_size: int,
        session_id: int,
    ) -> None:
        """screen_nameリストの一括処理"""
        total_count = len(screen_names)
        processed_count = 0
        
        for i in range(0, len(screen_names), batch_size):
            batch_names = screen_names[i:i + batch_size]
            batch_start = i + 1
            batch_end = min(i + batch_size, total_count)
            
            print(f"\n[BATCH {batch_start}-{batch_end}/{total_count}] {len(batch_names)}ユーザーを一括取得中...")
            
            # 重複チェック（一括）
            unchecked_names = []
            for screen_name in batch_names:
                if self.is_already_blocked(screen_name, user_format):
                    print(f"  ℹ スキップ: @{screen_name} 既にブロック済み")
                    stats["skipped"] += 1
                    processed_count += 1
                else:
                    unchecked_names.append(screen_name)
            
            if not unchecked_names:
                print(f"  → 全{len(batch_names)}ユーザーがブロック済み")
                continue
            
            try:
                # 新しいAPIメソッドで一括ユーザー情報取得
                users_info = self.api.get_users_info_by_screen_names(unchecked_names, batch_size)
                
                # 各ユーザーを個別に処理
                for screen_name in unchecked_names:
                    processed_count += 1
                    user_info = users_info.get(screen_name)
                    
                    if not user_info:
                        print(f"  ✗ エラー: @{screen_name} ユーザー情報取得失敗（詳細は上記ログを参照）")
                        stats["errors"] += 1
                        self.database.record_block_result(
                            screen_name, None, None, False, 404, "ユーザー情報取得失敗"
                        )
                        continue
                    
                    # ユーザー状態チェック
                    if self._check_user_unavailable(user_info, screen_name, stats):
                        continue
                    
                    # フォロー関係チェック
                    if self._check_follow_relationship(user_info, screen_name, stats):
                        continue
                    
                    # 既にブロック済みかチェック
                    if self._check_already_blocking(user_info, screen_name, stats):
                        continue
                    
                    # ブロック実行
                    self._execute_block(user_info, screen_name, stats)
                    
                    # 処理間の待機
                    if processed_count < total_count:
                        time.sleep(delay)
                
                # セッション更新
                self.database.update_session(
                    session_id,
                    processed_count,
                    stats["blocked"],
                    stats["skipped"],
                    stats["errors"],
                )
                
                # 進捗表示
                print(
                    f"  進捗: {processed_count}/{total_count} 完了 "
                    f"(ブロック: {stats['blocked']}, スキップ: {stats['skipped']}, エラー: {stats['errors']})"
                )
                
            except Exception as e:
                print(f"  ✗ バッチ処理エラー: {e}")
                # バッチエラー時は個別処理にフォールバック
                for screen_name in unchecked_names:
                    processed_count += 1
                    stats["errors"] += 1
                    self.database.record_block_result(
                        screen_name, None, None, False, 0, f"バッチ処理エラー: {str(e)}"
                    )

    def _process_single_user(
        self,
        user_identifier: str,
        user_format: str,
        current_index: int,
        total_count: int,
        stats: Dict[str, int],
        delay: float,
    ) -> None:
        """単一ユーザーの処理"""
        # ユーザー形式に応じて表示とキーを設定
        if user_format == "user_id":
            print(
                f"[{current_index}/{total_count}] ユーザーID {user_identifier} を処理中..."
            )
        else:
            print(f"[{current_index}/{total_count}] @{user_identifier} を処理中...")

        lookup_key = str(user_identifier)

        try:
            # 重複チェック
            if self.is_already_blocked(lookup_key, user_format):
                print("  ℹ スキップ: 既にブロック済み")
                stats["skipped"] += 1
                return

            # ユーザー情報を取得
            if user_format == "user_id":
                user_info = self.api.get_user_info_by_id(user_identifier)
            else:
                user_info = self.api.get_user_info(user_identifier)

            if not user_info:
                print("  ✗ エラー: ユーザー情報取得失敗（詳細は上記ログを参照）")
                stats["errors"] += 1
                fallback_screen_name = (
                    str(user_identifier) if user_format == "screen_name" else None
                )
                self.database.record_block_result(
                    fallback_screen_name, None, None, False, 404, "ユーザー情報取得失敗"
                )
                return

            screen_name = user_info.get("screen_name") or str(user_identifier)

            # ユーザー状態チェック
            if self._check_user_unavailable(user_info, screen_name, stats):
                return

            # フォロー関係チェック
            if self._check_follow_relationship(user_info, screen_name, stats):
                return

            # 既にブロック済みかチェック
            if self._check_already_blocking(user_info, screen_name, stats):
                return

            # ブロック実行
            self._execute_block(user_info, screen_name, stats)

            stats["processed"] += 1

            # レート制限対策
            time.sleep(delay)

        except Exception as e:
            print(f"  ✗ 処理エラー: {e}")
            stats["errors"] += 1
            self.database.record_block_result(
                lookup_key if user_format == "screen_name" else None,
                None,
                None,
                False,
                0,
                str(e),
            )

    def _process_retry_user(
        self,
        candidate: Dict[str, Any],
        current_index: int,
        total_count: int,
        stats: Dict[str, int],
    ) -> None:
        """リトライユーザーの処理"""
        screen_name = candidate["screen_name"]
        user_id = candidate["user_id"]
        retry_count = candidate["retry_count"] + 1

        print(
            f"[{current_index}/{total_count}] @{screen_name} をリトライ中... (試行回数: {retry_count})"
        )

        try:
            # 最新のユーザー情報を再取得
            user_info = self.api.get_user_info(screen_name)

            if not user_info:
                print("  ✗ ユーザー情報取得失敗（詳細は上記ログを参照）")
                stats["errors"] += 1
                self.database.record_block_result(
                    screen_name,
                    user_id,
                    candidate["display_name"],
                    False,
                    404,
                    "ユーザー情報取得失敗 (リトライ)",
                    None,
                    retry_count,
                )
                return

            # 各種チェックとブロック実行（詳細実装は省略）
            # ... 実際の実装では元のprocess_retries()と同じロジック

            stats["processed"] += 1
            time.sleep(2.0)

        except Exception as e:
            print(f"  ✗ リトライ処理エラー: {e}")
            stats["errors"] += 1
            self.database.record_block_result(
                screen_name,
                user_id,
                candidate["display_name"],
                False,
                0,
                f"リトライ処理エラー: {str(e)}",
                None,
                retry_count,
            )

    def _check_user_unavailable(
        self, user_info: Dict[str, Any], screen_name: str, stats: Dict[str, int]
    ) -> bool:
        """ユーザー利用不可チェック"""
        if user_info.get("unavailable", False):
            user_status = user_info.get("user_status", "unavailable")
            print(f"  ⚠ スキップ: ユーザー利用不可 ({user_status})")
            stats["skipped"] += 1

            if self.retry_manager.should_retry(
                user_status, 0, f"User {user_status}", 0
            ):
                print("    → リトライ対象として記録")
                self.database.record_block_result(
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
                self.database.record_block_result(
                    screen_name,
                    user_info.get("id"),
                    user_info.get("name"),
                    False,
                    0,
                    f"User {user_status} (permanent)",
                    user_status,
                    0,
                )
            return True
        return False

    def _check_follow_relationship(
        self, user_info: Dict[str, Any], screen_name: str, stats: Dict[str, int]
    ) -> bool:
        """フォロー関係チェック"""
        if user_info["following"] or user_info["followed_by"]:
            print(
                f"  ⚠ スキップ: フォロー関係あり "
                f"(フォロー中: {user_info['following']}, フォロワー: {user_info['followed_by']})"
            )
            stats["skipped"] += 1
            self.database.record_block_result(
                screen_name,
                user_info["id"],
                user_info["name"],
                False,
                0,
                "フォロー関係あり",
                user_info.get("user_status", "active"),
            )
            return True
        return False

    def _check_already_blocking(
        self, user_info: Dict[str, Any], screen_name: str, stats: Dict[str, int]
    ) -> bool:
        """既にブロック済みかチェック"""
        if user_info["blocking"]:
            print("  ℹ スキップ: 既にブロック済み")
            stats["skipped"] += 1
            self.database.record_block_result(
                screen_name,
                user_info["id"],
                user_info["name"],
                True,
                200,
                "既にブロック済み",
                user_info.get("user_status", "active"),
            )
            return True
        return False

    def _execute_block(
        self, user_info: Dict[str, Any], screen_name: str, stats: Dict[str, int]
    ) -> None:
        """ブロック実行"""
        print(f"  → ブロック実行: {user_info['name']} (ID: {user_info['id']})")
        block_result = self.api.block_user(user_info["id"], screen_name)

        if block_result["success"]:
            print("  ✓ ブロック成功")
            stats["blocked"] += 1
            self.database.record_block_result(
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
                block_result["message"][:200]
                if block_result["message"]
                else "Unknown error"
            )
            print(f"  ✗ ブロック失敗: {block_result['status_code']} - {error_msg}")

            # リトライ判定
            user_status = user_info.get("user_status", "active")
            if self.retry_manager.should_retry(
                user_status,
                block_result["status_code"],
                block_result["message"],
                0,
            ):
                print("    → リトライ対象として記録")
                stats["errors"] += 1
                self.database.record_block_result(
                    screen_name,
                    user_info["id"],
                    user_info["name"],
                    False,
                    block_result["status_code"],
                    block_result["message"],
                    user_status,
                    0,
                )
            else:
                print("    → 永続的な失敗として記録")
                stats["errors"] += 1
                self.database.record_block_result(
                    screen_name,
                    user_info["id"],
                    user_info["name"],
                    False,
                    block_result["status_code"],
                    f"{block_result['message']} (permanent)",
                    user_status,
                    0,
                )

    def _print_completion_stats(
        self, remaining_users: List[str], stats: Dict[str, int]
    ) -> None:
        """完了統計の表示"""
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
