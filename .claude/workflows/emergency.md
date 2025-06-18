# 緊急時対応ワークフロー

## 緊急事態の分類

### レベル1: 重大（システム停止）
```yaml
症状:
  - アプリケーション完全停止
  - データベース破損
  - 認証完全失敗
  - 大量データ消失

対応時間: 即座（5分以内）
責任者: 開発チーム全員
エスカレーション: 必要
```

### レベル2: 高（機能障害）
```yaml
症状:
  - 特定機能の完全停止
  - パフォーマンス大幅劣化
  - API制限違反による長期停止
  - セキュリティ脆弱性発見

対応時間: 30分以内
責任者: 担当開発者
エスカレーション: 1時間で未解決時
```

### レベル3: 中（部分的問題）
```yaml
症状:
  - 一部ユーザーへの影響
  - 軽微なデータ不整合
  - 非重要機能の障害
  - パフォーマンス軽微劣化

対応時間: 2時間以内
責任者: 担当開発者
エスカレーション: 1営業日で未解決時
```

## 即座実行手順（レベル1）

### 1. 緊急停止・状況確認（5分以内）
```bash
# アプリケーション緊急停止
pkill -f "python.*twitter_blocker"
pkill -f "python.*main.py"

# プロセス確認
ps aux | grep -E "(twitter_blocker|main.py)"

# システム状況確認
df -h  # ディスク容量
free -m  # メモリ使用量
top  # CPU/プロセス状況

echo "✅ 緊急停止完了 $(date)"
```

### 2. 緊急バックアップ（2分以内）
```bash
#!/bin/bash
# emergency-backup.sh

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="emergency_backup_${TIMESTAMP}"

mkdir -p "$BACKUP_DIR"

# 重要ファイルの緊急バックアップ
cp block_history.db "$BACKUP_DIR/" 2>/dev/null
cp cookies.json "$BACKUP_DIR/" 2>/dev/null
cp users.json "$BACKUP_DIR/" 2>/dev/null
cp -r cache/ "$BACKUP_DIR/" 2>/dev/null

# バックアップ確認
ls -la "$BACKUP_DIR/"

echo "🚨 緊急バックアップ完了: $BACKUP_DIR"
echo "バックアップ時刻: $(date)"
```

### 3. 問題診断（5分以内）
```bash
#!/bin/bash
# emergency-diagnosis.sh

echo "🔍 緊急診断開始 $(date)"
echo "================================"

# ファイルシステム確認
echo "## ディスク使用量"
df -h

echo -e "\n## 重要ファイル存在確認"
for file in block_history.db cookies.json users.json; do
    if [ -f "$file" ]; then
        echo "✅ $file (サイズ: $(stat -c%s $file) bytes)"
    else
        echo "❌ $file (存在しない)"
    fi
done

echo -e "\n## データベース整合性確認"
if sqlite3 block_history.db "PRAGMA integrity_check;" 2>/dev/null; then
    echo "✅ データベース正常"
else
    echo "❌ データベース破損の可能性"
fi

echo -e "\n## メモリ・プロセス状況"
free -m
ps aux | grep -E "(twitter|python)" | head -10

echo -e "\n## 最新ログ（直近50行）"
tail -50 twitter_blocker.log 2>/dev/null || echo "ログファイルなし"

echo -e "\n## ネットワーク確認"
ping -c 3 twitter.com 2>/dev/null && echo "✅ ネットワーク正常" || echo "❌ ネットワーク問題"

echo "🔍 緊急診断完了 $(date)"
```

## 問題別対応手順

### データベース破損
```bash
# 1. 破損状況確認
sqlite3 block_history.db "PRAGMA integrity_check;"

# 2. 修復試行
sqlite3 block_history.db "PRAGMA main.integrity_check;"
sqlite3 block_history.db ".recover" | sqlite3 recovered.db

# 3. バックアップからの復旧
if [ -f "backup/block_history_latest.db" ]; then
    cp "backup/block_history_latest.db" block_history.db
    echo "✅ バックアップから復旧"
else
    echo "❌ バックアップファイルなし"
fi

# 4. 最小限データベース再作成
if [ ! -f "block_history.db" ]; then
    python3 -c "
from twitter_blocker.database import DatabaseManager
db = DatabaseManager('block_history.db')
db.init_database()
print('✅ 最小限データベース作成完了')
"
fi
```

### 認証失敗
```bash
# 1. クッキーファイル確認
if [ -f "cookies.json" ]; then
    echo "📄 現在のクッキーファイル:"
    jq '.' cookies.json 2>/dev/null || echo "❌ JSONパース失敗"
else
    echo "❌ cookies.json が存在しません"
fi

# 2. 認証状態テスト
python3 -c "
from twitter_blocker.twitter_api import TwitterAPI
api = TwitterAPI()
try:
    user_info = api.get_login_user_info()
    print(f'✅ 認証成功: {user_info}')
except Exception as e:
    print(f'❌ 認証失敗: {e}')
"

# 3. クッキー修復手順
echo "🔧 クッキー修復手順:"
echo "1. ブラウザでTwitterにログイン"
echo "2. 開発者ツール > Application > Cookies"
echo "3. ct0とauth_tokenの値をコピー"
echo "4. cookies.jsonを更新"
```

