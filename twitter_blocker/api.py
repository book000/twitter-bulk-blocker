"""
Twitter API アクセス管理モジュール
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from .config import CookieManager


class TwitterAPI:
    """Twitter API アクセス管理クラス"""

    BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

    # GraphQLエンドポイント
    USER_BY_SCREEN_NAME_ENDPOINT = (
        "https://x.com/i/api/graphql/7mjxD3-C6BxitPMVQ6w0-Q/UserByScreenName"
    )
    USER_BY_REST_ID_ENDPOINT = (
        "https://x.com/i/api/graphql/I5nvpI91ljifos1Y3Lltyg/UserByRestId"
    )
    USERS_BY_REST_IDS_ENDPOINT = (
        "https://x.com/i/api/graphql/lUdRvHzVPvdQQTmWVHYu6Q/UsersByRestIds"
    )

    # REST APIエンドポイント
    BLOCKS_CREATE_ENDPOINT = "https://x.com/i/api/1.1/blocks/create.json"

    def __init__(self, cookie_manager: CookieManager, cache_dir: str = "/data/cache"):
        self.cookie_manager = cookie_manager
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 新しいキャッシュ構造
        # lookups: screen_name -> user_id変換（全ユーザー共有）
        self.lookups_cache_dir = self.cache_dir / "lookups"
        self.lookups_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # relationships: ユーザー関係情報（ログインユーザー別）
        self.relationships_cache_dir = self.cache_dir / "relationships"
        self.relationships_cache_dir.mkdir(parents=True, exist_ok=True)
        
        # 従来キャッシュ（互換性のため）
        self.screen_name_cache_dir = self.cache_dir / "screen_name"
        self.user_id_cache_dir = self.cache_dir / "user_id"
        self.screen_name_cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_id_cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_ttl = 2592000  # 30日間（秒）
        self._login_user_id = None

    def _get_login_user_id(self) -> str:
        """ログインユーザーのIDを取得（キャッシュ用）"""
        if self._login_user_id is None:
            try:
                # Cookieからユーザー情報を取得してIDを特定
                cookies = self.cookie_manager.load_cookies()
                # Twitterのログインユーザー識別方法: twid cookieまたはpersonalization_id
                
                # Method 1: twid cookieから抽出
                twid = cookies.get('twid')
                if twid and twid.startswith('u%3D'):
                    # URLデコード: u%3D -> u=
                    import urllib.parse
                    decoded = urllib.parse.unquote(twid)
                    if decoded.startswith('u='):
                        user_id = decoded[2:].split('%')[0]  # u=123456789%...
                        self._login_user_id = user_id
                        return self._login_user_id
                
                # Method 2: personalization_idまたはguest_idを使用
                pid = cookies.get('personalization_id', cookies.get('guest_id', 'unknown'))
                # ハッシュ化してユニークなIDとして使用
                import hashlib
                self._login_user_id = hashlib.md5(pid.encode()).hexdigest()[:12]
                
            except Exception:
                # フォールバック: 固定ID
                self._login_user_id = "default_user"
        
        return self._login_user_id

    def get_user_info(self, screen_name: str) -> Optional[Dict[str, Any]]:
        """スクリーンネームからユーザー情報を取得"""
        # キャッシュから確認
        cached_result = self._get_from_cache("screen_name", screen_name)
        if cached_result is not None:
            print(f"[CACHE HIT] {screen_name}: キャッシュからユーザー情報を取得")
            return cached_result
        
        try:
            cookies = self.cookie_manager.load_cookies()
            headers = self._build_graphql_headers(cookies)

            params = {
                "variables": json.dumps(
                    {
                        "screen_name": screen_name,
                        "withSafetyModeUserFields": True,
                        "withSuperFollowsUserFields": True,
                    }
                ),
                "features": json.dumps(self._get_graphql_features()),
            }

            response = requests.get(
                self.USER_BY_SCREEN_NAME_ENDPOINT, headers=headers, params=params
            )

            # 詳細なエラー情報を記録
            self._log_response_details(response, screen_name, method_name="get_user_info")

            # レートリミット検出
            if response.status_code == 429:
                wait_seconds = self._calculate_wait_time(response)
                wait_minutes = wait_seconds / 60
                print(f"レートリミット検出 ({screen_name}): {wait_minutes:.1f}分間待機します")
                time.sleep(wait_seconds)
                # 1回だけリトライ
                response = requests.get(
                    self.USER_BY_SCREEN_NAME_ENDPOINT, headers=headers, params=params
                )
                self._log_response_details(response, screen_name, method_name="get_user_info_retry")

            # 認証エラー検出
            if response.status_code == 401:
                print(f"認証エラー検出 ({screen_name}): Cookieが無効です。処理を終了します")
                raise SystemExit("Authentication failed - Cookie is invalid")

            # アカウントロック検出
            if self._is_account_locked(response):
                print(f"アカウントロック検出 ({screen_name}): 処理を終了します")
                raise SystemExit("Account locked - terminating process")

            if response.status_code == 200:
                result = self._parse_user_response(response.json(), screen_name)
                # 成功時はキャッシュに保存
                if result is not None:
                    self._save_to_cache("screen_name", screen_name, result)
                return result

            # ステータスコード別のエラー表示
            error_msg = self._get_detailed_error_message(response, screen_name)
            print(f"ユーザー情報取得失敗 ({screen_name}): {error_msg}")
            return None

        except Exception as e:
            print(f"ユーザー情報取得エラー ({screen_name}): {e}")
            return None

    def get_user_info_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザーIDからユーザー情報を取得"""
        # キャッシュから確認
        cached_result = self._get_from_cache("user_id", user_id)
        if cached_result is not None:
            print(f"[CACHE HIT] ID:{user_id}: キャッシュからユーザー情報を取得")
            return cached_result
        
        try:
            cookies = self.cookie_manager.load_cookies()
            headers = self._build_graphql_headers(cookies)

            params = {
                "variables": json.dumps(
                    {
                        "userId": str(user_id),
                        "withSafetyModeUserFields": True,
                        "withSuperFollowsUserFields": True,
                    }
                ),
                "features": json.dumps(self._get_graphql_features()),
            }

            response = requests.get(
                self.USER_BY_REST_ID_ENDPOINT, headers=headers, params=params
            )

            # 詳細なエラー情報を記録
            self._log_response_details(response, user_id, method_name="get_user_info_by_id")

            # レートリミット検出
            if response.status_code == 429:
                wait_seconds = self._calculate_wait_time(response)
                wait_minutes = wait_seconds / 60
                print(f"レートリミット検出 (ID: {user_id}): {wait_minutes:.1f}分間待機します")
                time.sleep(wait_seconds)
                # 1回だけリトライ
                response = requests.get(
                    self.USER_BY_REST_ID_ENDPOINT, headers=headers, params=params
                )
                self._log_response_details(response, user_id, method_name="get_user_info_by_id_retry")

            # 認証エラー検出
            if response.status_code == 401:
                print(f"認証エラー検出 (ID: {user_id}): Cookieが無効です。処理を終了します")
                raise SystemExit("Authentication failed - Cookie is invalid")

            # アカウントロック検出
            if self._is_account_locked(response):
                print(f"アカウントロック検出 (ID: {user_id}): 処理を終了します")
                raise SystemExit("Account locked - terminating process")

            if response.status_code == 200:
                result = self._parse_user_response(response.json(), user_id=user_id)
                # 成功時はキャッシュに保存
                if result is not None:
                    self._save_to_cache("user_id", user_id, result)
                return result

            # ステータスコード別のエラー表示
            error_msg = self._get_detailed_error_message(response, user_id)
            print(f"ユーザー情報取得失敗 (ID: {user_id}): {error_msg}")
            return None

        except Exception as e:
            print(f"ユーザー情報取得エラー (ID: {user_id}): {e}")
            return None

    def get_users_info_by_screen_names_batch(self, screen_names: List[str], batch_size: int = 50) -> Dict[str, Dict[str, Any]]:
        """複数のscreen_nameから一括でユーザー情報を取得（2段階キャッシュ方式）"""
        results = {}
        
        # Step 1: screen_name -> user_id変換（共有キャッシュ）
        user_id_mappings = {}
        uncached_names = []
        
        for screen_name in screen_names:
            lookup_data = self._get_lookup_from_cache(screen_name)
            if lookup_data and lookup_data.get('user_id'):
                user_id_mappings[screen_name] = lookup_data['user_id']
                print(f"[LOOKUP CACHE HIT] {screen_name} -> {lookup_data['user_id']}")
            else:
                uncached_names.append(screen_name)
        
        # Step 2: 未キャッシュのscreen_nameのlookupを取得
        if uncached_names:
            print(f"[LOOKUP] {len(uncached_names)}件のscreen_name -> user_id変換を実行")
            for i in range(0, len(uncached_names), batch_size):
                batch_names = uncached_names[i:i + batch_size]
                batch_lookups = self._fetch_screen_name_lookups(batch_names)
                
                for screen_name, user_id in batch_lookups.items():
                    if user_id:
                        user_id_mappings[screen_name] = user_id
                        # lookupキャッシュに保存
                        self._save_lookup_to_cache(screen_name, user_id)
        
        # Step 3: user_idから関係情報を一括取得
        user_ids = list(user_id_mappings.values())
        if user_ids:
            relationships_data = self.get_users_info_batch(user_ids, batch_size)
            
            # screen_nameをキーとして結果を再構築
            for screen_name, user_id in user_id_mappings.items():
                relationship_info = relationships_data.get(user_id)
                if relationship_info:
                    # screen_nameを関係情報に追加
                    relationship_info['screen_name'] = screen_name
                    results[screen_name] = relationship_info
                else:
                    results[screen_name] = None
        
        # Step 4: 変換に失敗したscreen_nameをNoneとして記録
        for screen_name in screen_names:
            if screen_name not in results:
                results[screen_name] = None
        
        return results

    def get_users_info_batch(self, user_ids: List[str], batch_size: int = 50) -> Dict[str, Dict[str, Any]]:
        """複数ユーザーIDから一括でユーザー情報を取得"""
        results = {}
        
        # 関係情報キャッシュから取得済みのものをチェック（ログインユーザー別）
        uncached_ids = []
        for user_id in user_ids:
            cached_result = self._get_relationship_from_cache(user_id)
            if cached_result is not None:
                results[user_id] = cached_result
                print(f"[RELATIONSHIP CACHE HIT] ID:{user_id}: キャッシュからユーザー関係情報を取得")
            else:
                uncached_ids.append(user_id)
        
        if not uncached_ids:
            print(f"[BATCH] 全{len(user_ids)}ユーザーがキャッシュから取得済み")
            return results
        
        print(f"[BATCH] {len(uncached_ids)}/{len(user_ids)}ユーザーをAPI取得")
        
        # 未キャッシュのユーザーを一括取得
        for i in range(0, len(uncached_ids), batch_size):
            batch_ids = uncached_ids[i:i + batch_size]
            batch_results = self._fetch_users_batch(batch_ids)
            
            # 結果をマージし、関係情報キャッシュに保存
            for user_id, user_data in batch_results.items():
                results[user_id] = user_data
                if user_data:  # Noneでない場合のみキャッシュ
                    self._save_relationship_to_cache(user_id, user_data)
        
        return results

    def _fetch_users_batch(self, user_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """UsersByRestIds APIで一括ユーザー情報取得"""
        try:
            cookies = self.cookie_manager.load_cookies()
            headers = self._build_graphql_headers(cookies)

            params = {
                "variables": json.dumps({
                    "userIds": user_ids,
                    "withSafetyModeUserFields": True,
                    "withSuperFollowsUserFields": True,
                }),
                "features": json.dumps(self._get_graphql_features()),
            }

            response = requests.get(
                self.USERS_BY_REST_IDS_ENDPOINT, headers=headers, params=params
            )

            # 詳細なエラー情報を記録
            self._log_response_details(response, f"batch({len(user_ids)}users)", method_name="get_users_batch")

            # レートリミット検出
            if response.status_code == 429:
                wait_seconds = self._calculate_wait_time(response)
                wait_minutes = wait_seconds / 60
                print(f"レートリミット検出 (batch): {wait_minutes:.1f}分間待機します")
                time.sleep(wait_seconds)
                # 1回だけリトライ
                response = requests.get(
                    self.USERS_BY_REST_IDS_ENDPOINT, headers=headers, params=params
                )
                self._log_response_details(response, f"batch({len(user_ids)}users)", method_name="get_users_batch_retry")

            # 認証エラー検出
            if response.status_code == 401:
                print(f"認証エラー検出 (batch): Cookieが無効です。処理を終了します")
                raise SystemExit("Authentication failed - Cookie is invalid")

            # アカウントロック検出
            if self._is_account_locked(response):
                print(f"アカウントロック検出 (batch): 処理を終了します")
                raise SystemExit("Account locked - terminating process")

            if response.status_code == 200:
                return self._parse_users_batch_response(response.json(), user_ids)

            # ステータスコード別のエラー表示
            error_msg = self._get_detailed_error_message(response, f"batch({len(user_ids)}users)")
            print(f"一括ユーザー情報取得失敗: {error_msg}")
            
            # エラー時は空の辞書を返す（個別取得に自動フォールバック）
            return {user_id: None for user_id in user_ids}

        except Exception as e:
            print(f"一括ユーザー情報取得エラー: {e}")
            return {user_id: None for user_id in user_ids}

    def _parse_users_batch_response(self, data: Dict[str, Any], requested_ids: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """一括ユーザー情報レスポンスを解析"""
        results = {}
        
        if "data" in data and "users" in data["data"]:
            users_data = data["data"]["users"]
            
            for user_entry in users_data:
                if "result" in user_entry:
                    result = user_entry["result"]
                    
                    # 各ユーザーを個別の_parse_user_responseで処理
                    user_info = self._parse_single_user_from_batch(result)
                    
                    if user_info and user_info.get("id"):
                        results[user_info["id"]] = user_info
        
        # リクエストされたIDでレスポンスにないものはNoneとして記録
        for user_id in requested_ids:
            if user_id not in results:
                results[user_id] = None
        
        return results

    def _parse_single_user_from_batch(self, result: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """一括取得レスポンスから単一ユーザー情報を解析"""
        # ユーザーのTypeNameをチェック
        typename = result.get("__typename", "User")
        user_status = "active"

        if typename == "UserUnavailable":
            # ユーザーが利用不可
            user_status = "unavailable"
            if "reason" in result:
                user_status = result["reason"].lower()

            return {
                "id": result.get("rest_id"),
                "screen_name": None,
                "name": None,
                "user_status": user_status,
                "following": False,
                "followed_by": False,
                "blocking": False,
                "blocked_by": False,
                "protected": False,
                "unavailable": True,
            }

        if "legacy" in result:
            legacy = result["legacy"]

            return {
                "id": (
                    legacy.get("id_str") or result.get("rest_id")
                ),
                "screen_name": legacy.get("screen_name"),
                "name": legacy.get("name"),
                "user_status": user_status,
                "following": legacy.get("following", False),
                "followed_by": legacy.get("followed_by", False),
                "blocking": legacy.get("blocking", False),
                "blocked_by": legacy.get("blocked_by", False),
                "protected": legacy.get("protected", False),
                "unavailable": False,
            }

        return None

    def _fetch_screen_names_batch(self, screen_names: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
        """複数のscreen_nameを並行して取得（個別APIの並行実行）"""
        results = {}
        
        # 並行処理の代わりに、レート制限を考慮した順次処理を実装
        for screen_name in screen_names:
            try:
                user_info = self._fetch_single_screen_name(screen_name)
                results[screen_name] = user_info
                
                # 短い間隔で待機（レート制限対策）
                if len(screen_names) > 1:
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"  ✗ {screen_name}: 取得エラー - {e}")
                results[screen_name] = None
        
        return results

    def _fetch_screen_name_lookups(self, screen_names: List[str]) -> Dict[str, Optional[str]]:
        """複数のscreen_nameからuser_idを取得（lookup専用）"""
        results = {}
        
        for screen_name in screen_names:
            try:
                user_info = self._fetch_single_screen_name_lookup(screen_name)
                results[screen_name] = user_info.get('id') if user_info else None
                
                # 短い間隔で待機（レート制限対策）
                if len(screen_names) > 1:
                    time.sleep(0.1)
                    
            except Exception as e:
                print(f"  ✗ {screen_name}: lookup失敗 - {e}")
                results[screen_name] = None
        
        return results

    def _fetch_single_screen_name_lookup(self, screen_name: str) -> Optional[Dict[str, Any]]:
        """単一のscreen_nameからuser_idを取得（lookup専用・関係情報なし）"""
        try:
            cookies = self.cookie_manager.load_cookies()
            headers = self._build_graphql_headers(cookies)

            params = {
                "variables": json.dumps({
                    "screen_name": screen_name,
                    "withSafetyModeUserFields": False,  # 関係情報不要
                    "withSuperFollowsUserFields": False,  # 関係情報不要
                }),
                "features": json.dumps(self._get_graphql_features()),
            }

            response = requests.get(
                self.USER_BY_SCREEN_NAME_ENDPOINT, headers=headers, params=params
            )

            # 基本的なエラーハンドリングのみ
            if response.status_code == 429:
                wait_seconds = self._calculate_wait_time(response)
                print(f"  レートリミット検出 ({screen_name}): {wait_seconds/60:.1f}分間待機")
                time.sleep(wait_seconds)
                response = requests.get(
                    self.USER_BY_SCREEN_NAME_ENDPOINT, headers=headers, params=params
                )

            if response.status_code == 401:
                raise SystemExit("Authentication failed - Cookie is invalid")

            if self._is_account_locked(response):
                raise SystemExit("Account locked - terminating process")

            if response.status_code == 200:
                # 基本情報のみ解析（関係情報なし）
                return self._parse_lookup_response(response.json(), screen_name)

            return None

        except Exception as e:
            print(f"  ✗ {screen_name}: lookup取得エラー - {e}")
            return None

    def _parse_lookup_response(self, data: Dict[str, Any], screen_name: str) -> Optional[Dict[str, Any]]:
        """lookup専用レスポンス解析（IDと基本情報のみ）"""
        if (
            "data" in data
            and "user" in data["data"]
            and "result" in data["data"]["user"]
        ):
            result = data["data"]["user"]["result"]
            
            if "legacy" in result:
                legacy = result["legacy"]
                return {
                    "id": legacy.get("id_str") or result.get("rest_id"),
                    "screen_name": legacy.get("screen_name") or screen_name,
                    "name": legacy.get("name"),
                }
        return None

    def _fetch_single_screen_name(self, screen_name: str) -> Optional[Dict[str, Any]]:
        """単一のscreen_nameを取得（get_user_infoの軽量版）"""
        try:
            cookies = self.cookie_manager.load_cookies()
            headers = self._build_graphql_headers(cookies)

            params = {
                "variables": json.dumps({
                    "screen_name": screen_name,
                    "withSafetyModeUserFields": True,
                    "withSuperFollowsUserFields": True,
                }),
                "features": json.dumps(self._get_graphql_features()),
            }

            response = requests.get(
                self.USER_BY_SCREEN_NAME_ENDPOINT, headers=headers, params=params
            )

            # レートリミット検出（基本チェックのみ）
            if response.status_code == 429:
                wait_seconds = self._calculate_wait_time(response)
                wait_minutes = wait_seconds / 60
                print(f"  レートリミット検出 ({screen_name}): {wait_minutes:.1f}分間待機します")
                time.sleep(wait_seconds)
                
                # 1回だけリトライ
                response = requests.get(
                    self.USER_BY_SCREEN_NAME_ENDPOINT, headers=headers, params=params
                )

            # 認証エラー検出
            if response.status_code == 401:
                print(f"  認証エラー検出 ({screen_name}): Cookieが無効です。処理を終了します")
                raise SystemExit("Authentication failed - Cookie is invalid")

            # アカウントロック検出
            if self._is_account_locked(response):
                print(f"  アカウントロック検出 ({screen_name}): 処理を終了します")
                raise SystemExit("Account locked - terminating process")

            if response.status_code == 200:
                return self._parse_user_response(response.json(), screen_name)

            # エラーの場合
            error_msg = self._get_detailed_error_message(response, screen_name)
            print(f"  ✗ {screen_name}: {error_msg}")
            return None

        except Exception as e:
            print(f"  ✗ {screen_name}: 取得エラー - {e}")
            return None

    def block_user(self, user_id: str, screen_name: str) -> Dict[str, Any]:
        """REST APIでユーザーをブロック"""
        try:
            cookies = self.cookie_manager.load_cookies()
            headers = self._build_rest_headers(cookies)

            data = {"user_id": user_id}

            response = requests.post(
                self.BLOCKS_CREATE_ENDPOINT, headers=headers, data=data
            )

            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_data": (
                    response.json() if response.status_code == 200 else None
                ),
                "error_message": response.text if response.status_code != 200 else None,
            }

        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "response_data": None,
                "error_message": str(e),
            }

    def _build_graphql_headers(self, cookies: Dict[str, str]) -> Dict[str, str]:
        """GraphQL APIリクエスト用ヘッダーを構築"""
        cookie_str = "; ".join([f"{name}={value}" for name, value in cookies.items()])

        return {
            "authorization": f"Bearer {self.BEARER_TOKEN}",
            "x-csrf-token": cookies.get("ct0", ""),
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-active-user": "yes",
            "content-type": "application/json",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
            "accept": "*/*",
            "accept-language": "ja,en-US;q=0.7,en;q=0.3",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "dnt": "1",
            "cookie": cookie_str,
        }

    def _build_rest_headers(self, cookies: Dict[str, str]) -> Dict[str, str]:
        """REST APIリクエスト用ヘッダーを構築"""
        cookie_str = "; ".join([f"{name}={value}" for name, value in cookies.items()])

        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:139.0) Gecko/20100101 Firefox/139.0",
            "Accept": "*/*",
            "Accept-Language": "ja,en-US;q=0.7,en;q=0.3",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Content-Type": "application/x-www-form-urlencoded",
            "Referer": "https://x.com/home",
            "x-twitter-auth-type": "OAuth2Session",
            "x-csrf-token": cookies.get("ct0", ""),
            "x-twitter-client-language": "ja",
            "x-twitter-active-user": "yes",
            "Origin": "https://x.com",
            "DNT": "1",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "authorization": f"Bearer {self.BEARER_TOKEN}",
            "Connection": "keep-alive",
            "Cookie": cookie_str,
        }

    def _get_graphql_features(self) -> Dict[str, bool]:
        """GraphQL機能フラグを取得"""
        return {
            "hidden_profile_likes_enabled": True,
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "subscriptions_verification_info_is_identity_verified_enabled": True,
            "subscriptions_verification_info_verified_since_enabled": True,
            "highlights_tweets_tab_ui_enabled": True,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "responsive_web_graphql_timeline_navigation_enabled": True,
        }

    def _parse_user_response(
        self,
        data: Dict[str, Any],
        screen_name: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """ユーザー情報レスポンスを解析"""
        if (
            "data" in data
            and "user" in data["data"]
            and "result" in data["data"]["user"]
        ):
            result = data["data"]["user"]["result"]

            # ユーザーのTypeNameをチェック
            typename = result.get("__typename", "User")
            user_status = "active"

            if typename == "UserUnavailable":
                # ユーザーが利用不可
                user_status = "unavailable"
                if "reason" in result:
                    user_status = result["reason"].lower()

                return {
                    "id": result.get("rest_id") or str(user_id) if user_id else None,
                    "screen_name": screen_name,
                    "name": None,
                    "user_status": user_status,
                    "following": False,
                    "followed_by": False,
                    "blocking": False,
                    "blocked_by": False,
                    "protected": False,
                    "unavailable": True,
                }

            if "legacy" in result:
                legacy = result["legacy"]

                return {
                    "id": (
                        legacy.get("id_str") or result.get("rest_id") or 
                        (str(user_id) if user_id else None)
                    ),
                    "screen_name": legacy.get("screen_name") or screen_name,
                    "name": legacy.get("name"),
                    "user_status": user_status,
                    "following": legacy.get("following", False),
                    "followed_by": legacy.get("followed_by", False),
                    "blocking": legacy.get("blocking", False),
                    "blocked_by": legacy.get("blocked_by", False),
                    "protected": legacy.get("protected", False),
                    "unavailable": False,
                }

        elif "errors" in data:
            # GraphQLエラーの場合
            errors = data["errors"]
            for error in errors:
                if "User not found" in error.get("message", ""):
                    return {
                        "id": str(user_id) if user_id else None,
                        "screen_name": screen_name,
                        "name": None,
                        "user_status": "not_found",
                        "following": False,
                        "followed_by": False,
                        "blocking": False,
                        "blocked_by": False,
                        "protected": False,
                        "unavailable": True,
                    }

        return None

    def _log_response_details(self, response: requests.Response, identifier: str, method_name: str) -> None:
        """レスポンス詳細をログ出力"""
        print(f"[{method_name}] {identifier}: HTTP {response.status_code}")
        
        # ヘッダー情報（レート制限関連）
        if hasattr(response, 'headers'):
            rate_limit_remaining = response.headers.get('x-rate-limit-remaining')
            rate_limit_reset = response.headers.get('x-rate-limit-reset')
        else:
            rate_limit_remaining = None
            rate_limit_reset = None
        
        if rate_limit_remaining is not None:
            print(f"  レート制限残り: {rate_limit_remaining}")
        if rate_limit_reset is not None:
            # UNIXタイムスタンプをAsia/Tokyoタイムゾーンで表示
            try:
                reset_timestamp = int(rate_limit_reset)
                reset_datetime = datetime.fromtimestamp(reset_timestamp, tz=ZoneInfo("Asia/Tokyo"))
                formatted_time = reset_datetime.strftime("%Y-%m-%d %H:%M:%S JST")
                print(f"  レート制限リセット: {rate_limit_reset} ({formatted_time})")
            except (ValueError, TypeError):
                print(f"  レート制限リセット: {rate_limit_reset}")

        # エラー時の詳細情報
        if hasattr(response, 'status_code') and response.status_code >= 400:
            try:
                error_data = response.json()
                if 'errors' in error_data:
                    for error in error_data['errors']:
                        print(f"  エラー詳細: {error.get('message', 'Unknown error')}")
            except:
                if hasattr(response, 'text'):
                    print(f"  レスポンステキスト: {response.text[:200]}")
                else:
                    print(f"  レスポンス詳細取得不可")

    def _get_detailed_error_message(self, response: requests.Response, identifier: str) -> str:
        """詳細なエラーメッセージを生成"""
        status_messages = {
            400: "不正なリクエスト",
            401: "認証エラー（Cookieが無効）",
            403: "アクセス拒否（アカウント制限の可能性）",
            404: "ユーザーが見つからない",
            429: "レートリミット（API制限）",
            500: "サーバー内部エラー",
            502: "Bad Gateway",
            503: "サービス利用不可",
            504: "Gateway Timeout"
        }
        
        base_msg = status_messages.get(response.status_code, f"HTTP {response.status_code}")
        
        # JSONレスポンスからエラー詳細を取得
        try:
            if hasattr(response, 'json'):
                error_data = response.json()
                if 'errors' in error_data and error_data['errors']:
                    error_details = ', '.join([error.get('message', '') for error in error_data['errors']])
                    return f"{base_msg} - {error_details}"
        except:
            pass
            
        return base_msg

    def _is_account_locked(self, response: requests.Response) -> bool:
        """アカウントロック状態を検出"""
        # HTTP 403 + 特定のエラーメッセージでアカウントロックを判定
        if hasattr(response, 'status_code') and response.status_code == 403:
            try:
                if hasattr(response, 'json'):
                    error_data = response.json()
                    if 'errors' in error_data:
                        for error in error_data['errors']:
                            error_msg = error.get('message', '').lower()
                            if any(keyword in error_msg for keyword in [
                                'account locked', 'account suspended', 'your account',
                                'temporarily locked', 'restricted'
                            ]):
                                return True
            except:
                pass
        return False

    def _calculate_wait_time(self, response: requests.Response, buffer_seconds: int = 60) -> int:
        """レートリミットリセット時刻に基づいて適切な待機時間を計算"""
        # x-rate-limit-resetヘッダーからリセット時刻を取得
        if hasattr(response, 'headers'):
            rate_limit_reset = response.headers.get('x-rate-limit-reset')
            if rate_limit_reset:
                try:
                    reset_timestamp = int(rate_limit_reset)
                    current_timestamp = int(time.time())
                    
                    # リセット時刻まての時間を計算
                    wait_seconds = reset_timestamp - current_timestamp
                    
                    # バッファ時間を追加（デフォルト60秒）
                    wait_seconds += buffer_seconds
                    
                    # 最小待機時間は60秒、最大は30分に制限
                    wait_seconds = max(60, min(wait_seconds, 1800))
                    
                    print(f"  計算された待機時間: {wait_seconds}秒 (リセット時刻+{buffer_seconds}秒)")
                    return wait_seconds
                    
                except (ValueError, TypeError):
                    pass
        
        # ヘッダーが取得できない場合はデフォルトの15分
        print("  リセット時刻取得失敗: デフォルト15分待機")
        return 900

    def _get_cache_file_path(self, cache_type: str, identifier: str) -> Path:
        """キャッシュファイルのパスを取得"""
        # ファイル名に使えない文字をサニタイズ
        safe_identifier = "".join(c for c in identifier if c.isalnum() or c in "._-")
        
        if cache_type == "screen_name":
            return self.screen_name_cache_dir / f"{safe_identifier}.json"
        elif cache_type == "user_id":
            return self.user_id_cache_dir / f"{safe_identifier}.json"
        else:
            raise ValueError(f"Unsupported cache type: {cache_type}")

    def _get_from_cache(self, cache_type: str, identifier: str) -> Optional[Dict[str, Any]]:
        """キャッシュからユーザー情報を取得"""
        cache_file = self._get_cache_file_path(cache_type, identifier)
        
        try:
            if cache_file.exists():
                # ファイル更新時刻をTTLチェックに使用
                file_mtime = cache_file.stat().st_mtime
                current_time = time.time()
                
                # TTL期限内かチェック
                if current_time - file_mtime < self.cache_ttl:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    # 期限切れのファイルを削除
                    cache_file.unlink()
                    print(f"[CACHE EXPIRED] {cache_type}:{identifier}: キャッシュが期限切れです")
        except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
            # 破損ファイルや読み取りエラーの場合は削除
            if cache_file.exists():
                try:
                    cache_file.unlink()
                except:
                    pass
        
        return None

    def _save_to_cache(self, cache_type: str, identifier: str, user_data: Dict[str, Any]) -> None:
        """ユーザー情報をキャッシュに保存"""
        cache_file = self._get_cache_file_path(cache_type, identifier)
        
        try:
            # ディレクトリが存在しない場合は作成
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, ensure_ascii=False, indent=2)
            print(f"[CACHE SAVE] {cache_type}:{identifier}: ユーザー情報をキャッシュに保存")
        except Exception as e:
            print(f"キャッシュ保存エラー ({cache_type}:{identifier}): {e}")

    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        try:
            deleted_count = 0
            
            # screen_nameキャッシュをクリア
            for cache_file in self.screen_name_cache_dir.glob("*.json"):
                cache_file.unlink()
                deleted_count += 1
            
            # user_idキャッシュをクリア
            for cache_file in self.user_id_cache_dir.glob("*.json"):
                cache_file.unlink()
                deleted_count += 1
            
            print(f"キャッシュファイルを削除しました ({deleted_count}ファイル)")
        except Exception as e:
            print(f"キャッシュ削除エラー: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計情報を取得"""
        current_time = time.time()
        
        total_entries = 0
        valid_entries = 0
        expired_entries = 0
        
        # screen_nameキャッシュを確認
        for cache_file in self.screen_name_cache_dir.glob("*.json"):
            total_entries += 1
            try:
                file_mtime = cache_file.stat().st_mtime
                if current_time - file_mtime < self.cache_ttl:
                    valid_entries += 1
                else:
                    expired_entries += 1
            except:
                expired_entries += 1
        
        # user_idキャッシュを確認
        for cache_file in self.user_id_cache_dir.glob("*.json"):
            total_entries += 1
            try:
                file_mtime = cache_file.stat().st_mtime
                if current_time - file_mtime < self.cache_ttl:
                    valid_entries += 1
                else:
                    expired_entries += 1
            except:
                expired_entries += 1
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_dirs": {
                "screen_name": str(self.screen_name_cache_dir),
                "user_id": str(self.user_id_cache_dir)
            },
            "cache_ttl_days": self.cache_ttl / 86400
        }

    def _get_lookup_from_cache(self, screen_name: str) -> Optional[Dict[str, Any]]:
        """lookupキャッシュから取得（screen_name -> user_id変換用）"""
        safe_screen_name = "".join(c for c in screen_name if c.isalnum() or c in "._-")
        cache_file = self.lookups_cache_dir / f"{safe_screen_name}.json"
        
        try:
            if cache_file.exists():
                file_mtime = cache_file.stat().st_mtime
                current_time = time.time()
                
                if current_time - file_mtime < self.cache_ttl:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    cache_file.unlink()
        except Exception:
            if cache_file.exists():
                try:
                    cache_file.unlink()
                except:
                    pass
        
        return None

    def _save_lookup_to_cache(self, screen_name: str, user_id: str) -> None:
        """lookupキャッシュに保存（screen_name -> user_id変換用）"""
        safe_screen_name = "".join(c for c in screen_name if c.isalnum() or c in "._-")
        cache_file = self.lookups_cache_dir / f"{safe_screen_name}.json"
        
        try:
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            
            lookup_data = {
                "screen_name": screen_name,
                "user_id": user_id,
                "cached_at": time.time()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(lookup_data, f, ensure_ascii=False, indent=2)
            print(f"[LOOKUP CACHE SAVE] {screen_name} -> {user_id}")
        except Exception as e:
            print(f"lookupキャッシュ保存エラー ({screen_name}): {e}")

    def _get_relationship_from_cache(self, user_id: str) -> Optional[Dict[str, Any]]:
        """関係情報キャッシュから取得（ログインユーザー別）"""
        login_user_id = self._get_login_user_id()
        user_cache_dir = self.relationships_cache_dir / login_user_id
        
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in "._-")
        cache_file = user_cache_dir / f"{safe_user_id}.json"
        
        try:
            if cache_file.exists():
                file_mtime = cache_file.stat().st_mtime
                current_time = time.time()
                
                if current_time - file_mtime < self.cache_ttl:
                    with open(cache_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                else:
                    cache_file.unlink()
        except Exception:
            if cache_file.exists():
                try:
                    cache_file.unlink()
                except:
                    pass
        
        return None

    def _save_relationship_to_cache(self, user_id: str, user_data: Dict[str, Any]) -> None:
        """関係情報キャッシュに保存（ログインユーザー別）"""
        login_user_id = self._get_login_user_id()
        user_cache_dir = self.relationships_cache_dir / login_user_id
        user_cache_dir.mkdir(parents=True, exist_ok=True)
        
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in "._-")
        cache_file = user_cache_dir / f"{safe_user_id}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(user_data, f, ensure_ascii=False, indent=2)
            print(f"[RELATIONSHIP CACHE SAVE] {login_user_id}/ID:{user_id}: ユーザー関係情報をキャッシュに保存")
        except Exception as e:
            print(f"関係情報キャッシュ保存エラー ({user_id}): {e}")
