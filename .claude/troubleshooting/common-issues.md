# よくある問題とトラブルシューティング

## 認証関連の問題

### 🚨 問題: 401 Unauthorized エラー
```
エラーメッセージ: "認証に失敗しました (401)"
```

**原因と対処法:**
1. **クッキーの有効期限切れ**
   ```python
   # 確認方法
   cookies = self.cookie_manager.load_cookies()
   if not cookies or 'ct0' not in cookies or 'auth_token' not in cookies:
       print("❌ 必須クッキーが不足しています")
   
   # 対処法
   # 1. ブラウザから最新のクッキーを取得
   # 2. cookies.jsonファイルを更新
   ```

2. **CSRFトークンの不整合**
   ```python
   # 確認方法
   def check_csrf_token():
       cookies = self.cookie_manager.load_cookies()
       ct0_cookie = cookies.get('ct0')
       
       # リクエストヘッダーのCSRFトークンと比較
       headers = self.get_headers()
       csrf_header = headers.get('x-csrf-token')
       
       if ct0_cookie != csrf_header:
           print("❌ CSRFトークンが不整合です")
           return False
       return True
   
   # 対処法
   self.cookie_manager.clear_cache()
   # 新しいセッションで再実行
   ```

3. **アカウント制限・凍結**
   ```python
   # 確認方法
   # 手動でTwitterにアクセスして状態確認
   # - アカウントが凍結されていないか？
   # - 二段階認証が要求されていないか？
   # - アカウントロックされていないか？
   ```

### 🚨 問題: "フィーチャーフラグが無効" エラー
```
エラーメッセージ: "必要なフィーチャーフラグが設定されていません"
```

**原因と対処法:**
```python
# 最新のフィーチャーフラグに更新
FEATURES = {
    "hidden_profile_likes_enabled": True,
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    # Twitterの仕様変更により定期的に更新が必要
}

# デバッグ方法
def debug_feature_flags():
    # ブラウザのネットワークタブでTwitterの実際のリクエストを確認
    # 最新のfeaturesパラメータをコピー
    pass
```

## API関連の問題

### 🚨 問題: 429 Rate Limit エラー
```
エラーメッセージ: "Rate limit exceeded"
```

**原因と対処法:**
```python
def handle_rate_limit_error(response):
    """レート制限エラーの詳細解析と対処"""
    
    # 1. レート制限情報の取得
    remaining = response.headers.get('x-rate-limit-remaining', 0)
    reset_time = response.headers.get('x-rate-limit-reset', 0)
    
    print(f"📊 レート制限状況:")
    print(f"  残り回数: {remaining}")
    print(f"  リセット時刻: {datetime.fromtimestamp(int(reset_time))}")
    
    # 2. 適切な待機時間の計算
    wait_seconds = max(int(reset_time) - int(time.time()), 60)
    print(f"⏰ {wait_seconds}秒待機します...")
    
    # 3. 段階的な再開
    time.sleep(wait_seconds + 10)  # 余裕をもって待機
    return True

# 予防策
def implement_rate_limit_prevention():
    """レート制限の予防策"""
    
    # APIコール数のカウント
    self.api_call_count = 0
    self.last_reset_time = time.time()
    
    def before_api_call(self):
        if self.api_call_count >= 140:  # 制限の少し手前
            wait_time = 900 - (time.time() - self.last_reset_time)
            if wait_time > 0:
                print(f"🛡️ 予防的待機: {wait_time}秒")
                time.sleep(wait_time)
            self.api_call_count = 0
            self.last_reset_time = time.time()
        
        self.api_call_count += 1
```

### 🚨 問題: GraphQLエラー "User not found"
```
エラーメッセージ: {"errors": [{"message": "User not found"}]}
```

**原因と対処法:**
```python
def handle_user_not_found(screen_name, user_id=None):
    """ユーザー未発見エラーの詳細分析"""
    
    # 1. 原因の特定
    possible_causes = [
        "ユーザーがアカウントを削除した",
        "ユーザー名が変更された", 
        "アカウントが凍結された",
        "プライベートアカウントで検索不可",
        "一時的なTwitter側の問題"
    ]
    
    print(f"❓ {screen_name} が見つかりません。考えられる原因:")
    for i, cause in enumerate(possible_causes, 1):
        print(f"  {i}. {cause}")
    
    # 2. 対処法の実行
    # 永続的失敗として記録
    self.database.record_permanent_failure(
        screen_name=screen_name,
        user_id=user_id,
        error_type="not_found",
        error_message="ユーザーが見つかりません"
    )
    
    print(f"📝 {screen_name} を永続的失敗として記録しました")
    return {"status": "permanent_failure", "reason": "not_found"}
```

## データベース関連の問題

### 🚨 問題: SQLite database is locked
```
エラーメッセージ: "database is locked"
```

