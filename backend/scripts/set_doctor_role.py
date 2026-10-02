import argparse
from typing import Any

from firebase_admin import auth

from app.firebase import get_firebase_app


def with_doctor_role(existing_claims: dict[str, Any] | None) -> dict[str, Any]:
    claims = dict(existing_claims or {})
    claims["role"] = "doctor"
    return claims


def assign_doctor_role(email: str) -> str:
    app = get_firebase_app()
    user = auth.get_user_by_email(email, app=app)
    auth.set_custom_user_claims(
        user.uid,
        with_doctor_role(user.custom_claims),
        app=app,
    )
    return user.uid


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Assign TwinBean's trusted doctor custom claim."
    )
    parser.add_argument("--email", required=True, help="Existing Firebase user email")
    args = parser.parse_args()
    uid = assign_doctor_role(args.email)
    print(f"Doctor role assigned to {args.email} ({uid}).")
    print("The user must sign out and back in, or force-refresh their ID token.")


if __name__ == "__main__":
    main()
