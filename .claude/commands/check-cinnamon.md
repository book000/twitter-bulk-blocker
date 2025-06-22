# check-cinnamon - 分割型監視システム

Cinnamonサーバーの包括的な状態分析を**段階的・選択的**に実行します。

従来の巨大なスクリプト（2637行）による出力制限問題を解決し、機能別に分割された軽量システムを提供します。

## 🚀 新しい分割アーキテクチャ

### メインコマンド
```bash
check-cinnamon                    # 基本チェック（軽量）
check-cinnamon --detailed         # 全詳細分析
check-cinnamon --errors-only      # 403エラー分析のみ
check-cinnamon --module <name>    # 特定モジュールのみ
```

### 利用可能なモジュール
| モジュール | 機能 | ファイル |
|------------|------|----------|
| `version` | バージョン情報分析 | `check-cinnamon-version` |
| `container` | コンテナ状態分析 | `check-cinnamon-containers` |
| `errors` | 403エラー分析 | `check-cinnamon-errors` |
| `completion` | 完了率分析 | `check-cinnamon-completion` |
| `health` | 長期ヘルス分析 | `check-cinnamon-health` |
| `performance` | パフォーマンス指標・履歴比較 | `check-cinnamon-performance` |
| `accounts` | アカウント別詳細分析・最適化提案 | `check-cinnamon-account-analysis` |

## 📊 基本使用方法

### 🎯 推奨フロー
1. **クイックチェック**: `check-cinnamon`
2. **問題検出時**: `check-cinnamon --errors-only`
3. **詳細調査**: `check-cinnamon --detailed`

### 💡 よくある使用例

#### 日常監視
```bash
# 軽量な基本チェック（推奨）
check-cinnamon

# 403エラーが気になる時
check-cinnamon --errors-only
```

#### 問題調査
```bash
# 特定モジュールでの深掘り
check-cinnamon --module errors
check-cinnamon --module health
check-cinnamon --module performance
check-cinnamon --module accounts

# 完全な詳細分析
check-cinnamon --detailed
```

#### トラブルシューティング
```bash
# バージョン問題の調査
check-cinnamon --module version

# コンテナ問題の調査
check-cinnamon --module container
```

## 🔍 各モジュールの詳細

### check-cinnamon-version
**バージョン情報の分析**
- 稼働中コンテナのバージョン取得
- GitHub最新リリースとの比較
- イメージ整合性チェック（プレフィックス正規化対応）
- 更新推奨判定

```bash
check-cinnamon-version --brief    # 簡潔版
check-cinnamon-version           # 詳細版
```

### check-cinnamon-containers
**コンテナ状態の分析**
- 稼働中/停止中コンテナの確認
- ヘルスチェック状況
- 稼働時間マイルストーン分析
- 停止理由の自動判定

```bash
check-cinnamon-containers --brief # 簡潔版
check-cinnamon-containers        # 詳細版
```

### check-cinnamon-errors
**403エラーの分析**
- 各サービスの403エラー頻度
- 重要度自動判定（CRITICAL/HIGH/MEDIUM/LOW）
- エラーサンプルの表示
- 緊急推奨事項の提案

```bash
check-cinnamon-errors --brief    # 簡潔版
check-cinnamon-errors           # 詳細版
```

### check-cinnamon-completion
**完了率の分析**
- 各サービスの処理進捗
- 実質完了率の計算（永続的失敗考慮）
- サービス間比較
- 統計データの詳細表示

### check-cinnamon-health
**長期ヘルスの分析**
- 24時間エラー履歴
- 認証状態の推移
- Cookie更新システムの健全性
- ヘルススコアの算出

### check-cinnamon-performance
**パフォーマンス指標・履歴比較**
- 24時間のパフォーマンス指標収集（処理数、エラー数、成功率）
- アカウント別詳細メトリクス
- 履歴データとの比較分析（最大100件保持）
- トレンド判定機能（改善/悪化の自動検出）
- 処理速度の推定（件/時）

```bash
check-cinnamon-performance        # 現在の指標表示
check-cinnamon-performance --compare  # 履歴比較分析
```

