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
        if detailed_stats["failed_max_retries"] > 0:
            print(f"  - リトライ上限到達: {detailed_stats['failed_max_retries']}人")
        if detailed_stats["failed_retryable"] > 0:
            print(f"  - リトライ可能: {detailed_stats['failed_retryable']}人")
        _show_failure_breakdown(manager)

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
    # ステータス別の内訳を取得
    status_counts = {}
    code_counts = {}
    
    for candidate in retry_candidates:
        user_status = candidate.get("user_status", "unknown")
        response_code = candidate.get("response_code")
        
        # ユーザーステータス別カウント
        if user_status != "unknown":
            status_counts[user_status] = status_counts.get(user_status, 0) + 1
        
        # HTTPステータスコード別カウント
        if response_code:
            code_counts[response_code] = code_counts.get(response_code, 0) + 1
    
    # ステータス別表示
    for status, count in status_counts.items():
        print(f"  - {status}: {count}人")
    
    # HTTPステータスコード別表示
    if code_counts:
        print("  - HTTPエラー:")
        for code, count in sorted(code_counts.items()):
            print(f"    {code}: {count}人")


def _show_failure_breakdown(manager: BulkBlockManager) -> None:
    """失敗の詳細内訳を表示"""
    breakdown = manager.database.get_failure_breakdown()
    
    # ユーザーステータス別の失敗
    if breakdown["by_status"]:
        print("  - ステータス別:")
        for status, count in breakdown["by_status"].items():
            print(f"    {status}: {count}人")
    
    # HTTPステータスコード別の失敗
    if breakdown["by_response_code"]:
        print("  - HTTPエラー別:")
        for code, count in sorted(breakdown["by_response_code"].items()):
            print(f"    {code}: {count}人")
    
    # エラータイプ別の失敗
    if breakdown["by_error_type"]:
        print("  - エラータイプ別:")
        for error_type, count in breakdown["by_error_type"].items():
            print(f"    {error_type}: {count}人")
        
        # otherが多い場合は実際のエラーメッセージのサンプルを表示
        if breakdown["by_error_type"].get("other", 0) > 0:
            print("  - エラーメッセージサンプル (other):")
            error_samples = manager.database.get_error_message_samples(5)
            for i, sample in enumerate(error_samples[:3], 1):
                print(f"    {i}. {sample}")
