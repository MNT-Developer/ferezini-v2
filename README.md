# Ferezini — Gestão Financeira de Obras · V1

Sistema Django em português para projetos, etapas, linhas de orçamento e despesas. Inclui planilha com autosave, auditoria, lotes com taxa de serviço e snapshots, PDF em memória e fila persistente de e-mails. Relatórios Gerais e Diretoria são páginas protegidas “Em desenvolvimento”, conforme o escopo.

## Instalação Windows

Requer Python 3.13, MySQL 8.4 LTS ou MariaDB 11.4 LTS e Pango para PDF. Também há compatibilidade Django com MySQL 8.0.11+; prefira versões de banco mantidas. As versões diretas estão fixadas em `requirements/` e documentadas em [docs/dependencias.md](docs/dependencias.md).

```powershell
./scripts/windows/instalar.ps1
# Edite .env com as credenciais do banco e configuração local.
./.venv/Scripts/python.exe manage.py migrate
./.venv/Scripts/python.exe manage.py criar_gestor --username gestor --email gestor@example.com
./scripts/windows/iniciar.ps1
```

Acesse http://127.0.0.1:8000. `criar_gestor` solicita a senha sem exibi-la. `createsuperuser` concede somente privilégios técnicos do Django; as cinco flags de negócio são independentes. Não há senha inicial fixa, conta de demonstração habilitada por padrão nem segredo versionado.

O Django Admin está disponível em http://127.0.0.1:8000/admin/. Crie um acesso técnico com `./.venv/Scripts/python.exe manage.py createsuperuser`. O usuário personalizado está registrado com auditoria de alterações e exclusão física desabilitada; registros financeiros são gerenciados pelas telas da aplicação.

Se o pip ficar bloqueado ao escrever seu cache em um ambiente restrito, use `python -m pip install --no-cache-dir -r requirements/windows.txt` dentro da `.venv`.

## Banco

Crie banco e usuário restrito com uma conta administrativa (não use root na aplicação):

```sql
CREATE DATABASE ferezini CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'ferezini'@'localhost' IDENTIFIED BY 'SUBSTITUA_POR_UMA_SENHA_FORTE';
GRANT SELECT, INSERT, UPDATE, CREATE, ALTER, INDEX, REFERENCES ON ferezini.* TO 'ferezini'@'localhost';
```

Migrações que precisem de permissões adicionais devem ser executadas por uma conta de implantação apropriada; a conta de execução pode ficar com SELECT/INSERT/UPDATE. As tabelas usam InnoDB, SQL strict, utf8mb4 e READ COMMITTED. Nunca remova migrações ou tabelas com dados. Os vínculos financeiros são protegidos e a interface só permite inativação lógica.

Para experimentar sem configurar banco, defina explicitamente `DB_ENGINE=sqlite` no `.env` e execute os mesmos comandos. Essa opção é exclusiva de desenvolvimento; produção rejeita SQLite. Os testes rápidos também usam SQLite e não comprovam bloqueios transacionais MySQL.

## PDF / WeasyPrint

O código gera bytes em memória com WeasyPrint 70.0; PDFs não são gravados em disco, banco ou armazenamento externo. Snapshots JSON persistentes permitem reconstruir os relatórios históricos. Corrigir ou inativar uma despesa não muda o relatório do lote.

