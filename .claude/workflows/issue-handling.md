# Issue対応完全ワークフロー

## 基本プロセス概要

「issue #nnを対応してください」→ 完全自動実行手順：

1. **Issue内容・コメント確認** → 2. ブランチ作成（type/description） → 3. 実装 → 4. 品質チェック → 5. コミット・プッシュ → 6. PR作成（Closes #nn）

**重要**: Issueコメントも必ず確認し、実装方針の変更や追加制約を反映

## 詳細手順

### 1. Issue情報の完全収集
```bash
# Issue基本情報取得
gh issue view 25 --json title,body,author,labels,milestone,assignees

# Issue全コメント取得（重要）
gh issue view 25 --json comments --jq '.comments[] | {author: .author.login, body: .body, createdAt: .createdAt}'

# 関連PRの確認
gh issue view 25 --json timelineItems --jq '.timelineItems[] | select(.typename == "PullRequest")'
```

**分析ポイント:**
- Issue本文の要件分析
- **コメントでの要件変更・追加制約**
- ラベルによる優先度・カテゴリ
- 関連Issue・PRの存在確認

### 2. ブランチ戦略
```bash
# ブランチ名規則: {type}/{issue-number}-{brief-description}
# type: feat, fix, docs, refactor, test, chore

# Issue #25 (バグ修正) の例
git checkout -b fix/25-permanent-failure-detection

# Issue #30 (機能追加) の例  
git checkout -b feat/30-batch-query-optimization

# Issue #35 (ドキュメント) の例
git checkout -b docs/35-update-api-documentation
```

**ブランチタイプ判定:**
- `feat/`: 新機能追加
- `fix/`: バグ修正
- `docs/`: ドキュメント更新
- `refactor/`: リファクタリング
- `test/`: テスト追加・修正
- `chore/`: ビルド・設定変更

### 3. 実装フェーズ

#### 要件分析と実装計画
```python
# Issue要件の TodoWrite への展開例
def analyze_issue_requirements(issue_data):
    """Issue要件をタスクに分解"""
    
    # Issue #25: 永続的失敗の検出機能追加
    todos = [
        {
            "content": "永続的失敗検出ロジックの実装（database.py）",
            "status": "pending", 
            "priority": "high",
            "id": "1"
        },
        {
            "content": "バッチクエリ最適化の実装",
            "status": "pending",
            "priority": "high", 
            "id": "2"
        },
        {
            "content": "manager.pyでの事前チェック実装",
            "status": "pending",
            "priority": "medium",
            "id": "3"
        },
        {
            "content": "既存コードへの統合",
            "status": "pending",
            "priority": "medium",
            "id": "4"
        },
        {
            "content": "テストケース作成",
            "status": "pending",
            "priority": "medium",
            "id": "5"
        }
    ]
    
    return todos
```

#### 段階的実装
```python
# 段階1: コア機能の実装
def implement_core_functionality():
    """
    TodoWrite: 「永続的失敗検出ロジックの実装」を in_progress に
    """
    
    # database.py の変更
    # - is_permanent_failure() メソッド追加
    # - get_permanent_failure_info() メソッド追加
    
    """
    TodoWrite: 「永続的失敗検出ロジックの実装」を completed に
    TodoWrite: 「バッチクエリ最適化の実装」を in_progress に
    """

# 段階2: パフォーマンス最適化
def implement_optimization():
    """
    N+1問題の解決とバッチ処理実装
    """
    
    # get_permanent_failures_batch() の実装
    
    """
    TodoWrite: 「バッチクエリ最適化の実装」を completed に
    TodoWrite: 「manager.pyでの事前チェック実装」を in_progress に
    """

# 段階3: 統合実装
def integrate_with_existing_code():
    """
    既存コードへの機能統合
    """
    
    # manager.py の3箇所での統合
    
    """
    TodoWrite: 「manager.pyでの事前チェック実装」を completed に
    """
```

### 4. 品質チェックプロセス

