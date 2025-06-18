# twitter-bulk-blocker

Twitter/X.comで大量のユーザーを効率的にブロックするPythonツールです。クッキー認証とGraphQL APIを使用し、安全で確実なブロック処理を提供します。

## ✨ 特徴

- 🔒 **安全性重視**: フォロー関係チェック、重複防止、リトライ機能
- 📊 **詳細統計**: リアルタイム進捗表示、処理結果の詳細レポート
- 🏗️ **モジュール設計**: 保守しやすい分離された設計
- 🐳 **Docker対応**: コンテナ環境での実行をサポート
- 🔄 **自動リトライ**: 一時的エラーの自動再試行（suspendedは除外）
- 🎛️ **柔軟な設定**: 環境変数・コマンドライン引数・デフォルト値による多層設定
- 🧪 **強力なデバッグ機能**: 詳細ログ、特定ユーザーテスト、エラー分析

## 🚀 クイックスタート

### 必要なファイル

1. **`cookies.json`** - X.comからエクスポートしたクッキー情報
2. **ユーザーファイル** - ブロック対象ユーザーリスト（JSON形式）

### 基本的な使用方法

```bash
# 1. テスト実行（最初の5人のみ）
python3 -m twitter_blocker

# 2. 統計表示
python3 -m twitter_blocker --stats

# 3. 本格実行
python3 -m twitter_blocker --all

# 4. 自動リトライ付き本格実行
python3 -m twitter_blocker --all --auto-retry

# 5. 特定ユーザーのテスト
python3 -m twitter_blocker --test-user example_user

# 6. デバッグモードで実行
python3 -m twitter_blocker --debug --test-user example_user
```

## 📋 ユーザーファイル形式

ユーザーファイルは以下の形式で指定してください：

### スクリーンネーム形式

```json
{
  "format": "screen_name",
  "users": [
    "example_user",
    "another_user",
    "spam_account"
  ]
}
```

### ユーザーID形式

```json
{
  "format": "user_id",
  "users": [
    "1316469127914029057",
    "1234567890123456789",
    "9876543210987654321"
  ]
}
```

## ⚙️ コマンドオプション

### 実行制御

- `--all` - 全ユーザーを処理（本格実行）
- `--retry` - 失敗したユーザーのリトライ処理のみ実行
- `--auto-retry` - `--all`と組み合わせて使用：実行後に自動でリトライ
- `--reset-retry` - 失敗ユーザーのリトライ回数をリセット
- `--stats` - 処理統計を表示

### 処理制御

- `--max-users N` - 処理するユーザーの最大数を指定
- `--delay N` - リクエスト間隔を秒で指定（デフォルト: 1.0）

### デバッグ・テスト機能

- `--debug` - デバッグモードで実行（詳細なAPI応答を表示）
- `--test-user SCREEN_NAME` - 特定のユーザーのみテスト（デバッグ用）
- `--debug-errors` - 失敗したエラーメッセージのサンプルを表示（デバッグ用）

**デバッグ機能の使用例:**

```bash
# 特定ユーザーのAPI応答を詳細確認
python3 -m twitter_blocker --debug --test-user problematic_user

# エラーメッセージの実例を確認
python3 -m twitter_blocker --debug-errors

# デバッグモードで本格実行
python3 -m twitter_blocker --all --debug --max-users 10
```

### ファイル・ディレクトリ指定

- `--cookies PATH` - クッキーファイルのパス（デフォルト: cookies.json）
- `--users-file PATH` - ブロック対象ユーザーファイルのパス（デフォルト: video_misuse_detecteds.json）
- `--db PATH` - ブロック履歴データベースのパス（デフォルト: block_history.db）
- `--cache-dir PATH` - キャッシュディレクトリのパス（デフォルト: /data/cache）

## 🔧 設定方法

### 1. コマンド引数で指定

```bash
python3 -m twitter_blocker --all \
  --cookies /path/to/cookies.json \
  --users-file /path/to/users.json \
  --db /path/to/database.db \
  --cache-dir /path/to/cache
```

### 2. 環境変数で指定

```bash
export TWITTER_COOKIES_PATH=/path/to/cookies.json
export TWITTER_USERS_FILE=/path/to/users.json
export TWITTER_BLOCK_DB=/path/to/database.db
export CACHE_DIR=/path/to/cache

python3 -m twitter_blocker --all
```

### 3. 設定ファイルの優先順位

1. **コマンド引数**（最優先）
2. **環境変数**
3. **デフォルト値**

### 4. 推奨設定パターン

**開発・テスト環境:**
```bash
export CACHE_DIR=./cache
export TWITTER_COOKIES_PATH=./cookies.json
export TWITTER_USERS_FILE=./test_users.json
```

**本番環境:**
```bash
export CACHE_DIR=/var/lib/twitter-blocker/cache
export TWITTER_COOKIES_PATH=/etc/twitter-blocker/cookies.json
export TWITTER_USERS_FILE=/var/lib/twitter-blocker/users.json
export TWITTER_BLOCK_DB=/var/lib/twitter-blocker/database.db
```

## 🐳 Docker使用方法

