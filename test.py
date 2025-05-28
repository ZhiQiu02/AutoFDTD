import importlib
import os
import time
import numpy as np

# ================== 全局参数控制 ==================
NEW_MATRIX = True
FSP_FILENAME = "Base_model.fsp"
pixel_size = 130e-9
si_layer_thickness = 220e-9
air_hole_radius = 45e-9

# 输入/输出波导参数
waveguide_width = 0.5e-6
output_spacing = 1.5e-6
waveguide_length = 3e-6

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


def create_airholes_batch(fdtd, structure_matrix):
    # 创建临时脚本文件
    script_path = "create_airholes.lsf"

    # 构建Lumerical脚本内容
    script_content = f"""
    // 批量创建空气孔脚本
    mat = {str(structure_matrix.tolist()).replace("],", "];")};
    for(i=0; i<20; i++) {{
        for(j=0; j<20; j++) {{
            if(mat[i][j] == 0) {{
                addcircle;
                set("name", "air_hole_" + num2str(i) + "_" + num2str(j));
                set("x", (i-9.5)*{pixel_size});
                set("y", (j-9.5)*{pixel_size});
                set("z", {si_layer_thickness / 2});
                set("z span", {si_layer_thickness});
                set("radius", {air_hole_radius});
                set("material", "etch");
                addtogroup("air_holes_group");
            }}
        }}
    }}
    """

    # 保存脚本文件
    with open(script_path, "w") as f:
        f.write(script_content)

    # 执行脚本文件
    try:
        fdtd.eval(f"run('{script_path}');")
    except lumapi.LumApiError as e:
        print(f"执行错误: {str(e)}")
        with open(script_path, "r") as f:
            print("脚本内容:", f.read())

    # 删除临时文件
    os.remove(script_path)
fdtd = lumapi.FDTD(hide=False, newproject=True)

num_iterations = 2
for iteration in range(num_iterations):
    print(f"\n===== 第 {iteration + 1} 次迭代 =====")

    # 载入基础模型
    fdtd.load("Base_model.fsp")
    fdtd.switchtolayout()

    # 删除旧空气孔组并创建新组
    fdtd.select("air_holes_group")
    fdtd.delete()
    fdtd.addstructuregroup()
    fdtd.set("name", "air_holes_group")

    # 生成随机矩阵
    structure_matrix = np.random.randint(0, 2, size=(20, 20))

    # 批量创建空气孔 (关键优化)
    start = time.time()
    create_airholes_batch(fdtd, structure_matrix)
    print(f"批量创建耗时: {time.time() - start:.4f}秒")

    # 运行仿真和数据处理
    fdtd.run()
    calculate_data(fdtd)

