#!/bin/bash
# Cinnamonサーバー継続的監視スクリプト

echo "=== CINNAMON SERVER CONTINUOUS MONITORING STARTED ==="
echo "Start time: $(date '+%Y-%m-%d %H:%M:%S')"
echo "Monitoring will run indefinitely with adaptive intervals (5-30 minutes)"
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECK_CINNAMON_SCRIPT="$SCRIPT_DIR/check-cinnamon"

# 無限ループ
while true; do
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🔄 Executing check-cinnamon at $(date '+%Y-%m-%d %H:%M:%S')"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # check-cinnamonの実行と出力の保存
    OUTPUT=$("$CHECK_CINNAMON_SCRIPT" 2>&1)
    EXIT_CODE=$?
    
    # 出力を表示
    echo "$OUTPUT"
    
    # スクリプト実行エラーのチェック
    if [ $EXIT_CODE -ne 0 ]; then
        echo "⚠️ WARNING: check-cinnamon script failed with exit code $EXIT_CODE"
        NEXT_INTERVAL="5 minutes"
    else
        # 次回実行間隔の抽出（改良版の正規表現）
        NEXT_INTERVAL=$(echo "$OUTPUT" | grep -E "Next check recommended:.*\(適応的間隔: ([0-9]+ minutes)\)" | sed -E 's/.*適応的間隔: ([0-9]+ minutes).*/\1/' | tail -1)
        
        # フォールバック処理
        if [ -z "$NEXT_INTERVAL" ] || ! [[ "$NEXT_INTERVAL" =~ ^[0-9]+\ minutes$ ]]; then
            # ヘルススコアから間隔を決定
            HEALTH_SCORE=$(echo "$OUTPUT" | grep "Overall Health Score:" | grep -o '[0-9]*' | head -1)
            
            if [ -n "$HEALTH_SCORE" ]; then
                if [ "$HEALTH_SCORE" -lt 50 ]; then
                    NEXT_INTERVAL="5 minutes"
                elif [ "$HEALTH_SCORE" -lt 80 ]; then
                    NEXT_INTERVAL="10 minutes"
                else
                    NEXT_INTERVAL="30 minutes"
                fi
                echo "ℹ️ Using health score ($HEALTH_SCORE/100) to determine interval: $NEXT_INTERVAL"
            else
                # デフォルト値
                NEXT_INTERVAL="10 minutes"
                echo "ℹ️ Using default interval: $NEXT_INTERVAL"
            fi
        fi
    fi
    
    # 重要なアラートのチェック
    if echo "$OUTPUT" | grep -q "🚨 URGENT\|🔴 HIGH RISK\|ATTENTION_REQUIRED"; then
        echo
        echo "🚨 ALERT: Critical issues detected! Next check in $NEXT_INTERVAL"
        echo
    fi
    
    # 秒数に変換
    INTERVAL_SECONDS=$(echo "$NEXT_INTERVAL" | awk '{print $1 * 60}')
    
    echo
    echo "📊 Monitoring Summary:"
    echo "  • Current time: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "  • Next check: $(date -d "+$INTERVAL_SECONDS seconds" '+%Y-%m-%d %H:%M:%S')"
    echo "  • Interval: $NEXT_INTERVAL"
    echo
    echo "💤 Sleeping for $NEXT_INTERVAL..."
    echo
    
    # 次回実行まで待機（timeoutコマンドで実装）
    timeout $INTERVAL_SECONDS sleep infinity || true
done