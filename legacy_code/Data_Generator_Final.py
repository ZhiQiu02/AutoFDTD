import importlib
import os
import time
import numpy as np
import csv

# ================== 全局参数控制 ==================
FSP_FILENAME = "../Base_model.fsp"


# 数据集保存参数
SAVE_INTERVAL = 500  # 每100次迭代保存一次数据
DATA_DIR = "../dataset"  # 数据集保存目录
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
        return np.concatenate([top_trans, bottom_trans])  # 合并上下端口数据
    except Exception as e:
        print(f"Error in calculate_data: {str(e)}")
        return None


# 验证透射率数据是否合理
def is_valid_transmission(trans_data, max_total=1):

    """
    验证透射率数据是否合理
    :param trans_data: 42维透射率数组（前21个是上端口，后21个是下端口）
    :param max_total: 允许的最大总透射率（考虑仿真误差）
    :return: 是否有效
    """
    if trans_data is None:
        return False
    # 分离上下端口数据
    top_trans = trans_data[:21]
    bottom_trans = trans_data[21:]
    # 检查每个波长点的总透射率
    for i in range(21):
        total = top_trans[i] + bottom_trans[i]
        if total > max_total:  # 总透射率不应超过1（考虑仿真误差）
            return False

    # 检查是否存在异常值（NaN或无穷大）
    if np.any(np.isnan(trans_data)) or np.any(np.isinf(trans_data)):
        return False
    # 检查所有值是否在合理范围内
    if np.any(trans_data < 0) or np.any(trans_data > 1.0):
        return False
    return True


# 批量创建空气孔的函数
def create_airholes_batch(fdtd, structure_matrix):
    try:
        script_lines = [
            "addstructuregroup;",  # 分号单独一行更清晰
            "set('name', 'air_holes_group');",
        ]
        for i in range(20):
            for j in range(20):
                if structure_matrix[i, j] == 0:
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

# 错误恢复机制：查找最后保存的迭代点
def find_last_saved_iteration():
    existing_files = os.listdir(DATA_DIR)
    if not existing_files:
        return 0

    iter_numbers = []
    for f in existing_files:
        if f.startswith("structures_") and f.endswith(".csv"):
            try:
                # 提取文件名中的迭代编号
                parts = f.split('_')
                iter_num = int(parts[1].split('.')[0])
                iter_numbers.append(iter_num)
            except (ValueError, IndexError):
                continue
    if iter_numbers:
        return max(iter_numbers)
    return 0


# 主程序
fdtd = lumapi.FDTD(hide=True, newproject=True)

try:
    # 确定起始迭代点
    start_iter = find_last_saved_iteration()
    print(f"Resuming from iteration {start_iter}")

    # 统计变量
    total_iterations = 50000  # 总迭代次数
    valid_count = 0
    invalid_count = 0

    # 从start_iter开始运行
    for iteration in range(start_iter, total_iterations):

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
            s = time.time()
            if not create_airholes_batch(fdtd, structure_matrix):
                invalid_count += 1
                continue
            # 运行仿真
            e = time.time()
            print(f"第{iteration}次迭代耗时: {e - s} 秒")
            s1 = time.time()
            fdtd.run()
            e1 = time.time()
            print(f"第 {iteration + 1} 次仿真耗时: {e1 - s1} 秒")
            # 获取数据
            trans_data = calculate_data(fdtd)

            # 验证数据
            if is_valid_transmission(trans_data):
                # 存储有效数据
                structures.append(structure_matrix)
                transmissions.append(trans_data)
                valid_count += 1
            else:
                print(f"Invalid data detected at iteration {iteration}, skipping")
                invalid_count += 1
                continue

            # 定期保存
            if (iteration + 1) % SAVE_INTERVAL == 0:
                save_dataset(structures, transmissions, iteration + 1)
            # 定期报告进度

        except Exception as e:
            print(f"Error at iteration {iteration}: {str(e)}")
            invalid_count += 1
            # 尝试恢复FDTD会话
            try:
                fdtd.close()
                fdtd = lumapi.FDTD(hide=True, newproject=True)
            except:
                pass
            continue

finally:
    # 确保最后的数据被保存
    if structures and transmissions:
        save_dataset(structures, transmissions, "final")

    # 关闭FDTD
    fdtd.close()
    print(f"Completed. Total: {total_iterations}, Valid: {valid_count}, Invalid: {invalid_count}")
    print("FDTD已关闭")