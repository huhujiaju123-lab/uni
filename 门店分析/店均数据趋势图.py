#!/usr/bin/env python3
"""店均新客数据趋势图（2025年12月-2026年1月）"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import numpy as np

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'SimHei', 'STHeiti']
plt.rcParams['axes.unicode_minus'] = False

# 数据（按时间顺序排列）
dates_str = [
    '2025-12-01', '2025-12-02', '2025-12-03', '2025-12-04', '2025-12-05',
    '2025-12-06', '2025-12-07', '2025-12-08', '2025-12-09', '2025-12-10',
    '2025-12-11', '2025-12-12', '2025-12-13', '2025-12-14', '2025-12-15',
    '2025-12-16', '2025-12-17', '2025-12-18', '2025-12-19', '2025-12-20',
    '2025-12-21', '2025-12-22', '2025-12-23', '2025-12-24', '2025-12-25',
    '2025-12-26', '2025-12-27', '2025-12-28', '2025-12-29', '2025-12-30',
    '2025-12-31',
    '2026-01-01', '2026-01-02', '2026-01-03', '2026-01-04', '2026-01-05',
    '2026-01-06', '2026-01-07', '2026-01-08', '2026-01-09', '2026-01-10',
    '2026-01-11', '2026-01-12', '2026-01-13', '2026-01-14', '2026-01-15',
    '2026-01-16', '2026-01-17', '2026-01-18', '2026-01-19', '2026-01-20',
    '2026-01-21', '2026-01-22', '2026-01-23', '2026-01-24', '2026-01-25',
    '2026-01-26', '2026-01-27', '2026-01-28', '2026-01-29', '2026-01-30',
    '2026-01-31'
]

# 店均新客数
new_customers = [
    92.57, 71.43, 103.29, 81.14, 69.43, 95.86, 72.29, 63.71, 76.71, 74.29,
    74.86, 57.86, 87.86, 60.50, 84.89, 92.00, 94.11, 93.78, 68.11, 107.22,
    93.44, 77.33, 66.11, 66.56, 95.43, 64.00, 64.11, 66.89, 66.22, 74.56,
    71.00,
    69.89, 71.56, 85.38, 59.44, 53.78, 63.00, 70.44, 73.67, 64.89, 68.00,
    76.33, 55.89, 65.56, 62.67, 68.56, 62.67, 66.00, 64.11, 60.44, 48.11,
    53.44, 69.33, 49.22, 50.89, 23.33, 29.43, 41.63, 43.88, 50.56, 45.56,
    57.67
]

# 店均用户数
total_customers = [
    389.43, 324.86, 432.86, 382.57, 310.29, 274.71, 230.86, 344.29, 377.29, 400.86,
    376.43, 290.14, 252.29, 175.50, 265.22, 314.33, 345.89, 332.22, 226.78, 250.78,
    205.89, 258.22, 210.89, 194.89, 183.43, 170.78, 146.33, 155.78, 199.78, 220.11,
    215.67,
    158.44, 205.44, 207.38, 178.22, 269.78, 309.11, 322.78, 339.44, 288.00, 208.11,
    213.33, 283.78, 319.33, 320.22, 318.67, 275.56, 197.67, 184.22, 221.67, 297.56,
    328.11, 349.56, 274.78, 177.44, 79.67, 135.86, 285.50, 300.00, 307.78, 254.67,
    199.44
]

# 新客占比
ratio = [
    23.77, 21.99, 23.86, 21.21, 22.38, 34.89, 31.31, 18.51, 20.33, 18.53,
    19.89, 19.94, 34.82, 34.47, 32.01, 29.27, 27.21, 28.23, 30.03, 42.76,
    45.39, 29.95, 31.35, 34.15, 52.02, 37.48, 43.81, 42.94, 33.15, 33.87,
    32.92,
    44.11, 34.83, 41.17, 33.35, 19.93, 20.38, 21.82, 21.70, 22.53, 32.67,
    35.78, 19.69, 20.53, 19.57, 21.51, 22.74, 33.39, 34.80, 27.27, 16.17,
    16.29, 19.83, 17.91, 28.68, 29.29, 21.66, 14.58, 14.63, 16.43, 17.89,
    28.91
]

# 转换日期
date_objects = [datetime.strptime(d, '%Y-%m-%d') for d in dates_str]

# 创建图表
fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)

# 计算12月和1月的平均值
dec_end_idx = 31
dec_avg_new = np.mean(new_customers[:dec_end_idx])
jan_avg_new = np.mean(new_customers[dec_end_idx:])
dec_avg_total = np.mean(total_customers[:dec_end_idx])
jan_avg_total = np.mean(total_customers[dec_end_idx:])
dec_avg_ratio = np.mean(ratio[:dec_end_idx])
jan_avg_ratio = np.mean(ratio[dec_end_idx:])

# 图1：店均新客数趋势
ax1 = axes[0]
ax1.plot(date_objects, new_customers, marker='o', linewidth=2.5,
         label='店均新客数', color='#FF6B6B', markersize=5)
ax1.axvline(x=datetime(2025, 12, 31, 23, 59, 59), color='gray',
            linestyle='--', alpha=0.5, linewidth=1.5, label='月份分界')
ax1.axhline(y=dec_avg_new, color='#FF6B6B', linestyle=':', alpha=0.4,
            label=f'12月均值: {dec_avg_new:.1f}人', linewidth=2)
ax1.axhline(y=jan_avg_new, color='#FF6B6B', linestyle=':', alpha=0.4,
            label=f'1月均值: {jan_avg_new:.1f}人', linewidth=2)
ax1.set_ylabel('店均新客数（人/店）', fontsize=13, fontweight='bold')
ax1.set_title('Lucky US 店均数据趋势分析（2025年12月-2026年1月）',
              fontsize=16, fontweight='bold', pad=20)
ax1.legend(loc='upper right', fontsize=10)
ax1.grid(True, alpha=0.3)
ax1.set_ylim(0, max(new_customers) * 1.15)

# 标注关键点
max_idx = new_customers.index(max(new_customers))
min_idx = new_customers.index(min(new_customers))
ax1.annotate(f'最高: {new_customers[max_idx]:.1f}人\n({dates_str[max_idx]})',
             xy=(date_objects[max_idx], new_customers[max_idx]),
             xytext=(10, 20), textcoords='offset points',
             fontsize=9, color='#FF6B6B', fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='yellow', alpha=0.3),
             arrowprops=dict(arrowstyle='->', color='#FF6B6B', lw=1.5))
ax1.annotate(f'最低: {new_customers[min_idx]:.1f}人\n({dates_str[min_idx]})',
             xy=(date_objects[min_idx], new_customers[min_idx]),
             xytext=(10, -30), textcoords='offset points',
             fontsize=9, color='#FF6B6B', fontweight='bold',
             bbox=dict(boxstyle='round,pad=0.5', facecolor='lightblue', alpha=0.3),
             arrowprops=dict(arrowstyle='->', color='#FF6B6B', lw=1.5))

# 图2：店均用户数趋势
ax2 = axes[1]
ax2.plot(date_objects, total_customers, marker='s', linewidth=2.5,
         label='店均用户数', color='#4ECDC4', markersize=4, alpha=0.8)
ax2.axvline(x=datetime(2025, 12, 31, 23, 59, 59), color='gray',
            linestyle='--', alpha=0.5, linewidth=1.5, label='月份分界')
ax2.axhline(y=dec_avg_total, color='#4ECDC4', linestyle=':', alpha=0.4,
            label=f'12月均值: {dec_avg_total:.1f}人', linewidth=2)
ax2.axhline(y=jan_avg_total, color='#4ECDC4', linestyle=':', alpha=0.4,
            label=f'1月均值: {jan_avg_total:.1f}人', linewidth=2)
ax2.set_ylabel('店均用户数（人/店）', fontsize=13, fontweight='bold')
ax2.legend(loc='upper right', fontsize=10)
ax2.grid(True, alpha=0.3)
ax2.set_ylim(0, max(total_customers) * 1.15)

# 图3：新客占比趋势
ax3 = axes[2]
ax3.bar(date_objects, ratio, color='#95E1D3', alpha=0.6, label='新客占比')
ax3.plot(date_objects, ratio, marker='o', linewidth=2, color='#F38181',
         label='趋势线', markersize=4)
ax3.axvline(x=datetime(2025, 12, 31, 23, 59, 59), color='gray',
            linestyle='--', alpha=0.5, linewidth=1.5, label='月份分界')
ax3.axhline(y=dec_avg_ratio, color='#F38181', linestyle=':', alpha=0.4,
            label=f'12月均值: {dec_avg_ratio:.1f}%', linewidth=2)
ax3.axhline(y=jan_avg_ratio, color='#F38181', linestyle=':', alpha=0.4,
            label=f'1月均值: {jan_avg_ratio:.1f}%', linewidth=2)
ax3.set_xlabel('日期', fontsize=13, fontweight='bold')
ax3.set_ylabel('新客占比 (%)', fontsize=13, fontweight='bold')
ax3.legend(loc='upper right', fontsize=10)
ax3.grid(True, alpha=0.3, axis='y')
ax3.set_ylim(0, max(ratio) * 1.15)

# 格式化x轴日期
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
ax3.xaxis.set_major_locator(mdates.DayLocator(interval=3))
plt.xticks(rotation=45, ha='right')

# 调整布局
plt.tight_layout()

# 保存图片
output_path = '/Users/xiaoxiao/Vibe coding/店均数据趋势图.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"趋势图已保存到: {output_path}")

# 显示图表
plt.show()
