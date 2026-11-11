from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.accounts.permissions import exigir_permissao
from apps.projetos.models import Projeto

from .forms import PeriodoForm
from .utils import despesas_por_periodo, gerar_pdf_periodo


@login_required
@require_GET
def despesas(request, projeto_id):
    exigir_permissao(request.user, "projetos")
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    hoje = timezone.localdate()
    form = PeriodoForm(request.GET or {"inicio": hoje.replace(day=1).isoformat(), "fim": hoje.isoformat()})
    contexto = {"projeto": projeto, "form": form}
    if form.is_valid():
        contexto.update(despesas_por_periodo(projeto, form.cleaned_data["inicio"], form.cleaned_data["fim"]))
        if request.GET.get("formato") == "pdf":
            try:
                conteudo = gerar_pdf_periodo(contexto)
            except (ImportError, OSError):
                return HttpResponse("O mecanismo PDF está indisponível. Verifique a instalação do WeasyPrint e suas bibliotecas nativas.", status=503, content_type="text/plain; charset=utf-8")
            response = HttpResponse(conteudo, content_type="application/pdf")
            response["Content-Disposition"] = f'attachment; filename="despesas-projeto-{projeto.pk}.pdf"'
            response["Cache-Control"] = "private, no-store"
            return response
    return render(request, "relatorios/despesas.html", contexto, status=200 if form.is_valid() else 400)
