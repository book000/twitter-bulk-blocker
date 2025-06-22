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
- **スクリプト開発方針**: check-cinnamonなどの監視スクリプトは実行時間より機能性・正確性を優先
  - 高速版・最適化版などのバリエーションは作成しない（単一バージョンを維持）
  - 機能の切り替えが必要な場合はコマンドラインオプションで対応

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

## 🔑 Cinnamonサーバー接続方法（重要）

⚠️ **Claude Code使用時の必須注意事項**

### ✅ 正しい接続方法
```bash
ssh Cinnamon  # 必ずこの形式を使用
```

### ❌ 間違った接続方法（絶対に使用禁止）
```bash
ssh ope@cinnamon.oimo.io         # ホスト名解決エラー
ssh ope@183.90.238.206          # IP直接（タイムアウト）
```

📋 **詳細**: `.claude/cinnamon-connection.md` 参照

## クイックリファレンス

### よく使うコマンド
```bash
# 開発環境
python3 -m py_compile twitter_blocker/*.py  # 全品質チェック
/check-api-status                          # APIステータス確認
/analyze-performance database              # パフォーマンス分析
/debug-issue "問題の説明"                    # 緊急デバッグ

# 拡張ヘッダー機能テスト
python3 -m twitter_blocker --test-user "username" --debug --enable-forwarded-for
python3 -m twitter_blocker --all --disable-header-enhancement  # 緊急時無効化

# 本番環境（Cinnamonサーバー）
/project:check-cinnamon                    # サーバー包括的状態分析（長期履歴対応）
/project:restart-service [service_name]    # サービス再起動（引数省略で全サービス）
/project:debug-issue "問題の説明"           # 詳細問題調査とデバッグ

# 開発・運用コマンド
/project:check-api-status [target]         # API・キャッシュ状態確認
/project:analyze-performance [target]      # パフォーマンス分析とボトルネック特定
/project:optimize-batch [target]           # バッチ処理最適化
/project:test-feature [feature_name]       # 機能テスト実行

# バージョン管理・リリース監視
.claude/commands/check-latest-release      # GitHub最新リリース確認
.claude/commands/update-containers         # コンテナイメージ更新
.claude/commands/monitor-releases          # リリース監視・自動更新
.claude/commands/wait-for-deployment       # デプロイ完了待機

# 監視ツールスイート v2.1 (長期履歴対応)
.claude/commands/check-cinnamon             # 包括的分析 (バージョン情報・24時間エラー履歴対応)
.claude/cinnamon-monitor-suite.sh [mode]   # 統合監視インターフェース (非対話型)
.claude/cinnamon-logs-ai-optimized.sh      # AI最適化版・構造化出力
.claude/cinnamon-logs.sh                   # 基本版 (参考用)
```

## 📊 Cinnamonサーバー監視ツールスイート

### 統合監視システム
```bash
# メインインターフェース（推奨）
.claude/cinnamon-monitor-suite.sh
# インタラクティブメニューで全ツールにアクセス
```

### 個別ツール詳細
```bash
# 🤖 AI最適化版（メイン）
.claude/cinnamon-logs-ai-optimized.sh
# Claude Code向け構造化出力・問題根本原因特定・修正提案

# 🔍 基本監視（参考用）
.claude/cinnamon-logs.sh
# 従来版・人間向け出力

# 🎛️ 統合インターフェース
.claude/cinnamon-monitor-suite.sh [mode]
# 引数ベース非対話型・複数分析手法への統一アクセス
# 例: .claude/cinnamon-monitor-suite.sh ai
```

### 監視ツール使い分けガイド
| 状況 | 推奨ツール | 実行方法 | 備考 |
|------|------------|----------|------|
| **📊 包括的分析（推奨）** | メイン版 | `.claude/commands/check-cinnamon` | バージョン情報・全機能搭載・詳細分析 |
| **🔢 バージョン確認のみ** | リリース確認 | `.claude/commands/check-latest-release` | GitHub最新リリース・稼働中比較 |
| **🚀 コンテナ更新** | 更新コマンド | `.claude/commands/update-containers` | 安全な更新・デプロイ待機統合 |
| **🔄 自動リリース監視** | リリース監視 | `.claude/commands/monitor-releases --auto-update` | 新リリース検出・自動更新 |
| **🔍 詳細分析** | 包括的分析（旧版） | `.claude/commands/check-cinnamon-original-backup` | 比較・参照用 |
| **🆕 長期履歴分析** | メイン版で対応 | `.claude/commands/check-cinnamon` | 24時間エラー履歴対応 |
| **Claude Code標準** | AI最適化版 | `cinnamon-logs-ai-optimized.sh` | 構造化出力 |
| **問題詳細調査** | AI最適化版 | `cinnamon-logs-ai-optimized.sh` | 根本原因分析 |
| **基本チェック** | 統合インターフェース | `cinnamon-monitor-suite.sh basic` | 基本監視 |
| **緊急対応** | 統合インターフェース | `cinnamon-monitor-suite.sh emergency` | 即時対応 |

### Claude Code分析システム
```bash
# 📊 包括分析コマンド（推奨）
.claude/commands/check-cinnamon
# 特徴: 詳細な分析機能、24時間エラー履歴、実行メタデータ収集
# 注: 実行時間の高速化は優先事項ではありません。機能性と正確性を重視

# 🔄 従来版包括分析（詳細調査・比較用）
.claude/commands/check-cinnamon-original-backup
# 特徴: 24時間エラー履歴、実行メタデータ収集、自動改善提案

# AI最適化版での問題特定・修正提案
.claude/cinnamon-logs-ai-optimized.sh

# 重要度別分類
# 🚨 CRITICAL: 即座の修正が必要（KeyError等のコード問題）
# ⚠️ WARNING: 注意が必要（認証エラー、パフォーマンス低下）
# ℹ️ INFO: 情報提供レベル（最適化提案）
# ✅ OK: 正常状態の確認

# 🔄 自己改善機能
# 📊 実行メタデータ収集: 性能指標、検出精度の自動記録
# 📈 履歴トレンド分析: 過去実行との比較・改善傾向判定
# 💡 自動改善提案: 具体的な最適化案の生成
# 🚨 緊急改善検出: 重大な性能低下時の即座アラート
```

### 重要な数値
- **GraphQLレート制限**: 150リクエスト/15分
- **RESTレート制限**: 300ブロック/15分
- **最適バッチサイズ**: 50件
- **キャッシュTTL**: 30日
- **目標処理速度**: 50件/秒以上

### 🔧 新機能: 拡張ヘッダー対応 (Issue #38)
- **動的ヘッダー生成**: Twitter/Xアンチボットシステム対応
- **段階的導入**: `--disable-header-enhancement`、`--enable-forwarded-for`オプション
- **詳細**: `.claude/guides/api-patterns.md` 参照

### 🔢 新機能: 高度なバージョン管理システム
- **動的バージョン取得**: Git・環境変数・ファイルベースの優先順位システム
- **--versionオプション**: `python3 -m twitter_blocker --version` で現在バージョン表示
- **GitHub連携**: リリース監視・自動更新・整合性確認
- **運用統合**: check-cinnamon、update-containers、monitor-releasesの連携システム
- **Docker対応**: APPLICATION_VERSION、.app-versionファイル埋め込み

---

この基本方針と詳細ドキュメントにより、効率的で高品質なtwitter-bulk-blocker開発を実現します。
詳細が必要な場合は該当する.claudeドキュメントを参照してください。