#!/usr/bin/env python3
"""对照组3 奇偶桶号切分 → 导出Excel（用curl绕过Python SSL问题）"""

import json
import time
import subprocess
import os

auth_file = os.path.expanduser("~/.claude/skills/cyberdata-query/auth.json")
with open(auth_file) as f:
    auth = json.load(f)

COOKIES = auth['cookies']
JWTTOKEN = auth['jwttoken']
BASE_URL = 'https://idpcd.luckincoffee.us'


def curl_post(url, payload):
    """用 curl 发 POST 请求"""
    cmd = [
        'curl', '-s', '--connect-timeout', '15', '--max-time', '30',
        url,
        '-H', 'accept: application/json, text/plain, */*',
        '-H', 'content-type: application/json; charset=UTF-8',
        '-b', COOKIES,
        '-H', f'jwttoken: {JWTTOKEN}',
        '-H', 'productkey: CyberData',
        '-H', f'origin: {BASE_URL}',
        '--data-raw', json.dumps(payload)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout)


def run_sql(sql, wait=7, max_retries=6):
    """提交SQL并获取结果"""
    payload = {
        "_t": int(time.time() * 1000),
        "tenantId": "1001", "userId": "47",
        "projectId": "1906904360294313985",
        "resourceGroupId": 1,
        "taskId": "1990991087752757249",
        "variables": {},
        "sqlStatement": sql,
        "env": 5
    }

    # 提交（带重试）
    for attempt in range(3):
        try:
            data = curl_post(f"{BASE_URL}/api/dev/task/run", payload)
            if data.get('code') == '200':
                break
        except Exception as e:
            if attempt == 2:
                raise
            print(f"    提交重试 {attempt+1}: {e}")
            time.sleep(5)

    task_id = data['data']

    # 获取结果（带重试）
    for attempt in range(max_retries):
        time.sleep(wait)
        try:
            payload2 = {
                "_t": int(time.time() * 1000),
                "tenantId": "1001", "userId": "47",
                "projectId": "1906904360294313985",
                "env": 5,
                "taskInstanceId": task_id
            }
            result = curl_post(f"{BASE_URL}/api/logger/getQueryLog", payload2)
            if result.get('code') == '200' and result.get('data'):
                for item in result['data']:
                    cols = item.get('columns', [])
                    if cols and len(cols) > 1:
                        return cols[0], cols[1:]
        except Exception as e:
            print(f"    获取重试 {attempt+1}: {e}")
        wait = min(wait + 2, 15)

    raise Exception(f"查询超时, task_id={task_id}")


