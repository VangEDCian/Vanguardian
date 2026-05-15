import phonenumbers

from apps.identity.application.exceptions import PhoneNumberValidationError


class PhoneNumberValidator:
    default_region = "VN"
    expected_region = "VN"

    def validate(self, value):
        normalized_value = (value or "").strip()
        if not normalized_value:
            return ""

        parsed_number = self._parse(normalized_value)
        self._validate_with_phonenumbers(parsed_number)
        self.validate_for_vietnamese(parsed_number)

        return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.E164)

    def _parse(self, value):
        try:
            return phonenumbers.parse(value, self.default_region)
        except phonenumbers.NumberParseException as exc:
            raise PhoneNumberValidationError("Invalid phone number format.") from exc

    @staticmethod
    def _validate_with_phonenumbers(parsed_number):
        if not phonenumbers.is_possible_number(parsed_number):
            raise PhoneNumberValidationError("Phone number has an invalid length or structure.")
        if not phonenumbers.is_valid_number(parsed_number):
            raise PhoneNumberValidationError("Phone number is not valid.")

    def validate_for_vietnamese(self, parsed_number):
        region_code = (phonenumbers.region_code_for_number(parsed_number) or "").upper()
        if region_code != self.expected_region:
            raise PhoneNumberValidationError("Phone number must be a valid Vietnamese number.")


__all__ = ["PhoneNumberValidationError", "PhoneNumberValidator"]
