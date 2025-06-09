import importlib
import os
import numpy as np
import csv
import copy

# ================== 全局参数控制 ==================
FSP_FILENAME = "Base_model.fsp"
MAX_DBS_ROUNDS = 10  # 用户可修改的DBS运行轮数

# 数据集保存参数
SAVE_INTERVAL = 10
DATA_DIR = "dbs_dataset"  # 数据集保存目录
os.makedirs(DATA_DIR, exist_ok=True)  # 创建数据集目录

# 初始化数据集
structures = []
transmissions = []

# 加载Lumerical API
lumapi_path = r'C:\Program Files\Lumerical\v241\api\python\lumapi.py'
spec = importlib.util.spec_from_file_location("lumapi", lumapi_path)
lumapi = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lumapi)


# 封装计算数据的函数 - 修改为单频率点版本
def calculate_data(fdtd):
    try:
        # 获取透射率数据 - 单频率点版本
        top_data = fdtd.getresult("top_output", "T")
        top_trans = top_data['T']
        bottom_data = fdtd.getresult("bottom_output", "T")
        bottom_trans = bottom_data['T']
        print(f"Top trans: {top_trans}, Bottom trans: {bottom_trans}")
        return np.array([top_trans[0], bottom_trans[0]])  # 只取第一个频率点
    except Exception as e:
        print(f"Error in calculate_data: {str(e)}")
        return None


# 计算品质因数 (Figure of Merit) - 单频率点版本
def calculate_fom(trans_data):
    """
    计算品质因数 FOM = T1 + T2 - 0.5 * abs(T1 - T2)
    :param trans_data: 2维透射率数组 [T_top, T_bottom]
    :return: FOM值
    """
    T1 = trans_data[0]  # 上端口透射率
    T2 = trans_data[1]  # 下端口透射率
    return T1 + T2 - 0.5 * abs(T1 - T2)


# 验证透射率数据是否合理 - 单频率点版本
def is_valid_transmission(trans_data, max_total=1.05):
    if trans_data is None:
        return False
    total = trans_data[0] + trans_data[1]
    if total > max_total:
        return False
    if np.any(np.isnan(trans_data)) or np.any(np.isinf(trans_data)):
        return False
    if np.any(trans_data < 0) or np.any(trans_data > 1.0):
        return False
    return True


