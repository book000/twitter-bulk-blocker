"""
Twitter API アクセス管理モジュール
"""

import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytz
import requests

from .config import CookieManager


class HeaderEnhancer:
    """Twitter API用の拡張ヘッダー生成クラス"""
    
    def __init__(self, enable_forwarded_for: bool = False):
        """
        拡張ヘッダー生成機能を初期化
        
        Args:
            enable_forwarded_for: x-xp-forwarded-forヘッダーの生成を有効にするか
        """
        self.enable_forwarded_for = enable_forwarded_for
        self._transaction_counter = random.randint(1000, 9999)
        self._session_ip = self._generate_session_ip() if enable_forwarded_for else None
        
    def get_transaction_id(self) -> str:
        """
        動的なtransaction ID生成（リクエスト毎にインクリメント）
        
        Returns:
            一意のtransaction ID文字列
        """
        self._transaction_counter += 1
        return str(self._transaction_counter)
    
    def get_forwarded_for(self) -> Optional[str]:
        """
        セッション固定IPの取得
        
        Returns:
            生成されたIPアドレス文字列、または無効時はNone
        """
        return self._session_ip if self.enable_forwarded_for else None
    
    def _generate_session_ip(self) -> str:
        """
        適切なIP範囲からランダムIPを生成（セッション中は固定）
        
        Returns:
            日本のISP範囲を模倣したIPアドレス
        """
        # 日本の主要ISP範囲を模倣
        ip_ranges = [
            (126, 0, 0, 1, 126, 255, 255, 254),      # NTT Communications
            (202, 32, 0, 1, 202, 47, 255, 254),      # KDDI
            (210, 128, 0, 1, 210, 255, 255, 254),    # SoftBank
            (219, 96, 0, 1, 219, 127, 255, 254),     # IIJ
            (61, 192, 0, 1, 61, 207, 255, 254),      # So-net
        ]
        
        start_a, start_b, start_c, start_d, end_a, end_b, end_c, end_d = random.choice(ip_ranges)
        
        a = random.randint(start_a, end_a)
        b = random.randint(start_b, end_b)
        c = random.randint(start_c, end_c)
        d = random.randint(start_d, end_d)
        
        return f"{a}.{b}.{c}.{d}"
    
    def get_enhanced_headers(self) -> Dict[str, str]:
        """
        拡張ヘッダーの辞書を取得
        
        Returns:
            拡張ヘッダーの辞書
        """
        headers = {
            "x-client-transaction-id": self.get_transaction_id()
        }
        
        forwarded_for = self.get_forwarded_for()
        if forwarded_for:
            headers["x-xp-forwarded-for"] = forwarded_for
            
        return headers


