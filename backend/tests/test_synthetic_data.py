from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from app.synthetic_data import EhrEvent, IotObservation, generate_cohort
from app.clinical_rules import calculate_creatinine_rule


TIME_BASIS = datetime(2026, 1, 15, 12, 0, tzinfo=UTC)


def _serialized_cohort(seed: int) -> str:
    cohort = generate_cohort(
        seed=seed,
        generator_version="2026.1",
        time_basis=TIME_BASIS,
        patient_count=4,
    )
    return json.dumps(cohort.to_dict(), sort_keys=True, separators=(",", ":"))


def test_same_inputs_produce_byte_equivalent_stable_cohort() -> None:
    first = generate_cohort(41, "2026.1", TIME_BASIS, patient_count=4)
    second = generate_cohort(41, "2026.1", TIME_BASIS, patient_count=4)

    assert _serialized_cohort(41) == _serialized_cohort(41)
    assert first.to_dict() == second.to_dict()
    assert _serialized_cohort(41) != _serialized_cohort(42)
    assert all(patient.patient_id.startswith("tbp-") for patient in first.patients)
    assert all(event.event_id.startswith("ehr-") for event in first.ehr_events)
    assert all(observation.observation_id.startswith("iot-") for observation in first.iot_observations)
    assert all(record.event_time.tzinfo is UTC for record in first.ehr_events)
    assert all(record.observed_at.tzinfo is UTC for record in first.iot_observations)


def test_adult_ckd_patients_have_plausible_longitudinal_ehr_content() -> None:
    cohort = generate_cohort(77, "2026.1", TIME_BASIS, patient_count=3)

    assert all(patient.age >= 18 for patient in cohort.patients)
    assert all(patient.ckd_stage in {"G3a", "G3b", "G4"} for patient in cohort.patients)
    assert all("chronic kidney disease" in patient.ckd_context.lower() for patient in cohort.patients)
    for patient in cohort.patients:
        events = [event for event in cohort.ehr_events if event.patient_id == patient.patient_id]
        event_types = {event.event_type for event in events}
        assert {"encounter", "medication", "laboratory"} <= event_types
        laboratory_names = {
            str(event.data["test_name"])
            for event in events
            if event.event_type == "laboratory"
        }
        assert {"creatinine", "egfr", "bun", "potassium"} <= laboratory_names
        assert any(event.event_time <= TIME_BASIS for event in events)
        assert all(event.event_time >= TIME_BASIS - timedelta(days=210) for event in events)


def test_every_generated_record_has_explicit_synthetic_utc_provenance() -> None:
    cohort = generate_cohort(12, "2026.1", TIME_BASIS, patient_count=2)
    serialized = cohort.to_dict()

    assert cohort.provenance.synthetic is True
    assert cohort.provenance.generator_version == "2026.1"
    assert cohort.provenance.seed == 12
    assert cohort.provenance.time_basis == TIME_BASIS
    assert serialized["provenance"]["generated_at"].endswith("Z")
    for record in (*cohort.patients, *cohort.ehr_events, *cohort.iot_observations):
        assert record.synthetic is True
        assert record.generator_version == "2026.1"
        assert record.seed == 12
        assert record.source.startswith("twinbean-")


def test_iot_observations_are_independent_typed_home_measurements() -> None:
    cohort = generate_cohort(19, "2026.1", TIME_BASIS, patient_count=2)

    assert cohort.iot_observations
    assert all(isinstance(observation, IotObservation) for observation in cohort.iot_observations)
    assert not any(isinstance(observation, EhrEvent) for observation in cohort.iot_observations)
    assert all(observation.measurement_type in {"weight_kg", "blood_pressure", "heart_rate_bpm"} for observation in cohort.iot_observations)
    assert all(observation.source == "twinbean-simulated-iot" for observation in cohort.iot_observations)
    assert not hasattr(EhrEvent, "measurement_type")


