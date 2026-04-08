"""
模块3: 分月订货计划模块
根据库存现状和销量预测，生成分月的订货计划
"""

from typing import Dict, Any
import pandas as pd
from datetime import datetime, timedelta
from .base_module import BaseModule


class OrderPlanner(BaseModule):
    """
    订货计划模块

    输入数据:
    - inventory_summary: 库存汇总数据 (来自InventoryCalculator)
    - forecast_by_month: 月度销量预测 (来自SalesPredictor)
    - supplier_info: 供应商信息 (SKU编码, 供应商, 最小订货量, 订货周期, 生产周期)
    - sku_info: SKU基础信息 (SKU编码, 产品名称, 类别, 单位)

    配置参数:
    - planning_months: 计划月份数
    - safety_stock_days: 安全库存天数
    - order_frequency: 订货频率 (monthly/bi-weekly/weekly)
    - min_order_quantity: 最小订货量

    输出数据:
    - order_plan: 订货计划明细
    - order_summary: 订货计划汇总
    """

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "module_name": "订货计划",
            "version": "1.0",
            "parameters": {
                "planning_months": 3,  # 计划月份数
                "safety_stock_days": 14,  # 安全库存天数
                "order_frequency": "monthly",  # 订货频率
                "lead_time_days": 30,  # 默认交货周期（天）
                "production_time_days": 15,  # 默认生产周期（天）
                "min_order_quantity": 100,  # 默认最小订货量
                "order_multiple": 50,  # 订货数量取整倍数
                "planning_start_date": None,  # 计划开始日期，None表示当月
                "buffer_ratio": 0.1,  # 缓冲比例（额外10%）
                "consider_moq": True,  # 是否考虑最小订货量
                "consider_lead_time": True  # 是否考虑交货周期
            }
        }

    def get_required_inputs(self) -> Dict[str, list]:
        return {
            "inventory_summary": ["sku_code", "total_available"],
            "forecast_by_month": ["sku_code", "year_month", "predicted_quantity"],
            "supplier_info": ["sku_code", "supplier", "min_order_quantity", "lead_time_days"],  # 可选
            "sku_info": ["sku_code", "product_name"]  # 可选
        }

    def calculate(self) -> Dict[str, pd.DataFrame]:
        """
        生成订货计划

        计算逻辑:
        1. 获取当前库存和月度预测销量
        2. 逐月计算：期初库存 - 预测销量 = 期末库存
        3. 当期末库存 < 安全库存时，生成订货需求
        4. 考虑最小订货量、订货周期等约束
        5. 生成订货计划
        """
        params = self.config.get("parameters", {})

        inventory_summary = self.input_data.get("inventory_summary", pd.DataFrame())
        forecast_by_month = self.input_data.get("forecast_by_month", pd.DataFrame())

        if inventory_summary.empty or forecast_by_month.empty:
            return {
                "order_plan": pd.DataFrame(),
                "order_summary": pd.DataFrame()
            }

        # 获取供应商信息
        supplier_info = self.input_data.get("supplier_info", pd.DataFrame())
        sku_info = self.input_data.get("sku_info", pd.DataFrame())

        # 获取所有SKU
        all_skus = forecast_by_month['sku_code'].unique()

        # 获取计划月份
        planning_months = sorted(forecast_by_month['year_month'].unique())[:params.get("planning_months", 3)]

        order_plan_list = []

        for sku in all_skus:
            # 获取当前库存
            sku_inventory = inventory_summary[inventory_summary['sku_code'] == sku]
            current_stock = sku_inventory['total_available'].values[0] if not sku_inventory.empty else 0

            # 获取SKU的预测数据
            sku_forecast = forecast_by_month[forecast_by_month['sku_code'] == sku]

            # 获取供应商配置
            sku_supplier = supplier_info[supplier_info['sku_code'] == sku] if not supplier_info.empty else pd.DataFrame()
            min_order_qty = sku_supplier['min_order_quantity'].values[0] if not sku_supplier.empty else params.get("min_order_quantity", 100)
            lead_time = sku_supplier['lead_time_days'].values[0] if not sku_supplier.empty else params.get("lead_time_days", 30)
            supplier_name = sku_supplier['supplier'].values[0] if not sku_supplier.empty else "默认供应商"

            # 获取SKU信息
            sku_detail = sku_info[sku_info['sku_code'] == sku] if not sku_info.empty else pd.DataFrame()
            product_name = sku_detail['product_name'].values[0] if not sku_detail.empty else sku

            # 逐月计算
            running_stock = current_stock
            safety_days = params.get("safety_stock_days", 14)
            buffer_ratio = params.get("buffer_ratio", 0.1)
            order_multiple = params.get("order_multiple", 50)

            for month in planning_months:
                month_forecast_row = sku_forecast[sku_forecast['year_month'] == month]

                if month_forecast_row.empty:
                    continue

                monthly_demand = month_forecast_row['predicted_quantity'].values[0]

                # 计算日均销量和安全库存
                days_in_month = 30  # 简化处理
                daily_sales = monthly_demand / days_in_month
                safety_stock = daily_sales * safety_days

                # 计算期末库存（不订货情况）
                end_stock_without_order = running_stock - monthly_demand

                # 判断是否需要订货
                order_quantity = 0
                order_needed = False

                if end_stock_without_order < safety_stock:
                    order_needed = True
                    # 计算需要订货的数量
                    # 目标：期末库存 = 安全库存 + 下月预测销量的buffer
                    target_stock = safety_stock + (monthly_demand * buffer_ratio)
                    raw_order_qty = monthly_demand - running_stock + target_stock

                    if raw_order_qty > 0:
                        # 考虑最小订货量
                        if params.get("consider_moq", True) and raw_order_qty < min_order_qty:
                            order_quantity = min_order_qty
                        else:
                            # 取整到订货倍数
                            order_quantity = ((raw_order_qty // order_multiple) + 1) * order_multiple

                # 计算订货时间（考虑交货周期）
                order_date = None
                arrival_date = None
                if order_needed and params.get("consider_lead_time", True):
                    # 订货需要在月初前lead_time天下单
                    month_start = pd.to_datetime(month + "-01")
                    order_date = month_start - timedelta(days=lead_time)
                    arrival_date = month_start

                # 更新running_stock
                end_stock = running_stock - monthly_demand + order_quantity
                running_stock = max(0, end_stock)

                order_plan_list.append({
                    'sku_code': sku,
                    'product_name': product_name,
                    'year_month': month,
                    'begin_stock': round(running_stock + monthly_demand - order_quantity, 0),
                    'predicted_demand': round(monthly_demand, 0),
                    'safety_stock': round(safety_stock, 0),
                    'order_needed': order_needed,
                    'order_quantity': round(order_quantity, 0),
                    'end_stock': round(running_stock, 0),
                    'supplier': supplier_name,
                    'order_date': order_date.strftime('%Y-%m-%d') if order_date else None,
                    'expected_arrival': arrival_date.strftime('%Y-%m-%d') if arrival_date else None,
                    'lead_time_days': lead_time
                })

        # 创建订货计划DataFrame
        order_plan = pd.DataFrame(order_plan_list)

        # 生成订货汇总（按月份汇总）
        if not order_plan.empty:
            order_summary = order_plan.groupby('year_month').agg({
                'order_quantity': 'sum',
                'predicted_demand': 'sum',
                'sku_code': 'count'
            }).reset_index()
            order_summary.columns = ['year_month', 'total_order_quantity', 'total_demand', 'sku_count']
        else:
            order_summary = pd.DataFrame()

        return {
            "order_plan": order_plan,
            "order_summary": order_summary
        }
