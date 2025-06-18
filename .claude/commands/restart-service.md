# Cinnamonサーバーサービス再起動

指定されたサービスまたは全サービスを再起動します。

使用方法: `/project:restart-service [service_name]`

引数:
- `service_name` (オプション): 特定のサービス名（book000, book000_vrc, ihc_amot, tomachi_priv, authorizedkey, tomarabbit）
- 引数なしの場合は全サービスを再起動

$ARGUMENTSが指定されている場合:
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose restart $ARGUMENTS"
```

引数が指定されていない場合:
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose restart"
```

再起動後、サービスの状態を確認してください:
```bash
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose ps"
```