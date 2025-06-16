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
        "--auto-retry",
        action="store_true",
        help="--allと組み合わせて使用：実行後に自動でリトライ処理も実行",
    )
    parser.add_argument("--stats", action="store_true", help="現在の処理統計を表示")
    parser.add_argument("--max-users", type=int, help="処理するユーザーの最大数")
    parser.add_argument(
        "--delay", type=float, default=1.0, help="リクエスト間隔（秒、デフォルト: 1.0）"
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

    args = parser.parse_args()

    # ファイル存在チェック
    if not args.stats and not args.retry:
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

    manager = BulkBlockManager(
        cookies_file=args.cookies, users_file=args.users_file, db_file=args.db
    )

    # 統計表示
    if args.stats:
        show_stats(manager)
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