### 基本実行

```bash
# イメージビルド
docker build -t twitter-blocker .

# ヘルプ表示
docker run --rm twitter-blocker

# 統計表示（データマウント必要）
docker run --rm -v ./data:/app/data twitter-blocker --stats

# 本格実行
docker run --rm -v ./data:/app/data twitter-blocker --all --auto-retry

# デバッグモードでテスト
docker run --rm -v ./data:/app/data twitter-blocker --debug --test-user example_user
```

### Docker環境変数

Docker環境では以下の環境変数が事前設定されています：

- `TWITTER_COOKIES_PATH=/data/cookies.json`
- `TWITTER_USERS_FILE=/data/users.json`
- `TWITTER_BLOCK_DB=/data/block_history.db`
- `CACHE_DIR=/data/cache`

### カスタム設定でDocker実行

```bash
# 環境変数をオーバーライド
docker run --rm \
  -v ./data:/app/data \
  -e CACHE_DIR=/app/data/custom_cache \
  -e TWITTER_USERS_FILE=/app/data/my_users.json \
  twitter-blocker --all

# ローカルディレクトリを別の場所にマウント
docker run --rm \
  -v ./cookies:/app/cookies:ro \
  -v ./data:/app/data \
  -e TWITTER_COOKIES_PATH=/app/cookies/cookies.json \
  twitter-blocker --stats
```

### Docker Compose

```yaml
version: '3.8'
services:
  twitter-blocker:
    build: .
    volumes:
      - ./data:/app/data
    environment:
      - CACHE_DIR=/app/data/cache
      - TWITTER_COOKIES_PATH=/app/data/cookies.json
      - TWITTER_USERS_FILE=/app/data/users.json
      - TWITTER_BLOCK_DB=/app/data/database.db
    command: ["--stats"]
```

```bash
# 実行
docker-compose run twitter-blocker
```

## 🛡️ 安全機能

### 重複防止システム

- **SQLiteデータベース**による永続的な履歴管理
- 一度ブロックしたユーザーは再度ブロックしない
- ユニークキー制約による重複実行の防止

### 高度な自動リトライ機能

- **一時的エラーの自動検出**: 429（レート制限）、500、502、503、504
- **指数バックオフ**によるリトライ間隔の調整
- **最大10回**までのリトライ制限
- **suspendedユーザーの除外**: 永続的な失敗として扱い、リトライしない
- **リトライ統計の詳細表示**: 成功/失敗の詳細分析

### 包括的安全性チェック

- **フォロー関係の検証**: フォロー中/フォロワーのユーザーは自動スキップ
- **既存ブロック状態の確認**: 重複ブロックを防止
- **ユーザー状態の詳細判定**: active/suspended/deactivated/not_found
- **API応答の詳細検証**: 各種エラータイプの適切な処理

### パフォーマンス最適化

- **APIキャッシュシステム**: ユーザー情報とリレーション情報の効率的キャッシュ
- **バッチ処理**: 複数ユーザーの一括取得でAPI効率化
- **レート制限の遵守**: 適切な間隔でのAPI呼び出し

## 📊 詳細な統計・デバッグ機能

### 統計表示機能

```bash
$ python3 -m twitter_blocker --stats
=== 処理統計 ===
全対象ユーザー: 2,308人
ブロック済み: 1,245人 (53.9%)
残り未処理: 1,063人
失敗: 12人
  - リトライ上限到達: 2人
  - リトライ可能: 3人
  - エラータイプ別:
    suspended: 8人
    unavailable: 4人
  - エラーメッセージサンプル (other):
    1. User not found
    2. Rate limit exceeded
    3. Authentication required

リトライ候補: 3人
  - unavailable: 3人
```

### エラー分析機能

```bash
# 失敗したエラーの詳細分析
python3 -m twitter_blocker --debug-errors

=== エラーメッセージサンプル ===
 1. User account is suspended
 2. Rate limit exceeded. Try again later
 3. The following features cannot be null: rweb_tipjar_consumption_enabled
 4. User not found
 5. Authentication credentials were invalid
```

### デバッグモード

```bash
# 特定ユーザーの詳細分析
python3 -m twitter_blocker --debug --test-user problematic_user

=== テストユーザー: problematic_user ===
[API Response - get_user_info] problematic_user
  Status Code: 200
  Rate Limit: 144/150
  Reset Time: 2025-06-18 08:15:49 JST
  Response Headers:
    content-type: application/json; charset=utf-8
    x-rate-limit-limit: 150
    x-rate-limit-remaining: 144
  Response Body: {"data": {"user": {"result": {...}}}}

ユーザー情報取得成功:
  ID: 982085873788489728
  名前: Example User
  フォロー関係: False
  フォロワー関係: False
  ブロック状態: True
```

## 🔄 処理フロー

### 通常の処理フロー

1. **設定検証** - ファイル存在確認と環境変数読み込み
2. **スキーマ検証** - ユーザーファイル形式の確認
3. **キャッシュ初期化** - ディレクトリ作成とキャッシュ準備
4. **ユーザー情報取得** - GraphQL APIでユーザー状態確認
5. **安全性チェック** - フォロー関係とユーザー状態を確認
6. **ブロック実行** - REST APIでブロック処理
7. **結果記録** - SQLiteデータベースに履歴保存
8. **リトライ判定** - 失敗時にリトライ対象かどうか判定

