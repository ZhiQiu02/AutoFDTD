import numpy as np
import importlib
import os
import time
import numpy as np
import pandas as pd
import csv

# ================== 全局参数控制 ==================
FSP_FILENAME = "../Base_model.fsp"
pixel_size = 130e-9
si_layer_thickness = 220e-9
air_hole_radius = 45e-9

# 数据集保存参数
SAVE_INTERVAL = 100  # 每100次迭代保存一次数据
DATA_DIR = "../dataset"  # 数据集保存目录
os.makedirs(DATA_DIR, exist_ok=True)  # 创建数据集目录

# 初始化数据集
structures = []
transmissions = []

lumapi_path = r'C:\Program Files\Lumerical\v241\api\python\lumapi.py'
spec = importlib.util.spec_from_file_location("lumapi", lumapi_path)
lumapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lumapi)
fdtd = lumapi.FDTD(hide=True, newproject=True)
# 生成20×20的随机01矩阵
# def create_airholes_batch(fdtd, structure_matrix):
#     try:
#         ssss = time.time()
#         script_lines = [
#             "addstructuregroup;",  # 分号单独一行更清晰
#             "set('name', 'air_holes_group');",
#         ]
#         sx = time.time()
#         for i in range(20):
#             for j in range(20):
#                 if structure_matrix[i, j] == 0:
#                     script_lines.append(f"""
#                            addcircle;
#                            set('name', 'air_hole_{i}_{j}');
#                            set('x', {(j - 9.5) * 130e-9});
#                            set('y', {(i - 9.5) * 130e-9});
#                            set('z', {220e-9 / 2});
#                            set('z span', {220e-9});
#                            set('radius', {45e-9});
#                            set('material', 'etch');
#                            select('air_hole_{i}_{j}');
#                            addtogroup('air_holes_group');
#                        """.strip())
#         ex = time.time()
#         print(f"添加script: {ex - sx} 秒")
#
#         fdtd.eval('\n'.join(script_lines))
#         eeee  = time.time()
#         print(f"create_airholes_batch time: {eeee - ssss}")
#         return True
#     except Exception as e:
#         print(f"Error in create_airholes_batch: {str(e)}")
#         return False
#
# 预计算所有可能的位置 - 避免循环中计算
X_POSITIONS = tuple((i - 9.5) * 130e-9 for i in range(20))
Y_POSITIONS = tuple((j - 9.5) * 130e-9 for j in range(20))
Z_POS = 110e-9  # 220e-9 / 2
Z_SPAN = 220e-9
RADIUS = 45e-9

# def create_airholes_batch(fdtd, structure_matrix):
#     # 生成所有(i,j)坐标对
#     i, j = np.meshgrid(np.arange(20), np.arange(20), indexing='ij')
#     valid = structure_matrix == 0
#     coords = np.stack([i[valid], j[valid]], axis=1)  # 所有需要创建空气孔的(i,j)
#
#     script = ["addstructuregroup; set('name', 'air_holes_group');"]
#     for idx, (i_val, j_val) in enumerate(coords):
#         script.append(f"""
#             addcircle;
#             set('name', 'air_hole_{idx}');
#             set('x', {(i_val - 9.5) * 130e-9});
#             set('y', {(j_val - 9.5) * 130e-9});
#             set('z', {220e-9 / 2});
#             set('z span', {220e-9});
#             set('radius', {45e-9});
#             set('material', 'etch');
#             select('air_hole_{idx}');
#             addtogroup('air_holes_group');
#         """)
#     fdtd.eval('\n'.join(script))

def create_airholes_fixed(fdtd, structure_matrix):
    start_time = time.time()

    # 构建创建孔的脚本
    hole_script = []
    for i in range(20):
        for j in range(20):
            if structure_matrix[i, j] == 0:
                # 使用预计算的位置值
                x = X_POSITIONS[i]
                y = Y_POSITIONS[j]

                # 直接构建命令字符串
                hole_script.append(f"addcircle;")
                hole_script.append(f"set('name', 'air_hole_{i}_{j}');")
                hole_script.append(f"set('x', {x});")
                hole_script.append(f"set('y', {y});")
                hole_script.append(f"set('z', {Z_POS});")
                hole_script.append(f"set('z span', {Z_SPAN});")
                hole_script.append(f"set('radius', {RADIUS});")
                hole_script.append(f"set('material', 'etch');")

    # 如果有孔需要创建
    if hole_script:
        # 添加组创建命令
        script_lines = [
            "addstructuregroup;",
            "set('name', 'air_holes_group');",
            *hole_script,
            "select('air_hole_*');",
            "addtogroup('air_holes_group');"
        ]

        # 一次性执行所有命令
        fdtd.eval(';\n'.join(script_lines))

    print(f"打孔时间: {time.time() - start_time:.4f}秒")
    return True


fdtd.load("Base_model.fsp")
fdtd.switchtolayout()
fdtd.select("air_holes_group")
fdtd.delete()
s2 = time.time()
create_airholes_fixed(fdtd, structure_matrix = np.random.randint(0, 2, size=(20, 20)))
e2 = time.time()
print(f"第1次迭代耗时: {e2 - s2} 秒")

stest = time.time()
fdtd.load("Base_model.fsp")
fdtd.switchtolayout()
fdtd.select("air_holes_group")
fdtd.delete()
etest = time.time()
print(f"test time: {etest - stest}")
s2 = time.time()
create_airholes_fixed(fdtd, structure_matrix = np.random.randint(0, 2, size=(20, 20)))
e2 = time.time()
print(f"第1次迭代耗时: {e2 - s2} 秒")
fdtd.load("Base_model.fsp")
fdtd.switchtolayout()
fdtd.select("air_holes_group")
fdtd.delete()
s2 = time.time()
create_airholes_fixed(fdtd, structure_matrix = np.random.randint(0, 2, size=(20, 20)))
e2 = time.time()
print(f"第1次迭代耗时: {e2 - s2} 秒")
fdtd.load("Base_model.fsp")
fdtd.switchtolayout()
fdtd.select("air_holes_group")
fdtd.delete()
s2 = time.time()
create_airholes_fixed(fdtd, structure_matrix = np.random.randint(0, 2, size=(20, 20)))
e2 = time.time()
print(f"第1次迭代耗时: {e2 - s2} 秒")