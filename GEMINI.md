# GEMINI.md

## 目的
- Gemini CLI 向けのコンテキストと作業方針を定義する。

## 出力スタイル
- 言語: 日本語
- トーン: 簡潔で事実ベース
- 形式: Markdown

## 共通ルール
- 会話は日本語で行う。
- PR とコミットは Conventional Commits に従う。
- PR タイトルとコミット本文の言語: PR タイトルは Conventional Commits 形式（英語推奨）。PR 本文は日本語。コミットは Conventional Commits 形式（description は日本語）。
- 日本語と英数字の間には半角スペースを入れる。

## プロジェクト概要
Enterprise-grade bulk block tool for Twitter/X using GraphQL/REST APIs with advanced caching, retry logic, and safety checks.

### 技術スタック
- **言語**: Python
- **フレームワーク**: N, /, A,  , (, p, u, r, e,  , s, t, a, n, d, a, r, d,  , l, i, b, r, a, r, y,  , +,  , r, e, q, u, e, s, t, s, )
- **パッケージマネージャー**: pip
- **主要な依存関係**:
  - requests>=2.31.0
  - pytz>=2023.3

## コーディング規約
- フォーマット: 既存設定（ESLint / Prettier / formatter）に従う。
- 命名規則: 既存のコード規約に従う。
- コメント言語: 日本語
- エラーメッセージ: 英語

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

## 注意事項
- 認証情報やトークンはコミットしない。
- ログに機密情報を出力しない。
- 既存のプロジェクトルールがある場合はそれを優先する。

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