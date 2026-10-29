from django.conf import settings
from twilio.rest import Client


class PhoneVerificationConfigurationError(Exception):
	pass


def _twilio_verify_service():
	credentials = (
		settings.TWILIO_ACCOUNT_SID,
		settings.TWILIO_AUTH_TOKEN,
		settings.TWILIO_VERIFY_SERVICE_SID,
	)
	if not all(credentials):
		raise PhoneVerificationConfigurationError
	client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
	return client.verify.v2.services(settings.TWILIO_VERIFY_SERVICE_SID)


def send_phone_verification_code(phone_number):
	_twilio_verify_service().verifications.create(to=phone_number, channel='sms')


def verify_phone_verification_code(phone_number, code):
	verification = _twilio_verify_service().verification_checks.create(
		to=phone_number,
		code=code,
	)
	return verification.status == 'approved'