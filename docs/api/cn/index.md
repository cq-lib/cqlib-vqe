# API 参考

`cqlib-vqe` 的公开接口分为四个子包。

## 导入约定

顶层包重导出了 `chemistry` 与 `vqe` 两个子包的公开名字：

```python
from cqlib_vqe import MolecularDataEngine, UCCSDFactory, VQESolver
```

`optim` 与 `utils` **不在**顶层重导出，需要从子包导入：

```python
from cqlib_vqe.optim import AdamOptimizer
from cqlib_vqe.utils import PerformanceTracker
```

## 子包一览

| 子包 | 公开名字数 | 职责 | 页面 |
| --- | --- | --- | --- |
| `cqlib_vqe.chemistry` | 14 | 分子预处理、映射、活性空间、规范单重态 UCCSD 生成元与振幅 | [chemistry](chemistry.md) |
| `cqlib_vqe.vqe` | 22 | 线路工厂、能量估计器、求解器、自适应选择、天衍执行 | [vqe](vqe.md) |
| `cqlib_vqe.optim` | 8 | 经典优化器与自定义优化器基类 | [optim](optim.md) |
| `cqlib_vqe.utils` | 2 | 阶段计时器 | [utils](utils.md) |

## 按任务查找

| 要做的事 | 入口 |
| --- | --- |
| 从分子几何构造哈密顿量 | [`MolecularDataEngine`](chemistry.md#moleculardataengine) |
| 选择活性空间 | [`ActiveSpaceConfig`](chemistry.md#activespaceconfig) / [`select_active_space`](chemistry.md) |
| 构造 UCCSD 线路或态矢量 | [`UCCSDFactory`](vqe.md#uccsdfactory) |
| 本地精确求期望值 | [`NativeStatevectorEstimator`](vqe.md#nativestatevectorestimator) / [`DirectStatevectorEstimator`](vqe.md#directstatevectorestimator) |
| 跑一次 VQE | [`VQESolver`](vqe.md#vqesolver) |
| 自适应增长算符池 | [`AdaptiveSelectedUCCSDSolver`](vqe.md#adaptiveselecteduccsdsolver) |
| 提交到天衍平台 | [`TianyanEnergyEstimator`](vqe.md#tianyanenergyestimator) |
| 换经典优化器 | [`cqlib_vqe.optim`](optim.md) |

## 约定

- **比特序**：Pauli 串使用 `q0-left` 顺序，即最左字符作用于 qubit 0。这一点在 [工作流](../../guide/cn/workflow.md) 中有说明。
- **返回类型**：多数结果对象是 `dataclass`（如 `AdaptiveRound`、`TianyanEnergyResult`），字段为只读命名属性；`VQESolver.run` 例外，返回 `dict`。
- **可选依赖**：需要 OpenFermion 或 PySCF 的入口在缺少依赖时抛 `ImportError`；天衍相关入口需要 `cqlib-tianyan`。
