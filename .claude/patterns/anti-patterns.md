# アンチパターン（回避すべき実装）

## パフォーマンスアンチパターン

### N+1クエリ問題
```python
# ❌ 避ける: ループ内での個別クエリ
def get_user_statuses_bad(self, user_list):
    results = {}
    for user_id in user_list:
        # 個別にDB問い合わせ（N+1問題）
        if self.database.is_permanent_failure(user_id):
            results[user_id] = "permanent_failure"
        else:
            # 個別にAPI呼び出し（さらに問題）
            results[user_id] = self.api.get_user_status(user_id)
    return results

# ✅ 正しい: バッチ処理
def get_user_statuses_good(self, user_list):
    # 1. バッチでDB問い合わせ
    permanent_failures = self.database.get_permanent_failures_batch(user_list)
    
    # 2. 処理対象を絞り込み
    processable_users = [u for u in user_list if u not in permanent_failures]
    
    # 3. バッチでAPI呼び出し
    api_results = self.api.get_user_statuses_batch(processable_users)
    
    # 4. 結果をマージ
    results = {}
    results.update({k: "permanent_failure" for k in permanent_failures})
    results.update(api_results)
    return results
```

### 過度な同期処理
```python
# ❌ 避ける: 逐次処理で時間浪費
def process_users_sequentially_bad(self, user_list):
    results = []
    for user in user_list:
        time.sleep(1)  # API制限対策で待機
        result = self.api.process_user(user)
        results.append(result)
        # 1000ユーザーなら1000秒（16分）かかる
    return results

# ✅ 正しい: バッチ処理で効率化
def process_users_batch_good(self, user_list):
    batch_size = 50
    results = []
    
    for i in range(0, len(user_list), batch_size):
        batch = user_list[i:i + batch_size]
        batch_results = self.api.process_users_batch(batch)
        results.extend(batch_results)
        time.sleep(1)  # バッチ間の待機のみ
        # 1000ユーザーなら20秒で完了
    
    return results
```

## エラーハンドリングアンチパターン

### 例外の隠蔽
```python
# ❌ 避ける: エラーを隠して継続
def process_user_hide_errors(self, user_id):
    try:
        return self.api.block_user(user_id)
    except Exception:
        # エラーを隠蔽→問題の発見が困難
        return {"success": False}

# ✅ 正しい: 適切なエラー分類と対応
def process_user_proper_error_handling(self, user_id):
    try:
        return self.api.block_user(user_id)
    except PermanentError as e:
        # 永続的失敗→記録して終了
        self.database.record_permanent_failure(user_id, str(e))
        return {"success": False, "reason": "permanent_failure"}
    except TemporaryError as e:
        # 一時的失敗→リトライ可能
        raise e  # 上位でリトライ処理
    except UnknownError as e:
        # 不明エラー→ログ記録して再発生
        self.logger.error(f"不明エラー: {e}", user_id=user_id)
        raise e
```

### 無限リトライ
```python
# ❌ 避ける: 制限のないリトライ
def retry_forever_bad(self, operation, *args):
    while True:  # 無限ループのリスク
        try:
            return operation(*args)
        except Exception:
            time.sleep(60)  # 永続的失敗でも永続的にリトライ

# ✅ 正しい: 制限付きリトライ
def retry_with_limits_good(self, operation, *args, max_retries=3):
    for attempt in range(max_retries):
        try:
            return operation(*args)
        except PermanentError:
            # 永続的失敗→即座に諦める
            raise
        except TemporaryError as e:
            if attempt == max_retries - 1:
                raise e
            wait_time = (2 ** attempt) * 60  # 指数バックオフ
            time.sleep(wait_time)
```

## リソース管理アンチパターン

