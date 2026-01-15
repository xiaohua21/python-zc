#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滑坡易发性评价系统
Landslide Susceptibility Assessment System
"""

import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import from_bounds
import geopandas as gpd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, roc_auc_score, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

class LandslideSusceptibility:
    """滑坡易发性评价主类"""
    
    def __init__(self):
        self.factors = []
        self.factor_names = []
        self.landslide_points = None
        self.non_landslide_points = None
        self.study_area = None
        self.scaler = StandardScaler()
        self.model = None
        self.X_train = None
        self.X_test = None
        self.y_train = None
        self.y_test = None
        
    def load_factors(self, factor_paths):
        """
        加载影响因子栅格数据
        
        Parameters:
        -----------
        factor_paths : list
            影响因子TIF文件路径列表
        """
        print("正在加载影响因子数据...")
        self.factors = []
        self.factor_names = []
        
        for path in factor_paths:
            with rasterio.open(path) as src:
                data = src.read(1)
                self.factors.append({
                    'data': data,
                    'transform': src.transform,
                    'crs': src.crs,
                    'nodata': src.nodata,
                    'bounds': src.bounds,
                    'shape': data.shape
                })
                self.factor_names.append(Path(path).stem)
        
        print(f"已加载 {len(self.factors)} 个影响因子: {', '.join(self.factor_names)}")
        
    def load_points(self, landslide_path, non_landslide_path):
        """
        加载滑坡点和非滑坡点
        
        Parameters:
        -----------
        landslide_path : str
            滑坡点shapefile路径
        non_landslide_path : str
            非滑坡点shapefile路径
        """
        print("正在加载样本点...")
        self.landslide_points = gpd.read_file(landslide_path)
        self.non_landslide_points = gpd.read_file(non_landslide_path)
        
        print(f"滑坡点数量: {len(self.landslide_points)}")
        print(f"非滑坡点数量: {len(self.non_landslide_points)}")
        
    def load_study_area(self, area_path):
        """加载研究区范围"""
        print("正在加载研究区范围...")
        self.study_area = gpd.read_file(area_path)
        print(f"研究区已加载")
        
    def extract_values_at_points(self, points, label):
        """
        提取样本点处的因子值
        
        Parameters:
        -----------
        points : GeoDataFrame
            样本点
        label : int
            标签 (1=滑坡, 0=非滑坡)
            
        Returns:
        --------
        DataFrame
            包含因子值和标签的数据框
        """
        samples = []
        
        for idx, point in points.iterrows():
            x, y = point.geometry.x, point.geometry.y
            sample = {'label': label}
            
            # 提取每个因子在该点的值
            for i, factor in enumerate(self.factors):
                row, col = rasterio.transform.rowcol(
                    factor['transform'], x, y
                )
                
                # 检查是否在栅格范围内
                if 0 <= row < factor['shape'][0] and 0 <= col < factor['shape'][1]:
                    value = factor['data'][row, col]
                    # 处理NoData值
                    if factor['nodata'] is not None and value == factor['nodata']:
                        value = np.nan
                    sample[self.factor_names[i]] = value
                else:
                    sample[self.factor_names[i]] = np.nan
            
            samples.append(sample)
        
        return pd.DataFrame(samples)
    
    def prepare_dataset(self):
        """准备训练数据集"""
        print("\n正在准备数据集...")
        
        # 提取滑坡点和非滑坡点的因子值
        landslide_data = self.extract_values_at_points(self.landslide_points, 1)
        non_landslide_data = self.extract_values_at_points(self.non_landslide_points, 0)
        
        # 合并数据
        data = pd.concat([landslide_data, non_landslide_data], ignore_index=True)
        
        # 删除含有NaN的样本
        data_clean = data.dropna()
        print(f"有效样本数: {len(data_clean)} (滑坡: {sum(data_clean['label']==1)}, 非滑坡: {sum(data_clean['label']==0)})")
        
        # 分离特征和标签
        X = data_clean[self.factor_names].values
        y = data_clean['label'].values
        
        # 归一化处理
        print("正在进行数据归一化...")
        X_normalized = self.scaler.fit_transform(X)
        
        # 划分训练集和测试集 (70% 训练, 30% 测试)
        self.X_train, self.X_test, self.y_train, self.y_test = train_test_split(
            X_normalized, y, test_size=0.3, random_state=42, stratify=y
        )
        
        print(f"训练集样本数: {len(self.X_train)}")
        print(f"测试集样本数: {len(self.X_test)}")
        
        return X_normalized, y
    
    def train_model(self, model_type='random_forest', **kwargs):
        """
        训练模型
        
        Parameters:
        -----------
        model_type : str
            模型类型: 'random_forest', 'svm', 'logistic', 'gradient_boost', 'neural_network'
        **kwargs : dict
            模型参数
        """
        print(f"\n正在训练 {model_type} 模型...")
        
        # 选择模型
        if model_type == 'random_forest':
            self.model = RandomForestClassifier(
                n_estimators=kwargs.get('n_estimators', 100),
                max_depth=kwargs.get('max_depth', 20),
                random_state=42,
                n_jobs=-1
            )
        elif model_type == 'svm':
            self.model = SVC(
                C=kwargs.get('C', 1.0),
                kernel=kwargs.get('kernel', 'rbf'),
                probability=True,
                random_state=42
            )
        elif model_type == 'logistic':
            self.model = LogisticRegression(
                C=kwargs.get('C', 1.0),
                max_iter=1000,
                random_state=42
            )
        elif model_type == 'gradient_boost':
            self.model = GradientBoostingClassifier(
                n_estimators=kwargs.get('n_estimators', 100),
                learning_rate=kwargs.get('learning_rate', 0.1),
                max_depth=kwargs.get('max_depth', 5),
                random_state=42
            )
        elif model_type == 'neural_network':
            self.model = MLPClassifier(
                hidden_layer_sizes=kwargs.get('hidden_layers', (100, 50)),
                max_iter=1000,
                random_state=42
            )
        else:
            raise ValueError(f"未知的模型类型: {model_type}")
        
        # 训练模型
        self.model.fit(self.X_train, self.y_train)
        
        # 模型评估
        self.evaluate_model()
        
    def evaluate_model(self):
        """评估模型性能"""
        print("\n模型评估结果:")
        print("="*50)
        
        # 训练集预测
        y_train_pred = self.model.predict(self.X_train)
        y_train_proba = self.model.predict_proba(self.X_train)[:, 1]
        
        # 测试集预测
        y_test_pred = self.model.predict(self.X_test)
        y_test_proba = self.model.predict_proba(self.X_test)[:, 1]
        
        # 计算指标
        metrics = {
            '训练集': {
                '准确率': accuracy_score(self.y_train, y_train_pred),
                '精确率': precision_score(self.y_train, y_train_pred),
                '召回率': recall_score(self.y_train, y_train_pred),
                'F1分数': f1_score(self.y_train, y_train_pred),
                'AUC': roc_auc_score(self.y_train, y_train_proba)
            },
            '测试集': {
                '准确率': accuracy_score(self.y_test, y_test_pred),
                '精确率': precision_score(self.y_test, y_test_pred),
                '召回率': recall_score(self.y_test, y_test_pred),
                'F1分数': f1_score(self.y_test, y_test_pred),
                'AUC': roc_auc_score(self.y_test, y_test_proba)
            }
        }
        
        # 打印结果
        for dataset, scores in metrics.items():
            print(f"\n{dataset}:")
            for metric, value in scores.items():
                print(f"  {metric}: {value:.4f}")
        
        # 混淆矩阵
        cm = confusion_matrix(self.y_test, y_test_pred)
        print(f"\n混淆矩阵 (测试集):")
        print(cm)
        
        return metrics
    
    def predict_susceptibility(self):
        """预测整个研究区的易发性"""
        print("\n正在预测滑坡易发性...")
        
        # 获取第一个因子的空间信息作为参考
        reference = self.factors[0]
        rows, cols = reference['shape']
        
        # 准备预测数据
        prediction_data = np.zeros((rows * cols, len(self.factors)))
        
        for i, factor in enumerate(self.factors):
            prediction_data[:, i] = factor['data'].flatten()
        
        # 标记有效数据
        valid_mask = np.all(~np.isnan(prediction_data), axis=1)
        
        # 归一化
        prediction_data_normalized = np.full_like(prediction_data, np.nan)
        prediction_data_normalized[valid_mask] = self.scaler.transform(
            prediction_data[valid_mask]
        )
        
        # 预测
        susceptibility = np.full(rows * cols, np.nan)
        susceptibility[valid_mask] = self.model.predict_proba(
            prediction_data_normalized[valid_mask]
        )[:, 1]
        
        # 重塑为栅格
        susceptibility_map = susceptibility.reshape(rows, cols)
        
        print("易发性预测完成！")
        return susceptibility_map, reference
    
    def export_results(self, susceptibility_map, reference, output_dir='output'):
        """
        导出结果
        
        Parameters:
        -----------
        susceptibility_map : ndarray
            易发性预测结果
        reference : dict
            参考栅格信息
        output_dir : str
            输出目录
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        print(f"\n正在导出结果到 {output_dir} ...")
        
        # 1. 导出TIF文件
        tif_path = output_path / 'susceptibility_map.tif'
        with rasterio.open(
            tif_path, 'w',
            driver='GTiff',
            height=susceptibility_map.shape[0],
            width=susceptibility_map.shape[1],
            count=1,
            dtype=susceptibility_map.dtype,
            crs=reference['crs'],
            transform=reference['transform'],
            nodata=np.nan
        ) as dst:
            dst.write(susceptibility_map, 1)
        print(f"✓ TIF文件已保存: {tif_path}")
        
        # 2. 导出CSV文件
        csv_data = []
        rows, cols = susceptibility_map.shape
        for row in range(rows):
            for col in range(cols):
                value = susceptibility_map[row, col]
                if not np.isnan(value):
                    x, y = rasterio.transform.xy(reference['transform'], row, col)
                    csv_data.append({
                        'X': x,
                        'Y': y,
                        'Row': row,
                        'Col': col,
                        'Susceptibility': value
                    })
        
        csv_path = output_path / 'susceptibility_data.csv'
        pd.DataFrame(csv_data).to_csv(csv_path, index=False, encoding='utf-8-sig')
        print(f"✓ CSV文件已保存: {csv_path}")
        
        # 3. 导出统计报告
        report_path = output_path / 'evaluation_report.txt'
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write("滑坡易发性评价报告\n")
            f.write("="*50 + "\n\n")
            f.write(f"影响因子: {', '.join(self.factor_names)}\n")
            f.write(f"训练样本数: {len(self.X_train)}\n")
            f.write(f"测试样本数: {len(self.X_test)}\n\n")
            
            # 写入评估指标
            y_test_pred = self.model.predict(self.X_test)
            y_test_proba = self.model.predict_proba(self.X_test)[:, 1]
            
            f.write("模型性能指标:\n")
            f.write(f"准确率: {accuracy_score(self.y_test, y_test_pred):.4f}\n")
            f.write(f"精确率: {precision_score(self.y_test, y_test_pred):.4f}\n")
            f.write(f"召回率: {recall_score(self.y_test, y_test_pred):.4f}\n")
            f.write(f"F1分数: {f1_score(self.y_test, y_test_pred):.4f}\n")
            f.write(f"AUC: {roc_auc_score(self.y_test, y_test_proba):.4f}\n")
        
        print(f"✓ 评价报告已保存: {report_path}")
        print("\n所有结果导出完成！")


