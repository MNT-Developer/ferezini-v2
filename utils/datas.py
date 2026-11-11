from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.core.exceptions import ValidationError


def limites_periodo(inicio, fim):
    if inicio > fim:
        raise ValidationError("A data inicial deve ser anterior ou igual à final.")
    fuso = ZoneInfo("America/Sao_Paulo")
    return (
        datetime.combine(inicio, time.min, tzinfo=fuso),
        datetime.combine(fim + timedelta(days=1), time.min, tzinfo=fuso),
    )
