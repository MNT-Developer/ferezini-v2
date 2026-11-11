# Ferezini — Projeto FRZ v2

Gestão financeira de obras com Django: projetos, etapas, orçamentos, despesas, auditoria, lotes com snapshots, PDF em memória e fila de e-mails. Interface em português. Relatórios Gerais e Diretoria permanecem em desenvolvimento.

A implantação é **Linux na HostMídia, com cPanel/Python Selector, Passenger, MySQL/MariaDB e Cron**. Windows é a estação de desenvolvimento. Há um único módulo de configuração: [`config/settings.py`](config/settings.py), controlado pelo `.env` privado.

## Documentação e operação

As ferramentas de apoio ficam em [`.codex/`](.codex/README.md):

```text
.codex/
    .env.example
    scripts/                 # instalação, atualização, Cron e testes
    docs/hostmidia.md        # guia de implantação completo
    tests/                  # testes JavaScript
    test_settings.py        # isolamento dos testes automatizados
    tests_deploy.py
    versao/v.0.0.3.md
```

O manifesto de dependencias fica em [`requirements.txt`](requirements.txt), na raiz.

Leia o [guia HostMídia](.codex/docs/hostmidia.md) antes de instalar. A [HostMídia anuncia Python/cPanel](https://www.hostmidia.com.br/hospedagem-de-sites/); confirme no plano **Python 3.11+, Passenger, Pango/WeasyPrint, mysqlclient e Cron**. Suporte genérico a Python não garante essas bibliotecas nativas.

## Implantação no cPanel

Envie o projeto, incluindo `.codex`, para uma pasta **fora de `public_html`**. No Setup Python App, selecione Python 3.12/3.13, configure a raiz do projeto, startup file `passenger_wsgi.py` e entry point `application`. Use um subdomínio com URL na raiz. Execute com o Python absoluto do virtualenv informado pelo painel; adapte o caminho ilustrativo:

```sh
cd /home/USUARIO/frz-v2
/home/USUARIO/virtualenv/frz-v2/3.12/bin/python .codex/scripts/instalar.py
# Configure o .env privado com dominio, banco e SMTP do servidor.
/home/USUARIO/virtualenv/frz-v2/3.12/bin/python .codex/scripts/atualizar.py
/home/USUARIO/virtualenv/frz-v2/3.12/bin/python manage.py criar_gestor --username gestor
/home/USUARIO/virtualenv/frz-v2/3.12/bin/python manage.py createsuperuser
```

O instalador preserva o `.env` existente. `atualizar.py` valida produção/banco/PDF, aplica migrações, coleta estáticos e solicita reinício ao Passenger. Confirme **Restart** e SSL pelo cPanel. WhiteNoise serve os estáticos pelo WSGI.

Configure o Cron conforme [o exemplo](.codex/scripts/cron_exemplo.txt), usando o mesmo Python absoluto e `.codex/scripts/processar_emails.py --limite 1`. A frequência respeita o plano; o banco continua controlando as três horas dos reenvios.

Produção exige debug desativado, segredo forte, hosts explícitos, HTTPS e SMTP. `passenger_wsgi.py` é parte da execução e fica na raiz; os arquivos de instalação e documentação permanecem em `.codex`.

## Desenvolvimento local

No Windows, use o mesmo manifesto e configuração:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --no-cache-dir -r requirements.txt
# Se ainda nao existir .env, copie .codex/.env.example para a raiz.
# No .env local: DJANGO_DEBUG=true, hosts locais, banco e backend de e-mail console.
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Login: `/entrar/`. Admin: `/admin/`. `criar_gestor` cria as permissões operacionais; `createsuperuser` concede privilégios técnicos independentes das cinco flags do sistema.

## Verificações

```powershell
.\.venv\Scripts\python.exe .codex/scripts/testar.py
.\.venv\Scripts\python.exe .codex/scripts/testar.py --mysql --pdf-real
node --test .codex/tests/formatacao.test.cjs .codex/tests/envios.test.cjs
```

No Linux, use o Python do virtualenv correspondente. Os testes não enviam e-mails reais. SQLite fica restrito ao isolamento dos testes; a aplicação usa MySQL/MariaDB. PDF exige WeasyPrint/Pango.

Consulte [implantação e backup](.codex/docs/hostmidia.md), [dependências](.codex/docs/dependencias.md), [decisões pendentes](.codex/docs/decisoes_pendentes.md) e [mudanças v.0.0.3](.codex/versao/v.0.0.3.md).