#### 自動品質チェック
```bash
# 1. Lint チェック
python -m flake8 twitter_blocker/

# 2. Type チェック  
python -m mypy twitter_blocker/

# 3. テスト実行
python -m pytest tests/ -v

# 4. パフォーマンステスト（該当する場合）
python -m pytest tests/performance/ -v
```

#### 手動品質チェック
- [ ] Issue要件の完全実装確認
- [ ] コメントでの追加要件の反映確認
- [ ] 既存機能への影響確認
- [ ] エラーハンドリングの適切性
- [ ] パフォーマンスへの影響評価

### 5. コミット・プッシュ

#### コミットメッセージ規則
```bash
# 規則: {type}(#{issue}): {description}
# 
# 🤖 Generated with Claude Code
# 
# Co-Authored-By: Claude <noreply@anthropic.com>

# 例: Issue #25 のコミット
git commit -m "$(cat <<'EOF'
fix(#25): 永続的失敗アカウントの事前チェック機能を追加

suspendedや削除済みアカウントについて再取得を防ぐため、
データベースに記録された永続的失敗を事前にチェックする機能を実装。
N+1問題を回避するバッチクエリも同時に導入。

- database.py: is_permanent_failure(), get_permanent_failures_batch() 追加
- manager.py: 3箇所でのバッチ事前チェック実装
- パフォーマンス: 37倍の処理速度向上を確認

Closes #25

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# プッシュ（upstream設定込み）
git push -u origin fix/25-permanent-failure-detection
```

### 6. PR作成

#### PR作成コマンド
```bash
gh pr create --title "fix(#25): 永続的失敗アカウントの事前チェック機能を追加" --body "$(cat <<'EOF'
## 概要
Issue #25 の対応として、永続的失敗アカウント（suspended/deleted）の事前チェック機能を実装しました。

## 変更内容
### 主要機能
- **永続的失敗検出**: `database.py` に `is_permanent_failure()` メソッドを追加
- **バッチ処理最適化**: N+1問題を解決する `get_permanent_failures_batch()` を実装
- **事前チェック統合**: `manager.py` の3箇所でバッチ事前チェックを導入

### パフォーマンス改善
- **処理速度**: 37倍の処理速度向上（個別クエリ → バッチクエリ）
- **API呼び出し削減**: 永続的失敗アカウントへの不要なAPI呼び出しを完全に排除
- **メモリ効率**: バッチ処理によるメモリ使用量の最適化

## テスト結果
- [ ] 全単体テストパス
- [ ] パフォーマンステスト実行済み（37倍改善確認）
- [ ] 永続的失敗検出の動作確認完了
- [ ] 既存機能への影響なし確認

## Issue対応
Closes #25

## 実装詳細
### database.py の追加メソッド
```python
def is_permanent_failure(self, identifier: str, user_format: str = "screen_name") -> bool:
    """永続的失敗アカウントかどうかをチェック"""
    
def get_permanent_failures_batch(self, identifiers: List[str], user_format: str = "screen_name") -> Dict[str, Dict[str, Any]]:
    """複数の永続的失敗アカウントを一括取得（N+1問題回避）"""
```

### manager.py の統合箇所
1. `block_users()` - ユーザーブロック処理
2. `get_users_info()` - ユーザー情報取得
3. `check_users_relationships()` - 関係確認処理

## 追加考慮事項
Issue コメントでの追加要件:
- [コメントでの要件があれば記載]
- [パフォーマンス要件があれば記載]

🤖 Generated with Claude Code
EOF
)"
```

#### PR本文の必須要素
1. **概要**: Issue対応の要約
2. **変更内容**: 実装した機能の詳細
3. **テスト結果**: 実行したテストの結果
4. **Closes #nn**: Issue連携（必須）
5. **実装詳細**: 重要な実装の説明
6. **追加考慮事項**: コメントでの要件変更など

## Issue固有対応パターン

### バグ修正Issue
```yaml
ブランチ: fix/{issue-number}-{description}
優先度: 高
必須チェック:
  - 根本原因の特定と修正
  - 再発防止策の実装
  - 関連機能への影響確認
  - テストケース追加
```

