import re

from django.conf import settings
from django.contrib import auth
from django.contrib.auth import authenticate, login
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from twilio.base.exceptions import TwilioException

from .models import User
from .services import PhoneVerificationConfigurationError, send_phone_verification_code, verify_phone_verification_code


def _registration_error(name, email, password, confirmation, username=None):
    if username is not None and not username:
        return 'Username, name, email, and password are required.'
    if not name or not email or not password:
        return 'Name, email, and password are required.'
    if len(name) > 255:
        return 'Name must be 255 characters or fewer.'
    try:
        validate_email(email)
    except ValidationError:
        return 'Enter a valid email address.'
    if username is not None:
        username_field = User._meta.get_field('username')
        if len(username) > username_field.max_length:
            return f'Username must be {username_field.max_length} characters or fewer.'
        try:
            username_field.run_validators(username)
        except ValidationError:
            return 'Enter a valid username.'
    if password != confirmation:
        return 'The passwords do not match.'

    password_requirements = (
        (len(password) >= 8, 'at least 8 characters'),
        (re.search(r'[A-Za-z]', password), 'at least one letter'),
        (re.search(r'[A-Z]', password), 'at least one uppercase letter'),
        (re.search(r'\d', password), 'at least one number'),
        (re.search(r'[^A-Za-z0-9\s]', password), 'at least one special character'),
    )
    unmet_requirements = [message for met, message in password_requirements if not met]
    if unmet_requirements:
        return 'Password must contain ' + ', '.join(unmet_requirements) + '.'

    validation_user = User(
        username=username or email,
        email=email,
        name=name,
        first_name=name,
    )
    try:
        validate_password(password, user=validation_user)
    except ValidationError as error:
        return ' '.join(error.messages)
    return None


def _set_session_expiry(request, user):
    request.session.set_expiry(0 if user.is_staff else settings.SESSION_COOKIE_AGE)


def login_view(request):
    next_url = request.POST.get('next') or request.GET.get('next', '')
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect('dashboard:home')
        if next_url and url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            return redirect(next_url)
        return redirect('home')

    error = None
    identifier_error = None
    password_error = None
    if request.method == 'POST':
        identifier = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        if not identifier and not password:
            error = 'Username/email and password are required.'
            identifier_error = 'Username or email is required.'
            password_error = 'Password is required.'
        elif not identifier:
            error = 'Username or email is required.'
            identifier_error = error
        elif not password:
            error = 'Password is required.'
            password_error = error
        else:
            user = authenticate(request, username=identifier, password=password)
            if user is not None:
                login(request, user)
                _set_session_expiry(request, user)
                if not user.is_staff and next_url and url_has_allowed_host_and_scheme(
                    next_url,
                    allowed_hosts={request.get_host()},
                    require_https=request.is_secure(),
                ):
                    return redirect(next_url)
                return redirect('dashboard:home' if user.is_staff else 'home')
            error = 'The username/email or password is incorrect.'

    return render(request, 'login.html', {
        'error': error,
        'identifier_error': identifier_error,
        'password_error': password_error,
        'next_url': next_url,
    })


def admin_login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home' if request.user.is_staff else 'admin_login')

    error = None
    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '')
        if not identifier and not password:
            error = 'Username/email and password are required.'
        elif not identifier:
            error = 'Username or email is required.'
        elif not password:
            error = 'Password is required.'
        else:
            user = authenticate(request, username=identifier, password=password)
            if user is not None and user.is_staff:
                login(request, user)
                _set_session_expiry(request, user)
                return redirect('dashboard:home')
            error = 'Admin username/email or password is incorrect.'

    return render(request, 'admin_login.html', {'error': error})


def admin_register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:home' if request.user.is_staff else 'home')

    error = None
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirmation = request.POST.get('confirmation', '')

        error = _registration_error(
            name, email, password, confirmation, username=username,
        )
        if error is None and User.objects.filter(
            Q(username__iexact=username) | Q(email__iexact=email)
        ).exists():
            error = 'That username or email is already registered.'
        if error is None:
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                name=name,
                first_name=name,
                role='admin',
                is_staff=True,
                is_superuser=True,
            )
            login(request, user)
            _set_session_expiry(request, user)
            return redirect('dashboard:home')

    return render(request, 'admin_register.html', {'error': error})


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    error = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirmation = request.POST.get('confirmation', '')

        error = _registration_error(
            name, email, password, confirmation,
        )
        if error is None and User.objects.filter(
            Q(email__iexact=email) | Q(username__iexact=email)
        ).exists():
            error = 'An account with this email already exists.'
        if error is None:
            user = User.objects.create_user(
                username=email,
                email=email,
                password=password,
                name=name,
                first_name=name,
                role='customer',
            )
            login(request, user)
            return redirect('home')

    return render(request, 'register.html', {'error': error})


def logout_view(request):
    if request.method == 'POST':
        auth.logout(request)
    return redirect('home')


@login_required(login_url='login')
def profile_view(request):
    phone_error = None
    phone_notice = None
    pending_phone = request.session.get('pending_phone_verification')

    if request.method == 'POST':
        action = request.POST.get('action')
        if action == 'send_phone_code':
            phone = request.POST.get('phone', '').strip()
            request.session['profile_phone_form_value'] = phone
            if not re.fullmatch(r'\+[1-9]\d{7,14}', phone):
                phone_error = 'Enter a valid phone number with country code, such as +14155552671.'
            else:
                try:
                    send_phone_verification_code(phone)
                except PhoneVerificationConfigurationError:
                    phone_error = 'Phone verification is not configured. Contact the site administrator.'
                except TwilioException:
                    phone_error = 'We could not send a verification code. Check the number and try again.'
                else:
                    request.session['pending_phone_verification'] = phone
                    pending_phone = phone
                    phone_notice = f'A verification code was sent to {phone}.'
        elif action == 'verify_phone_code':
            pending_phone = request.session.get('pending_phone_verification')
            code = request.POST.get('verification_code', '').strip()
            if not pending_phone:
                phone_error = 'Request a verification code before entering it.'
            elif not code:
                phone_error = 'Enter the verification code.'
            else:
                try:
                    verified = verify_phone_verification_code(pending_phone, code)
                except PhoneVerificationConfigurationError:
                    phone_error = 'Phone verification is not configured. Contact the site administrator.'
                except TwilioException:
                    phone_error = 'We could not verify that code. Try again.'
                else:
                    if verified:
                        request.user.phone = pending_phone
                        request.user.phone_verified = True
                        request.user.save(update_fields=['phone', 'phone_verified'])
                        request.session.pop('pending_phone_verification', None)
                        request.session.pop('profile_phone_form_value', None)
                        pending_phone = None
                        phone_notice = 'Your phone number has been verified and saved.'
                    else:
                        phone_error = 'That verification code is not valid. Try again.'
        else:
            phone_error = 'Choose a valid phone action.'

        if phone_error:
            request.session['profile_phone_error'] = phone_error
        else:
            request.session.pop('profile_phone_error', None)
        if phone_notice:
            request.session['profile_phone_notice'] = phone_notice
        else:
            request.session.pop('profile_phone_notice', None)
        return redirect('profile')

    return render(request, 'profile.html', {
        'phone_error': request.session.pop('profile_phone_error', None),
        'phone_notice': request.session.pop('profile_phone_notice', None),
        'pending_phone': pending_phone,
        'phone_form_value': request.session.get('profile_phone_form_value', ''),
    })
