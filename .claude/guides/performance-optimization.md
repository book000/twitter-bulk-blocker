# パフォーマンス最適化手法

## バッチ処理最適化

### 最適バッチサイズ
```python
OPTIMAL_BATCH_SIZES = {
    "user_lookup": 50,           # UsersByRestIds API
    "screen_name_conversion": 25, # UserByScreenName API
    "database_queries": 100,     # SQLite IN句
}

# バッチサイズの動的調整
def adjust_batch_size(self, success_rate, current_size):
    if success_rate > 0.95:
        return min(current_size + 10, 50)  # 成功率高い→増加
    elif success_rate < 0.8:
        return max(current_size - 10, 10)  # 成功率低い→減少
    return current_size
```

### N+1問題の完全回避
```python
# ✅ 推奨: 事前バッチ取得
def process_users_optimized(self, user_ids):
    # 1. 永続的失敗を一括チェック
    permanent_failures = self.database.get_permanent_failures_batch(user_ids)
    
    # 2. 処理対象の絞り込み
    processable_ids = [uid for uid in user_ids if uid not in permanent_failures]
    
    # 3. バッチAPIで一括取得
    users_info = self.api.get_users_info_batch(processable_ids)
    
    # 4. バッチ処理実行
    return self._process_batch(users_info)

# ❌ 避ける: ループ内個別処理
def process_users_inefficient(self, user_ids):
    for user_id in user_ids:  # N+1問題発生
        if self.database.is_permanent_failure(user_id):  # 個別DB
            continue
        user_info = self.api.get_user_info_by_id(user_id)  # 個別API
```

## データベース最適化

### バッチクエリパターン
```python
# SQLite IN句での一括処理
def get_permanent_failures_batch(self, identifiers, user_format="screen_name"):
    placeholders = ",".join("?" * len(identifiers))
    
    if user_format == "user_id":
        query = f"""
            SELECT user_id, user_status, error_message 
            FROM block_history 
            WHERE user_id IN ({placeholders}) AND status = 'failed'
        """
    else:
        query = f"""
            SELECT screen_name, user_status, error_message 
            FROM block_history 
            WHERE screen_name IN ({placeholders}) AND status = 'failed'
        """
    
    with sqlite3.connect(self.db_file) as conn:
        cursor = conn.cursor()
        cursor.execute(query, [str(id_) for id_ in identifiers])
        return {row[0]: {"status": row[1], "message": row[2]} 
                for row in cursor.fetchall()}
```

### リソース管理の最適化
```python
# ✅ 推奨: context manager使用
def database_operation(self):
    with sqlite3.connect(self.db_file) as conn:
        cursor = conn.cursor()
        # 自動的にcommit/rollback/close

# ❌ 避ける: 明示的なopen/close
def database_operation_bad(self):
    conn = sqlite3.connect(self.db_file)  # リーク可能性
    # close忘れのリスク
```

## メモリ効率化

### ストリーミング処理
```python
def process_large_dataset(self, large_user_list):
    batch_size = 50
    for i in range(0, len(large_user_list), batch_size):
        batch = large_user_list[i:i + batch_size]
        
        # バッチ処理
        self._process_batch(batch)
        
        # メモリ解放
        del batch
        
        # レート制限対策
        time.sleep(1)
```

### キャッシュメモリ管理
```python
def cleanup_expired_cache(self):
    current_time = time.time()
    
    for cache_dir in [self.lookups_cache_dir, self.profiles_cache_dir]:
        for cache_file in cache_dir.glob("*.json"):
            if current_time - cache_file.stat().st_mtime > self.cache_ttl:
                cache_file.unlink()  # 期限切れファイル削除
```

## パフォーマンス測定

### ベンチマーク実装
```python
def benchmark_operation(operation_func, test_data, iterations=3):
    import time
    
    times = []
    for _ in range(iterations):
        start = time.time()
        result = operation_func(test_data)
        elapsed = time.time() - start
        times.append(elapsed)
    
    avg_time = sum(times) / len(times)
    print(f"平均実行時間: {avg_time:.4f}秒")
    print(f"スループット: {len(test_data) / avg_time:.1f}件/秒")
    
    return result
```

### パフォーマンス目標値
```python
PERFORMANCE_TARGETS = {
    "user_processing_rate": 50,      # 件/秒以上
    "cache_hit_rate": 0.8,          # 80%以上
    "api_call_reduction": 0.7,       # 70%削減目標
    "database_query_time": 0.01,     # 10ms以下/クエリ
    "memory_usage": 100,             # 100MB以下
}

def validate_performance(current_metrics):
    violations = []
    for metric, target in PERFORMANCE_TARGETS.items():
        if current_metrics.get(metric, 0) < target:
            violations.append(f"{metric}: {current_metrics[metric]} < {target}")
    
    if violations:
        print("⚠️ パフォーマンス基準未達:")
        for violation in violations:
            print(f"  - {violation}")
```

## 最適化チェックリスト

### 実装前確認事項
- [ ] バッチ処理可能な箇所の特定
- [ ] N+1問題の潜在箇所確認
- [ ] キャッシュ活用可能性評価
- [ ] メモリ使用量予測

### 実装後検証事項
- [ ] パフォーマンステスト実行
- [ ] メモリプロファイリング
- [ ] キャッシュヒット率測定
- [ ] API呼び出し数削減確認