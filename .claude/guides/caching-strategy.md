# 3層キャッシュ戦略詳細

## キャッシュアーキテクチャ概要

### 3層構造
```
┌─────────────────┐
│ 1. Lookup Cache │ ← screen_name → user_id 変換
├─────────────────┤
│ 2. Profile Cache│ ← ユーザー基本情報
├─────────────────┤  
│ 3. Relation Cache│ ← フォロー・ブロック関係
└─────────────────┘
```

### 各層の役割と特徴
```python
CACHE_LAYERS = {
    "lookup": {
        "purpose": "screen_name → user_id 変換",
        "ttl": 86400,  # 24時間
        "size_limit": "unlimited",
        "key_format": "screen_name",
        "value_format": "user_id"
    },
    "profiles": {
        "purpose": "ユーザー基本情報",
        "ttl": 3600,   # 1時間
        "size_limit": "1000 files",
        "key_format": "user_id", 
        "value_format": "full_user_object"
    },
    "relationships": {
        "purpose": "フォロー・ブロック関係",
        "ttl": 1800,   # 30分
        "size_limit": "500 files",
        "key_format": "user_id",
        "value_format": "relationship_object"
    }
}
```

## 各層の実装詳細

### 1. Lookup Cache（最長期間）
```python
def get_lookup_from_cache(self, screen_name):
    """screen_name → user_id 変換キャッシュ"""
    cache_file = self.lookups_cache_dir / f"{screen_name}.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # TTLチェック（24時間）
            if time.time() - cache_data['timestamp'] < 86400:
                return cache_data['user_id']
            else:
                cache_file.unlink()  # 期限切れ削除
        except (json.JSONDecodeError, KeyError):
            cache_file.unlink()  # 破損ファイル削除
    
    return None

def save_lookup_to_cache(self, screen_name, user_id):
    """lookup結果をキャッシュに保存"""
    cache_data = {
        'user_id': user_id,
        'timestamp': time.time(),
        'screen_name': screen_name
    }
    
    cache_file = self.lookups_cache_dir / f"{screen_name}.json"
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
```

### 2. Profile Cache（中期間）
```python
def get_profile_from_cache(self, user_id):
    """ユーザー基本情報キャッシュ"""
    cache_file = self.profiles_cache_dir / f"{user_id}.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # TTLチェック（1時間）
            if time.time() - cache_data['timestamp'] < 3600:
                return cache_data['user_data']
            else:
                cache_file.unlink()
        except (json.JSONDecodeError, KeyError):
            cache_file.unlink()
    
    return None

def save_profile_to_cache(self, user_id, user_data):
    """プロフィール情報をキャッシュに保存"""
    cache_data = {
        'user_data': user_data,
        'timestamp': time.time(),
        'user_id': user_id
    }
    
    cache_file = self.profiles_cache_dir / f"{user_id}.json"
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
```

### 3. Relationship Cache（短期間）
```python
def get_relationship_from_cache(self, user_id):
    """フォロー・ブロック関係キャッシュ"""
    cache_file = self.relationships_cache_dir / f"{user_id}.json"
    
    if cache_file.exists():
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # TTLチェック（30分）
            if time.time() - cache_data['timestamp'] < 1800:
                return cache_data['relationship_data']
            else:
                cache_file.unlink()
        except (json.JSONDecodeError, KeyError):
            cache_file.unlink()
    
    return None

def save_relationship_to_cache(self, user_id, relationship_data):
    """関係情報をキャッシュに保存"""
    cache_data = {
        'relationship_data': relationship_data,
        'timestamp': time.time(),
        'user_id': user_id
    }
    
    cache_file = self.relationships_cache_dir / f"{user_id}.json"
    with open(cache_file, 'w', encoding='utf-8') as f:
        json.dump(cache_data, f, ensure_ascii=False, indent=2)
```

## 階層的アクセス戦略

