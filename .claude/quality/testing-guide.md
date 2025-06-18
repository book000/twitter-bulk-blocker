# テストガイド

## テスト戦略

### テストレベル分類
```python
# 1. 単体テスト（Unit Tests）
class TestDatabaseManager:
    def test_permanent_failure_detection(self):
        """永続的失敗検出のテスト"""
        db = DatabaseManager("test.db")
        
        # 永続的失敗を記録
        db.record_permanent_failure("suspended_user", "suspended")
        
        # 検出確認
        assert db.is_permanent_failure("suspended_user") == True
        assert db.is_permanent_failure("normal_user") == False
    
    def test_batch_query_performance(self):
        """バッチクエリのパフォーマンステスト"""
        db = DatabaseManager("test.db")
        
        # 大量データの準備
        test_users = [f"user_{i}" for i in range(1000)]
        
        # パフォーマンス測定
        start_time = time.time()
        results = db.get_permanent_failures_batch(test_users)
        elapsed = time.time() - start_time
        
        # 1秒以内に完了することを確認
        assert elapsed < 1.0
        assert isinstance(results, dict)

# 2. 統合テスト（Integration Tests）
class TestTwitterAPIIntegration:
    def test_authentication_flow(self):
        """認証フローの統合テスト"""
        api = TwitterAPI()
        
        # クッキー読み込み
        cookies = api.cookie_manager.load_cookies()
        assert 'ct0' in cookies
        assert 'auth_token' in cookies
        
        # 認証状態確認
        user_info = api.get_login_user_info()
        assert user_info['user_id'] is not None
    
    def test_user_lookup_integration(self):
        """ユーザー検索の統合テスト"""
        api = TwitterAPI()
        
        # 既知のユーザーでテスト
        result = api.get_user_info_by_screen_name("TwitterSupport")
        
        assert result['success'] == True
        assert 'user_id' in result
        assert result['screen_name'] == "TwitterSupport"

# 3. エンドツーエンドテスト（E2E Tests）
class TestBlockingWorkflow:
    def test_complete_blocking_process(self):
        """完全なブロック処理のE2Eテスト"""
        manager = BlockManager()
        
        # テストユーザーリスト
        test_users = ["test_user_1", "test_user_2"]
        
        # 完全なワークフロー実行
        results = manager.process_users(test_users, dry_run=True)
        
        # 結果検証
        assert len(results) == len(test_users)
        for result in results:
            assert 'status' in result
            assert result['status'] in ['success', 'failed', 'skipped']
```

## モック・スタブ実装

### API応答のモック
```python
import unittest.mock as mock

class MockTwitterAPI:
    """Twitter API のモック実装"""
    
    def __init__(self):
        self.call_count = 0
        self.responses = {}
    
    def set_response(self, method, screen_name, response):
        """レスポンスを設定"""
        self.responses[(method, screen_name)] = response
    
    def get_user_info_by_screen_name(self, screen_name):
        """モックされたユーザー情報取得"""
        self.call_count += 1
        key = ('get_user_info_by_screen_name', screen_name)
        
        if key in self.responses:
            return self.responses[key]
        
        # デフォルトレスポンス
        return {
            'success': True,
            'user_id': f"mock_id_{screen_name}",
            'screen_name': screen_name
        }
    
    def block_user_by_id(self, user_id):
        """モックされたブロック処理"""
        self.call_count += 1
        key = ('block_user_by_id', user_id)
        
        if key in self.responses:
            return self.responses[key]
        
        return {'success': True, 'blocked': True}

# モックを使用したテスト
class TestWithMock:
    def test_user_processing_with_mock(self):
        """モックAPIを使用したテスト"""
        mock_api = MockTwitterAPI()
        
        # 特定のレスポンスを設定
        mock_api.set_response(
            'get_user_info_by_screen_name', 
            'suspended_user',
            {'success': False, 'error': 'suspended'}
        )
        
        # マネージャーにモックを注入
        manager = BlockManager()
        manager.api = mock_api
        
        # 処理実行
        result = manager.process_user('suspended_user')
        
        # 結果検証
        assert result['status'] == 'failed'
        assert mock_api.call_count == 1
```

### データベースモック
```python
class MockDatabase:
    """データベースのモック実装"""
    
    def __init__(self):
        self.data = {}
        self.permanent_failures = set()
    
    def is_permanent_failure(self, identifier):
        return identifier in self.permanent_failures
    
    def record_permanent_failure(self, identifier, reason):
        self.permanent_failures.add(identifier)
    
    def get_permanent_failures_batch(self, identifiers):
        return {
            identifier: {"user_status": "suspended"}
            for identifier in identifiers
            if identifier in self.permanent_failures
        }
    
    def save_block_history(self, user_id, status):
        self.data[user_id] = {
            'status': status,
            'timestamp': time.time()
        }

# モックデータベースを使用したテスト
def test_permanent_failure_handling():
    mock_db = MockDatabase()
    
    # 永続的失敗を設定
    mock_db.record_permanent_failure("suspended_user", "suspended")
    
    # 検証
    assert mock_db.is_permanent_failure("suspended_user") == True
    assert mock_db.is_permanent_failure("normal_user") == False
```

