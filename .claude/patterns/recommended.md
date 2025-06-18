# 推奨実装パターン

## アーキテクチャパターン

### 責務分離パターン
```python
# ✅ 推奨: 各クラスの責務を明確に分離

class TwitterAPI:
    """Twitter API通信専門"""
    def get_user_info(self, screen_name): pass
    def block_user(self, user_id): pass

class DatabaseManager:
    """データベース操作専門"""
    def save_block_history(self, user_id, status): pass
    def get_retry_targets(self): pass

class CacheManager:
    """キャッシュ管理専門"""
    def get_from_cache(self, key): pass
    def save_to_cache(self, key, data): pass

class BlockManager:
    """ビジネスロジック統括"""
    def __init__(self):
        self.api = TwitterAPI()
        self.database = DatabaseManager()
        self.cache = CacheManager()
    
    def process_block_request(self, screen_name):
        # 各専門クラスを組み合わせて処理
        pass
```

### エラーハンドリングパターン
```python
# ✅ 推奨: 統一的なエラーハンドリング

def api_operation_with_recovery(operation_func, *args, **kwargs):
    """API操作の統一エラーハンドリング"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            return operation_func(*args, **kwargs)
        except PermanentError as e:
            # 永続的失敗→即座に諦める
            raise e
        except TemporaryError as e:
            # 一時的失敗→リトライ
            retry_count += 1
            wait_time = calculate_backoff_time(retry_count)
            time.sleep(wait_time)
        except UnknownError as e:
            # 不明エラー→1回だけリトライ
            if retry_count == 0:
                retry_count = max_retries - 1
                time.sleep(60)
            else:
                raise e
    
    raise MaxRetriesExceededError()

# 使用例
def block_user_safely(self, user_id):
    return api_operation_with_recovery(
        self.api.block_user_by_id, 
        user_id
    )
```

## データベースパターン

### バッチ処理最適化パターン
```python
# ✅ 推奨: バッチクエリでN+1問題を回避

def get_permanent_failures_batch(self, identifiers, user_format="screen_name"):
    """複数の永続的失敗を一括取得"""
    if not identifiers:
        return {}
    
    placeholders = ",".join("?" * len(identifiers))
    
    # 動的クエリ生成
    if user_format == "user_id":
        query = f"""
            SELECT user_id, user_status, error_message, updated_at
            FROM block_history 
            WHERE user_id IN ({placeholders}) 
            AND status = 'failed'
            AND user_status IN ('suspended', 'not_found', 'deactivated')
        """
    else:
        query = f"""
            SELECT screen_name, user_status, error_message, updated_at
            FROM block_history 
            WHERE screen_name IN ({placeholders}) 
            AND status = 'failed' 
            AND user_status IN ('suspended', 'not_found', 'deactivated')
        """
    
    with sqlite3.connect(self.db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(query, [str(id_) for id_ in identifiers])
        
        return {
            row[0]: {
                "user_status": row[1],
                "error_message": row[2],
                "updated_at": row[3]
            }
            for row in cursor.fetchall()
        }

# 使用例
def process_users_efficiently(self, user_list):
    # 1. バッチで永続的失敗をチェック
    permanent_failures = self.database.get_permanent_failures_batch(user_list)
    
    # 2. 処理対象を絞り込み
    processable_users = [u for u in user_list if u not in permanent_failures]
    
    # 3. バッチでAPI処理
    results = self.api.process_users_batch(processable_users)
    
    return results
```

### リソース管理パターン
```python
# ✅ 推奨: context manager使用

class DatabaseConnection:
    def __init__(self, db_file):
        self.db_file = db_file
        self.conn = None
    
    def __enter__(self):
        self.conn = sqlite3.connect(self.db_file)
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()

# 使用例
def save_block_result(self, user_id, result):
    with DatabaseConnection(self.db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO block_history (user_id, status, timestamp)
            VALUES (?, ?, ?)
        """, (user_id, result, time.time()))
        # 自動的にcommit/rollback/closeが実行される
```

