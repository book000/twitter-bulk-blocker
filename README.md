# twitter-bulk-blocker

Twitter/X.comで大量のユーザーを効率的にブロックするPythonツールです。クッキー認証とGraphQL APIを使用し、安全で確実なブロック処理を提供します。

## ✨ 特徴

- 🔒 **安全性重視**: フォロー関係チェック、重複防止、リトライ機能
- 📊 **詳細統計**: リアルタイム進捗表示、処理結果の詳細レポート
- 🏗️ **モジュール設計**: 保守しやすい分離された設計
- 🐳 **Docker対応**: コンテナ環境での実行をサポート
- 🔄 **自動リトライ**: 一時的エラーの自動再試行（suspendedは除外）

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

# 5. リトライ回数リセット
python3 -m twitter_blocker --reset-retry
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

### ファイルパス指定

- `--cookies PATH` - クッキーファイルのパス（デフォルト: cookies.json）
- `--users-file PATH` - ブロック対象ユーザーファイルのパス（デフォルト: video_misuse_detecteds.json）
- `--db PATH` - ブロック履歴データベースのパス（デフォルト: block_history.db）

## 🔧 設定方法

### 1. コマンド引数で指定

```bash
python3 -m twitter_blocker --all \
  --cookies /path/to/cookies.json \
  --users-file /path/to/users.json \
  --db /path/to/database.db
```

### 2. 環境変数で指定

```bash
export TWITTER_COOKIES_PATH=/path/to/cookies.json
export TWITTER_USERS_FILE=/path/to/users.json
export TWITTER_BLOCK_DB=/path/to/database.db

python3 -m twitter_blocker --all
```

### 優先順位

1. コマンド引数（最優先）
2. 環境変数
3. デフォルト値

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
```

### Docker Compose

```bash
# docker-compose.yml の command を編集
command: ["--stats"]
command: ["--all", "--auto-retry"]

# 実行
docker-compose run twitter-blocker
```

## 🛡️ 安全機能

### 重複防止

- SQLiteデータベースで履歴管理
- 一度ブロックしたユーザーは再度ブロックしない

### 自動リトライ

- 一時的なエラー（429, 500, 502, 503, 504）の自動リトライ
- 指数バックオフでリトライ間隔を調整
- 最大3回までのリトライ制限
- **suspendedユーザーはリトライ対象から除外**（永続的な失敗として扱い）

### 安全性チェック

- フォロー関係のあるユーザーは自動スキップ
- 既にブロック済みのユーザーは自動スキップ
- ユーザー状態の詳細判定（active/suspended/deactivated/not_found）

### 進捗管理

- リアルタイムの処理状況表示
- 詳細な統計情報（ブロック成功/スキップ/エラー数）
- セッション管理でプロセス追跡

## 📁 プロジェクト構造

```text
twitter-block/
├── twitter_blocker/          # メインパッケージ
│   ├── __init__.py           # パッケージ初期化
│   ├── __main__.py           # 実行エントリーポイント
│   ├── api.py                # Twitter API管理
│   ├── config.py             # 設定・クッキー管理
│   ├── database.py           # SQLiteデータベース管理
│   ├── manager.py            # 一括ブロック管理
│   ├── retry.py              # リトライ判定ロジック
│   └── stats.py              # 統計表示
├── Dockerfile                # Docker設定
├── docker-compose.yml        # Docker Compose設定
├── requirements.txt          # 依存関係
├── .gitignore               # Git除外設定
└── README.md                # このファイル
```

## 📊 使用例

### テスト実行

```bash
$ python3 -m twitter_blocker
📁 使用ファイル:
  クッキー: cookies.json
  ユーザーリスト: video_misuse_detecteds.json
  データベース: block_history.db

=== 処理統計 ===
全対象ユーザー: 2,308人
ブロック済み: 5人 (0.2%)
残り未処理: 2,303人

🧪 テストモード: 最初の5人のみ処理します
本格実行する場合は: python3 -m twitter_blocker --all
自動リトライ付きの場合は: python3 -m twitter_blocker --all --auto-retry

=== 一括ブロック処理開始 ===
ユーザーファイル形式: screen_name
[1/5] @example_user を処理中...
  → ブロック実行: Example User (ID: 1234567890)
  ✓ ブロック成功
...
```

### 統計表示

```bash
$ python3 -m twitter_blocker --stats
=== 処理統計 ===
全対象ユーザー: 2,308人
ブロック済み: 1,245人 (53.9%)
残り未処理: 1,063人
失敗: 12人
  - リトライ上限到達: 2人
  - リトライ可能: 3人
  - ステータス別:
    suspended: 8人
    unavailable: 4人
suspended: 8人
利用不可: 4人

リトライ候補: 3人
  - unavailable: 3人
```

## 🔄 処理フロー

1. **スキーマ検証** - ユーザーファイル形式の確認
2. **ユーザー情報取得** - GraphQL APIでユーザー状態確認
3. **安全性チェック** - フォロー関係とユーザー状態を確認
4. **ブロック実行** - REST APIでブロック処理
5. **結果記録** - SQLiteデータベースに履歴保存
6. **リトライ判定** - 失敗時にリトライ対象かどうか判定

## 🛠️ トラブルシューティング

### アカウントロック（エラー326）

X.comでアカウントのロックを解除してから再実行してください:
<https://twitter.com/account/access>

### クッキーの有効期限切れ

X.comで再ログインしてcookies.jsonを更新してください。

### レート制限（エラー429）

`--delay` オプションでリクエスト間隔を長くしてください:

```bash
python3 -m twitter_blocker --all --delay 2.0
```

### ファイル形式エラー

ユーザーファイルが正しい形式になっているか確認してください:

```json
{
  "format": "screen_name",
  "users": ["user1", "user2", "user3"]
}
```

## ⚠️ 注意事項

1. **テスト実行を推奨**: 最初は必ずテストモードで動作確認
2. **レート制限遵守**: APIレート制限を避けるため、適切な間隔で処理
3. **フォロー関係**: フォロー中/フォロワーのユーザーは自動的にスキップ
4. **データベース管理**: ブロック履歴はSQLiteで永続化され、重複を防止
5. **リトライ機能**: 一時的エラーは自動リトライ、suspendedは除外
