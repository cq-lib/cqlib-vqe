# 使用指南

`cqlib-vqe` 是面向 cqlib 2.x 的分子电子结构 VQE 软件包。

## 安装

需要 Python 3.10 或更高版本。建议在独立环境中安装：

```bash
git clone https://github.com/cq-lib/cqlib-vqe.git
cd cqlib-vqe

python -m venv .venv
source .venv/bin/activate              # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

按需要选择安装变体：

```bash
# 只有预编译拟设的本地 VQE
python -m pip install -e .

# 加上分子哈密顿量与 UCCSD 预处理
python -m pip install -e ".[chemistry]"

# 再加上天衍执行
python -m pip install -e ".[chemistry,tianyan]"

# 开发与测试依赖
python -m pip install -e ".[chemistry,tianyan,test]"
```

| 变体 | 引入的依赖 | 解锁的能力 |
| --- | --- | --- |
| （基础） | `numpy`、`scipy`、`cqlib` | 预编译拟设的本地 VQE |
| `chemistry` | `openfermion`、`openfermionpyscf`、`pyscf` | [`MolecularDataEngine`](../../api/cn/chemistry.md#moleculardataengine) 分子预处理 |
| `tianyan` | `cqlib-tianyan` | [`TianyanEnergyEstimator`](../../api/cn/vqe.md#tianyanenergyestimator) 云端执行 |
| `test` | `pytest` | 测试套件 |

安装后跑一遍测试套件：

```bash
pytest -q
```

## 包结构

| 子包 | 职责 |
| --- | --- |
| [`cqlib_vqe.chemistry`](../../api/cn/chemistry.md) | 分子预处理、映射、活性空间、规范单重态 UCCSD 生成元 |
| [`cqlib_vqe.vqe`](../../api/cn/vqe.md) | 线路工厂、能量估计器、求解器、自适应选择、天衍执行 |
| [`cqlib_vqe.optim`](../../api/cn/optim.md) | 经典优化器（SciPy 之外的自带实现） |
| [`cqlib_vqe.utils`](../../api/cn/utils.md) | 阶段计时器 |

`chemistry` 与 `vqe` 的公开名字可以从顶层 `cqlib_vqe` 直接导入；`optim` 与 `utils` 需要从子包导入。

## 第一个 VQE

下面这个例子**不依赖任何化学库**，用一个预编译的一参数拟设验证整条链路：拟设 → 估计器 →
求解器。Hamiltonian 是 $H = Z$，生成元是 $G = i \cdot 0.5 \cdot Y$。

```python
from cqlib_vqe import DirectStatevectorEstimator, UCCSDFactory, VQESolver

factory = UCCSDFactory.from_compiled(
    n_qubits=1,
    n_electrons=0,
    generators=[[('Y', 0.5)]],
    initial_values=[0.1],
    construction_mode='jit',
)

estimator = DirectStatevectorEstimator(n_qubits=1)
solver = VQESolver(
    factory,
    estimator,
    optimizer_method='COBYLA',
    max_iter=30,
    execution_mode='auto',
)
result = solver.run([('Z', 1.0)])

print(result['optimal_value'])
print(result['optimal_params'])
```

实测输出：

```
optimal_value  ≈ -0.99999999909
optimal_params =  [3.14155]
execution_mode =  'direct_statevector'
success        =  False
```

**注意 `success=False` 不是错误。** 这个例子刻意把 COBYLA 限制在 30 次求值，所以它已经到达数值
极小值，却因为求值预算耗尽而报 `success=False`：

```
Return from COBYLA because the objective function has been evaluated MAXFUN times.
```

生产研究里应放大 `max_iter`，并设置适合该研究的能量或参数收敛判据。返回字典的完整字段见
[`VQESolver`](../../api/cn/vqe.md#vqesolver)。

可运行的版本在仓库里：

```bash
python examples/minimal_compiled_smoke.py
```

## 下一步

- [分子 VQE 工作流](workflow.md)：从分子几何到能量，含映射、活性空间、执行模式、自适应选择与天衍执行。
- [API 参考](../../api/cn/index.md)：按子包查阅全部公开接口。
