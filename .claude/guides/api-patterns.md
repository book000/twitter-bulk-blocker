# Twitter API操作パターン詳細

## 必須Cookie認証
```python
REQUIRED_COOKIES = {
    "ct0": "32文字のCSRFトークン",
    "auth_token": "40文字のセッショントークン", 
    "twid": "u%3D1234567890",  # 任意
}

# 認証状態確認
def verify_auth():
    cookies = self.cookie_manager.load_cookies()
    return 'ct0' in cookies and 'auth_token' in cookies
```

## GraphQL APIエンドポイント
```python
ENDPOINTS = {
    "UserByScreenName": "qW5u-DAuXpMEG0zA1F7UGQ/UserByScreenName",
    "UserByRestId": "I5nvpI91ljifos1Y3Lltyg/UserByRestId",
    "UsersByRestIds": "OXBEDLUtUvKvNEP1RKRbuQ/UsersByRestIds",  # バッチ用
}

# フィーチャーフラグ（定期更新必要）
FEATURES = {
    "hidden_profile_likes_enabled": True,
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    # 他約10個...定期的にTwitterの仕様変更をチェック
}
```

## レート制限管理（精密）
```python
RATE_LIMITS = {
    "UserByScreenName": {"requests": 150, "window": 900},
    "UsersByRestIds": {"requests": 150, "window": 900}, 
    "blocks/create": {"requests": 300, "window": 900},
}

def _calculate_wait_time(self, response):
    reset_timestamp = response.headers.get('x-rate-limit-reset')
    if reset_timestamp:
        wait_seconds = max(int(reset_timestamp) - int(time.time()), 0)
        return max(60, min(wait_seconds + 10, 900))  # 60秒〜15分
    return 300  # デフォルト5分
```

## エラーレスポンス完全マッピング
```python
# 永続的失敗（API呼び出し禁止）
PERMANENT_ERRORS = {
    "suspended": "アカウント凍結",
    "not_found": "ユーザー削除済み", 
    "deactivated": "アカウント無効化",
}

# 一時的失敗（リトライ対象）
TEMPORARY_ERRORS = {
    "unavailable": "一時的利用不可",
    429: "レート制限",
    500: "サーバーエラー",
    502: "Bad Gateway",
    503: "Service Unavailable",
}

# 認証エラー処理
def handle_auth_error(self):
    self._login_user_id = None
    self.cookie_manager.clear_cache()
    time.sleep(2)
    # 1回だけ再試行
```

## バッチ処理パターン（必須）
```python
# ✅ 推奨: バッチAPI使用
def get_users_batch(self, user_ids, batch_size=50):
    results = {}
    for i in range(0, len(user_ids), batch_size):
        batch = user_ids[i:i + batch_size]
        batch_results = self._fetch_users_batch(batch)
        results.update(batch_results)
        time.sleep(1)  # レート制限対策
    return results

# ❌ 避ける: 個別API呼び出し
def get_users_individually(self, user_ids):  # N+1問題
    for user_id in user_ids:
        self.get_user_info_by_id(user_id)
```

## キャッシュアクセスパターン
```python
# 段階的フォールバック戦略
def get_user_info_optimized(self, screen_name):
    # 1. フルキャッシュ確認
    if user_id := self._get_lookup_from_cache(screen_name):
        if combined := self._combine_profile_and_relationship(user_id):
            return combined
    
    # 2. 部分キャッシュ + 最小API
    if user_id:
        # 関係情報のみAPI取得
        relationships = self._fetch_relationships_only(user_id)
        profile = self._get_profile_from_cache(user_id)
        return self._combine_data(profile, relationships)
    
    # 3. フルAPI取得（最終手段）
    return self.get_user_info(screen_name)
```