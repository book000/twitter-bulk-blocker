"""
リトライ管理モジュール
"""

from typing import Any, Dict


class RetryManager:
    """リトライ判定と管理クラス"""

    # 永続的な失敗（リトライ不要）
    PERMANENT_FAILURES = [
        "not_found",  # ユーザーが存在しない
        "deactivated",  # アカウント無効化
        "suspended",  # アカウント凍結（リトライ対象から除外）
    ]

    # 一時的な失敗（リトライ対象）
    TEMPORARY_FAILURES = [
        "unavailable",  # 一時的に利用不可
    ]

    # HTTPステータスコードによるリトライ対象
    RETRYABLE_STATUS_CODES = [
        429,  # Rate limit
        500,  # Internal server error
        502,  # Bad gateway
        503,  # Service unavailable
        504,  # Gateway timeout
    ]

    # エラーメッセージによるリトライ対象
    RETRYABLE_MESSAGES = [
        "temporarily unavailable",
        "rate limit",
        "timeout",
        "server error",
    ]

    MAX_RETRIES = 3

    def should_retry(
        self,
        user_status: str,
        status_code: int,
        error_message: str,
        retry_count: int,
    ) -> bool:
        """リトライすべきかどうかを判定"""
        # リトライ回数上限チェック
        if retry_count >= self.MAX_RETRIES:
            return False

        # 永続的な失敗
        if user_status in self.PERMANENT_FAILURES:
            return False

        # 一時的な失敗
        if user_status in self.TEMPORARY_FAILURES:
            return True

        # HTTPステータスコードによる判定
        if status_code in self.RETRYABLE_STATUS_CODES:
            return True

        # エラーメッセージによる判定
        if error_message:
            error_lower = error_message.lower()
            for msg in self.RETRYABLE_MESSAGES:
                if msg in error_lower:
                    return True

        return False

    def get_retry_delay(self, retry_count: int, base_delay: int = 30) -> int:
        """リトライ間隔を計算（指数バックオフ）"""
        return base_delay * (2**retry_count)
