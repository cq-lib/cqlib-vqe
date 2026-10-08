# cqlib_vqe.utils

`cqlib_vqe.utils` provides a lightweight phase timer for locating the distribution of
time spent in each VQE phase.

**This subpackage is not re-exported at the top level of `cqlib_vqe`**:

```python
from cqlib_vqe.utils import PerformanceTracker, global_tracker
```

## Overview

| Name | Type | Description |
| --- | --- | --- |
| [`PerformanceTracker`](#performancetracker) | Class | Accumulates elapsed time and call counts per phase |
| [`global_tracker`](#global-tracker) | Instance | Module-level shared `PerformanceTracker` |

---

## PerformanceTracker

```python
PerformanceTracker() -> None
```

Accumulates elapsed time and call counts per phase. The constructor takes no arguments.

### Methods

```python
phase(name: str)
report() -> None
reset() -> None
```

- `phase(name)`: a context manager. It starts timing on entry and, on exit, adds the elapsed time to `name` and increments the call count by one.
- `report()`: prints the statistics to standard output as a table, sorted by total elapsed time in descending order.
- `reset()`: clears all records.

### Attributes

| Attribute | Type | Meaning |
| --- | --- | --- |
| `records` | `dict[str, float]` | Accumulated elapsed time in seconds for each phase name |
| `counts` | `dict[str, int]` | Call count for each phase name |

`records` and `counts` are `defaultdict` instances; reading a phase name that has never
been recorded gives `0`.

### Example

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

Phases with the same name are accumulated, so a loop can enter and exit them repeatedly:

```python
for _ in range(5):
    with tracker.phase("energy_evaluate"):
        estimator.evaluate(circuit, molecule.hamiltonian_data)

assert tracker.counts["energy_evaluate"] == 5
```

---

## global_tracker

```python
global_tracker: PerformanceTracker
```

A module-level shared instance of type `PerformanceTracker`. Use it to aggregate one set
of statistics across several modules instead of passing an object around.

It and a separately created `PerformanceTracker()` **do not affect each other**;
`global_tracker.reset()` clears only its own records.

```python
from cqlib_vqe.utils import global_tracker

with global_tracker.phase("some_stage"):
    ...

global_tracker.report()
global_tracker.reset()
```
