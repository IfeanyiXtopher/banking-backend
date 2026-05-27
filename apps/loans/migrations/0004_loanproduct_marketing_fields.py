from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('loans', '0003_seed_default_loan_products'),
    ]

    operations = [
        migrations.AddField(
            model_name='loanproduct',
            name='tagline',
            field=models.CharField(blank=True, max_length=280),
        ),
        migrations.AddField(
            model_name='loanproduct',
            name='full_description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='loanproduct',
            name='hero_image',
            field=models.ImageField(blank=True, null=True, upload_to='loans/products/'),
        ),
    ]
