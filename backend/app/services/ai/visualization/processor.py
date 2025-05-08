"""数据可视化处理器模块

根据查询结果智能推断适合的可视化类型并生成图表配置。
"""

import logging
import json
from typing import Any, Dict, List, Optional, Union, Tuple
from datetime import datetime
import re
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class DataVisualizer:
    """数据可视化处理器类"""
    
    def __init__(self, default_chart_type: str = "table"):
        """
        初始化数据可视化处理器
        
        Args:
            default_chart_type: 默认图表类型，当无法确定合适类型时使用
        """
        self.default_chart_type = default_chart_type
        
        # 支持的图表类型
        self.supported_chart_types = {
            "line": "折线图",
            "bar": "柱状图",
            "horizontal-bar": "条形图",
            "pie": "饼图",
            "scatter": "散点图",
            "area": "面积图",
            "heatmap": "热力图",
            "radar": "雷达图",
            "funnel": "漏斗图",
            "table": "表格",
            "gauge": "仪表盘",
            "treemap": "矩形树图"
        }
    
    def analyze_data_features(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        分析数据特征
        
        Args:
            data: 查询结果数据，列表中的每个字典代表一行数据
            
        Returns:
            数据特征信息字典
        """
        if not data:
            return {"empty": True}
        
        # 将数据转换为DataFrame便于分析
        df = pd.DataFrame(data)
        
        # 识别数据列类型
        column_types = {}
        numerical_columns = []
        categorical_columns = []
        datetime_columns = []
        text_columns = []
        
        for col in df.columns:
            # 检测数值类型
            if pd.api.types.is_numeric_dtype(df[col]):
                column_types[col] = "numerical"
                numerical_columns.append(col)
            # 检测日期类型
            elif self._is_datetime_column(df[col]):
                column_types[col] = "datetime"
                datetime_columns.append(col)
            # 检测分类类型（唯一值较少）
            elif len(df[col].unique()) < max(10, len(df) * 0.2):
                column_types[col] = "categorical"
                categorical_columns.append(col)
            # 其他作为文本类型
            else:
                column_types[col] = "text"
                text_columns.append(col)
        
        # 分析时间趋势
        has_time_series = len(datetime_columns) > 0
        
        # 分析分类数据
        categorical_analysis = {}
        for col in categorical_columns:
            value_counts = df[col].value_counts().to_dict()
            categorical_analysis[col] = {
                "unique_values": len(value_counts),
                "distribution": value_counts
            }
        
        # 分析数值数据
        numerical_analysis = {}
        for col in numerical_columns:
            numerical_analysis[col] = {
                "min": float(df[col].min()) if not pd.isna(df[col].min()) else None,
                "max": float(df[col].max()) if not pd.isna(df[col].max()) else None,
                "mean": float(df[col].mean()) if not pd.isna(df[col].mean()) else None,
                "std": float(df[col].std()) if not pd.isna(df[col].std()) else None
            }
        
        return {
            "empty": False,
            "row_count": len(df),
            "column_count": len(df.columns),
            "column_types": column_types,
            "numerical_columns": numerical_columns,
            "categorical_columns": categorical_columns,
            "datetime_columns": datetime_columns,
            "text_columns": text_columns,
            "has_time_series": has_time_series,
            "categorical_analysis": categorical_analysis,
            "numerical_analysis": numerical_analysis
        }
    
    def _is_datetime_column(self, series: pd.Series) -> bool:
        """
        检测列是否为日期时间类型
        
        Args:
            series: 数据列
            
        Returns:
            是否为日期时间类型
        """
        # 如果已经是日期类型
        if pd.api.types.is_datetime64_dtype(series):
            return True
        
        # 尝试转换为日期类型
        if series.dtype == object:
            # 取样本进行检测
            sample = series.dropna().head(10).tolist()
            if not sample:
                return False
            
            # 常见日期格式正则表达式
            date_patterns = [
                r'^\d{4}-\d{1,2}-\d{1,2}$',  # YYYY-MM-DD
                r'^\d{1,2}/\d{1,2}/\d{4}$',  # MM/DD/YYYY
                r'^\d{1,2}-\d{1,2}-\d{4}$',  # DD-MM-YYYY
                r'^\d{4}/\d{1,2}/\d{1,2}$',  # YYYY/MM/DD
                r'^\d{4}-\d{1,2}-\d{1,2} \d{1,2}:\d{1,2}:\d{1,2}$'  # YYYY-MM-DD HH:MM:SS
            ]
            
            match_count = 0
            for value in sample:
                if isinstance(value, str):
                    for pattern in date_patterns:
                        if re.match(pattern, value):
                            match_count += 1
                            break
            
            # 如果有超过70%的样本匹配日期格式，则认为是日期列
            return match_count / len(sample) >= 0.7
        
        return False
    
    def recommend_chart_type(self, data: List[Dict[str, Any]], features: Optional[Dict[str, Any]] = None) -> str:
        """
        根据数据特征推荐最适合的图表类型
        
        Args:
            data: 查询结果数据
            features: 数据特征，如果未提供则会自动分析
            
        Returns:
            推荐的图表类型
        """
        if not data:
            return "table"  # 空数据使用表格展示
        
        if features is None:
            features = self.analyze_data_features(data)
        
        if features.get("empty", True):
            return "table"
        
        # 行数太多的数据不适合饼图
        row_count = features.get("row_count", 0)
        if row_count > 100:
            large_dataset = True
        else:
            large_dataset = False
        
        numerical_columns = features.get("numerical_columns", [])
        categorical_columns = features.get("categorical_columns", [])
        datetime_columns = features.get("datetime_columns", [])
        
        # 时间序列数据适合折线图或面积图
        if features.get("has_time_series", False) and len(numerical_columns) > 0:
            return "line"
        
        # 单个分类列和单个数值列适合柱状图或饼图
        if len(categorical_columns) == 1 and len(numerical_columns) == 1:
            if row_count <= 10 and not large_dataset:
                return "pie"  # 数据量小适合饼图
            else:
                return "bar"  # 数据量大用柱状图
        
        # 多个分类列和单个数值列适合柱状图
        if len(categorical_columns) > 0 and len(numerical_columns) == 1:
            return "bar"
        
        # 两个数值列适合散点图
        if len(numerical_columns) == 2 and len(categorical_columns) <= 1:
            return "scatter"
        
        # 多个数值列可以使用多系列折线图
        if len(numerical_columns) > 1:
            return "line"
        
        # 默认使用表格
        return "table"
    
    def generate_chart_config(
        self, 
        data: List[Dict[str, Any]], 
        chart_type: Optional[str] = None,
        title: str = "数据可视化",
        description: str = ""
    ) -> Dict[str, Any]:
        """
        生成图表配置
        
        Args:
            data: 查询结果数据
            chart_type: 图表类型，如果未提供则自动推荐
            title: 图表标题
            description: 图表描述
            
        Returns:
            图表配置
        """
        if not data:
            return {
                "chart_type": "table",
                "title": title,
                "description": "没有数据可供可视化",
                "empty": True
            }
        
        # 分析数据特征
        features = self.analyze_data_features(data)
        
        # 如果未指定图表类型，则推荐一个
        if chart_type is None or chart_type not in self.supported_chart_types:
            chart_type = self.recommend_chart_type(data, features)
        
        # 根据图表类型生成配置
        config = {
            "chart_type": chart_type,
            "title": title,
            "description": description,
            "data": data[:100]  # 限制数据量
        }
        
        # 调用相应的配置生成方法
        if chart_type == "line":
            chart_config = self._generate_line_chart_config(data, features)
        elif chart_type == "bar":
            chart_config = self._generate_bar_chart_config(data, features)
        elif chart_type == "horizontal-bar":
            chart_config = self._generate_horizontal_bar_chart_config(data, features)
        elif chart_type == "pie":
            chart_config = self._generate_pie_chart_config(data, features)
        elif chart_type == "scatter":
            chart_config = self._generate_scatter_chart_config(data, features)
        elif chart_type == "area":
            chart_config = self._generate_area_chart_config(data, features)
        elif chart_type == "heatmap":
            chart_config = self._generate_heatmap_chart_config(data, features)
        else:
            # 默认使用表格
            chart_config = self._generate_table_config(data, features)
        
        # 合并配置
        config.update(chart_config)
        
        return config
    
    def _generate_line_chart_config(self, data: List[Dict[str, Any]], features: Dict[str, Any]) -> Dict[str, Any]:
        """生成折线图配置"""
        datetime_columns = features.get("datetime_columns", [])
        numerical_columns = features.get("numerical_columns", [])
        categorical_columns = features.get("categorical_columns", [])
        
        # 确定X轴
        if datetime_columns:
            x_axis = datetime_columns[0]  # 使用第一个时间列作为X轴
            x_axis_type = "time"
        elif categorical_columns:
            x_axis = categorical_columns[0]  # 使用第一个分类列作为X轴
            x_axis_type = "category"
        else:
            x_axis = numerical_columns[0] if numerical_columns else list(data[0].keys())[0]
            x_axis_type = "value"
        
        # 确定Y轴（系列）
        series = []
        if numerical_columns:
            for col in numerical_columns:
                if col != x_axis:  # 避免将X轴也作为Y轴
                    series.append({
                        "name": col,
                        "type": "line",
                        "data": [item.get(col) for item in data]
                    })
        
        # 如果没有找到合适的数值列作为Y轴，尝试使用除X轴外的第一列
        if not series:
            for col in data[0].keys():
                if col != x_axis:
                    series.append({
                        "name": col,
                        "type": "line", 
                        "data": [item.get(col) for item in data]
                    })
                    break
        
        return {
            "x_axis": {
                "name": x_axis,
                "type": x_axis_type,
                "data": [item.get(x_axis) for item in data]
            },
            "y_axis": {
                "type": "value"
            },
            "series": series
        }
    
    def _generate_bar_chart_config(self, data: List[Dict[str, Any]], features: Dict[str, Any]) -> Dict[str, Any]:
        """生成柱状图配置"""
        categorical_columns = features.get("categorical_columns", [])
        numerical_columns = features.get("numerical_columns", [])
        
        # 确定X轴（分类轴）
        if categorical_columns:
            x_axis = categorical_columns[0]
        else:
            # 如果没有分类列，则选择第一列作为X轴
            x_axis = list(data[0].keys())[0]
        
        # 确定Y轴（数值轴）
        series = []
        if numerical_columns:
            for col in numerical_columns:
                if col != x_axis:  # 避免将X轴也作为Y轴
                    series.append({
                        "name": col,
                        "type": "bar",
                        "data": [item.get(col) for item in data]
                    })
        
        # 如果没有找到合适的数值列作为Y轴，尝试使用除X轴外的第一列
        if not series:
            for col in data[0].keys():
                if col != x_axis:
                    series.append({
                        "name": col,
                        "type": "bar", 
                        "data": [item.get(col) for item in data]
                    })
                    break
        
        return {
            "x_axis": {
                "name": x_axis,
                "type": "category",
                "data": [str(item.get(x_axis)) for item in data]
            },
            "y_axis": {
                "type": "value"
            },
            "series": series
        }
    
    def _generate_pie_chart_config(self, data: List[Dict[str, Any]], features: Dict[str, Any]) -> Dict[str, Any]:
        """生成饼图配置"""
        categorical_columns = features.get("categorical_columns", [])
        numerical_columns = features.get("numerical_columns", [])
        
        # 确定名称列和数值列
        if categorical_columns and numerical_columns:
            name_column = categorical_columns[0]
            value_column = numerical_columns[0]
        elif categorical_columns:
            name_column = categorical_columns[0]
            # 使用计数作为数值
            value_column = None
        else:
            # 使用第一列作为名称列，第二列作为数值列
            cols = list(data[0].keys())
            name_column = cols[0]
            value_column = cols[1] if len(cols) > 1 else None
        
        # 准备数据
        pie_data = []
        for item in data:
            name = str(item.get(name_column, ""))
            value = item.get(value_column, 1) if value_column else 1
            pie_data.append({"name": name, "value": value})
        
        return {
            "series": [{
                "type": "pie",
                "data": pie_data,
                "name": value_column or "计数"
            }]
        }
    
    def _generate_scatter_chart_config(self, data: List[Dict[str, Any]], features: Dict[str, Any]) -> Dict[str, Any]:
        """生成散点图配置"""
        numerical_columns = features.get("numerical_columns", [])
        categorical_columns = features.get("categorical_columns", [])
        
        # 散点图需要至少两个数值列
        if len(numerical_columns) >= 2:
            x_column = numerical_columns[0]
            y_column = numerical_columns[1]
        else:
            # 如果没有足够的数值列，尝试使用前两列
            cols = list(data[0].keys())
            x_column = cols[0]
            y_column = cols[1] if len(cols) > 1 else cols[0]
        
        # 如果有分类列，可以用来区分不同系列
        series_column = categorical_columns[0] if categorical_columns else None
        
        if series_column:
            # 按系列分组
            groups = {}
            for item in data:
                series_value = str(item.get(series_column, "其他"))
                if series_value not in groups:
                    groups[series_value] = []
                groups[series_value].append([
                    item.get(x_column), 
                    item.get(y_column)
                ])
            
            series = []
            for name, points in groups.items():
                series.append({
                    "name": name,
                    "type": "scatter",
                    "data": points
                })
        else:
            # 单系列散点图
            series = [{
                "type": "scatter",
                "data": [[item.get(x_column), item.get(y_column)] for item in data]
            }]
        
        return {
            "x_axis": {
                "name": x_column,
                "type": "value"
            },
            "y_axis": {
                "name": y_column,
                "type": "value"
            },
            "series": series
        }
    
    def _generate_area_chart_config(self, data: List[Dict[str, Any]], features: Dict[str, Any]) -> Dict[str, Any]:
        """生成面积图配置"""
        # 面积图配置与折线图类似，但系列类型为area
        line_config = self._generate_line_chart_config(data, features)
        
        for series in line_config.get("series", []):
            series["type"] = "line"
            series["areaStyle"] = {}  # 添加面积样式
        
        return line_config
    
    def _generate_table_config(self, data: List[Dict[str, Any]], features: Dict[str, Any]) -> Dict[str, Any]:
        """生成表格配置"""
        if not data:
            return {
                "columns": [],
                "data_source": []
            }
        
        # 获取所有列
        columns = list(data[0].keys())
        
        # 构建列配置
        column_configs = []
        for col in columns:
            column_configs.append({
                "title": col,
                "dataIndex": col,
                "key": col
            })
        
        return {
            "columns": column_configs,
            "data_source": data
        }
    
    def _generate_horizontal_bar_chart_config(self, data: List[Dict[str, Any]], features: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成水平条形图配置
        
        Args:
            data: 查询结果数据
            features: 数据特征
            
        Returns:
            水平条形图配置
        """
        categorical_columns = features.get("categorical_columns", [])
        numerical_columns = features.get("numerical_columns", [])
        
        if not categorical_columns or not numerical_columns:
            return self._generate_table_config(data, features)
        
        # 选择分类列作为Y轴
        y_axis = categorical_columns[0]
        
        # 选择数值列作为X轴
        x_axis = numerical_columns[0]
        
        # 对数据进行排序
        df = pd.DataFrame(data)
        df = df.sort_values(by=x_axis, ascending=False)
        
        # 限制数据点数量，保留前15个
        if len(df) > 15:
            df = df.head(15)
        
        # 转换回字典列表
        sorted_data = df.to_dict(orient="records")
        
        return {
            "x_axis": x_axis,
            "y_axis": y_axis,
            "data": sorted_data,
            "sort_by": x_axis,
            "sort_order": "desc",
            "limit": 15,
            "description": f"展示按{x_axis}排序的{y_axis}数据，采用水平条形图更适合展示类别标签较长的场景"
        }
    
    def _generate_heatmap_chart_config(self, data: List[Dict[str, Any]], features: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成热力图配置
        
        Args:
            data: 查询结果数据
            features: 数据特征
            
        Returns:
            热力图配置
        """
        categorical_columns = features.get("categorical_columns", [])
        numerical_columns = features.get("numerical_columns", [])
        
        if len(categorical_columns) < 2 or not numerical_columns:
            return self._generate_table_config(data, features)
        
        # 选择两个分类列作为X轴和Y轴
        x_axis = categorical_columns[0]
        y_axis = categorical_columns[1] if len(categorical_columns) > 1 else categorical_columns[0]
        
        # 选择数值列作为色彩值
        value_field = numerical_columns[0]
        
        # 将数据转为DataFrame以便处理
        df = pd.DataFrame(data)
        
        # 对数据进行聚合
        pivot_data = None
        try:
            # 尝试创建透视表
            pivot_data = df.pivot_table(
                index=y_axis, 
                columns=x_axis, 
                values=value_field,
                aggfunc='sum'
            ).fillna(0)
            
            # 转换为热力图所需格式
            heatmap_data = []
            for y_val in pivot_data.index:
                for x_val in pivot_data.columns:
                    heatmap_data.append({
                        x_axis: x_val,
                        y_axis: y_val,
                        value_field: float(pivot_data.loc[y_val, x_val])
                    })
        except Exception as e:
            # 如果失败，回退到表格
            return self._generate_table_config(data, features)
        
        return {
            "x_axis": x_axis,
            "y_axis": y_axis, 
            "value_field": value_field,
            "data": heatmap_data,
            "aggregation": "sum",
            "description": f"展示{x_axis}和{y_axis}之间的{value_field}分布热力图，颜色强度表示{value_field}的数值大小"
        } 