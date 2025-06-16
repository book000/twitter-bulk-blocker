"""
Twitter API アクセス管理モジュール
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

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

    # REST APIエンドポイント
    BLOCKS_CREATE_ENDPOINT = "https://x.com/i/api/1.1/blocks/create.json"

    def __init__(self, cookie_manager: CookieManager, cache_dir: str = "/data/cache"):
        self.cookie_manager = cookie_manager
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.user_cache_file = self.cache_dir / "user_info_cache.json"
        self.cache_ttl = 2592000  # 30日間（秒）

    def get_user_info(self, screen_name: str) -> Optional[Dict[str, Any]]:
        """スクリーンネームからユーザー情報を取得"""
        # キャッシュから確認
        cache_key = f"screen_name:{screen_name}"
        cached_result = self._get_from_cache(cache_key)
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
                    self._save_to_cache(cache_key, result)
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
        cache_key = f"user_id:{user_id}"
        cached_result = self._get_from_cache(cache_key)
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
                    self._save_to_cache(cache_key, result)
                return result

            # ステータスコード別のエラー表示
            error_msg = self._get_detailed_error_message(response, user_id)
            print(f"ユーザー情報取得失敗 (ID: {user_id}): {error_msg}")
            return None

        except Exception as e:
            print(f"ユーザー情報取得エラー (ID: {user_id}): {e}")
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

    def _load_cache(self) -> Dict[str, Any]:
        """キャッシュファイルを読み込み"""
        try:
            if self.user_cache_file.exists():
                with open(self.user_cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            pass
        return {}

    def _save_cache(self, cache_data: Dict[str, Any]) -> None:
        """キャッシュファイルに保存"""
        try:
            with open(self.user_cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"キャッシュ保存エラー: {e}")

    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """キャッシュからユーザー情報を取得"""
        cache_data = self._load_cache()
        
        if cache_key in cache_data:
            cached_entry = cache_data[cache_key]
            cached_time = cached_entry.get("cached_at", 0)
            current_time = time.time()
            
            # TTL期限内かチェック
            if current_time - cached_time < self.cache_ttl:
                return cached_entry.get("data")
            else:
                # 期限切れのエントリを削除
                del cache_data[cache_key]
                self._save_cache(cache_data)
                print(f"[CACHE EXPIRED] {cache_key}: キャッシュが期限切れです")
        
        return None

    def _save_to_cache(self, cache_key: str, user_data: Dict[str, Any]) -> None:
        """ユーザー情報をキャッシュに保存"""
        cache_data = self._load_cache()
        
        cache_entry = {
            "data": user_data,
            "cached_at": time.time()
        }
        
        cache_data[cache_key] = cache_entry
        self._save_cache(cache_data)
        print(f"[CACHE SAVE] {cache_key}: ユーザー情報をキャッシュに保存")

    def clear_cache(self) -> None:
        """キャッシュをクリア"""
        try:
            if self.user_cache_file.exists():
                self.user_cache_file.unlink()
                print("キャッシュファイルを削除しました")
        except Exception as e:
            print(f"キャッシュ削除エラー: {e}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """キャッシュ統計情報を取得"""
        cache_data = self._load_cache()
        current_time = time.time()
        
        total_entries = len(cache_data)
        valid_entries = 0
        expired_entries = 0
        
        for entry in cache_data.values():
            cached_time = entry.get("cached_at", 0)
            if current_time - cached_time < self.cache_ttl:
                valid_entries += 1
            else:
                expired_entries += 1
        
        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_file": str(self.user_cache_file),
            "cache_ttl_days": self.cache_ttl / 86400
        }
