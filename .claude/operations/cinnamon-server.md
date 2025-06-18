# Cinnamonサーバー運用ガイド

## 概要
Cinnamonサーバーは複数のTwitterアカウントで自動ブロック処理を並列実行するための専用サーバーです。このドキュメントは本番環境での運用に特化した情報を提供します。

## 基本情報
- **アクセス方法**: `ssh Cinnamon`
- **プロジェクトパス**: `/mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users`
- **Docker Compose設定**: `compose.yaml`

## 稼働中のサービス
- `book000`: promoted_and_blueverified.json対象
- `book000_vrc`: promoted_only.json対象  
- `ihc_amot`: promoted_only.json対象
- `tomachi_priv`: promoted_and_blueverified.json対象
- `authorizedkey`: promoted_and_blueverified.json対象
- `tomarabbit`: promoted_and_blueverified.json対象

## Claude Codeコマンド

### `/project:check-cinnamon`
包括的なサーバー状態調査を実行

### `/project:restart-service [service_name]`
指定サービスまたは全サービスの再起動

## 運用監視

### 日常チェック項目
1. **コンテナ状態確認**
   ```bash
   ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose ps"
   ```

2. **エラー統計確認**
   ```bash
   ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose logs --tail 1000 | grep -E '(エラー|error|failed|401|403|429|500)' | sort | uniq -c | sort -nr | head -10"
   ```

3. **各サービスの処理状況**
   ```bash
   for service in book000 book000_vrc ihc_amot tomachi_priv authorizedkey tomarabbit; do
       echo "=== $service ==="
       ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose logs $service --tail 50 | grep -E '(ブロック成功|スキップ|エラー)' | tail -5"
   done
   ```

### 問題の兆候
- **🔴 緊急**: 全コンテナ停止、継続的な401認証エラー
- **🟡 要注意**: 403エラーの急増、特定サービスの異常停止
- **🟢 正常**: 404エラー（削除済みアカウント）、一時的なレートリミット

## エラー対処

### 認証エラー（401）対応
1. **Cookie確認**
   ```bash
   # 該当アカウントのCookieファイル確認
   ssh Cinnamon "ls -la /mnt/hdd/cinnamon/twitter-chrome/userdata/{account_name}/cookies.json"
   ```

2. **Cookie更新手順**
   - 対象アカウントでChromeに再ログイン
   - Cookie抽出ツールでcookies.jsonを更新
   - 該当Dockerサービスを再起動

### 403エラー分析
```bash
# 403エラーの詳細調査
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose logs --tail 200 | grep -A10 -B5 'Status Code: 403'"

# 影響サービスの特定
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose logs --tail 500 | grep -E '403.*authorizedkey|403.*book000|403.*tomachi'"
```

### レートリミット確認
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose logs --tail 200 | grep -E 'Rate Limit:' | tail -10"
```

## 緊急時対応

### 全体停止
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose down"
```

### 全体再起動
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose up -d"
```

### 個別サービス再起動
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose restart {service_name}"
```

## エスカレーション基準

### 即座にエスカレーション
- 全サービス停止（30分以上）
- 継続的な認証エラー（1時間以上）
- セキュリティ関連の異常

### 監視継続
- 一時的な403エラー
- 個別サービスの一時停止
- レートリミットによる待機

## 定期メンテナンス

### 週次作業
- ログファイルのローテーション確認
- ディスク容量チェック
- パフォーマンス統計の確認

### 月次作業
- Cookie有効期限の確認
- Docker imageの更新確認
- 処理統計の分析