## キャッシュ活用パターン

### 階層キャッシュパターン
```python
# ✅ 推奨: 3層キャッシュの効率的利用

def get_user_with_hierarchical_cache(self, screen_name):
    """階層キャッシュを活用した最適な取得"""
    
    # 1層目: screen_name → user_id 変換
    user_id = self.cache.get_lookup(screen_name)
    if not user_id:
        # APIでlookup実行
        user_id = self.api.get_user_id_by_screen_name(screen_name)
        self.cache.save_lookup(screen_name, user_id)
    
    # 2層目: ユーザー基本情報
    profile = self.cache.get_profile(user_id)
    
    # 3層目: フォロー・ブロック関係
    relationships = self.cache.get_relationships(user_id)
    
    missing_data = []
    if not profile:
        missing_data.append("profile")
    if not relationships:
        missing_data.append("relationships")
    
    if missing_data:
        # 必要最小限のAPI呼び出し
        api_data = self.api.get_user_data(user_id, include=missing_data)
        
        if "profile" in missing_data:
            profile = api_data["profile"]
            self.cache.save_profile(user_id, profile)
        
        if "relationships" in missing_data:
            relationships = api_data["relationships"]
            self.cache.save_relationships(user_id, relationships)
    
    return self.combine_user_data(profile, relationships)
```

### キャッシュ無効化パターン
```python
# ✅ 推奨: 適切なキャッシュ無効化

def invalidate_user_cache(self, user_id, screen_name=None):
    """ユーザー関連キャッシュの無効化"""
    
    # プロフィール・関係キャッシュは常に無効化
    self.cache.invalidate_profile(user_id)
    self.cache.invalidate_relationships(user_id)
    
    # lookup キャッシュは選択的に無効化
    if screen_name:
        self.cache.invalidate_lookup(screen_name)
    
    # 操作ログ
    print(f"🗑️ キャッシュ無効化: user_id={user_id}")

def block_user_with_cache_update(self, user_id, screen_name):
    """ブロック操作とキャッシュ更新"""
    
    # ブロック実行
    result = self.api.block_user_by_id(user_id)
    
    if result["success"]:
        # 関係キャッシュのみ無効化（プロフィールは残す）
        self.cache.invalidate_relationships(user_id)
        
        # データベース記録
        self.database.save_block_history(user_id, "success")
    
    return result
```

## 非同期・並行処理パターン

### バッチ処理の並行実行
```python
# ✅ 推奨: レート制限を考慮した並行処理

import asyncio
import aiohttp
from asyncio import Semaphore

class ConcurrentProcessor:
    def __init__(self, max_concurrent=5):
        self.semaphore = Semaphore(max_concurrent)
        self.rate_limiter = RateLimiter(requests_per_window=150, window_seconds=900)
    
    async def process_user_batch(self, user_list):
        """ユーザーリストの並行処理"""
        tasks = []
        
        for user in user_list:
            task = self.process_single_user_with_limits(user)
            tasks.append(task)
        
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def process_single_user_with_limits(self, user):
        """レート制限・並行制限付き単一ユーザー処理"""
        async with self.semaphore:  # 並行数制限
            await self.rate_limiter.wait()  # レート制限
            return await self.process_user(user)
    
    async def process_user(self, user):
        """実際のユーザー処理"""
        # 永続的失敗チェック
        if self.database.is_permanent_failure(user):
            return {"user": user, "status": "skipped", "reason": "permanent_failure"}
        
        # API処理
        try:
            result = await self.api.block_user_async(user)
            return {"user": user, "status": "success", "result": result}
        except Exception as e:
            return {"user": user, "status": "error", "error": str(e)}
```

