from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('StudentScanner', 'previous_migration'),
    ]

    operations = [
        migrations.AlterField(
            model_name='customuser',
            name='username',
            field=models.CharField(db_index=True, max_length=150, unique=True),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='email',
            field=models.EmailField(db_index=True, blank=True, max_length=254),
        ),
        migrations.AlterField(
            model_name='customuser',
            name='role',
            field=models.CharField(db_index=True, choices=[...], max_length=20),
        ),
    ]