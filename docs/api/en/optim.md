# cqlib_vqe.optim

`cqlib_vqe.optim` provides classical optimizers that can be passed directly to
[`VQESolver`](vqe.md#vqesolver), together with the base class for writing custom
optimizers.

**This subpackage is not re-exported at the top level of `cqlib_vqe`** and must be
imported from the subpackage:

```python
from cqlib_vqe.optim import AdamOptimizer, ClassicalOptimizer, OptimizerResult
```

The optimizers shipped with SciPy (`"COBYLA"`, `"BFGS"`, and others) are used through
method-name strings and do not require this subpackage. The implementations below are
provided by this package, for cases that SciPy does not cover or that require custom
behavior.

## Overview

| Name | Description |
| --- | --- |
| [`ClassicalOptimizer`](#classicaloptimizer) | Base class for custom optimizers |
| [`OptimizerResult`](#optimizerresult) | Optimizer return value |
| [`NelderMeadOptimizer`](#neldermeadoptimizer) | Nelder-Mead simplex search |
| [`QuantumCoordinateDescent`](#quantumcoordinatedescent) | Quantum coordinate descent |
| [`SPSAOptimizer`](#spsaoptimizer) | Simultaneous perturbation stochastic approximation |
| [`AdamOptimizer`](#adamoptimizer) | Adam (central-difference gradient) |
| [`AdagradOptimizer`](#adagradoptimizer) | Adagrad (central-difference gradient) |
| [`MomentumOptimizer`](#momentumoptimizer) | Finite-difference gradient descent with momentum |

---

## Base class and return value

### ClassicalOptimizer

```python
ClassicalOptimizer(max_iter: int = 100, tol: float = 1e-06, verbose: bool = False)
```

The base class for custom optimizers. Subclass it and implement `minimize` to pass it to
[`VQESolver`](vqe.md#vqesolver).

#### Methods

```python
minimize(objective_function, x0: np.ndarray) -> OptimizerResult
```

Minimizes `objective_function` starting from `x0`.

- `objective_function`: the objective function to minimize; it takes a parameter array and returns a scalar energy.
- `x0`: the starting parameters.

It must return [`OptimizerResult`](#optimizerresult).

### OptimizerResult

```python
OptimizerResult(
    success: bool,
    x: np.ndarray,
    fun: float,
    nfev: int,
    nit: int,
    message: str,
    trajectory: list[float] = [],
) -> None
```

The return value of an optimizer.

| Field | Meaning |
| --- | --- |
| `success` | Whether the optimizer converged |
| `x` | The optimal parameters |
| `fun` | The optimal objective-function value |
| `nfev` | Number of objective-function evaluations |
| `nit` | Number of iterations |
| `message` | Descriptive text |
| `trajectory` | Record of successive energies |

---

## Gradient-free optimizers

### NelderMeadOptimizer

```python
NelderMeadOptimizer(
    max_iter: int = 100,
    tol: float = 1e-06,
    alpha: float = 1.0,
    gamma: float = 2.0,
    rho: float = 0.5,
    sigma: float = 0.5,
)
```

Nelder-Mead simplex search. No gradient is required; suited to settings with few
parameters and little noise.

`alpha` / `gamma` / `rho` / `sigma` are the reflection, expansion, contraction, and
shrink coefficients.

### QuantumCoordinateDescent

```python
QuantumCoordinateDescent(max_iter: int = 50, tol: float = 1e-06)
```

Coordinate descent, intended for objective functions in which **each parameter
corresponds to a single sinusoidal frequency** (the UCCSD energy has exactly this form
in a single parameter). It solves each coordinate analytically and does not construct a
gradient.

### SPSAOptimizer

```python
SPSAOptimizer(
    max_iter: int = 100,
    a: float = 0.6,
    c: float = 0.1,
    A: float = 0.0,
    alpha: float = 0.602,
    gamma: float = 0.101,
)
```

Simultaneous Perturbation Stochastic Approximation (SPSA). Each iteration performs only
two objective-function evaluations; suited to settings **with sampling noise**.

The parameters `a` / `c` / `A` / `alpha` / `gamma` control the decay of the step size and
the perturbation magnitude.

---

## Gradient-based optimizers

All three below estimate the gradient with **central finite differences**, so the number
of objective-function evaluations per iteration grows linearly with the number of
parameters.

### AdamOptimizer

```python
AdamOptimizer(
    lr: float = 0.01,
    beta1: float = 0.9,
    beta2: float = 0.999,
    epsilon: float = 1e-08,
    max_iter: int = 200,
    tol: float = 1e-06,
)
```

Gradient descent with adaptive moment estimation.

### AdagradOptimizer

```python
AdagradOptimizer(
    learning_rate: float = 0.01,
    epsilon: float = 1e-08,
    max_iter: int = 200,
    tol: float = 1e-06,
)
```

Gradient descent that accumulates the squares of past gradients.

### MomentumOptimizer

```python
MomentumOptimizer(
    learning_rate: float = 0.01,
    momentum: float = 0.9,
    max_iter: int = 200,
    tol: float = 1e-06,
    epsilon: float = 1e-05,
)
```

Finite-difference gradient descent with heavy-ball momentum.
