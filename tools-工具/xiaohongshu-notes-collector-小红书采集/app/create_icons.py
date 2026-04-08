#!/usr/bin/env python3
"""
简单的图标生成脚本
为小红书笔记采集器生成基本图标
"""

from PIL import Image, ImageDraw, ImageFont
import os

def create_icon(size, filename):
    """创建指定尺寸的图标"""
    # 创建图像（红色背景）
    img = Image.new('RGB', (size, size), color='#FF2442')
    draw = ImageDraw.Draw(img)

    # 绘制白色圆角矩形
    margin = size // 8
    draw.rounded_rectangle(
        [margin, margin, size - margin, size - margin],
        radius=size // 10,
        fill='white',
        outline='#FF2442',
        width=2
    )

    # 绘制一个简单的笔记本图标
    center_x = size // 2
    center_y = size // 2

    # 绘制笔记本线条
    line_width = max(1, size // 40)
    line_length = size // 3
    line_spacing = size // 8

    for i in range(3):
        y = center_y - line_spacing + (i * line_spacing // 2)
        draw.line(
            [center_x - line_length // 2, y, center_x + line_length // 2, y],
            fill='#FF2442',
            width=line_width
        )

    # 保存图标
    icons_dir = os.path.join(os.path.dirname(__file__), 'icons')
    os.makedirs(icons_dir, exist_ok=True)

    filepath = os.path.join(icons_dir, filename)
    img.save(filepath, 'PNG')
    print(f'✅ 创建图标: {filename} ({size}x{size})')

def main():
    """主函数"""
    print('开始生成图标...\n')

    try:
        # 生成三个不同尺寸的图标
        create_icon(16, 'icon16.png')
        create_icon(48, 'icon48.png')
        create_icon(128, 'icon128.png')

        print('\n✅ 所有图标生成完成！')
        print('图标位置: icons/ 目录')

    except Exception as e:
        print(f'\n❌ 生成图标时出错: {e}')
        print('\n备选方案：')
        print('1. 安装 Pillow 库: pip3 install Pillow')
        print('2. 或手动创建 16x16, 48x48, 128x128 的 PNG 图标文件')

if __name__ == '__main__':
    main()
