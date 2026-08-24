from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("conversations", "0002_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="external_peer_data",
            field=models.TextField(blank=True),
        ),
    ]
