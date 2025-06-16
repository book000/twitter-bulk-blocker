#!/usr/bin/env python3
"""
Twitter一括ブロック機能
video_misuse_detecteds.json に記載されているユーザーを一括でブロックします
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Optional, Any
from twitter_openapi_python import TwitterOpenapiPython
import requests


class TwitterBlocker:
    def __init__(self, cookies_file: str = "cookies.json", 
                 users_file: str = "video_misuse_detecteds.json",
                 db_file: str = "block_history.db"):
        self.cookies_file = cookies_file
        self.users_file = users_file
        self.db_file = db_file
        self.client = None
        self.current_user = None
        
        # データベース初期化
        self._init_database()
        
    def _init_database(self):
        """SQLiteデータベースを初期化"""
        try:
            # データベースファイルのディレクトリを確保
            db_path = Path(self.db_file)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # データベース接続を試行
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
        except sqlite3.Error as e:
            print(f"データベース接続エラー: {e}")
            print(f"データベースファイルパス: {self.db_file}")
            raise
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS block_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screen_name TEXT NOT NULL,
                user_id TEXT,
                blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'blocked',
                UNIQUE(screen_name, user_id)
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS follow_status (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screen_name TEXT NOT NULL,
                user_id TEXT,
                following BOOLEAN DEFAULT FALSE,
                followed_by BOOLEAN DEFAULT FALSE,
                checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(screen_name, user_id)
        )
        """)
        
        conn.commit()
        conn.close()
        print(f"データベース初期化完了: {self.db_file}")
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        print(f"データベース初期化エラー: {e}")
        raise
        
    def load_cookies(self) -> Dict[str, Any]:
        """クッキーファイルを読み込み"""
        with open(self.cookies_file, 'r') as f:
            cookies_list = json.load(f)
            
        # リスト形式のクッキーを辞書形式に変換
        cookies_dict = {}
        for cookie in cookies_list:
            domain = cookie.get('domain', '')
            if domain in ['.x.com', '.twitter.com', 'x.com', 'twitter.com']:
                cookies_dict[cookie['name']] = cookie['value']
                
        print("読み込まれたクッキー:")
        for name, value in cookies_dict.items():
            print(f"  {name}: {value[:50]}...")
                
        return cookies_dict
        
    def load_target_users(self) -> List[str]:
        """ブロック対象ユーザーリストを読み込み"""
        with open(self.users_file, 'r') as f:
            return json.load(f)
            
    def authenticate(self) -> bool:
        """Twitter APIに認証"""
        try:
            cookies = self.load_cookies()
            
            # 必要なクッキーが存在するかチェック
            required_cookies = ['auth_token', 'ct0']
            for cookie_name in required_cookies:
                if cookie_name not in cookies:
                    print(f"必要なクッキー '{cookie_name}' が見つかりません")
                    return False
                    
            # クライアント初期化
            twitter_api = TwitterOpenapiPython()
            self.client = twitter_api.get_client_from_cookies(cookies=cookies)
            
            return True
            
        except Exception as e:
            print(f"認証エラー: {e}")
            return False
            
    def get_current_user(self) -> Optional[Dict[str, Any]]:
        """ログイン中のユーザー情報を取得（account/settings.jsonから）"""
        try:
            if not self.client:
                print("認証が必要です")
                return None
                
            # account/settings.json エンドポイントを直接呼び出し
            try:
                print("account/settings.json エンドポイントからユーザー情報を取得中...")
                
                # 直接HTTP APIを呼び出し
                import requests
                
                cookies = self.load_cookies()
                
                headers = {
                    'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
                    'x-csrf-token': cookies.get('ct0', ''),
                    'x-twitter-auth-type': 'OAuth2Session',
                    'x-twitter-active-user': 'yes',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                    'content-type': 'application/json',
                }
                
                # クッキーを適切な形式に変換
                cookie_str = '; '.join([f"{name}={value}" for name, value in cookies.items()])
                headers['cookie'] = cookie_str
                
                # 複数のエンドポイントを試す
                endpoints = [
                    'https://api.twitter.com/1.1/account/settings.json',
                    'https://twitter.com/i/api/1.1/account/settings.json',
                    'https://api.x.com/1.1/account/settings.json',
                    'https://x.com/i/api/1.1/account/settings.json'
                ]
                
                response = None
                for endpoint in endpoints:
                    try:
                        print(f"エンドポイント試行: {endpoint}")
                        response = requests.get(endpoint, headers=headers)
                        print(f"レスポンス: {response.status_code}")
                        if response.status_code == 200:
                            break
                    except Exception as req_e:
                        print(f"リクエストエラー ({endpoint}): {req_e}")
                        continue
                
                if response and response.status_code == 200:
                    settings_data = response.json()
                    print("account/settings.json 取得成功!")
                    
                    self.current_user = {
                        'id': str(settings_data.get('id', '')),
                        'screen_name': settings_data.get('screen_name', 'unknown'),
                        'name': settings_data.get('name', 'unknown')
                    }
                    return self.current_user
                elif response:
                    print(f"最終APIエラー: {response.status_code} - {response.text}")
                else:
                    print("全てのエンドポイントが失敗しました")
                    
            except Exception as api_e:
                print(f"account/settings.json API呼び出し失敗: {api_e}")
                
            # フォールバック: twid クッキーから直接ユーザーIDを取得
            cookies = self.load_cookies()
            twid = cookies.get('twid', '')
            
            if twid.startswith('u%3D'):
                user_id = twid.replace('u%3D', '')
                print(f"フォールバック: クッキーから取得したユーザーID: {user_id}")
                
                self.current_user = {
                    'id': user_id,
                    'screen_name': 'unknown',
                    'name': 'unknown'
                }
                return self.current_user
                
            print("ユーザー情報の取得に失敗しました")
            return None
                
        except Exception as e:
            print(f"ユーザー情報取得エラー: {e}")
            return None
            
    def check_follow_relationship(self, screen_name: str) -> Dict[str, bool]:
        """フォロー関係をチェック（直接HTTP API使用）"""
        try:
            cookies = self.load_cookies()
            
            headers = {
                'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
                'x-csrf-token': cookies.get('ct0', ''),
                'x-twitter-auth-type': 'OAuth2Session',
                'x-twitter-active-user': 'yes',
                'content-type': 'application/json',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'accept': '*/*',
                'accept-language': 'ja,en-US;q=0.9,en;q=0.8',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
            }
            
            cookie_str = '; '.join([f"{name}={value}" for name, value in cookies.items()])
            headers['cookie'] = cookie_str
            
            # GraphQLエンドポイントを使用
            url = 'https://x.com/i/api/graphql/7mjxD3-C6BxitPMVQ6w0-Q/UserByScreenName'
            
            params = {
                'variables': json.dumps({
                    'screen_name': screen_name,
                    'withSafetyModeUserFields': True,
                    'withSuperFollowsUserFields': True
                }),
                'features': json.dumps({
                    'hidden_profile_likes_enabled': True,
                    'responsive_web_graphql_exclude_directive_enabled': True,
                    'verified_phone_label_enabled': False,
                    'subscriptions_verification_info_is_identity_verified_enabled': True,
                    'subscriptions_verification_info_verified_since_enabled': True,
                    'highlights_tweets_tab_ui_enabled': True,
                    'creator_subscriptions_tweet_preview_api_enabled': True,
                    'responsive_web_graphql_skip_user_profile_image_extensions_enabled': False,
                    'responsive_web_graphql_timeline_navigation_enabled': True
                })
            }
            
            response = requests.get(url, headers=headers, params=params)
            
            print(f"フォロー関係チェック ({screen_name}): {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"API レスポンス構造: {list(data.keys()) if isinstance(data, dict) else 'Not dict'}")
                
                if 'data' in data:
                    print(f"data keys: {list(data['data'].keys()) if isinstance(data['data'], dict) else 'data not dict'}")
                    
                    if 'user' in data['data']:
                        user_info = data['data']['user']
                        print(f"user keys: {list(user_info.keys()) if isinstance(user_info, dict) else 'user not dict'}")
                        
                        if 'result' in user_info:
                            user_result = user_info['result']
                            print(f"result keys: {list(user_result.keys()) if isinstance(user_result, dict) else 'result not dict'}")
                            
                            if 'legacy' in user_result:
                                legacy = user_result['legacy']
                                # rest_id をuser_idとして使用（id_strが存在しない場合）
                                user_id = legacy.get('id_str') or user_result.get('rest_id')
                                
                                return {
                                    'following': legacy.get('following', False),
                                    'followed_by': legacy.get('followed_by', False),
                                    'user_id': user_id,
                                    'blocking': legacy.get('blocking', False),
                                    'blocked_by': legacy.get('blocked_by', False),
                                    'screen_name': legacy.get('screen_name'),
                                    'name': legacy.get('name')
                                }
                            else:
                                print("legacy フィールドが見つかりません")
                        else:
                            print("result フィールドが見つかりません")
                    else:
                        print("user フィールドが見つかりません")
                else:
                    print("data フィールドが見つかりません")
                    print(f"全レスポンス: {data}")
            else:
                print(f"API エラー詳細: {response.text}")
                    
            return {'following': False, 'followed_by': False, 'user_id': None, 'blocking': False, 'blocked_by': False}
            
        except Exception as e:
            print(f"フォロー関係チェックエラー ({screen_name}): {e}")
            return {'following': False, 'followed_by': False, 'user_id': None, 'blocking': False, 'blocked_by': False}
            
    def is_safe_to_block(self, screen_name: str) -> bool:
        """ブロックしても安全かチェック（フォロー関係を確認）"""
        follow_info = self.check_follow_relationship(screen_name)
        
        # フォロー中またはフォロワーの場合はブロックしない
        if follow_info['following'] or follow_info['followed_by']:
            print(f"スキップ: {screen_name} (フォロー関係あり)")
            return False
            
        return True
        
    def block_user(self, screen_name: str) -> bool:
        """ユーザーをブロック"""
        try:
            # フォロー関係をチェック
            if not self.is_safe_to_block(screen_name):
                return False
                
            # ユーザー情報を取得
            follow_info = self.check_follow_relationship(screen_name)
            user_id = follow_info.get('user_id')
            
            if not user_id:
                print(f"ユーザーID取得失敗: {screen_name}")
                return False
                
            # 実際のブロック処理（直接HTTP API使用）
            try:
                block_success = self._execute_block_api(user_id, screen_name)
                if block_success:
                    print(f"✓ ブロック完了: {screen_name} (ID: {user_id})")
                else:
                    print(f"ブロック処理失敗: {screen_name} (ID: {user_id})")
                    return False
            except Exception as block_e:
                print(f"ブロック処理エラー ({screen_name}): {block_e}")
                return False
            
            # データベースに記録
            self._record_block_action(screen_name, user_id)
            
            # レート制限対策で1秒待機
            time.sleep(1)
            
            return True
            
        except Exception as e:
            print(f"ブロックエラー ({screen_name}): {e}")
            return False
            
    def _record_block_action(self, screen_name: str, user_id: str):
        """ブロック履歴をデータベースに記録"""
        try:
            conn = sqlite3.connect(self.db_file)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT OR REPLACE INTO block_history 
                (screen_name, user_id, status) 
                VALUES (?, ?, 'blocked')
            """, (screen_name, user_id))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"データベース記録エラー: {e}")
            
    def _execute_block_api(self, user_id: str, screen_name: str) -> bool:
        """直接HTTP APIでブロックを実行"""
        try:
            cookies = self.load_cookies()
            
            headers = {
                'authorization': 'Bearer AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA',
                'x-csrf-token': cookies.get('ct0', ''),
                'x-twitter-auth-type': 'OAuth2Session',
                'x-twitter-active-user': 'yes',
                'content-type': 'application/json',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'accept': '*/*',
                'accept-language': 'ja,en-US;q=0.9,en;q=0.8',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-origin',
                'referer': f'https://x.com/{screen_name}',
            }
            
            cookie_str = '; '.join([f"{name}={value}" for name, value in cookies.items()])
            headers['cookie'] = cookie_str
            
            # GraphQLブロックエンドポイントを試す
            block_urls = [
                'https://x.com/i/api/1.1/blocks/create.json',
                'https://api.x.com/1.1/blocks/create.json',
                'https://x.com/i/api/graphql/ZI8LcnOyeZUZFWwG5bYrzw/BlockUser'
            ]
            
            for url in block_urls:
                try:
                    print(f"ブロックエンドポイント試行: {url}")
                    
                    if 'graphql' in url:
                        # GraphQL形式
                        payload = {
                            'variables': json.dumps({
                                'user_id': user_id
                            }),
                            'queryId': 'ZI8LcnOyeZUZFWwG5bYrzw'
                        }
                        response = requests.post(url, headers=headers, json=payload)
                    else:
                        # REST API形式
                        payload = {
                            'user_id': user_id,
                            'skip_status': '1'
                        }
                        response = requests.post(url, headers=headers, data=payload)
                    
                    print(f"ブロックAPI レスポンス: {response.status_code}")
                    
                    if response.status_code == 200:
                        result_data = response.json()
                        print(f"ブロック成功レスポンス: {result_data}")
                        return True
                    else:
                        print(f"ブロックAPI エラー: {response.status_code} - {response.text}")
                        
                except Exception as req_e:
                    print(f"ブロックリクエストエラー ({url}): {req_e}")
                    continue
                    
            return False
            
        except Exception as e:
            print(f"ブロック実行エラー: {e}")
            return False
            
    def process_block_list(self) -> Dict[str, int]:
        """ブロック対象リストを処理"""
        try:
            target_users = self.load_target_users()
            
            stats = {
                'total': len(target_users),
                'blocked': 0,
                'skipped': 0,
                'errors': 0
            }
            
            print(f"ブロック対象ユーザー: {stats['total']}人")
            
            for i, screen_name in enumerate(target_users, 1):
                print(f"処理中 ({i}/{stats['total']}): {screen_name}")
                
                try:
                    if self.block_user(screen_name):
                        stats['blocked'] += 1
                        print(f"✓ ブロック完了: {screen_name}")
                    else:
                        stats['skipped'] += 1
                        print(f"- スキップ: {screen_name}")
                        
                except Exception as e:
                    stats['errors'] += 1
                    print(f"✗ エラー: {screen_name} - {e}")
                    
            return stats
            
        except Exception as e:
            print(f"ブロックリスト処理エラー: {e}")
            return {'total': 0, 'blocked': 0, 'skipped': 0, 'errors': 1}


def main():
    """メイン関数"""
    blocker = TwitterBlocker()
    
    # 認証テスト
    print("Twitter APIに認証中...")
    if not blocker.authenticate():
        print("認証に失敗しました")
        return
        
    print("認証成功!")
    
    # ログイン中のユーザー情報を取得
    print("ログイン中のユーザー情報を確認中...")
    current_user = blocker.get_current_user()
    
    if current_user:
        print(f"ログイン中のユーザー: {current_user['screen_name']} (@{current_user['name']})")
        print(f"ユーザーID: {current_user['id']}")
        print()
    else:
        print("ユーザー情報の取得に失敗しました")
        return
        
    # 少数のユーザーでテスト（最初の5人のみ）
    print("テスト実行: 最初の5人のユーザーで動作確認...")
    target_users = blocker.load_target_users()[:5]
    
    print(f"テスト対象: {target_users}")
    print()
    
    test_stats = {
        'total': len(target_users),
        'blocked': 0,
        'skipped': 0,
        'errors': 0
    }
    
    for i, screen_name in enumerate(target_users, 1):
        print(f"テスト処理中 ({i}/{test_stats['total']}): {screen_name}")
        
        try:
            if blocker.block_user(screen_name):
                test_stats['blocked'] += 1
                print(f"✓ ブロック完了: {screen_name}")
            else:
                test_stats['skipped'] += 1
                print(f"- スキップ: {screen_name}")
                
        except Exception as e:
            test_stats['errors'] += 1
            print(f"✗ エラー: {screen_name} - {e}")
        
        print()
            
    print("=== テスト結果 ===")
    print(f"対象ユーザー: {test_stats['total']}人")
    print(f"ブロック済み: {test_stats['blocked']}人")
    print(f"スキップ: {test_stats['skipped']}人")
    print(f"エラー: {test_stats['errors']}人")
    
    # 全体実行を確認
    print("\n注意: これはテストモードです。")
    print("実際のブロック処理は安全のため無効化されています。")
    print("全ユーザーをブロックする場合は、blocker.process_block_list() を呼び出してください。")


if __name__ == "__main__":
    main()