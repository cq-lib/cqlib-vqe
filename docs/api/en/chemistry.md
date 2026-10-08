# cqlib_vqe.chemistry

`cqlib_vqe.chemistry` handles the molecular preprocessing: the
electronic-structure calculation from the molecular geometry, the active-space
selection, the mapping of fermionic operators onto qubits, and the generation of the
canonical singlet-UCCSD excitation generators and packed amplitudes.

Most entry points in this subpackage require **OpenFermion** and **PySCF** (install
`cqlib-vqe[chemistry]`). They raise `ImportError` when the dependency is missing.

## Overview

| Name | Type | Description |
| --- | --- | --- |
| [`MolecularDataEngine`](#moleculardataengine) | Class | Primary molecular-preprocessing entry point: geometry → Hamiltonian + UCCSD data |
| [`ActiveSpaceConfig`](#activespaceconfig) | Class | Active-space policy configuration |
| [`ActiveSpaceReport`](#activespacereport) | Class | Active-space selection report |
| [`select_active_space`](#select-active-space) | Function | Determines the active space from a configuration and returns the report |
| [`estimate_frozen_core_orbitals`](#estimate-frozen-core-orbitals) | Function | Estimates the conventional frozen-core orbital count |
| [`normalize_mapper_type`](#normalize-mapper-type) | Function | Normalizes the mapping name |
| [`map_fermion_operator`](#map-fermion-operator) | Function | Transforms a fermionic operator with the specified mapping |
| [`encoded_occupied_qubits`](#encoded-occupied-qubits) | Function | Encodes the fermionic occupation into occupied qubits |
| [`canonical_singlet_descriptors`](#canonical-singlet-descriptors) | Function | Returns excitation-generator descriptors in packed order |
| [`canonical_singlet_operator`](#canonical-singlet-operator) | Function | Returns a single one-hot anti-Hermitian generator |
| [`canonical_parameter_count`](#canonical-parameter-count) | Function | The canonical singlet-UCCSD parameter count |
| [`pack_closed_shell_ccsd`](#pack-closed-shell-ccsd) | Function | Packs CCSD amplitudes into canonical singlet order |
| [`SingletExcitation`](#singletexcitation) | Class | A single excitation descriptor |
| [`CanonicalBasisAudit`](#canonicalbasisaudit) | Class | Orthogonality-audit result for the packing procedure |

---

## Molecular preprocessing

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

Prepares a closed-shell active-space Hamiltonian and canonical UCCSD data.

Construction only validates parameters and stores the configuration; **the calculation
happens in [`run()`](#moleculardataengine-run)**.

Parameters:

- `geometry`: the atomic geometry, each entry is `(element_symbol, (x, y, z))`.
- `basis`: the basis-set name, `"sto-3g"` by default.
- `multiplicity`: the spin multiplicity. **Only `1` is currently supported** (closed-shell singlet); other values raise `NotImplementedError`.
- `charge`: the molecular charge.
- `mapper_type`: `"jw"`, `"bk"`, or `"parity"`; see [`normalize_mapper_type`](#normalize-mapper-type).
- `occupied_indices` / `active_indices`: manually specify the frozen occupied orbitals and the active orbitals.
- `excitation_threshold`: the selection threshold for excitation generators.
- `active_space`: the active-space configuration; accepts an [`ActiveSpaceConfig`](#activespaceconfig) instance or a mode-name string.

(moleculardataengine-run)=
#### run

```python
run(*, run_fci: bool = True, audit_ccsd_basis: bool = True) -> MolecularDataEngine
```

Runs the electronic-structure calculation and returns `self`, so it can be written as
`MolecularDataEngine(...).run()`.

Parameters:

- `run_fci`: whether to also compute the FCI reference energy.
- `audit_ccsd_basis`: whether to run the orthogonality audit on the canonical-basis packing of the CCSD amplitudes.

Attributes available after `run()`:

| Attribute | Meaning |
| --- | --- |
| `n_qubits` | Number of qubits after mapping |
| `n_spin_orbitals` | Number of spin orbitals |
| `n_electrons` | Number of electrons |
| `nuclear_repulsion` | Nuclear repulsion energy |
| `hf_energy` | Hartree-Fock energy |
| `hamiltonian_data` | The mapped Pauli Hamiltonian, passed directly to [`VQESolver`](vqe.md#vqesolver) |
| `reference_energies` | Reference energies (including FCI when `run_fci=True`) |
| `active_space_report` | The active-space report, see [`ActiveSpaceReport`](#activespacereport) |
| `ccsd_parameters` | The packed CCSD amplitudes |
| `ccsd_packing_report` | The packing audit result, see [`CanonicalBasisAudit`](#canonicalbasisaudit) |
| `initial_occupied_qubits` | The initial occupied qubits after mapping |
| `initial_bitstring` | The reference-state bitstring |

#### Other methods

```python
candidate_packed_indices(minimum_amplitude: float = 0.0) -> list[int]
ccsd_amplitude_map() -> dict[int, float]
ccsd_items(packed_indices: Sequence[int] | None = None) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]
```

- `candidate_packed_indices`: returns the packed indices whose amplitude magnitude is not less than `minimum_amplitude`. **This implements "operators with a zero initial amplitude remain in the candidate pool"** — the default threshold `0.0` does not exclude zero-amplitude operators.
- `ccsd_amplitude_map`: returns the `{packed index: amplitude}` mapping.
- `ccsd_items`: returns the lists of single- and double-excitation entries, for inspection or external consumption.

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

Active-space policy configuration. A frozen `dataclass`; it cannot be modified after
construction.

Construct it with the static methods rather than by passing `mode` directly:

```python
ActiveSpaceConfig.full()          # 保留全部轨道空间（mode="full", freeze_core=False）
ActiveSpaceConfig.automatic(...)  # 确定性自动选择
ActiveSpaceConfig.manual()        # 手工指定（mode="manual"）
```

The signature of `automatic`:

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

#### Methods

- `validate() -> None`: validates the configuration. Raises `ValueError` when `mode` is not one of the three values, or when `max_active_qubits` is not positive or is odd.

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

The complete report of an active-space selection. Its fields record the orbital and
electron counts before and after the selection, the frozen/active/excluded orbital
indices, and a `selection_reason` explaining why the selection was made.

**This report should be recorded with every numerical result**, because it fixes the
simulated Hamiltonian and parameter pool.

---

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

Determines the active space from a configuration and returns the complete report. This
is a deterministic function: identical inputs give an identical report.

---

### estimate_frozen_core_orbitals

```python
estimate_frozen_core_orbitals(symbols: Iterable[str]) -> int
```

Estimates the conventional frozen-core spatial-orbital count from the element symbols.

---

## Mappings

### normalize_mapper_type

```python
normalize_mapper_type(mapper_type: str) -> MapperType
```

Normalizes a mapping name into the form accepted by the VQE workflow. Case-insensitive.
Unrecognized names raise `ValueError`.

### map_fermion_operator

```python
map_fermion_operator(fermion_operator, *, mapper_type: str, n_spin_orbitals: int)
```

Transforms a `FermionOperator` with the specified mapping.

### encoded_occupied_qubits

```python
encoded_occupied_qubits(
    *, n_spin_orbitals: int, occupied_spin_orbitals: Iterable[int], mapper_type: str
) -> tuple[int, ...]
```

Encodes the fermionic occupation vector as the indices of the "occupied qubits".

> Under the BK and parity mappings, the reference-state bit pattern is **not in general
> characterized by its Hamming weight alone**. Do not replace the factory reference
> construction with a JW occupancy shortcut.

---

## Canonical singlet-UCCSD

This group of functions implements the "packed order": it arranges the single and double
excitations into a stable parameter sequence, so that the CCSD amplitudes, the
generators, and the circuit parameters correspond one to one.

### canonical_singlet_descriptors

```python
canonical_singlet_descriptors(n_qubits: int, n_electrons: int) -> list[SingletExcitation]
```

Returns the descriptor list in OpenFermion's packed singlet-UCCSD order.

### canonical_singlet_operator

```python
canonical_singlet_operator(packed_index: int, n_qubits: int, n_electrons: int)
```

Returns the `packed_index`-th one-hot anti-Hermitian OpenFermion singlet generator.

### canonical_parameter_count

```python
canonical_parameter_count(n_qubits: int, n_electrons: int) -> int
```

Returns the canonical singlet-UCCSD parameter count for the given qubit and electron
counts. It is computed from the number of occupied-virtual orbital pairs, which is
determined by the closed-shell occupied-orbital and virtual-orbital counts.

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

Packs the CCSD single and double amplitudes into canonical singlet order.

Returns a triple: the descriptor list, the packed amplitude array, and the audit result.

Requires OpenFermion; raises `ImportError` when it is missing.

Parameters:

- `atol`: the absolute tolerance for deciding whether an amplitude is negligible.
- `audit`: whether to run the canonical-basis audit. When it is disabled, the third return value is still produced, but `audited` is false.

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

A single excitation descriptor. `kind` distinguishes single from double excitations;
`pair_b` has a value only for double excitations.

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

Orthogonality-audit result for the canonical-basis packing. A `rank` that differs from
`parameter_count` indicates that the packed basis is incomplete.
