import pytest
from pydantic import ValidationError

from app.schemas import WhatsAppOnboardingComplete


@pytest.mark.parametrize("value", ["13999990000", "13 99999-0000", "+55 (13) 99999-0000", "5513999990000"])
def test_onboarding_normalizes_brazilian_phone_numbers(value: str) -> None:
    payload = WhatsAppOnboardingComplete(state="state", waba_id="waba-123", phone_number=value)

    assert payload.phone_number == "+5513999990000"


def test_onboarding_keeps_local_number_with_ddd_55() -> None:
    payload = WhatsAppOnboardingComplete(state="state", waba_id="waba-123", phone_number="55999990000")

    assert payload.phone_number == "+5555999990000"


def test_onboarding_rejects_invalid_brazilian_phone_number() -> None:
    with pytest.raises(ValidationError):
        WhatsAppOnboardingComplete(state="state", waba_id="waba-123", phone_number="139999")
