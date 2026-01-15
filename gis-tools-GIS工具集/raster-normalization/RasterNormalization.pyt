# -*- coding: utf-8 -*-
"""
RasterNormalization.pyt
批量对文件夹内所有 TIF 栅格进行归一化处理
支持三种方法：
1. 线性归一化（Min-Max）
2. Z-score 标准化
3. 标准差归一化（Mean / Std）
自动输出 CSV（UTF-8 BOM，Excel 不乱码）
含进度条显示
"""

import arcpy
import os
import csv


class Toolbox(object):
    def __init__(self):
        self.label = "批量栅格归一化工具"
        self.alias = "RasterNormalizationToolbox"
        self.tools = [RasterNormalization]


class RasterNormalization(object):
    def __init__(self):
        self.label = "栅格归一化"
        self.description = "对文件夹内所有 TIF 栅格进行批量归一化，并输出统计 CSV 表"


    def getParameterInfo(self):
        params = [
            arcpy.Parameter(
                displayName="输入文件夹",
                name="input_folder",
                datatype="DEFolder",
                parameterType="Required",
                direction="Input"
            ),
            arcpy.Parameter(
                displayName="输出文件夹",
                name="output_folder",
                datatype="DEFolder",
                parameterType="Required",
                direction="Output"
            ),
            arcpy.Parameter(
                displayName="归一化方法",
                name="method",
                datatype="GPString",
                parameterType="Required",
                direction="Input"
            ),
            arcpy.Parameter(
                displayName="CSV 输出路径（可为空）",
                name="csv_output",
                datatype="DEFile",
                parameterType="Optional",
                direction="Output"
            )
        ]

        params[2].filter.type = "ValueList"
        params[2].filter.list = [
            "线性归一化 (Min-Max)",
            "Z-score标准化",
            "标准差归一化 (Mean/Std)"
        ]

        return params


    def isLicensed(self):
        return True


    def execute(self, parameters, messages):

        input_folder = parameters[0].valueAsText
        output_folder = parameters[1].valueAsText
        method = parameters[2].valueAsText
        csv_output = parameters[3].valueAsText

        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        if not csv_output:
            csv_output = os.path.join(output_folder, "raster_statistics.csv")

        arcpy.env.workspace = input_folder
        arcpy.env.overwriteOutput = True

        tif_files = arcpy.ListRasters("*.tif")
        if not tif_files:
            arcpy.AddWarning("⚠️ 未检测到 TIF 栅格文件")
            return

        # ===== 创建 CSV（UTF-8 BOM，Excel 不乱码）=====
        with open(csv_output, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                '文件名',
                '最小值',
                '最大值',
                '均值',
                '标准差',
                '归一化方法',
                '状态'
            ])

        # ===== 进度条 =====
        arcpy.SetProgressor(
            "step",
            "正在批量归一化栅格...",
            0,
            len(tif_files),
            1
        )

        for idx, tif in enumerate(tif_files, start=1):
            try:
                input_raster = os.path.join(input_folder, tif)
                base_name = os.path.splitext(tif)[0]
                output_raster = os.path.join(
                    output_folder,
                    f"{base_name}_normalized.tif"
                )

                arcpy.AddMessage(f"\n正在处理 {idx}/{len(tif_files)}：{tif}")
                arcpy.CalculateStatistics_management(input_raster)

                min_val = float(arcpy.GetRasterProperties_management(input_raster, "MINIMUM").getOutput(0))
                max_val = float(arcpy.GetRasterProperties_management(input_raster, "MAXIMUM").getOutput(0))
                mean_val = float(arcpy.GetRasterProperties_management(input_raster, "MEAN").getOutput(0))
                std_val = float(arcpy.GetRasterProperties_management(input_raster, "STD").getOutput(0))

                in_ras = arcpy.Raster(input_raster)

                # ===== 归一化 =====
                if method == "线性归一化 (Min-Max)":
                    normalized = (in_ras - min_val) / (max_val - min_val) if max_val != min_val else in_ras * 0

                elif method == "Z-score标准化":
                    normalized = (in_ras - mean_val) / std_val if std_val != 0 else in_ras * 0

                elif method == "标准差归一化 (Mean/Std)":
                    normalized = in_ras / std_val if std_val != 0 else in_ras * 0

                else:
                    raise ValueError("未知归一化方法")

                normalized.save(output_raster)
                arcpy.AddMessage(f"  ✅ 已保存：{output_raster}")

                # ===== 写 CSV（UTF-8 BOM）=====
                with open(csv_output, 'a', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([
                        tif,
                        min_val,
                        max_val,
                        mean_val,
                        std_val,
                        method,
                        '成功'
                    ])

            except Exception as e:
                arcpy.AddError(f"❌ 处理失败：{tif} | {str(e)}")
                with open(csv_output, 'a', newline='', encoding='utf-8-sig') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerow([
                        tif,
                        '',
                        '',
                        '',
                        '',
                        method,
                        '失败'
                    ])

            arcpy.SetProgressorPosition(idx)

        arcpy.ResetProgressor()
        arcpy.AddMessage("\n✅ 所有栅格处理完成")
        arcpy.AddMessage(f"📄 CSV 已生成：{csv_output}")