**原因と対処法:**
```python
def fix_database_lock():
    """データベースロック問題の解決"""
    
    # 1. 原因の確認
    causes = [
        "他のプロセスが同じDBファイルを使用中",
        "前回の処理が異常終了してロックが残存",
        "ファイルシステムのアクセス権限問題", 
        "SQLite接続が適切にクローズされていない"
    ]
    
    # 2. 診断スクリプト
    def diagnose_db_lock(db_file):
        import sqlite3
        import os
        
        # ファイル存在確認
        if not os.path.exists(db_file):
            print(f"❌ DBファイルが存在しません: {db_file}")
            return False
        
        # アクセス権限確認
        if not os.access(db_file, os.R_OK | os.W_OK):
            print(f"❌ DBファイルの権限が不足: {db_file}")
            return False
        
        # ロックファイル確認
        lock_files = [f"{db_file}-wal", f"{db_file}-shm"]
        for lock_file in lock_files:
            if os.path.exists(lock_file):
                print(f"⚠️ ロックファイル発見: {lock_file}")
        
        # 接続テスト
        try:
            with sqlite3.connect(db_file, timeout=5) as conn:
                conn.execute("SELECT 1")
                print("✅ データベース接続正常")
                return True
        except sqlite3.OperationalError as e:
            print(f"❌ データベース接続エラー: {e}")
            return False
    
    # 3. 修復処理
    def repair_database_lock(db_file):
        import os
        import time
        
        # WALファイルの削除（慎重に）
        wal_file = f"{db_file}-wal"
        shm_file = f"{db_file}-shm"
        
        if os.path.exists(wal_file):
            try:
                os.remove(wal_file)
                print(f"🗑️ WALファイルを削除: {wal_file}")
            except OSError as e:
                print(f"❌ WALファイル削除失敗: {e}")
        
        if os.path.exists(shm_file):
            try:
                os.remove(shm_file)
                print(f"🗑️ SHMファイルを削除: {shm_file}")
            except OSError as e:
                print(f"❌ SHMファイル削除失敗: {e}")
        
        # 少し待機
        time.sleep(1)
        
        # 再接続テスト
        return diagnose_db_lock(db_file)
```

### 🚨 問題: 重複データの挿入エラー
```
エラーメッセージ: "UNIQUE constraint failed"
```

**原因と対処法:**
```python
def handle_duplicate_data():
    """重複データエラーの対処"""
    
    # 1. UPSERT操作の使用
    def safe_insert_or_update(self, user_id, screen_name, status):
        query = """
        INSERT INTO block_history (user_id, screen_name, status, timestamp)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, screen_name) DO UPDATE SET
            status = excluded.status,
            timestamp = excluded.timestamp
        """
        
        with sqlite3.connect(self.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute(query, (user_id, screen_name, status, time.time()))
    
    # 2. 事前チェック
    def insert_with_check(self, user_id, screen_name, status):
        # 既存データの確認
        existing = self.get_user_history(user_id, screen_name)
        
        if existing:
            # 更新
            self.update_user_status(user_id, screen_name, status)
            print(f"🔄 データ更新: {screen_name}")
        else:
            # 新規挿入
            self.insert_new_user(user_id, screen_name, status)
            print(f"➕ データ挿入: {screen_name}")
```

## ネットワーク関連の問題

### 🚨 問題: Connection timeout / Network error
```
エラーメッセージ: "requests.exceptions.ConnectionError"
```

**原因と対処法:**
```python
def handle_network_issues():
    """ネットワーク問題の診断と対処"""
    
    # 1. 接続診断
    def diagnose_network():
        import socket
        import requests
        import time
        
        # DNS解決テスト
        try:
            socket.gethostbyname('twitter.com')
            print("✅ DNS解決正常")
        except socket.gaierror:
            print("❌ DNS解決失敗")
            return False
        
        # HTTP接続テスト
        try:
            response = requests.get('https://twitter.com', timeout=10)
            print(f"✅ HTTP接続正常 (ステータス: {response.status_code})")
        except requests.exceptions.RequestException as e:
            print(f"❌ HTTP接続失敗: {e}")
            return False
        
        return True
    
    # 2. リトライ戦略
    def network_retry_wrapper(func, *args, **kwargs):
        max_retries = 3
        base_delay = 30
        
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except requests.exceptions.ConnectionError as e:
                if attempt == max_retries - 1:
                    raise e
                
                delay = base_delay * (2 ** attempt)
                print(f"🔄 ネットワークエラー、{delay}秒後にリトライ (試行: {attempt + 1}/{max_retries})")
                time.sleep(delay)
            except requests.exceptions.Timeout as e:
                print(f"⏰ タイムアウト発生: {e}")
                if attempt == max_retries - 1:
                    raise e
                time.sleep(base_delay)
    
    # 3. プロキシ・VPN確認
    def check_proxy_settings():
        import os
        
        proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
        for var in proxy_vars:
            if os.environ.get(var):
                print(f"🌐 プロキシ設定発見: {var} = {os.environ[var]}")
                print("注意: プロキシ設定がTwitterアクセスに影響する可能性があります")
```

