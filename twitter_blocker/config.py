"""
設定管理モジュール
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple


class ConfigManager:
    """設定ファイルとスキーマ管理クラス"""

    SUPPORTED_FORMATS = ["user_id", "screen_name"]

    def __init__(self, users_file: str):
        self.users_file = users_file
        self._user_format = None
        self._users_data = None

    def load_users_data(self) -> Tuple[List[str], str]:
        """ユーザーデータをロードし、形式と共に返す"""
        if self._users_data is not None and self._user_format is not None:
            return self._users_data, self._user_format

        with open(self.users_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        self._validate_schema(data)
        self._user_format = data["format"]
        self._users_data = data["users"]

        return self._users_data, self._user_format

    def get_user_format(self) -> str:
        """ユーザーファイルの形式を取得"""
        if self._user_format is None:
            self.load_users_data()
        return self._user_format

    def _validate_schema(self, data: Any) -> None:
        """提案1スキーマの検証"""
        if not isinstance(data, dict):
            raise ValueError(
                f"不正なユーザーファイル形式: {type(data)}。"
                f"期待値: {{'format': 'user_id|screen_name', 'users': [...]}}"
            )

        # 必須フィールドの確認
        if "format" not in data:
            raise ValueError(
                "不正なスキーマ: 'format' フィールドが必要です。"
                "期待値: {'format': 'user_id|screen_name', 'users': [...]}"
            )

        if "users" not in data:
            raise ValueError(
                "不正なスキーマ: 'users' フィールドが必要です。"
                "期待値: {'format': 'user_id|screen_name', 'users': [...]}"
            )

        # formatフィールドの検証
        format_value = data["format"]
        if format_value not in self.SUPPORTED_FORMATS:
            raise ValueError(
                f"不正なformat値: '{format_value}'。"
                f"有効値: {' または '.join(self.SUPPORTED_FORMATS)}"
            )

        # usersフィールドの検証
        users = data["users"]
        if not isinstance(users, list):
            raise ValueError(
                f"不正なusers値: リストである必要があります。取得値: {type(users)}"
            )

        if not users:
            raise ValueError("users リストが空です")


class CookieManager:
    """クッキー管理クラス"""

    TWITTER_DOMAINS = [".x.com", ".twitter.com", "x.com", "twitter.com"]

    def __init__(self, cookies_file: str):
        self.cookies_file = cookies_file

    def load_cookies(self) -> Dict[str, str]:
        """クッキーファイルを読み込み、Twitterドメインのクッキーのみ抽出"""
        with open(self.cookies_file, "r", encoding="utf-8") as f:
            cookies_list = json.load(f)

        cookies_dict = {}
        for cookie in cookies_list:
            domain = cookie.get("domain", "")
            if domain in self.TWITTER_DOMAINS:
                cookies_dict[cookie["name"]] = cookie["value"]

        return cookies_dict
