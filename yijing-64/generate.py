#!/usr/bin/env python3
"""
易经64卦 HTML 生成器
用法: python generate.py data/gua/01-qian.json
      python generate.py --all          # 生成所有已有卦
      python generate.py --index        # 仅生成首页
"""

import json
import sys
import os
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

BASE_DIR = Path(__file__).parent
TEMPLATE_DIR = BASE_DIR / 'templates'
DATA_DIR = BASE_DIR / 'data'
DIST_DIR = BASE_DIR / 'dist'
ASSETS_DIR = BASE_DIR / 'assets'


def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def load_meta():
    return load_json(DATA_DIR / 'meta.json')


def read_css():
    css_path = ASSETS_DIR / 'css' / 'yijing.css'
    with open(css_path, 'r', encoding='utf-8') as f:
        return f.read()


def read_js():
    js_path = ASSETS_DIR / 'js' / 'yijing.js'
    with open(js_path, 'r', encoding='utf-8') as f:
        return f.read()


def create_env():
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=False,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    return env


def enrich_relations(gua_data, meta):
    """为 relations 中的 prev/next 注入 pinyin，用于生成文件名链接"""
    name_to_pinyin = {h['name']: h['pinyin'].replace(' ', '-') for h in meta['hexagrams']}
    relations = gua_data.get('relations', {})
    for key in ('prev', 'next'):
        rel = relations.get(key)
        if rel and 'name' in rel:
            rel['pinyin'] = name_to_pinyin.get(rel['name'], rel['name'])


def generate_gua_page(gua_data, env, meta):
    """生成单卦详情页"""
    template = env.get_template('gua-detail.html')
    css = read_css()
    js = read_js()

    enrich_relations(gua_data, meta)

    html = template.render(
        gua=gua_data,
        meta=meta,
        css=css,
        js=js,
    )

    # 输出文件
    number = gua_data['meta']['number']
    pinyin = gua_data['meta']['pinyin'].replace(' ', '-')
    filename = f"{number:02d}-{pinyin}.html"
    out_path = DIST_DIR / filename

    DIST_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  生成: {out_path}")
    return out_path


def generate_index(env, meta, available_gua):
    """生成首页/64卦导航"""
    template = env.get_template('index.html')
    css = read_css()
    js = read_js()

    html = template.render(
        meta=meta,
        css=css,
        js=js,
        available_gua=available_gua,
    )

    out_path = DIST_DIR / 'index.html'
    DIST_DIR.mkdir(parents=True, exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"  生成: {out_path}")
    return out_path


def find_available_gua():
    """查找已有的卦数据文件"""
    gua_dir = DATA_DIR / 'gua'
    available = []
    if gua_dir.exists():
        for f in sorted(gua_dir.glob('*.json')):
            data = load_json(f)
            available.append({
                'number': data['meta']['number'],
                'name': data['meta']['name'],
                'pinyin': data['meta']['pinyin'].replace(' ', '-'),
                'fullName': data['meta']['fullName'],
                'file': str(f),
            })
    return available


def main():
    env = create_env()
    meta = load_meta()

    if len(sys.argv) < 2:
        print("用法:")
        print("  python generate.py data/gua/01-qian.json  # 生成指定卦")
        print("  python generate.py --all                   # 生成所有卦+首页")
        print("  python generate.py --index                 # 仅生成首页")
        sys.exit(1)

    arg = sys.argv[1]

    if arg == '--all':
        available = find_available_gua()
        print(f"找到 {len(available)} 卦数据文件")
        for gua_info in available:
            gua_data = load_json(gua_info['file'])
            generate_gua_page(gua_data, env, meta)
        generate_index(env, meta, available)
        print(f"\n完成！共生成 {len(available)} 个卦页面 + 1 个首页")

    elif arg == '--index':
        available = find_available_gua()
        generate_index(env, meta, available)

    else:
        # 生成指定卦
        gua_path = Path(arg)
        if not gua_path.exists():
            gua_path = BASE_DIR / arg
        if not gua_path.exists():
            print(f"文件不存在: {arg}")
            sys.exit(1)

        gua_data = load_json(gua_path)
        available = find_available_gua()
        generate_gua_page(gua_data, env, meta)
        generate_index(env, meta, available)
        print("\n完成！")


if __name__ == '__main__':
    main()
