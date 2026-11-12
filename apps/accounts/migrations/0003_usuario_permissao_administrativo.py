from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_alter_usuario_managers")]

    operations = [
        migrations.AddField(
            model_name="usuario",
            name="permissao_administrativo",
            field=models.BooleanField(default=False, verbose_name="Administrativo"),
        ),
    ]
