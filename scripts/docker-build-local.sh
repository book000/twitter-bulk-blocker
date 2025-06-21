#!/bin/bash
set -euo pipefail

# Twitter Bulk Blocker - ローカル Docker ビルドスクリプト
# GitHub Actions と同じビルドプロセスをローカルで実行

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "🐳 Twitter Bulk Blocker - ローカル Docker ビルド"
echo "================================================"

cd "$PROJECT_DIR"

# Git情報の取得
echo "📋 Git情報を取得中..."
COMMIT_SHA=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
COMMIT_SHORT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
TAG=$(git describe --tags --exact-match 2>/dev/null || echo "")
DIRTY=$(if [ -n "$(git status --porcelain 2>/dev/null)" ]; then echo "true"; else echo "false"; fi)

echo "  • Commit SHA: $COMMIT_SHA"
echo "  • Commit Short: $COMMIT_SHORT"
echo "  • Branch: $BRANCH"
echo "  • Tag: $TAG"
echo "  • Dirty: $DIRTY"

# バージョン情報の取得
echo "📦 バージョン情報を取得中..."
VERSION=$(python3 -c "
import sys
sys.path.insert(0, 'twitter_blocker')
import version as v
git_info = v.get_git_info()
base_version = v.__version__

if git_info.get('tag'):
    # タグがある場合はタグを使用（v プレフィックスを除去）
    tag = git_info['tag']
    if tag.startswith('v'):
        version = tag[1:]
    else:
        version = tag
elif git_info.get('commit_short'):
    # コミット情報がある場合
    version = f'{base_version}-{git_info[\"commit_short\"]}'
    if git_info.get('dirty'):
        version += '-dirty'
else:
    version = base_version

print(version)
")

BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "  • Version: $VERSION"
echo "  • Build Date: $BUILD_DATE"

# Docker イメージ名の設定
IMAGE_NAME="twitter-bulk-blocker"
IMAGE_TAG="$VERSION"
if [ "$DIRTY" = "true" ]; then
    IMAGE_TAG="$IMAGE_TAG-dirty"
fi

echo "🏗️ Docker イメージをビルド中..."
echo "  • Image: $IMAGE_NAME:$IMAGE_TAG"

# Docker ビルド実行
docker build \
    --build-arg VERSION="$VERSION" \
    --build-arg BUILD_DATE="$BUILD_DATE" \
    --build-arg COMMIT_SHA="$COMMIT_SHA" \
    --build-arg COMMIT_SHORT="$COMMIT_SHORT" \
    --tag "$IMAGE_NAME:$IMAGE_TAG" \
    --tag "$IMAGE_NAME:latest" \
    .

echo "✅ Docker ビルド完了!"

# ビルド結果の確認
echo ""
echo "🔍 ビルド結果:"
docker images "$IMAGE_NAME" --format "table {{.Repository}}:{{.Tag}}\t{{.Size}}\t{{.CreatedAt}}"

echo ""
echo "🧪 イメージテスト:"

# バージョン情報のテスト
echo "--- バージョン情報 ---"
docker run --rm "$IMAGE_NAME:$IMAGE_TAG" --version || echo "⚠️ バージョンコマンドが失敗しました"

echo ""
echo "--- ヘルプ情報 ---"
timeout 10 docker run --rm "$IMAGE_NAME:$IMAGE_TAG" --help || echo "⚠️ ヘルプコマンドが失敗またはタイムアウトしました"

echo ""
echo "--- イメージメタデータ ---"
docker inspect "$IMAGE_NAME:$IMAGE_TAG" --format='{{json .Config.Labels}}' | jq . 2>/dev/null || echo "⚠️ メタデータの表示に失敗しました"

echo ""
echo "🎉 ローカル Docker ビルドが完了しました!"
echo ""
echo "📦 実行コマンド例:"
echo "  docker run --rm -v \$(pwd)/data:/app/data $IMAGE_NAME:$IMAGE_TAG --help"
echo "  docker run --rm -v \$(pwd)/data:/app/data $IMAGE_NAME:$IMAGE_TAG --version"
echo ""
echo "🧹 イメージ削除コマンド:"
echo "  docker rmi $IMAGE_NAME:$IMAGE_TAG $IMAGE_NAME:latest"