def main():
    """主函数 - 示例使用流程"""
    
    # 创建评价系统实例
    lsa = LandslideSusceptibility()
    
    # 1. 加载影响因子 (你的11个TIF文件)
    factor_paths = [
        'C:/Users/lenovo/Desktop/训练/影像因子列表/NDVIxp.tif',
        'C:/Users/lenovo/Desktop/训练/影像因子列表/xp坡度.tif',
        'C:/Users/lenovo/Desktop/训练/影像因子列表/坡向xp.tif',
        'C:/Users/lenovo/Desktop/训练/影像因子列表/年降雨量xp.tif',
        'C:/Users/lenovo/Desktop/训练/影像因子列表/曲率xp.tif',
        'C:/Users/lenovo/Desktop/训练/影像因子列表/河流密度xp.tif',
        'C:/Users/lenovo/Desktop/训练/影像因子列表/道路密度xp.tif',
        'C:/Users/lenovo/Desktop/训练/影像因子列表/高程xp.tif'
    ]
    lsa.load_factors(factor_paths)
    
    # 2. 加载样本点
    lsa.load_points(
        landslide_path='C:/Users/lenovo/Desktop/训练/滑坡点.shp',
        non_landslide_path='C:/Users/lenovo/Desktop/训练/非滑坡点.shp'
    )
    
    # 3. 加载研究区范围
    lsa.load_study_area('C:/Users/lenovo/Desktop/训练/研究区范围.shp')
    
    # 4. 准备数据集
    lsa.prepare_dataset()
    
    # 5. 训练模型 - 可选择不同模型
    # 随机森林
    lsa.train_model('random_forest', n_estimators=100, max_depth=20)
    
    # 或者使用其他模型:
    # lsa.train_model('svm', C=1.0, kernel='rbf')
    # lsa.train_model('logistic', C=1.0)
    # lsa.train_model('gradient_boost', n_estimators=100, learning_rate=0.1)
    # lsa.train_model('neural_network', hidden_layers=(100, 50))
    
    # 6. 预测易发性
    susceptibility_map, reference = lsa.predict_susceptibility()
    
    # 7. 导出结果
    lsa.export_results(susceptibility_map, reference, output_dir='output')
    
    print("\n" + "="*50)
    print("滑坡易发性评价完成！")
    print("="*50)


if __name__ == '__main__':
    main()
