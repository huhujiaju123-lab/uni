"""
模块4: 原材料拆解模块
将成品订货计划拆解为原材料需求
"""

from typing import Dict, Any
import pandas as pd
from .base_module import BaseModule


class MaterialDecomposer(BaseModule):
    """
    原材料拆解模块

    输入数据:
    - order_plan: 订货计划 (来自OrderPlanner)
    - bom_data: 物料清单BOM (成品SKU, 原材料编码, 原材料名称, 用量, 单位)
    - material_stock: 原材料库存 (原材料编码, 库存数量, 仓库)
    - material_supplier: 原材料供应商信息 (原材料编码, 供应商, 单价, 最小订货量, 交货周期)

    配置参数:
    - include_safety_stock: 是否计算原材料安全库存
    - material_safety_days: 原材料安全库存天数
    - consolidate_materials: 是否合并相同原材料

    输出数据:
    - material_requirement: 原材料需求明细
    - material_summary: 原材料需求汇总
    - material_order_plan: 原材料订货计划
    """

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "module_name": "原材料拆解",
            "version": "1.0",
            "parameters": {
                "include_safety_stock": True,  # 是否计算原材料安全库存
                "material_safety_days": 7,  # 原材料安全库存天数
                "consolidate_materials": True,  # 是否合并相同原材料
                "loss_rate": 0.02,  # 损耗率（2%）
                "min_order_quantity": 100,  # 原材料默认最小订货量
                "order_multiple": 10,  # 原材料订货数量取整倍数
                "lead_time_buffer_days": 7,  # 交货周期缓冲天数
                "calculate_cost": True  # 是否计算成本
            }
        }

    def get_required_inputs(self) -> Dict[str, list]:
        return {
            "order_plan": ["sku_code", "year_month", "order_quantity"],
            "bom_data": ["sku_code", "material_code", "material_name", "quantity_per_unit", "unit"],
            "material_stock": ["material_code", "stock_quantity"],  # 可选
            "material_supplier": ["material_code", "supplier", "unit_price", "min_order_quantity", "lead_time_days"]  # 可选
        }

    def calculate(self) -> Dict[str, pd.DataFrame]:
        """
        执行原材料拆解

        计算逻辑:
        1. 根据BOM展开成品订货需求到原材料
        2. 考虑损耗率
        3. 汇总各原材料总需求
        4. 减去现有原材料库存
        5. 生成原材料订货计划
        """
        params = self.config.get("parameters", {})

        order_plan = self.input_data.get("order_plan", pd.DataFrame())
        bom_data = self.input_data.get("bom_data", pd.DataFrame())

        if order_plan.empty or bom_data.empty:
            return {
                "material_requirement": pd.DataFrame(),
                "material_summary": pd.DataFrame(),
                "material_order_plan": pd.DataFrame()
            }

        # 只处理需要订货的记录
        orders_to_process = order_plan[order_plan['order_quantity'] > 0].copy()

        if orders_to_process.empty:
            return {
                "material_requirement": pd.DataFrame(),
                "material_summary": pd.DataFrame(),
                "material_order_plan": pd.DataFrame()
            }

        # 获取其他输入数据
        material_stock = self.input_data.get("material_stock", pd.DataFrame())
        material_supplier = self.input_data.get("material_supplier", pd.DataFrame())

        loss_rate = params.get("loss_rate", 0.02)

        # 1. 根据BOM展开
        material_requirement_list = []

        for _, order in orders_to_process.iterrows():
            sku = order['sku_code']
            order_qty = order['order_quantity']
            year_month = order['year_month']

            # 获取该SKU的BOM
            sku_bom = bom_data[bom_data['sku_code'] == sku]

            for _, bom_item in sku_bom.iterrows():
                material_code = bom_item['material_code']
                material_name = bom_item['material_name']
                qty_per_unit = bom_item['quantity_per_unit']
                unit = bom_item['unit']

                # 计算原材料需求（考虑损耗）
                raw_requirement = order_qty * qty_per_unit
                requirement_with_loss = raw_requirement * (1 + loss_rate)

                material_requirement_list.append({
                    'year_month': year_month,
                    'sku_code': sku,
                    'order_quantity': order_qty,
                    'material_code': material_code,
                    'material_name': material_name,
                    'quantity_per_unit': qty_per_unit,
                    'unit': unit,
                    'raw_requirement': round(raw_requirement, 2),
                    'requirement_with_loss': round(requirement_with_loss, 2),
                    'loss_rate': loss_rate
                })

        material_requirement = pd.DataFrame(material_requirement_list)

        # 2. 汇总原材料需求
        if params.get("consolidate_materials", True):
            material_summary = material_requirement.groupby(
                ['year_month', 'material_code', 'material_name', 'unit']
            ).agg({
                'requirement_with_loss': 'sum',
                'raw_requirement': 'sum',
                'sku_code': lambda x: ', '.join(x.unique())  # 关联的SKU列表
            }).reset_index()
            material_summary.columns = ['year_month', 'material_code', 'material_name',
                                        'unit', 'total_requirement', 'raw_requirement', 'related_skus']
        else:
            material_summary = material_requirement.copy()

        # 3. 计算原材料订货计划
        material_order_list = []

        # 按原材料汇总总需求
        total_material_need = material_summary.groupby(
            ['material_code', 'material_name', 'unit']
        )['total_requirement'].sum().reset_index()

        for _, mat in total_material_need.iterrows():
            material_code = mat['material_code']
            material_name = mat['material_name']
            total_need = mat['total_requirement']
            unit = mat['unit']

            # 获取当前库存
            mat_stock = material_stock[material_stock['material_code'] == material_code] if not material_stock.empty else pd.DataFrame()
            current_stock = mat_stock['stock_quantity'].sum() if not mat_stock.empty else 0

            # 获取供应商信息
            mat_supplier = material_supplier[material_supplier['material_code'] == material_code] if not material_supplier.empty else pd.DataFrame()

            if not mat_supplier.empty:
                supplier_name = mat_supplier['supplier'].values[0]
                unit_price = mat_supplier['unit_price'].values[0]
                min_order_qty = mat_supplier['min_order_quantity'].values[0]
                lead_time = mat_supplier['lead_time_days'].values[0]
            else:
                supplier_name = "默认供应商"
                unit_price = 0
                min_order_qty = params.get("min_order_quantity", 100)
                lead_time = 30

            # 计算需要订购的数量
            net_requirement = total_need - current_stock
            order_quantity = 0

            if net_requirement > 0:
                # 考虑最小订货量和取整
                order_multiple = params.get("order_multiple", 10)
                if net_requirement < min_order_qty:
                    order_quantity = min_order_qty
                else:
                    order_quantity = ((net_requirement // order_multiple) + 1) * order_multiple

            # 计算成本
            estimated_cost = order_quantity * unit_price if params.get("calculate_cost", True) else 0

            material_order_list.append({
                'material_code': material_code,
                'material_name': material_name,
                'unit': unit,
                'total_requirement': round(total_need, 2),
                'current_stock': round(current_stock, 2),
                'net_requirement': round(max(0, net_requirement), 2),
                'order_quantity': round(order_quantity, 2),
                'supplier': supplier_name,
                'unit_price': unit_price,
                'estimated_cost': round(estimated_cost, 2),
                'min_order_quantity': min_order_qty,
                'lead_time_days': lead_time
            })

        material_order_plan = pd.DataFrame(material_order_list)

        return {
            "material_requirement": material_requirement,
            "material_summary": material_summary,
            "material_order_plan": material_order_plan
        }
