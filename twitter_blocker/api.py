"""
Twitter API アクセス管理モジュール
"""

import json
from typing import Any, Dict, Optional

import requests

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

    def __init__(self, cookie_manager: CookieManager):
        self.cookie_manager = cookie_manager

    def get_user_info(self, screen_name: str) -> Optional[Dict[str, Any]]:
        """スクリーンネームからユーザー情報を取得"""
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

            if response.status_code == 200:
                return self._parse_user_response(response.json(), screen_name)

            return None

        except Exception as e:
            print(f"ユーザー情報取得エラー ({screen_name}): {e}")
            return None

    def get_user_info_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """ユーザーIDからユーザー情報を取得"""
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

            if response.status_code == 200:
                return self._parse_user_response(response.json(), user_id=user_id)

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
                        legacy.get("id_str") or result.get("rest_id") or str(user_id)
                        if user_id
                        else None
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
