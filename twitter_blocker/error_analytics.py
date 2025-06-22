"""
HTTPエラー統計収集・分析システム
長期稼働時のエラーパターン詳細分析機能
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .database import DatabaseManager


class HTTPErrorAnalytics:
    """HTTP エラー統計収集・分析システム"""
    
    def __init__(self, database_manager: DatabaseManager):
        self.db = database_manager
        self.error_timeline = []  # (timestamp, error_type, context)
        self.session_id = self._generate_session_id()
        self.init_analytics_tables()
    
    def _generate_session_id(self) -> str:
        """セッションIDを生成"""
        return f"session_{int(time.time())}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def init_analytics_tables(self):
        """エラー分析用テーブルの初期化"""
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            
            # HTTP エラー詳細ログテーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS http_error_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    session_id TEXT NOT NULL,
                    error_type TEXT NOT NULL,
                    status_code INTEGER,
                    response_text TEXT,
                    headers_json TEXT,
                    runtime_hours REAL,
                    retry_count INTEGER,
                    success_rate_before REAL,
                    header_enhancement_active BOOLEAN,
                    user_context TEXT,
                    recovery_time_seconds REAL,
                    container_name TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 長期パターン分析テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS long_term_patterns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_date DATE NOT NULL,
                    session_id TEXT NOT NULL,
                    total_runtime_hours REAL,
                    error_type_distribution TEXT,  -- JSON
                    critical_transitions TEXT,     -- JSON 
                    effectiveness_metrics TEXT,    -- JSON
                    recommendations TEXT,          -- JSON
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 時間帯別エラー統計テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hourly_error_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    hour_offset INTEGER NOT NULL,  -- セッション開始からの時間（時）
                    total_requests INTEGER DEFAULT 0,
                    total_errors INTEGER DEFAULT 0,
                    error_types_json TEXT,  -- JSON: {error_type: count}
                    success_rate REAL DEFAULT 1.0,
                    avg_response_time REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(session_id, hour_offset)
                )
            """)
            
            conn.commit()
            print(f"📊 HTTPエラー分析テーブル初期化完了: {self.db.db_file}")
    
    def record_error_with_context(self, error_data: Dict[str, Any]) -> None:
        """コンテキスト付きエラー記録"""
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO http_error_analytics 
                (timestamp, session_id, error_type, status_code, response_text, 
                 headers_json, runtime_hours, retry_count, success_rate_before,
                 header_enhancement_active, user_context, recovery_time_seconds, container_name)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                error_data['timestamp'],
                self.session_id,
                error_data['error_type'],
                error_data['status_code'],
                error_data.get('response_text', ''),
                json.dumps(error_data.get('headers', {})),
                error_data['runtime_hours'],
                error_data['retry_count'],
                error_data['success_rate_before'],
                error_data['header_enhancement_active'],
                error_data.get('user_context', ''),
                error_data.get('recovery_time_seconds'),
                error_data.get('container_name', 'unknown')
            ))
    
    def update_hourly_stats(self, runtime_hours: float, error_occurred: bool, 
                          error_type: str = None, response_time: float = None) -> None:
        """時間帯別統計の更新"""
        hour_offset = int(runtime_hours)
        
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            
            # 既存レコードを取得または新規作成
            cursor.execute("""
                SELECT total_requests, total_errors, error_types_json, success_rate
                FROM hourly_error_stats 
                WHERE session_id = ? AND hour_offset = ?
            """, (self.session_id, hour_offset))
            
            result = cursor.fetchone()
            
            if result:
                total_requests, total_errors, error_types_json, current_success_rate = result
                error_types = json.loads(error_types_json) if error_types_json else {}
            else:
                total_requests, total_errors = 0, 0
                error_types = {}
                current_success_rate = 1.0
            
            # 統計更新
            total_requests += 1
            if error_occurred:
                total_errors += 1
                if error_type:
                    error_types[error_type] = error_types.get(error_type, 0) + 1
            
            new_success_rate = (total_requests - total_errors) / total_requests if total_requests > 0 else 1.0
            
            # レコード更新または挿入
            cursor.execute("""
                INSERT OR REPLACE INTO hourly_error_stats 
                (session_id, hour_offset, total_requests, total_errors, 
                 error_types_json, success_rate, avg_response_time)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                self.session_id,
                hour_offset,
                total_requests,
                total_errors,
                json.dumps(error_types),
                new_success_rate,
                response_time
            ))
    
    def analyze_error_progression_patterns(self) -> Dict[str, Any]:
        """エラー進行パターンの分析"""
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            
            # 時間別エラー推移を取得
            cursor.execute("""
                SELECT hour_offset, total_requests, total_errors, success_rate, error_types_json
                FROM hourly_error_stats 
                WHERE session_id = ?
                ORDER BY hour_offset
            """, (self.session_id,))
            
            hourly_data = cursor.fetchall()
            
            if not hourly_data:
                return {"status": "no_data", "message": "分析に十分なデータがありません"}
            
            # パターン分析
            patterns = {
                "steady_decline": False,    # 段階的悪化
                "sudden_spike": False,      # 急激なエラー増加
                "periodic_issues": False,   # 周期的な問題
                "recovery_pattern": False,  # 回復パターン
                "critical_threshold": False # 重要閾値到達
            }
            
            success_rates = [row[3] for row in hourly_data]
            error_counts = [row[2] for row in hourly_data]
            
            # 段階的悪化の検出
            if len(success_rates) >= 3:
                declining_trend = all(
                    success_rates[i] >= success_rates[i+1] 
                    for i in range(len(success_rates)-1)
                )
                if declining_trend and success_rates[-1] < 0.8:
                    patterns["steady_decline"] = True
            
            # 急激なエラー増加の検出
            if len(error_counts) >= 2:
                for i in range(1, len(error_counts)):
                    if error_counts[i] > error_counts[i-1] * 3:  # 3倍以上の増加
                        patterns["sudden_spike"] = True
                        break
            
            # 重要閾値到達の検出
            if success_rates and success_rates[-1] < 0.5:  # 成功率50%未満
                patterns["critical_threshold"] = True
            
            return {
                "status": "analysis_complete",
                "patterns_detected": patterns,
                "hourly_data": hourly_data,
                "recommendations": self._generate_pattern_recommendations(patterns)
            }
    
    def _generate_pattern_recommendations(self, patterns: Dict[str, bool]) -> List[str]:
        """パターンに基づく推奨事項の生成"""
        recommendations = []
        
        if patterns["steady_decline"]:
            recommendations.append("🔄 段階的悪化検出 - Cookie予防的再読み込みを推奨")
            recommendations.append("📉 ヘッダー戦略の段階的変更を検討")
        
        if patterns["sudden_spike"]:
            recommendations.append("🚨 急激なエラー増加 - 即座にリクエスト停止して原因調査")
            recommendations.append("🔧 アンチボット検出の可能性 - ヘッダー即座変更")
        
        if patterns["critical_threshold"]:
            recommendations.append("⚠️ 重要閾値到達 - システム停止を検討")
            recommendations.append("🏥 緊急メンテナンスモードへの切り替え")
        
        if not any(patterns.values()):
            recommendations.append("✅ 健全なパターン - 現在の戦略継続")
        
        return recommendations
    
    def generate_weekly_analysis_report(self) -> Dict[str, Any]:
        """週次分析レポート生成"""
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            
            # 過去7日間のデータを分析
            cursor.execute("""
                SELECT error_type, runtime_hours, COUNT(*) as frequency,
                       AVG(recovery_time_seconds) as avg_recovery,
                       header_enhancement_active
                FROM http_error_analytics 
                WHERE timestamp > ? 
                GROUP BY error_type, ROUND(runtime_hours), header_enhancement_active
                ORDER BY runtime_hours, frequency DESC
            """, (time.time() - 7*24*3600,))
            
            results = cursor.fetchall()
            
            return {
                "analysis_period": "7_days",
                "error_patterns": self._analyze_error_patterns(results),
                "header_effectiveness": self._analyze_header_effectiveness(results),
                "runtime_correlations": self._analyze_runtime_correlations(results),
                "optimization_recommendations": self._generate_optimization_recommendations(results)
            }
    
    def _analyze_error_patterns(self, results: List[Tuple]) -> Dict[str, Any]:
        """エラーパターンの分析"""
        error_by_type = {}
        error_by_hour = {}
        
        for error_type, runtime_hours, frequency, avg_recovery, header_enhanced in results:
            # エラータイプ別集計
            if error_type not in error_by_type:
                error_by_type[error_type] = {
                    "total_frequency": 0,
                    "avg_recovery_time": 0,
                    "first_occurrence_hour": runtime_hours,
                    "header_effectiveness": {"with": 0, "without": 0}
                }
            
            error_by_type[error_type]["total_frequency"] += frequency
            error_by_type[error_type]["avg_recovery_time"] = avg_recovery or 0
            
            if header_enhanced:
                error_by_type[error_type]["header_effectiveness"]["with"] += frequency
            else:
                error_by_type[error_type]["header_effectiveness"]["without"] += frequency
            
            # 時間別集計
            hour_key = f"{int(runtime_hours)}h"
            if hour_key not in error_by_hour:
                error_by_hour[hour_key] = {"total_errors": 0, "error_types": {}}
            
            error_by_hour[hour_key]["total_errors"] += frequency
            error_by_hour[hour_key]["error_types"][error_type] = frequency
        
        return {
            "by_error_type": error_by_type,
            "by_runtime_hour": error_by_hour,
            "dominant_error_types": sorted(
                error_by_type.items(), 
                key=lambda x: x[1]["total_frequency"], 
                reverse=True
            )[:5]
        }
    
    def _analyze_header_effectiveness(self, results: List[Tuple]) -> Dict[str, Any]:
        """ヘッダー有効性の分析"""
        with_headers = {"total_errors": 0, "error_types": {}}
        without_headers = {"total_errors": 0, "error_types": {}}
        
        for error_type, runtime_hours, frequency, avg_recovery, header_enhanced in results:
            if header_enhanced:
                with_headers["total_errors"] += frequency
                with_headers["error_types"][error_type] = with_headers["error_types"].get(error_type, 0) + frequency
            else:
                without_headers["total_errors"] += frequency
                without_headers["error_types"][error_type] = without_headers["error_types"].get(error_type, 0) + frequency
        
        # 効果性の計算
        total_with = with_headers["total_errors"]
        total_without = without_headers["total_errors"]
        total_requests = total_with + total_without
        
        effectiveness_score = 0.0
        if total_requests > 0:
            error_rate_with = total_with / total_requests
            error_rate_without = total_without / total_requests
            
            if total_without > 0:
                effectiveness_score = max(0, (error_rate_without - error_rate_with) / error_rate_without)
        
        return {
            "with_headers": with_headers,
            "without_headers": without_headers,
            "effectiveness_score": effectiveness_score,
            "recommendation": "use_enhanced" if effectiveness_score > 0.2 else "use_basic"
        }
    
    def _analyze_runtime_correlations(self, results: List[Tuple]) -> Dict[str, Any]:
        """稼働時間とエラーの相関分析"""
        runtime_buckets = {
            "0-1h": {"errors": 0, "types": {}},
            "1-3h": {"errors": 0, "types": {}},
            "3-6h": {"errors": 0, "types": {}},
            "6-12h": {"errors": 0, "types": {}},
            "12h+": {"errors": 0, "types": {}}
        }
        
        for error_type, runtime_hours, frequency, avg_recovery, header_enhanced in results:
            bucket = self._get_runtime_bucket(runtime_hours)
            runtime_buckets[bucket]["errors"] += frequency
            runtime_buckets[bucket]["types"][error_type] = runtime_buckets[bucket]["types"].get(error_type, 0) + frequency
        
        # 相関分析
        correlations = {
            "error_increase_over_time": False,
            "critical_hours": [],
            "stable_periods": []
        }
        
        # エラー増加傾向の検出
        error_counts = [bucket["errors"] for bucket in runtime_buckets.values()]
        if len(error_counts) >= 3:
            increasing_trend = sum(
                1 for i in range(len(error_counts)-1) 
                if error_counts[i+1] > error_counts[i]
            ) > len(error_counts) // 2
            correlations["error_increase_over_time"] = increasing_trend
        
        # 重要時間帯の特定
        max_errors = max(bucket["errors"] for bucket in runtime_buckets.values())
        if max_errors > 0:
            for bucket_name, bucket_data in runtime_buckets.items():
                if bucket_data["errors"] > max_errors * 0.7:  # 最大エラー数の70%以上
                    correlations["critical_hours"].append(bucket_name)
        
        return {
            "runtime_buckets": runtime_buckets,
            "correlations": correlations,
            "insights": self._generate_runtime_insights(runtime_buckets, correlations)
        }
    
    def _get_runtime_bucket(self, runtime_hours: float) -> str:
        """稼働時間をバケットに分類"""
        if runtime_hours < 1:
            return "0-1h"
        elif runtime_hours < 3:
            return "1-3h"
        elif runtime_hours < 6:
            return "3-6h"
        elif runtime_hours < 12:
            return "6-12h"
        else:
            return "12h+"
    
    def _generate_runtime_insights(self, runtime_buckets: Dict, correlations: Dict) -> List[str]:
        """稼働時間分析からの洞察生成"""
        insights = []
        
        if correlations["error_increase_over_time"]:
            insights.append("⚠️ 稼働時間の増加に伴いエラーが増加する傾向")
            insights.append("🔄 定期的なシステムリセットの検討が必要")
        
        if "3-6h" in correlations["critical_hours"]:
            insights.append("🕒 3-6時間が最もエラーが発生しやすい時間帯")
            insights.append("🛡️ この時間帯での予防的対策の強化を推奨")
        
        if not correlations["critical_hours"]:
            insights.append("✅ 特定の問題時間帯なし - 安定したパフォーマンス")
        
        return insights
    
    def _generate_optimization_recommendations(self, results: List[Tuple]) -> List[str]:
        """最適化推奨事項の生成"""
        recommendations = []
        
        # エラー頻度分析
        total_errors = sum(frequency for _, _, frequency, _, _ in results)
        
        if total_errors > 100:
            recommendations.append("🚨 高頻度エラー検出 - 緊急対応が必要")
            recommendations.append("🔧 基本設定の見直しを推奨")
        elif total_errors > 50:
            recommendations.append("⚠️ 中程度のエラー - 予防的対策の強化")
        else:
            recommendations.append("✅ 低エラー率 - 現在の設定継続")
        
        # 復旧時間分析
        recovery_times = [avg_recovery for _, _, _, avg_recovery, _ in results if avg_recovery]
        if recovery_times:
            avg_recovery = sum(recovery_times) / len(recovery_times)
            if avg_recovery > 300:  # 5分以上
                recommendations.append("⏱️ 復旧時間が長い - バックオフ戦略の調整が必要")
        
        return recommendations
    
    def get_real_time_status(self) -> Dict[str, Any]:
        """リアルタイム状態の取得"""
        current_time = time.time()
        
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            
            # 最近1時間のエラー統計
            cursor.execute("""
                SELECT COUNT(*) as total_errors,
                       COUNT(DISTINCT error_type) as unique_error_types
                FROM http_error_analytics 
                WHERE session_id = ? AND timestamp > ?
            """, (self.session_id, current_time - 3600))
            
            recent_stats = cursor.fetchone()
            
            # 最新の時間別統計
            cursor.execute("""
                SELECT hour_offset, success_rate, total_errors
                FROM hourly_error_stats 
                WHERE session_id = ?
                ORDER BY hour_offset DESC
                LIMIT 1
            """, (self.session_id,))
            
            latest_hourly = cursor.fetchone()
        
        return {
            "session_id": self.session_id,
            "recent_errors_1h": recent_stats[0] if recent_stats else 0,
            "unique_error_types_1h": recent_stats[1] if recent_stats else 0,
            "current_hour_success_rate": latest_hourly[1] if latest_hourly else 1.0,
            "current_hour_errors": latest_hourly[2] if latest_hourly else 0,
            "analysis_available": latest_hourly is not None
        }