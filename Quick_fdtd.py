import importlib
import os
import numpy as np

# CSV_FILE_PATH = 'F:\PythonProjects\c-DNN\designed_structure.csv'  # 验证dnn出来的结构矩阵
# CSV_FILE_PATH = 'F:\PythonProjects\c-DNN\data\ceshi\matrix_5000.csv'
CSV_FILE_PATH = 'asd.csv'

structure_matrix = np.loadtxt(CSV_FILE_PATH, delimiter=',')
'''
def calculate_data(fdtd):
    #21数据版本
    # 获取透射率数据（返回字典，需提取'T'字段）
    top_data = fdtd.getresult("top_output", "T")
    top_trans = top_data['T'].flatten()  # 提取T字段并展平

    bottom_data = fdtd.getresult("bottom_output", "T")
    bottom_trans = bottom_data['T'].flatten()

    # 获取波长数据
    monitor_freq = fdtd.getdata("top_output", "f").flatten()  # 频率数组（Hz，形状(21,)）
    wavelengths = 3e8 / monitor_freq  # 频率转波长（米）
    wavelengths_nm = wavelengths * 1e9  # 转换为纳米（单位：nm）

    # 计算平均功率比
    avg_top = np.mean(top_trans)
    avg_bottom = np.mean(bottom_trans)
    avg_ratio = avg_top / avg_bottom

    # 计算损失功率和损失分贝
    loss_dB = -10 * np.log10(top_trans + bottom_trans)
    avg_loss_dB = np.mean(loss_dB)

    print(f"\n===== 关键指标 =====")
    print(f"平均上分光率: {avg_top:.4f} ({avg_top*100:.1f}%)")
    print(f"平均下分光率: {avg_bottom:.4f} ({avg_bottom*100:.1f}%)")
    print(f"功率比（上/下）: {avg_ratio:.2f}:1")
    print(f"平均损失分贝: {avg_loss_dB:.2f} dB")

    return top_trans, bottom_trans, wavelengths_nm, avg_top, avg_bottom, avg_ratio, avg_loss_dB
'''
def calculate_data(fdtd):
    try:
        # 获取透射率数据（返回字典，需提取'T'字段）
        top_data = fdtd.getresult("top_output", "T")
        top_trans = top_data['T'].flatten()  # 提取T字段并展平

        bottom_data = fdtd.getresult("bottom_output", "T")
        bottom_trans = bottom_data['T'].flatten()
        return np.concatenate([top_trans, bottom_trans])  # 合并上下端口数据
    except Exception as e:
        print(f"Error in calculate_data: {str(e)}")
        return None

def create_airholes_batch(fdtd, structure_matrix):
    script_lines = [
        "addstructuregroup;",  # 分号单独一行更清晰
        "set('name', 'air_holes_group');",
    ]
    # 关键修改：调整矩阵索引到FDTD坐标的映射
    for i in range(20):  # 行（对应FDTD的y坐标）
        for j in range(20):  # 列（对应FDTD的x坐标）
            if structure_matrix[i, j] == 0:  # 矩阵中0表示空气孔
                script_lines.append(f"addcircle;")
                script_lines.append(f"set('name', 'air_hole_{i}_{j}');")
                script_lines.append(f"set('x', {float((j - 9.5) * 130e-9)});")
                script_lines.append(f"set('y', {float((9.5 - i) * 130e-9)});")
                script_lines.append(f"set('z', {float(220e-9 / 2)});")
                script_lines.append(f"set('z span', {float(220e-9)});")
                script_lines.append(f"set('radius', {float(45e-9)});")
                script_lines.append(f"set('material', 'etch');")
                script_lines.append(f"select('air_hole_{i}_{j}');")
                script_lines.append(f"addtogroup('air_holes_group');")

    fdtd.eval('\n'.join(script_lines))

# API连接
lumapi_path = r'C:\Program Files\Lumerical\v241\api\python\lumapi.py'
spec = importlib.util.spec_from_file_location("lumapi", lumapi_path)
lumapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lumapi)

fdtd = lumapi.FDTD(hide=False, newproject=True)
fdtd.load("Base_model.fsp")
fdtd.switchtolayout()

fdtd.select("air_holes_group")
fdtd.delete()

create_airholes_batch(fdtd, structure_matrix)

fdtd.run()

calculate_data(fdtd)

os.system("pause")