### 機能追加Issue
```yaml
ブランチ: feat/{issue-number}-{description}
優先度: 中
必須チェック:
  - 要件の完全実装
  - 既存機能との整合性
  - パフォーマンスへの影響
  - ドキュメント更新
```

### パフォーマンス改善Issue
```yaml
ブランチ: refactor/{issue-number}-{description}
優先度: 中
必須チェック:
  - 改善効果の定量測定
  - 既存機能の動作保証
  - メモリ・CPU使用量の確認
  - ベンチマーク結果の記録
```

### ドキュメントIssue
```yaml  
ブランチ: docs/{issue-number}-{description}
優先度: 低
必須チェック:
  - 内容の正確性
  - 既存ドキュメントとの整合性
  - 読みやすさ・理解しやすさ
  - リンクの有効性
```

## トラブルシューティング

### よくあるIssue対応の問題

#### Issue要件の理解不足
```markdown
❌ 問題: Issue本文のみ読んで実装開始
✅ 解決: Issue + 全コメントを精読、不明点は確認

❌ 問題: 要件変更のコメントを見逃し
✅ 解決: コメント時系列順に確認、最新要件の把握
```

#### ブランチ戦略の間違い
```markdown
❌ 問題: メインブランチから直接実装
✅ 解決: Issue専用ブランチの作成

❌ 問題: ブランチ名が不明確
✅ 解決: type/issue-number-description 形式の遵守
```

#### PR作成の不備
```markdown
❌ 問題: Closes #nn の記載忘れ
✅ 解決: PR本文に必ず "Closes #nn" を記載

❌ 問題: 実装内容の説明不足
✅ 解決: 変更内容・テスト結果・実装詳細を具体的に記載
```

## 効率化ツール

### Issue情報収集スクリプト
```bash
#!/bin/bash
# issue-info.sh - Issue情報の一括取得

ISSUE_NUMBER=$1

echo "=== Issue #${ISSUE_NUMBER} 情報収集 ==="

# 基本情報
echo "## 基本情報"
gh issue view $ISSUE_NUMBER --json title,body,author,labels,state

# コメント一覧
echo -e "\n## コメント履歴"  
gh issue view $ISSUE_NUMBER --json comments --jq '.comments[] | "**\(.author.login)** (\(.createdAt)):\n\(.body)\n"'

# 関連PR
echo -e "\n## 関連PR"
gh issue view $ISSUE_NUMBER --json timelineItems --jq '.timelineItems[] | select(.typename == "PullRequest") | .pullRequest | "\(.number): \(.title)"'

echo -e "\n=== 情報収集完了 ==="
```

### ブランチ作成ヘルパー
```bash
#!/bin/bash
# create-issue-branch.sh - Issue対応ブランチの作成

ISSUE_NUMBER=$1
ISSUE_TYPE=$2  # feat/fix/docs/refactor/test/chore
DESCRIPTION=$3

# ブランチ名生成
BRANCH_NAME="${ISSUE_TYPE}/${ISSUE_NUMBER}-${DESCRIPTION}"

echo "ブランチ作成: $BRANCH_NAME"

# メインブランチから最新取得
git checkout main
git pull origin main

# 新ブランチ作成・切り替え
git checkout -b $BRANCH_NAME

echo "✅ ブランチ準備完了: $BRANCH_NAME"
echo "Issue #${ISSUE_NUMBER} の実装を開始してください"
```

## チェックリスト

### Issue対応開始時
- [ ] Issue本文の完全理解
- [ ] 全コメントの確認
- [ ] 要件変更・追加制約の把握
- [ ] 関連Issue・PRの確認
- [ ] 適切なブランチ名でブランチ作成

### 実装中
- [ ] TodoWriteでタスク管理
- [ ] 段階的実装の実行
- [ ] 各段階でのTodo完了マーク
- [ ] Issue要件の逸脱防止

### 実装完了時
- [ ] Issue要件の完全実装確認
- [ ] 品質チェック（lint/test/typecheck）
- [ ] パフォーマンステスト（該当時）
- [ ] 適切なコミットメッセージ
- [ ] PR作成（Closes #nn必須）