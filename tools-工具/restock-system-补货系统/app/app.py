#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
智能订货预测系统 - Streamlit 网页版
拖拽上传、滑块调参、一键计算、直接下载
"""

import streamlit as st
import pandas as pd
import numpy as np
import math
import re
import io
from typing import Dict, List, Tuple, Optional
from datetime import datetime

# ==================== 页面配置 ====================
st.set_page_config(
    page_title="智能补货系统",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 常量定义 ====================

STANDARD_SKUS = [
    '床笠 150*200',
    '床笠 180*200',
    '床笠 200*200',
    '床笠 220*200',
    '被套 200*230',
    '被套 220*240',
    '床单 240*250',
    '床单 270*250',
    '枕套 (一对)',
    '枕套 (单只)'
]

REF_PRICES = {
    '床笠 150*200': 360,
    '床笠 180*200': 360,
    '床笠 200*200': 360,
    '床笠 220*200': 360,
    '被套 200*230': 499,
    '被套 220*240': 499,
    '床单 240*250': 360,
    '床单 270*250': 360,
    '枕套 (一对)': 170,
    '枕套 (单只)': 85
}

FILTER_KEYWORDS = ['布样', '运费', '补差价', '定制', '包装', '安装', '赠品']


# ==================== 工具函数 ====================

def clean_text(text: str) -> str:
    if pd.isna(text):
        return ""
    text = str(text).strip()
    text = text.replace('（', '(').replace('）', ')')
    text = text.replace('＊', '*').replace('×', '*').replace('X', '*').replace('x', '*')
    return text


def extract_color(spec_text: str) -> str:
    """
    从规格文本中提取颜色

    支持多种格式:
    1. 简单格式: "繁星黄(加暖款)" -> "繁星黄(加暖款)"
    2. 分号分隔格式: "1.5米床单套件，搭配200*230被套；纽扣款；暮光褐；加暖款"
       -> 颜色在最后两段: "暮光褐(加暖款)"
    """
    if not spec_text:
        return "未知颜色"
    text = clean_text(spec_text)

    # 检查是否包含产品规格信息（说明是复杂格式）
    if '套件' in text or '被套' in text or '床笠' in text or '床单' in text or '米床' in text:
        # 复杂格式：按分号分割，取最后的颜色+款式
        parts = [p.strip() for p in re.split(r'[；;]', text) if p.strip()]

        if len(parts) >= 2:
            # 最后一段通常是款式（加暖款/四季款）
            last = parts[-1]
            second_last = parts[-2]

            # 判断最后一段是否是款式标识
            if last in ['加暖款', '四季款', '纽扣款'] or '款' in last:
                # 颜色 = 倒数第二段 + 最后一段
                return f"{second_last}({last})"
            else:
                # 最后一段就是颜色
                return last
        elif len(parts) == 1:
            return parts[0]

    # 简单格式：直接返回清理后的文本
    color = text.strip()

    # 如果是纯数字则返回未知
    if re.match(r'^[\d\.*]+$', color):
        return "未知颜色"

    return color


def should_filter_row(product_name: str) -> bool:
    if pd.isna(product_name):
        return True
    name = str(product_name)
    return any(keyword in name for keyword in FILTER_KEYWORDS)


# ==================== SKU解析 ====================

def detect_product_type(product_name: str) -> str:
    name = clean_text(product_name)
    if '五件套' in name:
        return 'five_piece'
    elif '四件套' in name or '套件' in name or '件套' in name:
        return 'four_piece'
    else:
        return 'single'


def parse_bed_size(product_name: str) -> str:
    """
    从商品名称解析床的尺寸
    示例: "【床笠款】1.8米床套件" -> "180"
          "【床笠款】2.0米床套件" -> "200"
          "【床笠款】2.2米床套件" -> "220"
    """
    name = clean_text(product_name)

    # 优先匹配 "X.X米床" 格式
    if '2.2米' in name or '2.2m' in name.lower():
        return '220'
    elif '2.0米' in name or '2m' in name.lower() or '2米' in name:
        return '200'
    elif '1.8米' in name or '1.8m' in name.lower():
        return '180'
    elif '1.5米' in name or '1.5m' in name.lower():
        return '150'

    # 备用: 匹配尺寸数字 (排除被套尺寸)
    # 先移除被套相关描述再匹配
    name_without_duvet = re.sub(r'被套.*?cm|搭配.*?被套', '', name)
    if '220' in name_without_duvet:
        return '220'
    elif '200' in name_without_duvet:
        return '200'
    elif '180' in name_without_duvet:
        return '180'
    elif '150' in name_without_duvet:
        return '150'

    return None


def parse_duvet_size(product_name: str) -> str:
    """
    从商品名称解析被套尺寸
    示例: "搭配220x240cm被套" -> "220*240"
          "搭配200x230cm被套" -> "200*230"
    """
    name = clean_text(product_name)

    # 匹配被套尺寸
    if '220' in name and '240' in name:
        return '220*240'
    elif '220*240' in name or '220x240' in name:
        return '220*240'
    elif '200*230' in name or '200x230' in name:
        return '200*230'
    elif '240' in name:
        return '220*240'
    else:
        return '200*230'


def is_fitted_sheet_style(product_name: str) -> bool:
    """判断是否为床笠款"""
    name = clean_text(product_name)
    return '床笠款' in name or '床笠' in name


def is_flat_sheet_style(product_name: str) -> bool:
    """判断是否为床单款"""
    name = clean_text(product_name)
    return '床单款' in name or '床单' in name


def explode_to_standard_skus(product_name: str, spec_text: str) -> List[Tuple[str, float]]:
    """
    将商品拆解为标准SKU
    示例: "【床笠款】1.8米床套件，搭配220x240cm被套" + "米白（四季款）"
    -> [('被套 220*240', 1), ('床笠 180*200', 1), ('枕套 (一对)', 1)]
    """
    product_type = detect_product_type(product_name)
    name = clean_text(product_name)
    result = []

    # 从商品名称解析尺寸信息
    bed_size = parse_bed_size(product_name)
    duvet_size = parse_duvet_size(product_name)

    if product_type == 'five_piece':
        # 五件套: 被套 + 床笠/床单 + 枕套(一对) + 枕套(单只)
        result.append((f'被套 {duvet_size}', 1))

        if is_fitted_sheet_style(product_name):
            # 床笠款
            if bed_size == '220':
                result.append(('床笠 220*200', 1))
            elif bed_size == '200':
                result.append(('床笠 200*200', 1))
            elif bed_size == '180':
                result.append(('床笠 180*200', 1))
            elif bed_size == '150':
                result.append(('床笠 150*200', 1))
            else:
                result.append(('床笠 180*200', 1))  # 默认1.8米
        elif is_flat_sheet_style(product_name):
            # 床单款
            if bed_size == '150':
                result.append(('床单 240*250', 1))
            else:
                result.append(('床单 270*250', 1))

        result.append(('枕套 (一对)', 1))
        result.append(('枕套 (单只)', 1))

    elif product_type == 'four_piece':
        # 四件套/套件: 被套 + 床笠/床单 + 枕套(一对)
        result.append((f'被套 {duvet_size}', 1))

        if is_fitted_sheet_style(product_name):
            # 床笠款
            if bed_size == '220':
                result.append(('床笠 220*200', 1))
            elif bed_size == '200':
                result.append(('床笠 200*200', 1))
            elif bed_size == '180':
                result.append(('床笠 180*200', 1))
            elif bed_size == '150':
                result.append(('床笠 150*200', 1))
            else:
                result.append(('床笠 180*200', 1))  # 默认1.8米
        elif is_flat_sheet_style(product_name):
            # 床单款
            if bed_size == '150':
                result.append(('床单 240*250', 1))
            else:
                result.append(('床单 270*250', 1))

        result.append(('枕套 (一对)', 1))

    else:
        # 单品
        if '枕套' in name:
            if '一对' in name or '对' in name or '2只' in name:
                result.append(('枕套 (一对)', 1))
            else:
                result.append(('枕套 (单只)', 1))
        elif '被套' in name:
            result.append((f'被套 {duvet_size}', 1))
        elif '床笠' in name:
            bed_size = parse_bed_size(product_name)
            if bed_size == '220':
                result.append(('床笠 220*200', 1))
            elif bed_size == '200':
                result.append(('床笠 200*200', 1))
            elif bed_size == '180':
                result.append(('床笠 180*200', 1))
            elif bed_size == '150':
                result.append(('床笠 150*200', 1))
        elif '床单' in name:
            if bed_size == '150':
                result.append(('床单 240*250', 1))
            else:
                result.append(('床单 270*250', 1))

    result = [(sku, qty) for sku, qty in result if sku in STANDARD_SKUS]
    return result


def normalize_inventory_sku(product_name: str, spec_text: str) -> Optional[str]:
    name = clean_text(product_name)
    spec = clean_text(spec_text)
    combined = name + " " + spec

    if '枕套' in name:
        if '一对' in combined or '对' in combined:
            return '枕套 (一对)'
        else:
            return '枕套 (单只)'
    if '被套' in name:
        if '220' in combined or '240' in combined:
            return '被套 220*240'
        else:
            return '被套 200*230'
    if '床笠' in name:
        if '220*200' in combined or '220×200' in combined:
            return '床笠 220*200'
        elif '200*200' in combined or '200×200' in combined:
            return '床笠 200*200'
        elif '180*200' in combined or '180×200' in combined:
            return '床笠 180*200'
        elif '150*200' in combined or '150×200' in combined:
            return '床笠 150*200'
        elif '220' in combined or '2.2' in combined:
            return '床笠 220*200'
        elif '200' in combined or '2.0' in combined:
            return '床笠 200*200'
        elif '180' in combined or '1.8' in combined:
            return '床笠 180*200'
        elif '150' in combined or '1.5' in combined:
            return '床笠 150*200'
    if '床单' in name:
        if '240*250' in combined or '240×250' in combined:
            return '床单 240*250'
        elif '270*250' in combined or '270×250' in combined:
            return '床单 270*250'
        elif '240' in combined:
            return '床单 240*250'
        else:
            return '床单 270*250'
    return None


# ==================== 数据处理 ====================

@st.cache_data
def process_sales_data(df: pd.DataFrame) -> pd.DataFrame:
    """处理销售数据"""
    required_cols = ['商品名称', '颜色及规格', '商品金额']
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"销售表缺少列: {missing}")
        return None

    df = df[~df['商品名称'].apply(should_filter_row)]
    df = df[df['商品金额'].notna() & (df['商品金额'] > 0)]
    return df[required_cols].copy()


@st.cache_data
def process_inventory_data(df: pd.DataFrame) -> pd.DataFrame:
    """处理库存数据"""
    spec_col = None
    if '规格' in df.columns:
        spec_col = '规格'
    elif '颜色及规格' in df.columns:
        spec_col = '颜色及规格'

    if spec_col is None or '商品名称' not in df.columns or '可用数' not in df.columns:
        st.error("库存表需要: 商品名称, 规格(或颜色及规格), 可用数")
        return None

    df = df.rename(columns={spec_col: '规格'})
    df['可用数'] = pd.to_numeric(df['可用数'], errors='coerce').fillna(0)
    return df[['商品名称', '规格', '可用数']].copy()


def calculate_sales_breakdown(sales_df: pd.DataFrame) -> pd.DataFrame:
    """拆解销售数据"""
    records = []
    for _, row in sales_df.iterrows():
        product_name = row['商品名称']
        spec = row['颜色及规格']
        amount = row['商品金额']
        color = extract_color(spec)
        sku_list = explode_to_standard_skus(product_name, spec)
        if not sku_list:
            continue
        total_items = sum(qty for _, qty in sku_list)
        if total_items == 0:
            continue
        for sku, qty in sku_list:
            sku_price = REF_PRICES.get(sku, 100)
            total_price = sum(REF_PRICES.get(s, 100) * q for s, q in sku_list)
            weight = (sku_price * qty) / total_price if total_price > 0 else 1/len(sku_list)
            records.append({'颜色': color, 'SKU': sku, '销售额': amount * weight})

    result_df = pd.DataFrame(records)
    if len(result_df) > 0:
        result_df = result_df.groupby(['颜色', 'SKU'], as_index=False)['销售额'].sum()
    return result_df


def build_inventory_matrix(inventory_df: pd.DataFrame) -> pd.DataFrame:
    """构建库存矩阵"""
    records = []
    for _, row in inventory_df.iterrows():
        product_name = row['商品名称']
        spec = row['规格']
        qty = row['可用数']
        std_sku = normalize_inventory_sku(product_name, spec)
        if std_sku is None:
            continue
        color = extract_color(spec)
        records.append({'颜色': color, 'SKU': std_sku, '库存': qty})

    if not records:
        return pd.DataFrame(index=STANDARD_SKUS)

    temp_df = pd.DataFrame(records)
    temp_df = temp_df.groupby(['颜色', 'SKU'], as_index=False)['库存'].sum()
    matrix = temp_df.pivot(index='SKU', columns='颜色', values='库存').fillna(0)

    for sku in STANDARD_SKUS:
        if sku not in matrix.index:
            matrix.loc[sku] = 0
    matrix = matrix.loc[STANDARD_SKUS]
    return matrix


def calculate_replenishment(
    sales_breakdown: pd.DataFrame,
    inventory_matrix: pd.DataFrame,
    inbound_matrix: pd.DataFrame,
    target: float,
    coefficient: float
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """执行补货计算"""
    total_sales = sales_breakdown['销售额'].sum()
    if total_sales == 0:
        st.error("总销售额为0，无法计算")
        return None, None

    all_colors = set()
    if len(sales_breakdown) > 0:
        all_colors.update(sales_breakdown['颜色'].unique())
    all_colors.update(inventory_matrix.columns)
    if inbound_matrix is not None:
        all_colors.update(inbound_matrix.columns)
    all_colors = sorted(all_colors)

    detail_records = []
    replenishment_data = {sku: {} for sku in STANDARD_SKUS}

    for color in all_colors:
        for sku in STANDARD_SKUS:
            sales_amount = 0
            mask = (sales_breakdown['颜色'] == color) & (sales_breakdown['SKU'] == sku)
            if mask.any():
                sales_amount = sales_breakdown.loc[mask, '销售额'].values[0]
            ratio = sales_amount / total_sales if total_sales > 0 else 0
            ref_price = REF_PRICES.get(sku, 100)
            gross = (target * coefficient * ratio) / ref_price
            current_inv = 0
            if color in inventory_matrix.columns:
                current_inv = inventory_matrix.loc[sku, color]
            inbound = 0
            if inbound_matrix is not None and color in inbound_matrix.columns:
                inbound = inbound_matrix.loc[sku, color]
            net = gross - current_inv - inbound
            final = math.ceil(max(0, net))

            detail_records.append({
                '颜色属性': color,
                'SKU名称': sku,
                '销售权重': round(ratio, 6),
                '理论需求': round(gross, 2),
                '当前库存': current_inv,
                '在途库存': inbound,
                '建议补货': final
            })
            replenishment_data[sku][color] = final

    detail_df = pd.DataFrame(detail_records)
    matrix_df = pd.DataFrame(replenishment_data).T
    matrix_df = matrix_df.loc[STANDARD_SKUS]
    matrix_df = matrix_df[sorted(matrix_df.columns)]

    return matrix_df, detail_df


def generate_template(sales_df: pd.DataFrame, inventory_df: pd.DataFrame) -> pd.DataFrame:
    """生成在途库存模板"""
    colors = set()
    if sales_df is not None:
        for spec in sales_df['颜色及规格']:
            color = extract_color(spec)
            if color and color != "未知颜色":
                colors.add(color)
    if inventory_df is not None:
        for spec in inventory_df['规格']:
            color = extract_color(spec)
            if color and color != "未知颜色":
                colors.add(color)
    colors = sorted(colors) if colors else ['颜色1', '颜色2', '颜色3']

    template_df = pd.DataFrame(index=STANDARD_SKUS, columns=colors, data=0)
    template_df.index.name = 'SKU'
    return template_df


def to_excel_bytes(matrix_df: pd.DataFrame, detail_df: pd.DataFrame) -> bytes:
    """将结果转换为Excel字节流"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        matrix_df.to_excel(writer, sheet_name='补货矩阵')
        detail_df.to_excel(writer, sheet_name='计算详情', index=False)
    return output.getvalue()


