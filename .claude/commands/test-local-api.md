# ローカルAPI動作テスト

指定されたユーザーでローカル環境でのTwitter API動作をテストします。

使用方法: `/project:test-local-api [username]`

引数:
- `username`: テスト対象のTwitterユーザー名

$ARGUMENTSで指定されたユーザーでテストを実行:

```bash
# Cookieファイルの存在確認
if [ -f "test-cookies/cookies.json" ]; then
    echo "✅ Cookieファイル確認済み"
else
    echo "❌ Cookieファイルが見つかりません: test-cookies/cookies.json"
    echo "Cinnamonサーバーからコピーしますか？"
fi

# APIテスト実行
python3 -m twitter_blocker --cookies test-cookies/cookies.json --test-user "$ARGUMENTS" --cache-dir ./test-cache --debug
```

引数なしの場合はデフォルトユーザーでテスト:
```bash
python3 -m twitter_blocker --cookies test-cookies/cookies.json --test-user book000 --cache-dir ./test-cache
```

**テスト内容**:
1. Cookie認証の確認
2. 指定ユーザーの情報取得
3. APIレスポンスの詳細確認
4. エラーハンドリングの動作確認

**期待される結果**:
- ✅ 200レスポンス: 正常
- ⚠️ 403レスポンス: アクセス制限（詳細調査が必要）
- ❌ 401レスポンス: 認証エラー（Cookie更新が必要）
- ⏱️ 429レスポンス: レートリミット（正常動作）