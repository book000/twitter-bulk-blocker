# エラー統計分析

Cinnamonサーバーの各種エラーを統計的に分析し、問題の優先度を判定します。

引数として期間を指定できます: `/project:analyze-error-stats [時間]`
- 例: `/project:analyze-error-stats 1h` (過去1時間)
- 例: `/project:analyze-error-stats 24h` (過去24時間)
- 引数なしの場合はデフォルトで最新1000行を分析

$ARGUMENTSが指定されている場合は時間ベースの分析を実行:
```bash
SINCE_TIME="$ARGUMENTS"
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose logs --since='$SINCE_TIME' | grep -E '(エラー|error|failed|401|403|429|500)'"
```

引数なしの場合は行数ベースの分析:
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose logs --tail 1000 | grep -E '(エラー|error|failed|401|403|429|500)' | sort | uniq -c | sort -nr"
```

**分析項目**:
1. エラータイプ別の発生頻度
2. サービス別のエラー分布
3. 時系列でのエラートレンド
4. 致命的エラーの特定
5. 対処が必要なエラーの優先度判定

**判定基準**:
- 🔴 **緊急**: 401認証エラーの継続、全コンテナ停止
- 🟡 **要監視**: 403エラーの急増、特定サービスの高頻度エラー
- 🟢 **正常**: 404エラー（削除済みアカウント）、一時的なレートリミット