### API制限違反
```bash
# 1. API制限状況確認
python3 -c "
import requests
import json

# 最後のAPI応答ヘッダー確認（ログから）
print('📊 API制限状況の確認が必要')
print('1. 最新のAPIエラーログを確認')
print('2. x-rate-limit-* ヘッダーの値を確認')
print('3. 制限解除まで待機')
"

# 2. 強制待機
echo "⏰ API制限解除待機（15分）"
sleep 900

# 3. 段階的復旧
echo "🔄 段階的復旧開始"
python3 main.py --max-users 1 --delay 5.0  # 最小限テスト
```

### 大容量ファイル問題
```bash
# 1. 大容量ファイル検出
find . -type f -size +100M -exec ls -lh {} + 2>/dev/null

# 2. ログファイル圧縮・削除
gzip twitter_blocker.log 2>/dev/null
find . -name "*.log" -mtime +7 -delete

# 3. キャッシュクリーンアップ
rm -rf cache/lookups/*.json
rm -rf cache/profiles/*.json
rm -rf cache/relationships/*.json

echo "🧹 クリーンアップ完了"
df -h  # 容量確認
```

## 復旧手順

### 段階的復旧
```bash
#!/bin/bash
# gradual-recovery.sh

echo "🔄 段階的復旧開始"

# フェーズ1: 最小限機能確認
echo "## フェーズ1: 最小限テスト"
timeout 30 python3 main.py --max-users 1 --delay 5.0
if [ $? -eq 0 ]; then
    echo "✅ フェーズ1成功"
else
    echo "❌ フェーズ1失敗 - 基本機能に問題"
    exit 1
fi

# フェーズ2: 少量データテスト
echo "## フェーズ2: 少量データテスト"
timeout 60 python3 main.py --max-users 5 --delay 3.0
if [ $? -eq 0 ]; then
    echo "✅ フェーズ2成功"
else
    echo "❌ フェーズ2失敗 - スケール問題の可能性"
    exit 1
fi

# フェーズ3: 通常運用復帰
echo "## フェーズ3: 通常運用復帰"
echo "手動確認後、通常パラメーターで実行してください"
echo "python3 main.py --all --auto-retry"
```

### データ整合性確認
```bash
#!/bin/bash
# data-integrity-check.sh

echo "🔍 データ整合性確認"

# データベーステーブル確認
sqlite3 block_history.db "
.tables
SELECT COUNT(*) as total_records FROM block_history;
SELECT status, COUNT(*) FROM block_history GROUP BY status;
SELECT COUNT(*) as permanent_failures FROM block_history WHERE status = 'failed' AND user_status IN ('suspended', 'not_found', 'deactivated');
"

# 重複データ確認
sqlite3 block_history.db "
SELECT user_id, screen_name, COUNT(*) as count 
FROM block_history 
GROUP BY user_id, screen_name 
HAVING count > 1;
"

# ファイル整合性
echo "## ファイル整合性"
md5sum block_history.db cookies.json users.json 2>/dev/null

echo "✅ データ整合性確認完了"
```

## 通信・連絡体制

### インシデント報告テンプレート
```markdown
# 🚨 緊急インシデント報告

## 基本情報
- **発生時刻**: YYYY-MM-DD HH:MM:SS
- **検出者**: [名前]
- **重要度**: レベル1/2/3
- **影響範囲**: [影響を受ける機能・ユーザー]

## 症状
- **現象**: [具体的な症状]
- **エラーメッセージ**: [エラーメッセージ全文]
- **再現方法**: [再現手順]

## 実施済み対応
- [ ] 緊急停止実行
- [ ] バックアップ作成
- [ ] 問題診断実行
- [ ] [その他の実施済み対応]

## 現在の状況
- **システム状態**: 停止中/部分動作/正常
- **データ影響**: あり/なし/不明
- **復旧予想時間**: [予想時間]

## 次のアクション
1. [次に実行予定のアクション]
2. [代替手段の検討]
3. [エスカレーション予定]

## 添付情報
- ログファイル: [ファイル名]
- スクリーンショット: [必要に応じて]
- 診断結果: [diagnostic結果]
```

### エスカレーション基準
```yaml
即座エスカレーション:
  - データ消失発生
  - セキュリティ侵害疑い
  - 復旧方法不明

時間制限エスカレーション:
  - レベル1: 1時間で未解決
  - レベル2: 4時間で未解決  
  - レベル3: 1営業日で未解決

エスカレーション先:
  - シニア開発者
  - プロジェクトマネージャー
  - システム管理者
```

