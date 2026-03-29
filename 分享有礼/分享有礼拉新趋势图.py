#!/usr/bin/env python3
"""分享有礼拉新趋势图"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
plt.rcParams['axes.unicode_minus'] = False

# 数据
dates = [
    '2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05',
    '2026-01-06', '2026-01-07', '2026-01-08', '2026-01-09', '2026-01-10',
    '2026-01-11', '2026-01-12', '2026-01-13', '2026-01-14', '2026-01-15',
    '2026-01-16', '2026-01-17', '2026-01-18', '2026-01-19', '2026-01-20',
    '2026-01-21', '2026-01-22', '2026-01-23', '2026-01-24', '2026-01-25',
    '2026-01-26', '2026-01-27', '2026-01-28', '2026-01-29', '2026-01-30',
    '2026-01-31'
]

share_new_users = [
    33, 42, 40, 34, 37, 38, 37, 62, 31, 26,
    35, 35, 31, 31, 45, 48, 46, 41, 43, 38,
    42, 54, 34, 22, 7, 18, 30, 42, 43, 26, 26
]

total_new_users = [
    629, 644, 683, 535, 484, 567, 634, 663, 584, 612,
    687, 503, 590, 564, 617, 564, 594, 577, 544, 433,
    481, 624, 443, 458, 140, 206, 333, 351, 455, 410, 519
]

ratio = [s/t*100 for s, t in zip(share_new_users, total_new_users)]

# 转换日期
date_objects = [datetime.strptime(d, '%Y-%m-%d') for d in dates]

# 创建图表
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# 图1：拉新人数趋势
ax1.plot(date_objects, share_new_users, marker='o', linewidth=2,
         label='分享有礼拉新', color='#FF6B6B', markersize=6)
ax1.plot(date_objects, total_new_users, marker='s', linewidth=2,
         label='大盘拉新', color='#4ECDC4', markersize=5, alpha=0.7)

# 添加平均线
avg_share = np.mean(share_new_users)
avg_total = np.mean(total_new_users)
ax1.axhline(y=avg_share, color='#FF6B6B', linestyle='--', alpha=0.5,
            label=f'分享有礼日均: {avg_share:.0f}人')
ax1.axhline(y=avg_total, color='#4ECDC4', linestyle='--', alpha=0.5,
            label=f'大盘日均: {avg_total:.0f}人')

ax1.set_ylabel('拉新人数', fontsize=12, fontweight='bold')
ax1.set_title('分享有礼活动拉新效果分析（2026年1月，完单口径）',
              fontsize=14, fontweight='bold', pad=20)
ax1.legend(loc='upper left', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.set_ylim(0, max(total_new_users) * 1.1)

# 图2：占比趋势
ax2.bar(date_objects, ratio, color='#95E1D3', alpha=0.7, label='占比')
ax2.plot(date_objects, ratio, marker='o', linewidth=2, color='#F38181',
         label='占比趋势线', markersize=5)

# 添加平均占比线
avg_ratio = np.mean(ratio)
ax2.axhline(y=avg_ratio, color='#F38181', linestyle='--', alpha=0.5,
            label=f'平均占比: {avg_ratio:.2f}%')

ax2.set_xlabel('日期', fontsize=12, fontweight='bold')
ax2.set_ylabel('分享有礼占比 (%)', fontsize=12, fontweight='bold')
ax2.legend(loc='upper left', fontsize=10)
ax2.grid(True, alpha=0.3, axis='y')
ax2.set_ylim(0, max(ratio) * 1.2)

# 格式化x轴日期
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax2.xaxis.set_major_locator(mdates.DayLocator(interval=2))
plt.xticks(rotation=45, ha='right')

# 添加数据标注
plt.tight_layout()

# 保存图片
output_path = '/Users/xiaoxiao/Vibe coding/分享有礼拉新趋势图.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"趋势图已保存到: {output_path}")

# 显示图表
plt.show()
