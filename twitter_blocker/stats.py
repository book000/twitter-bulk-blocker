"""
統計表示モジュール
"""

from typing import Any, Dict, List

from .manager import BulkBlockManager


def show_stats(manager: BulkBlockManager) -> None:
    """現在の処理統計を表示"""
    total_targets = len(manager.load_target_users())
    blocked_count = manager.get_blocked_users_count()
    remaining_count = len(manager.get_remaining_users())
    retry_candidates = manager.get_retry_candidates()

    # データベースから詳細統計を取得
    detailed_stats = manager.database.get_detailed_stats()

    print("=== 処理統計 ===")
    print(f"全対象ユーザー: {total_targets:,}人")
    print(f"ブロック済み: {blocked_count:,}人 ({blocked_count/total_targets*100:.1f}%)")
    print(f"残り未処理: {remaining_count:,}人")

    if detailed_stats["failed"] > 0:
        print(f"失敗: {detailed_stats['failed']}人")

    if detailed_stats["follow_relationship"] > 0:
        print(f"フォロー関係でスキップ: {detailed_stats['follow_relationship']}人")

    if detailed_stats["suspended"] > 0:
        print(f"suspended: {detailed_stats['suspended']}人")

    if detailed_stats["unavailable"] > 0:
        print(f"利用不可: {detailed_stats['unavailable']}人")

    if len(retry_candidates) > 0:
        print(f"\nリトライ候補: {len(retry_candidates)}人")
        _show_retry_details(retry_candidates)


def _show_retry_details(retry_candidates: List[Dict[str, Any]]) -> None:
    """リトライ候補の詳細表示"""
    suspended_retries = len(
        [c for c in retry_candidates if c.get("user_status") == "suspended"]
    )
    error_retries = len(
        [c for c in retry_candidates if c.get("user_status") != "suspended"]
    )

    if suspended_retries > 0:
        print(f"  - suspended: {suspended_retries}人")
    if error_retries > 0:
        print(f"  - その他エラー: {error_retries}人")
