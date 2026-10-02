from scripts.set_doctor_role import with_doctor_role


def test_doctor_role_preserves_unrelated_claims() -> None:
    assert with_doctor_role({"tenant": "demo"}) == {
        "tenant": "demo",
        "role": "doctor",
    }


def test_doctor_role_can_start_from_no_claims() -> None:
    assert with_doctor_role(None) == {"role": "doctor"}
