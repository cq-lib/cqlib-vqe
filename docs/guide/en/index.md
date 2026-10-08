# Usage guide

`cqlib-vqe` is a VQE package for molecular electronic-structure calculations on cqlib 2.x.

## Installation

Python 3.10 or newer is required. An isolated environment is recommended:

```bash
git clone https://github.com/cq-lib/cqlib-vqe.git
cd cqlib-vqe

python -m venv .venv
source .venv/bin/activate              # Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install the variant required by the workflow:

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

| Variant | Dependencies pulled in | Capabilities unlocked |
| --- | --- | --- |
| (base) | `numpy`, `scipy`, `cqlib` | Local VQE from a precompiled ansatz |
| `chemistry` | `openfermion`, `openfermionpyscf`, `pyscf` | [`MolecularDataEngine`](../../api/en/chemistry.md#moleculardataengine) molecular preprocessing |
| `tianyan` | `cqlib-tianyan` | [`TianyanEnergyEstimator`](../../api/en/vqe.md#tianyanenergyestimator) cloud execution |
| `test` | `pytest` | Test suite |

Run the test suite after installation:

```bash
pytest -q
```

## Package layout

| Subpackage | Responsibility |
| --- | --- |
| [`cqlib_vqe.chemistry`](../../api/en/chemistry.md) | Molecular preprocessing, mappings, active space, canonical singlet-UCCSD generators |
| [`cqlib_vqe.vqe`](../../api/en/vqe.md) | Circuit factories, energy estimators, solvers, adaptive selection, Tianyan execution |
| [`cqlib_vqe.optim`](../../api/en/optim.md) | Classical optimizers (built-in implementations besides SciPy) |
| [`cqlib_vqe.utils`](../../api/en/utils.md) | Phase timers |

Public names of `chemistry` and `vqe` can be imported directly from the top-level `cqlib_vqe`; `optim` and `utils` must be imported from their subpackages.

## A first VQE

The example below **does not depend on any chemistry library** and validates the whole chain with a precompiled one-parameter ansatz: ansatz → estimator → solver. The Hamiltonian is $H = Z$ and the generator is $G = i \cdot 0.5 \cdot Y$.

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

Actual output:

```
optimal_value  ≈ -0.99999999909
optimal_params =  [3.14155]
execution_mode =  'direct_statevector'
success        =  False
```

**Note that `success=False` is not an error.** This example deliberately caps COBYLA at 30 evaluations, so it reaches the numerical minimum while still reporting `success=False` because the evaluation budget is exhausted:

```
Return from COBYLA because the objective function has been evaluated MAXFUN times.
```

In a production study, increase `max_iter` and define an energy or parameter convergence criterion appropriate to that study. The complete fields of the returned dictionary are documented in [`VQESolver`](../../api/en/vqe.md#vqesolver).

The runnable version is available as:

```bash
python examples/minimal_compiled_smoke.py
```

## Next steps

- [Molecular VQE workflow](workflow.md): from molecular geometry to energy, covering mappings, active space, execution mode, adaptive selection, and Tianyan execution.
- [API reference](../../api/en/index.md): all public interfaces, organized by subpackage.
