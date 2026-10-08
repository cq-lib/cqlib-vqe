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

from __future__ import annotations

import cqlib_vqe
from cqlib_vqe import chemistry, vqe


def test_canonical_package_metadata_and_exports():
    assert cqlib_vqe.__version__ == "0.1.0-beta.1"
    assert cqlib_vqe.UCCSDFactory is vqe.UCCSDFactory
    assert cqlib_vqe.MolecularDataEngine is chemistry.MolecularDataEngine
    assert cqlib_vqe.TianyanEnergyEstimator is vqe.TianyanEnergyEstimator


def test_canonical_submodules_share_implementations():
    from cqlib_vqe.chemistry.active_space import ActiveSpaceConfig
    from cqlib_vqe.vqe.factory import UCCSDFactory
    from cqlib_vqe.vqe.tianyan import TianyanEnergyEstimator

    assert ActiveSpaceConfig is chemistry.ActiveSpaceConfig
    assert UCCSDFactory is vqe.UCCSDFactory
    assert TianyanEnergyEstimator is vqe.TianyanEnergyEstimator
