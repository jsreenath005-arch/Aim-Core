from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('orders', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='PaymentQR',
            fields=[
                ('qr_id', models.AutoField(primary_key=True, serialize=False)),
                ('title', models.CharField(max_length=200)),
                ('notes', models.TextField(blank=True, null=True)),
                ('qr_code', models.ImageField(blank=True, null=True, upload_to='payment_qr/')),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'PAYMENT_QR',
            },
        ),
    ]
