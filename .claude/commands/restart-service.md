Cinnamonサーバーのサービス再起動を実行します。

引数処理：
- `$ARGUMENTS` が指定されている場合：指定されたサービスのみ再起動
- 引数なしの場合：全サービスを再起動

対象サービス：book000, book000_vrc, ihc_amot, tomachi_priv, authorizedkey, tomarabbit

以下の手順で実行してください：

1. **サービス再起動の実行**
   - 引数がある場合：`ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose restart $ARGUMENTS"`
   - 引数なしの場合：`ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose restart"`

2. **再起動後の状態確認**
   - コンテナ状態の確認：`ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose ps"`
   - エラーログの確認：`ssh Cinnamon "docker logs --tail 10 bulk-block-users-[service]-1"`

3. **結果報告**
   - 再起動の成功/失敗を報告
   - エラーが発生した場合は詳細を分析
   - 必要に応じて追加の対応を提案