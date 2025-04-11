from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('lending', '0001_initial'),  # or whatever your latest is
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='total_copies',
            field=models.PositiveIntegerField(default=1, verbose_name='Total Copies'),
        ),
    ]