### check-cinnamon-account-analysis
**アカウント別詳細分析・最適化提案**
- アカウント別リスク評価（HIGH/MEDIUM/LOW）
- エラータイプ分析（AUTH/RATE_LIMIT/NETWORK/GENERAL）
- 個別最適化提案の自動生成
- 具体的な実行コマンド提示
- アカウント固有の推奨事項
- 全体リスク分布サマリー

```bash
check-cinnamon-account-analysis        # 全アカウント分析
check-cinnamon-account-analysis --brief  # 簡潔版
```

## ⚡ パフォーマンス改善

### 従来の問題
- **2637行の巨大スクリプト**
- **30,000文字の出力制限に抵触**
- **分析途中での切断**

### 新しい解決策
- **機能別分割**: 必要な情報のみ取得
- **段階的実行**: --brief, --detailed オプション
- **選択的分析**: --module オプション
- **軽量な基本チェック**: 高速実行

## 🔧 高度な使用方法

### 複数モジュールの組み合わせ
```bash
# エラーとヘルス分析の組み合わせ
check-cinnamon --module errors --module health

# バージョンとコンテナ状態のみ
check-cinnamon --module version --module container

# パフォーマンスとアカウント分析
check-cinnamon --module performance --module accounts
```

### 自動化での活用
```bash
# CI/CDでの軽量チェック
check-cinnamon --brief

# 定期監視での詳細チェック
check-cinnamon --detailed 2>&1 | tee cinnamon-$(date +%Y%m%d-%H%M).log
```

## 📋 移行ガイド

### 従来からの移行
| 従来の使用方法 | 新しい使用方法 |
|----------------|----------------|
| `check-cinnamon` | `check-cinnamon` (軽量化済み) |
| 巨大な出力をスクロール | `check-cinnamon --module errors` |
| 特定情報を探す | 該当モジュールを直接実行 |
| 出力制限で切断 | 段階的に詳細分析 |

### Claude Code使用時の推奨
1. **基本**: `check-cinnamon` で概要把握
2. **問題検出**: 該当モジュールで詳細分析
3. **完全調査**: `check-cinnamon --detailed`

## 🛠️ トラブルシューティング

### よくある問題

**「モジュールが見つからない」**
```bash
# 実行権限の確認
ls -la .claude/commands/check-cinnamon-*

# 実行権限の付与
chmod +x .claude/commands/check-cinnamon-*
```

**「出力が不完全」**
```bash
# 段階的に分析
check-cinnamon --module errors
check-cinnamon --module health
```

**「従来の機能が欲しい」**
```bash
# 詳細モードで従来に近い出力
check-cinnamon --detailed
```

## 💡 ベストプラクティス

### 効率的な監視フロー
1. **定期監視**: `check-cinnamon` (軽量)
2. **アラート時**: `check-cinnamon --errors-only`
3. **詳細調査**: 問題に応じたモジュール選択
4. **完全分析**: `check-cinnamon --detailed`

### Claude Code使用時の注意
- **段階的アプローチ**: 一度に全てを取得せず、必要な情報から開始
- **モジュール活用**: 問題の種類に応じて適切なモジュールを選択
- **出力制限回避**: 大量の情報が必要な場合は複数回に分けて実行

## 📈 最新機能追加（v0.34.2）

### 🆕 バージョン表示の改善
- プレフィックス（v）の正規化により、バージョン比較の精度向上
- 「0.34.2」と「v0.34.2」を同一視して正しく判定

### 🆕 パフォーマンス分析機能
- 処理速度、成功率の履歴保存と比較
- トレンド分析による改善/悪化の自動判定
- アカウント別の詳細メトリクス

### 🆕 アカウント別最適化提案
- リスクレベルの自動評価（HIGH/MEDIUM/LOW）
- エラータイプ別の具体的な対処法
- アカウント固有の最適化アドバイス

## 📈 今後の拡張予定

- **カスタムプロファイル**: 用途別のモジュール組み合わせ
- **レポート機能**: 分析結果の構造化出力
- **アラート機能**: 閾値ベースの自動通知
- **予測分析**: 将来のパフォーマンス予測