### リソースリーク
```python
# ❌ 避ける: リソースの明示的クローズ忘れ
def database_operation_leak(self):
    conn = sqlite3.connect(self.db_file)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    results = cursor.fetchall()
    # conn.close()を忘れる→リソースリーク
    return results

# ✅ 正しい: context manager使用
def database_operation_safe(self):
    with sqlite3.connect(self.db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users")
        return cursor.fetchall()
        # 自動的にクローズされる
```

### メモリ効率の悪い実装
```python
# ❌ 避ける: 全データをメモリに保持
def process_large_file_bad(self, large_file_path):
    with open(large_file_path, 'r') as f:
        all_data = json.load(f)  # 巨大ファイル全体をメモリに
        
    results = []
    for item in all_data:  # 全データを同時に処理
        result = self.expensive_operation(item)
        results.append(result)
    
    return results  # 全結果をメモリに保持

# ✅ 正しい: ストリーミング処理
def process_large_file_good(self, large_file_path):
    batch_size = 100
    
    with open(large_file_path, 'r') as f:
        data = json.load(f)
    
    for i in range(0, len(data), batch_size):
        batch = data[i:i + batch_size]
        
        # バッチ単位で処理
        batch_results = self.process_batch(batch)
        
        # 結果を即座に保存（メモリから解放）
        self.save_batch_results(batch_results)
        
        # バッチデータを明示的に削除
        del batch
        del batch_results
```

## API設計アンチパターン

### レート制限無視
```python
# ❌ 避ける: レート制限を考慮しないAPI呼び出し
def call_api_aggressively_bad(self, user_list):
    results = []
    for user in user_list:
        # レート制限無視→429エラー大量発生
        result = self.api.get_user_info(user)
        results.append(result)
    return results

# ✅ 正しい: レート制限考慮
def call_api_respectfully_good(self, user_list):
    results = []
    api_calls_count = 0
    last_reset_time = time.time()
    
    for user in user_list:
        # レート制限チェック
        if api_calls_count >= 150:  # 制限近し
            wait_time = 900 - (time.time() - last_reset_time)
            if wait_time > 0:
                time.sleep(wait_time)
            api_calls_count = 0
            last_reset_time = time.time()
        
        result = self.api.get_user_info(user)
        results.append(result)
        api_calls_count += 1
    
    return results
```

### API依存の過度な実装
```python
# ❌ 避ける: APIに完全依存した実装
def get_user_info_api_dependent_bad(self, user_id):
    # キャッシュ無し→毎回API呼び出し
    return self.api.get_user_info_by_id(user_id)

# ✅ 正しい: キャッシュ活用でAPI依存軽減
def get_user_info_cache_first_good(self, user_id):
    # 1. キャッシュ確認
    cached_data = self.cache.get_user_info(user_id)
    if cached_data and not self.is_cache_expired(cached_data):
        return cached_data
    
    # 2. API呼び出し（必要時のみ）
    api_data = self.api.get_user_info_by_id(user_id)
    
    # 3. キャッシュ更新
    self.cache.save_user_info(user_id, api_data)
    
    return api_data
```

## データベース設計アンチパターン

### インデックス不足
```python
# ❌ 避ける: インデックスなしのクエリ
"""
CREATE TABLE block_history (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    screen_name TEXT,
    status TEXT,
    timestamp REAL
);
-- user_idやscreen_nameで頻繁に検索するのにインデックスなし
"""

# ✅ 正しい: 適切なインデックス設定
"""
CREATE TABLE block_history (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    screen_name TEXT,
    status TEXT,
    timestamp REAL
);

-- 頻繁に使用するカラムにインデックス作成
CREATE INDEX idx_user_id ON block_history(user_id);
CREATE INDEX idx_screen_name ON block_history(screen_name);
CREATE INDEX idx_status ON block_history(status);
CREATE INDEX idx_timestamp ON block_history(timestamp);

-- 複合検索用のインデックス
CREATE INDEX idx_user_status ON block_history(user_id, status);
"""
```

