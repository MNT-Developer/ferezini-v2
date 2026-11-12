from getpass import getpass

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Usuario
from apps.auditoria.utils import registrar


class Command(BaseCommand):
    help = "Cria o primeiro gestor com todas as permissões de negócio, sem privilégios técnicos Django."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", default="")

    @transaction.atomic
    def handle(self, *args, **options):
        if Usuario.objects.filter(username=options["username"]).exists():
            raise CommandError("Esse usuário já existe; as permissões atuais não foram alteradas.")
        senha = getpass("Senha: ")
        if senha != getpass("Confirme a senha: "):
            raise CommandError("As senhas não conferem.")
        usuario = Usuario(username=options["username"], email=options["email"],
                          permissao_diretoria=True, permissao_administrativo=True, permissao_gestao_funcionario=True,
                          permissao_acesso_geral=True, permissao_gestao_projetos=True,
                          permissao_relatorios_gerais=True)
        try:
            password_validation.validate_password(senha, usuario)
            usuario.set_password(senha)
            usuario.full_clean()
        except ValidationError as erro:
            raise CommandError(" ".join(erro.messages)) from erro
        usuario.save()
        registrar(usuario, usuario, "CRIACAO_GESTOR", novos={"username": usuario.username, "permissoes_iniciais": "Todas as seis"})
        self.stdout.write(self.style.SUCCESS("Gestor inicial criado. Altere as permissões de cada funcionário pela interface."))