### API最適化フロー

1. **キャッシュ確認**: 既存のキャッシュデータをチェック
2. **バッチ処理**: 複数ユーザーの情報を一括取得
3. **レート制限管理**: API制限を監視し適切な間隔で実行
4. **エラーハンドリング**: 各種エラータイプに応じた適切な処理

## 🛠️ トラブルシューティング

### よくある問題と解決方法

#### アカウントロック（エラー326）

X.comでアカウントのロックを解除してから再実行してください:
<https://twitter.com/account/access>

#### クッキーの有効期限切れ

```
Error: Authentication credentials were invalid
```

X.comで再ログインしてcookies.jsonを更新してください。

#### レート制限（エラー429）

```bash
# リクエスト間隔を長くする
python3 -m twitter_blocker --all --delay 2.0

# または少数ずつ処理
python3 -m twitter_blocker --all --max-users 50
```

#### GraphQL APIエラー（400エラー）

最新のTwitter GraphQL APIの要求により、必須フィーチャーフラグが追加されています。このツールは最新の要求に対応済みです。

#### ファイル形式エラー

ユーザーファイルが正しい形式になっているか確認してください:

```json
{
  "format": "screen_name",
  "users": ["user1", "user2", "user3"]
}
```

#### キャッシュディレクトリのアクセス権限エラー

```bash
# ディレクトリの作成・権限設定
mkdir -p /path/to/cache
chmod 755 /path/to/cache

# または環境変数で別の場所を指定
export CACHE_DIR=./cache
```

#### Docker環境でのファイルアクセス問題

```bash
# ボリュームマウントと権限の確認
docker run --rm -v $(pwd)/data:/app/data:rw twitter-blocker --stats

# SELinux環境での場合
docker run --rm -v $(pwd)/data:/app/data:Z twitter-blocker --stats
```

### デバッグ手順

1. **問題の特定**:
   ```bash
   python3 -m twitter_blocker --debug-errors
   ```

2. **特定ユーザーでのテスト**:
   ```bash
   python3 -m twitter_blocker --debug --test-user problematic_user
   ```

3. **少数での動作確認**:
   ```bash
   python3 -m twitter_blocker --debug --max-users 5
   ```

4. **ログの詳細確認**: デバッグモードで詳細なAPI応答を確認

## 📁 プロジェクト構造

```text
twitter-bulk-blocker/
├── twitter_blocker/          # メインパッケージ
│   ├── __init__.py           # パッケージ初期化
│   ├── __main__.py           # 実行エントリーポイント
│   ├── api.py                # Twitter API管理（GraphQL/REST）
│   ├── config.py             # 設定・クッキー管理
│   ├── database.py           # SQLiteデータベース管理
│   ├── manager.py            # 一括ブロック管理
│   ├── retry.py              # リトライ判定ロジック
│   └── stats.py              # 統計表示・エラー分析
├── Dockerfile                # Docker設定
├── docker-compose.yml        # Docker Compose設定
├── requirements.txt          # 依存関係
├── .gitignore               # Git除外設定
├── examples.md              # 使用例とサンプル
└── README.md                # このファイル
```

## 🔧 開発者向け情報

### API設計

- **GraphQL API**: ユーザー情報取得、関係性確認
- **REST API**: ブロック実行
- **キャッシュシステム**: 効率的なAPI利用
- **エラーハンドリング**: 包括的なエラータイプ分類

### 拡張可能性

- モジュール分離設計による機能追加の容易さ
- 設定システムの柔軟性
- デバッグ機能の充実
- 統計・分析機能の詳細性

## ⚠️ 注意事項・ベストプラクティス

### 必須の安全対策

1. **テスト実行を推奨**: 最初は必ずテストモードで動作確認
2. **レート制限遵守**: APIレート制限を避けるため、適切な間隔で処理
3. **フォロー関係の尊重**: フォロー中/フォロワーのユーザーは自動的にスキップ
4. **データベース管理**: ブロック履歴はSQLiteで永続化され、重複を防止
5. **リトライ機能の理解**: 一時的エラーは自動リトライ、suspendedは除外

### 推奨運用方法

- **段階的実行**: 少数ずつテストしてから本格実行
- **統計の定期確認**: `--stats`での進捗状況の把握
- **エラー分析**: `--debug-errors`での問題の早期発見
- **環境変数の活用**: 設定の外部化によるセキュリティ向上

### 法的・倫理的考慮事項

- Twitter/X.comの利用規約を遵守してください
- 過度なAPI利用は避け、適切な間隔での実行を心がけてください
- 本ツールの使用は自己責任で行ってください

---

## 🤝 コントリビューション

バグ報告、機能リクエスト、プルリクエストを歓迎します。

## 📜 ライセンス

本プロジェクトは適切なライセンスの下で公開されています。詳細はLICENSEファイルをご確認ください。