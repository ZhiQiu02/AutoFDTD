import matplotlib.pyplot as plt
import importlib
import os
import numpy as np

# ================== 全局参数控制 ==================
LOAD_EXISTING_FSP = False
NEW_MATRIX = False
FSP_FILENAME = "power_splitter_corrected.fsp"
# CSV_FILE_PATH = 'F:\PythonProjects\c-DNN\designed_structure.csv'  # 验证dnn出来的结构矩阵
CSV_FILE_PATH = 'F:\PythonProjects\c-DNN\data\ceshi\matrix_5000.csv'
pixel_size = 130e-9
design_region_size = 2.6e-6
substrate_height = 2e-6
si_layer_thickness = 220e-9
cladding_height = 1e-6
air_hole_radius = 45e-9

# 输入/输出波导参数
waveguide_width = 0.5e-6
output_spacing = 1.5e-6
waveguide_length = 3e-6


# 检查CSV文件是否存在并加载
if os.path.exists(CSV_FILE_PATH):
    structure_matrix = np.loadtxt(CSV_FILE_PATH, delimiter=',')
    print("√ 已从CSV文件加载结构矩阵")
else:
    raise FileNotFoundError(f"× 无法找到指定的CSV文件: {CSV_FILE_PATH}")


def calculate_data(fdtd):
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

#
# # 结构矩阵生成
# MATRIX_FILE = 'structure_matrix.npy'
# if not NEW_MATRIX and os.path.exists(MATRIX_FILE):
#     structure_matrix = np.load(MATRIX_FILE)
#     print("已加载保存的20×20结构矩阵")
# else:
#     # np.random.seed(42)
#     structure_matrix = np.random.randint(0, 2, size=(20, 20))
#     np.save(MATRIX_FILE, structure_matrix)
#     print("生成的新20×20结构矩阵已保存")

# ====== API连接部分 ======
lumapi_path = r'C:\Program Files\Lumerical\v241\api\python\lumapi.py'
try:
    spec = importlib.util.spec_from_file_location("lumapi", lumapi_path)
    lumapi = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lumapi)

    if LOAD_EXISTING_FSP and os.path.exists(FSP_FILENAME):
        fdtd = lumapi.FDTD(filename=FSP_FILENAME, hide=False)
        print("√ 已加载已有fsp文件")
    else:
        fdtd = lumapi.FDTD(hide=False, newproject=True)
        print("√ 创建新工程，开始生成结构")
except Exception as e:
    print(f"× API连接失败: {str(e)}")
    exit()

# ================== 基底与包层 ==================
# 二氧化硅衬底设置
substrate = fdtd.addrect()
fdtd.set("name", "SiO2_substrate")
fdtd.set("x min", -5e-6)
fdtd.set("x max", 5e-6)
fdtd.set("y min", -1.9e-6)
fdtd.set("y max", 1.9e-6)
fdtd.set("z min", -1e-6)
fdtd.set("z max", 0)
fdtd.set("material", "SiO2 (Glass) - Palik")

# 硅层（设计区域和波导）
# 设计区域
design_region = fdtd.addrect()
fdtd.set("name", "Si_design_region")
fdtd.set("x", 0)
fdtd.set("y", 0)
fdtd.set("x span", design_region_size)
fdtd.set("y span", design_region_size)
fdtd.set("z", si_layer_thickness/2)
fdtd.set("z span", si_layer_thickness)
fdtd.set("material", "Si (Silicon) - Palik")

# 输入波导（嵌入硅层）
input_waveguide = fdtd.addrect()
fdtd.set("name", "input_waveguide")
fdtd.set("x span", waveguide_length)
fdtd.set("y span", waveguide_width)
fdtd.set("z", si_layer_thickness/2)
fdtd.set("z span", si_layer_thickness)
fdtd.set("x", -design_region_size/2 - waveguide_length/2)
fdtd.set("y", 0)
fdtd.set("material", "Si (Silicon) - Palik")

