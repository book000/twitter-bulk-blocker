# コードレビュー観点

## パフォーマンス観点

### バッチ処理の確認事項
```python
# チェックポイント
def review_batch_processing(code):
    """
    ✅ 確認事項:
    - N+1問題が発生していないか？
    - バッチサイズは適切か？（推奨: 50-100件）
    - バッチ間の待機時間は設定されているか？
    - メモリ使用量は考慮されているか？
    """
    
    # ❌ 問題のあるコード例
    for user_id in user_list:  # ループ内個別処理
        result = api.get_user(user_id)  # N+1問題
        db.save(user_id, result)       # 個別DB保存
    
    # ✅ 改善されたコード例  
    batch_size = 50
    for i in range(0, len(user_list), batch_size):
        batch = user_list[i:i + batch_size]
        results = api.get_users_batch(batch)  # バッチAPI
        db.save_batch(results)                # バッチ保存
        time.sleep(1)                         # レート制限対策
```

### キャッシュ活用の確認
```python
def review_cache_usage(code):
    """
    ✅ 確認事項:
    - キャッシュ戦略は適切か？（lookup/profiles/relationships）
    - キャッシュTTLは用途に応じて設定されているか？
    - キャッシュ無効化処理は適切に実装されているか？
    - キャッシュミス時のフォールバック処理があるか？
    """
    
    # レビュー質問例:
    # - なぜこのデータをキャッシュしないのか？
    # - TTL設定の根拠は？
    # - このキャッシュ無効化タイミングは適切か？
```

## エラーハンドリング観点

### エラー分類の確認
```python
def review_error_handling(code):
    """
    ✅ 確認事項:
    - 永続的失敗と一時的失敗が適切に分類されているか？
    - リトライ回数・間隔は適切か？
    - エラーログは十分な情報を含んでいるか？
    - 例外が適切に処理されているか？
    """
    
    # 確認すべきエラーパターン
    error_patterns = {
        "permanent": ["suspended", "not_found", "deactivated"],
        "temporary": ["rate_limit", "server_error", "network_timeout"],
        "auth": ["invalid_token", "csrf_mismatch"]
    }
    
    # レビュー質問例:
    # - このエラーでリトライする必要があるか？
    # - エラー情報は十分にログに記録されているか？
    # - ユーザーに適切なフィードバックが提供されるか？
```

### リトライ戦略の評価
```python
def review_retry_strategy(code):
    """
    ✅ 確認事項:
    - 最大リトライ回数は適切か？（推奨: 3回以下）
    - 指数バックオフが実装されているか？
    - 永続的失敗でリトライしていないか？
    - リトライ間隔は適切か？
    """
    
    # 問題のあるリトライ実装例
    def bad_retry():
        while True:  # ❌ 無限リトライ
            try:
                return api_call()
            except:  # ❌ 全例外をキャッチ
                time.sleep(5)  # ❌ 固定間隔
    
    # 適切なリトライ実装例
    def good_retry(max_retries=3):
        for attempt in range(max_retries):
            try:
                return api_call()
            except PermanentError:  # ✅ 永続的失敗は即座に終了
                raise
            except TemporaryError:  # ✅ 一時的失敗のみリトライ
                if attempt == max_retries - 1:
                    raise
                wait_time = (2 ** attempt) * 60  # ✅ 指数バックオフ
                time.sleep(wait_time)
```

## セキュリティ観点

### 認証情報の取り扱い
```python
def review_auth_security(code):
    """
    ✅ 確認事項:
    - 認証情報がログに出力されていないか？
    - クッキーファイルの権限は適切か？
    - 不要な認証情報を保存していないか？
    - 機密情報がコードにハードコーディングされていないか？
    """
    
    # ❌ セキュリティ問題例
    def bad_security():
        cookies = load_cookies()
        logger.info(f"使用クッキー: {cookies}")  # ❌ ログに機密情報
        
        with open('cookies.json', 'w') as f:  # ❌ 権限設定なし
            json.dump(cookies, f)
    
    # ✅ セキュリティ配慮例
    def good_security():
        cookies = load_cookies()
        logger.info("認証情報を読み込みました")  # ✅ 機密情報なし
        
        with open('cookies.json', 'w') as f:
            json.dump(cookies, f)
        os.chmod('cookies.json', 0o600)  # ✅ 適切な権限設定
```

### 入力値検証
```python
def review_input_validation(code):
    """
    ✅ 確認事項:
    - ユーザー入力の検証は十分か？
    - SQLインジェクション対策はあるか？
    - ファイルパスの検証は適切か？
    - APIレスポンスの検証は行われているか？
    """
    
    # レビュー質問例:
    # - この入力値は信頼できるか？
    # - 不正な値が渡される可能性はないか？
    # - エラーメッセージから内部情報が漏洩しないか？
```

## コード品質観点

