# cqlib_vqe.utils

`cqlib_vqe.utils` 提供一个轻量的阶段计时器，用于定位 VQE 各阶段的耗时分布。

**该子包不在顶层 `cqlib_vqe` 重导出**：

```python
from cqlib_vqe.utils import PerformanceTracker, global_tracker
```

## 总览

| 名字 | 类型 | 简介 |
| --- | --- | --- |
| [`PerformanceTracker`](#performancetracker) | 类 | 按阶段累计耗时与调用次数 |
| [`global_tracker`](#global-tracker) | 实例 | 模块级共享的 `PerformanceTracker` |

---

## PerformanceTracker

```python
PerformanceTracker() -> None
```

按阶段累计耗时与调用次数。构造不接受参数。

### 方法

```python
phase(name: str)
report() -> None
reset() -> None
```

- `phase(name)`：上下文管理器。进入时开始计时，退出时把耗时累加到 `name` 并把调用计数加一。
- `report()`：把统计结果以表格形式打印到标准输出，按总耗时降序排列。
- `reset()`：清空全部记录。

### 属性

| 属性 | 类型 | 含义 |
| --- | --- | --- |
| `records` | `dict[str, float]` | 每个阶段名的累计耗时（秒） |
| `counts` | `dict[str, int]` | 每个阶段名的调用次数 |

`records` 与 `counts` 是 `defaultdict`，读取未记录过的阶段名会得到 `0`。

### 示例

```python
from cqlib_vqe.utils import PerformanceTracker

tracker = PerformanceTracker()

with tracker.phase("hamiltonian_prepare"):
    estimator.prepare_hamiltonian(molecule.hamiltonian_data)

with tracker.phase("energy_evaluate"):
    value = estimator.evaluate(circuit, molecule.hamiltonian_data)

tracker.report()
print(tracker.records["energy_evaluate"], tracker.counts["energy_evaluate"])
```

同名 `phase` 会被累计，因此可以在循环里反复进入退出：

```python
for _ in range(5):
    with tracker.phase("energy_evaluate"):
        estimator.evaluate(circuit, molecule.hamiltonian_data)

assert tracker.counts["energy_evaluate"] == 5
```

---

(global-tracker)=
## global_tracker

```python
global_tracker: PerformanceTracker
```

模块级共享实例，`PerformanceTracker` 类型。需要在多个模块之间汇总同一份统计时用它，
避免自己传对象。

它与自建的 `PerformanceTracker()` **互不影响**；`global_tracker.reset()` 只清空它自己的记录。

```python
from cqlib_vqe.utils import global_tracker

with global_tracker.phase("some_stage"):
    ...

global_tracker.report()
global_tracker.reset()
```