# 输出波导（上下两条）
for y_pos in [output_spacing/2, -output_spacing/2]:
    output = fdtd.addrect()
    fdtd.set("name", f"output_waveguide_{'top' if y_pos>0 else 'bottom'}")
    fdtd.set("x span", waveguide_length)
    fdtd.set("y span", waveguide_width)
    fdtd.set("z", si_layer_thickness/2)
    fdtd.set("z span", si_layer_thickness)
    fdtd.set("x", design_region_size/2 + waveguide_length/2)
    fdtd.set("y", y_pos)
    fdtd.set("material", "Si (Silicon) - Palik")

# ================== 空气孔阵列 ==================
fdtd.addstructuregroup()
fdtd.set("name", "air_holes_group")

for i in range(20):
    for j in range(20):
        if structure_matrix[i, j] == 0:
            air_hole = fdtd.addcircle()
            fdtd.set("name", f"air_hole_{i}_{j}")
            fdtd.set("x", (i - 9.5) * pixel_size)
            fdtd.set("y", (j - 9.5) * pixel_size)
            fdtd.set("z", si_layer_thickness/2)
            fdtd.set("z span", si_layer_thickness)
            fdtd.set("radius", air_hole_radius)
            fdtd.set("material", "etch")
            fdtd.select(f"air_hole_{i}_{j}")
            fdtd.addtogroup("air_holes_group")

# ================== 光源设置 ==================
source = fdtd.addmode()
fdtd.set("name", "input_source")
fdtd.set("injection axis", "x")
fdtd.set("x", -2e-6)
fdtd.set("y", 0)
fdtd.set("y span", waveguide_width*2)
fdtd.set("z", si_layer_thickness/2)
fdtd.set("z span", si_layer_thickness*2)
fdtd.set("center wavelength", 1550e-9)
fdtd.set("wavelength span", 100e-9)
fdtd.set("mode selection", "fundamental TE mode")

# ================== 功率监视器及其自定义Mesh ==================
for name, y_pos in [("top_output", output_spacing/2), ("bottom_output", -output_spacing/2)]:
    monitor = fdtd.addpower()
    fdtd.set("name", name)
    fdtd.set("monitor type", "2D X-normal")
    fdtd.set("x", 2.5e-6)
    fdtd.set("y", y_pos)
    fdtd.set("y span", waveguide_width*2)
    fdtd.set("z", si_layer_thickness/2)
    fdtd.set("z span", si_layer_thickness*2)
    fdtd.set("override global monitor settings", 1)
    fdtd.set("frequency points", 21)

    mesh = fdtd.addmesh()
    fdtd.set("name", name+"_mesh")
    fdtd.set("x", 2.5e-6)
    fdtd.set("x span", 4e-8)
    fdtd.set("y", y_pos)
    fdtd.set("y span", waveguide_width * 2)
    fdtd.set("z", si_layer_thickness / 2)
    fdtd.set("z span", si_layer_thickness * 2)
    # 只在 x 方向 override，并设置 dx = 0.02 μm
    fdtd.set("override x mesh", 1)
    fdtd.set("override y mesh", 0)
    fdtd.set("override z mesh", 0)
    fdtd.set("dx", 2e-8)

# ================== 仿真区域 ==================
fdtd_region = fdtd.addfdtd()
fdtd.set("dimension", "3D")
# 仅覆盖硅层和监视器区域
fdtd.set("x min", -design_region_size/2 - waveguide_length - 0.5e-6)
fdtd.set("x max", design_region_size/2 + waveguide_length + 0.5e-6)
fdtd.set("y min", -design_region_size/2 - 0.5e-6)
fdtd.set("y max", design_region_size/2 + 0.5e-6)
fdtd.set("z min", -0.1e-6)  # 略低于硅层
fdtd.set("z max", si_layer_thickness + 0.1e-6)  # 略高于硅层

# 边界条件
fdtd.set("x min bc", "PML")
fdtd.set("x max bc", "PML")
fdtd.set("y min bc", "PML")
fdtd.set("y max bc", "PML")
fdtd.set("z min bc", "PML")
fdtd.set("z max bc", "PML")

fdtd.save(FSP_FILENAME)

fdtd.run()

# 封装计算数据的函数

# 第一次运行仿真后计算数据
calculate_data(fdtd)

os.system("pause")

