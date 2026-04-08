"""
基础模块类 - 所有计算模块的父类
定义了统一的接口和数据处理流程
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import pandas as pd
import json
import os


class BaseModule(ABC):
    """
    基础计算模块抽象类

    所有计算模块都需要:
    1. 加载配置文件
    2. 加载输入数据
    3. 执行计算
    4. 输出结果
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化模块

        Args:
            config_path: 配置文件路径，如果为None则使用默认配置
        """
        self.config: Dict[str, Any] = {}
        self.input_data: Dict[str, pd.DataFrame] = {}
        self.output_data: Dict[str, pd.DataFrame] = {}

        if config_path:
            self.load_config(config_path)
        else:
            self.config = self.get_default_config()

    @abstractmethod
    def get_default_config(self) -> Dict[str, Any]:
        """返回模块的默认配置"""
        pass

    @abstractmethod
    def get_required_inputs(self) -> Dict[str, list]:
        """
        返回模块所需的输入数据说明

        Returns:
            Dict: {
                "数据名称": ["必需字段1", "必需字段2", ...]
            }
        """
        pass

    @abstractmethod
    def calculate(self) -> Dict[str, pd.DataFrame]:
        """
        执行核心计算逻辑

        Returns:
            Dict: 计算结果，key为结果名称，value为DataFrame
        """
        pass

    def load_config(self, config_path: str) -> None:
        """加载JSON配置文件"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)

    def save_config(self, config_path: str) -> None:
        """保存配置到JSON文件"""
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, ensure_ascii=False, indent=2)

    def load_input_data(self, data_name: str, file_path: str) -> pd.DataFrame:
        """
        加载CSV输入数据

        Args:
            data_name: 数据名称（用于内部存储）
            file_path: CSV文件路径

        Returns:
            加载的DataFrame
        """
        df = pd.read_csv(file_path, encoding='utf-8')
        self.input_data[data_name] = df
        return df

    def set_input_data(self, data_name: str, df: pd.DataFrame) -> None:
        """直接设置输入数据（用于模块间数据传递）"""
        self.input_data[data_name] = df

    def validate_input(self, data_name: str) -> bool:
        """
        验证输入数据是否包含必需字段

        Args:
            data_name: 要验证的数据名称

        Returns:
            验证是否通过
        """
        required = self.get_required_inputs()
        if data_name not in required:
            return True

        if data_name not in self.input_data:
            raise ValueError(f"缺少必需的输入数据: {data_name}")

        df = self.input_data[data_name]
        missing_cols = set(required[data_name]) - set(df.columns)

        if missing_cols:
            raise ValueError(f"数据 '{data_name}' 缺少必需字段: {missing_cols}")

        return True

    def validate_all_inputs(self) -> bool:
        """验证所有必需的输入数据"""
        for data_name in self.get_required_inputs().keys():
            self.validate_input(data_name)
        return True

    def run(self) -> Dict[str, pd.DataFrame]:
        """
        执行完整的计算流程

        Returns:
            计算结果
        """
        # 1. 验证输入
        self.validate_all_inputs()

        # 2. 执行计算
        self.output_data = self.calculate()

        return self.output_data

    def export_results(self, output_dir: str) -> Dict[str, str]:
        """
        导出计算结果到CSV文件

        Args:
            output_dir: 输出目录

        Returns:
            Dict: {结果名称: 文件路径}
        """
        os.makedirs(output_dir, exist_ok=True)
        exported_files = {}

        for name, df in self.output_data.items():
            file_path = os.path.join(output_dir, f"{name}.csv")
            df.to_csv(file_path, index=False, encoding='utf-8-sig')
            exported_files[name] = file_path

        return exported_files

    def get_output(self, name: str) -> Optional[pd.DataFrame]:
        """获取指定名称的输出结果"""
        return self.output_data.get(name)
