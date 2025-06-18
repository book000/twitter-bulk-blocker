# CLAUDE.md - Twitter Bulk Blocker

このプロジェクト専用のClaude Code設定です。グローバル設定（~/.claude/CLAUDE.md）を継承し、プロジェクト固有の基本方針を定義します。

## プロジェクト概要

**Twitter Bulk Blocker** - 高度なキャッシュ戦略とバッチ処理を備えたエンタープライズグレードの大規模Twitter一括ブロックシステム

### 技術スタック
- **Python 3.x** with requests, pytz, sqlite3
- **Twitter GraphQL API v2 / REST API v1.1**
- **SQLite with WAL mode** (高速並行処理)
- **3層キャッシュアーキテクチャ** (Lookup/Profile/Relationship)

### アーキテクチャ
```
twitter_blocker/
├── api.py          # Twitter API管理（GraphQL/REST）+ 3層キャッシュ
├── database.py     # SQLite管理 + 永続的失敗キャッシュ + バッチ最適化
├── manager.py      # ワークフロー制御 + バッチ処理制御 + セッション管理
├── config.py       # 設定・スキーマ・Cookie管理
├── retry.py        # リトライ判定ロジック（永続的/一時的失敗分類）
└── stats.py        # 統計表示・分析・詳細レポート
```

## 基本開発方針

### コード品質基準
- **パフォーマンス要求**: 50件/秒以上、キャッシュヒット率80%以上維持
- **永続的失敗の事前チェック**: suspended/not_found/deactivatedでAPI呼び出し回避
- **バッチ処理必須**: N+1問題の徹底回避
- **リソース管理**: SQLite接続はcontext manager必須使用

### 実装パターン
```python
# ✅ 推奨: バッチ処理 + 事前チェック
permanent_failures = self.database.get_permanent_failures_batch(batch_ids, user_format)
for user_id in batch_ids:
    if user_id in permanent_failures:
        continue  # API呼び出しスキップ

# ❌ 避ける: 個別処理でのN+1問題
for user in users:
    if self.database.is_permanent_failure(user):  # 個別DB呼び出し
        continue
```

### エラーハンドリング
- **永続的失敗**: suspended, not_found, deactivated (API呼び出し禁止)
- **一時的失敗**: unavailable, rate_limit, server_error (リトライ対象)
- **認証エラー**: Cookie再読み込み + 自動復旧フロー

## 詳細ドキュメント参照

プロジェクト固有の深層知識は以下で参照：

### 開発ガイド
- `.claude/guides/api-patterns.md` - Twitter API操作パターン詳細
- `.claude/guides/performance-optimization.md` - パフォーマンス最適化手法
- `.claude/guides/error-handling.md` - エラーパターン完全マッピング
- `.claude/guides/caching-strategy.md` - 3層キャッシュ戦略詳細

### 実装パターン
- `.claude/patterns/recommended.md` - 推奨実装パターン集
- `.claude/patterns/anti-patterns.md` - 避けるべきアンチパターン
- `.claude/patterns/code-review.md` - コードレビュー観点

### ワークフロー
- `.claude/workflows/issue-handling.md` - Issue対応完全自動化プロセス
- `.claude/workflows/emergency.md` - 緊急事態対応プロトコル

### 運用管理
- `.claude/operations/cinnamon-server.md` - 本番Cinnamonサーバー運用ガイド

### トラブルシューティング
- `.claude/troubleshooting/common-issues.md` - よくある問題と解決手順

### 品質保証
- `.claude/quality/testing-guide.md` - テスト戦略・モック実装・CI設定

## クイックリファレンス

### よく使うコマンド
```bash
# 開発環境
python3 -m py_compile twitter_blocker/*.py  # 全品質チェック
/check-api-status                          # APIステータス確認
/analyze-performance database              # パフォーマンス分析
/debug-issue "問題の説明"                    # 緊急デバッグ

# 本番環境（Cinnamonサーバー）
/project:check-cinnamon                    # サーバー状態調査
/project:restart-service [service_name]    # サービス再起動
```

### 重要な数値
- **GraphQLレート制限**: 150リクエスト/15分
- **RESTレート制限**: 300ブロック/15分
- **最適バッチサイズ**: 50件
- **キャッシュTTL**: 30日
- **目標処理速度**: 50件/秒以上

---

この基本方針と詳細ドキュメントにより、効率的で高品質なtwitter-bulk-blocker開発を実現します。
詳細が必要な場合は該当する.claudeドキュメントを参照してください。