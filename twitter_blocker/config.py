"""
設定管理モジュール
"""

import json
import time
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

    def __init__(self, cookies_file: str, cache_duration: int = 120):
        self.cookies_file = cookies_file
        self._cookies_cache = None
        self._cache_timestamp = None
        self._file_mtime = None
        self.cache_duration = cache_duration  # デフォルト2分（高頻度更新）
        
        # サービス固有の積極的更新設定
        self._aggressive_services = {"tomarabbit"}  # 問題頻発サービス
        self._aggressive_duration = 60  # 1分間隔

    def load_cookies(self) -> Dict[str, str]:
        """クッキーファイルを読み込み、動的更新対応のTwitterドメインクッキー抽出"""
        current_time = time.time()
        cookie_path = Path(self.cookies_file)
        
        # ファイル存在チェック
        if not cookie_path.exists():
            raise FileNotFoundError(f"Cookieファイルが見つかりません: {self.cookies_file}")
        
        current_mtime = cookie_path.stat().st_mtime
        
        # サービス固有の積極的更新判定
        service_name = self._detect_service_from_path()
        effective_duration = (self._aggressive_duration 
                            if service_name in self._aggressive_services 
                            else self.cache_duration)
        
        # キャッシュ有効性チェック（サービス別設定対応）
        cache_valid = (
            self._cookies_cache is not None and
            self._cache_timestamp is not None and
            self._file_mtime is not None and
            # 1. サービス別時間ベース有効期限チェック
            (current_time - self._cache_timestamp < effective_duration) and
            # 2. ファイル更新チェック  
            (current_mtime == self._file_mtime)
        )
        
        if cache_valid:
            return self._cookies_cache
        
        # キャッシュ無効時：ファイルから再読み込み
        refresh_reason = "サービス別積極更新" if service_name in self._aggressive_services else "通常更新"
        print(f"🔄 Cookie再読み込み ({refresh_reason}): {self.cookies_file}")
        if self._cookies_cache is not None:
            print(f"   理由: 時間経過={current_time - (self._cache_timestamp or 0):.1f}秒 "
                  f"(設定: {effective_duration}秒), "
                  f"ファイル更新={'Yes' if current_mtime != (self._file_mtime or 0) else 'No'}")
        
        with open(self.cookies_file, "r", encoding="utf-8") as f:
            cookies_list = json.load(f)

        cookies_dict = {}
        for cookie in cookies_list:
            domain = cookie.get("domain", "")
            if domain in self.TWITTER_DOMAINS:
                cookies_dict[cookie["name"]] = cookie["value"]

        # キャッシュ更新
        self._cookies_cache = cookies_dict
        self._cache_timestamp = current_time
        self._file_mtime = current_mtime
        
        print(f"✅ Cookie更新完了: {len(cookies_dict)}個のTwitter関連Cookie取得")
        return cookies_dict
    
    def clear_cache(self):
        """クッキーキャッシュをクリアして次回読み込み時にファイルから再読み込みさせる"""
        print("🧹 Cookieキャッシュクリア実行")
        self._cookies_cache = None
        self._cache_timestamp = None
        self._file_mtime = None
    
    def force_refresh_on_error_threshold(self, error_count: int, threshold: int = 5) -> bool:
        """403エラーが閾値を超えた場合の強制Cookie更新（適正化）"""
        if error_count >= threshold:
            print(f"🚨 403エラー{error_count}回検出: Cookie強制更新実行（閾値: {threshold}）")
            self.clear_cache()
            return True
        return False
    
    def set_cache_duration(self, duration: int):
        """キャッシュ有効期限を動的変更（秒単位）"""
        old_duration = self.cache_duration
        self.cache_duration = duration
        print(f"⏰ Cookieキャッシュ有効期限変更: {old_duration}秒 → {duration}秒")
        
    def get_cache_info(self) -> Dict[str, Any]:
        """現在のキャッシュ状態情報を取得"""
        current_time = time.time()
        service_name = self._detect_service_from_path()
        effective_duration = (self._aggressive_duration 
                            if service_name in self._aggressive_services 
                            else self.cache_duration)
        
        return {
            "cached": self._cookies_cache is not None,
            "cache_age": current_time - (self._cache_timestamp or 0) if self._cache_timestamp else None,
            "cache_duration": self.cache_duration,
            "effective_duration": effective_duration,
            "service_name": service_name,
            "aggressive_mode": service_name in self._aggressive_services,
            "cookies_count": len(self._cookies_cache) if self._cookies_cache else 0,
            "file_mtime": self._file_mtime,
            "next_refresh_in": max(0, effective_duration - (current_time - (self._cache_timestamp or 0))) if self._cache_timestamp else 0
        }
    
    def _detect_service_from_path(self) -> str:
        """Cookieファイルパスからサービス名を検出"""
        path_str = str(self.cookies_file)
        if "tomarabbit" in path_str:
            return "tomarabbit"
        elif "book000_vrc" in path_str:
            return "book000_vrc"
        elif "book000" in path_str:
            return "book000"
        elif "authorizedkey" in path_str:
            return "authorizedkey"
        elif "tomachi_priv" in path_str:
            return "tomachi_priv"
        elif "ihc_amot" in path_str:
            return "ihc_amot"
        else:
            return "unknown"
