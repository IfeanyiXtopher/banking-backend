from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_alter_account_options"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="account",
            constraint=models.UniqueConstraint(
                fields=("owner", "account_type"),
                name="unique_account_type_per_owner",
            ),
        ),
    ]