# 批量创建空气孔的函数 (修复)
def create_airholes_batch(fdtd, structure_matrix):
    script_lines = [
        "addstructuregroup;",
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

                # 一次性执行所有命令
    fdtd.eval('\n'.join(script_lines))

def modify_airhole(fdtd, i, j, state):
    """修改单个空气孔的状态 (0=空气孔, 1=硅)"""
    name = f'air_hole_{i}_{j}'
    #
    # # 首先尝试删除（如果存在）
    # fdtd.eval(f"select('{name}'); delete;")
    fdtd.switchtolayout()
    fdtd.select(name)
    fdtd.delete()
    # 如果需要创建空气孔
    if state == 0:
        script_lines = [
            f"addcircle;",
            f"set('name', '{name}');",
            f"set('x', {float((j - 9.5) * 130e-9)});",
            f"set('y', {float((9.5 - i) * 130e-9)});",
            f"set('z', {float(220e-9 / 2)});",
            f"set('z span', {float(220e-9)});",
            f"set('radius', {float(45e-9)});",
            f"set('material', 'etch');",
            f"select('{name}');",
            f"addtogroup('air_holes_group');"
        ]
        fdtd.eval('\n'.join(script_lines))


# 保存数据集到CSV (优化保存逻辑)
def save_dataset(structures, transmissions, iteration):
    struct_path = os.path.join(DATA_DIR, f"structures_{iteration}.csv")
    trans_path = os.path.join(DATA_DIR, f"transmissions_{iteration}.csv")

    # 确保目录存在
    os.makedirs(DATA_DIR, exist_ok=True)

    # 保存结构数据
    with open(struct_path, 'w', newline='') as f:
        writer = csv.writer(f)
        for struct in structures:
            writer.writerow(struct.flatten())

    # 保存透射率数据
    with open(trans_path, 'w', newline='') as f:
        writer = csv.writer(f)
        for trans in transmissions:
            writer.writerow(trans)

    print(f"Saved {len(structures)} samples to {struct_path} and {trans_path}")


# 错误恢复机制
def find_last_saved_iteration():
    existing_files = os.listdir(DATA_DIR)
    if not existing_files:
        return 0
    iter_numbers = []
    for f in existing_files:
        if f.startswith("structures_") and f.endswith(".csv"):
            try:
                parts = f.split('_')
                iter_num = int(parts[1].split('.')[0])
                iter_numbers.append(iter_num)
            except (ValueError, IndexError):
                continue
    return max(iter_numbers) if iter_numbers else 0


# 从CSV加载结构矩阵
def load_structure_from_csv(filepath):
    """从CSV文件加载结构矩阵"""
    if not os.path.exists(filepath):
        print(f"Warning: File {filepath} not found. Using random structure instead.")
        return np.random.randint(0, 2, size=(20, 20))

    structure = []
    with open(filepath, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            # 将字符串转换为整数
            structure.append([int(x) for x in row])

    # 确保矩阵是20x20
    if len(structure) != 20 or any(len(row) != 20 for row in structure):
        print(f"Warning: Invalid matrix size in {filepath}. Using random structure instead.")
        return np.random.randint(0, 2, size=(20, 20))

    return np.array(structure)


# ================== DBS优化主程序 ==================
def dbs_optimization(fdtd, max_rounds=MAX_DBS_ROUNDS, initial_structure=None):
    # 初始化结构
    if initial_structure is not None:
        current_structure = initial_structure
        print("Using custom initial structure")
    else:
        current_structure = np.random.randint(0, 2, size=(20, 20))
        print("Using random initial structure")

    # 创建初始结构
    fdtd.switchtolayout()
    fdtd.select("air_holes_group")
    fdtd.delete()
    create_airholes_batch(fdtd, current_structure)

    # 运行初始仿真
    fdtd.run()
    trans_data = calculate_data(fdtd)

    # 验证初始数据
    if not is_valid_transmission(trans_data):
        print("Initial structure has invalid transmission data. Regenerating...")
        return dbs_optimization(fdtd, max_rounds, np.random.randint(0, 2, size=(20, 20)))

    # 存储初始结构
    structures.append(current_structure.copy())
    transmissions.append(trans_data.copy())
    current_fom = calculate_fom(trans_data)
    print(f"Initial FOM: {current_fom:.4f}")

    # 使用集合跟踪已保存的结构（避免重复）
    saved_structures = set()

    # 计数器用于保存间隔
    sample_count = 0

    # DBS优化循环
    for round_idx in range(max_rounds):
        print(f"\n=== Starting DBS Round {round_idx + 1}/{max_rounds} ===")
        print(f"Current FOM: {current_fom:.4f}")

        # 遍历所有像素进行优化
        improved = False
        for i in range(20):
            for j in range(20):
                # 保存原始状态
                original_state = current_structure[i, j]
                original_fom = current_fom

                # 尝试翻转像素
                new_state = 1 - original_state
                current_structure[i, j] = new_state
                modify_airhole(fdtd, i, j, new_state)

                # 运行仿真
                try:
                    fdtd.run()
                    new_trans = calculate_data(fdtd)

                    if is_valid_transmission(new_trans):
                        new_fom = calculate_fom(new_trans)
                        print(f"  Flip at ({i},{j}) - Tentative FOM: {new_fom:.9f} (Original: {original_fom:.9f})")
                        # ===== 关键修改：总是保存新结构 =====
                        # 创建结构的哈希值用于比较
                        struct_hash = hash(tuple(current_structure.flatten()))

                        # 如果这是新结构且尚未保存
                        if struct_hash not in saved_structures:
                            structures.append(current_structure.copy())
                            transmissions.append(new_trans.copy())
                            saved_structures.add(struct_hash)
                            sample_count += 1

                            # 检查是否达到保存间隔
                            if sample_count >= SAVE_INTERVAL:
                                save_dataset(
                                    structures,
                                    transmissions,
                                    f"round_{round_idx + 1}_step_{i}_{j}"
                                )
                                sample_count = 0

                        # 如果FOM提高，接受改变
                        if new_fom > current_fom:
                            current_fom = new_fom
                            trans_data = new_trans
                            improved = True
                            print(f"  Accepted flip at ({i},{j}) - New FOM: {new_fom:.4f}")
                        else:
                            # 恢复原始状态（但已保存新结构）
                            current_structure[i, j] = original_state
                            modify_airhole(fdtd, i, j, original_state)
                            current_fom = original_fom
                    else:
                        # 恢复原始状态
                        current_structure[i, j] = original_state
                        modify_airhole(fdtd, i, j, original_state)
                        print(f"  Invalid transmission at ({i},{j}), reverting")

                except Exception as e:
                    print(f"  Error at ({i},{j}): {str(e)}")
                    current_structure[i, j] = original_state
                    modify_airhole(fdtd, i, j, original_state)

        # 每轮结束后保存剩余数据
        if structures:
            save_dataset(
                structures,
                transmissions,
                f"round_{round_idx + 1}_final"
            )
            sample_count = 0

        print(f"Completed Round {round_idx + 1} - Best FOM: {current_fom:.4f}")

        # 如果没有改进，提前结束
        if not improved:
            print(f"No improvement in round {round_idx + 1}, ending optimization early")
            break

    # 保存最终剩余数据
    if structures:
        save_dataset(structures, transmissions, "final")

    return current_structure, trans_data

# 主程序
if __name__ == "__main__":
    fdtd = lumapi.FDTD(hide=True, newproject=True)

    try:
        # 启用GPU加速
        # fdtd.eval("setresource('FDTD','GPU', true);")

        # 加载基础模型
        fdtd.load("Base_model.fsp")

        # 自定义初始结构选项
        INITIAL_STRUCTURE_FILE = "custom_structure.csv"  # 自定义结构文件路径
        initial_structure = None

        # 如果存在自定义结构文件，则加载
        if os.path.exists(INITIAL_STRUCTURE_FILE):
            initial_structure = load_structure_from_csv(INITIAL_STRUCTURE_FILE)
            print(f"Loaded custom structure from {INITIAL_STRUCTURE_FILE}")

        # 运行DBS优化
        best_structure, best_trans = dbs_optimization(fdtd, MAX_DBS_ROUNDS, initial_structure)

        # 保存最终结果
        np.savetxt(os.path.join(DATA_DIR, "best_structure.csv"), best_structure, delimiter=",")
        np.savetxt(os.path.join(DATA_DIR, "best_transmission.csv"), best_trans, delimiter=",")
        print(f"\nOptimization completed. Best structure and transmission saved.")

        # 保存剩余数据
        if structures and transmissions:
            save_dataset(structures, transmissions, "final")

    except Exception as e:
        print(f"Main process error: {str(e)}")
        import traceback

        traceback.print_exc()
    finally:
        fdtd.close()
        print("FDTD session closed")