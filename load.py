import csv
import sys
import numpy as np


def main():
    input_file = "dbs_dataset/structures_round_1_step_0_19.csv"  # 直接指定输入文件
    line_number = 21                     # 直接指定要提取的行号

    try:
        with open(input_file, 'r') as f:
            reader = csv.reader(f)
            lines = list(reader)

        if line_number < 1 or line_number > len(lines):
            print(f"错误: 行号超出范围 (1-{len(lines)})")
            sys.exit(1)

        # 获取指定行的数据
        flat_data = lines[line_number - 1]

        # 转换为浮点数数组
        try:
            data = [float(x) for x in flat_data]
        except ValueError as e:
            print(f"数据转换错误: {e}")
            sys.exit(1)

        # 检查数据长度是否为400
        if len(data) != 400:
            print(f"错误: 数据长度应为400，但实际为{len(data)}")
            sys.exit(1)

        # 重塑为20×20矩阵
        matrix = np.array(data).reshape(20, 20)

        # 保存为新的CSV文件
        output_file = "asd.csv"
        np.savetxt(output_file, matrix, delimiter=',')

        print(f"成功将第{line_number}行还原为20×20矩阵并保存到{output_file}")

    except FileNotFoundError:
        print(f"错误: 文件 '{input_file}' 不存在")
        sys.exit(1)
    except Exception as e:
        print(f"发生未知错误: {e}")
        sys.exit(1)


if __name__ == "__main__":

    main()