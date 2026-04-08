#!/usr/bin/env python3
"""
Lucky US 日报 → 飞书群推送
从 daily_report.py 复用查询逻辑，格式化后通过飞书 webhook 发送到群。

Usage:
    python send_to_feishu.py            # 推送昨天的日报（默认对比近3天）
    python send_to_feishu.py -n 5       # 推送近5天数据
    python send_to_feishu.py --dry-run  # 只生成不发送，用于调试
"""

import json
import os
import sys
import requests
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONFIG_FILE = os.path.join(BASE_DIR, "config-配置", "feishu_config.json")

sys.path.insert(0, SCRIPT_DIR)
from daily_report import (
    get_recent_dates,
    query_business_metrics,
    query_user_metrics,
    query_funnel_metrics,
    query_product_penetration,
)


def load_webhook_url():
    with open(CONFIG_FILE) as f:
        return json.load(f)["webhook_url"]


def fmt_num(v, style="int"):
    """格式化数字"""
    if v is None or (hasattr(v, '__class__') and v.__class__.__name__ == 'float' and v != v):
        return "-"
    if style == "int":
        return f"{int(v):,}"
    if style == "pct":
        return f"{v:.1f}%"
    if style == "dollar":
        return f"${v:.2f}"
    if style == "f1":
        return f"{v:.1f}"
    return str(v)


def dod(cur, prev):
    """日环比"""
    if not prev or prev == 0:
        return ""
    change = (cur - prev) / prev * 100
    arrow = "↑" if change > 0 else "↓" if change < 0 else "→"
    return f" {arrow}{abs(change):.1f}%"


def build_report_text(dates):
    """查询数据并构建纯文本报告"""

    lines = []
    lines.append(f"📊 Lucky US 日报 — {dates[-1]}")
    lines.append(f"对比: {dates[0]} ~ {dates[-1]}")
    lines.append("")

    # ── 模块1: 业务结果 ──
    biz = query_business_metrics(dates)
    if not biz.empty:
        lines.append("━━ 业务结果 ━━")
        last = biz.iloc[-1]
        prev = biz.iloc[-2] if len(biz) >= 2 else None

        rows = [
            ("杯量", "杯量", "int"),
            ("店日均杯量", "店日均杯量", "int"),
            ("单杯实收", "单杯实收", "dollar"),
            ("订单数", "订单数", "int"),
            ("销售额", "销售额", "dollar"),
        ]
        for label, col, style in rows:
            if col in biz.columns:
                val = last[col]
                change = dod(val, prev[col]) if prev is not None and col in prev.index else ""
                lines.append(f"  {label}: {fmt_num(val, style)}{change}")
        lines.append("")

    # ── 模块2: 用户 ──
    usr = query_user_metrics(dates)
    if not usr.empty:
        lines.append("━━ 用户 ━━")
        last = usr.iloc[-1]
        prev = usr.iloc[-2] if len(usr) >= 2 else None

        rows = [
            ("注册用户", "注册用户数", "int"),
            ("新客", "新客数", "int"),
            ("老客", "老客数", "int"),
            ("新客占比", "新客占比", "pct"),
            ("店日均新客", "店日均新客", "f1"),
            ("新客7日留存", "新客7日留存率", "pct"),
            ("老客7日留存", "老客7日留存率", "pct"),
        ]
        for label, col, style in rows:
            if col in usr.columns:
                val = last[col]
                change = dod(val, prev[col]) if prev is not None and col in prev.index else ""
                lines.append(f"  {label}: {fmt_num(val, style)}{change}")
        lines.append("")

    # ── 模块3: 漏斗 ──
    funnel = query_funnel_metrics(dates)
    if not funnel.empty:
        lines.append("━━ 漏斗转化 ━━")
        last = funnel.iloc[-1]
        prev = funnel.iloc[-2] if len(funnel) >= 2 else None

        rows = [
            ("Menu→详情", "Menu转化率", "pct"),
            ("详情→确认", "商品详情页转化率", "pct"),
            ("确认→支付", "确认订单转化率", "pct"),
        ]
        for label, col, style in rows:
            if col in funnel.columns:
                val = last[col]
                change = dod(val, prev[col]) if prev is not None and col in prev.index else ""
                lines.append(f"  {label}: {fmt_num(val, style)}{change}")
        lines.append("")

    # ── 模块4: 商品渗透 ──
    prod = query_product_penetration(dates)
    if not prod.empty:
        lines.append("━━ 核心商品渗透 ━━")
        last = prod.iloc[-1]
        prev = prod.iloc[-2] if len(prod) >= 2 else None

        for p in ['Coconut', 'Cold Brew', 'Pineapple', 'Matcha', 'Velvet']:
            col = f'{p}渗透率'
            if col in prod.columns:
                val = last[col]
                change = dod(val, prev[col]) if prev is not None and col in prev.index else ""
                lines.append(f"  {p}: {fmt_num(val, 'pct')}{change}")
        lines.append("")

    lines.append(f"⏱ 生成于 {datetime.now().strftime('%H:%M')}")

    return "\n".join(lines)


def send_feishu(webhook_url, text):
    """发送文本消息到飞书群"""
    payload = {
        "msg_type": "text",
        "content": {
            "text": text
        }
    }
    resp = requests.post(webhook_url, json=payload, timeout=10)
    result = resp.json()
    if result.get("code") != 0:
        raise RuntimeError(f"飞书发送失败: {result}")
    print(f"✅ 飞书推送成功")
    return result


def main():
    import argparse

    parser = argparse.ArgumentParser(description='日报飞书推送')
    parser.add_argument('-n', '--num-days', type=int, default=3,
                        help='分析最近N天 (默认: 3)')
    parser.add_argument('-d', '--dates', nargs='+',
                        help='指定日期 YYYY-MM-DD')
    parser.add_argument('--dry-run', action='store_true',
                        help='只生成报告不发送')

    args = parser.parse_args()

    dates = args.dates if args.dates else get_recent_dates(args.num_days)
    print(f"分析日期: {dates}")

    text = build_report_text(dates)

    print("\n" + "=" * 50)
    print(text)
    print("=" * 50)

    if args.dry_run:
        print("\n🔕 dry-run 模式，未发送")
        return

    webhook_url = load_webhook_url()
    send_feishu(webhook_url, text)


if __name__ == "__main__":
    main()
