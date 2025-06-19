# Cinnamonサーバー接続方法 - 確実な接続ガイド

## 🔑 正しい接続方法

### **基本接続コマンド**
```bash
ssh Cinnamon
```

⚠️ **重要**: IP アドレス直接指定や間違ったホスト名は使用しない

### ❌ 間違った接続方法（使用禁止）
```bash
ssh ope@cinnamon.oimo.io         # ホスト名解決エラー
ssh ope@183.90.238.206          # IP直接指定（タイムアウト）
ssh user@cinnamon               # ユーザー名指定不正
```

### ✅ 正しい接続方法（必須）
```bash
ssh Cinnamon                    # SSH設定で定義済みのホスト名
```

## 📋 SSH設定の確認

### 接続設定の存在確認
```bash
# SSH設定ファイルでCinnamonホストが定義されているか確認
grep -A 10 "Host Cinnamon" ~/.ssh/config
```

### 期待される設定例
```
Host Cinnamon
    HostName [正しいホスト名またはIP]
    User [正しいユーザー名]
    Port [正しいポート]
    IdentityFile [正しい秘密鍵のパス]
```

## 🔧 自動接続確認機能

### 接続テスト関数
```bash
#!/bin/bash
test_cinnamon_connection() {
    echo "🔍 Cinnamonサーバー接続テスト中..."
    
    if ssh Cinnamon "echo 'Connection successful'" >/dev/null 2>&1; then
        echo "✅ Cinnamon接続: 正常"
        return 0
    else
        echo "❌ Cinnamon接続: 失敗"
        echo "SSH設定を確認してください: ~/.ssh/config"
        return 1
    fi
}
```

## 🚨 緊急時の対処法

### 接続できない場合の診断手順
1. **SSH設定確認**
   ```bash
   cat ~/.ssh/config | grep -A 5 "Host Cinnamon"
   ```

2. **ネットワーク確認**
   ```bash
   ssh -v Cinnamon  # 詳細ログで問題特定
   ```

3. **代替接続方法の検討**
   - 設定に記載されたIP/ホスト名での直接接続を試行
   - VPN接続状態の確認

## 📊 接続方法の統一

### Claude Code スクリプトでの標準化
```bash
# すべてのスクリプトでこの形式を使用
CINNAMON_CONNECTION="ssh Cinnamon"

# 使用例
$CINNAMON_CONNECTION "docker compose ps"
$CINNAMON_CONNECTION "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && docker compose logs"
```

### 接続前チェック機能
```bash
ensure_cinnamon_connection() {
    if ! ssh Cinnamon "true" >/dev/null 2>&1; then
        echo "❌ Cinnamonサーバーに接続できません"
        echo "SSH設定を確認してください: ~/.ssh/config"
        echo "正しい接続方法: ssh Cinnamon"
        exit 1
    fi
}
```

## 📝 開発者向けガイドライン

### スクリプト作成時の注意点
1. **常に `ssh Cinnamon` を使用**
2. **接続テストを実装**
3. **エラー時の明確なメッセージ**
4. **代替手段の提示**

### テンプレートコード
```bash
#!/bin/bash
# Cinnamon操作スクリプトテンプレート

# 接続確認
if ! ssh Cinnamon "true" >/dev/null 2>&1; then
    echo "❌ Error: Cannot connect to Cinnamon server"
    echo "Please check SSH configuration: ~/.ssh/config"
    echo "Correct usage: ssh Cinnamon"
    exit 1
fi

echo "✅ Connected to Cinnamon server"

# 実際の操作
ssh Cinnamon "cd /mnt/hdd/cinnamon/twitter-auto-blocking/bulk-block-users && your_command_here"
```

## 🔄 自動修正機能

### 間違った接続方法の自動検出
```bash
detect_wrong_connection() {
    if grep -r "ssh.*cinnamon\.oimo\.io\|ssh.*183\.90\.238\.206" .claude/ 2>/dev/null; then
        echo "⚠️ 警告: 間違った接続方法が検出されました"
        echo "修正してください: ssh Cinnamon"
        return 1
    fi
    return 0
}
```

この文書に従って、今後すべてのCinnamonサーバー接続は `ssh Cinnamon` で統一してください。