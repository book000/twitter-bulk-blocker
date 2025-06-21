"""
リトライ管理モジュール
"""

import time
from typing import Any, Dict, Optional, Tuple
from datetime import datetime, timedelta


class ErrorClassifier:
    """HTTP 403エラーの詳細分類クラス"""
    
    # 403エラーの詳細分類
    ERROR_TYPES = {
        "RATE_LIMIT": "rate_limit",           # レート制限
        "AUTH_REQUIRED": "auth_required",     # 認証必須
        "PERMISSION_DENIED": "permission_denied", # 権限不足
        "ACCOUNT_RESTRICTED": "account_restricted", # アカウント制限
        "HEADER_ISSUE": "header_issue",       # ヘッダー問題
        "UNKNOWN_403": "unknown_403",         # 未分類403エラー
        "ANTI_BOT": "anti_bot",               # アンチボット検出
        "IP_BLOCKED": "ip_blocked",           # IP制限
    }
    
    @staticmethod
    def classify_403_error(response_text: str = "", headers: Dict[str, str] = None, 
                          status_code: int = 403) -> Tuple[str, str, int]:
        """403エラーを詳細に分類
        
        Returns:
            Tuple[error_type, description, priority_level]
            priority_level: 1=即座に修正可能, 2=調整必要, 3=深刻な問題
        """
        if status_code != 403:
            return "NOT_403", "Not a 403 error", 0
        
        response_lower = response_text.lower() if response_text else ""
        headers = headers or {}
        
        # レート制限の検出
        if ("rate limit" in response_lower or 
            "too many requests" in response_lower or
            headers.get("x-rate-limit-remaining") == "0"):
            return ErrorClassifier.ERROR_TYPES["RATE_LIMIT"], "API rate limit exceeded", 1
        
        # 認証関連エラー
        if ("authorization" in response_lower or 
            "authenticate" in response_lower or
            "invalid token" in response_lower or
            "credential" in response_lower):
            return ErrorClassifier.ERROR_TYPES["AUTH_REQUIRED"], "Authentication required or invalid", 2
        
        # 権限不足
        if ("permission" in response_lower or 
            "access denied" in response_lower or
            "not authorized" in response_lower or
            "forbidden" in response_lower):
            return ErrorClassifier.ERROR_TYPES["PERMISSION_DENIED"], "Insufficient permissions", 2
        
        # アカウント制限
        if ("account" in response_lower and 
            ("restricted" in response_lower or "limited" in response_lower or
             "suspended" in response_lower or "locked" in response_lower)):
            return ErrorClassifier.ERROR_TYPES["ACCOUNT_RESTRICTED"], "Account restrictions detected", 3
        
        # ヘッダー関連問題
        if ("header" in response_lower or 
            "user-agent" in response_lower or
            "missing" in response_lower and "required" in response_lower):
            return ErrorClassifier.ERROR_TYPES["HEADER_ISSUE"], "Header validation failed", 1
        
        # アンチボット検出
        if ("bot" in response_lower or 
            "automated" in response_lower or
            "suspicious" in response_lower or
            "unusual activity" in response_lower or
            "verification" in response_lower):
            return ErrorClassifier.ERROR_TYPES["ANTI_BOT"], "Anti-bot system triggered", 2
        
        # IP制限
        if ("ip" in response_lower and 
            ("blocked" in response_lower or "restricted" in response_lower)):
            return ErrorClassifier.ERROR_TYPES["IP_BLOCKED"], "IP address blocked or restricted", 3
        
        # Unknown error (Twitter特有)
        if "unknown error" in response_lower:
            return ErrorClassifier.ERROR_TYPES["UNKNOWN_403"], "Twitter Unknown Error - likely anti-bot", 2
        
        # その他の403エラー
        return ErrorClassifier.ERROR_TYPES["UNKNOWN_403"], "Unclassified 403 Forbidden error", 2


class AdaptiveBackoffStrategy:
    """適応的バックオフ戦略クラス"""
    
    def __init__(self):
        self.error_history = []  # (timestamp, error_type, success) のタプルリスト
        self.success_rate_window = 300  # 5分間の成功率を計算
        
    def calculate_backoff_delay(self, error_type: str, retry_count: int, 
                              base_delay: int = 30) -> int:
        """エラータイプと履歴に基づく適応的バックオフ計算"""
        
        # エラータイプ別の基本乗数
        type_multipliers = {
            "rate_limit": 2.0,        # レート制限は長めに
            "auth_required": 1.5,     # 認証エラーは中程度
            "permission_denied": 1.0, # 権限エラーは標準
            "account_restricted": 3.0, # アカウント制限は長期
            "header_issue": 0.5,      # ヘッダー問題は短め
            "unknown_403": 2.5,       # Unknown errorは長め
            "anti_bot": 3.0,          # アンチボットは長期
            "ip_blocked": 4.0,        # IP制限は最長
        }
        
        # 成功率による調整
        success_rate = self._calculate_recent_success_rate(error_type)
        success_multiplier = 1.0
        if success_rate < 0.3:  # 成功率30%未満
            success_multiplier = 2.0
        elif success_rate < 0.5:  # 成功率50%未満
            success_multiplier = 1.5
        elif success_rate > 0.8:  # 成功率80%超
            success_multiplier = 0.8
        
        # 基本計算
        base_multiplier = type_multipliers.get(error_type, 1.0)
        exponential_factor = min(2 ** retry_count, 8)  # 最大8倍まで
        
        total_delay = int(base_delay * base_multiplier * exponential_factor * success_multiplier)
        
        # 上限・下限の設定
        min_delay = 5 if error_type == "header_issue" else 10
        max_delay = 1800 if error_type in ["ip_blocked", "account_restricted"] else 600
        
        return max(min_delay, min(total_delay, max_delay))
    
    def _calculate_recent_success_rate(self, error_type: str) -> float:
        """指定エラータイプの最近の成功率を計算"""
        current_time = time.time()
        cutoff_time = current_time - self.success_rate_window
        
        # 指定時間内の該当エラータイプの履歴を抽出
        relevant_history = [
            entry for entry in self.error_history 
            if entry[0] >= cutoff_time and entry[1] == error_type
        ]
        
        if not relevant_history:
            return 0.5  # デフォルト50%
        
        success_count = sum(1 for entry in relevant_history if entry[2])  # success flag
        return success_count / len(relevant_history)
    
    def record_attempt(self, error_type: str, success: bool):
        """試行結果を記録"""
        current_time = time.time()
        self.error_history.append((current_time, error_type, success))
        
        # 古い履歴を削除（メモリ効率化）
        cutoff_time = current_time - self.success_rate_window * 2  # 10分間保持
        self.error_history = [
            entry for entry in self.error_history if entry[0] >= cutoff_time
        ]


