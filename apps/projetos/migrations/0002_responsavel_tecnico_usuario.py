from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("projetos", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("accounts", "0003_usuario_permissao_administrativo"),
    ]

    operations = [
        # O texto livre fica preservado, sem atribuir funcionários por semelhança de nome.
        migrations.RenameField(
            model_name="projeto", old_name="responsavel_tecnico", new_name="responsavel_tecnico_anterior",
        ),
        migrations.AlterField(
            model_name="projeto", name="responsavel_tecnico_anterior",
            field=models.CharField(blank=True, editable=False, max_length=200),
        ),
        migrations.AddField(
            model_name="projeto", name="responsavel_tecnico",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.PROTECT,
                related_name="projetos_responsavel", to=settings.AUTH_USER_MODEL,
                verbose_name="Responsável técnico",
            ),
        ),
    ]
