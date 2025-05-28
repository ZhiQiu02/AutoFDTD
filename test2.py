import importlib
import os
import time
import numpy as np

# ================== 全局参数控制 ==================
FSP_FILENAME = "Base_model.fsp"
pixel_size = 130e-9
si_layer_thickness = 220e-9
air_hole_radius = 45e-9

lumapi_path = r'C:\Program Files\Lumerical\v241\api\python\lumapi.py'
spec = importlib.util.spec_from_file_location("lumapi", lumapi_path)
lumapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lumapi)

# 封装计算数据的函数
def calculate_data(fdtd):
    # 获取透射率数据（返回字典，需提取'T'字段）
    top_data = fdtd.getresult("top_output", "T")
    top_trans = top_data['T'].flatten()  # 提取T字段并展平

    bottom_data = fdtd.getresult("bottom_output", "T")
    bottom_trans = bottom_data['T'].flatten()
    print(top_trans)
    print(bottom_trans)


# 批量创建空气孔的函数
def create_airholes_batch(fdtd, structure_matrix):
    script_lines = []
    script_lines.append("addstructuregroup;")
    script_lines.append("set('name', 'air_holes_group');")
    for i in range(20):
        for j in range(20):
            if structure_matrix[i, j] == 0:
                script_lines.append(f"addcircle;")
                script_lines.append(f"set('name', 'air_hole_{i}_{j}');")
                script_lines.append(f"set('x', {float((i - 9.5) * pixel_size)});")
                script_lines.append(f"set('y', {float((j - 9.5) * pixel_size)});")
                script_lines.append(f"set('z', {float(si_layer_thickness/2)});")
                script_lines.append(f"set('z span', {float(si_layer_thickness)});")
                script_lines.append(f"set('radius', {float(air_hole_radius)});")
                script_lines.append(f"set('material', 'etch');")
                script_lines.append(f"select('air_hole_{i}_{j}');")
                script_lines.append(f"addtogroup('air_holes_group');")
    fdtd.eval('\n'.join(script_lines))
fdtd = lumapi.FDTD(hide=True, newproject=True)

for iteration in range(5):
    s1 = time.time()
    # 载入Base_model.fsp
    fdtd.load("Base_model.fsp")
    fdtd.switchtolayout()
    fdtd.select("air_holes_group")
    fdtd.delete()
    create_airholes_batch(fdtd, structure_matrix = np.random.randint(0, 2, size=(20, 20)))
    e1 = time.time()
    fdtd.run()
    calculate_data(fdtd)

    print(f"第 {iteration + 1} 次迭代耗时: {e1 - s1} 秒")