## パフォーマンステスト

### 実行時間測定
```python
import time
import statistics

def benchmark_function(func, *args, iterations=5, **kwargs):
    """関数のベンチマーク測定"""
    times = []
    
    for _ in range(iterations):
        start_time = time.time()
        result = func(*args, **kwargs)
        elapsed = time.time() - start_time
        times.append(elapsed)
    
    avg_time = statistics.mean(times)
    std_dev = statistics.stdev(times) if len(times) > 1 else 0
    
    return {
        'average_time': avg_time,
        'std_deviation': std_dev,
        'min_time': min(times),
        'max_time': max(times),
        'iterations': iterations,
        'last_result': result
    }

# パフォーマンステストの実行
def test_batch_processing_performance():
    """バッチ処理のパフォーマンステスト"""
    db = DatabaseManager("test.db")
    
    # テストデータ
    test_users = [f"user_{i}" for i in range(1000)]
    
    # 個別処理（比較用）
    def individual_processing():
        results = []
        for user in test_users[:100]:  # 100件に制限
            result = db.is_permanent_failure(user)
            results.append(result)
        return results
    
    # バッチ処理
    def batch_processing():
        return db.get_permanent_failures_batch(test_users[:100])
    
    # ベンチマーク実行
    individual_benchmark = benchmark_function(individual_processing)
    batch_benchmark = benchmark_function(batch_processing)
    
    # 結果比較
    improvement_ratio = individual_benchmark['average_time'] / batch_benchmark['average_time']
    
    print(f"個別処理: {individual_benchmark['average_time']:.4f}秒")
    print(f"バッチ処理: {batch_benchmark['average_time']:.4f}秒")
    print(f"改善率: {improvement_ratio:.1f}倍")
    
    # パフォーマンス要件チェック
    assert batch_benchmark['average_time'] < 0.1  # 100ms以下
    assert improvement_ratio > 10  # 10倍以上の改善
```

### メモリ使用量テスト
```python
import psutil
import os

def measure_memory_usage(func, *args, **kwargs):
    """メモリ使用量の測定"""
    import gc
    
    # ガベージコレクション実行
    gc.collect()
    
    # 実行前メモリ使用量
    process = psutil.Process(os.getpid())
    memory_before = process.memory_info().rss / 1024 / 1024  # MB
    
    # 関数実行
    result = func(*args, **kwargs)
    
    # 実行後メモリ使用量
    memory_after = process.memory_info().rss / 1024 / 1024  # MB
    memory_increase = memory_after - memory_before
    
    return {
        'result': result,
        'memory_before_mb': memory_before,
        'memory_after_mb': memory_after,
        'memory_increase_mb': memory_increase
    }

def test_memory_usage():
    """メモリ使用量テスト"""
    
    def process_large_dataset():
        # 大量データの処理
        large_data = [f"user_{i}" for i in range(10000)]
        return process_users_batch(large_data)
    
    memory_stats = measure_memory_usage(process_large_dataset)
    
    print(f"処理前メモリ: {memory_stats['memory_before_mb']:.1f}MB")
    print(f"処理後メモリ: {memory_stats['memory_after_mb']:.1f}MB")
    print(f"メモリ増加量: {memory_stats['memory_increase_mb']:.1f}MB")
    
    # メモリリーク検出
    assert memory_stats['memory_increase_mb'] < 100  # 100MB以下の増加
```

## 自動テストスイート

