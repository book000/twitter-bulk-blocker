# check-cinnamon パフォーマンス最適化ガイド

## 🚀 最適化版の概要

### 1. **check-cinnamon** (オリジナル)
- **実行時間**: 60秒以上
- **用途**: 完全な診断、詳細なトラブルシューティング
- **特徴**: 2031行、62回のSSH接続、包括的な分析

### 2. **check-cinnamon-optimized** (最適化版)
- **実行時間**: 15-20秒
- **用途**: 通常の監視、定期チェック
- **特徴**: 
  - SSH接続を1回に統合
  - キャッシュ機能（60秒TTL）
  - 構造化されたデータ収集
  - カラー出力で視認性向上

### 3. **check-cinnamon-fast** (高速版)
- **実行時間**: 10-15秒
- **用途**: 頻繁なチェック、CI/CD統合
- **特徴**:
  - 並列処理でデータ収集
  - SSHコントロールマスター使用
  - 最小限の出力フォーマット
  - エラーは直近1時間のみ

### 4. **check-cinnamon-minimal** (最小版)
- **実行時間**: 3-5秒
- **用途**: ヘルスチェック、死活監視
- **特徴**:
  - 最重要情報のみ（コンテナ状態、エラー有無、負荷）
  - 1回のSSH接続で完結
  - タイムアウト設定で高速化

## 📊 パフォーマンス比較

| バージョン | 実行時間 | SSH接続数 | 出力行数 | キャッシュ | 並列処理 |
|-----------|---------|----------|---------|----------|----------|
| オリジナル | 60秒+ | 62回 | 500行+ | なし | なし |
| optimized | 15-20秒 | 1-2回 | 100行 | あり | なし |
| fast | 10-15秒 | 1回 | 50行 | なし | あり |
| minimal | 3-5秒 | 1回 | 5-10行 | なし | なし |

## 🔧 最適化技術

### 1. SSH接続の統合
```bash
# ❌ 非効率: 複数のSSH接続
ssh Cinnamon "docker ps"
ssh Cinnamon "docker logs container1"
ssh Cinnamon "docker logs container2"

# ✅ 効率的: 1回の接続で全データ取得
ssh Cinnamon '
docker ps
docker logs container1
docker logs container2
'
```

### 2. SSHコントロールマスター
```bash
# SSH接続の再利用
SSH_OPTS="-o ControlMaster=auto -o ControlPath=/tmp/ssh-%r@%h:%p -o ControlPersist=30s"
ssh $SSH_OPTS Cinnamon "command1"
ssh $SSH_OPTS Cinnamon "command2"  # 既存接続を再利用
```

### 3. 並列処理
```bash
# リモートでの並列実行
get_containers &
get_errors &
get_system &
wait
```

### 4. キャッシュ戦略
```bash
# 頻繁に変更されないデータのキャッシュ
CACHE_FILE="/tmp/.check-cinnamon-cache/data"
if [ -f "$CACHE_FILE" ] && [ $(($(date +%s) - $(stat -c %Y "$CACHE_FILE"))) -lt 60 ]; then
    cat "$CACHE_FILE"
else
    ssh Cinnamon "command" | tee "$CACHE_FILE"
fi
```

## 🎯 使い分けガイド

### 開発時
```bash
# 問題調査時（詳細情報が必要）
.claude/commands/check-cinnamon

# 通常の確認
.claude/commands/check-cinnamon-optimized
```

### 運用時
```bash
# 定期監視（cronなど）
*/5 * * * * /path/to/check-cinnamon-fast

# ヘルスチェック（監視システム連携）
*/1 * * * * /path/to/check-cinnamon-minimal
```

### CI/CD
```bash
# デプロイ前チェック
.claude/commands/check-cinnamon-fast

# デプロイ後の簡易確認
.claude/commands/check-cinnamon-minimal
```

## 📈 さらなる最適化のアイデア

1. **プロセス監視デーモン**
   - 常駐プロセスでデータ収集
   - WebSocketやgRPCでリアルタイム配信

2. **メトリクス収集**
   - PrometheusやGrafana連携
   - 時系列データの可視化

3. **アラート統合**
   - Slack/Discord通知
   - PagerDuty連携

4. **分散キャッシュ**
   - Redis使用でマルチユーザー対応
   - TTL管理の高度化

## 🔄 移行ガイド

既存のcheck-cinnamonからの移行：

```bash
# 1. エイリアス設定（段階的移行）
alias check-cinnamon-original="/path/to/check-cinnamon"
alias check-cinnamon="/path/to/check-cinnamon-optimized"

# 2. スクリプト内での使用
if [ "$FAST_MODE" = "1" ]; then
    .claude/commands/check-cinnamon-fast
else
    .claude/commands/check-cinnamon-optimized
fi

# 3. 環境変数での制御
export CHECK_CINNAMON_MODE="fast"  # fast, optimized, minimal
```