### 段階的フォールバック
```python
def get_user_info_with_cache_hierarchy(self, screen_name):
    """3層キャッシュを活用した効率的なユーザー情報取得"""
    
    # Level 1: Lookup Cache確認
    user_id = self.get_lookup_from_cache(screen_name)
    
    if user_id:
        # Level 2: Profile Cache確認
        profile_data = self.get_profile_from_cache(user_id)
        
        # Level 3: Relationship Cache確認
        relationship_data = self.get_relationship_from_cache(user_id)
        
        # 完全キャッシュヒット
        if profile_data and relationship_data:
            return self.combine_user_data(profile_data, relationship_data)
        
        # 部分キャッシュヒット→最小API呼び出し
        elif profile_data:
            # 関係情報のみAPI取得
            relationship_data = self.fetch_relationship_only(user_id)
            self.save_relationship_to_cache(user_id, relationship_data)
            return self.combine_user_data(profile_data, relationship_data)
        
        elif relationship_data:
            # プロフィール情報のみAPI取得
            profile_data = self.fetch_profile_only(user_id)
            self.save_profile_to_cache(user_id, profile_data)
            return self.combine_user_data(profile_data, relationship_data)
    
    # キャッシュミス→フルAPI取得
    return self.fetch_user_info_full(screen_name)
```

### パフォーマンス最適化
```python
def get_users_batch_with_cache(self, screen_names):
    """バッチ処理でのキャッシュ活用"""
    
    # キャッシュ状況の事前分析
    cache_analysis = self.analyze_cache_coverage(screen_names)
    
    # 完全キャッシュヒット
    cached_users = {}
    for screen_name in cache_analysis['full_cache_hit']:
        cached_users[screen_name] = self.get_user_info_with_cache_hierarchy(screen_name)
    
    # 部分キャッシュヒット→最小API
    partial_cache_users = {}
    for screen_name in cache_analysis['partial_cache_hit']:
        partial_cache_users[screen_name] = self.get_user_info_with_cache_hierarchy(screen_name)
    
    # キャッシュミス→バッチAPI
    missing_users = {}
    if cache_analysis['cache_miss']:
        missing_users = self.fetch_users_batch_api(cache_analysis['cache_miss'])
        
        # 取得データをキャッシュに保存
        for screen_name, user_data in missing_users.items():
            self.save_all_cache_layers(screen_name, user_data)
    
    # 結果をマージ
    all_users = {}
    all_users.update(cached_users)
    all_users.update(partial_cache_users)
    all_users.update(missing_users)
    
    return all_users

def analyze_cache_coverage(self, screen_names):
    """キャッシュカバレッジ分析"""
    analysis = {
        'full_cache_hit': [],
        'partial_cache_hit': [],
        'cache_miss': []
    }
    
    for screen_name in screen_names:
        user_id = self.get_lookup_from_cache(screen_name)
        
        if user_id:
            has_profile = self.get_profile_from_cache(user_id) is not None
            has_relationship = self.get_relationship_from_cache(user_id) is not None
            
            if has_profile and has_relationship:
                analysis['full_cache_hit'].append(screen_name)
            elif has_profile or has_relationship:
                analysis['partial_cache_hit'].append(screen_name)
            else:
                analysis['cache_miss'].append(screen_name)
        else:
            analysis['cache_miss'].append(screen_name)
    
    return analysis
```

## キャッシュ管理

