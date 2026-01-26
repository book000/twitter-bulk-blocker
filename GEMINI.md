# GEMINI.md - Twitter Bulk Blocker

## 目的

このドキュメントは、Gemini CLI が Twitter Bulk Blocker プロジェクトで作業する際のコンテキストと作業方針を定義します。Gemini CLI は、外部仕様の調査、最新情報の確認、SaaS 仕様の検証などに特化したエージェントとして機能します。

## 出力スタイル

### 言語とトーン

- **会話言語**: 日本語
- **説明のトーン**: 明確で簡潔、技術的に正確
- **コード内コメント**: 日本語
- **エラーメッセージ**: 日本語（プロジェクト規約に準拠）

### 出力形式

- **構造化された情報**: 見出し、リスト、コードブロックを活用
- **根拠の明示**: 情報源（公式ドキュメント、仕様書など）を明記
- **最新性の確認**: 情報の更新日や有効期限を示す
- **日本語と英数字の間**: 半角スペースを挿入

## 共通ルール

### コミット規約

- **コミットメッセージ**: [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) に従う
  - `<type>(<scope>): <description>` 形式
  - `<description>` は英語で記載
  - 例: `feat: support Twitter API v2 latest specification`
- **ブランチ命名**: [Conventional Branch](https://conventional-branch.github.io) に従う
  - `<type>/<description>` 形式
  - `<type>` は短縮形（feat, fix）を使用
  - 例: `feat/update-api-spec`

### 日本語と英数字の間隔

- 日本語文字と半角英数字・記号の間には半角スペースを挿入する
- 例: ✅ `Twitter API v2 の仕様` / ❌ `Twitter API v2の仕様`

## プロジェクト概要

### 目的

Twitter/X.com で大量のユーザーを効率的にブロックする Python ツール。クッキー認証と GraphQL API/REST API を使用し、高度なキャッシュ戦略とバッチ処理を備えたエンタープライズグレードのシステム。

### 主な機能

- 🔒 **安全性重視**: フォロー関係チェック、重複防止、自動リトライ機能
- 📊 **詳細統計**: リアルタイム進捗表示、処理結果の詳細レポート、エラー分析
- 🏗️ **モジュール設計**: api.py、database.py、manager.py など保守しやすい分離設計
- 🐳 **Docker 対応**: コンテナ環境での実行、環境変数による柔軟な設定
- 🔄 **自動リトライ**: 一時的エラー（レート制限、サーバーエラー）の自動再試行
- 🎛️ **3 層キャッシュ**: Lookup/Profile/Relationship の効率的キャッシュ戦略

### 技術スタック

- **言語**: Python 3.x
- **主要ライブラリ**: requests 2.31.0+, pytz 2023.3+, sqlite3（標準ライブラリ）
- **API**: Twitter GraphQL API v2（ユーザー情報取得）、REST API v1.1（ブロック実行）
- **データベース**: SQLite with WAL mode（高速並行処理）
- **コンテナ**: Docker（単一ステージ Dockerfile）

## Gemini CLI の役割と責務

### 専門領域

Gemini CLI は以下の領域で Claude Code をサポートします：

#### 1. 外部 API 仕様の調査

- **Twitter/X API の最新仕様**:
  - GraphQL API v2 のエンドポイント変更
  - REST API v1.1 のレート制限更新
  - 新しいフィーチャーフラグの追加
  - 認証方式の変更（Cookie、Bearer Token など）

#### 2. レート制限とクォータの確認

- **API レート制限**:
  - GraphQL API: 150 リクエスト/15 分（最新値の確認）
  - REST API: 300 ブロック/15 分（最新値の確認）
  - レート制限ヘッダーの仕様（x-rate-limit-*）

#### 3. 外部依存サービスの仕様変更

- **Docker Hub**: Python 公式イメージの最新バージョン（3.14.x 系列）
- **依存ライブラリ**: requests、pytz の最新安定版とセキュリティアップデート
- **GitHub Actions**: ワークフローで使用するアクションの最新バージョン

#### 4. セキュリティ脆弱性情報

- **CVE データベース**: 使用中のライブラリの脆弱性確認
- **GitHub Security Advisory**: リポジトリに関連するセキュリティ勧告
- **Python パッケージ**: requests、pytz などの既知の脆弱性

## コーディング規約

### Python スタイル

- **命名規則**:
  - 関数・変数: snake_case
  - クラス: PascalCase
  - 定数: UPPER_SNAKE_CASE
- **インデント**: 4 スペース
- **最大行長**: 100 文字（推奨）
- **docstring**: 日本語で記載（Google スタイル推奨）

### コメント言語

- **コード内コメント**: 日本語
- **docstring**: 日本語
- **TODO コメント**: 日本語

### エラーメッセージ言語

- **プログラム内のエラーメッセージ**: 日本語（プロジェクト規約に準拠）
- **ログメッセージ**: 日本語（ユーザー向け情報）、英語（デバッグ情報も可）

## 開発コマンド

### 依存関係のインストール

```bash
# requirements.txt からインストール
pip install -r requirements.txt
```

### 実行コマンド

```bash
# テスト実行（最初の 5 人のみ）
python3 -m twitter_blocker

# 統計表示
python3 -m twitter_blocker --stats

# 本格実行
python3 -m twitter_blocker --all

# 自動リトライ付き本格実行
python3 -m twitter_blocker --all --auto-retry

# デバッグモードで特定ユーザーのテスト
python3 -m twitter_blocker --test-user example_user --debug

# バージョン確認
python3 -m twitter_blocker --version
```

### 品質チェック

```bash
# Python 構文チェック
python3 -m py_compile twitter_blocker/*.py

# エラー分析
python3 -m twitter_blocker --debug-errors
```

### Docker コマンド

```bash
# イメージビルド
docker build -t twitter-blocker .

# ヘルプ表示
docker run --rm twitter-blocker

# 統計表示（デフォルト環境変数を使用）
docker run --rm -v ./data:/data twitter-blocker --stats

# 本格実行（デフォルト環境変数を使用）
docker run --rm -v ./data:/data twitter-blocker --all --auto-retry

# または /app/data にマウントする場合は環境変数で明示的にオーバーライド
docker run --rm -v ./data:/app/data -e TWITTER_COOKIES_PATH=/app/data/cookies.json -e TWITTER_USERS_FILE=/app/data/users.json twitter-blocker --stats
```

## 注意事項

### 認証情報の扱い

- **Cookie 情報**: `cookies.json` ファイルで管理し、Git にコミットしない（.gitignore に追加済み）
- **環境変数**: 認証情報は環境変数で管理可能（TWITTER_COOKIES_PATH）
- **ログ出力**: 認証情報や個人情報をログに出力しない、マスク処理を実施

### Twitter API の利用規約

- **レート制限の遵守**: API レート制限を厳格に守る
- **適切な使用**: 過度な API 利用を避け、適切な間隔での実行（デフォルト 1.0 秒）
- **フォロー関係の尊重**: フォロー中/フォロワーのユーザーは自動的にスキップ
- **重複防止**: SQLite データベースで一度ブロックしたユーザーは再度ブロックしない

### 既存ルールの優先

- プロジェクト固有の実装パターンを尊重する
- 既存のコードスタイルに従う
- 既存のエラーハンドリングパターン（永続的失敗 vs 一時的失敗）を継承する

## Gemini CLI の作業フロー

### 1. 調査フェーズ

```
1. Claude Code から調査依頼を受ける
2. 公式ドキュメント・仕様書を確認
3. 最新の変更履歴をチェック
4. セキュリティ勧告を確認
```

### 2. 分析フェーズ

```
1. 情報の信頼性を評価
2. プロジェクトへの影響を分析
3. 必要な対応を特定
4. 代替案を検討
```

### 3. 報告フェーズ

```
1. 構造化された情報を作成
2. 根拠（情報源）を明記
3. 推奨アクションを提示
4. Claude Code にフィードバック
```

## 既知の制約

### Twitter API の制約

- **GraphQL API**:
  - レート制限: 150 リクエスト/15 分（2025 年 1 月時点）
  - フィーチャーフラグ要求: `rweb_tipjar_consumption_enabled` 等の必須フィールド
- **REST API v1.1**:
  - レート制限: 300 ブロック/15 分（2025 年 1 月時点）
  - エラー 326（アカウントロック）は手動対応が必要

### 環境制約

- **Python バージョン**: 3.x 必須（3.14.2 を推奨、2026 年 1 月時点）
- **SQLite**: WAL モード対応必須
- **キャッシュディレクトリ**: 書き込み権限が必要（デフォルト: /app/data/cache）

### Docker 制約

- **ボリュームマウント**: `/data` ディレクトリへのマウントを推奨（Dockerfile デフォルト）。`/app/data` にマウントする場合は環境変数でパスをオーバーライド
- **環境変数**: Dockerfile のデフォルト値は `/data/*` を指定。異なるパスを使用する場合は TWITTER_COOKIES_PATH、TWITTER_USERS_FILE などの環境変数でオーバーライドが必要

## リポジトリ固有の重要事項

### パフォーマンス要求

- **処理速度目標**: 50 件/秒以上
- **キャッシュヒット率**: 80% 以上維持
- **最適バッチサイズ**: 50 件
- **キャッシュ TTL**: 30 日

### エラーハンドリング分類

#### 永続的失敗（API 呼び出し禁止、リトライ対象外）

- `suspended` - アカウント停止
- `not_found` - ユーザー不存在
- `deactivated` - アカウント無効化

#### 一時的失敗（リトライ対象）

- `unavailable` - 一時的な利用不可
- `rate_limit` - レート制限（429 エラー）
- `server_error` - サーバーエラー（500, 502, 503, 504）

### 拡張ヘッダー機能（Issue #38 対応）

- **x-client-transaction-id**: 動的トランザクション ID 生成（デフォルト有効）
- **x-xp-forwarded-for**: 日本主要 ISP 範囲の IP 生成（オプション、要 `--enable-forwarded-for`）
- **緊急無効化**: `--disable-header-enhancement` オプション

### バージョン管理システム

- **動的バージョン取得優先順位**:
  1. Git tag/branch（開発環境）
  2. 環境変数: APPLICATION_VERSION
  3. ファイル: .app-version
  4. デフォルト: "development"

### 法的・倫理的考慮事項

- Twitter/X.com の利用規約を遵守する
- 過度な API 利用を避ける
- 本ツールの使用は自己責任で行う
- ユーザー情報の適切な管理とプライバシー尊重

## 相談プロトコル

### Claude Code から Gemini CLI への相談

Claude Code が以下のような状況で Gemini CLI に相談します：

```
✅ 相談すべき状況:
- Twitter API の最新仕様変更の確認
- レート制限値の最新情報の確認
- Python や依存ライブラリの最新バージョン確認
- セキュリティ脆弱性情報の調査
- SaaS の料金プラン・制限・クォータの確認

❌ 相談不要な状況:
- コードレビュー（Codex CLI の領域）
- アーキテクチャ設計（Codex CLI の領域）
- 既存コードの整合性確認（Codex CLI の領域）
```

### Gemini CLI からの応答形式

```markdown
## 調査結果

### 情報源
- [Twitter API Documentation](https://developer.twitter.com/en/docs)
- 更新日: 2026-01-XX

### 主要な発見
1. **項目 1**: 詳細説明
2. **項目 2**: 詳細説明

### プロジェクトへの影響
- **影響レベル**: 高/中/低
- **対応の緊急性**: 即時/近日中/将来的

### 推奨アクション
1. アクション 1: 具体的な手順
2. アクション 2: 具体的な手順

### 不確実性・前提条件
- 前提条件 1
- 不確実性のある要素 2
```

## 参考リンク

### 公式ドキュメント

- [Twitter API Documentation](https://developer.twitter.com/en/docs)
- [Twitter API Rate Limits](https://developer.twitter.com/en/docs/twitter-api/rate-limits)
- [Python Official Documentation](https://docs.python.org/3/)
- [Docker Documentation](https://docs.docker.com/)

### 規約・ガイドライン

- [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
- [Conventional Branch](https://conventional-branch.github.io)

### セキュリティ

- [CVE Database](https://cve.mitre.org/)
- [GitHub Security Advisory](https://github.com/advisories)
- [Python Package Index (PyPI) Security](https://pypi.org/security/)

---

このガイドラインに従い、Gemini CLI は外部情報の調査・確認を通じて、Twitter Bulk Blocker プロジェクトの正確性と最新性を支援します。
