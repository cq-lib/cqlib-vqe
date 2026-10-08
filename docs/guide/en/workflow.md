# Molecular VQE workflow

This page walks through the complete chain of a molecular electronic-structure VQE: molecular geometry → active space → Hamiltonian → UCCSD ansatz → energy optimization, together with mapping choice, execution mode, the adaptive operator pool, and Tianyan execution.

The chemistry parts of this page require the `chemistry` variant (`pip install -e ".[chemistry]"`).

## End-to-end flow

The chain has four steps:

1. Perform electronic-structure preprocessing with [`MolecularDataEngine`](../../api/en/chemistry.md#moleculardataengine);
2. Construct the ansatz with [`UCCSDFactory`](../../api/en/vqe.md#uccsdfactory);
3. Choose an [energy estimator](../../api/en/vqe.md);
4. Run the optimization with [`VQESolver`](../../api/en/vqe.md#vqesolver).

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

`MolecularDataEngine(...).run()` returns the engine itself, so calls can be chained. After `run()` the engine exposes attributes such as `n_qubits`, `n_electrons`, `hamiltonian_data`, and `reference_energies`; the complete list is in [`MolecularDataEngine`](../../api/en/chemistry.md#moleculardataengine).

The maintained H2 example:

```bash
python examples/h2_vqe_cqlib2.py
```

## Choosing a mapping

`mapper_type` accepts `"jw"` (Jordan-Wigner), `"bk"` (Bravyi-Kitaev), or `"parity"`:

```python
molecule = MolecularDataEngine(
    geometry=[('H', (0.0, 0.0, 0.0)), ('H', (0.0, 0.0, 0.735))],
    basis='sto-3g',
    mapper_type='bk',
).run()
```

The selected mapping is applied **consistently** to three places: the molecular Hamiltonian, the UCCSD excitation generators, and the Hartree-Fock reference state.

> In BK and parity encodings, the reference bit pattern cannot in general be characterized by its Hamming weight alone.
> **Do not replace the factory reference construction with a JW occupancy shortcut.**

## Active space

For larger systems, set an explicit active-space policy before running the molecule engine. The qubit budget must be positive and even.

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

Use `ActiveSpaceConfig.full()` to retain the full orbital space.

> **The active space report should be recorded with every numerical result** because it fixes the simulated Hamiltonian and parameter pool.
> The report fields are documented in [`ActiveSpaceReport`](../../api/en/chemistry.md#activespacereport).

## Execution mode and construction mode

### execution_mode

| Value | When to use |
| --- | --- |
| `"auto"` | **Recommended local default.** Prefers the available native Pauli direct-statevector path, including for factories with `construction_mode="bind"`; see below for the fallback order |
| `"circuit"` | When a circuit-oriented estimator is required, for example a cloud estimator |
| `"direct_statevector"` | Only when both `factory.build_statevector(...)` and `estimator.evaluate_parameters(...)` are available |

### construction_mode

| Value | Behavior |
| --- | --- |
| `"jit"` | Builds numeric circuits for repeated evaluation |
| `"bind"` | Keeps a symbolic template. Used when the target execution path benefits from parameter binding |

`execution_mode="auto"` first checks the native Pauli direct-statevector path. If
`factory.native_pauli_rotation_available` is true and both `factory.build_statevector(...)` and
`estimator.evaluate_parameters(...)` are available, it selects `"direct_statevector"`, even when
the factory uses `construction_mode="bind"`.

If those conditions are not met, a `"bind"` factory uses circuit execution with parameters bound
through cqlib2's `assign_parameters`. Other factories still use `"direct_statevector"` if both
methods above are available, and otherwise use circuit execution. Set
`execution_mode="circuit"` to explicitly use parameter-bound circuits.

## Adaptive selected-UCCSD

The adaptive solver initializes an ansatz from canonical CCSD amplitudes and then scans the **complete** remaining canonical operator pool, ranking candidates by their measured energy gradients.

**Candidates with a zero initial CCSD amplitude are not removed** and still take part in the ranking; this is the most important difference from pre-filtering operators by CCSD amplitude.

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

The returned [`AdaptiveSelectedUCCSDResult`](../../api/en/vqe.md#adaptiveselecteduccsdresult) contains the per-round records (`rounds`), the final selected operator set (`selected_packed_indices`), the stop reason (`stop_reason`), and whether the target precision was reached (`precision_certified`).

The multi-molecule end-to-end runner:

```bash
python examples/run_five_adaptive_full_pool.py h2 \
  --output-dir run_outputs/h2_adaptive \
  --pool-rounds 2 \
  --maxiter 80
```

The output directory contains per-molecule logs and JSON records, plus a CSV and JSON summary. The runner accepts `h2`, `h4`, `lih`, `beh2`, and `h2o`; omit the positional molecule list to run all five. Use `--active-space-policy full` only when the full orbital space is intended and the available resources are adequate.

## Tianyan execution

> Tianyan submits **real measurement tasks and consumes platform credits**. Credentials are configured outside version control.

First verify the interface and the backend names:

```bash
export TIANYAN_API_KEY='YOUR_API_KEY'
python tools/check_tianyan_api.py --online
```

Then select a backend and a physical-qubit mapping. The mapping is ordered from logical qubits to physical qubits and must contain exactly `n_qubits` entries:

```bash
export TIANYAN_DEVICE='BACKEND_NAME'
export TIANYAN_PHYSICAL_QUBITS='0,1,2,3'
export TIANYAN_SHOTS=2000
export TIANYAN_MAXITER=10
export TIANYAN_CALIBRATION=disabled
python -u examples/h2_vqe_tianyan.py
```

[`TianyanEnergyEstimator`](../../api/en/vqe.md#tianyanenergyestimator) groups qubit-wise commuting Pauli terms before submission and validates task ordering, measured qubit headers, and count payloads on return.

> The estimator **does not infer routing or silently repair backend metadata**.

**Never commit API keys, credential files, or raw cloud output that contains account information.**

## Useful entry points

| Task | Command |
| --- | --- |
| Minimal precompiled VQE | `python examples/minimal_compiled_smoke.py` |
| Local H2 UCCSD-VQE | `python examples/h2_vqe_cqlib2.py` |
| Adaptive H2 workflow | `python examples/run_five_adaptive_full_pool.py h2` |
| Tianyan interface check | `python tools/check_tianyan_api.py --online` |
| Full test suite | `pytest -q` |
