# 使用例集

## 基本的な使用方法

### 1. デフォルトファイルでテスト実行

```bash
python3 main.py
```

### 2. デフォルトファイルで本格実行

```bash
python3 main.py --all
```

### 3. 自動リトライ付き本格実行

```bash
python3 main.py --all --auto-retry
```

## ファイルパス指定

### 4. 絶対パスで指定

```bash
python3 main.py --all \
  --cookies /home/user/twitter/cookies.json \
  --users-file /home/user/twitter/block_targets.json \
  --db /home/user/twitter/block_history.db
```

### 5. 相対パスで指定

```bash
python3 main.py --all \
  --cookies ./data/cookies.json \
  --users-file ./data/users.json \
  --db ./data/history.db
```

### 6. 環境変数で指定

```bash
export TWITTER_COOKIES_PATH=/home/user/twitter/cookies.json
export TWITTER_USERS_FILE=/home/user/twitter/users.json
export TWITTER_BLOCK_DB=/home/user/twitter/history.db

python3 main.py --all --auto-retry
```

## 処理制御

### 7. 最大100人まで処理

```bash
python3 main.py --all --max-users 100
```

### 8. 処理間隔を2秒に設定

```bash
python3 main.py --all --delay 2.0
```

### 9. リトライのみ実行

```bash
python3 main.py --retry
```

### 10. 統計情報表示

```bash
python3 main.py --stats
```

## 複合的な使用例

### 11. 高速処理（0.5秒間隔）

```bash
python3 main.py --all --delay 0.5 --auto-retry
```

### 12. 慎重な処理（3秒間隔、最大50人）

```bash
python3 main.py --all --delay 3.0 --max-users 50
```

### 13. カスタムファイルでテスト

```bash
python3 main.py \
  --cookies ./test_cookies.json \
  --users-file ./test_users.json \
  --db ./test_history.db \
  --max-users 5
```

### 14. バックアップデータベースを使用

```bash
python3 main.py --all \
  --db ./backup/block_history_$(date +%Y%m%d).db \
  --auto-retry
```

## エラー対処例

### 15. ファイル不存在エラーのテスト

```bash
python3 main.py --cookies ./nonexistent.json
# ❌ エラー: クッキーファイルが見つかりません: ./nonexistent.json
```

### 16. 環境変数の確認

```bash
echo "TWITTER_COOKIES_PATH: $TWITTER_COOKIES_PATH"
echo "TWITTER_USERS_FILE: $TWITTER_USERS_FILE"
echo "TWITTER_BLOCK_DB: $TWITTER_BLOCK_DB"
```

## バッチ処理例

### 17. シェルスクリプトでの自動化

```bash
#!/bin/bash
# batch_block.sh

# 設定
export TWITTER_COOKIES_PATH=/home/user/twitter/cookies.json
export TWITTER_USERS_FILE=/home/user/twitter/block_targets.json
export TWITTER_BLOCK_DB=/home/user/twitter/block_history.db

# 実行前統計
echo "=== 実行前統計 ==="
python3 main.py --stats

# メイン処理
echo "=== メイン処理開始 ==="
python3 main.py --all --auto-retry --delay 1.5

# 実行後統計
echo "=== 実行後統計 ==="
python3 main.py --stats

echo "=== 処理完了 ==="
```

### 18. cron で定期実行

```bash
# crontab -e で以下を追加
# 毎日午前2時に実行
0 2 * * * cd /path/to/twitter-block && python3 main.py --retry >> /var/log/twitter-block.log 2>&1
```

## デバッグ・トラブルシューティング

### 19. ファイルパス確認

```bash
python3 main.py --stats --cookies ./cookies.json --users-file ./users.json --db ./test.db
```

### 20. 最小限テスト（1人のみ）

```bash
python3 main.py --max-users 1 --delay 5.0
```
