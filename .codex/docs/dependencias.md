# Dependências — Linux / HostMídia / cPanel

Revisão v.0.0.3, em 11/11/2026. Um único [requirements.txt](../../requirements.txt) atende produção Linux e desenvolvimento Windows. O servidor HTTP/WSGI é administrado pelo provedor, via Passenger/cPanel.

| Componente | Base desta revisão | Referência |
| --- | --- | --- |
| Python | 3.11+; preferir 3.12/3.13 no Python Selector | [Cadastro cPanel](https://support.cpanel.net/hc/en-us/articles/360057849753-How-to-register-an-application-with-Python-Selector) |
| Django | 5.2.19 LTS | [Django 5.2](https://docs.djangoproject.com/en/5.2/) |
| mysqlclient | 2.3.1; bibliotecas nativas fornecidas pelo host | [Instalação](https://pypi.org/project/mysqlclient/) |
| MySQL / MariaDB | Mínimos Django: 8.0.11 / 10.5; preferir versões mantidas | [Bancos Django](https://docs.djangoproject.com/en/5.2/ref/databases/#mysql-notes) |
| Passenger | Instalado e mantido pelo provedor; não é dependência pip | [WSGI cPanel](https://docs.cpanel.net/knowledge-base/web-services/how-to-install-a-python-wsgi-application/) |
| WhiteNoise | 6.12.0; estáticos pelo WSGI, compressão e manifesto | [Django/WhiteNoise](https://whitenoise.readthedocs.io/en/stable/django.html) |
| WeasyPrint | 70.0; Pango 1.44+ e fontes do sistema | [Instalação](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) |
| python-dotenv | 1.2.4 | Manifesto único |
| tzdata | 2026.2 | Manifesto único |
| Cron | Fornecido pelo cPanel; frequência/recursos conforme plano | [Cron Jobs](https://docs.cpanel.net/cpanel/advanced/cron-jobs/) |
| Bootstrap | 5.3.8, assets locais e licença MIT | `static/vendor/` |

Gunicorn saiu do manifesto; Nginx, systemd, Certbot, Waitress, NSSM e Task Scheduler não integram a instalação atual. O cPanel administra aplicação e SSL. Não há manifestos separados por sistema operacional nem perfis Django de desenvolvimento/produção.

O banco usa InnoDB, `utf8mb4`, SQL strict e READ COMMITTED. Conexões persistentes ficam desativadas por padrão (`DB_CONN_MAX_AGE=0`). SQLite serve somente ao isolamento dos testes.

`verificar_ambiente.py` verifica configuração, conexão, compatibilidade do banco via Django, InnoDB, cache e PDF em memória. A compatibilidade do plano depende das bibliotecas e recursos efetivamente disponibilizados pela HostMídia; suporte genérico a Python não confirma Pango ou compilação de `mysqlclient`. Veja o [guia de implantação](hostmidia.md).

Dependências transitivas são resolvidas pelo pip. Um lock Linux deve ser produzido após homologar o ambiente real, sem declarar uma validação que não ocorreu. O [lock Windows inicial](historico-lock-windows-py313.txt) é histórico e não deve ser usado para instalar esta revisão. Para PDF local, `WEASYPRINT_DLL_DIRECTORIES` pode ser informado no `.env` conforme a documentação oficial; a aplicação não contém detecção especial de Windows.

O validador mantém CPF, CNPJ numérico e alfanumérico, segundo o [manual da Receita Federal](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj/manual-dv-cnpj.pdf). Esta reorganização não altera modelos nem regras financeiras.
