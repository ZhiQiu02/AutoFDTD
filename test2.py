import importlib
import os
import time
import numpy as np
import pandas as pd
import csv

# ================== 全局参数控制 ==================
FSP_FILENAME = "Base_model.fsp"
pixel_size = 130e-9
si_layer_thickness = 220e-9
air_hole_radius = 45e-9

# 数据集保存参数
SAVE_INTERVAL = 100  # 每100次迭代保存一次数据
DATA_DIR = "dataset"  # 数据集保存目录
os.makedirs(DATA_DIR, exist_ok=True)  # 创建数据集目录

# 初始化数据集
structures = []
transmissions = []

lumapi_path = r'C:\Program Files\Lumerical\v241\api\python\lumapi.py'
spec = importlib.util.spec_from_file_location("lumapi", lumapi_path)
lumapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lumapi)


# 封装计算数据的函数
def calculate_data(fdtd):
    try:
        # 获取透射率数据（返回字典，需提取'T'字段）
        top_data = fdtd.getresult("top_output", "T")
        top_trans = top_data['T'].flatten()  # 提取T字段并展平

        bottom_data = fdtd.getresult("bottom_output", "T")
        bottom_trans = bottom_data['T'].flatten()

        # print("Top transmission:", top_trans)
        # print("Bottom transmission:", bottom_trans)

        return np.concatenate([top_trans, bottom_trans])  # 合并上下端口数据
    except Exception as e:
        print(f"Error in calculate_data: {str(e)}")
        return None


# 批量创建空气孔的函数
def create_airholes_batch(fdtd, structure_matrix):
    try:
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
                    script_lines.append(f"set('z', {float(si_layer_thickness / 2)});")
                    script_lines.append(f"set('z span', {float(si_layer_thickness)});")
                    script_lines.append(f"set('radius', {float(air_hole_radius)});")
                    script_lines.append(f"set('material', 'etch');")
                    script_lines.append(f"select('air_hole_{i}_{j}');")
                    script_lines.append(f"addtogroup('air_holes_group');")
        fdtd.eval('\n'.join(script_lines))
        return True
    except Exception as e:
        print(f"Error in create_airholes_batch: {str(e)}")
        return False


# 保存数据集到CSV
def save_dataset(structures, transmissions, iteration):
    struct_path = os.path.join(DATA_DIR, f"structures_{iteration}.csv")
    trans_path = os.path.join(DATA_DIR, f"transmissions_{iteration}.csv")

    # 保存结构数据
    with open(struct_path, 'w', newline='') as f:
        writer = csv.writer(f)
        for struct in structures:
            # 展平为1D数组
            writer.writerow(struct.flatten())

    # 保存透射率数据
    with open(trans_path, 'w', newline='') as f:
        writer = csv.writer(f)
        for trans in transmissions:
            writer.writerow(trans)

    print(f"Saved {len(structures)} samples to {struct_path} and {trans_path}")

    # 清空临时存储
    structures.clear()
    transmissions.clear()


# 主程序
fdtd = lumapi.FDTD(hide=True, newproject=True)

try:
    for iteration in range(5):  # 实际使用应改为更大的值，如150000
        s1 = time.time()
        try:
            # 载入Base_model.fsp
            fdtd.load("Base_model.fsp")
            fdtd.switchtolayout()

            # 删除已有的空气孔组
            fdtd.select("air_holes_group")
            fdtd.delete()

            # 创建随机结构
            structure_matrix = np.random.randint(0, 2, size=(20, 20))

            # 创建空气孔
            if not create_airholes_batch(fdtd, structure_matrix):
                continue

            e1 = time.time()

            # 运行仿真
            fdtd.run()

            # 获取数据
            trans_data = calculate_data(fdtd)
            if trans_data is None:
                continue

            # 存储数据
            structures.append(structure_matrix)
            transmissions.append(trans_data)

            # 定期保存
            if (iteration + 1) % SAVE_INTERVAL == 0:
                save_dataset(structures, transmissions, iteration + 1)

            print(f"第 {iteration + 1} 次迭代耗时: {e1 - s1} 秒")
            if iteration % 1000 == 0:
                print(f"已完成 {iteration}/{150000} 次迭代")

        except Exception as e:
            print(f"第 {iteration + 1} 次迭代失败: {str(e)}")
            continue

finally:
    # 确保最后的数据被保存
    if structures and transmissions:
        save_dataset(structures, transmissions, "final")

    # 关闭FDTD
    fdtd.close()
    print("FDTD已关闭")



#没有判断，加了保存

'''Traceback (most recent call last):
  File "F:\PythonProjects\lum\test2.py", line 150, in <module>
    save_dataset(structures, transmissions, "final")
  File "F:\PythonProjects\lum\test2.py", line 80, in save_dataset
    with open(struct_path, 'w', newline='') as f:
PermissionError: [Errno 13] Permission denied: 'dataset\\structures_final.csv'
'''