No Windows, instale [MSYS2](https://www.msys2.org/). No shell UCRT64 do MSYS2, execute:

```sh
pacman -S mingw-w64-ucrt-x86_64-pango
```

No `.env`, configure `WEASYPRINT_DLL_DIRECTORIES=C:\msys64\ucrt64\bin`, reinicie o processo e verifique:

```powershell
./.venv/Scripts/python.exe -m weasyprint --info
```

Pango >=1.44 é necessário. Siga a [instalação oficial](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows) para alternativas. A ausência das bibliotecas não impede as telas HTML; download PDF informa a indisponibilidade.

Alternativa isolada, já validada neste projeto: `./scripts/windows/instalar_pdf.ps1` baixa o pacote **oficial** WeasyPrint 70.0 do GitHub, verifica SHA256 e extrai suas bibliotecas em `.venv/weasyprint-native`. Não altera o Windows nem o `.env`; as configurações Django detectam as DLLs automaticamente. `.venv/cache` recebe somente cache de fontes, sem PDFs; a conta de execução precisa de acesso a essa pasta. Recrie essa instalação ao recriar a `.venv`. Se `WEASYPRINT_DLL_DIRECTORIES` estiver definido no `.env`, ele tem prioridade.

## Linux

Em Debian/Ubuntu compatível, instale Python/venv, bibliotecas do mysqlclient e Pango:

```sh
sudo apt install python3-venv python3-dev build-essential pkg-config default-libmysqlclient-dev libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0
sh scripts/linux/instalar.sh
# Configure .env e o banco antes dos próximos comandos.
.venv/bin/python manage.py migrate
.venv/bin/python manage.py criar_gestor --username gestor
sh scripts/linux/iniciar.sh
```

Adapte o pacote/versão de Python à distribuição; a versão de referência é 3.13. Confira a [documentação de instalação do WeasyPrint](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#linux).

## Produção e HTTPS

Defina `DJANGO_SETTINGS_MODULE=config.settings.production`, uma `DJANGO_SECRET_KEY` aleatória de pelo menos 50 caracteres, `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` com a origem HTTPS, banco e SMTP. Gere a chave fora do controle de versão, por exemplo com `secrets.token_urlsafe(64)`. Proteja o arquivo `.env` e restrinja o usuário do serviço.

```powershell
./.venv/Scripts/python.exe manage.py collectstatic --noinput --settings=config.settings.production
./.venv/Scripts/python.exe manage.py check --deploy --settings=config.settings.production
./scripts/windows/iniciar.ps1 -Producao
```

Windows usa Waitress; `scripts/windows/instalar_servico.ps1` integra com NSSM previamente instalado, em terminal administrativo. Linux usa Gunicorn; adapte `/opt/ferezini` e o usuário nas unidades em `scripts/linux/`, instale-as em `/etc/systemd/system` e habilite `gestao-obras.service`.

Coloque Nginx/IIS/Caddy na frente, com certificado TLS válido, redirecionamento HTTP→HTTPS, arquivos de `staticfiles/` servidos em `/static/`, limites de requisição e timeouts. Mantenha WSGI em `127.0.0.1:8000` e restrinja a porta no servidor. Se o proxy definir `X-Forwarded-Proto` após remover o cabeçalho recebido do cliente, configure `TRUST_PROXY_HTTPS=true`. Nunca habilite confiança em cabeçalhos enviados diretamente pelo cliente. Não use `runserver` em produção.

## E-mails e reenvios

Desenvolvimento usa backend console; testes usam backend em memória/fakes. Produção requer `EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend` e credenciais SMTP no `.env`. O usuário seleciona endereços cadastrados ativos e/ou destinatários temporários; mensagens usam CCO. O default provisório exige pelo menos um contato ativo no projeto para o primeiro envio.

Confirmar o lote grava o trabalho pendente na mesma transação, sem chamar SMTP na requisição. Rode continuamente pelo agendador:

```powershell
./.venv/Scripts/python.exe manage.py processar_emails_pendentes
# Windows: configurar tarefa a cada minuto (ajuste a conta do agendador em produção).
./scripts/windows/configurar_agendador.ps1
```

Linux: habilite `gestao-obras-email.timer`; alternativa cron, com caminhos absolutos e usuário restrito:

```cron
* * * * * cd /opt/ferezini && DJANGO_SETTINGS_MODULE=config.settings.production /opt/ferezini/.venv/bin/python manage.py processar_emails_pendentes
```

Falhas confirmadas têm até três reenvios, três horas depois de cada falha. Reservas transacionais impedem envios simultâneos do mesmo lote. Timeout/queda após transmissão pode deixar resultado incerto; a fila não repete automaticamente. Verifique o Message-ID nos registros SMTP antes de solicitar reenvio manual pela tela. Reservas interrompidas há mais de 15 minutos são marcadas incertas. “Enviado” significa aceito pelo SMTP. Tentativas manuais não zeram o contador automático; sucesso cancela pendências.

## Uso e regras principais

1. Cadastre projetos, contatos e percentual de taxa. Ao criar uma etapa, sua tela exclusiva de orçamento abre automaticamente. Use **Adicionar orçamento** dentro da etapa para incluir itens; na aba Orçamento, **Abrir orçamentos** permite voltar à tela exclusiva de qualquer etapa.
2. Edite uma célula e pressione Enter/Tab ou saia dela; aguarde a confirmação “Salvo”. Em erro, use Tentar novamente ou Reverter. Conflito de versão exige atualização consciente dos dados.
3. Na aba Geral, adicione despesas na etapa ou em um item. Valor válido entra no realizado mesmo em rascunho; só fornecedor preenchido e valor positivo tornam a despesa elegível para lote.
4. Arraste etapas/itens na aba Orçamento para ordenar e use Restaurar A–Z para remover a personalização. Filtros e cabeçalhos de despesas afetam apenas apresentação; indicadores e subtotais continuam oficiais.
5. Envio de Despesas pré-seleciona elegíveis e calcula a taxa na tela. Marcar ou desmarcar despesas recalcula a taxa e descarta ajuste e justificativa anteriores. Editar a taxa revela a justificativa obrigatória quando diferente do cálculo. Revise a prévia e confirme; o lote confirmado é imutável.
6. Consulte HTML/PDF e tentativas no histórico de lotes. O relatório por período usa datas inclusivas de confirmação dos lotes no fuso de São Paulo e valores dos snapshots.

Não há exclusão física pela aplicação. Despesa inativa requer justificativa; reativação sempre exige observação. Item que já teve despesa exige justificativa para alterações. Inativar item mantém suas despesas e vínculos, exibindo-as na área geral da etapa. Etapa com despesas ativas não pode ser inativada. Histórico registra operador, horário, antes/depois e correlação.

## Testes

```powershell
./.venv/Scripts/python.exe manage.py test --settings=config.settings.test
./.venv/Scripts/python.exe manage.py check --settings=config.settings.test
./.venv/Scripts/python.exe manage.py makemigrations --check --dry-run --settings=config.settings.test
node --test tests/formatacao.test.cjs tests/envios.test.cjs
```

Para testar em MySQL/MariaDB, configure `DB_*` para um banco exclusivo de testes e defina `TEST_MYSQL=true` antes do comando. O Django cria o banco `test_<DB_NAME>`; forneça a conta de teste com privilégios CREATE/DROP nesse banco. Nunca use um banco real com `--keepdb` sem controle. Testes de concorrência com SELECT FOR UPDATE são ignorados em SQLite e devem passar no banco de produção alvo antes da homologação.

Você pode definir `TEST_DB_NAME` para um nome temporário exclusivo. Para habilitar os testes de geração real em memória, defina também `TEST_PDF_REAL=true`. As DLLs locais instaladas pelo script são detectadas durante a configuração Django.

## Backup e restauração

Faça backup transacional do banco inteiro: usuários, permissões, projetos, linhas, despesas, vínculos, lotes, snapshots, auditoria e tentativas. PDFs não fazem parte do backup. Use `mysqldump --single-transaction --routines --triggers --default-character-set=utf8mb4` (ou `mariadb-dump`) com credenciais em arquivo protegido/opção interativa; nunca senha em linha de comando. Guarde cópias criptografadas fora do servidor e teste restauração em banco isolado, verificando totais e reconstrução de relatórios. Preserve também versão do código, migrations e `.env` em cofre separado. Periodicidade, retenção e responsáveis ainda precisam ser aprovados.

[docs/decisoes_pendentes.md](docs/decisoes_pendentes.md) registra todos os defaults provisórios e a limitação de colagem multicélula. [docs/validacao.md](docs/validacao.md) informa o que foi efetivamente verificado neste ambiente.
