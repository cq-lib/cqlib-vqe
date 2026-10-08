# cqlib_vqe.chemistry

`cqlib_vqe.chemistry` 负责分子预处理的全部工作：从分子几何出发做电子结构计算，
选择活性空间，把费米子算符映射到量子比特，并生成规范单重态 UCCSD 的激发生成元与
打包后的振幅。

该子包的多数入口依赖 **OpenFermion** 与 **PySCF**（安装 `cqlib-vqe[chemistry]`）。
缺少依赖时抛 `ImportError`。

## 总览

| 名字 | 类型 | 简介 |
| --- | --- | --- |
| [`MolecularDataEngine`](#moleculardataengine) | 类 | 分子预处理主入口：几何 → 哈密顿量 + UCCSD 数据 |
| [`ActiveSpaceConfig`](#activespaceconfig) | 类 | 活性空间策略配置 |
| [`ActiveSpaceReport`](#activespacereport) | 类 | 活性空间选择报告 |
| [`select_active_space`](#select-active-space) | 函数 | 按配置确定活性空间并返回报告 |
| [`estimate_frozen_core_orbitals`](#estimate-frozen-core-orbitals) | 函数 | 估算常规冻结核轨道数 |
| [`normalize_mapper_type`](#normalize-mapper-type) | 函数 | 规范化映射名 |
| [`map_fermion_operator`](#map-fermion-operator) | 函数 | 按指定映射转换费米子算符 |
| [`encoded_occupied_qubits`](#encoded-occupied-qubits) | 函数 | 把费米子占据态编码成占据的量子比特 |
| [`canonical_singlet_descriptors`](#canonical-singlet-descriptors) | 函数 | 按打包顺序返回激发生成元描述符 |
| [`canonical_singlet_operator`](#canonical-singlet-operator) | 函数 | 返回单个 one-hot 反厄米生成元 |
| [`canonical_parameter_count`](#canonical-parameter-count) | 函数 | 规范单重态 UCCSD 的参数个数 |
| [`pack_closed_shell_ccsd`](#pack-closed-shell-ccsd) | 函数 | 把 CCSD 振幅打包成规范单重态顺序 |
| [`SingletExcitation`](#singletexcitation) | 类 | 单个激发描述符 |
| [`CanonicalBasisAudit`](#canonicalbasisaudit) | 类 | 打包过程的正交性审计结果 |

---

## 分子预处理

### MolecularDataEngine

```python
MolecularDataEngine(
    geometry: Sequence[tuple[str, Sequence[float]]],
    basis: str = "sto-3g",
    multiplicity: int = 1,
    charge: int = 0,
    mapper_type: str = "jw",
    occupied_indices: Sequence[int] | None = None,
    active_indices: Sequence[int] | None = None,
    *,
    excitation_threshold: float = 0.001,
    active_space: ActiveSpaceConfig | str | None = None,
) -> None
```

准备闭壳层活性空间哈密顿量与规范 UCCSD 数据。

构造只做参数校验与配置保存，**计算发生在 [`run()`](#mde-run) 里**。

参数：

- `geometry`：原子几何，每项为 `(元素符号, (x, y, z))`。
- `basis`：基组名，默认 `"sto-3g"`。
- `multiplicity`：自旋多重度。**目前只支持 `1`**（闭壳层单重态），其它取值抛 `NotImplementedError`。
- `charge`：分子电荷。
- `mapper_type`：`"jw"`、`"bk"` 或 `"parity"`，见 [`normalize_mapper_type`](#normalize-mapper-type)。
- `occupied_indices` / `active_indices`：手工指定冻结占据轨道与活性轨道。
- `excitation_threshold`：激发生成元的筛选阈值。
- `active_space`：活性空间配置，接受 [`ActiveSpaceConfig`](#activespaceconfig) 实例或模式名字符串。

(mde-run)=
#### run

```python
run(*, run_fci: bool = True, audit_ccsd_basis: bool = True) -> MolecularDataEngine
```

执行电子结构计算并返回 `self`，因此可以写成 `MolecularDataEngine(...).run()`。

参数：

- `run_fci`：是否同时计算 FCI 参考能量。
- `audit_ccsd_basis`：是否对 CCSD 振幅的规范基打包做正交性审计。

`run()` 之后可读取的属性：

| 属性 | 含义 |
| --- | --- |
| `n_qubits` | 映射后的量子比特数 |
| `n_spin_orbitals` | 自旋轨道数 |
| `n_electrons` | 电子数 |
| `nuclear_repulsion` | 核排斥能 |
| `hf_energy` | Hartree--Fock 能量 |
| `hamiltonian_data` | 映射后的 Pauli 哈密顿量，直接传给 [`VQESolver`](vqe.md#vqesolver) |
| `reference_energies` | 参考能量（含 FCI，若 `run_fci=True`） |
| `active_space_report` | 活性空间报告，见 [`ActiveSpaceReport`](#activespacereport) |
| `ccsd_parameters` | 打包后的 CCSD 振幅 |
| `ccsd_packing_report` | 打包审计结果，见 [`CanonicalBasisAudit`](#canonicalbasisaudit) |
| `initial_occupied_qubits` | 映射后的初始占据量子比特 |
| `initial_bitstring` | 参考态比特串 |

#### 其它方法

```python
candidate_packed_indices(minimum_amplitude: float = 0.0) -> list[int]
ccsd_amplitude_map() -> dict[int, float]
ccsd_items(packed_indices: Sequence[int] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]
```

- `candidate_packed_indices`：返回振幅绝对值不小于 `minimum_amplitude` 的打包索引。**这是「初始振幅为零的算符仍留在候选池中」的实现基础**——默认阈值 `0.0` 不会排除零振幅算符。
- `ccsd_amplitude_map`：返回 `{打包索引: 振幅}` 映射。
- `ccsd_items`：返回单激发与双激发条目列表，用于检查或外部消费。

---

### ActiveSpaceConfig

```python
ActiveSpaceConfig(
    mode: Literal["full", "auto", "manual"] = "full",
    freeze_core: bool = True,
    max_active_qubits: int | None = None,
    max_active_orbitals: int | None = None,
    active_electrons: int | None = None,
    active_orbitals: int | None = None,
    min_virtual_orbitals: int = 1,
    virtual_energy_window: float | None = None,
    allow_additional_frozen_occupied: bool = True,
) -> None
```

活性空间策略配置。冻结的 `dataclass`，构造后不可修改。

推荐用静态方法构造，而不是直接传 `mode`：

```python
ActiveSpaceConfig.full()          # 保留全部轨道空间（mode="full", freeze_core=False）
ActiveSpaceConfig.automatic(...)  # 确定性自动选择
ActiveSpaceConfig.manual()        # 手工指定（mode="manual"）
```

`automatic` 的签名：

```python
ActiveSpaceConfig.automatic(
    *,
    max_active_qubits: int | None = None,
    max_active_orbitals: int | None = None,
    active_electrons: int | None = None,
    active_orbitals: int | None = None,
    freeze_core: bool = True,
    min_virtual_orbitals: int = 1,
) -> ActiveSpaceConfig
```

#### 方法

- `validate() -> None`：校验配置。`mode` 不是三个取值之一、或 `max_active_qubits` 非正或为奇数时抛 `ValueError`。

---

### ActiveSpaceReport

```python
ActiveSpaceReport(
    mode: str,
    original_spatial_orbitals: int,
    original_electrons: int,
    occupied_spatial_orbitals: int,
    frozen_occupied_indices: tuple[int, ...],
    active_indices: tuple[int, ...],
    excluded_virtual_indices: tuple[int, ...],
    active_electrons: int,
    active_spatial_orbitals: int,
    pre_taper_qubits: int,
    estimated_core_orbitals: int,
    additional_frozen_occupied: int,
    selection_reason: str,
    orbital_energies: tuple[float, ...] = (),
    warnings: tuple[str, ...] = (),
) -> None
```

活性空间选择的完整报告。字段记录了选择前后的轨道与电子数、冻结/活性/排除的轨道索引、
以及 `selection_reason` 说明为什么这样选。

**该报告应当与每个数值结果一起记录**，因为它固定了所模拟的哈密顿量与参数池。

---

(select-active-space)=
### select_active_space

```python
select_active_space(
    *,
    config: ActiveSpaceConfig,
    geometry: Sequence[tuple[str, Sequence[float]]],
    n_orbitals: int,
    n_electrons: int,
    orbital_energies: Sequence[float],
    occupied_indices: Sequence[int] | None = None,
    active_indices: Sequence[int] | None = None,
) -> ActiveSpaceReport
```

按配置确定活性空间并返回完整报告。这是确定性函数：相同输入给出相同报告。

---

(estimate-frozen-core-orbitals)=
### estimate_frozen_core_orbitals

```python
estimate_frozen_core_orbitals(symbols: Iterable[str]) -> int
```

按元素符号估算常规的冻结核空间轨道数。

---

## 映射

(normalize-mapper-type)=
### normalize_mapper_type

```python
normalize_mapper_type(mapper_type: str) -> MapperType
```

把映射名规范化为 VQE 流程接受的形式。大小写不敏感。无法识别的名字抛 `ValueError`。

(map-fermion-operator)=
### map_fermion_operator

```python
map_fermion_operator(fermion_operator, *, mapper_type: str, n_spin_orbitals: int)
```

用指定映射转换一个 `FermionOperator`。

(encoded-occupied-qubits)=
### encoded_occupied_qubits

```python
encoded_occupied_qubits(
    *, n_spin_orbitals: int, occupied_spin_orbitals: Iterable[int], mapper_type: str
) -> tuple[int, ...]
```

把费米子占据向量编码为「占据的量子比特」索引。

> BK 与 parity 映射下，参考态的比特图样**一般不能只用 Hamming 重量刻画**。不要用 JW 的
> 占据捷径去替换工厂的参考态构造。

---

## 规范单重态 UCCSD

这一组函数实现「打包顺序」（packed order）：把单激发与双激发排成一个稳定的参数序列，
使 CCSD 振幅、生成元、线路参数三者一一对应。

(canonical-singlet-descriptors)=
### canonical_singlet_descriptors

```python
canonical_singlet_descriptors(n_qubits: int, n_electrons: int) -> list[SingletExcitation]
```

按 OpenFermion 的打包单重态 UCCSD 顺序返回描述符列表。

(canonical-singlet-operator)=
### canonical_singlet_operator

```python
canonical_singlet_operator(packed_index: int, n_qubits: int, n_electrons: int)
```

返回第 `packed_index` 个 one-hot 的反厄米 OpenFermion 单重态生成元。

(canonical-parameter-count)=
### canonical_parameter_count

```python
canonical_parameter_count(n_qubits: int, n_electrons: int) -> int
```

返回给定比特数与电子数下规范单重态 UCCSD 的参数个数。由闭壳层占据轨道数与虚拟轨道数
决定的占据-虚拟轨道对数算出。

(pack-closed-shell-ccsd)=
### pack_closed_shell_ccsd

```python
pack_closed_shell_ccsd(
    single_amplitudes: np.ndarray,
    double_amplitudes: np.ndarray,
    n_qubits: int,
    n_electrons: int,
    *,
    atol: float = 1e-12,
    audit: bool = True,
) -> tuple[list[SingletExcitation], np.ndarray, CanonicalBasisAudit]
```

把 CCSD 的单、双振幅打包成规范单重态顺序。

返回三元组：描述符列表、打包后的振幅数组、以及审计结果。

需要 OpenFermion；缺少时抛 `ImportError`。

参数：

- `atol`：判定振幅是否可忽略的绝对容差。
- `audit`：是否执行规范基审计。关闭时第三个返回值仍会给出，但 `audited` 为假。

---

### SingletExcitation

```python
SingletExcitation(
    kind: str,
    pair_a: tuple[int, int],
    pair_b: tuple[int, int] | None = None,
    packed_index: int = -1,
) -> None
```

单个激发描述符。`kind` 区分单激发与双激发；`pair_b` 只在双激发时有值。

### CanonicalBasisAudit

```python
CanonicalBasisAudit(
    relative_residual: float,
    absolute_residual: float,
    target_norm: float,
    rank: int,
    parameter_count: int,
    term_count: int,
    audited: bool = True,
) -> None
```

规范基打包的正交性审计结果。`rank` 与 `parameter_count` 不一致说明打包基不完备。