class RetryManager:
    """リトライ判定と管理クラス（403エラー強化版）"""

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
        403,  # Forbidden (Twitter API一時的制限、Unknown error含む)
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
        "unknown error",  # Twitter API 403 Unknown error
    ]

    MAX_RETRIES = 10
    
    def __init__(self):
        self.error_classifier = ErrorClassifier()
        self.backoff_strategy = AdaptiveBackoffStrategy()

    def should_retry(
        self,
        user_status: str,
        status_code: int,
        error_message: str,
        retry_count: int,
        response_text: str = "",
        response_headers: Dict[str, str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """リトライすべきかどうかを判定（403エラー強化版）
        
        Returns:
            Tuple[should_retry: bool, error_classification: Optional[str]]
        """
        # リトライ回数上限チェック
        if retry_count >= self.MAX_RETRIES:
            return False, "max_retries_exceeded"

        # 永続的な失敗
        if user_status in self.PERMANENT_FAILURES:
            return False, "permanent_failure"

        # 一時的な失敗
        if user_status in self.TEMPORARY_FAILURES:
            return True, "temporary_failure"

        # 403エラーの詳細分類
        if status_code == 403:
            error_type, description, priority = self.error_classifier.classify_403_error(
                response_text=response_text,
                headers=response_headers,
                status_code=status_code
            )
            
            # 分類に基づくリトライ判定
            non_retryable_types = ["account_restricted", "ip_blocked"]
            if error_type in non_retryable_types and priority >= 3:
                return False, error_type
            
            # その他の403エラーはリトライ対象
            return True, error_type
        
        # HTTPステータスコードによる判定（403以外）
        if status_code and status_code in self.RETRYABLE_STATUS_CODES:
            return True, f"status_code_{status_code}"

        # エラーメッセージによる判定
        if error_message:
            error_lower = error_message.lower()
            for msg in self.RETRYABLE_MESSAGES:
                if msg in error_lower:
                    return True, "message_based_retry"
            
            # 日本語エラーメッセージの判定
            if "ユーザー情報取得失敗" in error_message:
                return True, "japanese_error_message"

        # status_codeがNullで特定のエラーパターンでない場合はリトライ対象
        if status_code is None and error_message and "permanent" not in error_message.lower():
            return True, "null_status_retry"

        return False, "no_retry_condition_met"

    def get_retry_delay(self, retry_count: int, base_delay: int = 30, status_code: int = None, 
                       error_message: str = "", error_classification: str = "", 
                       response_text: str = "", response_headers: Dict[str, str] = None) -> int:
        """リトライ間隔を計算（適応的バックオフ強化版）"""
        # 403エラーの詳細分類に基づく適応的バックオフ
        if status_code == 403 and error_classification:
            return self.backoff_strategy.calculate_backoff_delay(
                error_classification, retry_count, base_delay
            )
        
        # Twitter API 403 Unknown errorの従来対応（フォールバック）
        if status_code == 403 and "unknown error" in error_message.lower():
            return base_delay * 3 * (2**retry_count)  # 通常の3倍の間隔
        
        # その他のエラーは通常の指数バックオフ
        return base_delay * (2**retry_count)
    
    def record_retry_result(self, error_classification: str, success: bool):
        """リトライ結果を記録（学習用）"""
        if error_classification:
            self.backoff_strategy.record_attempt(error_classification, success)
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """エラー統計情報を取得"""
        current_time = time.time()
        recent_errors = [
            entry for entry in self.backoff_strategy.error_history 
            if current_time - entry[0] <= 300  # 直近5分間
        ]
        
        if not recent_errors:
            return {"total_attempts": 0, "success_rate": 0.0, "error_types": {}}
        
        # エラータイプ別集計
        error_type_stats = {}
        for _, error_type, success in recent_errors:
            if error_type not in error_type_stats:
                error_type_stats[error_type] = {"total": 0, "success": 0}
            error_type_stats[error_type]["total"] += 1
            if success:
                error_type_stats[error_type]["success"] += 1
        
        # 成功率計算
        total_success = sum(1 for entry in recent_errors if entry[2])
        overall_success_rate = total_success / len(recent_errors)
        
        return {
            "total_attempts": len(recent_errors),
            "success_rate": overall_success_rate,
            "error_types": error_type_stats,
            "time_window_minutes": 5
        }
