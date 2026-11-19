from django.shortcuts import redirect
from django.urls import reverse


class RedefinicaoSenhaMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.exigir_redefinicao_senha:
            permitidos = {reverse("accounts:redefinir_senha"), reverse("logout")}
            if request.path_info not in permitidos:
                return redirect("accounts:redefinir_senha")
        return self.get_response(request)
