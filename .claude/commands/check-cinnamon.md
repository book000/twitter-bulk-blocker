# Cinnamonサーバー状態調査 - Claude Code最適化版

Claude Code専用の包括的なCinnamonサーバー監視・問題特定・修正提案システム

## 概要

このコマンドは以下の高度な分析を実行します：

### 基本監視項目
- コンテナ稼働状態と健康チェック（稼働中/停止中の詳細分析）
- 停止理由の自動判定（正常完了 vs エラー終了）
- **実質完了率の正確な計算**（永続的失敗を処理済みとして扱う）
- 認証状態の詳細確認
- パフォーマンス指標の分析

### 新機能: 包括的分析
- **正確な完了率表示**: 永続的失敗を含む実質100%完了の判定
- **詳細なコンテナ分析**: Exit Code分析と停止理由の特定
- **即座のアクション提示**: 対応が必要な問題の明確化
- **トラブルシューティング**: 具体的な解決手順の提示

## 実行方法

### メイン分析 (推奨)
```bash
.claude/cinnamon-logs-ai-optimized.sh
```
**特徴**: 構造化された出力、具体的修正提案、優先度付け

### 従来版 (参考)
```bash
.claude/cinnamon-logs.sh
```
**特徴**: 基本的なログ調査、人間向け出力

### 統合インターフェース
```bash
.claude/cinnamon-monitor-suite.sh ai
```
**特徴**: 引数ベースの非対話型実行

## 出力形式の理解

### セクション構造
```
SECTION_START: セクション名
[分析内容]
SECTION_END: セクション名
```

### 問題報告フォーマット
```
FINDING: severity=LEVEL category=CATEGORY message="問題の説明"
  DETAILS: 詳細情報
  RECOMMENDED_ACTION: 推奨する対応方法
```

### 重要度レベル
- **CRITICAL**: 即座の修正が必要（システム停止・データ破損の可能性）
- **WARNING**: 注意が必要（パフォーマンス低下・将来的な問題）
- **INFO**: 情報提供レベル（最適化の提案）
- **OK**: 正常状態の確認

## 問題パターンと自動対応

### 1. KeyError: 'error_message' 
**重要度**: CRITICAL
**場所**: `CODE_ANALYSIS_RECOMMENDATIONS`セクション
```
ISSUE: KeyError_in_manager_py
  FILE: twitter_blocker/manager.py
  LINES: 402-403, 493
  CODE_FIX: 'failure_info.get("key", default) if failure_info else default'
  PRIORITY: IMMEDIATE
```
**Claude Code対応**: manager.pyの安全な辞書アクセスに自動修正

### 2. 認証エラー多発
**重要度**: HIGH
**場所**: `AUTHENTICATION_STATUS`セクション
```
ISSUE: Authentication_failure_service_name
  SERVICE: service_name
  SOLUTION: Update cookies.json for service_name
  PRIORITY: HIGH
```
**Claude Code対応**: 該当サービスのCookie更新

### 3. パフォーマンス劣化
**重要度**: MEDIUM
**場所**: `PERFORMANCE_ANALYSIS`セクション
```
ISSUE: Service_performance_degradation_service_name
  ERRORS: 高エラー率
  SUCCESSFUL_BLOCKS: 低成功率
  PRIORITY: MEDIUM
```
**Claude Code対応**: サービス再起動・設定調整

## 期待される動作パターン

### 正常時
```
OVERALL_STATUS: HEALTHY
TOTAL_FINDINGS: 0-2
ACTIONABLE_ITEMS: MAINTENANCE_ONLY
```
**Claude Code動作**: 通常の監視継続

### 問題検出時
```
OVERALL_STATUS: CRITICAL
TOTAL_FINDINGS: 3+
ACTIONABLE_ITEMS: YES

IMMEDIATE_FIXES_REQUIRED:
  1. Fix KeyError in manager.py failure_info handling
     - File: twitter_blocker/manager.py
     - Lines: 402-403, 493
```
**Claude Code動作**: 自動修正の実行

### 認証問題検出時
```
HIGH_PRIORITY_FIXES:
  1. Update authentication cookies
     - Service: tomachi_priv (5 errors)
     - Service: book000_vrc (3 errors)
```
**Claude Code動作**: Cookie更新プロセスの開始

## 使用例とワークフロー

### 包括的チェック (推奨)
```bash
# AI最適化分析（メイン）
.claude/cinnamon-logs-ai-optimized.sh
```
1. **構造化出力の解析**: 詳細な問題特定
2. **完了率の正確な理解**: 永続的失敗を含む実質完了率
3. **問題の自動特定**: 認証エラー、アカウントロック等
4. **修正提案**: 具体的な対応手順

#### 完了率の正確な理解
永続的失敗（suspended/not_found/deactivated）を処理済みとして扱うため：
```
従来表示: ブロック済み: 3,236人 (83.3%)
正確な理解: 実質完了率 100% = 3,236人ブロック + 649人永続的失敗
```

### 基本監視
```bash
# 統合インターフェース
.claude/cinnamon-monitor-suite.sh

# 従来版（参考用）
.claude/cinnamon-logs.sh
```
- 基本的なログ調査と人間向け出力
- インタラクティブメニューでの操作

### 問題対応フロー
1. **問題検出**: Exit Code 1または認証エラーの特定
2. **根本原因特定**: 停止理由と影響範囲の分析
3. **修正実行**: Cookie更新やサービス再起動
4. **効果確認**: 修正後の再実行による検証

## 結果の解釈

### 🟢 正常動作
- `OVERALL_STATUS: HEALTHY`
- 全コンテナ稼働
- エラー率 < 5%
- 処理継続中

### 🟡 要注意状態
- `OVERALL_STATUS: ATTENTION`
- 一部認証エラー
- パフォーマンス低下
- WARNING問題複数

### 🔴 緊急対応必要
- `OVERALL_STATUS: CRITICAL`
- システム停止
- 継続的なエラー
- CRITICAL問題検出

## トラブルシューティング

### 接続失敗
```
CONNECTION_ERROR: Cannot connect to Cinnamon server
```
**対応**: SSH設定とサーバー状態の確認

### データ不足
```
WARNING: No recent processing statistics available
```
**対応**: Docker Composeサービス状態の確認

### 権限エラー
**対応**: スクリプト実行権限の確認 (`chmod +x`)

---

このコマンドにより、Claude CodeがCinnamonサーバーの状態を正確に把握し、問題を迅速に特定・修正できます。