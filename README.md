# Gaming Mouse Store

## Local development

Use the project's virtual environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver
```

Development mode defaults to `DJANGO_DEBUG=True`, localhost allowed hosts, and console email.

## Manual payment workflow

Customers can pay by UPI using the configured UPI ID or QR code, or choose Cash on Delivery. Payments are created as pending; placing an order does not mark an online payment as paid. Staff should verify the transfer or cash receipt in the payment provider/bank, then confirm the payment in the admin dashboard. A transaction reference can be recorded during confirmation. Confirming a pending payment moves a pending order to processing.

## Production configuration

Set these environment variables before starting Django:

| Variable | Required | Purpose |
| --- | --- | --- |
| `DJANGO_DEBUG` | Yes | Set to `False` in production. |
| `DJANGO_SECRET_KEY` | Yes | Long, random secret; required when debug is off. |
| `DJANGO_ALLOWED_HOSTS` | Yes | Comma-separated hostnames, without schemes. |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | For cross-origin HTTPS deployments | Comma-separated origins including `https://`. |
| `DJANGO_EMAIL_HOST` | For SMTP email | SMTP server hostname. |
| `DJANGO_EMAIL_PORT` | No | SMTP port; defaults to `587`. |
| `DJANGO_EMAIL_HOST_USER` | If required by SMTP | SMTP username. |
| `DJANGO_EMAIL_HOST_PASSWORD` | If required by SMTP | SMTP password. |
| `DJANGO_DEFAULT_FROM_EMAIL` | No | Sender address used for outgoing mail. |

With debug disabled, HTTPS redirects, secure session/CSRF cookies, and HSTS are enabled by default. Configure HTTPS at the host or trusted reverse proxy before enabling production traffic. Run `python manage.py check --deploy`, `python manage.py migrate`, and `python manage.py collectstatic` as part of deployment.

The default database is SQLite for local development. Select and configure a production database and persistent media storage to match your hosting platform before deploying; uploaded product and payment images currently use local media storage.
