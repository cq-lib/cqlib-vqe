# API reference

The public interface of `cqlib-vqe` is divided into four subpackages.

## Import conventions

The top-level package re-exports the public names of the `chemistry` and `vqe`
subpackages:

```python
from cqlib_vqe import MolecularDataEngine, UCCSDFactory, VQESolver
```

`optim` and `utils` are **not** re-exported at the top level and must be imported
from their subpackages:

```python
from cqlib_vqe.optim import AdamOptimizer
from cqlib_vqe.utils import PerformanceTracker
```

## Subpackages at a glance

| Subpackage | Public names | Responsibility | Page |
| --- | --- | --- | --- |
| `cqlib_vqe.chemistry` | 14 | Molecular preprocessing, mappings, active space, canonical singlet-UCCSD generators and amplitudes | [chemistry](chemistry.md) |
| `cqlib_vqe.vqe` | 22 | Circuit factories, energy estimators, solvers, adaptive selection, Tianyan execution | [vqe](vqe.md) |
| `cqlib_vqe.optim` | 8 | Classical optimizers and the custom-optimizer base class | [optim](optim.md) |
| `cqlib_vqe.utils` | 2 | Phase timers | [utils](utils.md) |

## Find by task

| Task | Entry point |
| --- | --- |
| Build a Hamiltonian from a molecular geometry | [`MolecularDataEngine`](chemistry.md#moleculardataengine) |
| Select an active space | [`ActiveSpaceConfig`](chemistry.md#activespaceconfig) / [`select_active_space`](chemistry.md) |
| Build a UCCSD circuit or statevector | [`UCCSDFactory`](vqe.md#uccsdfactory) |
| Evaluate expectation values exactly and locally | [`NativeStatevectorEstimator`](vqe.md#nativestatevectorestimator) / [`DirectStatevectorEstimator`](vqe.md#directstatevectorestimator) |
| Run one VQE | [`VQESolver`](vqe.md#vqesolver) |
| Grow the operator pool adaptively | [`AdaptiveSelectedUCCSDSolver`](vqe.md#adaptiveselecteduccsdsolver) |
| Submit to the Tianyan platform | [`TianyanEnergyEstimator`](vqe.md#tianyanenergyestimator) |
| Switch the classical optimizer | [`cqlib_vqe.optim`](optim.md) |

## Conventions

- **Bit order**: Pauli strings use `q0-left` order, that is, the leftmost character acts on qubit 0. This is described in [Molecular VQE workflow](../../guide/en/workflow.md).
- **Return types**: most result objects are `dataclass` instances (such as `AdaptiveRound` and `TianyanEnergyResult`) whose fields are read-only named attributes; `VQESolver.run` is the exception and returns a `dict`.
- **Optional dependencies**: entry points that require OpenFermion or PySCF raise `ImportError` when the dependency is missing; Tianyan entry points require `cqlib-tianyan`.