### 可読性の確認
```python
def review_code_readability(code):
    """
    ✅ 確認事項:
    - 関数・変数名は目的を明確に表しているか？
    - 複雑な処理にコメントはあるか？
    - 関数の責務は明確に分離されているか？
    - マジックナンバーは定数として定義されているか？
    """
    
    # ❌ 可読性の低いコード例
    def process(data):  # ❌ 曖昧な関数名
        for i in data:
            if i[1] == 0:  # ❌ マジックナンバー
                do_something(i)
    
    # ✅ 可読性の高いコード例
    def block_users_from_list(user_list):  # ✅ 明確な関数名
        STATUS_ACTIVE = 0  # ✅ 定数定義
        
        for user in user_list:
            if user.status == STATUS_ACTIVE:  # ✅ 意味の明確な比較
                self.block_user(user)
```

### テスタビリティの評価
```python
def review_testability(code):
    """
    ✅ 確認事項:
    - 依存関係は注入可能か？
    - 副作用は最小限に抑えられているか？
    - 関数は単一責任原則に従っているか？
    - グローバル変数への依存はないか？
    """
    
    # ❌ テストしにくいコード例
    def process_user_bad(user_id):
        api = TwitterAPI()  # ❌ 依存関係がハードコーディング
        result = api.get_user(user_id)
        print(f"処理完了: {result}")  # ❌ 副作用（出力）
        save_to_file(result)  # ❌ 副作用（ファイル書き込み）
        return result
    
    # ✅ テストしやすいコード例
    def process_user_good(self, user_id, api=None):
        api = api or self.api  # ✅ 依存関係注入可能
        result = api.get_user(user_id)
        return result  # ✅ 副作用なし、戻り値のみ
```

## アーキテクチャ観点

### 責務分離の確認
```python
def review_separation_of_concerns(code):
    """
    ✅ 確認事項:
    - 各クラス・関数の責務は明確か？
    - ビジネスロジックとインフラ層は分離されているか？
    - 設定管理は適切に抽象化されているか？
    - 依存関係の方向は適切か？
    """
    
    # レビュー質問例:
    # - この関数は複数の責務を持っていないか？
    # - データベース操作とビジネスロジックが混在していないか？
    # - 設定値がハードコーディングされていないか？
```

### 拡張性の評価
```python
def review_extensibility(code):
    """
    ✅ 確認事項:
    - 新機能追加時の影響範囲は明確か？
    - インターフェースは適切に定義されているか？
    - 設定による動作変更は可能か？
    - プラグイン的な拡張が可能か？
    """
    
    # 拡張性の良い設計例
    class ProcessorBase:
        def process(self, data):
            raise NotImplementedError
    
    class TwitterBlockProcessor(ProcessorBase):
        def process(self, user_data):
            # Twitter固有の実装
            pass
    
    class InstagramBlockProcessor(ProcessorBase):
        def process(self, user_data):
            # Instagram固有の実装
            pass
```

## レビューチェックリスト

### 必須確認事項
```markdown
## パフォーマンス
- [ ] N+1問題は発生していないか？
- [ ] バッチ処理は適切に実装されているか？
- [ ] キャッシュ戦略は効率的か？
- [ ] メモリ使用量は適切か？

## エラーハンドリング
- [ ] 永続的失敗と一時的失敗が適切に分類されているか？
- [ ] リトライ戦略は適切か？
- [ ] エラーログは十分な情報を含んでいるか？
- [ ] 例外処理は漏れていないか？

## セキュリティ
- [ ] 認証情報がログに出力されていないか？
- [ ] ファイル権限は適切に設定されているか？
- [ ] 入力値検証は十分か？
- [ ] 機密情報の取り扱いは適切か？

## コード品質
- [ ] 関数・変数名は明確か？
- [ ] 複雑な処理にコメントはあるか？
- [ ] 責務分離は適切か？
- [ ] テストしやすい設計か？

## アーキテクチャ
- [ ] 依存関係の方向は適切か？
- [ ] 拡張性は考慮されているか？
- [ ] 設定管理は適切か？
- [ ] インターフェースは明確か？
```

### レビューフィードバックテンプレート

```markdown
## パフォーマンス改善提案
**問題点**: ループ内でのAPI個別呼び出しが発生している
**影響**: 処理時間が線形に増大し、レート制限に抵触するリスク
**改善案**: バッチAPIを使用して一括処理に変更
**参考**: `.claude/guides/performance-optimization.md`の「バッチ処理最適化」を参照

## セキュリティ懸念
**問題点**: 認証トークンがログに出力されている
**リスク**: ログファイルから認証情報が漏洩する可能性
**改善案**: ログ出力時に機密情報をマスク処理
**参考**: `.claude/patterns/anti-patterns.md`の「セキュリティアンチパターン」を参照

## 設計改善提案
**問題点**: 責務が混在している関数がある
**影響**: テストが困難で、変更時の影響範囲が不明確
**改善案**: 関数を責務ごとに分割
**参考**: `.claude/patterns/recommended.md`の「責務分離パターン」を参照
```