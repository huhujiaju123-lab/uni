"""
模块2: 未来销量预测模块
基于历史销量数据预测未来各SKU的销量
"""

from typing import Dict, Any, Optional
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from .base_module import BaseModule


class SalesPredictor(BaseModule):
    """
    销量预测模块

    输入数据:
    - sales_history: 历史销量数据 (SKU编码, 日期, 销量, 渠道)
    - promotion_plan: 促销计划数据 (SKU编码, 开始日期, 结束日期, 预估提升比例) [可选]
    - seasonality_factors: 季节性因子 (月份, 因子) [可选]

    配置参数:
    - prediction_method: 预测方法 (moving_average/weighted_average/linear_regression)
    - prediction_days: 预测天数
    - history_days: 用于预测的历史天数
    - seasonality_enabled: 是否启用季节性调整

    输出数据:
    - sales_forecast: 销量预测结果
    - forecast_by_month: 按月汇总的预测结果
    """

    def get_default_config(self) -> Dict[str, Any]:
        return {
            "module_name": "销量预测",
            "version": "1.0",
            "parameters": {
                "prediction_method": "weighted_average",  # 预测方法
                "prediction_days": 90,  # 预测未来天数
                "history_days": 90,  # 使用历史天数
                "granularity": "daily",  # 预测粒度: daily/weekly/monthly
                "seasonality_enabled": True,  # 启用季节性调整
                "trend_enabled": True,  # 启用趋势调整
                "promotion_adjustment": True,  # 启用促销调整
                "weights": {
                    "recent_30_days": 0.5,  # 最近30天权重
                    "30_60_days": 0.3,  # 30-60天权重
                    "60_90_days": 0.2   # 60-90天权重
                },
                "min_history_days": 30,  # 最少需要的历史天数
                "default_daily_sales": 0  # 历史数据不足时的默认日销量
            }
        }

    def get_required_inputs(self) -> Dict[str, list]:
        return {
            "sales_history": ["sku_code", "date", "quantity"],
            "promotion_plan": ["sku_code", "start_date", "end_date", "uplift_ratio"],  # 可选
            "seasonality_factors": ["month", "factor"]  # 可选
        }

    def calculate(self) -> Dict[str, pd.DataFrame]:
        """
        执行销量预测

        计算逻辑:
        1. 计算历史日均销量（根据配置的方法）
        2. 应用季节性因子（如果启用）
        3. 应用促销提升（如果有促销计划）
        4. 生成每日预测结果
        5. 汇总为月度预测
        """
        params = self.config.get("parameters", {})
        sales_history = self.input_data.get("sales_history", pd.DataFrame())

        if sales_history.empty:
            return {
                "sales_forecast": pd.DataFrame(),
                "forecast_by_month": pd.DataFrame()
            }

        # 确保日期列为datetime类型
        sales_history['date'] = pd.to_datetime(sales_history['date'])

        # 获取所有SKU
        all_skus = sales_history['sku_code'].unique()

        # 预测起始日期（使用历史数据的最后日期的下一天）
        start_date = sales_history['date'].max() + timedelta(days=1)
        prediction_days = params.get("prediction_days", 90)

        # 生成预测日期范围
        forecast_dates = pd.date_range(start=start_date, periods=prediction_days, freq='D')

        # 存储预测结果
        forecast_results = []

        for sku in all_skus:
            sku_history = sales_history[sales_history['sku_code'] == sku].copy()

            # 计算基础日均销量
            base_daily_sales = self._calculate_base_sales(sku_history, params)

            # 为每个预测日期生成预测值
            for forecast_date in forecast_dates:
                predicted_qty = base_daily_sales

                # 应用季节性因子
                if params.get("seasonality_enabled", True):
                    predicted_qty = self._apply_seasonality(
                        predicted_qty, forecast_date.month
                    )

                # 应用促销调整
                if params.get("promotion_adjustment", True):
                    predicted_qty = self._apply_promotion(
                        sku, forecast_date, predicted_qty
                    )

                forecast_results.append({
                    'sku_code': sku,
                    'date': forecast_date,
                    'predicted_quantity': round(predicted_qty, 2),
                    'base_quantity': round(base_daily_sales, 2)
                })

        # 创建预测结果DataFrame
        sales_forecast = pd.DataFrame(forecast_results)

        # 生成月度汇总
        if not sales_forecast.empty:
            sales_forecast['year_month'] = sales_forecast['date'].dt.to_period('M')
            forecast_by_month = sales_forecast.groupby(['sku_code', 'year_month']).agg({
                'predicted_quantity': 'sum',
                'base_quantity': 'sum'
            }).reset_index()
            forecast_by_month['year_month'] = forecast_by_month['year_month'].astype(str)
        else:
            forecast_by_month = pd.DataFrame()

        return {
            "sales_forecast": sales_forecast,
            "forecast_by_month": forecast_by_month
        }

    def _calculate_base_sales(self, sku_history: pd.DataFrame, params: Dict) -> float:
        """根据配置的方法计算基础日均销量"""
        method = params.get("prediction_method", "weighted_average")
        history_days = params.get("history_days", 90)

        # 获取最近N天的数据
        max_date = sku_history['date'].max()
        min_date = max_date - timedelta(days=history_days)
        recent_data = sku_history[sku_history['date'] >= min_date]

        if recent_data.empty:
            return params.get("default_daily_sales", 0)

        if method == "moving_average":
            # 简单移动平均
            return recent_data['quantity'].mean()

        elif method == "weighted_average":
            # 加权移动平均
            weights = params.get("weights", {})
            total_weight = 0
            weighted_sum = 0

            # 最近30天
            recent_30 = recent_data[recent_data['date'] >= max_date - timedelta(days=30)]
            if not recent_30.empty:
                w = weights.get("recent_30_days", 0.5)
                weighted_sum += recent_30['quantity'].mean() * w
                total_weight += w

            # 30-60天
            mask_30_60 = (recent_data['date'] >= max_date - timedelta(days=60)) & \
                         (recent_data['date'] < max_date - timedelta(days=30))
            data_30_60 = recent_data[mask_30_60]
            if not data_30_60.empty:
                w = weights.get("30_60_days", 0.3)
                weighted_sum += data_30_60['quantity'].mean() * w
                total_weight += w

            # 60-90天
            mask_60_90 = (recent_data['date'] >= max_date - timedelta(days=90)) & \
                         (recent_data['date'] < max_date - timedelta(days=60))
            data_60_90 = recent_data[mask_60_90]
            if not data_60_90.empty:
                w = weights.get("60_90_days", 0.2)
                weighted_sum += data_60_90['quantity'].mean() * w
                total_weight += w

            return weighted_sum / total_weight if total_weight > 0 else 0

        elif method == "linear_regression":
            # 简单线性回归
            recent_data = recent_data.sort_values('date')
            recent_data['day_num'] = range(len(recent_data))

            if len(recent_data) < 2:
                return recent_data['quantity'].mean()

            x = recent_data['day_num'].values
            y = recent_data['quantity'].values

            # 计算线性回归系数
            n = len(x)
            sum_x = np.sum(x)
            sum_y = np.sum(y)
            sum_xy = np.sum(x * y)
            sum_x2 = np.sum(x ** 2)

            slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2) if (n * sum_x2 - sum_x ** 2) != 0 else 0
            intercept = (sum_y - slope * sum_x) / n

            # 预测下一天的值
            next_day = n
            predicted = slope * next_day + intercept

            return max(0, predicted)  # 确保不为负数

        return recent_data['quantity'].mean()

    def _apply_seasonality(self, base_qty: float, month: int) -> float:
        """应用季节性因子"""
        seasonality_data = self.input_data.get("seasonality_factors", pd.DataFrame())

        if seasonality_data.empty:
            # 使用默认季节性因子（假设无季节性）
            return base_qty

        factor_row = seasonality_data[seasonality_data['month'] == month]
        if not factor_row.empty:
            factor = factor_row['factor'].values[0]
            return base_qty * factor

        return base_qty

    def _apply_promotion(self, sku: str, date: datetime, base_qty: float) -> float:
        """应用促销提升"""
        promotion_plan = self.input_data.get("promotion_plan", pd.DataFrame())

        if promotion_plan.empty:
            return base_qty

        # 查找该SKU在该日期的促销
        sku_promotions = promotion_plan[promotion_plan['sku_code'] == sku]

        for _, promo in sku_promotions.iterrows():
            start = pd.to_datetime(promo['start_date'])
            end = pd.to_datetime(promo['end_date'])

            if start <= date <= end:
                uplift = promo.get('uplift_ratio', 1.0)
                return base_qty * uplift

        return base_qty