def test_ehr_and_iot_streams_share_patients_and_an_aligned_utc_window() -> None:
    cohort = generate_cohort(31, "2026.1", TIME_BASIS, patient_count=5)
    patient_ids = {patient.patient_id for patient in cohort.patients}
    ehr_patient_ids = {event.patient_id for event in cohort.ehr_events}
    iot_patient_ids = {observation.patient_id for observation in cohort.iot_observations}
    ehr_times = [event.event_time for event in cohort.ehr_events]
    iot_times = [observation.observed_at for observation in cohort.iot_observations]

    assert ehr_patient_ids == patient_ids
    assert iot_patient_ids == patient_ids
    assert all(TIME_BASIS - timedelta(days=210) <= value <= TIME_BASIS for value in ehr_times)
    assert all(TIME_BASIS - timedelta(days=210) <= value <= TIME_BASIS for value in iot_times)
    assert max(min(ehr_times), min(iot_times)) <= min(max(ehr_times), max(iot_times))
    assert all(value.tzinfo is UTC for value in (*ehr_times, *iot_times))


def test_generated_ids_are_unique_and_input_contract_is_bounded() -> None:
    cohort = generate_cohort(29, "2026.1", TIME_BASIS, patient_count=6)
    identifiers = [
        *(patient.patient_id for patient in cohort.patients),
        *(event.event_id for event in cohort.ehr_events),
        *(observation.observation_id for observation in cohort.iot_observations),
    ]

    assert len(identifiers) == len(set(identifiers))
    with pytest.raises(ValueError, match="patient_count"):
        generate_cohort(1, "2026.1", TIME_BASIS, patient_count=0)
    with pytest.raises(ValueError, match="generator_version"):
        generate_cohort(1, "", TIME_BASIS)
    with pytest.raises(ValueError, match="UTC"):
        generate_cohort(1, "2026.1", datetime(2026, 1, 15, 12, 0))


def test_terminal_observations_are_deterministic_and_cutoff_safe() -> None:
    cohort = generate_cohort(53, "2026.2", TIME_BASIS, patient_count=4)
    cutoff = TIME_BASIS - timedelta(hours=24)

    terminal_events = [
        event
        for event in cohort.ehr_events
        if event.event_type == "laboratory"
        and event.data.get("test_name") == "creatinine"
        and cutoff - timedelta(days=7) <= event.event_time <= cutoff + timedelta(hours=24)
    ]
    terminal_blood_pressures = [
        observation
        for observation in cohort.iot_observations
        if observation.measurement_type == "blood_pressure" and observation.observed_at == cutoff
    ]

    assert len(terminal_events) == len(cohort.patients) * 9
    assert len(terminal_blood_pressures) == len(cohort.patients)
    assert all(event.event_time <= TIME_BASIS for event in terminal_events)
    assert all(observation.data["unit"] == "mmHg" for observation in terminal_blood_pressures)
    assert _serialized_cohort(53) == _serialized_cohort(53)


def test_terminal_trajectories_derive_both_label_classes_without_persisted_labels() -> None:
    cohort = generate_cohort(59, "2026.2", TIME_BASIS, patient_count=6)
    cutoff = TIME_BASIS - timedelta(hours=24)
    statuses_at_cutoff = {}
    statuses_after_cutoff = {}

    for patient in cohort.patients:
        history = [event for event in cohort.ehr_events if event.patient_id == patient.patient_id]
        statuses_at_cutoff[patient.patient_id] = calculate_creatinine_rule(history, cutoff).status
        statuses_after_cutoff[patient.patient_id] = calculate_creatinine_rule(history, TIME_BASIS).status

    assert set(statuses_at_cutoff.values()) == {"criteria_not_met"}
    assert "criteria_met" in statuses_after_cutoff.values()
    assert "criteria_not_met" in statuses_after_cutoff.values()
    for event in cohort.ehr_events:
        assert "outcome" not in event.data
        assert "label" not in event.data
        assert "scenario" not in event.data
