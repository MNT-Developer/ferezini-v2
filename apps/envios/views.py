import uuid

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import signing
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.permissions import exigir_permissao
from apps.projetos.models import Projeto

from .forms import PrepararLoteForm, ReenvioForm
from .models import LoteEnvioDespesa
from .utils import confirmar_lote, gerar_pdf_lote, resumo_selecao, solicitar_reenvio


@login_required
@require_GET
def painel(request, projeto_id):
    exigir_permissao(request.user, "projetos")
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    form = PrepararLoteForm(projeto)
    return render(request, "envios/painel.html", {"projeto": projeto, "form": form, "lotes": projeto.lotes.all()})


@login_required
@require_POST
def preparar(request, projeto_id):
    exigir_permissao(request.user, "projetos")
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    form = PrepararLoteForm(projeto, request.POST)
    if form.is_valid():
        dados = form.cleaned_data
        despesas = [d for d in form.elegiveis if str(d.pk) in dados["despesas"]]
        try:
            resumo = resumo_selecao(projeto, despesas, dados["valor_taxa"], dados["justificativa_taxa"])
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            payload = {
                "usuario_id": request.user.pk, "projeto_id": projeto.pk,
                "versao_projeto": projeto.versao,
                "despesa_ids": [d.pk for d in despesas],
                "versoes_despesas": {str(d.pk): d.versao for d in despesas},
                "modalidade": dados["modalidade"], "valor_taxa": str(resumo["valor_taxa"]),
                "justificativa_taxa": dados["justificativa_taxa"],
                "destinatarios": dados["enderecos_efetivos"],
            }
            payload["chave_confirmacao"] = str(uuid.uuid4())
            token = signing.dumps(payload, salt="ferezini.lote.v1", compress=True)
            return render(request, "envios/confirmar.html", {
                "projeto": projeto, "despesas": despesas, "resumo": resumo,
                "modalidade": dados["modalidade"], "destinatarios": dados["enderecos_efetivos"], "token": token,
            })
    return render(request, "envios/painel.html", {"projeto": projeto, "form": form, "lotes": projeto.lotes.all()}, status=400)


@login_required
@require_POST
def confirmar(request, projeto_id):
    exigir_permissao(request.user, "projetos")
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    try:
        dados = signing.loads(request.POST.get("token", ""), salt="ferezini.lote.v1", max_age=900)
        if dados.pop("usuario_id") != request.user.pk or dados["projeto_id"] != projeto.pk:
            raise ValidationError("A prévia não pertence a este projeto e usuário.")
        lote = confirmar_lote(request.user, **dados)
    except signing.BadSignature:
        messages.error(request, "A prévia expirou ou é inválida. Prepare o lote novamente.")
        return redirect("envios:painel", projeto_id=projeto.pk)
    except ValidationError as exc:
        messages.error(request, " ".join(exc.messages))
        return redirect("envios:painel", projeto_id=projeto.pk)
    messages.success(request, "Lote confirmado. O PDF está disponível e o e-mail solicitado será processado pela fila.")
    return redirect("envios:detalhe", lote_id=lote.pk)


@login_required
@require_GET
def detalhe(request, lote_id):
    exigir_permissao(request.user, "projetos")
    lote = get_object_or_404(LoteEnvioDespesa.objects.select_related("projeto", "enviado_por").prefetch_related("itens", "tentativas__solicitado_por"), pk=lote_id)
    form = ReenvioForm(initial={"destinatarios": ", ".join(lote.destinatarios)})
    return render(request, "envios/detalhe.html", {"projeto": lote.projeto, "lote": lote, "form": form})


@login_required
@require_GET
def pdf(request, lote_id):
    exigir_permissao(request.user, "projetos")
    lote = get_object_or_404(LoteEnvioDespesa.objects.prefetch_related("itens"), pk=lote_id)
    try:
        conteudo = gerar_pdf_lote(lote)
    except (ImportError, OSError):
        return HttpResponse("O mecanismo PDF está indisponível. Verifique a instalação do ReportLab pelo requirements.txt.", status=503, content_type="text/plain; charset=utf-8")
    response = HttpResponse(conteudo, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="despesas-lote-{lote.pk}.pdf"'
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
@require_POST
def reenviar(request, lote_id):
    exigir_permissao(request.user, "projetos")
    lote = get_object_or_404(LoteEnvioDespesa.objects.select_related("projeto").prefetch_related("itens", "tentativas"), pk=lote_id)
    form = ReenvioForm(request.POST)
    if form.is_valid():
        try:
            solicitar_reenvio(request.user, lote.pk, form.cleaned_data["destinatarios"])
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, "Reenvio colocado na fila. O lote e seus snapshots foram preservados.")
            return redirect("envios:detalhe", lote_id=lote.pk)
    return render(request, "envios/detalhe.html", {"projeto": lote.projeto, "lote": lote, "form": form}, status=400)
