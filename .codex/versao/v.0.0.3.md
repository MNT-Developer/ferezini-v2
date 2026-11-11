# Ferezini — Projeto FRZ v2 · v.0.0.3

> **Data:** 11/11/2026  
> **Base:** [v.0.0.2](v.0.0.2.md) e [especificação inicial](v.0.0.1.md).  
> **Objetivo:** centralizar os arquivos de apoio em `.codex` e implantar em Linux na HostMídia, pelo cPanel/Python Selector e Passenger.

O conteúdo desta versão foi substituído para refletir a implantação HostMídia solicitada. Esta é a revisão vigente; não há configuração ativa ou guia paralelo de VPS Hostinger.

## 1. Organização

| Arquivos | Local atual |
| --- | --- |
| Especificações e versões `v.*.md` | [`.codex/versao/`](./) |
| Documentação e validação | [`.codex/docs/`](../docs/) |
| Instalação, atualização, Cron e testes | [`.codex/scripts/`](../scripts/) |
| Dependências | [`requirements.txt`](../../requirements.txt) |
| Exemplo de configuração | [`.codex/.env.example`](../.env.example) |
| Isolamento e testes de implantação | [test_settings.py](../test_settings.py) e [tests_deploy.py](../tests_deploy.py) |
| Testes JavaScript | [`.codex/tests/`](../tests/) |

O código necessário à execução permanece em `apps/`, `config/`, `templates/`, `static/` e `utils/`, junto de `manage.py`. O `.env` real permanece na raiz, privado e ignorado pelo Git. [`passenger_wsgi.py`](../../passenger_wsgi.py) fica na raiz por ser a entrada de execução do servidor. Links das versões e dos documentos foram atualizados.

Scripts de VPS Ubuntu, Nginx, Gunicorn e unidades systemd foram removidos da instalação atual. O guia Hostinger foi substituído pelo [guia HostMídia](../docs/hostmidia.md). Windows continua sendo apenas uma estação possível de desenvolvimento.

## 2. Configuração única e proteção de produção

- [`config/settings.py`](../../config/settings.py) é o único módulo Django; `manage.py`, WSGI e ASGI o utilizam.
- O `.env` controla banco, SMTP, hosts e proxy. `DJANGO_DEBUG=false` é o padrão e exige segredo forte e hosts explícitos, com HTTPS, cookies seguros e HSTS.
- O entrypoint Passenger e os wrappers de atualização/Cron forçam produção para evitar debug acidental no servidor.
- Produção exige backend SMTP; console/arquivo são rejeitados para não registrar anexos PDF nos logs.
- `TRUST_PROXY_HTTPS=false` é o padrão. Ativação depende da confirmação do provedor de que o proxy sobrescreve o cabeçalho confiado.
- MySQL/MariaDB continua com InnoDB, `utf8mb4`, SQL strict e READ COMMITTED. `DB_CONN_MAX_AGE=0` é o padrão, configurável pelo `.env`.
- Cache gravável em `.cache` por padrão, com override por `XDG_CACHE_HOME`, sem caminho fixo de VPS. PDFs continuam somente em memória.
- `.cache/`, `tmp/`, `.env` e `staticfiles/` não entram no Git. `.env` local existente e suas credenciais foram preservados.

`test_settings.py` apenas isola os testes: banco SQLite em memória ou MySQL temporário, SMTP em memória, HTTPS desativado e armazenamento simples de estáticos. Não é um segundo perfil de hospedagem.

## 3. Execução no cPanel

| Item | Implementação |
| --- | --- |
| Aplicação web | Passenger com [`passenger_wsgi.py`](../../passenger_wsgi.py), callable `application` |
| Ambiente Python | Virtualenv fornecido pelo Python Selector; nenhum segundo virtualenv criado pelo instalador |
| Código e configuração privada | Raiz fora de `public_html`, por exemplo `/home/USUARIO/frz-v2` |
| Estáticos | WhiteNoise com compressão e nomes com hash; `collectstatic` antes do Restart |
| Fila de e-mails | Cron executando wrapper com limite padrão de uma tentativa por chamada |
| SSL e reinício | Administrados pelo cPanel/HostMídia |

Os caminhos do virtualenv são copiados do painel, sem assumir `/opt/ferezini`, permissões root ou serviços próprios. O guia usa um subdomínio dedicado com URL na raiz.

## 4. Ferramentas de operação