## ファイル・権限関連の問題

### 🚨 問題: Permission denied / File access error
```
エラーメッセージ: "PermissionError: [Errno 13] Permission denied"
```

**原因と対処法:**
```python
def handle_file_permission_issues():
    """ファイル権限問題の診断と修復"""
    
    # 1. 権限診断
    def diagnose_file_permissions(file_path):
        import os
        import stat
        
        if not os.path.exists(file_path):
            print(f"❌ ファイルが存在しません: {file_path}")
            return False
        
        # 権限情報の取得
        file_stat = os.stat(file_path)
        permissions = stat.filemode(file_stat.st_mode)
        owner = file_stat.st_uid
        group = file_stat.st_gid
        
        print(f"📄 ファイル情報: {file_path}")
        print(f"  権限: {permissions}")
        print(f"  所有者ID: {owner}")
        print(f"  グループID: {group}")
        
        # 読み書き権限の確認
        readable = os.access(file_path, os.R_OK)
        writable = os.access(file_path, os.W_OK)
        
        print(f"  読み取り可能: {readable}")
        print(f"  書き込み可能: {writable}")
        
        return readable and writable
    
    # 2. 権限修復
    def fix_file_permissions(file_path):
        import os
        
        try:
            # 読み書き権限を付与
            os.chmod(file_path, 0o600)  # 所有者のみ読み書き
            print(f"✅ 権限修復完了: {file_path}")
            return True
        except OSError as e:
            print(f"❌ 権限修復失敗: {e}")
            return False
    
    # 3. ディレクトリ作成
    def ensure_directory_exists(dir_path):
        import os
        
        if not os.path.exists(dir_path):
            try:
                os.makedirs(dir_path, exist_ok=True)
                print(f"📁 ディレクトリ作成: {dir_path}")
            except OSError as e:
                print(f"❌ ディレクトリ作成失敗: {e}")
                return False
        
        return True
```

## デバッグ・診断ツール

### 総合診断スクリプト
```python
def run_comprehensive_diagnosis():
    """全体的な診断を実行"""
    
    print("🔍 Twitter Block Tool 診断開始")
    print("=" * 50)
    
    # 1. ファイル存在確認
    required_files = [
        'cookies.json',
        'users.json', 
        'block_history.db'
    ]
    
    print("\n📁 必須ファイル確認:")
    for file_path in required_files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"  ✅ {file_path} (サイズ: {size} bytes)")
        else:
            print(f"  ❌ {file_path} (見つかりません)")
    
    # 2. 認証状態確認
    print("\n🔐 認証状態確認:")
    try:
        cookies = load_cookies()
        if 'ct0' in cookies and 'auth_token' in cookies:
            print("  ✅ 必須クッキー存在")
        else:
            print("  ❌ 必須クッキー不足")
    except Exception as e:
        print(f"  ❌ クッキー読み込みエラー: {e}")
    
    # 3. データベース確認
    print("\n💾 データベース確認:")
    try:
        with sqlite3.connect('block_history.db') as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM block_history")
            count = cursor.fetchone()[0]
            print(f"  ✅ レコード数: {count}")
    except Exception as e:
        print(f"  ❌ データベースエラー: {e}")
    
    # 4. ネットワーク確認
    print("\n🌐 ネットワーク確認:")
    try:
        response = requests.get('https://twitter.com', timeout=10)
        print(f"  ✅ Twitter接続正常 (ステータス: {response.status_code})")
    except Exception as e:
        print(f"  ❌ Twitter接続エラー: {e}")
    
    print("\n✅ 診断完了")

# 使用方法
if __name__ == "__main__":
    run_comprehensive_diagnosis()
```

## 緊急時対応

### データバックアップ・復旧
```python
def emergency_backup():
    """緊急時のデータバックアップ"""
    import shutil
    import datetime
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = f"backup_{timestamp}"
    
    os.makedirs(backup_dir, exist_ok=True)
    
    # 重要ファイルのバックアップ
    important_files = [
        'block_history.db',
        'cookies.json',
        'users.json'
    ]
    
    for file_path in important_files:
        if os.path.exists(file_path):
            shutil.copy2(file_path, backup_dir)
            print(f"💾 バックアップ: {file_path} → {backup_dir}")
    
    print(f"✅ 緊急バックアップ完了: {backup_dir}")
    return backup_dir

def emergency_recovery(backup_dir):
    """緊急時の復旧処理"""
    if not os.path.exists(backup_dir):
        print(f"❌ バックアップディレクトリが見つかりません: {backup_dir}")
        return False
    
    # ファイルの復旧
    for file_name in os.listdir(backup_dir):
        src = os.path.join(backup_dir, file_name)
        dst = file_name
        
        try:
            shutil.copy2(src, dst)
            print(f"🔄 復旧: {src} → {dst}")
        except Exception as e:
            print(f"❌ 復旧失敗: {e}")
    
    print("✅ 緊急復旧完了")
    return True
```