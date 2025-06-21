#!/usr/bin/env python3
"""
バージョン管理システムのテストスクリプト

このスクリプトは以下をテストします:
- 静的バージョン情報の取得
- Git情報の取得
- Docker環境変数の認識
- GitHub Actions環境変数の認識
- 実効バージョンの優先順位
"""

import os
import sys

# パスを追加してtwitter_blockerをインポート可能にする
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import twitter_blocker.version as version_module
except ImportError as e:
    print(f"❌ Failed to import version module: {e}")
    sys.exit(1)


def test_basic_version_info():
    """基本バージョン情報のテスト"""
    print("=== 基本バージョン情報テスト ===")
    
    try:
        # 静的バージョン
        static_version = version_module.__version__
        print(f"✅ Static version: {static_version}")
        
        # 基本バージョン文字列
        version_string = version_module.get_version_string()
        print(f"✅ Basic version string: {version_string}")
        
        # 詳細バージョン文字列
        detailed_string = version_module.get_version_string(detailed=True)
        print(f"✅ Detailed version string: {detailed_string}")
        
        return True
    except Exception as e:
        print(f"❌ Basic version test failed: {e}")
        return False


def test_git_info():
    """Git情報のテスト"""
    print("\n=== Git情報テスト ===")
    
    try:
        git_info = version_module.get_git_info()
        print(f"✅ Git info retrieved: {len(git_info)} fields")
        
        for key, value in git_info.items():
            if value:
                print(f"  - {key}: {value}")
            else:
                print(f"  - {key}: (not available)")
        
        return True
    except Exception as e:
        print(f"❌ Git info test failed: {e}")
        return False


def test_docker_info():
    """Docker環境情報のテスト"""
    print("\n=== Docker環境情報テスト ===")
    
    try:
        docker_info = version_module.get_docker_info()
        print(f"✅ Docker info retrieved: {len(docker_info)} fields")
        
        has_docker_env = any(v and v != "unknown" for v in docker_info.values())
        if has_docker_env:
            print("🐳 Docker environment detected:")
            for key, value in docker_info.items():
                if value and value != "unknown":
                    print(f"  - {key}: {value}")
        else:
            print("ℹ️ Not running in Docker environment")
        
        return True
    except Exception as e:
        print(f"❌ Docker info test failed: {e}")
        return False


def test_github_actions_info():
    """GitHub Actions環境情報のテスト"""
    print("\n=== GitHub Actions環境情報テスト ===")
    
    try:
        github_info = version_module.get_github_actions_info()
        print(f"✅ GitHub Actions info retrieved: {len(github_info)} fields")
        
        has_github_env = any(github_info.values())
        if has_github_env:
            print("🔧 GitHub Actions environment detected:")
            for key, value in github_info.items():
                if value:
                    print(f"  - {key}: {value}")
        else:
            print("ℹ️ Not running in GitHub Actions environment")
        
        return True
    except Exception as e:
        print(f"❌ GitHub Actions info test failed: {e}")
        return False


def test_effective_version():
    """実効バージョンのテスト"""
    print("\n=== 実効バージョンテスト ===")
    
    try:
        effective_version = version_module.get_effective_version()
        static_version = version_module.__version__
        
        print(f"✅ Effective version: {effective_version}")
        print(f"✅ Static version: {static_version}")
        
        if effective_version != static_version:
            print("🔄 Version override detected (Docker/GitHub Actions/Git)")
        else:
            print("📋 Using static version")
        
        return True
    except Exception as e:
        print(f"❌ Effective version test failed: {e}")
        return False


def test_version_priority():
    """バージョン優先順位のテスト"""
    print("\n=== バージョン優先順位テスト ===")
    
    try:
        # 各環境の情報を取得
        docker_info = version_module.get_docker_info()
        github_info = version_module.get_github_actions_info()
        package_version = version_module.get_package_json_version()
        git_info = version_module.get_git_info()
        static_version = version_module.__version__
        
        priority_source = "static"
        
        # 優先順位の判定
        if docker_info.get("version") and docker_info["version"] != "unknown":
            priority_source = "docker"
        elif github_info.get("version"):
            priority_source = "github_actions"
        elif package_version and package_version != static_version:
            priority_source = "package_json_ci"
        elif git_info.get("tag"):
            priority_source = "git_tag"
        elif git_info.get("commit_short"):
            priority_source = "git_commit"
        
        print(f"✅ Version source priority: {priority_source}")
        
        # 優先順位の説明
        print("📚 Priority order:")
        print("  1. Docker environment variables (highest)")
        print("  2. GitHub Actions environment variables")
        print("  3. package.json (updated by CI/CD)")
        print("  4. Git tags")
        print("  5. Git commit info + static version")
        print("  6. Static version only (lowest)")
        
        return True
    except Exception as e:
        print(f"❌ Version priority test failed: {e}")
        return False