### 容量管理
```python
def manage_cache_size(self):
    """キャッシュサイズ管理"""
    
    # 各層の容量チェック
    for cache_name, cache_dir in [
        ("lookup", self.lookups_cache_dir),
        ("profiles", self.profiles_cache_dir), 
        ("relationships", self.relationships_cache_dir)
    ]:
        cache_files = list(cache_dir.glob("*.json"))
        
        # サイズ制限チェック
        if len(cache_files) > CACHE_LAYERS[cache_name].get("size_limit", 1000):
            # 古いファイルから削除
            cache_files.sort(key=lambda f: f.stat().st_mtime)
            excess_count = len(cache_files) - CACHE_LAYERS[cache_name]["size_limit"]
            
            for old_file in cache_files[:excess_count]:
                old_file.unlink()
                
            print(f"📦 {cache_name} キャッシュ: {excess_count}件の古いファイルを削除")

def cleanup_expired_cache(self):
    """期限切れキャッシュの削除"""
    current_time = time.time()
    
    for cache_name, cache_dir in [
        ("lookup", self.lookups_cache_dir),
        ("profiles", self.profiles_cache_dir),
        ("relationships", self.relationships_cache_dir)
    ]:
        ttl = CACHE_LAYERS[cache_name]["ttl"]
        expired_count = 0
        
        for cache_file in cache_dir.glob("*.json"):
            if current_time - cache_file.stat().st_mtime > ttl:
                cache_file.unlink()
                expired_count += 1
        
        if expired_count > 0:
            print(f"🗑️ {cache_name} キャッシュ: {expired_count}件の期限切れファイルを削除")
```

### キャッシュ統計
```python
def get_cache_statistics(self):
    """キャッシュ統計情報"""
    stats = {}
    
    for cache_name, cache_dir in [
        ("lookup", self.lookups_cache_dir),
        ("profiles", self.profiles_cache_dir),
        ("relationships", self.relationships_cache_dir)
    ]:
        cache_files = list(cache_dir.glob("*.json"))
        
        if cache_files:
            total_size = sum(f.stat().st_size for f in cache_files)
            avg_age = (time.time() - sum(f.stat().st_mtime for f in cache_files) / len(cache_files)) / 3600
            
            stats[cache_name] = {
                "file_count": len(cache_files),
                "total_size_mb": total_size / (1024 * 1024),
                "avg_age_hours": avg_age,
                "ttl_hours": CACHE_LAYERS[cache_name]["ttl"] / 3600
            }
        else:
            stats[cache_name] = {
                "file_count": 0,
                "total_size_mb": 0,
                "avg_age_hours": 0,
                "ttl_hours": CACHE_LAYERS[cache_name]["ttl"] / 3600
            }
    
    return stats

def print_cache_summary(self):
    """キャッシュ統計の表示"""
    stats = self.get_cache_statistics()
    
    print("\n📊 キャッシュ統計:")
    for cache_name, data in stats.items():
        print(f"  {cache_name.upper()}: {data['file_count']}件, "
              f"{data['total_size_mb']:.1f}MB, "
              f"平均{data['avg_age_hours']:.1f}時間経過")
```

## 最適化のベストプラクティス

### キャッシュ戦略の選択
```python
def choose_cache_strategy(operation_type, data_freshness_requirement):
    """操作タイプに応じたキャッシュ戦略選択"""
    
    strategies = {
        "bulk_processing": {
            "use_cache": True,
            "cache_layers": ["lookup", "profiles", "relationships"],
            "freshness_tolerance": "medium"
        },
        "real_time_check": {
            "use_cache": True,
            "cache_layers": ["lookup", "profiles"],
            "freshness_tolerance": "high"  # 関係情報は最新必須
        },
        "batch_analysis": {
            "use_cache": True,
            "cache_layers": ["lookup", "profiles", "relationships"],
            "freshness_tolerance": "low"
        }
    }
    
    return strategies.get(operation_type, strategies["bulk_processing"])
```

### キャッシュ効率測定
```python
def measure_cache_efficiency(self):
    """キャッシュ効率の測定"""
    
    # キャッシュヒット率
    cache_hits = self.cache_hit_counter
    cache_misses = self.cache_miss_counter
    hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
    
    # API呼び出し削減率
    api_calls_saved = self.api_calls_saved_counter
    total_potential_calls = self.total_operations_counter
    api_reduction_rate = api_calls_saved / total_potential_calls if total_potential_calls > 0 else 0
    
    return {
        "cache_hit_rate": hit_rate,
        "api_reduction_rate": api_reduction_rate,
        "total_cache_hits": cache_hits,
        "total_cache_misses": cache_misses,
        "api_calls_saved": api_calls_saved
    }
```