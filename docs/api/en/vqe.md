# cqlib_vqe.vqe

`cqlib_vqe.vqe` covers the execution side of VQE: circuit factories, energy estimators, the
classical optimization loop, adaptive operator-pool growth, and measurement submission to the
Tianyan platform.

Local estimators depend only on cqlib 2.x; the Tianyan entry points require `cqlib-tianyan`
(install `cqlib-vqe[tianyan]`).

## Overview

| Name | Type | Summary |
| --- | --- | --- |
| [`VQESolver`](#vqesolver) | Class | Coordinates the factory, the estimator, and the classical optimizer |
| [`UCCSDFactory`](#uccsdfactory) | Class | Spin-adapted selected-UCCSD factory |
| [`UCCSD_Factory`](#uccsd-factory) | Class | Alias of `UCCSDFactory` (the same object) |
| [`NativeStatevectorEstimator`](#nativestatevectorestimator) | Class | Exact local estimator using the cqlib2 QIS API |
| [`DirectStatevectorEstimator`](#directstatevectorestimator) | Class | Fused path with direct statevector output from the factory |
| [`FastStatevectorEstimator`](#faststatevectorestimator) | Class | Backward-compatible name |
| [`EnergyEstimator`](#energyestimator) | Class | Sampling-based estimator |
| [`ParallelEnergyEstimator`](#parallelenergyestimator) | Class | Parallel QWC sampling |
| [`CloudEnergyEstimator`](#cloudenergyestimator) | Class | Compatibility name for the pre-cqlib-2.0 cloud API |
| [`AdaptiveSelectedUCCSDSolver`](#adaptiveselecteduccsdsolver) | Class | Adaptive solver with full-pool scans |
| [`AdaptiveSelectionConfig`](#adaptiveselectionconfig) | Class | Adaptive selection configuration |
| [`CandidateGradient`](#candidategradient) | Class | Gradient measurement result of a single candidate operator |
| [`AdaptiveRound`](#adaptiveround) | Class | State of one optimization round |
| [`AdaptiveSelectedUCCSDResult`](#adaptiveselecteduccsdresult) | Class | Complete result of an adaptive solve |
| [`TianyanEnergyEstimator`](#tianyanenergyestimator) | Class | QWC-grouped Tianyan energy estimator |
| [`TianyanCloudEnergyEstimator`](#tianyancloudenergyestimator) | Class | Alias of `TianyanEnergyEstimator` (the same object) |
| [`TianyanMeasurementPlan`](#tianyanmeasurementplan) | Class | Complete hardware circuits for one energy evaluation |
| [`TianyanMeasurementGroup`](#tianyanmeasurementgroup) | Class | One QWC group and its measurement metadata |
| [`TianyanSubmittedEvaluation`](#tianyansubmittedevaluation) | Class | Submitted plan and task handle |
| [`TianyanEnergyResult`](#tianyanenergyresult) | Class | Detailed result of a Tianyan evaluation |
| [`TianyanGroupResult`](#tianyangroupresult) | Class | Measurement result of a single QWC group |
| [`TianyanTermResult`](#tianyantermresult) | Class | Contribution of a single Pauli term |

---

## Solving

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

Coordinates the circuit factory, the energy estimator, and the classical optimizer.

`optimizer_method` accepts a SciPy optimizer name string, and also accepts an optimizer object
from [`cqlib_vqe.optim`](optim.md) or a custom optimizer instance.

Parameters:

- `factory`: circuit factory; it must implement the build interface, see [`UCCSDFactory`](#uccsdfactory).
- `estimator`: energy estimator, see [Energy estimators](#energy-estimators).
- `optimizer_method`: a SciPy method name such as `"COBYLA"`, or a custom optimizer object.
- `max_iter`: maximum number of iterations.
- `tol`: convergence tolerance.
- `execution_mode`: `"auto"`, `"circuit"`, or `"direct_statevector"`. See below.
- `optimizer_options`: extra options passed through to the optimizer.
- `warm_start`: `"none"` or `"gradient"`.
- `warm_start_*`: the three gradient warm-start parameters (step, backtracks, perturbation
  magnitude).

#### Execution mode

| Value | Behavior |
| --- | --- |
| `"auto"` | Recommended default. Prefers the native Pauli direct-statevector path when it and the required interfaces are available, even with `construction_mode="bind"`; otherwise selects the execution path in the order below |
| `"circuit"` | Forces circuit execution. Use it when a circuit-oriented estimator is required, for example a cloud estimator |
| `"direct_statevector"` | Use only when both `factory.build_statevector(...)` and `estimator.evaluate_parameters(...)` are available |

Raises `ValueError` for values outside the list above.

`"auto"` checks the following conditions in order:

1. If `factory.native_pauli_rotation_available` is true, the factory implements `build_statevector(...)`, and the estimator implements `evaluate_parameters(...)`, select `"direct_statevector"`.
2. Otherwise, if `construction_mode="bind"`, select `"circuit"` and bind parameters through cqlib2's `assign_parameters`.
3. Otherwise, if both methods above are available, select `"direct_statevector"`.
4. In all other cases, select `"circuit"`.

Set `execution_mode="circuit"` to explicitly use parameter-bound circuits.

> Under COBYLA this package uses a small chemical-scale initial trust-region radius, unless the caller
> specifies otherwise in `optimizer_options['rhobeg']`.

#### run

```python
run(
    hamiltonian_data,
    callback: Callable[[np.ndarray, float, int], None] | None = None,
    *,
    initial_params: Sequence[float] | None = None,
) -> dict[str, object]
```

Runs the optimization. The input circuit is not modified.

The returned dictionary contains the following keys:

| Key | Meaning |
| --- | --- |
| `optimal_value` | Optimal energy |
| `optimal_params` | Optimal parameters |
| `n_evals` | Number of objective-function evaluations (equal to `len(history)`) |
| `optimizer_n_evals` | The optimizer's own evaluation count |
| `n_iters` | Number of iterations |
| `time` | Wall-clock elapsed time (seconds) |
| `success` | Convergence flag reported by the optimizer |
| `message` | Message returned by the optimizer |
| `execution_mode` | Execution mode actually used |
| `history` | All energy records |
| `best_history` | Running best-energy records |
| `warm_start` | Warm-start execution report |
| `optimizer_options` | Optimizer options actually used for this run |

> `success=False` does not mean the result is wrong. When the evaluation budget is exhausted, the optimal value is still returned but `success=False` is reported.
> Production studies should increase `max_iter` and set an energy or parameter convergence criterion that fits the study.

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

Spin-adapted selected-UCCSD factory, supporting the JW, BK, and parity encodings.

`molecule_data` must provide the fields produced by [`MolecularDataEngine`](chemistry.md#moleculardataengine).

Parameters:

- `construction_mode`: `"jit"` builds numeric circuits for repeated evaluation; `"bind"` keeps a
  symbolic template and suits execution paths that benefit from parameter binding.
- `coefficient_threshold`: filtering threshold for generator coefficients.
- `trotter_steps` / `trotter_order`: the number of steps and the order of the Trotter expansion.
- `selected_packed_indices`: keep only the specified packed indices; `None` means all are used.

#### Static methods

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

Use this method to construct the factory when a Pauli-generator ansatz is already available and
molecular preprocessing is intentionally not part of the runtime.

Each generator is a list of `(pauli_string, coefficient)` terms. Pauli strings use the package's
`q0-left` order, **the leftmost character acts on qubit 0**.

#### Methods

```python
build(parameter_values: Sequence[float]) -> Circuit
build_statevector(parameter_values: Sequence[float]) -> Statevector
set_construction_mode(mode: str) -> None
```

- `build`: constructs the circuit from the parameters.
- `build_statevector`: constructs the statevector directly from the parameters. When this method
  exists, the `"auto"` mode of [`VQESolver`](#vqesolver) may select the fused path.
- `set_construction_mode`: switches the construction mode at runtime.

---

### UCCSD_Factory

`UCCSD_Factory` and `UCCSDFactory` are **the same object**:

```python
import cqlib_vqe
assert cqlib_vqe.UCCSD_Factory is cqlib_vqe.UCCSDFactory
```

It is retained only for compatibility with older spellings.

---

## Energy estimators

### NativeStatevectorEstimator

```python
NativeStatevectorEstimator(backend: Any = None, n_qubits: int | None = None) -> None
```

Exact local estimator using the cqlib2 QIS API.

#### Methods

```python
prepare_hamiltonian(hamiltonian_data, *, expected_num_qubits: int | None = None)
evaluate(circuit_or_state, hamiltonian_data) -> float
evaluate_statevector(state, hamiltonian_data) -> float
clear_cache() -> None
```

- `prepare_hamiltonian`: pre-computes the Hamiltonian representation. `expected_num_qubits` is used
  to validate that the qubit counts match.
- `evaluate`: accepts a circuit or a statevector and returns the expectation value.
- `evaluate_statevector`: accepts a statevector only.
- `clear_cache`: clears the internal cache.

### DirectStatevectorEstimator

```python
DirectStatevectorEstimator(backend: Any = None, n_qubits: int | None = None) -> None
```

**Fused parameter-to-energy path** targeting factories that implement `build_statevector`,
skipping circuit construction.

Under `execution_mode="auto"`, the native Pauli direct-statevector path takes priority when the
conditions above are met, including for factories with `construction_mode="bind"`. See
the execution-mode discussion above for the complete fallback order.

### FastStatevectorEstimator

```python
FastStatevectorEstimator(backend: Any = None, n_qubits: int | None = None) -> None
```

Backward-compatible name. **It inherits from [`NativeStatevectorEstimator`](#nativestatevectorestimator),
but it is not the same object** (`FastStatevectorEstimator is NativeStatevectorEstimator` is
`False`). New code should use the latter directly.

### EnergyEstimator

```python
EnergyEstimator(backend: ProbabilityBackend) -> None
```

Sampling-based estimator; the backend must provide `run(circuit) -> probs`.

### ParallelEnergyEstimator

```python
ParallelEnergyEstimator(backend: ProbabilityBackend, max_workers: int = 8) -> None
```

Parallel QWC sampling, targeting thread-safe C++ backends or remote backends.

### CloudEnergyEstimator

```python
CloudEnergyEstimator(backend: CloudBatchBackend, n_qubits: int, batch_size: int = 50) -> None
```

**Compatibility name for the pre-cqlib-2.0 cloud API only.** New Tianyan work should use
[`TianyanEnergyEstimator`](#tianyanenergyestimator).

---

## Adaptive selected-UCCSD

### AdaptiveSelectedUCCSDSolver

```python
AdaptiveSelectedUCCSDSolver(
    molecule_data,
    estimator,
    config: AdaptiveSelectionConfig | None = None,
)
```

Initializes the ansatz from canonical CCSD amplitudes, then scans the **complete** remaining
canonical operator pool, ranking candidates by their measured energy gradients and growing round
by round. **Candidates whose initial CCSD amplitude is zero are still retained in the pool**.

#### run

```python
run(
    *,
    reference_energy: float | None = None,
    round_callback: Callable[[AdaptiveRound], None] | None = None,
    optimizer_callback: Callable[[np.ndarray, float, int], None] | None = None,
) -> AdaptiveSelectedUCCSDResult
```

Parameters:

- `reference_energy`: reference energy, used to compute `reference_error` for each round.
- `round_callback`: callback invoked after each round.
- `optimizer_callback`: per-evaluation callback passed through to the internal VQE optimization.

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

Configuration for threshold-grown selected-UCCSD.

Key fields:

- `initial_amplitude_threshold`: amplitude threshold for operators included in the initial ansatz.
- `candidate_amplitude_threshold`: amplitude threshold for the candidate pool. **The default is
  `0.0`, that is, a candidate is not excluded because its amplitude is zero**.
- `pool_rounds`: number of full-pool scan rounds.
- `gradient_threshold` / `gradient_delta`: decision threshold and difference step for candidate
  gradients.
- `max_add_per_round` / `max_parameters` / `max_rounds`: growth limits.
- `target_energy_error`: target energy error used by the stopping criterion.

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

Gradient measurement result of a single candidate operator. `energy_plus` / `energy_minus` are the
energies on either side of the difference.

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

The state after one optimization round, together with the subsequent pool-scan result, if one was
performed.

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

Complete result of an adaptive solve. `stop_reason` explains why the solve stopped, and
`precision_certified` indicates whether `target_energy_error` was reached.

---

## Tianyan execution

Tianyan submits **real measurement tasks and consumes platform credits**. Credentials are
configured outside version control; before submitting, first confirm the backend name and the
physical-qubit mapping. The mapping runs from logical qubits to physical qubits and its length
must be exactly `n_qubits`.

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

QWC-grouped energy estimator for `cqlib_tianyan` backends. Before submission it groups Pauli terms
by the qubit-wise commuting relation; on return it validates task ordering, measured qubit
headers, and count payloads.

> This estimator **does not infer routing, and it does not silently repair backend metadata**.

(tianyanenergyestimator-methods)=
#### Methods

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

- `validate_backend_mapping`: validates the physical-qubit mapping and backend availability.
- `prepare` / `submit` / `collect`: split one energy evaluation into the three steps "assemble the
  plan", "submit", and "retrieve", so that submission and waiting can be separated.
- `evaluate`: convenience entry point that completes in one step and returns the energy.
- `evaluate_with_details`: the same, but returns the complete result object.
- `group_hamiltonian`: performs QWC grouping on the Hamiltonian.
- `clear_grouping_cache`: clears the grouping cache.

### TianyanCloudEnergyEstimator

Is **the same object** as [`TianyanEnergyEstimator`](#tianyanenergyestimator):

```python
import cqlib_vqe
assert cqlib_vqe.TianyanCloudEnergyEstimator is cqlib_vqe.TianyanEnergyEstimator
```

It is retained only for compatibility with older spellings.

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

All hardware circuits required for one VQE energy evaluation. `circuits` are the circuit texts to
be submitted, and `constant_energy` is the constant-term contribution that requires no
measurement.

### TianyanMeasurementGroup

```python
TianyanMeasurementGroup(
    master_pauli: str,
    terms: tuple[tuple[str, complex | float | int], ...],
    measured_logical_qubits: tuple[int, ...],
    measured_physical_qubits: tuple[int, ...],
) -> None
```

One QWC group and its corresponding hardware measurement metadata.

### TianyanSubmittedEvaluation

```python
TianyanSubmittedEvaluation(plan: TianyanMeasurementPlan, task: Any | None) -> None
```

A measurement plan and its corresponding Tianyan task handle. When `submit()` returns
`task=None`, `plan.circuits` is empty and no measurement circuits need to be submitted, for example
when the Hamiltonian contains only a constant term. No task is submitted to Tianyan;
`collect()` directly returns `plan.constant_energy` as the energy, with empty `groups` and
`task_ids`. This is a normal evaluation that requires no measurements, not a submission failure.

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

Detailed result returned by [`TianyanEnergyEstimator.evaluate_with_details`](#tianyanenergyestimator-methods).

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

Measurement result of a single QWC group.

### TianyanTermResult

```python
TianyanTermResult(
    pauli: str,
    coefficient: float,
    expectation: float,
    contribution: float,
) -> None
```

Expectation value of a single Pauli term and its contribution to the total energy
(`contribution = coefficient * expectation`).
