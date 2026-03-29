#!/bin/bash
# 对照组3 分批拉取用户列表（bash curl，绕过 Python SSL 问题）

AUTH_FILE="$HOME/.claude/skills/cyberdata-query/auth.json"
COOKIES=$(python3 -c "import json; print(json.load(open('$AUTH_FILE'))['cookies'])")
JWTTOKEN=$(python3 -c "import json; print(json.load(open('$AUTH_FILE'))['jwttoken'])")
OUTPUT_FILE="/tmp/control_group3_users.tsv"
BATCH_SIZE=30
TOTAL=0

# 清空输出文件
echo -e "user_no\tab_bash_10000" > "$OUTPUT_FILE"

for START in $(seq 6000 $BATCH_SIZE 9999); do
    END=$((START + BATCH_SIZE - 1))
    if [ $END -gt 9999 ]; then END=9999; fi

    SQL="SELECT g.user_no, l.ab_bash_10000 FROM dw_ads.ads_marketing_t_user_group_d_his g JOIN dw_ads.user_label_df l ON g.user_no = l.user_no AND l.tenant = 'LKUS' AND l.dt = '2026-03-09' WHERE g.tenant = 'LKUS' AND g.dt = '2026-03-09' AND g.group_name = '0212价格实验40%分流对照组3' AND l.ab_bash_10000 BETWEEN $START AND $END"

    TIMESTAMP=$(date +%s)000

    # 提交查询（带重试）
    for ATTEMPT in 1 2 3; do
        RESULT=$(curl -s --connect-timeout 10 --max-time 30 \
            'https://idpcd.luckincoffee.us/api/dev/task/run' \
            -H 'accept: application/json, text/plain, */*' \
            -H 'content-type: application/json; charset=UTF-8' \
            -b "$COOKIES" \
            -H "jwttoken: $JWTTOKEN" \
            -H 'productkey: CyberData' \
            -H 'origin: https://idpcd.luckincoffee.us' \
            --data-raw "{\"_t\":$TIMESTAMP,\"tenantId\":\"1001\",\"userId\":\"47\",\"projectId\":\"1906904360294313985\",\"resourceGroupId\":1,\"taskId\":\"1990991087752757249\",\"variables\":{},\"sqlStatement\":$(echo "$SQL" | python3 -c 'import sys,json; print(json.dumps(sys.stdin.read().strip()))'),\"env\":5}" 2>/dev/null)

        CODE=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code',''))" 2>/dev/null)
        if [ "$CODE" = "200" ]; then break; fi
        echo "  提交重试 $ATTEMPT..."
        sleep 3
    done

    if [ "$CODE" != "200" ]; then
        echo "❌ 桶号 $START-$END 提交失败，跳过"
        continue
    fi

    TASK_ID=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin)['data'])" 2>/dev/null)

    # 等待并获取结果（带重试）
    sleep 6
    for RETRY in 1 2 3 4 5; do
        TIMESTAMP=$(date +%s)000
        QUERY_RESULT=$(curl -s --connect-timeout 10 --max-time 30 \
            'https://idpcd.luckincoffee.us/api/logger/getQueryLog' \
            -H 'accept: application/json, text/plain, */*' \
            -H 'content-type: application/json; charset=UTF-8' \
            -b "$COOKIES" \
            -H "jwttoken: $JWTTOKEN" \
            -H 'productkey: CyberData' \
            -H 'origin: https://idpcd.luckincoffee.us' \
            --data-raw "{\"_t\":$TIMESTAMP,\"tenantId\":\"1001\",\"userId\":\"47\",\"projectId\":\"1906904360294313985\",\"env\":5,\"taskInstanceId\":\"$TASK_ID\"}" 2>/dev/null)

        ROW_COUNT=$(echo "$QUERY_RESULT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
if data.get('code') == '200' and data.get('data'):
    for item in data['data']:
        cols = item.get('columns', [])
        if len(cols) > 1:
            rows = cols[1:]
            for row in rows:
                print('\t'.join(str(c) for c in row))
            print(f'__COUNT__:{len(rows)}', file=sys.stderr)
            sys.exit(0)
print('__COUNT__:0', file=sys.stderr)
" >> "$OUTPUT_FILE" 2>&1)

        # 从输出提取行数
        COUNT=$(grep -o '__COUNT__:[0-9]*' "$OUTPUT_FILE" | tail -1 | cut -d: -f2)
        # 清理标记
        sed -i '' '/__COUNT__/d' "$OUTPUT_FILE"

        if [ -n "$COUNT" ] && [ "$COUNT" -gt 0 ]; then
            TOTAL=$((TOTAL + COUNT))
            WARN=""
            if [ "$COUNT" -ge 500 ]; then WARN=" ⚠️截断"; fi
            echo "桶号${START}-${END}: +${COUNT}条${WARN}, 累计${TOTAL}"
            break
        fi
        sleep 3
    done

    # 请求间隔
    sleep 1
done

echo ""
echo "=========================================="
echo "总计拉取 $TOTAL 条用户记录"
echo "保存到: $OUTPUT_FILE"
echo "=========================================="
