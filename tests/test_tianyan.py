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

from dataclasses import dataclass

import pytest

from cqlib import Circuit
from cqlib_vqe.vqe.tianyan import TianyanEnergyEstimator


@dataclass(frozen=True)
class FakeQubit:
    index: int


class FakeExecutionResult:
    def __init__(self, task_id, counts, qubits, probabilities=None):
        self.task_id = task_id
        self.counts = dict(counts)
        self.probabilities = probabilities
        self.qubits = [FakeQubit(q) for q in qubits]
        self.shots = sum(self.counts.values())


class FakeTask:
    def __init__(self, task_ids, results):
        self.task_ids = list(task_ids)
        self._results = list(results)
        self.wait_args = None

    def wait(self, timeout_secs, poll_interval_secs=5.0):
        self.wait_args = (timeout_secs, poll_interval_secs)
        return list(self._results)


class FakeBackend:
    name = "tianyan-test"
    num_qubits = 20

    def __init__(self, result_factory=None):
        self.result_factory = result_factory
        self.calls = []
        self.last_task = None

    def run_with_mode(self, circuits, shots, mode="auto"):
        self.calls.append((list(circuits), shots, mode))
        task_ids = [f"task-{i}" for i in range(len(circuits))]
        if self.result_factory is None:
            results = [
                FakeExecutionResult(task_id, {"0": shots}, [0])
                for task_id in task_ids
            ]
        else:
            results = self.result_factory(task_ids, circuits, shots)
        self.last_task = FakeTask(task_ids, results)
        return self.last_task


def test_prepare_groups_qwc_terms_and_skips_identity_submission():
    estimator = TianyanEnergyEstimator(FakeBackend(), 2, shots=1000)
    plan = estimator.prepare(
        Circuit(2),
        [
            ("II", 1.25),
            ("XI", 1.0),
            ("IX", 2.0),
            ("XX", -0.5),
            ("ZZ", 0.75),
        ],
    )

    assert plan.constant_energy == 1.25
    assert plan.num_pauli_terms == 4
    assert plan.num_measurement_circuits == 2
    assert any(group.master_pauli == "XX" and len(group.terms) == 3 for group in plan.groups)
    assert any(group.master_pauli == "ZZ" and len(group.terms) == 1 for group in plan.groups)


def test_grouping_none_submits_one_circuit_per_nonidentity_term():
    estimator = TianyanEnergyEstimator(FakeBackend(), 2, grouping="none")
    plan = estimator.prepare(
        Circuit(2),
        [("II", 0.1), ("XI", 1.0), ("IX", 2.0), ("XX", 3.0)],
    )
    assert plan.constant_energy == pytest.approx(0.1)
    assert plan.num_measurement_circuits == 3
    assert all(len(group.terms) == 1 for group in plan.groups)


def test_prepare_measures_only_group_support_and_remaps_physical_qubits():
    estimator = TianyanEnergyEstimator(
        FakeBackend(),
        2,
        physical_qubits=[5, 9],
        measure_only_support=True,
    )
    circuit = Circuit(2)
    circuit.h(0)
    circuit.cx(0, 1)

    plan = estimator.prepare(circuit, [("XI", 1.0)])
    assert plan.groups[0].measured_logical_qubits == (0,)
    assert plan.groups[0].measured_physical_qubits == (5,)
    script = plan.circuits[0]
    assert "CZ Q5 Q9" in script
    assert "CX Q5 Q9" not in script
    assert "H Q5" not in script
    assert "RZ Q5 3.141592653589793" in script
    assert "Y2P Q5" in script
    # Modified: match complete QCIS lines to avoid confusing Y2M with M.
    script_lines = script.splitlines()
    assert "M Q5" in script_lines
    assert "M Q9" not in script_lines


def test_strict_ordered_results_compute_energy_from_counts_only():
    def results(task_ids, circuits, shots):
        generated = []
        for task_id, script in zip(task_ids, circuits, strict=True):
            if "Y2M Q5" in script:
                generated.append(FakeExecutionResult(task_id, {"0": 250, "1": 750}, [5]))
            else:
                generated.append(FakeExecutionResult(task_id, {"0": 750, "1": 250}, [5]))
        return generated

    backend = FakeBackend(results)
    estimator = TianyanEnergyEstimator(
        backend,
        2,
        shots=1000,
        calibration_mode="disabled",
        physical_qubits=[5, 9],
        timeout_secs=123.0,
        poll_interval_secs=2.5,
    )
    energy = estimator.evaluate(Circuit(2), [("XI", 1.0), ("YI", 2.0)])

    assert energy == pytest.approx(-0.5)
    assert len(backend.calls) == 1
    assert backend.calls[0][1:] == (1000, "disabled")
    assert backend.last_task.wait_args == (123.0, 2.5)


def test_result_order_mismatch_is_exposed_not_repaired():
    def results(task_ids, circuits, shots):
        generated = [
            FakeExecutionResult(task_id, {"0": shots}, [0])
            for task_id in task_ids
        ]
        return list(reversed(generated))

    estimator = TianyanEnergyEstimator(FakeBackend(results), 1, grouping="none")
    with pytest.raises(RuntimeError, match="does not reorder results"):
        estimator.evaluate(Circuit(1), [("X", 1.0), ("Z", 1.0)])