## 事後対応

### インシデントレポート作成
```markdown
# インシデント事後報告書

## インシデント概要
- **インシデントID**: INC-YYYYMMDD-001
- **発生期間**: [開始時刻] - [解決時刻]
- **影響時間**: [時間]
- **重要度**: レベル1/2/3

## 根本原因分析
### 直接原因
[問題の直接的な原因]

### 根本原因
[問題の根本的な原因]

### 要因分析
1. [要因1]
2. [要因2]
3. [要因3]

## 対応タイムライン
| 時刻 | 実施者 | アクション | 結果 |
|------|--------|------------|------|
| HH:MM | [名前] | [アクション] | [結果] |

## 影響評価
- **システム停止時間**: [時間]
- **影響ユーザー数**: [人数]
- **データ影響**: [影響内容]
- **ビジネス影響**: [影響評価]

## 改善アクション
### 即座実施（完了済み）
- [ ] [改善アクション1]
- [ ] [改善アクション2]

### 短期実施（1週間以内）
- [ ] [改善アクション3]
- [ ] [改善アクション4]

### 長期実施（1ヶ月以内）
- [ ] [改善アクション5]
- [ ] [改善アクション6]

## 学習・改善点
1. [学習事項1]
2. [学習事項2]
3. [プロセス改善点]

## 添付資料
- ログファイル
- 診断結果
- 復旧スクリプト
```

### 予防策実装
```bash
#!/bin/bash
# preventive-measures.sh

echo "🛡️ 予防策実装"

# 1. 自動バックアップの設定
cat > backup_cron.sh << 'EOF'
#!/bin/bash
# 毎時間実行のバックアップ
TIMESTAMP=$(date +%Y%m%d_%H%M)
BACKUP_DIR="backup/auto_${TIMESTAMP}"

mkdir -p "$BACKUP_DIR"
cp block_history.db "$BACKUP_DIR/"
cp cookies.json "$BACKUP_DIR/" 2>/dev/null
cp users.json "$BACKUP_DIR/" 2>/dev/null

# 古いバックアップの削除（24時間以上前）
find backup/ -name "auto_*" -mtime +1 -exec rm -rf {} + 2>/dev/null

echo "✅ 自動バックアップ完了: $BACKUP_DIR"
EOF

chmod +x backup_cron.sh

# 2. ヘルスチェックスクリプト
cat > health_check.sh << 'EOF'
#!/bin/bash
# システムヘルスチェック

# データベース確認
if ! sqlite3 block_history.db "SELECT 1;" >/dev/null 2>&1; then
    echo "❌ データベースエラー検出"
    # 緊急処理実行
    ./emergency-backup.sh
fi

# ディスク容量確認
DISK_USAGE=$(df -h . | awk 'NR==2 {print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    echo "⚠️ ディスク使用量警告: ${DISK_USAGE}%"
fi

# メモリ使用量確認
MEMORY_USAGE=$(free | awk 'NR==2{printf "%.2f", $3*100/$2}')
if (( $(echo "$MEMORY_USAGE > 90" | bc -l) )); then
    echo "⚠️ メモリ使用量警告: ${MEMORY_USAGE}%"
fi

echo "✅ ヘルスチェック完了 $(date)"
EOF

chmod +x health_check.sh

# 3. 監視設定
echo "crontab設定例:"
echo "0 * * * * /path/to/backup_cron.sh"
echo "*/15 * * * * /path/to/health_check.sh"

echo "✅ 予防策実装完了"
```

## 緊急連絡先・リソース

### 重要ファイルの場所
```bash
# 設定ファイル
~/.claude/CLAUDE.md                    # Claude Code設定
./cookies.json                         # Twitter認証情報
./users.json                          # 処理対象ユーザー

# データファイル  
./block_history.db                    # メインデータベース
./cache/                              # キャッシュディレクトリ

# ログファイル
./twitter_blocker.log                 # アプリケーションログ
./error_log.jsonl                     # エラーログ

# バックアップ
./backup/                             # 手動バックアップ
./emergency_backup_*/                 # 緊急バックアップ
```

### 緊急時コマンド一覧
```bash
# 即座実行
./emergency-backup.sh                 # 緊急バックアップ
./emergency-diagnosis.sh              # 問題診断
./gradual-recovery.sh                 # 段階的復旧

# 確認コマンド
sqlite3 block_history.db "PRAGMA integrity_check;"  # DB整合性
python3 -c "from twitter_blocker.twitter_api import TwitterAPI; TwitterAPI().get_login_user_info()"  # 認証確認
df -h && free -m                      # システムリソース

# 復旧コマンド
cp backup/latest/block_history.db .   # DB復旧
python3 main.py --max-users 1         # 最小限テスト
python3 main.py --stats               # 統計確認
```