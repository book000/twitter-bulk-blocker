# 認証エラー監視システム

Twitter Bulk Blockerの認証エラーを詳細監視・分析するためのツールセット。

## 📋 概要

認証エラーの発生パターン、Cookie再読み込み状況、推奨対応アクションを自動分析し、適切な対処法を提示します。

## 🛠️ 利用可能なツール

### 1. check-cinnamon（統合監視・認証エラー強化版）
**用途**: 包括的なサーバー監視 + 詳細認証エラー分析
```bash
.claude/commands/check-cinnamon
```

**新機能（認証エラー対応強化）**:
- 時系列認証エラー分析（5分/1時間/6時間/24時間）
- エラータイプ別詳細分類（Cookie/CSRF/セッション/HTTP401/403）
- Cookie再読み込み成功率分析
- 重要度別アクション提示（CRITICAL/HIGH/MEDIUM/PREVENTIVE）
- 具体的対応コマンド提示

### 2. check-cinnamon-auth-enhanced（認証エラー特化版）
**用途**: 認証エラーのみに特化した深掘り分析
```bash
.claude/commands/check-cinnamon-auth-enhanced              # 24時間分析
.claude/commands/check-cinnamon-auth-enhanced --hours 6    # 6時間分析
.claude/commands/check-cinnamon-auth-enhanced --realtime   # リアルタイム監視
```

**特徴**:
- 認証エラーの根本原因分析
- エラータイムライン視覚化
- Cookie再読み込み詳細トラッキング
- サービス別認証状態分析
- リアルタイム監視モード

## 🔍 分析される認証エラータイプ

### エラー分類
1. **基本認証エラー**
   - `認証エラー`, `authentication failed`, `Could not authenticate you`

2. **Cookieエラー**
   - `cookie.*無効`, `cookie.*invalid`, `cookie.*expired`, `cookie.*missing`

3. **CSRFトークンエラー**
   - `csrf.*token`, `x-csrf-token`

4. **セッションエラー**
   - `session.*expired`, `session.*invalid`

5. **HTTPステータスエラー**
   - `unauthorized`, `401`, `forbidden.*auth`, `403.*auth`, `access.*denied`

6. **レート制限認証エラー**
   - `rate.*limit.*auth`, `too.*many.*auth`

## 🚨 アラートレベル

### CRITICAL（緊急対応）
- 5分間で5件以上の認証エラー
- 現在進行中の認証問題

### HIGH（早急対応）
- 1時間で10件以上の認証エラー
- Cookie再読み込み成功率50%未満
- 特定エラータイプの多発

### MEDIUM（監視継続）
- 24時間で認証エラーが発生
- 詳細分析が推奨される状況

### PREVENTIVE（予防的）
- 認証状態良好時の定期メンテナンス推奨

## 🔧 推奨対応アクション

### 緊急対応コマンド
```bash
# Cookie緊急更新
ssh Cinnamon 'cd ~/twitter-bulk-blocker && python3 -m twitter_blocker.update_cookies'

# Cookie完全更新
ssh Cinnamon 'cd ~/twitter-bulk-blocker && python3 -m twitter_blocker.refresh_all_cookies'

# Cookie品質確認
ssh Cinnamon 'python3 -m twitter_blocker.validate_cookies'

# Cookie状態確認
ssh Cinnamon 'python3 -m twitter_blocker.check_cookie_status'
```

### サービス管理
```bash
# 特定サービス再起動
ssh Cinnamon 'sudo systemctl restart twitter-blocker-1'

# 全サービス再起動
ssh Cinnamon 'sudo systemctl restart twitter-blocker-*'

# サービス状態確認
ssh Cinnamon 'sudo systemctl status twitter-blocker-*'
```

## 📊 使用例

### 基本的な認証状態確認
```bash
# 統合監視（認証エラー分析込み）
.claude/commands/check-cinnamon

# 認証エラーのみ詳細分析
.claude/commands/check-cinnamon-auth-enhanced
```

### トラブルシューティング
```bash
# 過去6時間の認証エラー詳細分析
.claude/commands/check-cinnamon-auth-enhanced --hours 6

# リアルタイム認証監視（60秒間隔）
.claude/commands/check-cinnamon-auth-enhanced --realtime 60
```

### 定期監視
```bash
# crontabで定期実行
# 毎時0分に認証状態チェック
0 * * * * /mnt/hdd/repos/twitter-bulk-blocker/.claude/commands/check-cinnamon-auth-enhanced >> /tmp/auth-monitor.log 2>&1
```

## 🔍 出力例

### 正常時
```
🔐 AUTHENTICATION STATUS (詳細認証エラー分析)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Authentication Error Timeline (詳細分析):
  • 最近5分間: 0 件
  • 最近1時間: 0 件
  • 最近6時間: 0 件
  • 最近24時間: 0 件

✅ No authentication errors in last 24 hours

🛡️ PREVENTIVE - 予防的メンテナンス:
  🛡️ [PREVENTIVE] 認証状態良好 - 定期メンテナンス推奨
     → 月次Cookie更新: 第1週実施予定
```

### 問題発生時
```
🔐 AUTHENTICATION STATUS (詳細認証エラー分析)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Authentication Error Timeline (詳細分析):
  • 最近5分間: 3 件
  • 最近1時間: 12 件
  • 最近6時間: 15 件
  • 最近24時間: 18 件

🔍 認証エラータイプ別分析（24時間）:
    • Cookieエラー: 12 件
    • HTTP 401エラー: 6 件

🔄 Cookie再読み込み分析:
    • 再読み込み試行: 4 回
    • 成功回数: 2 回
    • 成功率: 50%

⚠️ HIGH PRIORITY - 早急な対応推奨:
  ⚠️ [HIGH] 認証エラー多発 (1時間で12件)
     → Cookie更新推奨: ssh Cinnamon 'cd ~/twitter-bulk-blocker && python3 -m twitter_blocker.update_cookies'

🔧 認証エラー対応コマンド集:
  • 詳細認証分析: .claude/commands/check-cinnamon-auth-enhanced
  • リアルタイム監視: .claude/commands/check-cinnamon-auth-enhanced --realtime
  • Cookie状態確認: ssh Cinnamon 'python3 -m twitter_blocker.check_cookie_status'
  • 緊急Cookie更新: ssh Cinnamon 'cd ~/twitter-bulk-blocker && python3 -m twitter_blocker.emergency_cookie_refresh'
```

## 🔄 継続的改善

### 分析精度向上
- エラーパターンの継続的更新
- 新しい認証エラータイプの検出・追加
- 閾値の最適化

### 運用効率化
- 自動アラート通知の実装
- 対応アクション自動化の拡張
- 履歴データベース化

## 📚 関連ドキュメント

- `.claude/guides/api-patterns.md` - Twitter API操作パターン
- `.claude/guides/error-handling.md` - エラーハンドリング戦略
- `.claude/operations/cinnamon-server.md` - Cinnamonサーバー運用ガイド
- `CLAUDE.md` - プロジェクト基本設定