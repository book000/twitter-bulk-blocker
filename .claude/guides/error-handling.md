# エラーハンドリング完全ガイド

## エラー分類体系

### 永続的失敗（リトライ禁止）
```python
PERMANENT_FAILURES = {
    "suspended": {
        "description": "アカウント凍結",
        "action": "スキップ・記録",
        "retry": False,
        "user_status": "suspended"
    },
    "not_found": {
        "description": "ユーザー削除済み・存在しない",
        "action": "スキップ・記録", 
        "retry": False,
        "user_status": "not_found"
    },
    "deactivated": {
        "description": "アカウント無効化",
        "action": "スキップ・記録",
        "retry": False,
        "user_status": "deactivated"
    }
}

def is_permanent_failure(error_response):
    user_status = error_response.get("user_status")
    return user_status in PERMANENT_FAILURES
```

### 一時的失敗（リトライ対象）
```python
TEMPORARY_FAILURES = {
    "rate_limit": {
        "http_code": 429,
        "wait_time": "header_based",
        "max_retries": 3,
        "exponential_backoff": True
    },
    "server_error": {
        "http_codes": [500, 502, 503, 504],
        "wait_time": 60,
        "max_retries": 2,
        "exponential_backoff": False
    },
    "network_timeout": {
        "exceptions": ["requests.exceptions.Timeout", "requests.exceptions.ConnectionError"],
        "wait_time": 30,
        "max_retries": 3,
        "exponential_backoff": True
    }
}
```

### 認証エラー（特別処理）
```python
AUTH_ERRORS = {
    "invalid_token": {
        "http_code": 401,
        "action": "clear_cache_and_retry_once",
        "auto_recovery": True
    },
    "csrf_token_mismatch": {
        "description": "CSRFトークンの不整合",
        "action": "cookie_refresh_required",
        "auto_recovery": False
    }
}

def handle_auth_error(self):
    """認証エラー時の回復処理"""
    self._login_user_id = None
    self.cookie_manager.clear_cache()
    time.sleep(2)
    
    # 1回だけ自動回復試行
    if not self._auth_retry_attempted:
        self._auth_retry_attempted = True
        return "retry"
    return "abort"
```

## エラー検出パターン

### GraphQLエラー解析
```python
def parse_graphql_errors(response_json):
    """GraphQLレスポンスからエラー情報を抽出"""
    errors = response_json.get("errors", [])
    
    for error in errors:
        # ユーザー状態エラー
        if "user_status" in error:
            return {
                "type": "user_status_error",
                "status": error["user_status"],
                "permanent": error["user_status"] in PERMANENT_FAILURES
            }
        
        # レート制限エラー  
        if "rate limit" in error.get("message", "").lower():
            return {
                "type": "rate_limit",
                "reset_time": error.get("extensions", {}).get("rateLimitReset")
            }
        
        # その他のGraphQLエラー
        return {
            "type": "graphql_error",
            "message": error.get("message"),
            "code": error.get("code")
        }
    
    return None
```

### HTTPステータス別処理
```python
def handle_http_error(status_code, response):
    """HTTPステータスコード別エラーハンドリング"""
    
    if status_code == 401:
        return handle_auth_error(response)
    elif status_code == 403:
        return handle_forbidden_error(response)
    elif status_code == 429:
        return handle_rate_limit(response)
    elif 500 <= status_code < 600:
        return handle_server_error(status_code, response)
    else:
        return handle_unknown_error(status_code, response)

def calculate_retry_delay(attempt_count, base_delay=60):
    """指数バックオフによる待機時間計算"""
    if attempt_count <= 0:
        return base_delay
    
    # 指数バックオフ: base_delay * (2 ^ attempt_count)
    delay = base_delay * (2 ** (attempt_count - 1))
    
    # 最大15分まで
    return min(delay, 900)
```

## リトライ戦略

### 統合リトライマネージャー
```python
class RetryManager:
    def __init__(self):
        self.attempt_counts = {}
        self.last_attempt_times = {}
    
    def should_retry(self, operation_id, error_info):
        """リトライ可能かどうかの判定"""
        
        # 永続的失敗は即座に拒否
        if error_info.get("permanent"):
            return False
        
        # 試行回数チェック
        attempts = self.attempt_counts.get(operation_id, 0)
        max_retries = error_info.get("max_retries", 3)
        
        if attempts >= max_retries:
            return False
        
        # 時間間隔チェック（連続リトライ防止）
        last_attempt = self.last_attempt_times.get(operation_id, 0)
        min_interval = error_info.get("min_retry_interval", 60)
        
        if time.time() - last_attempt < min_interval:
            return False
        
        return True
    
    def record_attempt(self, operation_id):
        """リトライ試行の記録"""
        self.attempt_counts[operation_id] = self.attempt_counts.get(operation_id, 0) + 1
        self.last_attempt_times[operation_id] = time.time()
    
    def reset_attempts(self, operation_id):
        """成功時のリセット"""
        self.attempt_counts.pop(operation_id, None)
        self.last_attempt_times.pop(operation_id, None)
```

