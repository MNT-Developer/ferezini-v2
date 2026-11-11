from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.envios.models import LoteEnvioTentativa
from apps.envios.utils import processar_tentativa, recuperar_reservas_expiradas


class Command(BaseCommand):
    help = "Processa a fila persistente de e-mails sem manter transações abertas durante o SMTP."

    def add_arguments(self, parser):
        parser.add_argument("--limite", type=int, default=50, help="Número máximo de tentativas nesta execução.")

    def handle(self, *args, **options):
        if options["limite"] < 1:
            self.stderr.write("O limite deve ser positivo.")
            return
        recuperadas = recuperar_reservas_expiradas()
        ids = list(LoteEnvioTentativa.objects.filter(
            resultado="PENDENTE", agendada_para__lte=timezone.now(),
        ).order_by("agendada_para", "pk").values_list("pk", flat=True)[:options["limite"]])
        processadas = sum(processar_tentativa(pk) for pk in ids)
        self.stdout.write(f"Tentativas processadas: {processadas}. Reservas interrompidas registradas como incertas: {recuperadas}.")
