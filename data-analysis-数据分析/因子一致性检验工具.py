#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
滑坡易发性评价因子一致性检查工具
GUI界面版本
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import rasterio
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os
from datetime import datetime

class FactorCheckerGUI:
    """因子一致性检查工具 - GUI版本"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("滑坡因子一致性检查工具 v1.0")
        self.root.geometry("1000x700")
        
        # 存储因子信息
        self.factor_paths = []
        self.factor_info = []
        
        # 设置样式
        self.setup_styles()
        
        # 创建界面
        self.create_widgets()
        
    def setup_styles(self):
        """设置界面样式"""
        style = ttk.Style()
        style.theme_use('clam')  # 使用现代主题
        
        # 自定义颜色
        self.bg_color = "#f0f0f0"
        self.frame_bg = "#ffffff"
        self.accent_color = "#2c3e50"
        self.button_color = "#3498db"
        
        self.root.configure(bg=self.bg_color)
        
    def create_widgets(self):
        """创建界面组件"""
        
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # === 顶部标题 ===
        title_label = tk.Label(
            main_frame, 
            text="📊 滑坡易发性评价因子一致性检查",
            font=("Arial", 16, "bold"),
            fg=self.accent_color,
            bg=self.bg_color
        )
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # === 第1部分：目录选择 ===
        dir_frame = ttk.LabelFrame(main_frame, text="1. 选择因子目录", padding="10")
        dir_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        dir_frame.columnconfigure(1, weight=1)
        
        # 目录路径标签和按钮
        ttk.Label(dir_frame, text="因子目录:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        
        self.dir_var = tk.StringVar()
        dir_entry = ttk.Entry(dir_frame, textvariable=self.dir_var, width=50)
        dir_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=5)
        
        browse_btn = ttk.Button(
            dir_frame, 
            text="浏览...", 
            command=self.browse_directory,
            style="Accent.TButton"
        )
        browse_btn.grid(row=0, column=2, padx=(5, 0))
        
        # 文件过滤器
        filter_frame = ttk.Frame(dir_frame)
        filter_frame.grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        
        ttk.Label(filter_frame, text="文件类型:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.filter_var = tk.StringVar(value=".tif")
        filters = [(".tif 文件", "*.tif"), (".tiff 文件", "*.tiff"), ("所有文件", "*.*")]
        
        for text, pattern in filters:
            ttk.Radiobutton(
                filter_frame, 
                text=text, 
                variable=self.filter_var, 
                value=pattern
            ).pack(side=tk.LEFT, padx=(0, 10))
        
        # === 第2部分：因子文件列表 ===
        list_frame = ttk.LabelFrame(main_frame, text="2. 因子文件列表", padding="10")
        list_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 文件列表树状视图
        columns = ("序号", "文件名", "路径", "状态")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=8)
        
        # 设置列标题
        col_widths = [50, 150, 300, 100]
        for col, width in zip(columns, col_widths):
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width, anchor=tk.W)
        
        # 滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # === 第3部分：控制按钮 ===
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=3, column=0, columnspan=3, pady=(0, 10))
        
        self.check_btn = ttk.Button(
            button_frame,
            text="🔍 开始检查一致性",
            command=self.check_consistency,
            style="Accent.TButton",
            state="disabled"
        )
        self.check_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.clear_btn = ttk.Button(
            button_frame,
            text="🗑️ 清空列表",
            command=self.clear_list
        )
        self.clear_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.export_btn = ttk.Button(
            button_frame,
            text="📥 导出报告",
            command=self.export_report,
            state="disabled"
        )
        self.export_btn.pack(side=tk.LEFT)
        
        # === 第4部分：检查结果 ===
        result_frame = ttk.LabelFrame(main_frame, text="3. 检查结果", padding="10")
        result_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        
        # 结果表格
        result_columns = ("因子", "宽度", "高度", "像元总数", "坐标系", "分辨率X", "分辨率Y", "状态")
        self.result_tree = ttk.Treeview(result_frame, columns=result_columns, show="headings", height=6)
        
        result_col_widths = [120, 70, 70, 90, 100, 80, 80, 100]
        for col, width in zip(result_columns, result_col_widths):
            self.result_tree.heading(col, text=col)
            self.result_tree.column(col, width=width, anchor=tk.CENTER)
        
        result_scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=result_scrollbar.set)
        
        self.result_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        result_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # 统计信息标签
        self.stats_label = tk.Label(
            result_frame,
            text="等待检查...",
            font=("Arial", 10),
            anchor=tk.W,
            bg=self.frame_bg
        )
        self.stats_label.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # === 第5部分：日志输出 ===
        log_frame = ttk.LabelFrame(main_frame, text="4. 检查日志", padding="10")
        log_frame.grid(row=5, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S))
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            width=80,
            height=10,
            font=("Courier New", 9)
        )
        self.log_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置日志区域
        self.log_text.tag_config("INFO", foreground="black")
        self.log_text.tag_config("WARNING", foreground="orange")
        self.log_text.tag_config("ERROR", foreground="red")
        self.log_text.tag_config("SUCCESS", foreground="green")
        
        # 添加初始日志
        self.log("INFO", "=" * 60)
        self.log("INFO", "滑坡易发性评价因子一致性检查工具")
        self.log("INFO", f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.log("INFO", "=" * 60)
        
    def browse_directory(self):
        """浏览选择目录"""
        directory = filedialog.askdirectory(title="选择包含因子文件的目录")
        if directory:
            self.dir_var.set(directory)
            self.scan_directory()
    
    def scan_directory(self):
        """扫描目录中的栅格文件"""
        directory = self.dir_var.get()
        if not directory or not os.path.exists(directory):
            return
        
        # 清空现有列表
        self.clear_treeview(self.tree)
        self.factor_paths = []
        self.factor_info = []
        
        # 获取文件扩展名过滤条件
        ext_filter = self.filter_var.get()
        
        # 扫描文件
        found_files = []
        for ext in [ext_filter, "*"] if ext_filter != "*.*" else ["*"]:
            pattern = f"*{ext}" if ext != "*" else "*"
            for file_path in Path(directory).rglob(pattern):
                if file_path.is_file():
                    found_files.append(file_path)
        
        # 排序并添加
        found_files.sort()
        
        for idx, file_path in enumerate(found_files[:100], 1):  # 限制最多100个文件
            self.factor_paths.append(str(file_path))
            self.tree.insert("", "end", values=(
                idx,
                file_path.name,
                str(file_path.parent),
                "待检查"
            ))
        
        if found_files:
            self.check_btn.config(state="normal")
            self.log("SUCCESS", f"找到 {len(found_files)} 个文件")
        else:
            self.log("WARNING", f"未找到匹配 {ext_filter} 的文件")
    
    def clear_treeview(self, treeview):
        """清空树状视图"""
        for item in treeview.get_children():
            treeview.delete(item)
    
    def log(self, level, message):
        """添加日志信息"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_msg, level)
        self.log_text.see(tk.END)
        self.root.update_idletasks()
    
    def check_consistency(self):
        """检查因子一致性"""
        if not self.factor_paths:
            self.log("ERROR", "没有可检查的文件")
            return
        
        # 清空结果表格
        self.clear_treeview(self.result_tree)
        self.factor_info = []
        
        self.log("INFO", "=" * 60)
        self.log("INFO", "开始检查因子一致性...")
        
        # 检查每个因子
        reference_info = None
        inconsistent_factors = []
        
        for i, path in enumerate(self.factor_paths, 1):
            try:
                with rasterio.open(path) as src:
                    info = {
                        'name': Path(path).name,
                        'path': path,
                        'width': src.width,
                        'height': src.height,
                        'total_pixels': src.width * src.height,
                        'crs': str(src.crs) if src.crs else "无",
                        'res_x': src.transform.a,
                        'res_y': abs(src.transform.e),
                        'bounds': src.bounds,
                        'nodata': src.nodata,
                        'dtype': src.dtypes[0]
                    }
                    
                    self.factor_info.append(info)
                    
                    # 确定参考因子（第一个有效的因子）
                    if reference_info is None:
                        reference_info = info
                        status = "参考因子"
                        status_tag = "SUCCESS"
                    else:
                        # 检查一致性
                        is_consistent = True
                        issues = []
                        
                        # 检查尺寸
                        if info['width'] != reference_info['width']:
                            issues.append(f"宽度不一致 ({info['width']} != {reference_info['width']})")
                            is_consistent = False
                        if info['height'] != reference_info['height']:
                            issues.append(f"高度不一致 ({info['height']} != {reference_info['height']})")
                            is_consistent = False
                        
                        # 检查坐标系
                        if info['crs'] != reference_info['crs']:
                            issues.append("坐标系不一致")
                            is_consistent = False
                        
                        # 检查分辨率（允许微小差异）
                        if abs(info['res_x'] - reference_info['res_x']) > 0.001:
                            issues.append(f"X分辨率差异 ({info['res_x']:.6f} != {reference_info['res_x']:.6f})")
                            is_consistent = False
                        if abs(info['res_y'] - reference_info['res_y']) > 0.001:
                            issues.append(f"Y分辨率差异 ({info['res_y']:.6f} != {reference_info['res_y']:.6f})")
                            is_consistent = False
                        
                        if is_consistent:
                            status = "✓ 一致"
                            status_tag = "SUCCESS"
                        else:
                            status = "✗ 不一致: " + "; ".join(issues)
                            status_tag = "ERROR"
                            inconsistent_factors.append((info['name'], issues))
                    
                    # 添加到结果表格
                    self.result_tree.insert("", "end", values=(
                        info['name'],
                        info['width'],
                        info['height'],
                        f"{info['total_pixels']:,}",
                        info['crs'][:15] + "..." if len(info['crs']) > 15 else info['crs'],
                        f"{info['res_x']:.4f}",
                        f"{info['res_y']:.4f}",
                        status
                    ))
                    
                    # 记录日志
                    log_msg = f"检查: {info['name']} - {status}"
                    self.log(status_tag.split('.')[0], log_msg)
                    
            except Exception as e:
                error_msg = f"无法读取文件: {Path(path).name} - {str(e)}"
                self.result_tree.insert("", "end", values=(
                    Path(path).name,
                    "ERROR",
                    "ERROR",
                    "ERROR",
                    "ERROR",
                    "ERROR",
                    "ERROR",
                    f"读取失败"
                ))
                self.log("ERROR", error_msg)
        
        # 更新统计信息
        total_factors = len(self.factor_info)
        consistent_count = total_factors - len(inconsistent_factors)
        
        stats_text = f"检查完成: 共 {total_factors} 个因子 | "
        stats_text += f"一致: {consistent_count} | "
        stats_text += f"不一致: {len(inconsistent_factors)}"
        
        self.stats_label.config(text=stats_text)
        
        # 显示不一致的详细信息
        if inconsistent_factors:
            self.log("WARNING", "-" * 60)
            self.log("WARNING", "不一致因子详情:")
            for factor_name, issues in inconsistent_factors:
                self.log("WARNING", f"  {factor_name}:")
                for issue in issues:
                    self.log("WARNING", f"    - {issue}")
        
        self.log("INFO", "=" * 60)
        self.log("SUCCESS", f"一致性检查完成！")
        
        # 启用导出按钮
        self.export_btn.config(state="normal")
    
    def clear_list(self):
        """清空文件列表"""
        self.clear_treeview(self.tree)
        self.clear_treeview(self.result_tree)
        self.factor_paths = []
        self.factor_info = []
        self.stats_label.config(text="等待检查...")
        self.check_btn.config(state="disabled")
        self.export_btn.config(state="disabled")
        self.log("INFO", "列表已清空")
    
    def export_report(self):
        """导出检查报告"""
        if not self.factor_info:
            messagebox.showwarning("警告", "没有可导出的数据")
            return
        
        # 选择保存位置
        file_path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[
                ("Excel文件", "*.xlsx"),
                ("CSV文件", "*.csv"),
                ("文本文件", "*.txt")
            ],
            title="保存检查报告"
        )
        
        if not file_path:
            return
        
        try:
            # 准备数据
            data = []
            for info in self.factor_info:
                data.append({
                    '文件名': info['name'],
                    '文件路径': info['path'],
                    '宽度(列数)': info['width'],
                    '高度(行数)': info['height'],
                    '像元总数': info['total_pixels'],
                    '坐标系': info['crs'],
                    'X分辨率': info['res_x'],
                    'Y分辨率': info['res_y'],
                    '无效值': info['nodata'],
                    '数据类型': info['dtype'],
                    '左上X': info['bounds'][0],
                    '左上Y': info['bounds'][1],
                    '右下X': info['bounds'][2],
                    '右下Y': info['bounds'][3]
                })
            
            df = pd.DataFrame(data)
            
            # 根据文件类型保存
            if file_path.endswith('.xlsx'):
                with pd.ExcelWriter(file_path, engine='openpyxl') as writer:
                    df.to_excel(writer, sheet_name='因子信息', index=False)
                    
                    # 添加统计信息
                    stats_df = pd.DataFrame([{
                        '检查时间': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        '总因子数': len(df),
                        '宽度范围': f"{df['宽度(列数)'].min()} - {df['宽度(列数)'].max()}",
                        '高度范围': f"{df['高度(行数)'].min()} - {df['高度(列数)'].max()}",
                        '不一致数量': len(df[df['宽度(列数)'] != df['宽度(列数)'].iloc[0]])
                    }])
                    stats_df.to_excel(writer, sheet_name='统计信息', index=False)
                    
            elif file_path.endswith('.csv'):
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("滑坡因子一致性检查报告\n")
                    f.write("=" * 60 + "\n\n")
                    f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"总因子数: {len(df)}\n\n")
                    
                    f.write("详细信息:\n")
                    f.write("-" * 60 + "\n")
                    for _, row in df.iterrows():
                        f.write(f"\n文件: {row['文件名']}\n")
                        f.write(f"  尺寸: {row['宽度(列数)']} × {row['高度(行数)']} = {row['像元总数']:,} 像元\n")
                        f.write(f"  分辨率: {row['X分辨率']:.6f}, {row['Y分辨率']:.6f}\n")
                        f.write(f"  坐标系: {row['坐标系']}\n")
            
            self.log("SUCCESS", f"报告已导出到: {file_path}")
            messagebox.showinfo("成功", f"报告已成功导出到:\n{file_path}")
            
        except Exception as e:
            self.log("ERROR", f"导出失败: {str(e)}")
            messagebox.showerror("错误", f"导出失败:\n{str(e)}")


def main():
    """主函数"""
    root = tk.Tk()
    app = FactorCheckerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()