# 分子 VQE 工作流

这一页把分子电子结构 VQE 的完整链路走一遍：分子几何 → 活性空间 → 哈密顿量 → UCCSD 拟设 →
能量优化，以及映射选择、执行模式、自适应算符池和天衍执行。

本页的化学部分需要 `chemistry` 变体（`pip install -e ".[chemistry]"`）。

## 端到端流程

链路共四步：

1. 用 [`MolecularDataEngine`](../../api/cn/chemistry.md#moleculardataengine) 做电子结构预处理；
2. 用 [`UCCSDFactory`](../../api/cn/vqe.md#uccsdfactory) 构造拟设；
3. 选一个[能量估计器](../../api/cn/vqe.md)；
4. 用 [`VQESolver`](../../api/cn/vqe.md#vqesolver) 跑优化。

```python
from cqlib_vqe import (
    DirectStatevectorEstimator,
    MolecularDataEngine,
    UCCSDFactory,
    VQESolver,
)

molecule = MolecularDataEngine(
    geometry=[
        ('H', (0.0, 0.0, 0.0)),
        ('H', (0.0, 0.0, 0.735)),
    ],
    basis='sto-3g',
    multiplicity=1,
    charge=0,
    mapper_type='jw',
    excitation_threshold=1e-3,
).run()

factory = UCCSDFactory(
    molecule,
    construction_mode='jit',
    trotter_steps=1,
    trotter_order=2,
)
estimator = DirectStatevectorEstimator(n_qubits=molecule.n_qubits)
solver = VQESolver(
    factory,
    estimator,
    optimizer_method='COBYLA',
    max_iter=100,
    tol=1e-7,
    execution_mode='auto',
)


def progress(_parameters, energy, evaluation):
    if evaluation == 1 or evaluation % 10 == 0:
        print(f'eval={evaluation:4d}  energy={energy:.12f} Ha')


result = solver.run(molecule.hamiltonian_data, callback=progress)
print('VQE energy:', result['optimal_value'])
print('reference energies:', molecule.reference_energies)
```

`MolecularDataEngine(...).run()` 返回引擎自身，因此可以链式调用。`run()` 之后引擎暴露
`n_qubits`、`n_electrons`、`hamiltonian_data`、`reference_energies` 等属性，完整清单见
[`MolecularDataEngine`](../../api/cn/chemistry.md#moleculardataengine)。

维护中的 H2 示例：

```bash
python examples/h2_vqe_cqlib2.py
```

## 选择映射

`mapper_type` 可选 `"jw"`（Jordan--Wigner）、`"bk"`（Bravyi--Kitaev）或 `"parity"`：

```python
molecule = MolecularDataEngine(
    geometry=[('H', (0.0, 0.0, 0.0)), ('H', (0.0, 0.0, 0.735))],
    basis='sto-3g',
    mapper_type='bk',
).run()
```

所选映射会被**一致地**施加到三处：分子哈密顿量、UCCSD 激发生成元、以及 Hartree--Fock 参考态。

> BK 与 parity 映射下，参考态的比特图样一般不能只用 Hamming 重量刻画。**不要用 JW 的占据捷径
> 去替换工厂的参考态构造。**

## 活性空间

大体系要先设定活性空间策略。比特预算必须为正且为偶数。

```python
from cqlib_vqe import ActiveSpaceConfig, MolecularDataEngine

active_space = ActiveSpaceConfig.automatic(
    max_active_qubits=10,
    freeze_core=True,
    min_virtual_orbitals=1,
)
molecule = MolecularDataEngine(
    geometry=[('Li', (0.0, 0.0, 0.0)), ('H', (0.0, 0.0, 1.596))],
    basis='sto-3g',
    mapper_type='jw',
    active_space=active_space,
).run()

print(molecule.active_space_report)
```

用 `ActiveSpaceConfig.full()` 保留全部轨道空间。

> **活性空间报告应当与每个数值结果一起记录**，因为它固定了所模拟的哈密顿量和参数池。
> 报告字段见 [`ActiveSpaceReport`](../../api/cn/chemistry.md#activespacereport)。

## 执行模式与构造模式

### execution_mode

| 取值 | 何时用 |
| --- | --- |
| `"auto"` | **推荐的本地默认。** 优先使用可用的原生 Pauli 直出态矢量路径，包括 `construction_mode="bind"` 的工厂；回退顺序见下文 |
| `"circuit"` | 需要面向线路的估计器时，例如云端估计器 |
| `"direct_statevector"` | 仅当 `factory.build_statevector(...)` 与 `estimator.evaluate_parameters(...)` 都可用时 |

### construction_mode

| 取值 | 行为 |
| --- | --- |
| `"jit"` | 为重复求值构建数值线路 |
| `"bind"` | 保留符号模板。当目标执行路径从参数绑定中获益时使用 |

`execution_mode="auto"` 先检查原生 Pauli 直出态矢量路径：
`factory.native_pauli_rotation_available` 为真，且 `factory.build_statevector(...)` 与
`estimator.evaluate_parameters(...)` 都可用时，选择 `"direct_statevector"`，即使工厂设置了
`construction_mode="bind"`。

若上述条件不满足，`"bind"` 工厂走线路执行，经 cqlib2 的 `assign_parameters` 绑定参数；
其他工厂在上述两个方法都可用时仍选择 `"direct_statevector"`，否则走线路执行。
要明确使用参数绑定线路，应设置 `execution_mode="circuit"`。

## 自适应 selected-UCCSD

自适应求解器从规范 CCSD 振幅初始化拟设，然后扫描**完整的**剩余规范算符池，按实测能量梯度对
候选排序。

**初始 CCSD 振幅为零的候选不会被移除**，它们仍然参与排序——这是与「按 CCSD 振幅预筛选算符」
的做法最关键的区别。

```python
from cqlib_vqe import AdaptiveSelectedUCCSDSolver, AdaptiveSelectionConfig

config = AdaptiveSelectionConfig(
    pool_rounds=3,
    gradient_threshold=1e-4,
    target_energy_error=1.6e-3,
)
solver = AdaptiveSelectedUCCSDSolver(molecule, estimator, config)
result = solver.run(reference_energy=molecule.reference_energies['fci'])

print(result.optimal_value, result.stop_reason, result.precision_certified)
```

返回的 [`AdaptiveSelectedUCCSDResult`](../../api/cn/vqe.md#adaptiveselecteduccsdresult) 含每一轮的记录
（`rounds`）、最终选中的算符集合（`selected_packed_indices`）、停止原因（`stop_reason`）以及是否
达到目标精度（`precision_certified`）。

多分子端到端运行器：

```bash
python examples/run_five_adaptive_full_pool.py h2 \
  --output-dir run_outputs/h2_adaptive \
  --pool-rounds 2 \
  --maxiter 80
```

输出目录含每个分子的日志与 JSON 记录，以及 CSV 和 JSON 汇总。运行器接受 `h2`、`h4`、`lih`、`beh2`、
`h2o`；省略分子参数则全部运行。只有确实需要完整轨道空间且资源充足时，才使用
`--active-space-policy full`。

## 天衍执行

> 天衍会提交**真实的测量任务并消耗平台额度**。凭据配置在版本控制之外。

先确认接口可用与后端名：

```bash
export TIANYAN_API_KEY='YOUR_API_KEY'
python tools/check_tianyan_api.py --online
```

再选择后端与物理比特映射。映射从逻辑比特排到物理比特，长度必须恰好等于 `n_qubits`：

```bash
export TIANYAN_DEVICE='BACKEND_NAME'
export TIANYAN_PHYSICAL_QUBITS='0,1,2,3'
export TIANYAN_SHOTS=2000
export TIANYAN_MAXITER=10
export TIANYAN_CALIBRATION=disabled
python -u examples/h2_vqe_tianyan.py
```

[`TianyanEnergyEstimator`](../../api/cn/vqe.md#tianyanenergyestimator) 提交前按 qubit-wise commuting 关系分组
Pauli 项，返回时校验任务顺序、测量比特头与计数载荷。

> 该估计器**不推断路由，也不会静默修补后端元数据**。

**不要提交 API 密钥、凭据文件，或含账户信息的云端原始输出。**

## 常用入口

| 任务 | 命令 |
| --- | --- |
| 最小预编译 VQE | `python examples/minimal_compiled_smoke.py` |
| 本地 H2 UCCSD-VQE | `python examples/h2_vqe_cqlib2.py` |
| 自适应 H2 | `python examples/run_five_adaptive_full_pool.py h2` |
| 天衍接口自检 | `python tools/check_tianyan_api.py --online` |
| 完整测试套件 | `pytest -q` |
