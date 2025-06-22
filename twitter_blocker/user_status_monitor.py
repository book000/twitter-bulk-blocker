"""
Active状態ユーザー数変化監視機能
長期稼働時のユーザーステータス変化の追跡と403エラー予測
"""

import json
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from .database import DatabaseManager


class UserStatusMonitor:
    """ユーザーステータス変化監視システム"""
    
    def __init__(self, database_manager: DatabaseManager):
        self.db = database_manager
        self.session_id = self._generate_session_id()
        self.init_monitoring_tables()
    
    def _generate_session_id(self) -> str:
        """セッションIDを生成"""
        return f"status_{int(time.time())}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def init_monitoring_tables(self):
        """ユーザーステータス監視用テーブルの初期化"""
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            
            # ユーザーステータス履歴テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    session_id TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    total_users INTEGER NOT NULL,
                    blocked_users INTEGER NOT NULL,
                    failed_users INTEGER NOT NULL,
                    active_failed INTEGER NOT NULL,
                    suspended_failed INTEGER NOT NULL,
                    permanent_failures INTEGER NOT NULL,
                    completion_rate REAL NOT NULL,
                    runtime_hours REAL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ユーザーステータス変化アラート
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_status_alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    metrics_json TEXT,
                    predictions_json TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ステータス変化予測テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS status_change_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    service_name TEXT NOT NULL,
                    prediction_type TEXT NOT NULL,
                    confidence_score REAL NOT NULL,
                    estimated_time_hours REAL,
                    predicted_change_count INTEGER,
                    factors_json TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            print(f"👥 ユーザーステータス監視テーブル初期化完了: {self.db.db_file}")
    
    def record_service_status(self, service_data: Dict[str, Any]) -> None:
        """サービスのユーザーステータスを記録"""
        current_time = time.time()
        
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_status_history 
                (timestamp, session_id, service_name, total_users, blocked_users, 
                 failed_users, active_failed, suspended_failed, permanent_failures, 
                 completion_rate, runtime_hours)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                current_time,
                self.session_id,
                service_data['service_name'],
                service_data['total_users'],
                service_data['blocked_users'],
                service_data['failed_users'],
                service_data['active_failed'],
                service_data['suspended_failed'],
                service_data['permanent_failures'],
                service_data['completion_rate'],
                service_data.get('runtime_hours', 0)
            ))
    
    def analyze_status_changes(self, service_name: str) -> Dict[str, Any]:
        """ユーザーステータス変化の分析"""
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            
            # 過去24時間のデータを取得
            cursor.execute("""
                SELECT timestamp, active_failed, suspended_failed, total_users, 
                       completion_rate, runtime_hours
                FROM user_status_history 
                WHERE service_name = ? AND timestamp > ?
                ORDER BY timestamp DESC
            """, (service_name, time.time() - 24*3600))
            
            history_data = cursor.fetchall()
            
            if len(history_data) < 2:
                return {"status": "insufficient_data", "message": "分析に十分なデータがありません"}
            
            # 変化パターンの分析
            analysis = {
                "service_name": service_name,
                "data_points": len(history_data),
                "time_span_hours": (history_data[0][0] - history_data[-1][0]) / 3600,
                "trends": self._analyze_trends(history_data),
                "predictions": self._predict_status_changes(history_data, service_name),
                "anomalies": self._detect_anomalies(history_data),
                "risk_assessment": {}
            }
            
            # リスク評価
            analysis["risk_assessment"] = self._assess_403_error_risk(analysis)
            
            return analysis
    
    def _analyze_trends(self, history_data: List[Tuple]) -> Dict[str, Any]:
        """ステータス変化トレンドの分析"""
        if len(history_data) < 3:
            return {"insufficient_data": True}
        
        # データの時系列順に並び替え（古い順）
        sorted_data = sorted(history_data, key=lambda x: x[0])
        
        trends = {
            "active_failed_trend": self._calculate_trend([row[1] for row in sorted_data]),
            "suspended_trend": self._calculate_trend([row[2] for row in sorted_data]),
            "completion_rate_trend": self._calculate_trend([row[4] for row in sorted_data]),
            "overall_direction": "unknown"
        }
        
        # 全体的な傾向の判定
        active_trend = trends["active_failed_trend"]["direction"]
        completion_trend = trends["completion_rate_trend"]["direction"]
        
        if active_trend == "increasing" and completion_trend == "decreasing":
            trends["overall_direction"] = "deteriorating"
        elif active_trend == "decreasing" and completion_trend == "increasing":
            trends["overall_direction"] = "improving"
        elif active_trend == "stable" and completion_trend == "stable":
            trends["overall_direction"] = "stable"
        else:
            trends["overall_direction"] = "mixed"
        
        return trends
    
    def _calculate_trend(self, values: List[float]) -> Dict[str, Any]:
        """数値列のトレンドを計算"""
        if len(values) < 2:
            return {"direction": "unknown", "change_rate": 0, "confidence": 0}
        
        # 線形回帰での傾向計算
        n = len(values)
        x_values = list(range(n))
        
        # 傾きの計算
        x_mean = sum(x_values) / n
        y_mean = sum(values) / n
        
        numerator = sum((x_values[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x_values[i] - x_mean) ** 2 for i in range(n))
        
        if denominator == 0:
            slope = 0
        else:
            slope = numerator / denominator
        
        # 方向の判定
        if abs(slope) < 0.01:  # 閾値以下は安定
            direction = "stable"
        elif slope > 0:
            direction = "increasing"
        else:
            direction = "decreasing"
        
        # 変化率の計算
        if values[0] != 0:
            change_rate = ((values[-1] - values[0]) / values[0]) * 100
        else:
            change_rate = 0
        
        # 信頼度の計算（データ点数と変化の一貫性に基づく）
        confidence = min(100, (n - 1) * 20)  # 最大100%
        
        return {
            "direction": direction,
            "change_rate": change_rate,
            "confidence": confidence,
            "slope": slope
        }
    
    def _predict_status_changes(self, history_data: List[Tuple], service_name: str) -> Dict[str, Any]:
        """ステータス変化の予測"""
        if len(history_data) < 3:
            return {"prediction_available": False}
        
        sorted_data = sorted(history_data, key=lambda x: x[0])
        current_active = sorted_data[-1][1]  # 最新のactive失敗数
        
        # 過去のトレンドから予測
        recent_data = sorted_data[-5:]  # 直近5データポイント
        active_values = [row[1] for row in recent_data]
        
        trend = self._calculate_trend(active_values)
        
        predictions = {
            "prediction_available": True,
            "current_active_failed": current_active,
            "trend_direction": trend["direction"],
            "predicted_scenarios": {}
        }
        
        # シナリオ別予測
        if trend["direction"] == "increasing":
            # 増加傾向の場合
            hourly_increase = abs(trend["slope"])
            predictions["predicted_scenarios"] = {
                "1_hour": {
                    "active_failed": current_active + hourly_increase,
                    "risk_level": "low" if hourly_increase < 10 else "medium"
                },
                "3_hours": {
                    "active_failed": current_active + hourly_increase * 3,
                    "risk_level": "medium" if hourly_increase < 10 else "high"
                },
                "6_hours": {
                    "active_failed": current_active + hourly_increase * 6,
                    "risk_level": "high" if hourly_increase > 5 else "medium"
                }
            }
        elif trend["direction"] == "stable":
            predictions["predicted_scenarios"] = {
                "1_hour": {"active_failed": current_active, "risk_level": "low"},
                "3_hours": {"active_failed": current_active, "risk_level": "low"},
                "6_hours": {"active_failed": current_active, "risk_level": "low"}
            }
        else:  # decreasing
            predictions["predicted_scenarios"] = {
                "1_hour": {"active_failed": max(0, current_active - abs(trend["slope"])), "risk_level": "low"},
                "3_hours": {"active_failed": max(0, current_active - abs(trend["slope"]) * 3), "risk_level": "low"},
                "6_hours": {"active_failed": max(0, current_active - abs(trend["slope"]) * 6), "risk_level": "low"}
            }
        
        # 予測の保存
        self._save_predictions(service_name, predictions)
        
        return predictions
    
    def _save_predictions(self, service_name: str, predictions: Dict[str, Any]) -> None:
        """予測結果をデータベースに保存"""
        if not predictions.get("prediction_available"):
            return
        
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            
            for time_horizon, scenario in predictions["predicted_scenarios"].items():
                confidence = 0.8 if predictions["trend_direction"] == "stable" else 0.6
                
                cursor.execute("""
                    INSERT INTO status_change_predictions 
                    (session_id, service_name, prediction_type, confidence_score,
                     estimated_time_hours, predicted_change_count, factors_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.session_id,
                    service_name,
                    f"active_failed_{time_horizon}",
                    confidence,
                    int(time_horizon.split('_')[0]),
                    scenario["active_failed"],
                    json.dumps({"trend": predictions["trend_direction"], "risk": scenario["risk_level"]})
                ))
    
    def _detect_anomalies(self, history_data: List[Tuple]) -> List[Dict[str, Any]]:
        """異常値の検出"""
        anomalies = []
        
        if len(history_data) < 5:
            return anomalies
        
        sorted_data = sorted(history_data, key=lambda x: x[0])
        
        # active失敗数の異常値検出
        active_values = [row[1] for row in sorted_data]
        avg_active = sum(active_values) / len(active_values)
        std_active = (sum((x - avg_active) ** 2 for x in active_values) / len(active_values)) ** 0.5
        
        for i, row in enumerate(sorted_data):
            active_failed = row[1]
            if abs(active_failed - avg_active) > 2 * std_active:  # 2σ以上の偏差
                anomalies.append({
                    "type": "active_failed_spike",
                    "timestamp": row[0],
                    "value": active_failed,
                    "expected_range": f"{avg_active - 2*std_active:.0f} - {avg_active + 2*std_active:.0f}",
                    "severity": "high" if abs(active_failed - avg_active) > 3 * std_active else "medium"
                })
        
        # 完了率の急激な変化
        completion_rates = [row[4] for row in sorted_data]
        for i in range(1, len(completion_rates)):
            rate_change = abs(completion_rates[i] - completion_rates[i-1])
            if rate_change > 0.1:  # 10%以上の急激な変化
                anomalies.append({
                    "type": "completion_rate_jump",
                    "timestamp": sorted_data[i][0],
                    "value": completion_rates[i],
                    "change": rate_change,
                    "severity": "high" if rate_change > 0.2 else "medium"
                })
        
        return anomalies
    
    def _assess_403_error_risk(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """403エラー発生リスクの評価"""
        risk_factors = []
        risk_score = 0
        
        trends = analysis.get("trends", {})
        predictions = analysis.get("predictions", {})
        anomalies = analysis.get("anomalies", [])
        
        # active失敗数の増加トレンド
        if trends.get("active_failed_trend", {}).get("direction") == "increasing":
            risk_factors.append("Active失敗数の増加傾向")
            risk_score += 30
        
        # 完了率の低下
        if trends.get("completion_rate_trend", {}).get("direction") == "decreasing":
            risk_factors.append("完了率の低下傾向")
            risk_score += 25
        
        # 高リスク予測シナリオ
        if predictions.get("prediction_available"):
            for scenario in predictions.get("predicted_scenarios", {}).values():
                if scenario.get("risk_level") == "high":
                    risk_factors.append("高リスク予測シナリオの存在")
                    risk_score += 20
                    break
        
        # 異常値の存在
        high_severity_anomalies = [a for a in anomalies if a.get("severity") == "high"]
        if high_severity_anomalies:
            risk_factors.append(f"高重要度異常値 ({len(high_severity_anomalies)}件)")
            risk_score += len(high_severity_anomalies) * 15
        
        # リスクレベルの判定
        if risk_score >= 70:
            risk_level = "CRITICAL"
        elif risk_score >= 50:
            risk_level = "HIGH"
        elif risk_score >= 30:
            risk_level = "MEDIUM"
        else:
            risk_level = "LOW"
        
        return {
            "risk_level": risk_level,
            "risk_score": min(100, risk_score),
            "risk_factors": risk_factors,
            "recommendations": self._generate_risk_recommendations(risk_level, risk_factors)
        }
    
    def _generate_risk_recommendations(self, risk_level: str, risk_factors: List[str]) -> List[str]:
        """リスクレベルに基づく推奨事項の生成"""
        recommendations = []
        
        if risk_level == "CRITICAL":
            recommendations.extend([
                "🚨 緊急対応: システム停止を検討",
                "🔍 詳細調査: active失敗の急増原因を特定",
                "🛠️ 即座修正: Cookie再読み込み・ヘッダー変更",
                "📊 監視強化: 1時間以内の再チェック"
            ])
        elif risk_level == "HIGH":
            recommendations.extend([
                "⚠️ 予防的対応: 処理速度の調整",
                "🔄 システム調整: バックオフ時間の延長",
                "📈 監視頻度: 2時間以内の再チェック",
                "🛡️ 対策準備: 緊急停止手順の確認"
            ])
        elif risk_level == "MEDIUM":
            recommendations.extend([
                "📊 継続監視: トレンドの注意深い観察",
                "🔧 予防保守: システム設定の最適化",
                "📅 定期チェック: 4-6時間後の再確認"
            ])
        else:  # LOW
            recommendations.extend([
                "✅ 現状維持: 安定した状態を継続",
                "📋 定期監視: 通常の監視スケジュール"
            ])
        
        # 特定のリスク要因に対する推奨事項
        for factor in risk_factors:
            if "Active失敗数の増加" in factor:
                recommendations.append("🔍 Active失敗の詳細分析: エラータイプの分類確認")
            if "完了率の低下" in factor:
                recommendations.append("📈 処理効率の改善: バッチサイズ・遅延の調整")
            if "高重要度異常値" in factor:
                recommendations.append("🕵️ 異常値調査: 特定時間帯の詳細ログ確認")
        
        return recommendations
    
    def create_status_alert(self, service_name: str, alert_type: str, severity: str,
                           title: str, description: str = "",
                           metrics: Dict = None, predictions: Dict = None) -> None:
        """ユーザーステータス変化アラートの生成"""
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO user_status_alerts 
                (session_id, service_name, alert_type, severity, title, 
                 description, metrics_json, predictions_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                self.session_id,
                service_name,
                alert_type,
                severity,
                title,
                description,
                json.dumps(metrics or {}),
                json.dumps(predictions or {})
            ))
    
    def get_monitoring_summary(self) -> Dict[str, Any]:
        """監視状況の概要取得"""
        with sqlite3.connect(self.db.db_file) as conn:
            cursor = conn.cursor()
            
            # サービス別の最新状況
            cursor.execute("""
                SELECT service_name, active_failed, completion_rate, 
                       MAX(timestamp) as latest_timestamp
                FROM user_status_history 
                WHERE session_id = ?
                GROUP BY service_name
            """, (self.session_id,))
            
            services_status = cursor.fetchall()
            
            # アクティブアラート数
            cursor.execute("""
                SELECT COUNT(*) as total_alerts,
                       COUNT(CASE WHEN severity = 'CRITICAL' THEN 1 END) as critical_alerts,
                       COUNT(CASE WHEN severity = 'HIGH' THEN 1 END) as high_alerts
                FROM user_status_alerts 
                WHERE session_id = ? AND resolved = FALSE
            """, (self.session_id,))
            
            alert_counts = cursor.fetchone()
        
        summary = {
            "session_id": self.session_id,
            "monitoring_active": True,
            "services_monitored": len(services_status),
            "services_status": [
                {
                    "service_name": row[0],
                    "active_failed": row[1],
                    "completion_rate": row[2],
                    "last_updated": datetime.fromtimestamp(row[3]).isoformat()
                }
                for row in services_status
            ],
            "alerts": {
                "total": alert_counts[0] if alert_counts else 0,
                "critical": alert_counts[1] if alert_counts else 0,
                "high": alert_counts[2] if alert_counts else 0
            }
        }
        
        return summary