def test_package_json_info():
    """パッケージJSON情報のテスト"""
    print("\n=== パッケージJSON情報テスト ===")
    
    try:
        package_version = version_module.get_package_json_version()
        print(f"✅ Package.json version: {package_version or 'not found'}")
        
        if package_version:
            static_version = version_module.__version__
            if package_version != static_version:
                print(f"🔄 Version mismatch detected:")
                print(f"  - Static: {static_version}")
                print(f"  - Package.json: {package_version}")
                print(f"  - This indicates CI/CD updated package.json")
            else:
                print(f"📋 Versions match - no CI/CD update yet")
        else:
            print(f"⚠️ package.json not found or no version field")
        
        return True
    except Exception as e:
        print(f"❌ Package.json info test failed: {e}")
        return False


def test_full_version_info():
    """完全バージョン情報のテスト"""
    print("\n=== 完全バージョン情報テスト ===")
    
    try:
        full_info = version_module.get_version_info(
            include_git=True,
            include_system=True,
            include_docker=True,
            include_github=True,
            include_package=True
        )
        
        print(f"✅ Full version info retrieved: {len(full_info)} top-level fields")
        
        for key, value in full_info.items():
            if isinstance(value, dict):
                print(f"  - {key}: {len(value)} sub-fields")
                for sub_key, sub_value in value.items():
                    if sub_value:
                        # 長い値は切り詰める
                        display_value = str(sub_value)
                        if len(display_value) > 50:
                            display_value = display_value[:47] + "..."
                        print(f"    • {sub_key}: {display_value}")
            else:
                print(f"  - {key}: {value}")
        
        return True
    except Exception as e:
        print(f"❌ Full version info test failed: {e}")
        return False


def simulate_environments():
    """環境変数を設定してのシミュレーションテスト"""
    print("\n=== 環境シミュレーションテスト ===")
    
    # 元の環境変数を保存
    original_env = {}
    test_vars = [
        "DOCKER_VERSION", "DOCKER_BUILD_DATE", "DOCKER_COMMIT_SHA", "DOCKER_COMMIT_SHORT",
        "GITHUB_RELEASE_VERSION", "GITHUB_REF", "GITHUB_SHA", "GITHUB_REPOSITORY"
    ]
    
    for var in test_vars:
        original_env[var] = os.environ.get(var)
    
    try:
        # Dockerシミュレーション
        print("\n--- Docker環境シミュレーション ---")
        os.environ["DOCKER_VERSION"] = "1.2.3-test"
        os.environ["DOCKER_BUILD_DATE"] = "2025-01-01T00:00:00Z"
        os.environ["DOCKER_COMMIT_SHA"] = "abcd1234" * 8
        os.environ["DOCKER_COMMIT_SHORT"] = "abcd1234"
        
        docker_effective = version_module.get_effective_version()
        print(f"✅ Docker simulated effective version: {docker_effective}")
        
        # GitHub Actionsシミュレーション（Dockerをクリア）
        print("\n--- GitHub Actions環境シミュレーション ---")
        os.environ["DOCKER_VERSION"] = "unknown"  # Dockerを無効化
        os.environ["GITHUB_RELEASE_VERSION"] = "2.3.4-test"
        os.environ["GITHUB_REF"] = "refs/heads/main"
        os.environ["GITHUB_SHA"] = "efgh5678" * 8
        os.environ["GITHUB_REPOSITORY"] = "test/twitter-bulk-blocker"
        
        github_effective = version_module.get_effective_version()
        print(f"✅ GitHub Actions simulated effective version: {github_effective}")
        
        # package.jsonシミュレーション（既存ファイルを使用）
        print("\n--- package.jsonシミュレーション ---")
        # GitHub Actionsを無効化
        os.environ["GITHUB_RELEASE_VERSION"] = ""
        
        package_effective = version_module.get_effective_version()
        print(f"✅ package.json simulated effective version: {package_effective}")
        
        # package.jsonのバージョン表示
        package_version = version_module.get_package_json_version()
        if package_version:
            print(f"📎 package.json version: {package_version}")
        
        return True
        
    except Exception as e:
        print(f"❌ Environment simulation test failed: {e}")
        return False
    
    finally:
        # 元の環境変数を復元
        for var, value in original_env.items():
            if value is None:
                os.environ.pop(var, None)
            else:
                os.environ[var] = value


def main():
    """メインテスト実行"""
    print("🧪 Twitter Bulk Blocker バージョン管理システムテスト")
    print("=" * 60)
    
    tests = [
        ("基本バージョン情報", test_basic_version_info),
        ("Git情報", test_git_info),
        ("Docker環境情報", test_docker_info),
        ("GitHub Actions環境情報", test_github_actions_info),
        ("package.json情報", test_package_json_info),
        ("実効バージョン", test_effective_version),
        ("バージョン優先順位", test_version_priority),
        ("完全バージョン情報", test_full_version_info),
        ("環境シミュレーション", simulate_environments),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ Test '{test_name}' crashed: {e}")
            results[test_name] = False
    
    # 結果サマリー
    print("\n" + "=" * 60)
    print("📊 テスト結果サマリー")
    print("=" * 60)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print(f"\n🎯 Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())