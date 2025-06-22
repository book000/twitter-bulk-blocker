"""
Twitter API アクセス管理モジュール
"""

import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytz
import requests

from .config import CookieManager
from .retry import RetryManager
from .error_analytics import HTTPErrorAnalytics


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
        
        # 効果測定用のデータ
        self.header_stats = {
            "total_requests": 0,
            "enhanced_requests": 0,
            "success_rate_enhanced": 0.0,
            "success_rate_basic": 0.0,
            "recent_results": [],  # (timestamp, enhanced, success)
            "quality_score": 0.5,  # 0.0-1.0
        }
        self._max_results_history = 100
        
    def record_request_result(self, enhanced: bool, success: bool):
        """リクエスト結果を記録して効果を測定"""
        current_time = time.time()
        
        # 基本統計を更新
        self.header_stats["total_requests"] += 1
        if enhanced:
            self.header_stats["enhanced_requests"] += 1
        
        # 結果履歴を記録
        self.header_stats["recent_results"].append((current_time, enhanced, success))
        
        # 古い履歴を制限
        if len(self.header_stats["recent_results"]) > self._max_results_history:
            self.header_stats["recent_results"] = self.header_stats["recent_results"][-self._max_results_history:]
        
        # 成功率を計算
        self._update_success_rates()
        
    def _update_success_rates(self):
        """拡張ヘッダーあり/なしの成功率を計算"""
        cutoff_time = time.time() - 600  # 直近10分間
        recent_results = [
            result for result in self.header_stats["recent_results"]
            if result[0] >= cutoff_time
        ]
        
        if not recent_results:
            return
        
        # 拡張ヘッダーありの成功率
        enhanced_results = [r for r in recent_results if r[1]]  # enhanced=True
        if enhanced_results:
            enhanced_success = sum(1 for r in enhanced_results if r[2])  # success=True
            self.header_stats["success_rate_enhanced"] = enhanced_success / len(enhanced_results)
        
        # 基本ヘッダーの成功率
        basic_results = [r for r in recent_results if not r[1]]  # enhanced=False
        if basic_results:
            basic_success = sum(1 for r in basic_results if r[2])  # success=True
            self.header_stats["success_rate_basic"] = basic_success / len(basic_results)
        
        # 品質スコアの計算（拡張ヘッダーの有効性）
        if enhanced_results and basic_results:
            improvement = self.header_stats["success_rate_enhanced"] - self.header_stats["success_rate_basic"]
            self.header_stats["quality_score"] = max(0.0, min(1.0, 0.5 + improvement))
        elif enhanced_results:
            # 拡張ヘッダーのみの場合、成功率をスコアとする
            self.header_stats["quality_score"] = self.header_stats["success_rate_enhanced"]
    
    def should_use_enhanced_headers(self) -> bool:
        """拡張ヘッダーを使用すべきかを判定"""
        # 十分なデータがない場合はデフォルトで使用
        if self.header_stats["total_requests"] < 20:
            return True
        
        # 品質スコアが高い場合は継続使用
        return self.header_stats["quality_score"] >= 0.4
    
    def get_effectiveness_report(self) -> Dict[str, Any]:
        """拡張ヘッダーの効果レポートを取得"""
        return {
            "total_requests": self.header_stats["total_requests"],
            "enhanced_requests": self.header_stats["enhanced_requests"],
            "success_rate_enhanced": round(self.header_stats["success_rate_enhanced"], 3),
            "success_rate_basic": round(self.header_stats["success_rate_basic"], 3),
            "quality_score": round(self.header_stats["quality_score"], 3),
            "recommendation": "use_enhanced" if self.should_use_enhanced_headers() else "use_basic",
            "data_points": len(self.header_stats["recent_results"])
        }
        
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
        拡張ヘッダーの辞書を取得（Unknown error対策強化版）
        
        Returns:
            拡張ヘッダーの辞書
        """
        headers = {
            "x-client-transaction-id": self.get_transaction_id(),
            # Unknown error対策：追加のアンチボットヘッダー
            "x-client-uuid": self._generate_client_uuid(),
            "x-request-id": self._generate_request_id(),
        }
        
        forwarded_for = self.get_forwarded_for()
        if forwarded_for:
            headers["x-xp-forwarded-for"] = forwarded_for
            
        return headers
    
    def _generate_client_uuid(self) -> str:
        """クライアントUUIDを生成（セッション中は固定）"""
        if not hasattr(self, '_client_uuid'):
            self._client_uuid = ''.join(random.choices('0123456789abcdef-', k=36))
        return self._client_uuid
    
    def _generate_request_id(self) -> str:
        """リクエストIDを生成（リクエスト毎に変化）"""
        import time
        timestamp = int(time.time() * 1000)
        random_part = random.randint(100000, 999999)
        return f"{timestamp}-{random_part}"


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
        
        # セッション開始時刻の記録（長期稼働パターン検出用）
        self._session_start_time = time.time()
        
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
        self._max_auth_retries = 10  # 最大認証再試行回数（Cookie更新後の信頼性向上）
        
        # エラー多発検出用
        self._consecutive_errors = 0  # 連続エラー数
        self._error_window_start = None  # エラー監視窓の開始時刻
        self._error_count_in_window = 0  # 指定時間内のエラー数
        self._error_window_duration = 1800  # 30分間のエラー監視窓（秒）
        self._max_errors_in_window = 50  # 30分間で50回エラーでCookie再読み込み
        self._max_consecutive_errors = 10  # 連続10回エラーでCookie再読み込み
        
        # 強化された403エラー対応
        self.retry_manager = RetryManager()
        self._403_error_stats = {
            "total_403_errors": 0,
            "classified_errors": {},
            "recovery_success_rate": 0.0,
            "adaptive_delays_active": True
        }
        
        # 早期警告システム
        self.early_warning_system = {
            "error_spike_threshold": 20,  # 5分間で20回以上で警告
            "error_rate_threshold": 0.7,  # エラー率70%以上で警告
            "critical_error_types": ["anti_bot", "ip_blocked", "account_restricted"],
            "warning_issued": False,
            "last_warning_time": 0,
            "warning_cooldown": 600  # 10分間のクールダウン
        }
        
        # HTTPエラー分析システムの初期化（後で設定）
        self.error_analytics = None


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
                return self._handle_account_lock_error(screen_name, "get_user_info", 
                                                       lambda: self.get_user_info(screen_name))

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
                # 成功時はエラーカウンターをリセット
                self._reset_error_counters_on_success()
                
                # 拡張ヘッダーの効果測定　
                if self.header_enhancer:
                    self.header_enhancer.record_request_result(
                        enhanced=self.enable_header_enhancement,
                        success=True
                    )
                
                return result

            # ステータスコード別のエラー表示
            error_msg, error_classification = self._get_detailed_error_message(response, screen_name)
            
            # 拡張ヘッダーの効果測定
            if self.header_enhancer:
                self.header_enhancer.record_request_result(
                    enhanced=self.enable_header_enhancement,
                    success=False
                )
            
            print(f"ユーザー情報取得失敗 ({screen_name}): {error_msg}")
            
            # エラー多発チェック
            if self._track_error_and_check_cookie_reload(screen_name, "user_info"):
                return self._handle_frequent_errors(screen_name, "get_user_info", 
                                                   lambda: self.get_user_info(screen_name))
            
            return None

        except Exception as e:
            print(f"ユーザー情報取得エラー ({screen_name}): {e}")
            # エラー多発チェック（例外でも追跡）
            if self._track_error_and_check_cookie_reload(screen_name, "exception"):
                try:
                    return self._handle_frequent_errors(screen_name, "get_user_info", 
                                                       lambda: self.get_user_info(screen_name))
                except:
                    pass  # 回復に失敗した場合は通常のエラーとして扱う
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
                return self._handle_account_lock_error(user_id, "get_user_info_by_id", 
                                                       lambda: self.get_user_info_by_id(user_id))

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
            error_msg, error_classification = self._get_detailed_error_message(response, user_id)
            
            # 拡張ヘッダーの効果測定
            if self.header_enhancer:
                self.header_enhancer.record_request_result(
                    enhanced=self.enable_header_enhancement,
                    success=False
                )
            
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
                return self._handle_account_lock_error(f"batch({len(user_ids)}users)", "get_users_batch", 
                                                       lambda: self._fetch_users_batch(user_ids))

            if response.status_code == 200:
                return self._parse_users_batch_response(response.json(), user_ids)

            # ステータスコード別のエラー表示
            error_msg, error_classification = self._get_detailed_error_message(response, f"batch({len(user_ids)}users)")
            
            # 拡張ヘッダーの効果測定
            if self.header_enhancer:
                self.header_enhancer.record_request_result(
                    enhanced=self.enable_header_enhancement,
                    success=False
                )
            
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
                return self._handle_account_lock_error(screen_name, "_fetch_single_screen_name_lookup", 
                                                       lambda: self._fetch_single_screen_name_lookup(screen_name))

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
                return self._handle_account_lock_error(screen_name, "_fetch_single_screen_name", 
                                                       lambda: self._fetch_single_screen_name(screen_name))

            if response.status_code == 200:
                return self._parse_user_response(response.json(), screen_name)

            # エラーの場合
            error_msg, error_classification = self._get_detailed_error_message(response, screen_name)
            
            # 拡張ヘッダーの効果測定
            if self.header_enhancer:
                self.header_enhancer.record_request_result(
                    enhanced=self.enable_header_enhancement,
                    success=False
                )
            
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
                return self._handle_account_lock_error(f"block {screen_name}", "block_user", 
                                                       lambda: self.block_user(user_id, screen_name))

            if response.status_code == 200:
                # 成功時はエラーカウンターをリセット
                self._reset_error_counters_on_success()
                return {"success": True, "status_code": 200}

            # その他のエラー
            error_msg, error_classification = self._get_detailed_error_message(response, f"block {screen_name}")
            
            # 403エラー専用処理：Cookie強制更新
            if response.status_code == 403:
                self._403_error_stats["total_403_errors"] += 1
                # 403エラー閾値による強制Cookie更新（適正化）
                if self.cookie_manager.force_refresh_on_error_threshold(
                    self._403_error_stats["total_403_errors"], threshold=5):
                    print(f"🔄 403エラー蓄積による強制リトライ: {screen_name}")
                    # Cookie更新後の待機時間を追加（無限ループ防止）
                    import time
                    time.sleep(2)
                    # Cookie更新後に1回だけリトライ
                    return self.block_user(user_id, screen_name)
            
            # 拡張ヘッダーの効果測定
            if self.header_enhancer:
                self.header_enhancer.record_request_result(
                    enhanced=self.enable_header_enhancement,
                    success=False
                )
            
            # エラー多発チェック
            if self._track_error_and_check_cookie_reload(f"block {screen_name}", "block"):
                return self._handle_frequent_errors(f"block {screen_name}", "block_user", 
                                                   lambda: self.block_user(user_id, screen_name))
            
            return {
                "success": False,
                "status_code": response.status_code,
                "message": error_msg,
            }

        except Exception as e:
            # エラー多発チェック（例外でも追跡）
            if self._track_error_and_check_cookie_reload(f"block {screen_name}", "exception"):
                try:
                    return self._handle_frequent_errors(f"block {screen_name}", "block_user", 
                                                       lambda: self.block_user(user_id, screen_name))
                except:
                    pass  # 回復に失敗した場合は通常のエラーとして扱う
            
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

    def _get_detailed_error_message(self, response: requests.Response, identifier: str) -> Tuple[str, Optional[str]]:
        """詳細なエラーメッセージとエラー分類を生成"""
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
        
        # 403エラーの詳細分類
        if status_code == 403:
            response_text = ""
            try:
                response_text = response.text if hasattr(response, 'text') else ""
            except:
                pass
            
            headers = dict(response.headers) if hasattr(response, 'headers') else {}
            error_type, description, priority = self.retry_manager.error_classifier.classify_403_error(
                response_text=response_text,
                headers=headers,
                status_code=status_code
            )
            
            # 統計更新
            self._403_error_stats["total_403_errors"] += 1
            if error_type not in self._403_error_stats["classified_errors"]:
                self._403_error_stats["classified_errors"][error_type] = 0
            self._403_error_stats["classified_errors"][error_type] += 1
            
            # HTTPエラー分析システムへの記録
            if self.error_analytics:
                runtime_hours = (time.time() - self._session_start_time) / 3600
                self.error_analytics.record_error_with_context({
                    'timestamp': time.time(),
                    'error_type': error_type,
                    'status_code': status_code,
                    'response_text': response_text[:1000],  # 最初の1000文字のみ
                    'headers': dict(headers),
                    'runtime_hours': runtime_hours,
                    'retry_count': 0,  # 初回エラー
                    'success_rate_before': 1.0,  # TODO: 実際の成功率計算
                    'header_enhancement_active': self.enable_header_enhancement,
                    'user_context': f"Priority: {priority}, Description: {description}",
                    'container_name': 'unknown'  # TODO: コンテナ名の取得
                })
                
                # 時間帯別統計の更新
                self.error_analytics.update_hourly_stats(
                    runtime_hours=runtime_hours,
                    error_occurred=True,
                    error_type=error_type
                )
            
            # 早期警告システムのチェック
            self._check_early_warning_conditions(error_type)
            
            # アカウントロックの確認（従来ロジックも保持）
            if self._is_account_locked(response):
                detailed_msg = f"{base_msg} - アカウントロック [Type: {error_type}] {description}"
            else:
                detailed_msg = f"{base_msg} - [Type: {error_type}] {description} (Priority: {priority})"
            
            return detailed_msg, error_type
            
        return base_msg, None

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

    def _handle_account_lock_error(self, identifier: str, method_name: str, retry_func):
        """アカウントロックエラーをハンドリングし、クッキーを再読み込みして再試行"""
        if self._auth_retry_count < self._max_auth_retries:
            self._auth_retry_count += 1
            print(f"\n🔒 アカウントロック検出 ({identifier}): Cookie再読み込み＋リトライ {self._auth_retry_count}/{self._max_auth_retries}")
            
            # ログインユーザーIDのキャッシュをクリア
            self._login_user_id = None
            
            # リトライ間隔の計算（アカウントロック用により長い待機）
            base_delay = min(5 ** (self._auth_retry_count - 1), 300)  # より長い待機（最大5分）
            jitter = random.uniform(0.8, 1.2)  # 小さなランダム要素
            retry_delay = base_delay * jitter
            
            print(f"📊 アカウントロック用リトライ戦略: 基本待機時間={base_delay}秒, 調整後={retry_delay:.1f}秒")
            
            # クッキーファイルの更新を待機
            try:
                # 現在のクッキーファイルのタイムスタンプを取得
                cookie_path = Path(self.cookie_manager.cookies_file)
                if cookie_path.exists():
                    initial_mtime = cookie_path.stat().st_mtime
                    print(f"🕒 Cookie更新待機中... (現在: {datetime.fromtimestamp(initial_mtime).strftime('%H:%M:%S')})")
                    
                    # より長い時間をかけてCookie更新を待機
                    max_wait_time = max(60, retry_delay)  # 最低60秒
                    start_time = time.time()
                    
                    while time.time() - start_time < max_wait_time:
                        time.sleep(5)  # 5秒間隔でチェック
                        if cookie_path.exists():
                            current_mtime = cookie_path.stat().st_mtime
                            if current_mtime > initial_mtime:
                                print(f"✅ Cookie更新検出 (更新時刻: {datetime.fromtimestamp(current_mtime).strftime('%H:%M:%S')})")
                                # Cookie更新後のクールダウン期間（無限ループ防止）
                                time.sleep(5)
                                break
                        print(f"⏳ Cookie更新待機中... (経過: {int(time.time() - start_time)}秒)")
                    else:
                        print(f"⚠️ {max_wait_time}秒待機しましたが、Cookie更新を検出できませんでした")
                
                # 追加の待機時間
                print(f"⏸️ アカウントロック解除待機: {retry_delay:.1f}秒")
                time.sleep(retry_delay)
                
                # 認証リトライカウンターをリセット（新しいCookieでリトライ）
                temp_auth_retry = self._auth_retry_count
                self._auth_retry_count = 0
                
                try:
                    # リトライ実行
                    print(f"🔄 アカウントロック回復試行中...")
                    result = retry_func()
                    # 成功した場合はカウンターをリセット
                    self._auth_retry_count = 0
                    print(f"✅ アカウントロック回復成功！({temp_auth_retry}回目で成功)")
                    return result
                except SystemExit as e:
                    if "Account locked" in str(e):
                        # まだアカウントロック状態の場合
                        self._auth_retry_count = temp_auth_retry
                        if self._auth_retry_count < self._max_auth_retries:
                            print(f"🔒 アカウントロック継続中、再リトライします...")
                            return self._handle_account_lock_error(identifier, method_name, retry_func)
                        else:
                            print(f"🚫 最大リトライ回数（{self._max_auth_retries}回）に達しました")
                            raise
                    else:
                        raise
                except Exception as e:
                    # その他のエラーの場合、カウンターを戻して再試行
                    self._auth_retry_count = temp_auth_retry
                    if self._auth_retry_count < self._max_auth_retries:
                        return self._handle_account_lock_error(identifier, method_name, retry_func)
                    else:
                        raise
                        
            except Exception as e:
                print(f"❌ アカウントロック回復エラー ({identifier}): {e}")
                if self._auth_retry_count < self._max_auth_retries:
                    time.sleep(retry_delay)
                    return self._handle_account_lock_error(identifier, method_name, retry_func)
                else:
                    raise
                    
        # 再試行回数を超えた場合
        print(f"\n🚫 アカウントロック最終判定 ({identifier}): {self._max_auth_retries}回のリトライ後もロック状態")
        print("📋 考えられる原因:")
        print("  1. 長期的なアカウント制限")
        print("  2. セキュリティ検証が必要")
        print("  3. 新しいCookieファイルが必要")
        print("🔧 対処方法: ブラウザでTwitterにログインし、新しいCookieファイルを取得してください")
        self._auth_retry_count = 0  # カウンターをリセット
        raise SystemExit("Account locked - Cookie reload failed")

    def _track_error_and_check_cookie_reload(self, identifier: str, error_type: str = "general") -> bool:
        """エラーを追跡し、Cookie再読み込みが必要かチェック"""
        current_time = time.time()
        
        # 連続エラー数をカウント
        self._consecutive_errors += 1
        
        # エラー監視窓の管理
        if self._error_window_start is None:
            self._error_window_start = current_time
            self._error_count_in_window = 1
        else:
            # 監視窓内のエラーかチェック
            if current_time - self._error_window_start <= self._error_window_duration:
                self._error_count_in_window += 1
            else:
                # 新しい監視窓を開始
                self._error_window_start = current_time
                self._error_count_in_window = 1
        
        # Cookie再読み込み条件のチェック
        needs_cookie_reload = False
        reason = ""
        
        if self._consecutive_errors >= self._max_consecutive_errors:
            needs_cookie_reload = True
            reason = f"連続{self._consecutive_errors}回エラー"
        elif self._error_count_in_window >= self._max_errors_in_window:
            needs_cookie_reload = True
            reason = f"30分間で{self._error_count_in_window}回エラー"
        
        if needs_cookie_reload:
            print(f"\n⚠️ エラー多発検出 ({identifier}): {reason}")
            print(f"📊 エラー統計: 連続={self._consecutive_errors}回, 30分間={self._error_count_in_window}回")
            return True
        
        return False

    def _handle_frequent_errors(self, identifier: str, method_name: str, retry_func):
        """エラー多発時のCookie再読み込み処理"""
        print(f"\n🔄 エラー多発によるCookie再読み込み実行 ({identifier})")
        
        # エラーカウンターをリセット
        self._consecutive_errors = 0
        self._error_window_start = None
        self._error_count_in_window = 0
        
        # ログインユーザーIDのキャッシュをクリア
        self._login_user_id = None
        
        # Cookie再読み込み待機
        try:
            cookie_path = Path(self.cookie_manager.cookies_file)
            if cookie_path.exists():
                initial_mtime = cookie_path.stat().st_mtime
                print(f"🕒 エラー多発対応のCookie更新待機中... (現在: {datetime.fromtimestamp(initial_mtime).strftime('%H:%M:%S')})")
                
                # 短い時間でCookie更新を待機（エラー多発時は緊急対応）
                max_wait_time = 30  # 30秒で短縮
                start_time = time.time()
                
                while time.time() - start_time < max_wait_time:
                    time.sleep(2)  # 2秒間隔でチェック
                    if cookie_path.exists():
                        current_mtime = cookie_path.stat().st_mtime
                        if current_mtime > initial_mtime:
                            print(f"✅ Cookie更新検出 (更新時刻: {datetime.fromtimestamp(current_mtime).strftime('%H:%M:%S')})")
                            # Cookie更新後のクールダウン期間（無限ループ防止）
                            time.sleep(5)
                            break
                    print(f"⏳ Cookie更新待機中... (経過: {int(time.time() - start_time)}秒)")
                else:
                    print(f"⚠️ {max_wait_time}秒待機しましたが、Cookie更新を検出できませんでした")
            
            # 短い待機時間でリトライ
            retry_delay = 10  # エラー多発時は短縮
            print(f"⏸️ エラー多発対応待機: {retry_delay}秒")
            time.sleep(retry_delay)
            
            # リトライ実行
            print(f"🔄 エラー多発回復試行中...")
            result = retry_func()
            print(f"✅ エラー多発回復成功！")
            return result
            
        except Exception as e:
            print(f"❌ エラー多発回復エラー ({identifier}): {e}")
            # エラー多発回復に失敗した場合は通常のエラーとして扱う
            raise

    def _reset_error_counters_on_success(self):
        """成功時にエラーカウンターをリセット（403エラー統計含む）"""
        reset_messages = []
        
        if self._consecutive_errors > 0:
            reset_messages.append(f"連続: {self._consecutive_errors}")
            self._consecutive_errors = 0
        
        if self._error_count_in_window > 0:
            reset_messages.append(f"窓内: {self._error_count_in_window}")
            # 監視窓は継続（時間ベースのため）
        
        # 403エラー統計のリセット（重要: 無限ループ防止）
        if self._403_error_stats["total_403_errors"] > 0:
            reset_messages.append(f"403エラー: {self._403_error_stats['total_403_errors']}")
            self._403_error_stats["total_403_errors"] = 0
            self._403_error_stats["classified_errors"] = {}
        
        if reset_messages and self.debug_mode:
            print(f"📉 エラーカウンターリセット ({', '.join(reset_messages)})")


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
    
    def _check_long_term_403_patterns(self) -> List[str]:
        """長期稼働時の403エラーパターンを早期検出"""
        warnings = []
        current_time = time.time()
        
        # セッション開始時刻の推定（初回リクエスト時刻）
        if hasattr(self, '_session_start_time'):
            runtime_hours = (current_time - self._session_start_time) / 3600
        else:
            # 初回実行時はセッション開始時刻を設定
            self._session_start_time = current_time
            runtime_hours = 0
        
        # 2-3時間の重要遷移期間での警告
        if 2.0 <= runtime_hours <= 3.5:
            total_403s = self._403_error_stats["total_403_errors"]
            recent_auth_errors = self._403_error_stats["classified_errors"].get("auth_required", 0)
            recent_anti_bot = self._403_error_stats["classified_errors"].get("anti_bot", 0)
            
            if recent_auth_errors > 5:
                warnings.append(f"🚨 認証劣化検出 (2-3時間遷移期): 認証エラー{recent_auth_errors}回 - Cookie予防的再読み込み推奨")
            
            if recent_anti_bot > 3:
                warnings.append(f"🤖 アンチボット強化検出 (2-3時間遷移期): anti_botエラー{recent_anti_bot}回 - ヘッダー戦略変更必要")
            
            if total_403s > 20:
                warnings.append(f"⚠️ 403エラー集中発生 (2-3時間遷移期): 総数{total_403s}回 - システム劣化進行中")
        
        # 3時間以上の長期稼働での劣化パターン
        elif runtime_hours > 3.0:
            # IP評価低下の検出
            ip_blocked = self._403_error_stats["classified_errors"].get("ip_blocked", 0)
            account_restricted = self._403_error_stats["classified_errors"].get("account_restricted", 0)
            
            if ip_blocked > 0:
                warnings.append(f"🚨 IP制限検出 (長期稼働{runtime_hours:.1f}h): IP制限{ip_blocked}回 - 最重要レベル対応必要")
            
            if account_restricted > 2:
                warnings.append(f"🔒 アカウント制限増加 (長期稼働{runtime_hours:.1f}h): 制限{account_restricted}回 - アカウント健全性低下")
            
            # 長期稼働成功の場合のポジティブメッセージ
            if self._403_error_stats["total_403_errors"] < 10:
                warnings.append(f"✅ 長期稼働安定継続 ({runtime_hours:.1f}h): 403エラー{self._403_error_stats['total_403_errors']}回のみ - 優秀な安定性")
        
        return warnings
    
    def get_403_error_report(self) -> Dict[str, Any]:
        """詳細な403エラー統計レポートを取得"""
        retry_stats = self.retry_manager.get_error_statistics()
        
        return {
            "total_403_errors": self._403_error_stats["total_403_errors"],
            "classified_errors": dict(self._403_error_stats["classified_errors"]),
            "retry_manager_stats": retry_stats,
            "adaptive_delays_active": self._403_error_stats["adaptive_delays_active"],
            "header_enhancement_enabled": self.enable_header_enhancement,
            "header_effectiveness": self.header_enhancer.get_effectiveness_report() if self.header_enhancer else None
        }
    
    def get_comprehensive_error_analysis(self) -> Dict[str, Any]:
        """包括的なエラー分析レポートを生成"""
        # 403エラー統計
        error_403_report = self.get_403_error_report()
        
        # ヘッダー効果統計
        header_report = self.header_enhancer.get_effectiveness_report() if self.header_enhancer else {}
        
        # 長期稼働時の早期警告チェック
        long_term_warnings = self._check_long_term_403_patterns()
        
        # 推奨事項の生成
        recommendations = []
        
        # 長期稼働警告の追加
        if long_term_warnings:
            recommendations.extend(long_term_warnings)
        
        if error_403_report["total_403_errors"] > 50:
            dominant_error = max(error_403_report["classified_errors"].items(), key=lambda x: x[1])
            recommendations.append(f"最多エラータイプ: {dominant_error[0]} ({dominant_error[1]}回) - 特別対応が必要")
        
        if header_report.get("recommendation") == "use_basic":
            recommendations.append("拡張ヘッダーの効果が低いため、基本ヘッダーの使用を推奨")
        elif header_report.get("quality_score", 0) < 0.3:
            recommendations.append("ヘッダー戦略の見直しが必要")
        
        retry_stats = error_403_report.get("retry_manager_stats", {})
        if retry_stats.get("success_rate", 1.0) < 0.5:
            recommendations.append("リトライ成功率が低いため、バックオフ戦略の調整が必要")
        
        # HTTPエラー分析システムからの追加データ
        error_analytics_data = {}
        if self.error_analytics:
            try:
                error_analytics_data = {
                    "real_time_status": self.error_analytics.get_real_time_status(),
                    "error_progression": self.error_analytics.analyze_error_progression_patterns()
                }
            except Exception as e:
                error_analytics_data = {"error": f"分析データ取得エラー: {e}"}
        
        return {
            "summary": {
                "total_403_errors": error_403_report["total_403_errors"],
                "header_quality_score": header_report.get("quality_score", 0),
                "retry_success_rate": retry_stats.get("success_rate", 0),
                "analysis_timestamp": datetime.now().isoformat(),
                "runtime_hours": (time.time() - self._session_start_time) / 3600
            },
            "detailed_403_analysis": error_403_report,
            "header_effectiveness": header_report,
            "error_analytics": error_analytics_data,
            "recommendations": recommendations,
            "urgent_actions_needed": len([r for r in recommendations if "特別対応" in r or "緊急" in r]) > 0
        }
    
    def _check_early_warning_conditions(self, error_classification: str = None) -> bool:
        """エラーの早期警告条件をチェック"""
        current_time = time.time()
        
        # クールダウン中の場合は警告しない
        if (current_time - self.early_warning_system["last_warning_time"]) < self.early_warning_system["warning_cooldown"]:
            return False
        
        # エラー統計を取得
        retry_stats = self.retry_manager.get_error_statistics()
        
        # 条件1: エラースパイクの検出
        if retry_stats["total_attempts"] >= self.early_warning_system["error_spike_threshold"]:
            print(f"\n⚠️ 早期警告: エラースパイク検出 - 5分間で{retry_stats['total_attempts']}回のエラー")
            self._issue_early_warning("ERROR_SPIKE", retry_stats)
            return True
        
        # 条件2: エラー率の異常高騰
        if retry_stats["success_rate"] < (1 - self.early_warning_system["error_rate_threshold"]):
            print(f"\n⚠️ 早期警告: 高エラー率検出 - 成功率: {retry_stats['success_rate']:.1%}")
            self._issue_early_warning("HIGH_ERROR_RATE", retry_stats)
            return True
        
        # 条件3: 重大エラータイプの検出
        if error_classification in self.early_warning_system["critical_error_types"]:
            print(f"\n🚨 重大警告: 重編エラータイプ検出 - {error_classification}")
            self._issue_early_warning("CRITICAL_ERROR_TYPE", {"error_type": error_classification})
            return True
        
        return False
    
    def _issue_early_warning(self, warning_type: str, details: Dict[str, Any]):
        """早期警告を発行して対応策を提案"""
        current_time = time.time()
        self.early_warning_system["warning_issued"] = True
        self.early_warning_system["last_warning_time"] = current_time
        
        print(f"\n=== 早期警告システム ===\n")
        print(f"警告タイプ: {warning_type}")
        print(f"発生時刻: {datetime.fromtimestamp(current_time).strftime('%H:%M:%S')}")
        
        if warning_type == "ERROR_SPIKE":
            print(f"詳細: 5分間で{details['total_attempts']}回のエラーが発生")
            print("🔧 推奨対応:")
            print("  1. Cookieの再読み込みを実行")
            print("  2. リクエスト率を一時的に低下")
            print("  3. ヘッダー戦略の切り替えを検討")
        
        elif warning_type == "HIGH_ERROR_RATE":
            print(f"詳細: 成功率が{details['success_rate']:.1%}まで低下")
            print("🔧 推奨対応:")
            print("  1. バックオフ時間を延長")
            print("  2. 同時実行数を減らす")
            print("  3. APIエンドポイントの変更を検討")
        
        elif warning_type == "CRITICAL_ERROR_TYPE":
            error_type = details.get("error_type", "unknown")
            print(f"詳細: 重大エラータイプ '{error_type}' が発生")
            print("🚨 緊急対応:")
            if error_type == "anti_bot":
                print("  1. ヘッダー戦略を即座変更")
                print("  2. ユーザーエージェントをローテーション")
                print("  3. 一時停止してメンテナンスを検討")
            elif error_type == "ip_blocked":
                print("  1. IPアドレスの変更")
                print("  2. VPN/プロキシの利用を検討")
                print("  3. 24時間以上の休止を検討")
            elif error_type == "account_restricted":
                print("  1. アカウント状態の手動確認")
                print("  2. 代替アカウントの準備")
                print("  3. 数日間の操作停止")
        
        print(f"\n次回警告まで: {self.early_warning_system['warning_cooldown']//60}分間")
        print("========================\n")

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
        """認証エラーをハンドリングし、クッキーを再読み込みして再試行（最大10回）"""
        if self._auth_retry_count < self._max_auth_retries:
            self._auth_retry_count += 1
            print(f"\n🔑 認証エラー検出 ({identifier}): Cookie再読み込み＋リトライ {self._auth_retry_count}/{self._max_auth_retries}")
            
            # ログインユーザーIDのキャッシュをクリア
            self._login_user_id = None
            
            # リトライ間隔の計算（指数バックオフ + ランダム）
            base_delay = min(2 ** (self._auth_retry_count - 1), 60)  # 最大60秒
            jitter = random.uniform(0.5, 1.5)  # ランダム要素
            retry_delay = base_delay * jitter
            
            print(f"📊 リトライ戦略: 基本待機時間={base_delay}秒, 調整後={retry_delay:.1f}秒")
            
            # クッキーファイルの更新を待機
            try:
                # 現在のクッキーファイルのタイムスタンプを取得
                cookie_path = Path(self.cookie_manager.cookies_file)
                if cookie_path.exists():
                    original_mtime = cookie_path.stat().st_mtime
                    print(f"📁 現在のCookieファイル更新時刻: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(original_mtime))}")
                    
                    # タイムスタンプ更新を待機
                    if self._auth_retry_count == 1:
                        # 初回のみ長期間待機（Cookie更新を期待）
                        print("⏰ Cookieファイルのタイムスタンプ更新を待機中...")
                        timeout = 3600  # 1時間
                        check_interval = 1.0
                    else:
                        # 2回目以降は短期間の確認のみ
                        print(f"⏰ Cookieファイル確認中（{self._auth_retry_count}回目のリトライ）...")
                        timeout = 30  # 30秒
                        check_interval = 0.5
                    
                    start_time = time.time()
                    cookie_updated = False
                    
                    while time.time() - start_time < timeout:
                        current_mtime = cookie_path.stat().st_mtime
                        if current_mtime > original_mtime:
                            # ファイルが更新された
                            print(f"✅ Cookieファイルが更新されました: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_mtime))}")
                            cookie_updated = True
                            time.sleep(1)  # ファイル書き込み完了を待つため少し待機
                            break
                        
                        # 進捗表示（10秒ごと、またはタイムアウトが短い場合は5秒ごと）
                        elapsed = int(time.time() - start_time)
                        progress_interval = 5 if timeout <= 60 else 10
                        if elapsed > 0 and elapsed % progress_interval == 0:
                            remaining = timeout - elapsed
                            print(f"  📊 待機中... ({elapsed}秒経過 / 残り{remaining}秒)")
                        
                        time.sleep(check_interval)
                    
                    if not cookie_updated and self._auth_retry_count == 1:
                        print(f"⚠️ 警告: {timeout/60:.0f}分待機しましたが、Cookieファイルが更新されませんでした")
                        print("📋 既存のCookieでリトライを継続します")
                    elif not cookie_updated:
                        print(f"📋 Cookie更新なし（{timeout}秒経過）- 既存Cookieでリトライ継続")
                
                # クッキーキャッシュをクリア
                self.cookie_manager.clear_cache()
                print(f"🧹 Cookieキャッシュをクリアしました")
                
                # 適応的待機時間
                print(f"⏱️ リトライ前の待機: {retry_delay:.1f}秒")
                time.sleep(retry_delay)
                
                # 再試行実行
                print(f"🔄 リトライ実行中... ({self._auth_retry_count}/{self._max_auth_retries})")
                result = retry_func()
                
                # 成功したらカウンターをリセット
                print(f"✅ リトライ成功！認証エラーが解決されました ({self._auth_retry_count}回目で成功)")
                self._auth_retry_count = 0
                return result
                
            except SystemExit:
                # 再試行でも認証エラーの場合、次のリトライに進む
                print(f"❌ リトライ {self._auth_retry_count}回目も認証エラー")
                if self._auth_retry_count < self._max_auth_retries:
                    print(f"📈 次のリトライ（{self._auth_retry_count + 1}/{self._max_auth_retries}）を準備中...")
                    # 再帰的に再試行
                    return self._handle_auth_error(identifier, method_name, retry_func)
                else:
                    print(f"🚫 最大リトライ回数（{self._max_auth_retries}回）に達しました")
                    raise
            except Exception as e:
                print(f"❌ クッキー再読み込みエラー ({identifier}): {e}")
                print(f"📈 エラーにもかかわらず次のリトライを試行...")
                if self._auth_retry_count < self._max_auth_retries:
                    time.sleep(retry_delay)
                    return self._handle_auth_error(identifier, method_name, retry_func)
                else:
                    raise
                
        # 再試行回数を超えた場合
        print(f"\n🚫 認証エラー最終判定 ({identifier}): {self._max_auth_retries}回のリトライ後も認証失敗")
        print("📋 考えられる原因:")
        print("  1. Cookieファイルが完全に無効")
        print("  2. アカウント制限・停止")
        print("  3. Twitter API仕様変更")
        print("  4. ネットワーク接続問題")
        print("🔧 対処方法: 新しいCookieファイルの取得が必要です")
        self._auth_retry_count = 0  # カウンターをリセット
        raise SystemExit("Authentication failed - Cookie is invalid")
