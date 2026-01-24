# CLAUDE.md

## 目的
- Claude Code の作業方針とプロジェクト固有ルールを示す。

## 判断記録のルール
- 判断は必ずレビュー可能な形で記録する。
  1. 判断内容の要約
  2. 検討した代替案
  3. 採用しなかった案とその理由
  4. 前提条件・仮定・不確実性
  5. 他エージェントによるレビュー可否
- 前提・仮定・不確実性を明示し、仮定を事実のように扱わない。

## プロジェクト概要
Enterprise-grade bulk block tool for Twitter/X using GraphQL/REST APIs with advanced caching, retry logic, and safety checks.

### 技術スタック
- **言語**: Python
- **フレームワーク**: N, /, A,  , (, p, u, r, e,  , s, t, a, n, d, a, r, d,  , l, i, b, r, a, r, y,  , +,  , r, e, q, u, e, s, t, s, )
- **パッケージマネージャー**: pip
- **主要な依存関係**:
  - requests>=2.31.0
  - pytz>=2023.3

## 重要ルール
- 会話言語: 日本語
- PR とコミットは Conventional Commits に従う。
- PR タイトルとコミット本文の言語: PR タイトルは Conventional Commits 形式（英語推奨）。PR 本文は日本語。コミットは Conventional Commits 形式（description は日本語）。
- コメント言語: 日本語
- エラーメッセージ: 英語
- 日本語と英数字の間には半角スペースを入れる。
- 既存のプロジェクトルールがある場合はそれを優先する。

## 環境のルール
- ブランチ命名は Conventional Branch に従う。
- GitHub リポジトリを調査する場合はテンポラリディレクトリに `git clone` して検索する。
- Windows 環境では Git Bash を使用する。
- Renovate の既存 PR には追加コミットしない。

## Git Worktree
- 使う場合は `.bare/<branch>` 構成で作成する。

## ブラウザ操作
- 座標ではなくセレクターで要素を特定する。
- 実装と画面の差異を確認し、必要に応じて実装を改善する。

## コード改修時のルール
- 既存のエラーメッセージで先頭に絵文字がある場合、全体で統一する。
- TypeScript 使用時は `skipLibCheck` で回避しない。
- 関数やインターフェースには docstring（JSDoc など）を記載する。

### コーディング規約
- **design**: Modular 6-file architecture
- **cache**: 3-layer caching (Lookup/Profile/Relationship)
- **database**: SQLite with WAL mode
- **error_handling**: Permanent vs temporary failure classification
- **performance**: Target: 50+ users/second with 80%+ cache hit rate

## 相談ルール
- Codex CLI: 実装レビュー、局所設計、整合性確認に使う。
- Gemini CLI: 外部仕様や最新情報の確認に使う。
- 他エージェントの指摘は黙殺せず、採用または理由を明記して不採用とする。

### 開発コマンド
```bash
# install
pip install -r requirements.txt

# dev
python3 -m twitter_blocker [options]

# build
docker build -t twitter-blocker .

# test
python3 -m py_compile twitter_blocker/*.py

```

### プロジェクト構造

**主要ディレクトリ:**
- `twitter_blocker/ (core package)`
- `docker/ (Docker configuration)`

**重要ファイル:**
- `twitter_blocker/__main__.py (entry point)`
- `twitter_blocker/api.py (GraphQL/REST + 3-layer cache)`
- `twitter_blocker/database.py (SQLite management)`
- `twitter_blocker/manager.py (workflow control)`
- `twitter_blocker/config.py (configuration)`
- `twitter_blocker/retry.py (retry logic)`
- `twitter_blocker/stats.py (statistics)`

## 実装パターン
- 既存のコードパターンに従う。
- プロジェクト固有の実装ガイドラインがある場合はそれに従う。

## テスト
- 方針: 変更内容に応じてテストを追加する。

## ドキュメント更新ルール
- 更新タイミング: 実装確定後、同一コミットまたは追加コミットで更新する。
- README、API ドキュメント、コメント等は常に最新状態を保つ。

## 作業チェックリスト

### 新規改修時
1. プロジェクトを理解する。
2. 作業ブランチが適切であることを確認する。
3. 最新のリモートブランチに基づいた新規ブランチであることを確認する。
4. PR がクローズされた不要ブランチが削除済みであることを確認する。
5. 指定されたパッケージマネージャーで依存関係をインストールする。

### コミット・プッシュ前
1. Conventional Commits に従っていることを確認する。
2. センシティブな情報が含まれていないことを確認する。
3. Lint / Format エラーがないことを確認する。
4. 動作確認を行う。

### PR 作成前
1. PR 作成の依頼があることを確認する。
2. センシティブな情報が含まれていないことを確認する。
3. コンフリクトの恐れがないことを確認する。

### PR 作成後
1. コンフリクトがないことを確認する。
2. PR 本文が最新状態のみを網羅していることを確認する。
3. `gh pr checks <PR ID> --watch` で CI を確認する。
4. Copilot レビューに対応し、コメントに返信する。
5. Codex のコードレビューを実施し、指摘対応を行う。
6. PR 本文の崩れがないことを確認する。

## リポジトリ固有
- **architecture**: High-performance batch processing with N+1 prevention
- **authentication**: Cookie-based (X.com export)
- **api_limits**: GraphQL: 150/15min, REST: 300 blocks/15min
**safety_features:**
  - Duplicate prevention (SQLite persistent history)
  - Follow relationship check (skips followers/following)
  - Advanced retry with backoff (up to 10 retries)
  - suspended/not_found permanent failure skip
  - Enhanced headers for anti-bot (x-client-transaction-id)
**operations:**
  - Test mode (first 5 users)
  - Auto-retry with exponential backoff
  - Debug mode with detailed logging
  - Statistics and error analysis