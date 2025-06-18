# 403エラー詳細調査

Twitter APIの403エラーの詳細な調査と分析を実行します。

このコマンドは以下を実行します：

1. **最新の403エラーログを抽出**:
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose logs --tail 200 | grep -A10 -B5 'Status Code: 403'"
```

2. **403エラーの頻度とパターン分析**:
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose logs --tail 1000 | grep '403' | wc -l"
```

3. **影響を受けているサービスの特定**:
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose logs --tail 500 | grep -E '403.*authorizedkey|403.*book000|403.*tomachi'"
```

4. **レスポンステキストの内容確認**: 空白かどうかを検証
5. **Cookie認証状態の確認**: 401エラーとの相関関係を調査

**403エラーの一般的な原因**:
- Twitter API側の制限強化
- アカウント固有の制限
- レートリミット関連の一時的制限
- Cookie認証の部分的な問題

調査結果に基づいて適切な対処法を提案します。