- [`instalar.py`](../scripts/instalar.py): instala o manifesto usando o Python selecionado no cPanel, exige virtualenv e Python 3.11+, rejeita raiz dentro de `public_html`, cria `.env` somente se ausente com segredo aleatório e permissões privadas, sem mostrar a chave.
- [`verificar_ambiente.py`](../scripts/verificar_ambiente.py): verifica segurança de produção, conexão e compatibilidade do banco, InnoDB, cache e PDF real em memória. Não transmite e-mails.
- [`atualizar.py`](../scripts/atualizar.py): executa a verificação, migrações e `collectstatic`; só após sucesso solicita reinício via `tmp/restart.txt`. O botão Restart do painel confirma o reinício. Falhas interrompem a sequência.
- [`processar_emails.py`](../scripts/processar_emails.py): wrapper de Cron com produção forçada e `--limite 1` por padrão, usando a fila/bloqueios persistentes existentes.
- [`cron_exemplo.txt`](../scripts/cron_exemplo.txt): comando com caminhos absolutos e log privado. Frequência deve respeitar o plano; três horas continuam controladas no banco.
- [`testar.py`](../scripts/testar.py): suíte isolada local ou MySQL em banco temporário aleatório previamente verificado como inexistente.

Não há alteração nas três tentativas automáticas adicionais ao envio inicial, tratamento de resultado incerto/parcial, snapshots, auditoria ou permissões. Não há migração de modelos motivada por esta revisão.

## 5. Dependências e requisitos do plano

- Mantidos Django 5.2.19, mysqlclient 2.3.1, python-dotenv 1.2.4, WeasyPrint 70.0 e tzdata 2026.2.
- Adicionado WhiteNoise 6.12.0; removido Gunicorn do manifesto.
- Passenger vem do provedor, não do pip. Nginx/systemd/Certbot não são configurados pela aplicação.
- Base Python 3.11+, preferencialmente 3.12/3.13. MySQL 8.0.11+ ou MariaDB 10.5+ são os mínimos do Django; devem ser usadas versões mantidas.
- Pango 1.44+, fontes e bibliotecas necessárias a `mysqlclient` precisam estar disponíveis no ambiente do provedor. Instalar os pacotes Python não supre esses requisitos.
- Sem instalação Windows de produção, dependências separadas por plataforma, Docker, Redis ou Celery.

A [HostMídia anuncia Python/cPanel](https://www.hostmidia.com.br/hospedagem-de-sites/), mas as versões, bibliotecas nativas e limites de Cron/recursos do plano precisam ser confirmados. A estrutura preparada não significa hospedagem publicada ou compatibilidade já homologada. Veja [dependências](../docs/dependencias.md) e [implantação](../docs/hostmidia.md).

## 6. Validação

- **101 testes Python passaram**, sem testes ignorados, com MySQL e PDF real habilitados: 86 funcionais e 15 de configuração/implantação.
- **Sete testes JavaScript passaram**.
- `verificar_ambiente.py` passou com configuração de produção, `check --deploy --fail-level WARNING`, conexão MySQL/InnoDB, cache gravável e PDF real em memória. Nenhum e-mail foi transmitido.
- `collectstatic` passou com manifesto WhiteNoise e compressão. Removida uma referência do CSS Bootstrap a um source map ausente, mantendo o CSS e a licença.
- A entrada WSGI real foi carregada fora da pasta do projeto, com debug desativado: login, login do admin e CSS com hash retornaram HTTP 200 em HTTPS.
- Os testes verificam produção forçada no Passenger, limite/validação do Cron, preservação do `.env`, geração privada do segredo e recusa de código em `public_html`. Também verificam estáticos em produção e ausência de exposição do `.env`.
- `makemigrations --check --dry-run` não apontou alterações; `pip check` passou e o manifesto foi conferido por dry-run local.
- Links Markdown locais, sintaxe das entradas Python e `git diff --check` foram conferidos. Os arquivos Python e TXT têm normalização LF no `.gitattributes`.

A execução ocorreu em **Windows/Python 3.13.7/MySQL 8.0.41**. Não houve execução real de Passenger, Cron do cPanel, CageFS, SMTP ou SSL da conta HostMídia. Compatibilidade das bibliotecas nativas, limites de recursos e aparência visual final dos PDFs ainda precisam ser homologados no servidor.

## 7. Implantação e pendências

Envie o código incluindo `.codex`, cadastre a aplicação Python, instale pelo virtualenv do painel, configure o `.env`, execute `atualizar.py`, crie os usuários necessários, confirme SSL/Restart e configure o Cron. O guia detalha verificações, logs, atualização e backup.

Antes de publicar, confirme a compatibilidade do plano, domínio, SSL, SMTP, limites de recursos e frequência Cron. Preserve banco e snapshots em backup transacional e teste restauração em ambiente isolado. Retenção/responsáveis, homologação visual dos PDFs e relatórios estratégicos continuam pendentes.

Não houve acesso à conta HostMídia, implantação remota ou envio SMTP real nesta revisão.