def template_to_excel_bytes(template_df: pd.DataFrame) -> bytes:
    """将模板转换为Excel字节流"""
    output = io.BytesIO()
    template_df.to_excel(output, engine='openpyxl')
    return output.getvalue()


# ==================== 主界面 ====================

def main():
    # 标题
    st.title("📦 智能订货预测系统")
    st.markdown("**纺织品电商补货计划自动计算工具** | v11.0")
    st.divider()

    # 侧边栏 - 参数配置
    with st.sidebar:
        st.header("⚙️ 参数设置")

        target_sales = st.number_input(
            "目标销售额 (元)",
            min_value=10000,
            max_value=10000000,
            value=500000,
            step=50000,
            help="预计销售目标金额"
        )

        cover_coef = st.slider(
            "覆盖系数",
            min_value=1.0,
            max_value=3.0,
            value=1.5,
            step=0.1,
            help="货期系数，45天建议用1.5"
        )

        st.divider()
        st.markdown("### 📋 标准SKU列表")
        for sku in STANDARD_SKUS:
            st.text(f"• {sku}")

    # 主区域 - 文件上传
    col1, col2, col3 = st.columns(3)

    with col1:
        st.subheader("📊 历史订单表")
        sales_file = st.file_uploader(
            "上传销售数据",
            type=['xlsx', 'xls'],
            key="sales",
            help="需要包含: 商品名称, 颜色及规格, 商品金额"
        )

    with col2:
        st.subheader("📦 商品资料表")
        inventory_file = st.file_uploader(
            "上传库存数据",
            type=['xlsx', 'xls'],
            key="inventory",
            help="需要包含: 商品名称, 规格, 可用数"
        )

    with col3:
        st.subheader("🚚 在途库存表")
        inbound_file = st.file_uploader(
            "上传在途数据 (可选)",
            type=['xlsx', 'xls'],
            key="inbound",
            help="矩阵格式: 行=SKU, 列=颜色"
        )

    st.divider()

    # 处理数据
    sales_df = None
    inventory_df = None
    inbound_df = None

    if sales_file:
        try:
            raw_sales = pd.read_excel(sales_file)
            sales_df = process_sales_data(raw_sales)
            if sales_df is not None:
                st.success(f"✅ 销售数据: {len(sales_df)} 条有效记录")
        except Exception as e:
            st.error(f"读取销售表失败: {e}")

    if inventory_file:
        try:
            raw_inventory = pd.read_excel(inventory_file)
            inventory_df = process_inventory_data(raw_inventory)
            if inventory_df is not None:
                negative_count = (inventory_df['可用数'] < 0).sum()
                msg = f"✅ 库存数据: {len(inventory_df)} 条记录"
                if negative_count > 0:
                    msg += f" (含 {negative_count} 条负库存)"
                st.success(msg)
        except Exception as e:
            st.error(f"读取库存表失败: {e}")

    if inbound_file:
        try:
            inbound_df = pd.read_excel(inbound_file, index_col=0)
            for sku in STANDARD_SKUS:
                if sku not in inbound_df.index:
                    inbound_df.loc[sku] = 0
            inbound_df = inbound_df.loc[STANDARD_SKUS].fillna(0)
            st.success(f"✅ 在途数据: {len(inbound_df.columns)} 个颜色")
        except Exception as e:
            st.error(f"读取在途表失败: {e}")

    # 操作按钮
    st.divider()

    col_btn1, col_btn2 = st.columns(2)

    with col_btn1:
        if st.button("📝 生成在途库存模板", use_container_width=True, type="secondary"):
            if sales_df is not None or inventory_df is not None:
                template = generate_template(sales_df, inventory_df)
                template_bytes = template_to_excel_bytes(template)
                st.download_button(
                    label="⬇️ 下载模板",
                    data=template_bytes,
                    file_name="在途库存模板.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.info(f"模板已生成，包含 {len(template.columns)} 个颜色")
            else:
                st.warning("请先上传销售表或库存表")

    with col_btn2:
        calculate_btn = st.button(
            "🚀 计算补货计划",
            use_container_width=True,
            type="primary",
            disabled=(sales_df is None or inventory_df is None)
        )

    # 执行计算
    if calculate_btn and sales_df is not None and inventory_df is not None:
        with st.spinner("正在计算..."):
            # 拆解销售
            sales_breakdown = calculate_sales_breakdown(sales_df)

            # 构建库存矩阵
            inventory_matrix = build_inventory_matrix(inventory_df)

            # 计算补货
            matrix_df, detail_df = calculate_replenishment(
                sales_breakdown,
                inventory_matrix,
                inbound_df,
                target_sales,
                cover_coef
            )

            if matrix_df is not None and detail_df is not None:
                st.success("✅ 计算完成!")

                # 汇总统计
                total_order = matrix_df.sum().sum()
                non_zero = (matrix_df > 0).sum().sum()

                col_stat1, col_stat2, col_stat3 = st.columns(3)
                col_stat1.metric("总建议补货量", f"{int(total_order)} 件")
                col_stat2.metric("非零单元格", f"{non_zero} 个")
                col_stat3.metric("覆盖颜色数", f"{len(matrix_df.columns)} 种")

                st.divider()

                # 显示补货矩阵
                st.subheader("📋 补货矩阵")
                st.dataframe(
                    matrix_df,
                    use_container_width=True,
                    height=400
                )

                # 显示详情
                with st.expander("📊 查看计算详情"):
                    st.dataframe(detail_df, use_container_width=True, height=400)

                # 下载按钮
                excel_bytes = to_excel_bytes(matrix_df, detail_df)
                filename = f"补货计划_目标{int(target_sales)}_系数{cover_coef}.xlsx"

                st.download_button(
                    label="⬇️ 下载完整报告 (Excel)",
                    data=excel_bytes,
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

    # 页脚
    st.divider()
    st.caption("智能订货预测系统 v11.0 | 基于历史销售数据的智能补货建议")


if __name__ == "__main__":
    main()
