import torch
import torch.nn as nn
import torch.nn.functional as F

'''
论文流程：
输入图像 → [电]AWG生成电信号 → [光电]EOM调制为光信号 → [光]卷积计算 → [电]ADC转换 →  [电]非线性激活+池化 → [光电]全连接层 → [电]分类输出
'''
class OpticalCNN(nn.Module):
    def __init__(self, conv_weights, fc_weights):
        """
        - conv_weights: 光学卷积层的固定权重 [10, 1, 3, 3]
        - fc_weights: 全连接层权重分块列表 [28 blocks of (10, 72)]
        """
        super(OpticalCNN, self).__init__()
     
        # 第一阶段：光电输入编码（混合处理）
        # [电] AWG生成电信号 → [光电] EOM调制为光信号
        # 代码中直接输入光信号（张量模拟）
     
        # 第二阶段：光卷积计算（纯光处理）
        # [光] 微梳光源 + 光谱整形 + 色散光纤 + 探测器
        # 论文参数：10个3x3核，输入通道=1（灰度）
        self.optical_conv = nn.Conv2d(1, 10, kernel_size=3, stride=1, padding=0)
        self.optical_conv.weight.data = conv_weights
        self.optical_conv.weight.requires_grad = False  # 光处理不可训练
        self.optical_conv.bias = None  # 光芯片无偏置项
     
        # 第三阶段：电非线性激活与池化（纯电处理）
        # [电] ADC转换 + DSP处理
        self.electronic_relu = nn.ReLU()
        self.electronic_pool = nn.MaxPool2d(2, stride=2)
     
        # 第四阶段：光电全连接层（混合处理）
        # [光] 分块加权求和 → [电] 累加结果
        # 论文参数：1960维输入 → 分28块（72维/块）
        self.fc_weights_blocks = fc_weights  # List of [10, 72] tensors
        self.optical_fc_block_size = 72
     
        # 第五阶段：电分类输出（纯电处理）
        # [电] 光强最大值判断类别（等效Softmax）

    def forward(self, x):

        # 1. 输入光电编码（混合处理）
        # [光电] 输入图像已通过EOM调制为光信号（代码中用张量直接模拟）
        # [batch, 1, 30, 30]
     
        # 2. 光卷积计算（纯光处理）
        # [光] 波长编码权重 + 色散延迟
        x = self.optical_conv(x)  # [batch, 10, 28, 28]
     
        # 3. 电非线性激活与池化（纯电处理）
        # [电] ADC转换 + DSP处理
        x = self.electronic_relu(x)
        x = self.electronic_pool(x)  # [batch, 10, 14, 14]
        x = x.view(x.size(0), -1)  # [batch, 1960]
     
        # 4. 光电全连接层（混合处理）
        # [光] 分块光谱整形 → [电] 累加结果
        output = torch.zeros(x.size(0), 10).to(x.device)  # 初始化输出

        for i, block_weights in enumerate(self.fc_weights_blocks):
            # [光] 动态调整光谱整形器（模拟权重分块加载）
            start_idx = i * self.optical_fc_block_size
            end_idx = start_idx + self.optical_fc_block_size
            block_input = x[:, start_idx:end_idx]  # [batch, 72]

            # [光] 光加权求和（等效矩阵乘法）
            block_output = torch.mm(block_input, block_weights.t())  # [batch, 10]

            # [电] 电子累加部分和
            output += block_output
     
        # 5. 电分类输出（纯电处理）
        # [电] 光强最大值判断类别（等效LogSoftmax）
        return F.log_softmax(output, dim=1)


if __name__ == "__main__":
    batch_size = 1
    input_size = (30, 30)
    
    # 定义光学卷积核权重（固定不可训练）
    conv_weights = torch.randn(10, 1, 3, 3)  # [out_ch, in_ch, kH, kW]

    # 定义全连接层权重分块（28组 x [10, 72]）
    fc_weights_blocks = [torch.randn(10, 72) for _ in range(28)]  # 模拟光谱整形器分时加载

    # 模型初始化
    model = OpticalCNN(conv_weights=conv_weights, fc_weights=fc_weights_blocks)

    # 输入数据模拟（直接传入光信号张量）
    dummy_input = torch.randn(batch_size, 1, *input_size)  # [batch, C, H, W]

    # 前向传播测试
    output = model(dummy_input)
    print("输出尺寸:", output.shape)  # 预期输出: [batch, 10]