### 正規化不足
```python
# ❌ 避ける: 重複データの保存
"""
CREATE TABLE user_operations (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    screen_name TEXT,
    display_name TEXT,  -- 変更される可能性のあるデータ
    followers_count INTEGER,  -- 頻繁に変更される
    operation_type TEXT,
    timestamp REAL
);
-- ユーザー情報の重複→データ不整合のリスク
"""

# ✅ 正しい: 適切な正規化
"""
-- ユーザー基本情報テーブル
CREATE TABLE users (
    user_id TEXT PRIMARY KEY,
    screen_name TEXT,
    display_name TEXT,
    last_updated REAL
);

-- 操作履歴テーブル（正規化済み）
CREATE TABLE user_operations (
    id INTEGER PRIMARY KEY,
    user_id TEXT,
    operation_type TEXT,
    timestamp REAL,
    FOREIGN KEY(user_id) REFERENCES users(user_id)
);
"""
```

## セキュリティアンチパターン

### 認証情報の平文保存
```python
# ❌ 避ける: クッキーや認証情報の平文保存
def save_cookies_bad(self, cookies):
    with open('cookies.json', 'w') as f:
        json.dump(cookies, f)  # 平文で保存→セキュリティリスク

# ✅ 正しい: 適切な保護措置
def save_cookies_good(self, cookies):
    # 最小限の必要データのみ保存
    essential_cookies = {
        'ct0': cookies.get('ct0'),
        'auth_token': cookies.get('auth_token')
    }
    
    with open('cookies.json', 'w') as f:
        json.dump(essential_cookies, f)
    
    # ファイル権限の制限
    os.chmod('cookies.json', 0o600)  # 所有者のみ読み書き可能
```

### ログへの機密情報出力
```python
# ❌ 避ける: 機密情報をログに出力
def process_with_sensitive_logging_bad(self, user_data):
    # 認証トークンがログに残る
    self.logger.info(f"処理開始: {user_data}")
    
    cookies = user_data.get('cookies', {})
    # クッキー情報がログに残る
    self.logger.debug(f"使用クッキー: {cookies}")

# ✅ 正しい: 機密情報を除外したログ
def process_with_safe_logging_good(self, user_data):
    # 機密情報を除外
    safe_data = {k: v for k, v in user_data.items() if k not in ['cookies', 'tokens']}
    self.logger.info(f"処理開始: {safe_data}")
    
    # 機密情報は存在確認のみ
    has_auth = 'cookies' in user_data and user_data['cookies']
    self.logger.debug(f"認証情報の有無: {has_auth}")
```

## 設定管理アンチパターン

### ハードコーディング
```python
# ❌ 避ける: 設定値のハードコーディング
def process_users_hardcoded_bad(self, users):
    batch_size = 50  # ハードコーディング
    delay = 1.0      # ハードコーディング
    max_retries = 3  # ハードコーディング
    
    for i in range(0, len(users), batch_size):
        # 処理...
        time.sleep(delay)

# ✅ 正しい: 設定可能な実装
def process_users_configurable_good(self, users):
    config = self.get_config()
    batch_size = config.get('batch_size', 50)
    delay = config.get('processing_delay', 1.0)
    max_retries = config.get('max_retries', 3)
    
    for i in range(0, len(users), batch_size):
        # 処理...
        time.sleep(delay)
```

### グローバル変数の乱用
```python
# ❌ 避ける: グローバル変数での状態管理
current_user = None
processing_count = 0
error_count = 0

def process_user_global_bad(user_id):
    global current_user, processing_count, error_count
    current_user = user_id
    processing_count += 1
    # グローバル変数→テストが困難、副作用のリスク

# ✅ 正しい: クラスベースの状態管理
class UserProcessor:
    def __init__(self):
        self.current_user = None
        self.processing_count = 0
        self.error_count = 0
    
    def process_user(self, user_id):
        self.current_user = user_id
        self.processing_count += 1
        # 状態がカプセル化されている
```