def test_result_qubit_header_mismatch_is_exposed_not_repaired():
    def results(task_ids, circuits, shots):
        return [FakeExecutionResult(task_ids[0], {"0": shots}, [0])]

    estimator = TianyanEnergyEstimator(
        FakeBackend(results), 1, physical_qubits=[5]
    )
    with pytest.raises(RuntimeError, match="No fallback or synthetic-qubit repair"):
        estimator.evaluate(Circuit(1), [("Z", 1.0)])


def test_probability_only_result_is_not_accepted():
    def results(task_ids, circuits, shots):
        return [
            FakeExecutionResult(
                task_ids[0], {}, [0], probabilities={"0": 1.0}
            )
        ]

    estimator = TianyanEnergyEstimator(FakeBackend(results), 1)
    with pytest.raises(RuntimeError, match="empty counts map"):
        estimator.evaluate(Circuit(1), [("Z", 1.0)])


def test_missing_result_is_exposed_directly():
    def results(task_ids, circuits, shots):
        return [FakeExecutionResult(task_ids[0], {"0": shots}, [0])]

    estimator = TianyanEnergyEstimator(FakeBackend(results), 1, grouping="none")
    with pytest.raises(RuntimeError, match="different number of results"):
        estimator.evaluate(Circuit(1), [("X", 1.0), ("Z", 1.0)])


def test_identity_only_hamiltonian_never_submits_hardware_job():
    backend = FakeBackend()
    estimator = TianyanEnergyEstimator(backend, 2)
    result = estimator.evaluate_with_details(Circuit(2), [("II", -3.5)])
    assert result.energy == -3.5
    assert result.task_ids == ()
    assert backend.calls == []


def test_constructor_rejects_auto_calibration_and_invalid_grouping():
    with pytest.raises(ValueError, match="silently fall back"):
        TianyanEnergyEstimator(FakeBackend(), 1, calibration_mode="auto")
    with pytest.raises(ValueError, match="grouping"):
        TianyanEnergyEstimator(FakeBackend(), 1, grouping="magic")


def test_existing_measurement_in_base_circuit_is_rejected(monkeypatch):
    estimator = TianyanEnergyEstimator(FakeBackend(), 1)
    import cqlib_vqe.vqe.tianyan as module

    monkeypatch.setattr(module.qcis, "dumps", lambda circuit: "H Q0\nM Q0\n")
    with pytest.raises(ValueError, match="already contains measurement"):
        estimator.prepare(Circuit(1), [("Z", 1.0)])


def test_parity_uses_declared_result_qubit_order():
    probabilities = {"00": 0.25, "10": 0.75}
    value = TianyanEnergyEstimator._compute_physical_parity(
        probabilities,
        pauli="XI",
        measured_physical_qubits=(9, 5),
        logical_to_physical=(5, 9),
    )
    assert value == pytest.approx(-0.5)


def test_cloud_estimator_does_not_guess_new_backend_protocol():
    from cqlib_vqe.vqe.estimator import CloudEnergyEstimator

    with pytest.raises(TypeError, match="Use TianyanEnergyEstimator explicitly"):
        CloudEnergyEstimator(FakeBackend(), 1)


class FakeLegacyCloudBackend:
    def __init__(self):
        self.submissions = []

    def submit_experiment(self, *, circuit):
        self.submissions.append(list(circuit))
        return len(self.submissions) - 1

    def query_experiment(self, task_id):
        return [{"probability": {"0": 1.0}} for _ in self.submissions[task_id]]


def test_cloud_estimator_keeps_only_explicit_legacy_protocol():
    from cqlib_vqe.vqe.estimator import CloudEnergyEstimator

    backend = FakeLegacyCloudBackend()
    estimator = CloudEnergyEstimator(backend, 1)
    assert estimator.evaluate(Circuit(1), [("Z", 1.0)]) == 1.0
    assert len(backend.submissions) == 1


def test_from_credentials_strips_api_key(monkeypatch):
    observed = {}

    class FakePlatformInstance:
        def get_backend(self, name):
            assert name == "tianyan-test"
            return FakeBackend()

    class FakePlatform:
        @staticmethod
        def login(api_key, **kwargs):
            observed["api_key"] = api_key
            observed["kwargs"] = kwargs
            return FakePlatformInstance()

        @staticmethod
        def from_credentials(**kwargs):
            raise AssertionError("saved credentials path should not be used")

    import sys
    import types

    module = types.ModuleType("cqlib_tianyan")
    module.TianyanPlatform = FakePlatform
    monkeypatch.setitem(sys.modules, "cqlib_tianyan", module)

    estimator = TianyanEnergyEstimator.from_credentials(
        device_name="tianyan-test",
        n_qubits=1,
        api_key="  secret-token\r\n",
        save_credentials=False,
    )
    assert observed["api_key"] == "secret-token"
    assert observed["kwargs"] == {"save_credentials": False}
    assert estimator.device_name == "tianyan-test"


def test_from_credentials_rejects_blank_api_key(monkeypatch):
    import sys
    import types

    class FakePlatform:
        @staticmethod
        def login(api_key, **kwargs):
            raise AssertionError("login must not be called")

        @staticmethod
        def from_credentials(**kwargs):
            raise AssertionError("saved credentials path should not be used")

    module = types.ModuleType("cqlib_tianyan")
    module.TianyanPlatform = FakePlatform
    monkeypatch.setitem(sys.modules, "cqlib_tianyan", module)

    with pytest.raises(ValueError, match="whitespace-only"):
        TianyanEnergyEstimator.from_credentials(
            device_name="tianyan-test", n_qubits=1, api_key="  \r\n"
        )