### テスト実行スクリプト
```python
import unittest
import sys
import os

class TestRunner:
    """テストランナー"""
    
    def __init__(self):
        self.test_results = {}
    
    def run_unit_tests(self):
        """単体テストの実行"""
        print("🧪 単体テスト実行中...")
        
        # テストディスカバリー
        loader = unittest.TestLoader()
        suite = loader.discover('tests/unit', pattern='test_*.py')
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        self.test_results['unit'] = {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success': result.wasSuccessful()
        }
        
        return result.wasSuccessful()
    
    def run_integration_tests(self):
        """統合テストの実行"""
        print("🔗 統合テスト実行中...")
        
        loader = unittest.TestLoader()
        suite = loader.discover('tests/integration', pattern='test_*.py')
        
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)
        
        self.test_results['integration'] = {
            'tests_run': result.testsRun,
            'failures': len(result.failures),
            'errors': len(result.errors),
            'success': result.wasSuccessful()
        }
        
        return result.wasSuccessful()
    
    def run_performance_tests(self):
        """パフォーマンステストの実行"""
        print("⚡ パフォーマンステスト実行中...")
        
        # カスタムパフォーマンステスト
        performance_results = []
        
        # バッチ処理パフォーマンス
        batch_result = test_batch_processing_performance()
        performance_results.append(batch_result)
        
        # メモリ使用量
        memory_result = test_memory_usage()
        performance_results.append(memory_result)
        
        self.test_results['performance'] = {
            'tests_run': len(performance_results),
            'all_passed': all(performance_results)
        }
        
        return all(performance_results)
    
    def run_all_tests(self):
        """全テストの実行"""
        print("🚀 全テスト実行開始")
        print("=" * 50)
        
        # 各テストスイートの実行
        unit_success = self.run_unit_tests()
        integration_success = self.run_integration_tests()
        performance_success = self.run_performance_tests()
        
        # 結果サマリー
        print("\n📊 テスト結果サマリー:")
        print("-" * 30)
        
        for test_type, results in self.test_results.items():
            status = "✅ PASS" if results.get('success', results.get('all_passed', False)) else "❌ FAIL"
            print(f"{test_type.upper()}: {status}")
            
            if 'tests_run' in results:
                print(f"  実行: {results['tests_run']}件")
                if 'failures' in results:
                    print(f"  失敗: {results['failures']}件")
                if 'errors' in results:
                    print(f"  エラー: {results['errors']}件")
        
        # 全体結果
        overall_success = unit_success and integration_success and performance_success
        overall_status = "✅ 全テスト成功" if overall_success else "❌ テスト失敗"
        print(f"\n{overall_status}")
        
        return overall_success

# 使用例
if __name__ == "__main__":
    runner = TestRunner()
    success = runner.run_all_tests()
    sys.exit(0 if success else 1)
```

## 継続的インテグレーション

### GitHub Actions設定例
```yaml
# .github/workflows/test.yml
name: Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.8, 3.9, 3.10, 3.11]
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v3
      with:
        python-version: ${{ matrix.python-version }}
    
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-test.txt
    
    - name: Run unit tests
      run: |
        python -m pytest tests/unit/ -v --cov=twitter_blocker
    
    - name: Run integration tests
      run: |
        python -m pytest tests/integration/ -v
    
    - name: Run performance tests
      run: |
        python -m pytest tests/performance/ -v
    
    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
```

## テストデータ管理

### テストデータセット
```python
# tests/fixtures/test_data.py
TEST_USERS = {
    "normal_user": {
        "screen_name": "normal_user",
        "user_id": "123456789",
        "status": "active"
    },
    "suspended_user": {
        "screen_name": "suspended_user", 
        "user_id": "987654321",
        "status": "suspended",
        "error": "User has been suspended"
    },
    "not_found_user": {
        "screen_name": "deleted_user",
        "user_id": None,
        "status": "not_found",
        "error": "User not found"
    }
}

API_RESPONSES = {
    "user_lookup_success": {
        "data": {
            "user": {
                "rest_id": "123456789",
                "legacy": {
                    "screen_name": "normal_user",
                    "name": "Normal User"
                }
            }
        }
    },
    "user_lookup_suspended": {
        "errors": [{
            "message": "User has been suspended",
            "user_status": "suspended"
        }]
    },
    "rate_limit_error": {
        "errors": [{
            "message": "Rate limit exceeded",
            "code": 88
        }]
    }
}

def get_test_database():
    """テスト用データベースの作成"""
    import sqlite3
    import tempfile
    
    # 一時ファイル作成
    db_file = tempfile.mktemp(suffix='.db')
    
    # テーブル作成
    with sqlite3.connect(db_file) as conn:
        conn.execute("""
            CREATE TABLE block_history (
                id INTEGER PRIMARY KEY,
                user_id TEXT,
                screen_name TEXT,
                status TEXT,
                user_status TEXT,
                error_message TEXT,
                timestamp REAL
            )
        """)
        
        # テストデータ挿入
        test_records = [
            ("987654321", "suspended_user", "failed", "suspended", "User suspended", time.time()),
            ("111111111", "deleted_user", "failed", "not_found", "User not found", time.time())
        ]
        
        conn.executemany("""
            INSERT INTO block_history (user_id, screen_name, status, user_status, error_message, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, test_records)
    
    return db_file
```

## 品質チェックリスト

### リリース前チェック
```markdown
## 機能テスト
- [ ] 全ての単体テストがパス
- [ ] 統合テストがパス
- [ ] エンドツーエンドテストがパス
- [ ] パフォーマンステストがパス

## セキュリティテスト
- [ ] 認証情報の適切な管理
- [ ] ファイル権限の設定
- [ ] ログからの機密情報除外
- [ ] SQLインジェクション対策

## パフォーマンステスト
- [ ] バッチ処理の効率確認
- [ ] メモリ使用量の妥当性
- [ ] レート制限の遵守
- [ ] 大量データでの動作確認

## 互換性テスト
- [ ] 複数のPythonバージョンでの動作
- [ ] 異なるOS環境での動作
- [ ] 依存関係の互換性確認

## ドキュメント
- [ ] README.mdの更新
- [ ] APIドキュメントの更新
- [ ] 変更履歴の記録
- [ ] トラブルシューティングガイドの更新
```