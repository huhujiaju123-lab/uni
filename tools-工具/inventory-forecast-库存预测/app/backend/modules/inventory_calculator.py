"""
模块1: 现状库存计算模块
计算当前各SKU的库存状态，包括可用库存、在途库存、预留库存等
"""

from typing import Dict, Any
import pandas as pd
from .base_module import BaseModule


class InventoryCalculator(BaseModule):
    """
    现状库存计算模块

    输入数据:
    - current_stock: 当前库存数据 (SKU编码, 仓库, 数量, 库存类型)
    - pending_orders: 在途订单数据 (SKU编码, 预计到货日期, 数量)
    - reserved_stock: 预留库存数据 (SKU编码, 预留数量, 预留原因)

    配置参数:
    - safety_stock_days: 安全库存天数
    - warehouse_list: 需要计算的仓库列表
    - stock_types: 库存类型定义

    输出数据:
    - inventory_summary: 库存汇总表
    - inventory_detail: 库存明细表
    """

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "module_name": "现状库存计算",
            "version": "1.0",
            "parameters": {
                "safety_stock_days": 7,  # 安全库存天数
                "warehouse_list": ["主仓", "分仓A", "分仓B"],  # 仓库列表
                "stock_types": {
                    "available": "可用库存",
                    "reserved": "预留库存",
                    "damaged": "残次品",
                    "in_transit": "在途库存"
                },
                "include_in_transit": True,  # 是否计入在途库存
                "calculation_date": None  # 计算基准日期，None表示当天
            }
        }

    def get_required_inputs(self) -> Dict[str, list]:
        return {
            "current_stock": ["sku_code", "warehouse", "quantity", "stock_type"],
            "pending_orders": ["sku_code", "expected_date", "quantity"],  # 可选
            "reserved_stock": ["sku_code", "reserved_quantity", "reason"]  # 可选
        }

    def calculate(self) -> Dict[str, pd.DataFrame]:
        """
        计算库存状态

        计算逻辑:
        1. 汇总各仓库的当前库存
        2. 加入在途库存（如果配置启用）
        3. 减去预留库存
        4. 计算可用库存 = 当前库存 + 在途库存 - 预留库存
        """
        params = self.config.get("parameters", {})

        # 获取当前库存数据
        current_stock = self.input_data.get("current_stock", pd.DataFrame())

        if current_stock.empty:
            return {
                "inventory_summary": pd.DataFrame(),
                "inventory_detail": pd.DataFrame()
            }

        # 1. 按SKU汇总当前库存
        inventory_by_sku = current_stock.groupby(['sku_code', 'stock_type']).agg({
            'quantity': 'sum'
        }).reset_index()

        # 透视表：每个SKU各类型库存
        inventory_pivot = inventory_by_sku.pivot_table(
            index='sku_code',
            columns='stock_type',
            values='quantity',
            fill_value=0
        ).reset_index()

        # 2. 处理在途库存
        pending_orders = self.input_data.get("pending_orders", pd.DataFrame())
        if not pending_orders.empty and params.get("include_in_transit", True):
            in_transit = pending_orders.groupby('sku_code')['quantity'].sum().reset_index()
            in_transit.columns = ['sku_code', 'in_transit_quantity']
            inventory_pivot = inventory_pivot.merge(in_transit, on='sku_code', how='left')
            inventory_pivot['in_transit_quantity'] = inventory_pivot['in_transit_quantity'].fillna(0)
        else:
            inventory_pivot['in_transit_quantity'] = 0

        # 3. 处理预留库存
        reserved_stock = self.input_data.get("reserved_stock", pd.DataFrame())
        if not reserved_stock.empty:
            reserved = reserved_stock.groupby('sku_code')['reserved_quantity'].sum().reset_index()
            inventory_pivot = inventory_pivot.merge(reserved, on='sku_code', how='left')
            inventory_pivot['reserved_quantity'] = inventory_pivot['reserved_quantity'].fillna(0)
        else:
            inventory_pivot['reserved_quantity'] = 0

        # 4. 计算可用库存
        # 获取可用类型的库存列
        available_col = 'available' if 'available' in inventory_pivot.columns else None
        if available_col:
            base_available = inventory_pivot[available_col]
        else:
            # 如果没有明确的available列，取所有数值列的和
            numeric_cols = inventory_pivot.select_dtypes(include=['number']).columns
            exclude_cols = ['in_transit_quantity', 'reserved_quantity']
            stock_cols = [c for c in numeric_cols if c not in exclude_cols]
            base_available = inventory_pivot[stock_cols].sum(axis=1) if stock_cols else 0

        inventory_pivot['total_available'] = (
            base_available +
            inventory_pivot['in_transit_quantity'] -
            inventory_pivot['reserved_quantity']
        )

        # 生成汇总表
        inventory_summary = inventory_pivot[['sku_code', 'in_transit_quantity',
                                              'reserved_quantity', 'total_available']].copy()

        # 生成明细表（按仓库）
        inventory_detail = current_stock.groupby(['sku_code', 'warehouse', 'stock_type']).agg({
            'quantity': 'sum'
        }).reset_index()

        return {
            "inventory_summary": inventory_summary,
            "inventory_detail": inventory_detail
        }
