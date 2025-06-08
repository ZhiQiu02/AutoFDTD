import importlib
import os
from datetime import datetime
import numpy as np  # 需安装: pip install numpy


# ====== 保存FDTD项目文件（避免手动提示） ======
project_dir = r'/'  # 用户指定目录
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
save_dir = os.path.join(project_dir, f"fdtd_results_{timestamp}")
os.makedirs(save_dir, exist_ok=True)
fdtd.save(os.path.join(save_dir, "simulation.fsp"))  # 自动保存为.fsp项目文件
print(f"√ FDTD项目已保存至: {os.path.join(save_dir, 'simulation.fsp')}")
# ====== 运行仿真 ======
fdtd.run()
print("√ 仿真完成")
# ====== 保存监测器数据（功率） ======
monitor_data = fdtd.getresult('output_monitor', 'power')  # 获取功率数据
# 关键修复：判断数据类型（数组或字典）
if isinstance(monitor_data, np.ndarray):
    # 情况1：直接返回数组（2D截面监测器常见）
    np.save(os.path.join(save_dir, "output_power.npy"), monitor_data)
    print(f"√ 功率数据（数组）已保存至: {os.path.join(save_dir, 'output_power.npy')}")
elif isinstance(monitor_data, dict):
    # 情况2：返回字典（包含多个字段，如坐标+功率）
    if 'power' in monitor_data:
        power_array = monitor_data['power']
        np.save(os.path.join(save_dir, "output_power.npy"), power_array)
        print(f"√ 功率数据（字典提取）已保存至: {os.path.join(save_dir, 'output_power.npy')}")
    else:
        print(f"× 错误：监测器字典中未找到'power'字段，可用字段: {list(monitor_data.keys())}")
else:
    print(f"× 错误：监测器数据类型未知，类型为: {type(monitor_data)}")
# ====== 保存仿真参数（文本记录） ======
with open(os.path.join(save_dir, "simulation_params.txt"), 'w') as f:
    f.write("===== FDTD仿真参数记录 =====\n")
    f.write(f"仿真区域尺寸 (X,Y,Z): {10e-6}m, {10e-6}m, {2e-6}m\n")
    f.write(f"波导尺寸 (长,宽,厚): {8e-6}m, {0.5e-6}m, {0.22e-6}m\n")
    f.write(f"光源波长范围: {1.5e-6}m ~ {1.6e-6}m\n")
print(f"√ 仿真参数已保存至: {os.path.join(save_dir, 'simulation_params.txt')}")

