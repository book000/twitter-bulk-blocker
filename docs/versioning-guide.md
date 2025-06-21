# バージョン管理ガイド

Twitter Bulk BlockerのGitHub Actions自動バージョン管理システムの使用方法。

## 🚀 概要

このプロジェクトでは以下の自動バージョン管理システムが実装されています：

- **Semantic Versioning (SemVer)** 準拠
- **Conventional Commits** に基づく自動バージョンバンプ
- **GitHub Actions** による自動リリース作成
- **Docker Image** の自動ビルド・タグ付け
- **マルチ環境対応**（開発・Docker・CI/CD）

## 📦 バージョン決定の優先順位

| 優先度 | 環境 | 条件 | 例 |
|--------|------|------|-----|
| 1 | Docker | `DOCKER_VERSION` 環境変数が設定 | `1.2.3` |
| 2 | GitHub Actions | `GITHUB_RELEASE_VERSION` 環境変数が設定 | `2.3.4` |
| 3 | **package.json (CI更新)** | CI/CDによって更新されたpackage.json | `1.5.0` |
| 4 | Git Tag | リポジトリにタグが付いている | `v1.0.0` → `1.0.0` |
| 5 | Git Commit | コミット情報 + 静的バージョン | `0.28.1-abc123ef` |
| 6 | Static | `version.py` の `__version__` | `0.28.1` |

### 🔧 reusable workflow統合

