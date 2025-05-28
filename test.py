import numpy as np
loss_power = (0.19 + 0.64)
loss_dB = -10 * np.log10(loss_power)
avg_loss_dB = np.mean(loss_dB)

print(f"平均损失分贝: {avg_loss_dB:.2f} dB")