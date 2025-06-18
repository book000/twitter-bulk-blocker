# Cinnamonサーバー運用ガイド

## 概要
Cinnamonサーバーは複数のTwitterアカウントで自動ブロック処理を並列実行するための専用サーバーです。

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

## 利用可能なコマンド（Claude Code）

### `/project:check-cinnamon`
包括的なサーバー状態調査を実行

### `/project:restart-service [service_name]`
指定サービスまたは全サービスの再起動

### `/project:debug-403-errors`
403エラーの詳細調査と分析

### `/project:analyze-error-stats [時間]`
エラー統計の分析と優先度判定

### `/project:test-local-api [username]`
ローカル環境でのAPI動作テスト

## エラー対処ガイド

### 認証エラー（401）
**症状**: `Authentication failed - Cookie is invalid`
**対処**: 該当アカウントのCookie更新が必要

### アクセス拒否（403）
**症状**: `Status Code: 403` + 空のレスポンステキスト
**原因**: Twitter API側の制限強化
**対処**: 一時的な場合は自動回復、継続する場合は調査が必要

### ユーザー未発見（404）
**症状**: `ユーザーが見つからない`
**対処**: 正常動作（削除済みアカウントのスキップ）

### レートリミット（429）
**症状**: `Rate limit exceeded`
**対処**: 自動で待機・再試行（正常動作）

## Cookie管理

### Cookieファイルの場所
```
/mnt/hdd/cinnamon/twitter-chrome/userdata/{account_name}/cookies.json
```

### Cookie更新手順
1. 対象アカウントでChromeに再ログイン
2. Cookie抽出ツールでcookies.jsonを更新
3. 該当Dockerサービスを再起動

## 監視指標

### 正常状態
- コンテナが `Up (healthy)` 状態
- `✓ ブロック成功` ログが継続出力
- レートリミット適切管理（例: `149/150`）

### 要注意状態
- 一部サービスが `Exited` 状態
- 401/403エラーの継続発生
- 全APIリクエストの失敗

## 緊急時対応

### 全体停止
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose down"
```

### 全体再起動
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose up -d"
```