# GitHub Copilot Instructions - Twitter Bulk Blocker

## プロジェクト概要

**Twitter Bulk Blocker** は、Twitter/X.comで大量のユーザーを効率的にブロックするためのエンタープライズグレードのPythonツールです。高度なキャッシュ戦略、バッチ処理、包括的なエラーハンドリングを備えています。

### 技術スタック
- **Python 3.x** with requests, pytz, sqlite3
- **Twitter GraphQL API v2 / REST API v1.1** 
- **SQLite with WAL mode** (高速並行処理)
- **Docker** (コンテナ環境対応)
- **3層キャッシュアーキテクチャ** (Lookup/Profile/Relationship)

### アーキテクチャ概要
```
twitter_blocker/
├── api.py          # Twitter API管理（GraphQL/REST）+ 3層キャッシュ
├── database.py     # SQLite管理 + 永続的失敗キャッシュ + バッチ最適化
├── manager.py      # ワークフロー制御 + バッチ処理制御 + セッション管理
├── config.py       # 設定・スキーマ・Cookie管理
├── retry.py        # リトライ判定ロジック（永続的/一時的失敗分類）
├── stats.py        # 統計表示・分析・詳細レポート
├── version.py      # バージョン管理システム
└── その他の監視・分析モジュール
```

## コーディング規約とベストプラクティス

### 基本方針
1. **パフォーマンス要求**: 50件/秒以上、キャッシュヒット率80%以上維持
2. **永続的失敗の事前チェック**: suspended/not_found/deactivatedでAPI呼び出し回避
3. **バッチ処理必須**: N+1問題の徹底回避
4. **リソース管理**: SQLite接続はcontext manager必須使用
5. **日本語コメント**: コードコメント、ドキュメント、エラーメッセージは日本語

### 推奨実装パターン

#### ✅ 推奨: バッチ処理 + 事前チェック
```python
# 複数ユーザーの一括取得でAPI効率化
permanent_failures = self.database.get_permanent_failures_batch(batch_ids, user_format)
for user_id in batch_ids:
    if user_id in permanent_failures:
        continue  # API呼び出しスキップ
```

#### ❌ 避ける: 個別処理でのN+1問題
```python
# これは避ける - 個別DB呼び出しによるN+1問題
for user in users:
    if self.database.is_permanent_failure(user):  # 個別DB呼び出し
        continue
```

#### ✅ 推奨: Context Manager使用
```python
# SQLite接続は必ずcontext managerで管理
with sqlite3.connect(self.db_path) as conn:
    cursor = conn.cursor()
    # 処理...
```

#### ✅ 推奨: 包括的エラーハンドリング
```python
try:
    response = api_call()
except TwitterAPIError as e:
    if e.is_permanent_failure():
        # 永続的失敗として記録、リトライ対象外
        self.database.mark_permanent_failure(user_id, e.error_type)
    else:
        # 一時的失敗として記録、リトライ対象
        self.database.mark_temporary_failure(user_id, e.error_message)
```

### エラーハンドリング分類

#### 永続的失敗（API呼び出し禁止）
- `suspended` - アカウント停止
- `not_found` - ユーザー不存在
- `deactivated` - アカウント無効化

#### 一時的失敗（リトライ対象）
- `unavailable` - 一時的な利用不可
- `rate_limit` - レート制限
- `server_error` - サーバーエラー（500, 502, 503, 504）

#### 認証エラー
- Cookie再読み込み + 自動復旧フロー

## モジュール別開発ガイドライン

### api.py - Twitter API管理
- GraphQL API（ユーザー情報取得）とREST API（ブロック実行）の管理
- 3層キャッシュシステム（Lookup/Profile/Relationship）
- レート制限の監視と遵守
- 拡張ヘッダー対応（x-client-transaction-id、x-xp-forwarded-for）

### database.py - データベース管理
- SQLite WALモードでの高速並行処理
- 永続的失敗キャッシュの管理
- バッチ処理でのデータ取得最適化
- ユニークキー制約による重複防止

### manager.py - ワークフロー制御
- バッチ処理制御とセッション管理
- 安全性チェック（フォロー関係確認）
- 進捗表示とリアルタイム統計
- 自動リトライ機能

### config.py - 設定管理
- 環境変数、コマンドライン引数、デフォルト値の3層設定
- Cookie情報の安全な管理
- スキーマ検証（ユーザーファイル形式）

### stats.py - 統計分析
- 詳細な処理統計とエラー分析
- リトライ候補の分類表示
- パフォーマンス指標の監視