### ストリーミング処理パターン
```python
# ✅ 推奨: メモリ効率的な大量データ処理

def process_large_user_list_streaming(self, user_file_path, batch_size=50):
    """大量ユーザーリストのストリーミング処理"""
    
    def user_generator():
        """ユーザーをバッチ単位で順次読み込み"""
        with open(user_file_path, 'r') as f:
            users = json.load(f)
            
            for i in range(0, len(users), batch_size):
                yield users[i:i + batch_size]
    
    total_processed = 0
    total_success = 0
    
    for batch in user_generator():
        # バッチ処理
        batch_results = self.process_user_batch(batch)
        
        # 統計更新
        total_processed += len(batch)
        total_success += sum(1 for r in batch_results if r.get("status") == "success")
        
        # メモリ解放
        del batch_results
        
        # 進捗表示
        print(f"📊 処理進捗: {total_processed}件完了 (成功: {total_success}件)")
        
        # レート制限対策の休憩
        time.sleep(1)
    
    return {"total_processed": total_processed, "total_success": total_success}
```

## 設定管理パターン

### 環境別設定パターン
```python
# ✅ 推奨: 環境に応じた動的設定

import os

class Config:
    def __init__(self):
        self.environment = os.getenv('ENVIRONMENT', 'development')
        self.load_config()
    
    def load_config(self):
        """環境別設定の読み込み"""
        base_config = {
            'batch_size': 50,
            'retry_count': 3,
            'cache_ttl': 3600,
            'api_delay': 1.0
        }
        
        env_configs = {
            'development': {
                'batch_size': 10,  # 小さいバッチで安全に
                'api_delay': 2.0,  # ゆっくり実行
                'debug_mode': True
            },
            'production': {
                'batch_size': 100,  # 高効率バッチ
                'api_delay': 0.5,   # 高速実行
                'debug_mode': False
            },
            'test': {
                'batch_size': 5,
                'api_delay': 0.1,
                'mock_api': True
            }
        }
        
        # 基本設定をマージ
        self.config = base_config.copy()
        self.config.update(env_configs.get(self.environment, {}))
        
        # 環境変数オーバーライド
        self.apply_env_overrides()
    
    def apply_env_overrides(self):
        """環境変数による設定オーバーライド"""
        overrides = {
            'BATCH_SIZE': ('batch_size', int),
            'API_DELAY': ('api_delay', float),
            'RETRY_COUNT': ('retry_count', int)
        }
        
        for env_var, (config_key, type_func) in overrides.items():
            if env_value := os.getenv(env_var):
                self.config[config_key] = type_func(env_value)
    
    def get(self, key, default=None):
        """設定値の取得"""
        return self.config.get(key, default)

# 使用例
config = Config()
batch_size = config.get('batch_size')
api_delay = config.get('api_delay')
```

## ロギング・モニタリングパターン

### 構造化ログパターン
```python
# ✅ 推奨: 構造化されたログ出力

import json
import datetime

class StructuredLogger:
    def __init__(self, component_name):
        self.component = component_name
    
    def log(self, level, message, **kwargs):
        """構造化ログエントリ"""
        log_entry = {
            'timestamp': datetime.datetime.now().isoformat(),
            'level': level,
            'component': self.component,
            'message': message,
            'data': kwargs
        }
        
        # コンソール出力（人間可読）
        print(f"[{level}] {self.component}: {message}")
        if kwargs:
            for key, value in kwargs.items():
                print(f"  {key}: {value}")
        
        # ファイル出力（JSON）
        with open('application.log', 'a') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    
    def info(self, message, **kwargs):
        self.log('INFO', message, **kwargs)
    
    def warning(self, message, **kwargs):
        self.log('WARNING', message, **kwargs)
    
    def error(self, message, **kwargs):
        self.log('ERROR', message, **kwargs)

# 使用例
logger = StructuredLogger('BlockManager')

def process_block_request(self, user_id):
    logger.info("ブロック処理開始", user_id=user_id)
    
    try:
        result = self.api.block_user_by_id(user_id)
        logger.info("ブロック完了", user_id=user_id, success=True)
        return result
    except Exception as e:
        logger.error("ブロック失敗", user_id=user_id, error=str(e))
        raise
```