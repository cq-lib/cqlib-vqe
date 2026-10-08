# cqlib_vqe.optim

`cqlib_vqe.optim` 提供可直接传给 [`VQESolver`](vqe.md#vqesolver) 的经典优化器，以及编写自定义
优化器的基类。

**该子包不在顶层 `cqlib_vqe` 重导出**，需要从子包导入：

```python
from cqlib_vqe.optim import AdamOptimizer, ClassicalOptimizer, OptimizerResult
```

SciPy 自带的优化器（`"COBYLA"`、`"BFGS"` 等）通过方法名字符串使用，不需要这个子包。
下面这些是本包自带的实现，用于 SciPy 没有覆盖或需要自定义行为的情形。

## 总览

| 名字 | 简介 |
| --- | --- |
| [`ClassicalOptimizer`](#classicaloptimizer) | 自定义优化器的基类 |
| [`OptimizerResult`](#optimizerresult) | 优化器返回值 |
| [`NelderMeadOptimizer`](#neldermeadoptimizer) | Nelder--Mead 单纯形搜索 |
| [`QuantumCoordinateDescent`](#quantumcoordinatedescent) | 量子坐标下降 |
| [`SPSAOptimizer`](#spsaoptimizer) | 同时扰动随机逼近 |
| [`AdamOptimizer`](#adamoptimizer) | Adam（中心差分梯度） |
| [`AdagradOptimizer`](#adagradoptimizer) | Adagrad（中心差分梯度） |
| [`MomentumOptimizer`](#momentumoptimizer) | 带动量的有限差分梯度下降 |

---

## 基类与返回值

### ClassicalOptimizer

```python
ClassicalOptimizer(max_iter: int = 100, tol: float = 1e-06, verbose: bool = False)
```

自定义优化器的基类。继承它并实现 `minimize` 即可传给 [`VQESolver`](vqe.md#vqesolver)。

#### 方法

```python
minimize(objective_function, x0: np.ndarray) -> OptimizerResult
```

从 `x0` 出发最小化 `objective_function`。

- `objective_function`：待最小化的目标函数，接受参数数组、返回标量能量。
- `x0`：起始参数。

必须返回 [`OptimizerResult`](#optimizerresult)。

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

优化器的返回值。

| 字段 | 含义 |
| --- | --- |
| `success` | 是否收敛 |
| `x` | 最优参数 |
| `fun` | 最优目标函数值 |
| `nfev` | 目标函数求值次数 |
| `nit` | 迭代轮数 |
| `message` | 说明文本 |
| `trajectory` | 逐次能量记录 |

---

## 无梯度优化器

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

Nelder--Mead 单纯形搜索。不需要梯度，适合参数少、噪声低的场景。

`alpha` / `gamma` / `rho` / `sigma` 分别是反射、扩张、收缩、缩边系数。

### QuantumCoordinateDescent

```python
QuantumCoordinateDescent(max_iter: int = 50, tol: float = 1e-06)
```

坐标下降，面向**每个参数对应一个正弦频率**的目标函数（UCCSD 的能量对单个参数正是这种形式）。
逐坐标解析求解，不构造梯度。

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

同时扰动随机逼近（Simultaneous Perturbation Stochastic Approximation）。每次迭代只做两次
目标函数求值，适合**有采样噪声**的场景。

参数 `a` / `c` / `A` / `alpha` / `gamma` 控制步长与扰动幅度的衰减。

---

## 梯度类优化器

以下三个都使用**中心有限差分**估计梯度，因此每次迭代的目标函数求值次数随参数个数线性增长。

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

带自适应矩估计的梯度下降。

### AdagradOptimizer

```python
AdagradOptimizer(
    learning_rate: float = 0.01,
    epsilon: float = 1e-08,
    max_iter: int = 200,
    tol: float = 1e-06,
)
```

累积历史梯度平方的梯度下降。

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

有限差分梯度下降加重球动量。
