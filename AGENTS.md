# AGENTS.md - Twitter Bulk Blocker

## 目的

このドキュメントは、汎用 AI エージェントが Twitter Bulk Blocker プロジェクトで作業する際の共通方針とルールを定義します。

## 基本方針

### 会話言語とコミュニケーション

- **会話は日本語**で行う
- **コード内コメント**は日本語で記載する
- **エラーメッセージ**は英語で記載する
- **日本語と英数字の間**には半角スペースを挿入する

### コミット規約

- **コミットメッセージ**: [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) に従う
  - `<type>(<scope>): <description>` 形式
  - `<description>` は日本語で記載
  - 例: `feat: ユーザー認証機能を追加`
- **ブランチ命名**: [Conventional Branch](https://conventional-branch.github.io) に従う
  - `<type>/<description>` 形式
  - `<type>` は短縮形（feat, fix）を使用
  - 例: `feat/add-user-auth`

## 判断記録のルール

技術的判断を行う際は、以下の項目を明確に記録すること：

1. **判断内容の要約**: 何を決定したか
2. **検討した代替案**: 他にどのような選択肢があったか
3. **採用しなかった案とその理由**: なぜその案を選ばなかったか
4. **前提条件・仮定・不確実性**: 判断の前提となる条件や仮定
5. **他エージェントによるレビュー可否**: この判断は他のエージェントによるレビューが推奨されるか

**重要**: 前提・仮定・不確実性を明示し、仮定を事実のように扱わない。

## プロジェクト概要

### 目的

Twitter/X.com で大量のユーザーを効率的にブロックする Python ツール。高度なキャッシュ戦略とバッチ処理を備えたエンタープライズグレードのシステム。

### 主な機能

- 🔒 **安全性重視**: フォロー関係チェック、重複防止、リトライ機能
- 📊 **詳細統計**: リアルタイム進捗表示、処理結果の詳細レポート
- 🏗️ **モジュール設計**: 保守しやすい分離された設計
- 🐳 **Docker 対応**: コンテナ環境での実行をサポート
- 🔄 **自動リトライ**: 一時的エラーの自動再試行（永続的失敗は除外）
- 🎛️ **柔軟な設定**: 環境変数・コマンドライン引数・デフォルト値による多層設定

### 技術スタック

- **言語**: Python 3.x
- **主要ライブラリ**: requests, pytz, sqlite3
- **API**: Twitter GraphQL API v2 / REST API v1.1
- **データベース**: SQLite with WAL mode
- **コンテナ**: Docker

### アーキテクチャ

```
twitter_blocker/
├── api.py          # Twitter API 管理（GraphQL/REST）+ 3 層キャッシュ
├── database.py     # SQLite 管理 + 永続的失敗キャッシュ + バッチ最適化
├── manager.py      # ワークフロー制御 + バッチ処理制御 + セッション管理
├── config.py       # 設定・スキーマ・Cookie 管理
├── retry.py        # リトライ判定ロジック（永続的/一時的失敗分類）
└── stats.py        # 統計表示・分析・詳細レポート
```

## 開発手順（概要）

### 1. プロジェクトの理解

- README.md、CLAUDE.md、.github/copilot-instructions.md を読んで、プロジェクトの全体像を理解する
- アーキテクチャと主要モジュールの役割を把握する
- 既存のコードパターンとベストプラクティスを確認する

### 2. 依存関係のインストール

```bash
# 依存パッケージのインストール
pip install -r requirements.txt

# または Docker 環境を使用
docker build -t twitter-blocker .
```

### 3. 変更の実装

- **既存のコードパターンに従う**: プロジェクト固有の実装パターンを尊重
- **バッチ処理を優先**: N+1 問題を回避するため、常にバッチ処理を検討
- **リソース管理**: SQLite 接続は context manager を使用
- **エラーハンドリング**: 永続的失敗と一時的失敗を適切に分類

### 4. テストと Lint/Format 実行

```bash
# Python 構文チェック
python3 -m py_compile twitter_blocker/*.py

# デバッグモードでのテスト実行
python3 -m twitter_blocker --debug --test-user example_user

# 統計表示で動作確認
python3 -m twitter_blocker --stats
```

## コーディング規約

### Python スタイル

- **命名規則**: snake_case（関数、変数）、PascalCase（クラス）
- **インデント**: 4 スペース
- **最大行長**: 100 文字（推奨）
- **docstring**: 日本語で記載

### エラーハンドリング

#### 永続的失敗（API 呼び出し禁止）

- `suspended` - アカウント停止
- `not_found` - ユーザー不存在
- `deactivated` - アカウント無効化

#### 一時的失敗（リトライ対象）

- `unavailable` - 一時的な利用不可
- `rate_limit` - レート制限
- `server_error` - サーバーエラー（500, 502, 503, 504）

### 推奨実装パターン

```python
# ✅ 推奨: バッチ処理 + 事前チェック
permanent_failures = self.database.get_permanent_failures_batch(batch_ids, user_format)
for user_id in batch_ids:
    if user_id in permanent_failures:
        continue  # API 呼び出しスキップ

# ✅ 推奨: Context Manager 使用
with sqlite3.connect(self.db_path) as conn:
    cursor = conn.cursor()
    # 処理...
```

## セキュリティ / 機密情報

### 認証情報の管理

- **API キーや認証情報**: 環境変数または設定ファイルで管理し、Git にコミットしない
- **Cookie 情報**: `cookies.json` ファイルで管理し、.gitignore に追加済み
- **ログ出力**: 認証情報や個人情報をログに出力しない

### 重要なセキュリティ要件

1. **Cookie 情報の保護**: 認証情報は安全に管理し、ログ出力時はマスク
2. **レート制限遵守**: Twitter API の制限を厳格に守る
3. **フォロー関係の尊重**: フォロー中/フォロワーのユーザーは自動スキップ
4. **重複防止**: 一度ブロックしたユーザーは再度ブロックしない

## リポジトリ固有の注意事項

### パフォーマンス要求

- **処理速度**: 50 件/秒以上を目標
- **キャッシュヒット率**: 80% 以上を維持
- **バッチサイズ**: 50 件（最適値）
- **キャッシュ TTL**: 30 日

### Twitter API 制限

- **GraphQL レート制限**: 150 リクエスト/15 分
- **REST レート制限**: 300 ブロック/15 分
- **推奨リクエスト間隔**: 1.0 秒以上

### 拡張ヘッダー機能

- **動的ヘッダー生成**: Twitter/X のアンチボットシステム対応
- **段階的導入**: `--disable-header-enhancement`、`--enable-forwarded-for` オプション
- **トランザクション ID**: `x-client-transaction-id` の動的生成

### バージョン管理

- **動的バージョン取得**: Git・環境変数・ファイルベースの優先順位システム
- **--version オプション**: `python3 -m twitter_blocker --version` で現在バージョン表示
- **Docker 対応**: APPLICATION_VERSION、.app-version ファイル埋め込み

### 法的・倫理的考慮事項

- Twitter/X.com の利用規約を遵守する
- 過度な API 利用は避け、適切な間隔での実行を心がける
- 本ツールの使用は自己責任で行う
- ユーザー情報の適切な管理とプライバシー尊重

## 既知の制約

### API 制約

- GraphQL API のフィーチャーフラグ要求に対応済み
- レート制限エラー（429）は自動リトライ対象
- アカウントロック（エラー 326）は手動対応が必要

### システム制約

- SQLite WAL モードでの同時アクセス最適化済み
- キャッシュディレクトリの書き込み権限が必要
- Docker 環境では `/data` ディレクトリへのボリュームマウントが必要

### 動作環境

- Python 3.x 必須
- Linux/macOS/Windows 対応（Git Bash 推奨）
- Docker 環境での実行を推奨

## 参考リンク

- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
- [Conventional Branch](https://conventional-branch.github.io)
- [Twitter API Documentation](https://developer.twitter.com/en/docs)
- [SQLite WAL Mode](https://www.sqlite.org/wal.html)

---

このガイドラインに従って、安全で効率的な Twitter Bulk Blocker の開発と保守を行ってください。
