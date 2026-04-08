#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
电商套件库存自动计算系统 (ICAS) - Streamlit Web版
Inventory Calculation for Assembled Sets
"""

import streamlit as st
import pandas as pd
import re
from typing import Dict, Optional
from dataclasses import dataclass
from io import BytesIO

# =============================================================================
# 页面配置
# =============================================================================

st.set_page_config(
    page_title="套件库存计算系统",
    page_icon="📦",
    layout="wide"
)

# 设置中文字体支持
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Noto Sans SC', 'Microsoft YaHei', 'SimHei', sans-serif;
    }

    .stDataFrame {
        font-family: 'Noto Sans SC', 'Microsoft YaHei', 'SimHei', sans-serif;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# 数据结构定义
# =============================================================================

@dataclass
class ComponentSpec:
    """零部件规格"""
    type: str
    size: str
    color: str


@dataclass
class BOMItem:
    """套件BOM"""
    sheet_type: str
    sheet_size: str
    duvet_size: str
    pillow_count: int


# =============================================================================
# 在售颜色配置
# =============================================================================

DEFAULT_ACTIVE_COLORS = [
    '木青绿四季款',
    '米白四季款',
    '丁香紫四季款',
    '雨雾蓝四季款',
    '羊绒棕四季款',
    '暮云粉四季款',
    '繁星黄加暖款',
    '暮光褐加暖款',
    '松烟灰四季款',
]


# =============================================================================
# BOM配置
# =============================================================================

BOM_CONFIG = {
    "【床单款】1.5米床套件，搭配200x230cm被套": BOMItem("床单", "240*250", "200*230", 2),
    "【床笠款】1.5米床套件，搭配200x230cm被套": BOMItem("床笠", "150*200", "200*230", 2),
    "【床单款】1.5米床套件，搭配220x240cm被套": BOMItem("床单", "240*250", "220*240", 2),
    "【床笠款】1.5米床套件，搭配220x240cm被套": BOMItem("床笠", "150*200", "220*240", 2),
    "【床单款】1.8米床套件，搭配200x230cm被套": BOMItem("床单", "270*250", "200*230", 2),
    "【床笠款】1.8米床套件，搭配200x230cm被套": BOMItem("床笠", "180*200", "200*230", 2),
    "【床单款】1.8米床套件，搭配220x240cm被套": BOMItem("床单", "270*250", "220*240", 2),
    "【床笠款】1.8米床套件，搭配220x240cm被套": BOMItem("床笠", "180*200", "220*240", 2),
    "【床单款】2米床（200*200cm）套件，搭配220x240cm被套": BOMItem("床单", "270*250", "220*240", 2),
    "【床笠款】2米床（200*200cm）套件，搭配220x240cm被套": BOMItem("床笠", "200*200", "220*240", 2),
    "【床笠款】2.2米床（220*200cm）套件，搭配220x240cm被套": BOMItem("床笠", "220*200", "220*240", 2),
}


# =============================================================================
# 解析函数
# =============================================================================

def parse_product_name(name: str) -> Optional[ComponentSpec]:
    """从商品名称解析零部件规格"""
    if not isinstance(name, str):
        return None

    name = name.strip()

    exclude_keywords = ['浴巾', '蚕丝被', '洗衣液', '马克杯', '样布', '包装', '毛巾']
    for kw in exclude_keywords:
        if kw in name:
            return None

    if '枕套' in name:
        match = re.search(r'枕套（[^）]+）-(.+)$', name)
        if match:
            color = match.group(1)
            return ComponentSpec(type='枕套', size='标准', color=color)
        return None

    if name.startswith('床笠'):
        match = re.search(r'床笠(\d+)\*(\d+)\*\d+[cm]*[-－](.+)$', name)
        if match:
            d1, d2 = int(match.group(1)), int(match.group(2))
            color = match.group(3)
            size = f"{d1}*{d2}"
            return ComponentSpec(type='床笠', size=size, color=color)

        match = re.search(r'床笠(\d+)\*(\d+)\*\d+cm；([^；]+)；([^；]+)', name)
        if match:
            d1, d2 = int(match.group(1)), int(match.group(2))
            color_part = match.group(3)
            style_part = match.group(4)
            color = f"{color_part}{style_part}"
            size = f"{d1}*{d2}"
            return ComponentSpec(type='床笠', size=size, color=color)
        return None

    if name.startswith('床单'):
        match = re.search(r'床单(\d+)\*(\d+)[cm]*[-－](.+)$', name)
        if match:
            d1, d2 = int(match.group(1)), int(match.group(2))
            color = match.group(3)
            size = f"{d1}*{d2}"
            return ComponentSpec(type='床单', size=size, color=color)
        return None

    if name.startswith('被套'):
        match = re.search(r'被套(\d+)\*(\d+)[-－](.+)$', name)
        if match:
            d1, d2 = int(match.group(1)), int(match.group(2))
            color = match.group(3)
            size = f"{d1}*{d2}"
            return ComponentSpec(type='被套', size=size, color=color)
        return None

    return None


def parse_pillow_quantity(name: str) -> int:
    """判断枕套数量"""
    if '一对' in name:
        return 2
    elif '单只' in name:
        return 1
    return 1


def normalize_sku_name(sku_name: str) -> str:
    """标准化SKU名称"""
    if not isinstance(sku_name, str):
        return str(sku_name)
    return sku_name.strip()


def parse_ratio(value) -> float:
    """解析销售比例"""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        value = value.strip()
        if value.endswith('%'):
            return float(value[:-1]) / 100
        return float(value)
    return 0.0


# =============================================================================
# 数据加载
# =============================================================================

@st.cache_data
def load_inventory(file) -> pd.DataFrame:
    """加载库存源文件"""
    df = pd.read_excel(file)
    required_cols = ['商品名称', '可用数']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"库存文件缺少必需列: {col}")
    df_grouped = df.groupby('商品名称')['可用数'].sum().reset_index()
    df_grouped.columns = ['商品名称', '库存']
    return df_grouped


@st.cache_data
def load_sales_ratio(file) -> Dict[str, float]:
    """加载销售比例表"""
    df = pd.read_excel(file, header=None)
    ratio_dict = {}
    for _, row in df.iterrows():
        sku_name = normalize_sku_name(row[0])
        ratio = parse_ratio(row[1])
        ratio_dict[sku_name] = ratio
    return ratio_dict


@st.cache_data
def load_sku_mapping(file) -> pd.DataFrame:
    """加载SKU映射表"""
    df = pd.read_excel(file)
    df.columns = ['SKU_ID', '套件描述', '颜色']
    df['套件描述'] = df['套件描述'].apply(normalize_sku_name)
    return df


# =============================================================================
# 库存聚合
# =============================================================================

def aggregate_component_inventory(df_inventory: pd.DataFrame) -> Dict:
    """聚合零部件库存"""
    inventory = {'床笠': {}, '床单': {}, '被套': {}, '枕套': {}}

    for _, row in df_inventory.iterrows():
        name = row['商品名称']
        stock = int(row['库存']) if pd.notna(row['库存']) else 0

        if stock <= 0:
            continue

        spec = parse_product_name(name)
        if spec is None:
            continue

        comp_type = spec.type
        color = spec.color
        size = spec.size

        # 枕套处理：一对=1套，单只需要2只=1套
        if comp_type == '枕套':
            if '一对' in name:
                # 一对装：库存数就是可组装套数
                stock = stock
            else:
                # 单只：2只=1套，向下取整
                stock = stock // 2

        if color not in inventory[comp_type]:
            inventory[comp_type][color] = {}

        if size not in inventory[comp_type][color]:
            inventory[comp_type][color][size] = 0

        inventory[comp_type][color][size] += stock

    return inventory


# =============================================================================
# 核心算法
# =============================================================================

def calculate_sku_inventory(
    sku_mapping: pd.DataFrame,
    sales_ratio: Dict[str, float],
    component_inventory: Dict,
    active_colors: list,
    safety_factor: float = 0.3
) -> pd.DataFrame:
    """核心算法：计算SKU可售库存"""
    results = []

    for color in sku_mapping['颜色'].unique():
        if color not in active_colors:
            continue

        color_skus = sku_mapping[sku_mapping['颜色'] == color]
        sku_demands = []

        for _, row in color_skus.iterrows():
            sku_id = row['SKU_ID']
            sku_desc = row['套件描述']

            bom = BOM_CONFIG.get(sku_desc)
            if bom is None:
                continue

            ratio = sales_ratio.get(sku_desc, 0)

            sku_demands.append({
                'sku_id': sku_id,
                'sku_desc': sku_desc,
                'color': color,
                'bom': bom,
                'ratio': ratio
            })

        if not sku_demands:
            continue

        duvet_pools = {}
        sheet_pools = {}
        total_ratio = sum(d['ratio'] for d in sku_demands)

        for demand in sku_demands:
            bom = demand['bom']

            duvet_key = bom.duvet_size
            if duvet_key not in duvet_pools:
                duvet_pools[duvet_key] = []
            duvet_pools[duvet_key].append(demand)

            sheet_key = (bom.sheet_type, bom.sheet_size)
            if sheet_key not in sheet_pools:
                sheet_pools[sheet_key] = []
            sheet_pools[sheet_key].append(demand)

        color_base = color

        # 获取该颜色的枕套总库存（套数）
        pillow_total = 0
        if color_base in component_inventory.get('枕套', {}):
            pillow_total = component_inventory['枕套'][color_base].get('标准', 0)

        # 第一轮：计算每个SKU基于被套和床单/笠的理论可组装数
        sku_theoretical = []
        for demand in sku_demands:
            bom = demand['bom']
            ratio = demand['ratio']

            if ratio == 0:
                sku_theoretical.append({
                    'demand': demand,
                    'allocated_duvet': 0,
                    'allocated_sheet': 0,
                    'theoretical': 0,
                    'duvet_stock': 0,
                    'sheet_stock': 0,
                    'duvet_pool_ratio': 0,
                    'sheet_pool_ratio': 0,
                    'is_zero_ratio': True
                })
                continue

            # 被套分配
            duvet_key = bom.duvet_size
            duvet_pool_ratio = sum(d['ratio'] for d in duvet_pools[duvet_key])
            duvet_stock = 0
            if color_base in component_inventory.get('被套', {}):
                duvet_stock = component_inventory['被套'][color_base].get(duvet_key, 0)
            allocated_duvet = duvet_stock * (ratio / duvet_pool_ratio) if duvet_pool_ratio > 0 else 0

            # 床单/笠分配
            sheet_key = (bom.sheet_type, bom.sheet_size)
            sheet_pool_ratio = sum(d['ratio'] for d in sheet_pools[sheet_key])
            sheet_stock = 0
            sheet_type = bom.sheet_type
            sheet_size = bom.sheet_size
            if color_base in component_inventory.get(sheet_type, {}):
                sheet_stock = component_inventory[sheet_type][color_base].get(sheet_size, 0)
            allocated_sheet = sheet_stock * (ratio / sheet_pool_ratio) if sheet_pool_ratio > 0 else 0

            # 被套和床单/笠的短板（不含枕套）
            theoretical = min(allocated_duvet, allocated_sheet)

            sku_theoretical.append({
                'demand': demand,
                'allocated_duvet': allocated_duvet,
                'allocated_sheet': allocated_sheet,
                'theoretical': theoretical,
                'duvet_stock': duvet_stock,
                'sheet_stock': sheet_stock,
                'duvet_pool_ratio': duvet_pool_ratio,
                'sheet_pool_ratio': sheet_pool_ratio,
                'is_zero_ratio': False
            })

        # 第二轮：检查枕套是否足够，如果不够则按比例缩减
        total_theoretical = sum(s['theoretical'] for s in sku_theoretical)
        pillow_sufficient = pillow_total >= total_theoretical
        pillow_ratio = pillow_total / total_theoretical if total_theoretical > 0 else 1

        # 生成最终结果
        for sku_data in sku_theoretical:
            demand = sku_data['demand']
            bom = demand['bom']

            if sku_data['is_zero_ratio']:
                results.append({
                    'SKU_ID': demand['sku_id'],
                    '套件描述': demand['sku_desc'],
                    '颜色': color,
                    '可售库存': 0,
                    '计算明细': '比例为0'
                })
                continue

            theoretical = sku_data['theoretical']
            allocated_duvet = sku_data['allocated_duvet']
            allocated_sheet = sku_data['allocated_sheet']

            # 如果枕套不足，按比例缩减
            if not pillow_sufficient:
                theoretical = theoretical * pillow_ratio

            final_stock = int(theoretical * safety_factor)

            sheet_type = bom.sheet_type
            sheet_size = bom.sheet_size
            duvet_key = bom.duvet_size

            if pillow_sufficient:
                detail = (f"被套{duvet_key}:{sku_data['duvet_stock']}*{demand['ratio']:.4f}/{sku_data['duvet_pool_ratio']:.4f}={allocated_duvet:.1f}, "
                         f"{sheet_type}{sheet_size}:{sku_data['sheet_stock']}*{demand['ratio']:.4f}/{sku_data['sheet_pool_ratio']:.4f}={allocated_sheet:.1f}, "
                         f"枕套充足({pillow_total}套), "
                         f"短板:{theoretical:.1f}*{safety_factor}={final_stock}")
            else:
                detail = (f"被套{duvet_key}:{sku_data['duvet_stock']}*{demand['ratio']:.4f}/{sku_data['duvet_pool_ratio']:.4f}={allocated_duvet:.1f}, "
                         f"{sheet_type}{sheet_size}:{sku_data['sheet_stock']}*{demand['ratio']:.4f}/{sku_data['sheet_pool_ratio']:.4f}={allocated_sheet:.1f}, "
                         f"枕套不足({pillow_total}套<{total_theoretical:.0f}套需求,缩减{pillow_ratio:.2%}), "
                         f"短板:{theoretical:.1f}*{safety_factor}={final_stock}")

            results.append({
                'SKU_ID': demand['sku_id'],
                '套件描述': demand['sku_desc'],
                '颜色': color,
                '可售库存': final_stock,
                '计算明细': detail
            })

    return pd.DataFrame(results)


def to_excel_bytes(df: pd.DataFrame) -> bytes:
    """将DataFrame转换为Excel字节流"""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()


# =============================================================================
# Streamlit 主界面
# =============================================================================

def main():
    st.title("📦 套件库存自动计算系统")
    st.markdown("上传三个Excel文件，自动计算各SKU的可售库存")

    # 侧边栏 - 参数设置
    with st.sidebar:
        st.header("⚙️ 参数设置")

        safety_factor = st.slider(
            "安全库存系数",
            min_value=0.1,
            max_value=1.0,
            value=0.3,
            step=0.05,
            help="最终库存 = 理论库存 × 安全系数"
        )

        st.markdown("---")
        st.subheader("在售颜色")

        # 颜色选择
        all_colors = DEFAULT_ACTIVE_COLORS.copy()
        active_colors = st.multiselect(
            "选择在售颜色",
            options=all_colors,
            default=all_colors,
            help="只计算选中颜色的库存"
        )

    # 主区域 - 文件上传
    st.header("📁 上传数据文件")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("库存源文件")
        inventory_file = st.file_uploader(
            "包含商品名称、可用数等列",
            type=['xlsx', 'xls'],
            key='inventory'
        )

    with col2:
        st.subheader("销售比例表")
        ratio_file = st.file_uploader(
            "套件名称与销售占比",
            type=['xlsx', 'xls'],
            key='ratio'
        )

    with col3:
        st.subheader("SKU映射表")
        mapping_file = st.file_uploader(
            "SKU ID、套件描述、颜色",
            type=['xlsx', 'xls'],
            key='mapping'
        )

    # 计算按钮
    if st.button("🚀 开始计算", type="primary", use_container_width=True):
        if not all([inventory_file, ratio_file, mapping_file]):
            st.error("请先上传全部三个文件！")
            return

        if not active_colors:
            st.error("请至少选择一种在售颜色！")
            return

        with st.spinner("正在计算..."):
            try:
                # 加载数据
                df_inventory = load_inventory(inventory_file)
                sales_ratio = load_sales_ratio(ratio_file)
                sku_mapping = load_sku_mapping(mapping_file)

                # 聚合库存
                component_inventory = aggregate_component_inventory(df_inventory)

                # 计算
                results = calculate_sku_inventory(
                    sku_mapping,
                    sales_ratio,
                    component_inventory,
                    active_colors,
                    safety_factor
                )

                # 存储结果到session
                st.session_state['results'] = results
                st.session_state['component_inventory'] = component_inventory
                st.session_state['active_colors'] = active_colors

                st.success("✅ 计算完成！")

            except Exception as e:
                st.error(f"计算出错: {str(e)}")
                return

    # 显示结果
    if 'results' in st.session_state:
        results = st.session_state['results']
        component_inventory = st.session_state['component_inventory']
        active_colors = st.session_state['active_colors']

        st.markdown("---")
        st.header("📊 计算结果")

        # 统计概览
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("总SKU数", len(results))
        with col2:
            st.metric("有库存SKU", len(results[results['可售库存'] > 0]))
        with col3:
            st.metric("零库存SKU", len(results[results['可售库存'] == 0]))
        with col4:
            st.metric("总可售套数", int(results['可售库存'].sum()))

        # 按颜色统计
        st.subheader("按颜色统计")
        color_stats = results.groupby('颜色')['可售库存'].agg(['count', 'sum'])
        color_stats.columns = ['SKU数', '可售套数']
        color_stats = color_stats.reset_index()
        st.dataframe(color_stats, use_container_width=True)

        # 详细结果
        st.subheader("详细结果")

        # 筛选器
        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            selected_color = st.selectbox(
                "按颜色筛选",
                options=['全部'] + list(results['颜色'].unique())
            )
        with filter_col2:
            show_zero = st.checkbox("显示零库存SKU", value=True)

        # 过滤
        display_df = results.copy()
        if selected_color != '全部':
            display_df = display_df[display_df['颜色'] == selected_color]
        if not show_zero:
            display_df = display_df[display_df['可售库存'] > 0]

        st.dataframe(
            display_df[['SKU_ID', '套件描述', '颜色', '可售库存']],
            use_container_width=True,
            height=400
        )

        # 下载按钮
        st.subheader("📥 下载结果")
        col1, col2 = st.columns(2)

        with col1:
            simple_df = results[['SKU_ID', '套件描述', '颜色', '可售库存']]
            st.download_button(
                label="下载简版结果",
                data=to_excel_bytes(simple_df),
                file_name="套件库存计算结果.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        with col2:
            st.download_button(
                label="下载详细版（含计算明细）",
                data=to_excel_bytes(results),
                file_name="套件库存计算结果_详细.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        # 零部件库存概览
        with st.expander("查看零部件库存汇总"):
            for comp_type in ['床笠', '床单', '被套', '枕套']:
                st.write(f"**{comp_type}**")
                comp_data = []
                for color in active_colors:
                    if color in component_inventory.get(comp_type, {}):
                        for size, stock in component_inventory[comp_type][color].items():
                            comp_data.append({
                                '颜色': color,
                                '尺寸': size,
                                '库存': stock
                            })
                if comp_data:
                    st.dataframe(pd.DataFrame(comp_data), use_container_width=True)
                else:
                    st.write("无数据")


if __name__ == '__main__':
    main()
