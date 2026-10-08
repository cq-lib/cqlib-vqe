# This code is part of cqlib.
#
# Copyright (C) 2025-2026 China Telecom Quantum Group.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Public API for cqlib-vqe."""
from __future__ import annotations

from .chemistry import (
    ActiveSpaceConfig,
    ActiveSpaceReport,
    CanonicalBasisAudit,
    MolecularDataEngine,
    SingletExcitation,
    canonical_parameter_count,
    canonical_singlet_descriptors,
    canonical_singlet_operator,
    encoded_occupied_qubits,
    estimate_frozen_core_orbitals,
    map_fermion_operator,
    normalize_mapper_type,
    pack_closed_shell_ccsd,
    select_active_space,
)
from .vqe import (
    AdaptiveRound,
    AdaptiveSelectedUCCSDResult,
    AdaptiveSelectedUCCSDSolver,
    AdaptiveSelectionConfig,
    CandidateGradient,
    CloudEnergyEstimator,
    DirectStatevectorEstimator,
    EnergyEstimator,
    FastStatevectorEstimator,
    NativeStatevectorEstimator,
    ParallelEnergyEstimator,
    TianyanCloudEnergyEstimator,
    TianyanEnergyEstimator,
    TianyanEnergyResult,
    TianyanGroupResult,
    TianyanMeasurementGroup,
    TianyanMeasurementPlan,
    TianyanSubmittedEvaluation,
    TianyanTermResult,
    UCCSDFactory,
    UCCSD_Factory,
    VQESolver,
)

__version__ = "0.1.0-beta.1"

__all__ = [
    "__version__",
    "ActiveSpaceConfig",
    "ActiveSpaceReport",
    "CanonicalBasisAudit",
    "MolecularDataEngine",
    "SingletExcitation",
    "canonical_parameter_count",
    "canonical_singlet_descriptors",
    "canonical_singlet_operator",
    "encoded_occupied_qubits",
    "estimate_frozen_core_orbitals",
    "map_fermion_operator",
    "normalize_mapper_type",
    "pack_closed_shell_ccsd",
    "select_active_space",
    "AdaptiveRound",
    "AdaptiveSelectedUCCSDResult",
    "AdaptiveSelectedUCCSDSolver",
    "AdaptiveSelectionConfig",
    "CandidateGradient",
    "CloudEnergyEstimator",
    "DirectStatevectorEstimator",
    "EnergyEstimator",
    "FastStatevectorEstimator",
    "NativeStatevectorEstimator",
    "ParallelEnergyEstimator",
    "TianyanCloudEnergyEstimator",
    "TianyanEnergyEstimator",
    "TianyanEnergyResult",
    "TianyanGroupResult",
    "TianyanMeasurementGroup",
    "TianyanMeasurementPlan",
    "TianyanSubmittedEvaluation",
    "TianyanTermResult",
    "UCCSDFactory",
    "UCCSD_Factory",
    "VQESolver",
]