## セキュリティとプライバシー

### 必須事項
1. **Cookie情報の保護**: 認証情報は安全に管理し、ログ出力時はマスク
2. **レート制限遵守**: Twitter APIの制限を厳格に守る
3. **フォロー関係の尊重**: フォロー中/フォロワーのユーザーは自動スキップ
4. **重複防止**: 一度ブロックしたユーザーは再度ブロックしない

### Twitter API制限
- **GraphQLレート制限**: 150リクエスト/15分
- **RESTレート制限**: 300ブロック/15分
- **最適バッチサイズ**: 50件
- **推奨リクエスト間隔**: 1.0秒以上

## パフォーマンス要件

### 目標指標
- **処理速度**: 50件/秒以上
- **キャッシュヒット率**: 80%以上
- **バッチサイズ**: 50件（最適値）
- **キャッシュTTL**: 30日

### 最適化テクニック
1. **バッチ処理**: 複数ユーザーの一括取得
2. **キャッシュ活用**: ユーザー情報とリレーション情報のキャッシュ
3. **事前フィルタリング**: 永続的失敗ユーザーのAPI呼び出し回避
4. **並行処理**: SQLite WALモードでの同時アクセス最適化

## テストとデバッグ

### デバッグ機能
```bash
# 特定ユーザーのテスト
python3 -m twitter_blocker --test-user username --debug

# エラー分析
python3 -m twitter_blocker --debug-errors

# 統計表示
python3 -m twitter_blocker --stats
```

### テスト推奨パターン
1. **少数テスト**: `--max-users 5` で動作確認
2. **特定ユーザーテスト**: `--test-user` で個別確認
3. **段階的実行**: テスト → 少数実行 → 本格実行

## Docker対応

### 環境変数
```bash
TWITTER_COOKIES_PATH=/data/cookies.json
TWITTER_USERS_FILE=/data/users.json  
TWITTER_BLOCK_DB=/data/block_history.db
CACHE_DIR=/data/cache
```

### 推奨実行パターン
```bash
# ボリュームマウントでのデータ管理
docker run --rm -v ./data:/app/data twitter-blocker --stats
```

## バージョン管理とリリース

### バージョン取得優先順位
1. **Git tag/branch** (開発環境)
2. **環境変数**: `APPLICATION_VERSION`
3. **ファイル**: `.app-version`
4. **デフォルト**: "development"

### Conventional Commits
- **feat**: 新機能追加
- **fix**: バグ修正  
- **docs**: ドキュメント変更
- **refactor**: リファクタリング
- **perf**: パフォーマンス改善
- **test**: テスト追加・修正

## コミュニケーション規約

### PR・Issue対応
- **会話は日本語**: PR本文、レビューコメント、Issue議論は日本語
- **PRタイトルは英語**: Conventional Commits準拠
- **コミットメッセージ**: Conventional Commits準拠（英語）

### 例
```
PRタイトル: feat: add advanced header enhancement for anti-bot systems
PR本文: Twitter/Xのアンチボットシステムに対応するため、動的ヘッダー生成機能を追加しました...
コミット: feat: implement x-client-transaction-id dynamic generation
```

## 拡張機能

### 拡張ヘッダー機能
- **動的トランザクションID**: `x-client-transaction-id`の自動生成
- **地域IP偽装**: `x-xp-forwarded-for`（日本主要ISP）
- **段階的導入**: `--disable-header-enhancement`、`--enable-forwarded-for`

### 監視・分析機能
- **リアルタイム統計**: 処理進捗とエラー分析
- **パフォーマンス監視**: APIレート使用量、キャッシュ効率
- **長期履歴分析**: 24時間エラー履歴の追跡

## 開発環境セットアップ

### 必要ファイル
1. `cookies.json` - X.comからエクスポートしたクッキー
2. `users.json` - ブロック対象ユーザーリスト
3. `block_history.db` - ブロック履歴データベース（自動作成）

### 推奨ディレクトリ構成
```
project/
├── data/
│   ├── cookies.json
│   ├── users.json
│   ├── block_history.db
│   └── cache/
└── twitter_blocker/
```

## 重要な注意事項

1. **法的遵守**: Twitter/X.comの利用規約を厳格に遵守
2. **適切な使用**: 過度なAPI利用を避け、適切な間隔での実行
3. **責任ある開発**: 本ツールの使用は自己責任
4. **プライバシー保護**: ユーザー情報の適切な管理とプライバシー尊重

このガイドラインに従って、安全で効率的なTwitter一括ブロックツールの開発と保守を行ってください。