本プロジェクトは [book000/templates](https://github.com/book000/templates) の `reusable-docker.yml` ワークフローと統合されており：

- **mathieudutour/github-tag-action@v6.2** による自動バージョン計算
- **package.json の自動更新** (sed コマンドによる)
- **Docker build時のバージョン埋め込み** (BUILD_ARGS経由)
- **GitHub Release の自動作成**

## 🔄 自動リリースプロセス

### 1. コミットメッセージの作成

Conventional Commitsフォーマットに従ってコミットメッセージを作成：

```bash
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### 2. バージョンバンプのルール

| コミットタイプ | バージョンバンプ | 例 |
|----------------|------------------|-----|
| `feat:` | minor | `1.0.0` → `1.1.0` |
| `fix:` | patch | `1.0.0` → `1.0.1` |
| `perf:` | patch | `1.0.0` → `1.0.1` |
| `refactor:` | patch | `1.0.0` → `1.0.1` |
| `build:` | patch | `1.0.0` → `1.0.1` |
| `revert:` | patch | `1.0.0` → `1.0.1` |
| BREAKING CHANGE | major | `1.0.0` → `2.0.0` |
| `docs:`, `style:`, `test:`, `ci:`, `chore:` | リリースなし | - |

### 3. 実際のコミット例

#### 新機能追加（minor）
```bash
git commit -m "feat: API呼び出し時の動的ヘッダー生成機能を追加

Twitter/Xのアンチボットシステム対応のため、x-client-transaction-id等の
動的ヘッダーを自動生成する機能を実装。

Closes #38"
```

#### バグ修正（patch）
```bash
git commit -m "fix: 永続的失敗ユーザーのキャッシュ処理を修正

suspended/not_found/deactivatedユーザーのキャッシュが正しく
機能していない問題を修正。"
```

#### 破壊的変更（major）
```bash
git commit -m "feat!: API設定ファイル形式をYAMLに変更

BREAKING CHANGE: 設定ファイルの形式をJSONからYAMLに変更。
既存のcookies.jsonをcookies.ymlに移行する必要があります。"
```

## 🏗️ GitHub Actions ワークフロー

### ワークフロー概要

1. **テスト実行** - Python構文チェック・バージョンモジュールテスト
2. **Semantic Release** - 新しいリリースバージョンの決定・タグ作成
3. **Docker Build** - マルチアーキテクチャ対応イメージの自動ビルド
4. **バージョンファイル更新**（オプション） - `version.py`の更新

### トリガー条件

- `master`または`main`ブランチへのプッシュ
- Pull Requestの作成・更新（Docker buildのみ）

### 実行環境

- **Semantic Release**: Node.js 20
- **Docker Build**: Docker Buildx（linux/amd64, linux/arm64）
- **テスト**: Python 3.13

## 🐳 Docker バージョン管理

### イメージタグ戦略

| 状況 | タグ例 | 説明 |
|------|--------|------|
| リリース | `1.2.3`, `latest` | 正式リリース |
| PR | `pr-123` | Pull Request #123のテストビルド |
| 開発 | `0.28.1-abc123ef-dirty` | 開発環境（未コミット変更あり） |

### 環境変数

Docker実行時に自動設定される環境変数：

```bash
DOCKER_VERSION=1.2.3
DOCKER_BUILD_DATE=2025-06-21T19:12:57Z
DOCKER_COMMIT_SHA=51e66dbebe0e8c53a605cdfb367ed99e30f0fe21
DOCKER_COMMIT_SHORT=51e66db
```

### Docker画像の取得

```bash
# 最新リリース
docker pull ghcr.io/your-org/twitter-bulk-blocker:latest

# 特定バージョン
docker pull ghcr.io/your-org/twitter-bulk-blocker:1.2.3

# バージョン確認
docker run --rm ghcr.io/your-org/twitter-bulk-blocker:latest --version
```

## 🛠️ 開発環境での使用

### ローカルでのバージョン確認

```bash
# 基本バージョン情報
python3 -m twitter_blocker --version

# 詳細バージョン情報（Git・システム情報含む）
python3 -c "
import twitter_blocker.version as v
v.print_version_info(detailed=True)
"

# バージョン管理システムのテスト
python3 scripts/test-version.py
```

### ローカルDockerビルド

```bash
# 自動バージョン付きビルド
./scripts/docker-build-local.sh

# 手動バージョン指定
docker build \
  --build-arg VERSION=1.2.3-dev \
  --build-arg BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --build-arg COMMIT_SHA=$(git rev-parse HEAD) \
  --build-arg COMMIT_SHORT=$(git rev-parse --short HEAD) \
  -t twitter-bulk-blocker:dev .
```

## 📊 バージョン情報API

### Python API

```python
import twitter_blocker.version as version

# 基本情報
print(version.__version__)  # "0.28.1"
print(version.get_effective_version())  # "1.2.3" (実効バージョン)

# 詳細情報
info = version.get_version_info(
    include_git=True,
    include_docker=True, 
    include_github=True,
    include_system=True
)

# バージョン文字列
simple = version.get_version_string()  # "Twitter Bulk Blocker v1.2.3"
detailed = version.get_version_string(detailed=True)  # 詳細情報付き
```

### 環境情報の取得

```python
# Git情報
git_info = version.get_git_info()
print(git_info['commit_hash'])  # フルハッシュ
print(git_info['commit_short'])  # 短縮ハッシュ
print(git_info['branch'])  # ブランチ名
print(git_info['dirty'])  # 未コミット変更の有無

# Docker情報
docker_info = version.get_docker_info()
print(docker_info['version'])  # Docker環境でのバージョン

# GitHub Actions情報
github_info = version.get_github_actions_info()
print(github_info['version'])  # GitHub Actionsでのリリースバージョン
```

## 🚨 トラブルシューティング

### よくある問題

#### 1. バージョンが正しく更新されない

**原因**: Conventional Commitsフォーマットに従っていない

**解決法**:
```bash
# ❌ 間違い
git commit -m "update version"

# ✅ 正しい
git commit -m "fix: バージョン更新処理を修正"
```

#### 2. Dockerでバージョン情報が表示されない

**原因**: ビルド引数が正しく渡されていない

**解決法**:
```bash
# 必要なビルド引数を確認
docker build --build-arg VERSION=1.2.3 .
```

#### 3. リリースが作成されない

**原因**: 
- リリース対象のコミットタイプでない（`docs:`、`style:`等）
- `master`/`main`ブランチ以外にプッシュ

**解決法**:
- 適切なコミットタイプを使用
- 正しいブランチにプッシュ

### デバッグ用コマンド

```bash
# バージョン管理システムの全テスト
python3 scripts/test-version.py

# Git情報の確認
git log --oneline -5
git describe --tags --always --dirty

# Docker環境変数の確認
docker run --rm your-image env | grep DOCKER_

# GitHub Actions環境変数の確認（CI環境）
env | grep GITHUB_
```

## 🔗 関連リンク

- [Semantic Versioning](https://semver.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [semantic-release](https://github.com/semantic-release/semantic-release)
- [Docker Build Buildx](https://docs.docker.com/buildx/)
- [OpenContainer Image Specification](https://github.com/opencontainers/image-spec/blob/main/annotations.md)

## 📝 更新履歴

| バージョン | 日付 | 更新内容 |
|------------|------|----------|
| 1.0.0 | 2025-06-22 | 初版作成・自動バージョン管理システム実装 |

---

*このドキュメントは自動バージョン管理システムの一部として管理されています。*