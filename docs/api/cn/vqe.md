# cqlib_vqe.vqe

`cqlib_vqe.vqe` 覆盖 VQE 的执行侧：线路工厂、能量估计器、经典优化循环、自适应算符池
增长，以及天衍平台的测量提交。

本地估计器只依赖 cqlib 2.x；天衍相关入口需要 `cqlib-tianyan`（安装 `cqlib-vqe[tianyan]`）。

## 总览

| 名字 | 类型 | 简介 |
| --- | --- | --- |
| [`VQESolver`](#vqesolver) | 类 | 协调工厂、估计器与经典优化器 |
| [`UCCSDFactory`](#uccsdfactory) | 类 | 自旋适配的 selected-UCCSD 工厂 |
| [`UCCSD_Factory`](#uccsd-factory) | 类 | `UCCSDFactory` 的别名（同一个对象） |
| [`NativeStatevectorEstimator`](#nativestatevectorestimator) | 类 | 基于 cqlib2 QIS API 的精确本地估计器 |
| [`DirectStatevectorEstimator`](#directstatevectorestimator) | 类 | 工厂直出态矢量的融合路径 |
| [`FastStatevectorEstimator`](#faststatevectorestimator) | 类 | 向后兼容名 |
| [`EnergyEstimator`](#energyestimator) | 类 | 采样式估计器 |
| [`ParallelEnergyEstimator`](#parallelenergyestimator) | 类 | 并行 QWC 采样 |
| [`CloudEnergyEstimator`](#cloudenergyestimator) | 类 | cqlib 2.0 之前的云端 API 兼容名 |
| [`AdaptiveSelectedUCCSDSolver`](#adaptiveselecteduccsdsolver) | 类 | 全池扫描的自适应求解器 |
| [`AdaptiveSelectionConfig`](#adaptiveselectionconfig) | 类 | 自适应选择配置 |
| [`CandidateGradient`](#candidategradient) | 类 | 单个候选算符的梯度测量结果 |
| [`AdaptiveRound`](#adaptiveround) | 类 | 一轮优化的状态 |
| [`AdaptiveSelectedUCCSDResult`](#adaptiveselecteduccsdresult) | 类 | 自适应求解的完整结果 |
| [`TianyanEnergyEstimator`](#tianyanenergyestimator) | 类 | QWC 分组的天衍能量估计器 |
| [`TianyanCloudEnergyEstimator`](#tianyancloudenergyestimator) | 类 | `TianyanEnergyEstimator` 的别名（同一个对象） |
| [`TianyanMeasurementPlan`](#tianyanmeasurementplan) | 类 | 一次能量求值的完整硬件线路 |
| [`TianyanMeasurementGroup`](#tianyanmeasurementgroup) | 类 | 一个 QWC 分组及其测量元数据 |
| [`TianyanSubmittedEvaluation`](#tianyansubmittedevaluation) | 类 | 已提交的计划与任务句柄 |
| [`TianyanEnergyResult`](#tianyanenergyresult) | 类 | 天衍求值的详细结果 |
| [`TianyanGroupResult`](#tianyangroupresult) | 类 | 单个 QWC 分组的测量结果 |
| [`TianyanTermResult`](#tianyantermresult) | 类 | 单个 Pauli 项的贡献 |

---

## 求解

### VQESolver

```python
VQESolver(
    factory,
    estimator,
    optimizer_method: str | object = "COBYLA",
    max_iter: int = 50,
    *,
    tol: float = 1e-06,
    execution_mode: str = "auto",
    optimizer_options: Mapping[str, object] | None = None,
    warm_start: str = "none",
    warm_start_delta: float = 0.001,
    warm_start_step: float = 0.05,
    warm_start_backtracks: int = 8,
) -> None
```

协调线路工厂、能量估计器与经典优化器。

`optimizer_method` 接受 SciPy 的优化器名字符串，也接受 [`cqlib_vqe.optim`](optim.md) 里的
优化器对象或自定义优化器实例。

参数：

- `factory`：线路工厂，需实现 build 接口，见 [`UCCSDFactory`](#uccsdfactory)。
- `estimator`：能量估计器，见[能量估计器](#estimators)。
- `optimizer_method`：`"COBYLA"` 等 SciPy 方法名，或自定义优化器对象。
- `max_iter`：最大迭代次数。
- `tol`：收敛容差。
- `execution_mode`：`"auto"`、`"circuit"` 或 `"direct_statevector"`。见下。
- `optimizer_options`：透传给优化器的额外选项。
- `warm_start`：`"none"` 或 `"gradient"`。
- `warm_start_*`：梯度预热的三项参数（步长、回退次数、扰动幅度）。

#### 执行模式

| 取值 | 行为 |
| --- | --- |
| `"auto"` | 推荐默认。原生 Pauli 直出态矢量路径可用且所需接口齐全时，优先使用该路径，即使 `construction_mode="bind"`；否则按下述顺序选择执行路径 |
| `"circuit"` | 强制线路执行。需要面向线路的估计器时使用，例如云端估计器 |
| `"direct_statevector"` | 仅在 `factory.build_statevector(...)` 与 `estimator.evaluate_parameters(...)` 都可用时使用 |

不在上述取值内时抛 `ValueError`。

`"auto"` 按以下顺序判定：

1. `factory.native_pauli_rotation_available` 为真，且工厂实现 `build_statevector(...)`、估计器实现 `evaluate_parameters(...)` 时，选择 `"direct_statevector"`。
2. 否则，若 `construction_mode="bind"`，选择 `"circuit"`，经 cqlib2 的 `assign_parameters` 绑定参数。
3. 否则，若上述两个方法都可用，选择 `"direct_statevector"`。
4. 其余情况选择 `"circuit"`。

要明确使用参数绑定线路，应设置 `execution_mode="circuit"`。

> COBYLA 下本包使用一个化学尺度的小初始信赖域半径，除非调用方在
> `optimizer_options['rhobeg']` 中另行指定。

(vqe-run)=
#### run

```python
run(
    hamiltonian_data,
    callback: Callable[[np.ndarray, float, int], None] | None = None,
    *,
    initial_params: Sequence[float] | None = None,
) -> dict[str, object]
```

运行优化。输入线路不会被修改。

返回的字典含以下键：

| 键 | 含义 |
| --- | --- |
| `optimal_value` | 最优能量 |
| `optimal_params` | 最优参数 |
| `n_evals` | 目标函数求值次数（等于 `len(history)`） |
| `optimizer_n_evals` | 优化器自身的求值计数 |
| `n_iters` | 迭代轮数 |
| `time` | 墙钟耗时（秒） |
| `success` | 优化器报告的收敛标志 |
| `message` | 优化器返回的说明 |
| `execution_mode` | 实际使用的执行模式 |
| `history` | 全部能量记录 |
| `best_history` | 逐次最优能量记录 |
| `warm_start` | 预热执行报告 |
| `optimizer_options` | 本次实际使用的优化器选项 |

> `success=False` 不等于结果错误。达到求值预算上限时会返回最优值但仍然报 `success=False`。
> 生产研究应放大 `max_iter` 并设定适合的能量或参数收敛判据。

---

### UCCSDFactory

```python
UCCSDFactory(
    molecule_data,
    *,
    construction_mode: str = "jit",
    coefficient_threshold: float = 1e-12,
    trotter_steps: int = 1,
    trotter_order: int = 2,
    selected_packed_indices: Sequence[int] | None = None,
) -> None
```

自旋适配的 selected-UCCSD 工厂，支持 JW、BK 与 parity 映射。

`molecule_data` 需提供 [`MolecularDataEngine`](chemistry.md#moleculardataengine) 产生的字段。

参数：

- `construction_mode`：`"jit"` 为重复求值构建数值线路；`"bind"` 保留符号模板，适合参数绑定更有利的执行路径。
- `coefficient_threshold`：生成元系数筛选阈值。
- `trotter_steps` / `trotter_order`：Trotter 展开的步数与阶数。
- `selected_packed_indices`：只保留指定的打包索引；`None` 表示使用全部。

#### 静态方法

```python
UCCSDFactory.from_compiled(
    *,
    n_qubits: int,
    n_electrons: int,
    generators: Sequence[Sequence[tuple[str, float] | PauliRotationTerm]],
    initial_values: Sequence[float] | None = None,
    construction_mode: str = "jit",
    occupied_qubits: Sequence[int] | None = None,
    trotter_steps: int = 1,
    trotter_order: int = 1,
) -> UCCSDFactory
```

当 Pauli 生成元的拟设已经就绪、且分子预处理刻意不纳入运行时，用这个方法构造工厂。

每个生成元是 `(pauli_string, coefficient)` 的列表。Pauli 串使用本包的 `q0-left` 顺序，
**最左字符作用于 qubit 0**。

#### 方法

```python
build(parameter_values: Sequence[float]) -> Circuit
build_statevector(parameter_values: Sequence[float]) -> Statevector
set_construction_mode(mode: str) -> None
```

- `build`：按参数构造线路。
- `build_statevector`：按参数直接构造态矢量。存在此方法时 [`VQESolver`](#vqesolver) 的 `"auto"` 模式可能选择融合路径。
- `set_construction_mode`：运行时切换构造模式。

---

(uccsd-factory)=
### UCCSD_Factory

`UCCSD_Factory` 与 `UCCSDFactory` 是**同一个对象**：

```python
import cqlib_vqe
assert cqlib_vqe.UCCSD_Factory is cqlib_vqe.UCCSDFactory
```

保留它只为兼容旧写法。

---

(estimators)=
## 能量估计器

### NativeStatevectorEstimator

```python
NativeStatevectorEstimator(backend: Any = None, n_qubits: int | None = None) -> None
```

基于 cqlib2 QIS API 的精确本地估计器。

#### 方法

```python
prepare_hamiltonian(hamiltonian_data, *, expected_num_qubits: int | None = None)
evaluate(circuit_or_state, hamiltonian_data) -> float
evaluate_statevector(state, hamiltonian_data) -> float
clear_cache() -> None
```

- `prepare_hamiltonian`：预计算哈密顿量表示。`expected_num_qubits` 用于校验比特数一致。
- `evaluate`：接受线路或态矢量，返回期望值。
- `evaluate_statevector`：只接受态矢量。
- `clear_cache`：清空内部缓存。

### DirectStatevectorEstimator

```python
DirectStatevectorEstimator(backend: Any = None, n_qubits: int | None = None) -> None
```

面向实现了 `build_statevector` 的工厂的**参数到能量的融合路径**，省去线路构造。

在 `execution_mode="auto"` 下，原生 Pauli 直出态矢量路径满足上述条件时优先使用，
包括 `construction_mode="bind"` 的工厂；完整回退顺序见上面的执行模式说明。

### FastStatevectorEstimator

```python
FastStatevectorEstimator(backend: Any = None, n_qubits: int | None = None) -> None
```

向后兼容名。**它继承自 [`NativeStatevectorEstimator`](#nativestatevectorestimator)，但不是同一个对象**
（`FastStatevectorEstimator is NativeStatevectorEstimator` 为 `False`）。新代码应直接用后者。

### EnergyEstimator

```python
EnergyEstimator(backend: ProbabilityBackend) -> None
```

采样式估计器，后端需提供 `run(circuit) -> probs`。

### ParallelEnergyEstimator

```python
ParallelEnergyEstimator(backend: ProbabilityBackend, max_workers: int = 8) -> None
```

并行 QWC 采样，面向线程安全的 C++ 后端或远程后端。

### CloudEnergyEstimator

```python
CloudEnergyEstimator(backend: CloudBatchBackend, n_qubits: int, batch_size: int = 50) -> None
```

**仅用于 cqlib 2.0 之前的云端 API 的兼容名。** 新的天衍工作请用
[`TianyanEnergyEstimator`](#tianyanenergyestimator)。

---

## 自适应 selected-UCCSD

### AdaptiveSelectedUCCSDSolver

```python
AdaptiveSelectedUCCSDSolver(
    molecule_data,
    estimator,
    config: AdaptiveSelectionConfig | None = None,
)
```

从规范 CCSD 振幅出发初始化拟设，然后扫描**完整的**剩余规范算符池，按实测能量梯度对候选
排序并逐轮增长。**初始 CCSD 振幅为零的候选仍然保留在池中**。

#### run

```python
run(
    *,
    reference_energy: float | None = None,
    round_callback: Callable[[AdaptiveRound], None] | None = None,
    optimizer_callback: Callable[[np.ndarray, float, int], None] | None = None,
) -> AdaptiveSelectedUCCSDResult
```

参数：

- `reference_energy`：参考能量，用于计算每轮的 `reference_error`。
- `round_callback`：每轮结束后的回调。
- `optimizer_callback`：透传给内部 VQE 优化的逐次求值回调。

### AdaptiveSelectionConfig

```python
AdaptiveSelectionConfig(
    initial_amplitude_threshold: float = 0.001,
    candidate_amplitude_threshold: float = 0.0,
    min_initial_parameters: int = 1,
    pool_rounds: int = 2,
    max_add_per_round: int | None = None,
    max_rounds: int | None = None,
    batch_size: int | None = None,
    max_parameters: int | None = None,
    max_screen_candidates: int | None = None,
    gradient_delta: float = 0.001,
    gradient_threshold: float = 0.0001,
    target_energy_error: float = 0.0016,
    optimizer_method: str = "COBYLA",
    optimizer_maxiter: int = 80,
    optimizer_tolerance: float = 1e-07,
    optimizer_options: dict[str, Any] = {},
    construction_mode: str = "bind",
    execution_mode: str = "auto",
    trotter_steps: int = 2,
    trotter_order: int = 2,
    candidate_initialization: str = "best_probe",
) -> None
```

阈值增长式 selected-UCCSD 的配置。

关键字段：

- `initial_amplitude_threshold`：初始拟设纳入算符的振幅阈值。
- `candidate_amplitude_threshold`：候选池的振幅阈值。**默认 `0.0`，即不因振幅为零而排除候选**。
- `pool_rounds`：全池扫描轮数。
- `gradient_threshold` / `gradient_delta`：候选梯度的判定阈值与差分步长。
- `max_add_per_round` / `max_parameters` / `max_rounds`：增长上限。
- `target_energy_error`：停止判据使用的目标能量误差。

### CandidateGradient

```python
CandidateGradient(
    packed_index: int,
    gradient: float,
    absolute_gradient: float,
    ccsd_amplitude: float,
    energy_plus: float,
    energy_minus: float,
    initial_value: float = 0.0,
    predicted_improvement: float = 0.0,
) -> None
```

单个候选算符的梯度测量结果。`energy_plus` / `energy_minus` 是差分两侧的能量。

### AdaptiveRound

```python
AdaptiveRound(
    round_index: int,
    selected_before: tuple[int, ...],
    candidate_pool_before: tuple[int, ...],
    optimized_energy: float,
    reference_error: float | None,
    optimizer_evaluations: int,
    candidates: tuple[CandidateGradient, ...],
    gradient_norm: float | None,
    added_indices: tuple[int, ...],
    wall_time_seconds: float,
    pool_scan_index: int | None = None,
    eligible_indices: tuple[int, ...] = (),
    selected_after: tuple[int, ...] = (),
) -> None
```

一轮优化后的状态，以及随后的池扫描结果（若执行了）。

### AdaptiveSelectedUCCSDResult

```python
AdaptiveSelectedUCCSDResult(
    optimal_value: float,
    optimal_params: np.ndarray,
    full_pool_indices: tuple[int, ...],
    initial_selected_packed_indices: tuple[int, ...],
    selected_packed_indices: tuple[int, ...],
    remaining_candidate_packed_indices: tuple[int, ...],
    rounds: tuple[AdaptiveRound, ...],
    stop_reason: str,
    reference_energy: float | None,
    reference_error: float | None,
    precision_certified: bool,
    total_evaluations: int,
    full_parameter_count: int,
    pool_scans_completed: int,
    configuration: dict[str, Any],
) -> None
```

自适应求解的完整结果。`stop_reason` 说明为什么停止；`precision_certified` 表示是否达到了
`target_energy_error`。

---

## 天衍执行

天衍会提交**真实的测量任务并消耗平台额度**。凭据配置在版本控制之外，提交前先确认后端名与
物理比特映射。映射从逻辑比特排到物理比特，长度必须恰好等于 `n_qubits`。

### TianyanEnergyEstimator

```python
TianyanEnergyEstimator(
    backend,
    n_qubits: int,
    *,
    shots: int = 4096,
    calibration_mode: str = "disabled",
    physical_qubits: Sequence[int] | None = None,
    measure_only_support: bool = True,
    grouping: str = "qwc",
    timeout_secs: float = 1800.0,
    poll_interval_secs: float = 5.0,
) -> None
```

面向 `cqlib_tianyan` 后端的 QWC 分组能量估计器。提交前按 qubit-wise commuting 关系对 Pauli 项
分组，返回时校验任务顺序、测量比特头与计数载荷。

> 该估计器**不推断路由，也不会静默修补后端元数据**。

(tianyan-methods)=
#### 方法

```python
validate_backend_mapping(*, require_available: bool = True) -> Any
prepare(base_circuit, hamiltonian_data) -> TianyanMeasurementPlan
submit(base_circuit, hamiltonian_data) -> TianyanSubmittedEvaluation
collect(submitted: TianyanSubmittedEvaluation) -> TianyanEnergyResult
evaluate(base_circuit, hamiltonian_data) -> float
evaluate_with_details(base_circuit, hamiltonian_data) -> TianyanEnergyResult
group_hamiltonian(hamiltonian_data)
clear_grouping_cache() -> None
```

- `validate_backend_mapping`：校验物理比特映射与后端可用性。
- `prepare` / `submit` / `collect`：把一次能量求值拆成「组装计划」「提交」「取回」三步，便于分离提交与等待。
- `evaluate`：一步完成的便捷入口，返回能量。
- `evaluate_with_details`：同上，但返回完整结果对象。
- `group_hamiltonian`：对哈密顿量做 QWC 分组。
- `clear_grouping_cache`：清空分组缓存。

### TianyanCloudEnergyEstimator

与 [`TianyanEnergyEstimator`](#tianyanenergyestimator) 是**同一个对象**：

```python
import cqlib_vqe
assert cqlib_vqe.TianyanCloudEnergyEstimator is cqlib_vqe.TianyanEnergyEstimator
```

保留它只为兼容旧写法。

### TianyanMeasurementPlan

```python
TianyanMeasurementPlan(
    circuits: tuple[str, ...],
    groups: tuple[TianyanMeasurementGroup, ...],
    constant_energy: float,
    logical_to_physical: tuple[int, ...],
    n_qubits: int,
) -> None
```

一次 VQE 能量求值所需的全部硬件线路。`circuits` 是待提交的线路文本，`constant_energy` 是不需要
测量的常数项贡献。

### TianyanMeasurementGroup

```python
TianyanMeasurementGroup(
    master_pauli: str,
    terms: tuple[tuple[str, complex | float | int], ...],
    measured_logical_qubits: tuple[int, ...],
    measured_physical_qubits: tuple[int, ...],
) -> None
```

一个 QWC 分组及其对应的硬件测量元数据。

### TianyanSubmittedEvaluation

```python
TianyanSubmittedEvaluation(plan: TianyanMeasurementPlan, task: Any | None) -> None
```

测量计划与对应的天衍任务句柄。`submit()` 返回的 `task=None` 表示 `plan.circuits` 为空，
无需提交测量线路，例如哈密顿量仅含常数项。此时未向天衍提交任务，`collect()` 直接返回
以 `plan.constant_energy` 为能量、`groups` 与 `task_ids` 均为空的结果。这是正常的无需测量路径，
不表示提交失败。

### TianyanEnergyResult

```python
TianyanEnergyResult(
    energy: float,
    constant_energy: float,
    groups: tuple[TianyanGroupResult, ...],
    task_ids: tuple[str, ...],
    shots: int,
    device_name: str,
    calibration_mode: str,
) -> None
```

[`TianyanEnergyEstimator.evaluate_with_details`](#tianyan-methods) 返回的详细结果。

### TianyanGroupResult

```python
TianyanGroupResult(
    master_pauli: str,
    task_id: str,
    measured_physical_qubits: tuple[int, ...],
    terms: tuple[TianyanTermResult, ...],
    contribution: float,
) -> None
```

单个 QWC 分组的测量结果。

### TianyanTermResult

```python
TianyanTermResult(
    pauli: str,
    coefficient: float,
    expectation: float,
    contribution: float,
) -> None
```

单个 Pauli 项的期望值及其对总能量的贡献（`contribution = coefficient * expectation`）。
