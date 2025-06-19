#!/usr/bin/env python3
"""
Twitter一括ブロックツール - パッケージ実行エントリーポイント

python -m twitter_blocker で実行可能
"""

import argparse
import os
import sys

from . import BulkBlockManager
from .stats import show_stats


def main():
    parser = argparse.ArgumentParser(
        prog="python3 -m twitter_blocker", description="Twitter一括ブロックツール"
    )
    parser.add_argument(
        "--all", action="store_true", help="全ユーザーを処理（テストではなく本格実行）"
    )
    parser.add_argument(
        "--retry", action="store_true", help="失敗したユーザーのリトライ処理を実行"
    )
    parser.add_argument(
        "--reset-retry", action="store_true", help="失敗ユーザーのリトライ回数をリセット"
    )
    parser.add_argument(
        "--clear-errors", action="store_true", help="失敗ユーザーのエラーメッセージをクリア"
    )
    parser.add_argument(
        "--reset-failed", action="store_true", help="失敗ユーザーの状態を完全リセット（エラーメッセージ、リトライ回数、ステータス）"
    )
    parser.add_argument(
        "--auto-retry",
        action="store_true",
        help="--allと組み合わせて使用：実行後に自動でリトライ処理も実行",
    )
    parser.add_argument("--stats", action="store_true", help="現在の処理統計を表示")
    parser.add_argument("--debug-errors", action="store_true", help="失敗したエラーメッセージのサンプルを表示（デバッグ用）")
    parser.add_argument("--debug", action="store_true", help="デバッグモードで実行（詳細なAPI応答を表示）")
    parser.add_argument("--test-user", type=str, help="特定のユーザーのみテスト（デバッグ用）")
    parser.add_argument("--max-users", type=int, help="処理するユーザーの最大数")
    parser.add_argument(
        "--delay", type=float, default=1.0, help="リクエスト間隔（秒、デフォルト: 1.0）"
    )
    
    # 拡張ヘッダー関連オプション
    parser.add_argument(
        "--disable-header-enhancement", 
        action="store_true", 
        help="拡張ヘッダー生成を無効化（x-client-transaction-id等）"
    )
    parser.add_argument(
        "--enable-forwarded-for", 
        action="store_true", 
        help="x-xp-forwarded-forヘッダーの生成を有効化（試験的機能）"
    )

    # ファイルパス指定オプション
    parser.add_argument(
        "--cookies",
        type=str,
        default=os.getenv("TWITTER_COOKIES_PATH", "cookies.json"),
        help="クッキーファイルのパス（デフォルト: cookies.json、環境変数: TWITTER_COOKIES_PATH）",
    )
    parser.add_argument(
        "--users-file",
        type=str,
        default=os.getenv("TWITTER_USERS_FILE", "video_misuse_detecteds.json"),
        help="ブロック対象ユーザーファイルのパス（デフォルト: video_misuse_detecteds.json、環境変数: TWITTER_USERS_FILE）",
    )
    parser.add_argument(
        "--db",
        type=str,
        default=os.getenv("TWITTER_BLOCK_DB", "block_history.db"),
        help="ブロック履歴データベースのパス（デフォルト: block_history.db、環境変数: TWITTER_BLOCK_DB）",
    )
    parser.add_argument(
        "--cache-dir",
        type=str,
        default=os.getenv("CACHE_DIR", "/data/cache"),
        help="キャッシュディレクトリのパス（デフォルト: /data/cache、環境変数: CACHE_DIR）",
    )

    args = parser.parse_args()

    # ファイル存在チェック
    if not args.stats and not args.retry and not args.reset_retry and not args.clear_errors and not args.reset_failed and not args.debug_errors and not args.test_user:
        if not os.path.exists(args.cookies):
            print(f"❌ エラー: クッキーファイルが見つかりません: {args.cookies}")
            print("正しいパスを指定してください:")
            print(f"  --cookies /path/to/cookies.json")
            print(
                f"  または環境変数: export TWITTER_COOKIES_PATH=/path/to/cookies.json"
            )
            sys.exit(1)

        if not os.path.exists(args.users_file):
            print(f"❌ エラー: ユーザーファイルが見つかりません: {args.users_file}")
            print("正しいパスを指定してください:")
            print(f"  --users-file /path/to/users.json")
            print(f"  または環境変数: export TWITTER_USERS_FILE=/path/to/users.json")
            sys.exit(1)

    # パスの表示
    print(f"📁 使用ファイル:")
    print(f"  クッキー: {args.cookies}")
    print(f"  ユーザーリスト: {args.users_file}")
    print(f"  データベース: {args.db}")
    print()

    # 拡張ヘッダー設定の処理
    enable_header_enhancement = not args.disable_header_enhancement
    enable_forwarded_for = args.enable_forwarded_for
    
    if args.debug and enable_header_enhancement:
        print(f"🔧 拡張ヘッダー設定:")
        print(f"  ヘッダー拡張: {'有効' if enable_header_enhancement else '無効'}")
        print(f"  Forwarded-For: {'有効' if enable_forwarded_for else '無効'}")
        print()

    manager = BulkBlockManager(
        cookies_file=args.cookies, 
        users_file=args.users_file, 
        db_file=args.db, 
        cache_dir=args.cache_dir, 
        debug_mode=args.debug,
        enable_header_enhancement=enable_header_enhancement,
        enable_forwarded_for=enable_forwarded_for
    )

    # 統計表示
    if args.stats:
        show_stats(manager)
        return

    # エラーメッセージデバッグ表示
    if args.debug_errors:
        error_samples = manager.database.get_error_message_samples(20)
        print("=== エラーメッセージサンプル ===")
        for i, sample in enumerate(error_samples, 1):
            print(f"{i:2d}. {sample}")
        return

    # 特定ユーザーのテスト
    if args.test_user:
        print(f"=== テストユーザー: {args.test_user} ===")
        user_info = manager.api.get_user_info(args.test_user)
        if user_info:
            print(f"ユーザー情報取得成功:")
            print(f"  ID: {user_info.get('id')}")
            print(f"  名前: {user_info.get('name')}")
            print(f"  フォロー関係: {user_info.get('following', False)}")
            print(f"  フォロワー関係: {user_info.get('followed_by', False)}")
        else:
            print(f"ユーザー情報取得失敗")
        return

    # リトライ回数リセット処理
    if args.reset_retry:
        manager.reset_retry_counts()
        return

    # エラーメッセージクリア処理
    if args.clear_errors:
        affected = manager.database.clear_error_messages()
        print(f"✅ {affected}件のエラーメッセージをクリアしました")
        return

    # 失敗ユーザー完全リセット処理
    if args.reset_failed:
        affected = manager.database.reset_failed_users()
        print(f"✅ {affected}件の失敗ユーザーを完全リセットしました")
        print("  - エラーメッセージ: クリア")
        print("  - リトライ回数: 0")
        print("  - レスポンスコード: クリア")
        print("  - ユーザーステータス: クリア")
        return

    # リトライ処理
    if args.retry:
        manager.process_retries(max_retries=args.max_users)
        return

    # 現在の状況を表示
    show_stats(manager)

    remaining_count = len(manager.get_remaining_users())
    if remaining_count == 0:
        print("✓ 全てのユーザーが既に処理済みです")

        # リトライ候補をチェック
        retry_candidates = manager.get_retry_candidates()
        if retry_candidates:
            print(f"\nリトライ候補が {len(retry_candidates)}人 います")
            print("リトライ処理を実行: python3 -m twitter_blocker --retry")
        return

    # 実行確認
    if args.all:
        print(f"\n🔥 本格実行モード: {remaining_count}人を処理します")
        manager.process_bulk_block(max_users=args.max_users, delay=args.delay)

        # --auto-retryが指定されている場合は自動でリトライ処理も実行
        if args.auto_retry:
            print("\n" + "=" * 50)
            print("🔄 自動リトライ処理を開始します...")
            retry_candidates = manager.get_retry_candidates()
            if retry_candidates:
                manager.process_retries(max_retries=args.max_users)
            else:
                print("リトライ候補はありません")
    else:
        # テストモード（最初の5人のみ）
        max_test_users = min(5, remaining_count)
        print(f"\n🧪 テストモード: 最初の{max_test_users}人のみ処理します")
        print("本格実行する場合は: python3 -m twitter_blocker --all")
        print("自動リトライ付きの場合は: python3 -m twitter_blocker --all --auto-retry")

        manager.process_bulk_block(max_users=max_test_users, delay=args.delay)

    # 処理後の統計とリトライ候補チェック
    print("\n" + "=" * 50)
    show_stats(manager)

    if not args.auto_retry:  # 自動リトライを実行していない場合のみ表示
        retry_candidates = manager.get_retry_candidates()
        if retry_candidates:
            print(f"\nリトライ候補: {len(retry_candidates)}人")
            print("リトライ処理実行: python3 -m twitter_blocker --retry")
            print(
                "次回は自動リトライ付きで: python3 -m twitter_blocker --all --auto-retry"
            )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 処理が中断されました")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ エラーが発生しました: {e}")
        sys.exit(1)
