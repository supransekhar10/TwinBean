"""Pure, deterministic synthetic CKD data generation for TwinBean.

This module deliberately has no Firebase, filesystem, network, or system-clock
dependency.  Its only inputs are explicit generator settings.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from random import Random
from types import MappingProxyType
from typing import Mapping
from uuid import NAMESPACE_URL, uuid5


MAX_PATIENT_COUNT = 100
_CKD_STAGES = ("G3a", "G3b", "G4")
_SYNTHETIC_NAMES = (
    "Aarav Mehta", "Ananya Rao", "Arjun Nair", "Diya Sharma",
    "Ishaan Gupta", "Kavya Iyer", "Rohan Das", "Meera Kapoor",
    "Vikram Joshi", "Nisha Menon", "Aditya Kulkarni", "Sara Thomas",
    "Rahul Verma", "Priya Banerjee", "Neel Shah", "Aisha Khan",
    "Karan Patel", "Leela Krishnan", "Sanjay Bose", "Tara Reddy",
)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != timedelta(0):
        raise ValueError("time_basis must be timezone-aware UTC")
    return value.astimezone(UTC)


def _timestamp(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def _stable_id(prefix: str, *parts: object) -> str:
    name = ":".join(str(part) for part in parts)
    return f"{prefix}-{uuid5(NAMESPACE_URL, f'twinbean:{name}').hex}"


def _frozen_data(data: Mapping[str, object]) -> Mapping[str, object]:
    return MappingProxyType(dict(data))


def _serialize(value: object) -> object:
    if isinstance(value, datetime):
        return _timestamp(value)
    if isinstance(value, Mapping):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_serialize(item) for item in value]
    return value


@dataclass(frozen=True)
class CohortProvenance:
    synthetic: bool
    generator_version: str
    seed: int
    time_basis: datetime
    generated_at: datetime
    source: str = "twinbean-synthetic-generator"

    def to_dict(self) -> dict[str, object]:
        return {
            "synthetic": self.synthetic,
            "generator_version": self.generator_version,
            "seed": self.seed,
            "time_basis": _timestamp(self.time_basis),
            "generated_at": _timestamp(self.generated_at),
            "source": self.source,
        }


@dataclass(frozen=True)
class SyntheticPatient:
    patient_id: str
    display_name: str
    age: int
    sex: str
    ckd_stage: str
    ckd_context: str
    synthetic: bool
    generator_version: str
    seed: int
    source: str
    created_at: datetime

    def to_dict(self) -> dict[str, object]:
        return {
            "patient_id": self.patient_id,
            "display_name": self.display_name,
            "age": self.age,
            "sex": self.sex,
            "ckd_stage": self.ckd_stage,
            "ckd_context": self.ckd_context,
            "synthetic": self.synthetic,
            "generator_version": self.generator_version,
            "seed": self.seed,
            "source": self.source,
            "created_at": _timestamp(self.created_at),
        }


@dataclass(frozen=True)
class EhrEvent:
    event_id: str
    patient_id: str
    event_type: str
    event_time: datetime
    data: Mapping[str, object]
    synthetic: bool
    generator_version: str
    seed: int
    source: str

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "patient_id": self.patient_id,
            "event_type": self.event_type,
            "event_time": _timestamp(self.event_time),
            "data": _serialize(self.data),
            "synthetic": self.synthetic,
            "generator_version": self.generator_version,
            "seed": self.seed,
            "source": self.source,
        }


@dataclass(frozen=True)
class IotObservation:
    observation_id: str
    patient_id: str
    measurement_type: str
    observed_at: datetime
    data: Mapping[str, object]
    synthetic: bool
    generator_version: str
    seed: int
    source: str

    def to_dict(self) -> dict[str, object]:
        return {
            "observation_id": self.observation_id,
            "patient_id": self.patient_id,
            "measurement_type": self.measurement_type,
            "observed_at": _timestamp(self.observed_at),
            "data": _serialize(self.data),
            "synthetic": self.synthetic,
            "generator_version": self.generator_version,
            "seed": self.seed,
            "source": self.source,
        }


@dataclass(frozen=True)
class SyntheticCohort:
    provenance: CohortProvenance
    patients: tuple[SyntheticPatient, ...]
    ehr_events: tuple[EhrEvent, ...]
    iot_observations: tuple[IotObservation, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "provenance": self.provenance.to_dict(),
            "patients": [patient.to_dict() for patient in self.patients],
            "ehr_events": [event.to_dict() for event in self.ehr_events],
            "iot_observations": [observation.to_dict() for observation in self.iot_observations],
        }


def _lab_value(stage: str, test_name: str, random: Random) -> tuple[float, str]:
    ranges: dict[str, dict[str, tuple[float, float, str]]] = {
        "G3a": {
            "creatinine": (1.1, 1.7, "mg/dL"),
            "egfr": (46.0, 59.0, "mL/min/1.73m2"),
            "bun": (20.0, 32.0, "mg/dL"),
            "potassium": (3.7, 5.0, "mmol/L"),
        },
        "G3b": {
            "creatinine": (1.5, 2.3, "mg/dL"),
            "egfr": (31.0, 44.0, "mL/min/1.73m2"),
            "bun": (24.0, 40.0, "mg/dL"),
            "potassium": (3.8, 5.2, "mmol/L"),
        },
        "G4": {
            "creatinine": (2.2, 3.8, "mg/dL"),
            "egfr": (16.0, 29.0, "mL/min/1.73m2"),
            "bun": (30.0, 56.0, "mg/dL"),
            "potassium": (3.9, 5.4, "mmol/L"),
        },
    }
    lower, upper, unit = ranges[stage][test_name]
    return round(random.uniform(lower, upper), 2), unit


def _validate_patient(patient: SyntheticPatient) -> None:
    if not patient.patient_id.startswith("tbp-") or patient.age < 18:
        raise ValueError("patient must use a TwinBean adult identifier")
    if patient.ckd_stage not in _CKD_STAGES or "chronic kidney disease" not in patient.ckd_context.lower():
        raise ValueError("patient must include chronic kidney disease context")


def _validate_record(record: EhrEvent | IotObservation) -> None:
    if not record.synthetic or not record.source.startswith("twinbean-"):
        raise ValueError("all generated records must be explicitly synthetic TwinBean data")
    event_time = record.event_time if isinstance(record, EhrEvent) else record.observed_at
    _utc(event_time)


def generate_cohort(
    seed: int,
    generator_version: str,
    time_basis: datetime,
    patient_count: int = 12,
) -> SyntheticCohort:
    """Create an adult-only CKD cohort with an independent simulated IoT stream."""
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("seed must be an integer")
    if not isinstance(generator_version, str) or not generator_version.strip():
        raise ValueError("generator_version must be a non-empty string")
    if not 1 <= patient_count <= MAX_PATIENT_COUNT:
        raise ValueError(f"patient_count must be between 1 and {MAX_PATIENT_COUNT}")

    basis = _utc(time_basis)
    version = generator_version.strip()
    random = Random(seed)
    provenance = CohortProvenance(True, version, seed, basis, basis)
    patients: list[SyntheticPatient] = []
    ehr_events: list[EhrEvent] = []
    iot_observations: list[IotObservation] = []

    for index in range(patient_count):
        patient_id = _stable_id("tbp", version, seed, "patient", index)
        stage = _CKD_STAGES[random.randrange(len(_CKD_STAGES))]
        age = random.randint(42, 84)
        patient = SyntheticPatient(
            patient_id=patient_id,
            display_name=_SYNTHETIC_NAMES[index % len(_SYNTHETIC_NAMES)],
            age=age,
            sex=("female" if random.randrange(2) == 0 else "male"),
            ckd_stage=stage,
            ckd_context=f"Adult with chronic kidney disease stage {stage}; synthetic record.",
            synthetic=True,
            generator_version=version,
            seed=seed,
            source="twinbean-synthetic-ehr",
            created_at=basis - timedelta(days=210),
        )
        _validate_patient(patient)
        patients.append(patient)

        ehr_specs = (
            ("encounter", basis - timedelta(days=180), {"encounter_type": "nephrology follow-up"}),
            ("medication", basis - timedelta(days=165), {"medication": "lisinopril", "status": "active"}),
        )
        for event_index, (event_type, event_time, data) in enumerate(ehr_specs):
            event = EhrEvent(
                event_id=_stable_id("ehr", version, seed, patient_id, event_type, event_index),
                patient_id=patient_id,
                event_type=event_type,
                event_time=event_time,
                data=_frozen_data(data),
                synthetic=True,
                generator_version=version,
                seed=seed,
                source="twinbean-synthetic-ehr",
            )
            _validate_record(event)
            ehr_events.append(event)

        for month in range(6):
            lab_time = basis - timedelta(days=30 * (6 - month))
            for lab_index, test_name in enumerate(("creatinine", "egfr", "bun", "potassium")):
                value, unit = _lab_value(stage, test_name, random)
                event = EhrEvent(
                    event_id=_stable_id("ehr", version, seed, patient_id, "lab", month, lab_index),
                    patient_id=patient_id,
                    event_type="laboratory",
                    event_time=lab_time,
                    data=_frozen_data({"test_name": test_name, "value": value, "unit": unit}),
                    synthetic=True,
                    generator_version=version,
                    seed=seed,
                    source="twinbean-synthetic-ehr",
                )
                _validate_record(event)
                ehr_events.append(event)

        for week in range(8):
            observed_at = basis - timedelta(days=7 * (8 - week))
            observation_specs = (
                ("weight_kg", {"value": round(random.uniform(55.0, 110.0), 1), "unit": "kg"}),
                (
                    "blood_pressure",
                    {
                        "systolic": random.randint(108, 158),
                        "diastolic": random.randint(64, 94),
                        "unit": "mmHg",
                    },
                ),
                ("heart_rate_bpm", {"value": random.randint(56, 96), "unit": "bpm"}),
            )
            for observation_index, (measurement_type, data) in enumerate(observation_specs):
                observation = IotObservation(
                    observation_id=_stable_id("iot", version, seed, patient_id, week, observation_index),
                    patient_id=patient_id,
                    measurement_type=measurement_type,
                    observed_at=observed_at,
                    data=_frozen_data(data),
                    synthetic=True,
                    generator_version=version,
                    seed=seed,
                    source="twinbean-simulated-iot",
                )
                _validate_record(observation)
                iot_observations.append(observation)

        # `time_basis` remains the inclusive upper record bound.  The explicit
        # cutoff is one day earlier, so a terminal creatinine at `basis` is an
        # ordinary post-cutoff observation rather than an embedded outcome.
        terminal_cutoff = basis - timedelta(hours=24)
        terminal_baseline = {
            "G3a": 1.35,
            "G3b": 1.85,
            "G4": 2.75,
        }[stage] + ((seed + index) % 5) * 0.01
        worsening_trajectory = index % 2 == 1
        for terminal_index, days_from_cutoff in enumerate(range(-7, 2)):
            event_time = terminal_cutoff + timedelta(days=days_from_cutoff)
            value = terminal_baseline
            if days_from_cutoff == 1:
                value += 0.30 if worsening_trajectory else 0.05
            event = EhrEvent(
                event_id=_stable_id(
                    "ehr", version, seed, patient_id, "terminal-creatinine", terminal_index
                ),
                patient_id=patient_id,
                event_type="laboratory",
                event_time=event_time,
                data=_frozen_data(
                    {"test_name": "creatinine", "value": round(value, 2), "unit": "mg/dL"}
                ),
                synthetic=True,
                generator_version=version,
                seed=seed,
                source="twinbean-synthetic-ehr",
            )
            _validate_record(event)
            ehr_events.append(event)

        terminal_blood_pressure = IotObservation(
            observation_id=_stable_id("iot", version, seed, patient_id, "terminal-blood-pressure"),
            patient_id=patient_id,
            measurement_type="blood_pressure",
            observed_at=terminal_cutoff,
            data=_frozen_data(
                {
                    "systolic": 118 + ((seed + index * 7) % 31),
                    "diastolic": 72 + ((seed + index * 3) % 13),
                    "unit": "mmHg",
                }
            ),
            synthetic=True,
            generator_version=version,
            seed=seed,
            source="twinbean-simulated-iot",
        )
        _validate_record(terminal_blood_pressure)
        iot_observations.append(terminal_blood_pressure)

    identifiers = [
        *(patient.patient_id for patient in patients),
        *(event.event_id for event in ehr_events),
        *(observation.observation_id for observation in iot_observations),
    ]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("generated identifiers must be unique")
    return SyntheticCohort(provenance, tuple(patients), tuple(ehr_events), tuple(iot_observations))