def main():
    print("=" * 60)
    print("对照组3 奇偶桶号切分 → 导出Excel")
    print("=" * 60)

    # 断点续传
    progress_file = "/tmp/control_group_split_progress.json"
    all_users = []
    start_from = 6000

    if os.path.exists(progress_file):
        with open(progress_file) as f:
            progress = json.load(f)
        all_users = progress.get('users', [])
        start_from = progress.get('next_start', 6000)
        print(f"恢复进度: 已有 {len(all_users)} 用户, 从桶号 {start_from} 继续")

    BATCH_SIZE = 30
    batch_num = 0
    failed_batches = []

    for start in range(start_from, 10000, BATCH_SIZE):
        end = min(start + BATCH_SIZE - 1, 9999)
        batch_num += 1

        sql = f"""
        SELECT g.user_no, l.ab_bash_10000
        FROM dw_ads.ads_marketing_t_user_group_d_his g
        JOIN dw_ads.user_label_df l
          ON g.user_no = l.user_no AND l.tenant = 'LKUS' AND l.dt = '2026-03-09'
        WHERE g.tenant = 'LKUS' AND g.dt = '2026-03-09'
          AND g.group_name = '0212价格实验40%分流对照组3'
          AND l.ab_bash_10000 BETWEEN {start} AND {end}
        """

        try:
            header, rows = run_sql(sql, wait=7)
            batch_count = len(rows)
            all_users.extend(rows)
            warn = " ⚠️截断!" if batch_count >= 500 else ""
            print(f"  批次{batch_num}: 桶号{start}-{end}, +{batch_count}{warn}, 累计{len(all_users)}")
        except Exception as e:
            print(f"  ❌ 批次{batch_num} (桶号{start}-{end}): {e}")
            failed_batches.append((start, end))
            # 保存进度并继续（不中断）
            with open(progress_file, 'w') as f:
                json.dump({'users': all_users, 'next_start': end + 1}, f)

        # 每20批保存进度
        if batch_num % 20 == 0:
            with open(progress_file, 'w') as f:
                json.dump({'users': all_users, 'next_start': end + 1}, f)
            print(f"  --- 进度已保存 ({len(all_users)} 用户) ---")

        time.sleep(1.5)

    # 重试失败的批次
    if failed_batches:
        print(f"\n重试 {len(failed_batches)} 个失败批次...")
        time.sleep(5)
        for start, end in failed_batches:
            sql = f"""
            SELECT g.user_no, l.ab_bash_10000
            FROM dw_ads.ads_marketing_t_user_group_d_his g
            JOIN dw_ads.user_label_df l
              ON g.user_no = l.user_no AND l.tenant = 'LKUS' AND l.dt = '2026-03-09'
            WHERE g.tenant = 'LKUS' AND g.dt = '2026-03-09'
              AND g.group_name = '0212价格实验40%分流对照组3'
              AND l.ab_bash_10000 BETWEEN {start} AND {end}
            """
            try:
                header, rows = run_sql(sql, wait=10)
                all_users.extend(rows)
                print(f"  ✅ 重试成功: 桶号{start}-{end}, +{len(rows)}条")
            except Exception as e:
                print(f"  ❌ 重试仍失败: 桶号{start}-{end}: {e}")
            time.sleep(2)

    print(f"\n总计获取 {len(all_users)} 个用户")

    # 去重（以防重试导致重复）
    seen = set()
    unique_users = []
    for row in all_users:
        if row[0] not in seen:
            seen.add(row[0])
            unique_users.append(row)
    print(f"去重后: {len(unique_users)} 个用户")

    # 切分
    group_a, group_b = [], []
    for row in unique_users:
        user_no, bucket = row[0], int(row[1])
        entry = {'user_no': user_no, 'ab_bash_10000': bucket,
                 'sub_group': 'A_偶数桶' if bucket % 2 == 0 else 'B_奇数桶'}
        (group_a if bucket % 2 == 0 else group_b).append(entry)

    print(f"子组A (偶数桶): {len(group_a)} 人")
    print(f"子组B (奇数桶): {len(group_b)} 人")

    # 导出 Excel
    import openpyxl
    output_dir = os.path.expanduser("~/Downloads")

    def save_excel(data, filename, sheet_name):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = sheet_name
        ws.append(['user_no', 'ab_bash_10000', 'sub_group'])
        for u in data:
            ws.append([u['user_no'], u['ab_bash_10000'], u['sub_group']])
        path = os.path.join(output_dir, filename)
        wb.save(path)
        return path

    p1 = save_excel(group_a, "对照组3_子组A_偶数桶.xlsx", "子组A_偶数桶")
    print(f"\n✅ 子组A: {p1} ({len(group_a)}人)")
    p2 = save_excel(group_b, "对照组3_子组B_奇数桶.xlsx", "子组B_奇数桶")
    print(f"✅ 子组B: {p2} ({len(group_b)}人)")
    p3 = save_excel(group_a + group_b, "对照组3_切分汇总.xlsx", "对照组3_切分汇总")
    print(f"✅ 汇总表: {p3} ({len(group_a)+len(group_b)}人)")

    # 清理进度文件
    if os.path.exists(progress_file):
        os.remove(progress_file)

    print(f"\n{'=' * 60}")
    print("完成！3个文件已保存到 ~/Downloads/")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
