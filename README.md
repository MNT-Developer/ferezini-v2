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
    versao/v.0.0.7.md         # versão atual em desenvolvimento
```

O manifesto de dependencias fica em [`requirements.txt`](requirements.txt), na raiz.

A conexão é configurada por `DATABASE_URL=mysql://USUARIO:SENHA_CODIFICADA@HOST:3306/BANCO`, usando `dj-database-url`. Caracteres especiais das credenciais precisam ser codificados na URL, conforme a [documentação da biblioteca](https://pypi.org/project/dj-database-url/3.1.2/). A configuração mantém conexões por até 600 segundos, com verificação de saúde e `ssl_require=False`. As variáveis separadas `DB_*` foram substituídas pela URL.

A versão [v.0.0.6](.codex/versao/v.0.0.6.md) foi finalizada em 13/11/2026, com os quatro cards da página inicial e a conexão por `DATABASE_URL`. A versão ativa é a [v.0.0.7](.codex/versao/v.0.0.7.md); as próximas alterações serão registradas nela até o encerramento explícito pelo usuário.

Os dados descritivos da obra nos relatórios de envio e no detalhe dos lotes vêm sempre do cadastro atual do projeto. Não são duplicados no lote nem nos snapshots das notas. Notas, valores financeiros e destinatários dos e-mails permanecem registrados na confirmação. A migração `envios.0002` remove as cópias antigas dos dados do projeto.

Leia o [guia HostMídia](.codex/docs/hostmidia.md) antes de instalar. A [HostMídia anuncia Python/cPanel](https://www.hostmidia.com.br/hospedagem-de-sites/); confirme no plano **Python 3.11+, Passenger, mysqlclient e Cron**. Os PDFs usam ReportLab e fontes incluídas no pacote pip.

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
# No .env local: DJANGO_DEBUG=true, hosts locais, DATABASE_URL e backend de e-mail console.
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

Login: `/entrar/`. Admin: `/admin/`. `criar_gestor` cria as permissões operacionais; `createsuperuser` concede privilégios técnicos independentes das seis flags do sistema.

Login e novas senhas não diferenciam maiúsculas de minúsculas. A única regra de força é o mínimo de seis caracteres. A migração `accounts.0004` exige que as contas com senhas antigas as redefinam antes de continuar: a senha atual permite entrar na tela de redefinição. A alteração também pode ser feita por um gestor autorizado ou pelo comando `changepassword`. As senhas continuam armazenadas como hashes PBKDF2 com salt.

O responsável técnico é um colaborador opcional. Quem acessa projetos pode fazer o primeiro vínculo; depois, somente Diretoria ou Administrativo podem substituí-lo ou removê-lo. A seleção mostra colaboradores ativos que não sejam superusuários. Textos anteriores à conversão para usuário ficam preservados no cadastro, sem associação automática.

O módulo **Gestão de Usuários** permite cadastrar, editar, inativar e reativar usuários, com busca, filtro de situação e paginação de 25 registros. O acesso exige Diretoria, Gestão de funcionários ou superusuário. As contas de superusuários ficam fora da listagem operacional. A inativação preserva vínculos e histórico e impede o acesso enquanto a conta estiver inativa.

Somente Diretoria ou superusuários podem visualizar/gerenciar contas da Diretoria e conceder essa permissão, tanto no cadastro quanto na edição. Para os demais gestores, essas contas não aparecem nas listas ou pesquisas e a flag de Diretoria não aparece no formulário. As mesmas restrições são aplicadas ao Django Admin.

## Formatação dos templates

Os templates usam UTF-8, finais de linha LF e indentação de dois espaços, conforme o [guia de estilo do Django](https://docs.djangoproject.com/en/5.2/internals/contributing/writing-code/coding-style/). A configuração do formatador fica em [`.codex/djlint.toml`](.codex/djlint.toml).

Para formatar novamente ou conferir o padrão, instale a ferramenta de desenvolvimento no ambiente virtual:

```powershell
.\.venv\Scripts\python.exe -m pip install djlint==1.36.4
.\.venv\Scripts\python.exe .codex/scripts/formatar_templates.py
.\.venv\Scripts\python.exe .codex/scripts/formatar_templates.py --check
```

No Linux, use o executável do virtualenv correspondente. O formatador atua somente em `templates/`; ele não é uma dependência de execução da aplicação.

## Verificações

```powershell
.\.venv\Scripts\python.exe .codex/scripts/testar.py
.\.venv\Scripts\python.exe .codex/scripts/testar.py --mysql --pdf-real
node --test .codex/tests/formatacao.test.cjs .codex/tests/envios.test.cjs .codex/tests/responsavel-tecnico.test.cjs
```

No Linux, use o Python do virtualenv correspondente. Os testes não enviam e-mails reais. SQLite fica restrito ao isolamento dos testes; a aplicação usa MySQL/MariaDB. PDF usa ReportLab, instalado pelo manifesto pip, com as fontes fornecidas pelo próprio pacote. O layout dos PDFs é definido em `utils/pdf.py`; os antigos templates de impressão HTML permanecem como referência histórica de apresentação.

Consulte [implantação e backup](.codex/docs/hostmidia.md), [dependências](.codex/docs/dependencias.md), [decisões pendentes](.codex/docs/decisoes_pendentes.md), [versão ativa v.0.0.7](.codex/versao/v.0.0.7.md), [versão finalizada v.0.0.6](.codex/versao/v.0.0.6.md), [histórico v.0.0.5](.codex/versao/v.0.0.5.md), [mudanças v.0.0.4](.codex/versao/v.0.0.4.md) e [base de infraestrutura v.0.0.3](.codex/versao/v.0.0.3.md).