### 操作別リトライ設定
```python
RETRY_CONFIGS = {
    "user_lookup": {
        "max_retries": 3,
        "base_delay": 60,
        "exponential_backoff": True,
        "permanent_failure_check": True
    },
    "block_user": {
        "max_retries": 2,
        "base_delay": 30,
        "exponential_backoff": False,
        "permanent_failure_check": False
    },
    "batch_operation": {
        "max_retries": 5,
        "base_delay": 120,
        "exponential_backoff": True,
        "partial_retry": True  # バッチの一部のみリトライ
    }
}
```

## エラーロギング

### 構造化ログ出力
```python
import json
import datetime

def log_error(error_type, error_details, context=None):
    """構造化エラーログの出力"""
    
    log_entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "error_type": error_type,
        "error_details": error_details,
        "context": context or {},
        "severity": determine_severity(error_type)
    }
    
    # コンソール出力（見やすい形式）
    print(f"🚨 {error_type}: {error_details.get('message', 'Unknown error')}")
    
    # ファイル出力（JSON形式）
    with open("error_log.jsonl", "a") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

def determine_severity(error_type):
    """エラータイプから重要度を判定"""
    if error_type in ["permanent_failure", "auth_error"]:
        return "high"
    elif error_type in ["rate_limit", "server_error"]:
        return "medium"
    else:
        return "low"
```

### エラー統計の収集
```python
class ErrorStats:
    def __init__(self):
        self.error_counts = {}
        self.error_rates = {}
        self.start_time = time.time()
    
    def record_error(self, error_type):
        """エラー発生の記録"""
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1
    
    def get_error_summary(self):
        """エラー統計サマリー"""
        total_time = time.time() - self.start_time
        total_errors = sum(self.error_counts.values())
        
        return {
            "total_errors": total_errors,
            "error_rate": total_errors / (total_time / 3600),  # エラー/時
            "error_breakdown": self.error_counts,
            "most_common_error": max(self.error_counts.items(), key=lambda x: x[1]) if self.error_counts else None
        }
```

## 回復戦略

### 自動回復メカニズム
```python
def auto_recovery_workflow(error_info, context):
    """エラータイプに応じた自動回復処理"""
    
    if error_info["type"] == "auth_error":
        return recover_from_auth_error()
    elif error_info["type"] == "rate_limit":
        return recover_from_rate_limit(error_info)
    elif error_info["type"] == "network_error":
        return recover_from_network_error()
    else:
        return {"action": "manual_intervention_required"}

def recover_from_auth_error():
    """認証エラーからの自動回復"""
    steps = [
        "clear_cookie_cache",
        "wait_2_seconds", 
        "retry_once_only"
    ]
    return {"action": "auto_recovery", "steps": steps}

def recover_from_rate_limit(error_info):
    """レート制限からの回復"""
    reset_time = error_info.get("reset_time")
    if reset_time:
        wait_seconds = max(reset_time - int(time.time()), 60)
        return {"action": "wait_and_retry", "wait_seconds": wait_seconds}
    else:
        return {"action": "wait_and_retry", "wait_seconds": 300}
```

## エラー予防策

### プリフライトチェック
```python
def preflight_checks():
    """実行前の事前チェック"""
    checks = {
        "auth_status": verify_authentication(),
        "rate_limit_status": check_rate_limits(), 
        "network_connectivity": test_network_connection(),
        "file_permissions": verify_file_access(),
        "disk_space": check_disk_space()
    }
    
    failures = [k for k, v in checks.items() if not v]
    
    if failures:
        print(f"⚠️ 事前チェック失敗: {', '.join(failures)}")
        return False
    
    print("✅ 事前チェック完了")
    return True
```

### 早期警告システム
```python
def check_warning_conditions():
    """警告レベルの問題検出"""
    warnings = []
    
    # レート制限残量チェック
    if get_rate_limit_remaining() < 10:
        warnings.append("rate_limit_low")
    
    # 連続エラー率チェック
    if get_recent_error_rate() > 0.1:  # 10%以上
        warnings.append("high_error_rate")
    
    # ディスク容量チェック
    if get_disk_usage() > 0.9:  # 90%以上
        warnings.append("disk_space_low")
    
    return warnings
```