class TwitterAPI:
    """Twitter API操作を管理するクラス"""

    # GraphQL APIエンドポイント
    USER_BY_SCREEN_NAME_ENDPOINT = (
        "https://x.com/i/api/graphql/qW5u-DAuXpMEG0zA1F7UGQ/UserByScreenName"
    )
    USER_BY_REST_ID_ENDPOINT = (
        "https://x.com/i/api/graphql/I5nvpI91ljifos1Y3Lltyg/UserByRestId"
    )
    USERS_BY_REST_IDS_ENDPOINT = (
        "https://x.com/i/api/graphql/OXBEDLUtUvKvNEP1RKRbuQ/UsersByRestIds"
    )
    CREATE_TWEET_ENDPOINT = (
        "https://x.com/i/api/graphql/a1p9RWpkYKBjWv_I3WzS-A/CreateTweet"
    )

    # REST APIエンドポイント
    BLOCKS_CREATE_ENDPOINT = "https://x.com/i/api/1.1/blocks/create.json"

    def __init__(self, cookie_manager: CookieManager, cache_dir: str = "/data/cache", 
                 debug_mode: bool = False, enable_header_enhancement: bool = True,
                 enable_forwarded_for: bool = False):
        self.cookie_manager = cookie_manager
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.debug_mode = debug_mode
        self.enable_header_enhancement = enable_header_enhancement
        
        # ヘッダー拡張機能の初期化
        if enable_header_enhancement:
            self.header_enhancer = HeaderEnhancer(enable_forwarded_for=enable_forwarded_for)
            if debug_mode:
                print(f"🔧 Header enhancement enabled (forwarded_for: {enable_forwarded_for})")
        else:
            self.header_enhancer = None
            if debug_mode:
                print("🔧 Header enhancement disabled")
        
        # キャッシュ構造
        self.lookups_cache_dir = self.cache_dir / "lookups"  # screen_name -> user_id マッピング用（共有）
        self.profiles_cache_dir = self.cache_dir / "profiles"  # 基本ユーザー情報（共有）
        self.relationships_cache_dir = self.cache_dir / "relationships"  # 関係情報（ログインユーザー別）
        
        self.lookups_cache_dir.mkdir(parents=True, exist_ok=True)
        self.profiles_cache_dir.mkdir(parents=True, exist_ok=True)
        self.relationships_cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.cache_ttl = 2592000  # 30日間（秒）
        self._login_user_id = None  # ログインユーザーIDのキャッシュ
        self._auth_retry_count = 0  # 認証エラー時の再試行カウント
        self._max_auth_retries = 1  # 最大認証再試行回数


    def get_user_info(self, screen_name: str) -> Optional[Dict[str, Any]]:
        """スクリーンネームからユーザー情報を取得"""
        # 新しいキャッシュシステムで確認
        # 1. lookupキャッシュからuser_idを取得
        user_id = self._get_lookup_from_cache(screen_name)
        if user_id:
            # 2. 結合されたデータを取得
            cached_result = self._combine_profile_and_relationship(user_id)
            if cached_result:
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
                return self._handle_auth_error(screen_name, "get_user_info", 
                                               lambda: self.get_user_info(screen_name))

            # アカウントロック検出
            if self._is_account_locked(response):
                print(f"アカウントロック検出 ({screen_name}): 処理を終了します")
                raise SystemExit("Account locked - terminating process")

            if response.status_code == 200:
                result = self._parse_user_response(response.json(), screen_name)
                # 成功時は新しいキャッシュシステムに保存
                if result is not None and result.get("id"):
                    # lookupキャッシュにscreen_name -> user_idマッピングを保存
                    self._save_lookup_to_cache(screen_name, result["id"])
                    # プロフィールキャッシュに基本情報を保存
                    self._save_profile_to_cache(result["id"], result)
                    # 関係情報キャッシュに関係データを保存
                    self._save_relationship_to_cache(result["id"], result)
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
        # 新しいキャッシュシステムで確認
        cached_result = self._combine_profile_and_relationship(user_id)
        if cached_result is not None:
            print(f"[CACHE HIT] ID:{user_id}: キャッシュからユーザー情報を取得")
            return cached_result
        
        try:
            cookies = self.cookie_manager.load_cookies()
            headers = self._build_graphql_headers(cookies)

            params = {
                "variables": json.dumps(
                    {
                        "userId": user_id,
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
                return self._handle_auth_error(user_id, "get_user_info_by_id", 
                                               lambda: self.get_user_info_by_id(user_id))

            # アカウントロック検出
            if self._is_account_locked(response):
                print(f"アカウントロック検出 (ID: {user_id}): 処理を終了します")
                raise SystemExit("Account locked - terminating process")

            if response.status_code == 200:
                result = self._parse_user_response(response.json(), user_id)
                # 成功時は新しいキャッシュシステムに保存
                if result is not None and result.get("id"):
                    # プロフィールキャッシュに基本情報を保存
                    self._save_profile_to_cache(result["id"], result)
                    # 関係情報キャッシュに関係データを保存
                    self._save_relationship_to_cache(result["id"], result)
                return result

            # ステータスコード別のエラー表示
            error_msg = self._get_detailed_error_message(response, user_id)
            print(f"ユーザー情報取得失敗 (ID: {user_id}): {error_msg}")
            return None

        except Exception as e:
            print(f"ユーザー情報取得エラー (ID: {user_id}): {e}")
            return None

    def get_users_info_by_screen_names(self, screen_names: List[str], batch_size: int = 50) -> Dict[str, Dict[str, Any]]:
        """複数のscreen_nameからユーザー情報を取得（2段階処理）"""
        results = {}
        
        # Step 1: screen_name毎に処理を決定
        need_relationship_fetch = []  # (screen_name, user_id)のタプルのリスト
        
        for screen_name in screen_names:
            # lookupキャッシュから確認
            lookup_data = self._get_lookup_from_cache(screen_name)
            
            if lookup_data and lookup_data.get('user_id'):
                # キャッシュからuser_idを取得した場合
                user_id = lookup_data['user_id']
                print(f"[LOOKUP CACHE HIT] {screen_name} -> {user_id}")
                
                # プロフィール + 関係情報の結合を試行
                combined_data = self._combine_profile_and_relationship(user_id)
                if combined_data:
                    combined_data['screen_name'] = screen_name  # screen_nameを追加
                    results[screen_name] = combined_data
                    print(f"[COMBINED CACHE HIT] {screen_name} (ID: {user_id})")
                else:
                    # 関係情報の取得が必要
                    need_relationship_fetch.append((screen_name, user_id))
            else:
                # APIからUserByScreenNameを取得（関係情報込み）
                user_info = self.get_user_info(screen_name)
                if user_info:
                    results[screen_name] = user_info
                    # 各キャッシュに保存
                    if user_info.get('id'):
                        self._save_lookup_to_cache(screen_name, user_info['id'])
                        self._save_profile_to_cache(user_info['id'], user_info)
                        self._save_relationship_to_cache(user_info['id'], user_info)
                else:
                    results[screen_name] = None
        
        # Step 2: 関係情報が必要なユーザーをバッチ取得
        if need_relationship_fetch:
            print(f"\n[RELATIONSHIP BATCH] {len(need_relationship_fetch)}件の関係情報をバッチ取得")
            user_ids = [user_id for _, user_id in need_relationship_fetch]
            
            # バッチ処理
            for i in range(0, len(user_ids), batch_size):
                batch_ids = user_ids[i:i + batch_size]
                batch_results = self._fetch_users_batch(batch_ids)
                
                # 結果をscreen_nameベースで格納
                for screen_name, user_id in need_relationship_fetch:
                    if user_id in batch_ids:
                        user_data = batch_results.get(user_id)
                        if user_data:
                            user_data['screen_name'] = screen_name  # screen_nameを追加
                            results[screen_name] = user_data
                            # 両方のキャッシュに保存
                            self._save_profile_to_cache(user_id, user_data)
                            self._save_relationship_to_cache(user_id, user_data)
                        else:
                            results[screen_name] = None
        
        return results

    def get_users_info_batch(self, user_ids: List[str], batch_size: int = 50) -> Dict[str, Dict[str, Any]]:
        """複数ユーザーIDから一括でユーザー情報を取得"""
        results = {}
        
        # 結合キャッシュから取得済みのものをチェック
        uncached_ids = []
        for user_id in user_ids:
            combined_result = self._combine_profile_and_relationship(user_id)
            if combined_result is not None:
                results[user_id] = combined_result
                print(f"[COMBINED CACHE HIT] ID:{user_id}: キャッシュからユーザー情報を取得")
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
            
            # 結果をマージし、キャッシュに保存
            for user_id, user_data in batch_results.items():
                results[user_id] = user_data
                if user_data:  # Noneでない場合のみキャッシュ
                    self._save_profile_to_cache(user_id, user_data)
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
                return self._handle_auth_error(f"batch({len(user_ids)}users)", "get_users_batch", 
                                               lambda: self._fetch_users_batch(user_ids))

            # アカウントロック検出
            if self._is_account_locked(response):
                print(f"アカウントロック検出 (batch): 処理を終了します")
                raise SystemExit("Account locked - terminating process")

            if response.status_code == 200:
                return self._parse_users_batch_response(response.json(), user_ids)

            # ステータスコード別のエラー表示
            error_msg = self._get_detailed_error_message(response, f"batch({len(user_ids)}users)")
            print(f"一括ユーザー情報取得失敗: {error_msg}")
            
            # エラー時は空の辞書を返す
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
            
            # フォロー関係の取得
            following = legacy.get("following", False)
            # SuperFollowsを考慮
            if not following and "super_following" in legacy:
                following = legacy.get("super_following", False)

            return {
                "id": result.get("rest_id"),
                "screen_name": legacy.get("screen_name"),
                "name": legacy.get("name"),
                "user_status": user_status,
                "following": following,
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
                return self._handle_auth_error(screen_name, "_fetch_single_screen_name_lookup", 
                                               lambda: self._fetch_single_screen_name_lookup(screen_name))

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
                return self._handle_auth_error(screen_name, "_fetch_single_screen_name", 
                                               lambda: self._fetch_single_screen_name(screen_name))

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

            # レートリミット検出
            if response.status_code == 429:
                wait_seconds = self._calculate_wait_time(response)
                wait_minutes = wait_seconds / 60
                print(f"レートリミット検出 (block): {wait_minutes:.1f}分間待機します")
                time.sleep(wait_seconds)
                # 1回だけリトライ
                response = requests.post(
                    self.BLOCKS_CREATE_ENDPOINT, headers=headers, data=data
                )

            # 認証エラー検出
            if response.status_code == 401:
                return self._handle_auth_error(f"block {screen_name}", "block_user", 
                                               lambda: self.block_user(user_id, screen_name))

            # アカウントロック検出
            if self._is_account_locked(response):
                print(f"アカウントロック検出 (block): 処理を終了します")
                raise SystemExit("Account locked - terminating process")

            if response.status_code == 200:
                return {"success": True, "status_code": 200}

            # その他のエラー
            error_msg = self._get_detailed_error_message(response, f"block {screen_name}")
            return {
                "success": False,
                "status_code": response.status_code,
                "message": error_msg,
            }

        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "message": f"ブロック処理エラー: {e}",
            }

    def _calculate_wait_time(self, response: requests.Response) -> int:
        """レートリミット時の待機時間を動的に計算"""
        # レートリミットヘッダーから情報を取得
        reset_timestamp = response.headers.get('x-rate-limit-reset')
        
        if reset_timestamp:
            try:
                # リセット時刻（UNIX timestamp）
                reset_time = int(reset_timestamp)
                # 現在時刻（UNIX timestamp）
                current_time = int(time.time())
                # 待機時間を計算（秒）
                wait_seconds = max(reset_time - current_time, 0)
                
                # リセット時刻を人間が読める形式で表示（Asia/Tokyoタイムゾーン）
                tokyo_tz = pytz.timezone('Asia/Tokyo')
                reset_datetime = datetime.fromtimestamp(reset_time, tz=tokyo_tz)
                formatted_time = reset_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')
                
                print(f"  レートリミットリセット時刻: {formatted_time}")
                print(f"  待機時間: {wait_seconds}秒 ({wait_seconds/60:.1f}分)")
                
                # 最低でも60秒、最大で15分の待機
                return max(60, min(wait_seconds + 10, 900))  # 10秒の余裕を追加
            except (ValueError, TypeError):
                pass
        
        # ヘッダーから取得できない場合のデフォルト値
        print("  レートリミット情報を取得できませんでした。デフォルトの待機時間を使用します")
        return 300  # デフォルト5分

    def _build_graphql_headers(self, cookies: Dict[str, str]) -> Dict[str, str]:
        """GraphQL API用のヘッダーを構築"""
        csrf_token = cookies.get("ct0", "")
        auth_token = cookies.get("auth_token", "")

        headers = {
            "authority": "x.com",
            "accept": "*/*",
            "accept-language": "ja,en;q=0.9",
            "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "content-type": "application/json",
            "cookie": "; ".join([f"{k}={v}" for k, v in cookies.items()]),
            "referer": "https://x.com/",
            "sec-ch-ua": '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            "x-csrf-token": csrf_token,
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "ja",
        }

        # 拡張ヘッダーの追加
        if self.header_enhancer:
            enhanced_headers = self.header_enhancer.get_enhanced_headers()
            headers.update(enhanced_headers)
            
            # デバッグ情報の出力
            if self.debug_mode:
                self._log_enhanced_headers(enhanced_headers, "GraphQL")
        else:
            # 拡張ヘッダー無効時は従来の固定値を使用
            headers["x-client-transaction-id"] = "0"

        # auth_tokenが存在する場合のみヘッダーを追加
        if auth_token:
            headers["x-twitter-auth-token"] = auth_token

        return headers

    def _build_rest_headers(self, cookies: Dict[str, str]) -> Dict[str, str]:
        """REST API用のヘッダーを構築"""
        csrf_token = cookies.get("ct0", "")

        headers = {
            "authority": "x.com",
            "accept": "*/*",
            "accept-language": "ja,en;q=0.9",
            "authorization": "Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA",
            "content-type": "application/x-www-form-urlencoded",
            "cookie": "; ".join([f"{k}={v}" for k, v in cookies.items()]),
            "origin": "https://x.com",
            "referer": "https://x.com/",
            "sec-ch-ua": '"Google Chrome";v="117", "Not;A=Brand";v="8", "Chromium";v="117"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
            "x-csrf-token": csrf_token,
            "x-twitter-active-user": "yes",
            "x-twitter-auth-type": "OAuth2Session",
            "x-twitter-client-language": "ja",
        }

        # 拡張ヘッダーの追加
        if self.header_enhancer:
            enhanced_headers = self.header_enhancer.get_enhanced_headers()
            headers.update(enhanced_headers)
            
            # デバッグ情報の出力
            if self.debug_mode:
                self._log_enhanced_headers(enhanced_headers, "REST")

        return headers

    def _log_enhanced_headers(self, enhanced_headers: Dict[str, str], endpoint_type: str):
        """拡張ヘッダーのデバッグログ出力"""
        print(f"\n[ENHANCED HEADERS - {endpoint_type}]")
        for key, value in enhanced_headers.items():
            if key == "x-xp-forwarded-for":
                print(f"  {key}: {value}")
            else:
                print(f"  {key}: {value}")

    def _get_graphql_features(self) -> Dict[str, bool]:
        """GraphQL API用のフィーチャーフラグを取得"""
        return {
            "hidden_profile_likes_enabled": True,
            "hidden_profile_subscriptions_enabled": True,
            "rweb_tipjar_consumption_enabled": True,
            "responsive_web_graphql_exclude_directive_enabled": True,
            "verified_phone_label_enabled": False,
            "responsive_web_graphql_timeline_navigation_enabled": True,
            "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
            "subscriptions_verification_info_verified_since_enabled": True,
            "responsive_web_twitter_article_notes_tab_enabled": True,
            "highlights_tweets_tab_ui_enabled": True,
            "creator_subscriptions_tweet_preview_api_enabled": True,
            "subscriptions_verification_info_is_identity_verified_enabled": True,
        }

    def _parse_user_response(
        self, data: Dict[str, Any], identifier: str
    ) -> Optional[Dict[str, Any]]:
        """APIレスポンスからユーザー情報を解析"""
        if (
            "data" in data
            and "user" in data["data"]
            and "result" in data["data"]["user"]
        ):
            result = data["data"]["user"]["result"]

            # ユーザーのTypeNameをチェック
            typename = result.get("__typename", "User")

            # ユーザーステータスの判定
            user_status = "active"
            if typename == "UserUnavailable":
                # ユーザーが利用不可の場合
                user_status = "unavailable"
                if "reason" in result:
                    user_status = result["reason"].lower()

                # 利用不可能なユーザーの基本情報
                return {
                    "id": result.get("rest_id"),
                    "screen_name": identifier if "@" in identifier else None,
                    "name": None,
                    "user_status": user_status,
                    "following": False,
                    "followed_by": False,
                    "blocking": False,
                    "blocked_by": False,
                    "protected": False,
                    "unavailable": True,
                }

            # 通常のユーザー情報
            if "legacy" in result:
                legacy = result["legacy"]
                
                # フォロー関係の取得
                following = legacy.get("following", False)
                # SuperFollowsを考慮
                if not following and "super_following" in legacy:
                    following = legacy.get("super_following", False)

                return {
                    "id": result.get("rest_id"),
                    "screen_name": legacy.get("screen_name"),
                    "name": legacy.get("name"),
                    "user_status": user_status,
                    "following": following,
                    "followed_by": legacy.get("followed_by", False),
                    "blocking": legacy.get("blocking", False),
                    "blocked_by": legacy.get("blocked_by", False),
                    "protected": legacy.get("protected", False),
                    "unavailable": False,
                }

        return None
    
    def _log_response_details(self, response: requests.Response, identifier: str, method_name: str = "") -> None:
        """レスポンスの詳細情報をログ出力"""
        try:
            # ステータスコードと基本情報
            print(f"\n[API Response - {method_name}] {identifier}")
            print(f"  Status Code: {response.status_code}")
            print(f"  Debug Mode: {self.debug_mode}")  # デバッグモード状態を明示
            
            # レートリミット情報
            if hasattr(response, 'headers'):
                rate_limit = response.headers.get('x-rate-limit-limit')
                rate_remaining = response.headers.get('x-rate-limit-remaining')
                rate_reset = response.headers.get('x-rate-limit-reset')
                
                if rate_limit:
                    print(f"  Rate Limit: {rate_remaining}/{rate_limit}")
                    if rate_reset:
                        tokyo_tz = pytz.timezone('Asia/Tokyo')
                        reset_time = datetime.fromtimestamp(int(rate_reset), tz=tokyo_tz)
                        print(f"  Reset Time: {reset_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
                
                # デバッグモードまたは403エラーの場合は追加情報を表示
                if self.debug_mode or response.status_code == 403:
                    print(f"  Content-Type: {response.headers.get('content-type', 'N/A')}")
                    print(f"  Content-Length: {response.headers.get('content-length', 'N/A')}")
                    # 403エラーの場合は全ヘッダーを表示
                    if response.status_code == 403:
                        print("  === 全ヘッダー情報 ===")
                        for key, value in response.headers.items():
                            print(f"  {key}: {value}")
        except Exception as e:
            print(f"  ログ出力エラー: {e}")
            # デバッグ用：例外の詳細も表示
            import traceback
            print(f"  詳細エラー: {traceback.format_exc()}")

        # エラー時の詳細情報
        if hasattr(response, 'status_code') and response.status_code >= 400:
            try:
                error_data = response.json()
                if 'errors' in error_data:
                    for error in error_data['errors']:
                        print(f"  エラー詳細: {error.get('message', 'Unknown error')}")
                        if 'code' in error:
                            print(f"  エラーコード: {error['code']}")
                else:
                    # JSON形式だがerrorsフィールドがない場合
                    print(f"  レスポンスJSON: {json.dumps(error_data, ensure_ascii=False, indent=2)[:500]}")
            except Exception as json_error:
                print(f"  JSON解析エラー: {json_error}")
                if hasattr(response, 'text'):
                    # 403エラーまたはデバッグモードの場合は全文表示
                    if response.status_code == 403 or self.debug_mode:
                        print(f"  レスポンステキスト全文:")
                        print(f"  {response.text}")
                    else:
                        print(f"  レスポンステキスト: {response.text[:200]}")
                else:
                    print(f"  レスポンス詳細取得不可")

    def _get_detailed_error_message(self, response: requests.Response, identifier: str) -> str:
        """詳細なエラーメッセージを生成"""
        status_messages = {
            400: "不正なリクエスト",
            401: "認証エラー（Cookieが無効）",
            403: "アクセス拒否",
            404: "ユーザーが見つからない",
            429: "レートリミット",
            500: "サーバーエラー",
            502: "Bad Gateway",
            503: "サービス利用不可"
        }
        
        status_code = getattr(response, 'status_code', 0)
        base_msg = status_messages.get(status_code, f"HTTPエラー {status_code}")
        
        # JSONレスポンスからエラー詳細を取得
        try:
            if hasattr(response, 'json'):
                error_data = response.json()
                if 'errors' in error_data and error_data['errors']:
                    error_details = []
                    for error in error_data['errors']:
                        msg = error.get('message', '')
                        code = error.get('code', '')
                        if code:
                            error_details.append(f"{msg} (code: {code})")
                        else:
                            error_details.append(msg)
                    return f"{base_msg} - {', '.join(error_details)}"
        except:
            pass
        
        # 403エラーの場合、追加情報を提供
        if status_code == 403:
            # アカウントロックの確認
            if self._is_account_locked(response):
                return f"{base_msg} - アカウントがロックされている可能性があります"
            else:
                return f"{base_msg} - 詳細はレスポンステキストを確認してください"
            
        return base_msg

    def _is_account_locked(self, response: requests.Response) -> bool:
        """アカウントロック状態を検出"""
        # HTTP 403 + 特定のエラーメッセージでアカウントロックを判定
        if hasattr(response, 'status_code') and response.status_code == 403:
            try:
                error_data = response.json()
                if 'errors' in error_data:
                    for error in error_data['errors']:
                        message = error.get('message', '').lower()
                        # アカウントロックを示すメッセージパターン
                        if any(pattern in message for pattern in [
                            'account is temporarily locked',
                            'account has been locked',
                            'suspicious activity',
                            'verify your account'
                        ]):
                            return True
            except:
                pass
        return False


    def _get_login_user_id(self) -> str:
        """ログインユーザーIDを取得（キャッシュ付き）"""
        if self._login_user_id:
            return self._login_user_id
        
        try:
            cookies = self.cookie_manager.load_cookies()
            
            # Method 1: twid cookieから取得（最も信頼性が高い）
            if 'twid' in cookies:
                # twid=u%3D1234567890 形式から数値部分を抽出
                twid = cookies['twid']
                if 'u%3D' in twid:
                    self._login_user_id = twid.split('u%3D')[1].split('%')[0]
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


    def _get_profile_from_cache(self, user_id: str) -> Optional[Dict[str, Any]]:
        """基本プロフィール情報キャッシュからデータを取得（共有）"""
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in "._-")
        cache_file = self.profiles_cache_dir / f"{safe_user_id}.json"
        
        if cache_file.exists():
            try:
                # ファイルの更新時刻を確認
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

    def _save_profile_to_cache(self, user_id: str, profile_data: Dict[str, Any]) -> None:
        """基本プロフィール情報キャッシュに保存（共有）"""
        safe_user_id = "".join(c for c in user_id if c.isalnum() or c in "._-")
        cache_file = self.profiles_cache_dir / f"{safe_user_id}.json"
        
        try:
            # 基本情報のみ抽出（関係情報は除外）
            profile_only = {
                "id": profile_data.get("id"),
                "screen_name": profile_data.get("screen_name"),
                "name": profile_data.get("name"),
                "user_status": profile_data.get("user_status", "active"),
                "protected": profile_data.get("protected", False),
                "unavailable": profile_data.get("unavailable", False),
                "cached_at": datetime.now().isoformat()
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(profile_only, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"プロフィールキャッシュ保存エラー ({user_id}): {e}")


    def _combine_profile_and_relationship(self, user_id: str) -> Optional[Dict[str, Any]]:
        """プロフィール情報と関係情報を結合"""
        # 基本プロフィール情報を取得
        profile_data = self._get_profile_from_cache(user_id)
        if not profile_data:
            return None
        
        # 関係情報を取得
        relationship_data = self._get_relationship_from_cache(user_id)
        
        # 結合
        combined_data = profile_data.copy()
        if relationship_data:
            combined_data.update({
                "following": relationship_data.get("following", False),
                "followed_by": relationship_data.get("followed_by", False),
                "blocking": relationship_data.get("blocking", False),
                "blocked_by": relationship_data.get("blocked_by", False),
            })
        else:
            # 関係情報がない場合のデフォルト値
            combined_data.update({
                "following": False,
                "followed_by": False,
                "blocking": False,
                "blocked_by": False,
            })
        
        return combined_data

    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュの統計情報を取得"""
        stats = {
            "lookups_cache": {"total": 0, "valid": 0, "expired": 0},
            "profiles_cache": {"total": 0, "valid": 0, "expired": 0},
            "relationships_cache": {"total": 0, "valid": 0, "expired": 0}
        }
        
        current_time = time.time()
        
        # 各キャッシュディレクトリをチェック
        cache_dirs = [
            ("lookups_cache", self.lookups_cache_dir),
            ("profiles_cache", self.profiles_cache_dir),
            ("relationships_cache", self.relationships_cache_dir)
        ]
        
        for cache_name, cache_dir in cache_dirs:
            if cache_dir.exists():
                # relationships_cacheの場合は再帰的に検索
                if cache_name == "relationships_cache":
                    for user_dir in cache_dir.iterdir():
                        if user_dir.is_dir():
                            for cache_file in user_dir.glob("*.json"):
                                stats[cache_name]["total"] += 1
                                file_mtime = cache_file.stat().st_mtime
                                if current_time - file_mtime < self.cache_ttl:
                                    stats[cache_name]["valid"] += 1
                                else:
                                    stats[cache_name]["expired"] += 1
                else:
                    for cache_file in cache_dir.glob("*.json"):
                        stats[cache_name]["total"] += 1
                        file_mtime = cache_file.stat().st_mtime
                        if current_time - file_mtime < self.cache_ttl:
                            stats[cache_name]["valid"] += 1
                        else:
                            stats[cache_name]["expired"] += 1
        
        # 合計を計算
        total_entries = sum(s["total"] for s in stats.values())
        valid_entries = sum(s["valid"] for s in stats.values())
        expired_entries = sum(s["expired"] for s in stats.values())
        
        return {
            "caches": stats,
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_dirs": {
                "lookups": str(self.lookups_cache_dir),
                "profiles": str(self.profiles_cache_dir),
                "relationships": str(self.relationships_cache_dir)
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

    def _handle_auth_error(self, identifier: str, method_name: str, retry_func):
        """認証エラーをハンドリングし、クッキーを再読み込みして再試行"""
        if self._auth_retry_count < self._max_auth_retries:
            self._auth_retry_count += 1
            print(f"認証エラー検出 ({identifier}): Cookieを再読み込みして再試行します... (試行 {self._auth_retry_count}/{self._max_auth_retries})")
            
            # ログインユーザーIDのキャッシュをクリア
            self._login_user_id = None
            
            # クッキーファイルの更新を待機
            try:
                # 現在のクッキーファイルのタイムスタンプを取得
                cookie_path = Path(self.cookie_manager.cookies_file)
                if cookie_path.exists():
                    original_mtime = cookie_path.stat().st_mtime
                    print(f"現在のCookieファイル更新時刻: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(original_mtime))}")
                    print("Cookieファイルの更新を待機しています...")
                    
                    # 最大1時間、ファイルの更新を待機
                    start_time = time.time()
                    timeout = 3600  # 1時間（3600秒）のタイムアウト
                    check_interval = 1.0  # 1秒ごとにチェック
                    
                    while time.time() - start_time < timeout:
                        current_mtime = cookie_path.stat().st_mtime
                        if current_mtime > original_mtime:
                            # ファイルが更新された
                            print(f"Cookieファイルが更新されました: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_mtime))}")
                            time.sleep(1)  # ファイル書き込み完了を待つため少し待機
                            break
                        
                        # 進捗表示（10秒ごと）
                        elapsed = int(time.time() - start_time)
                        if elapsed > 0 and elapsed % 10 == 0:
                            print(f"  待機中... ({elapsed}秒経過 / 最大{timeout}秒)")
                        
                        time.sleep(check_interval)
                    else:
                        print(f"警告: {timeout/60:.0f}分待機しましたが、Cookieファイルが更新されませんでした")
                
                # クッキーキャッシュをクリア
                self.cookie_manager.clear_cache()
                # 少し待機してから再試行
                time.sleep(2)
                
                # 再試行
                result = retry_func()
                
                # 成功したらカウンターをリセット
                self._auth_retry_count = 0
                return result
                
            except SystemExit:
                # 再試行でも失敗した場合は元のエラーを再発生
                raise
            except Exception as e:
                print(f"クッキー再読み込みエラー ({identifier}): {e}")
                
        # 再試行回数を超えた場合、または再試行でも失敗した場合
        print(f"認証エラー検出 ({identifier}): Cookieが無効です。処理を終了します")
        raise SystemExit("Authentication failed - Cookie is invalid")
