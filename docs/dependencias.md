# Versões e compatibilidade

Consulta às fontes oficiais em 11/11/2026. Versões diretas fixadas em `requirements/`; Python de referência 3.13 (ambiente disponível: 3.13.7). Atualize o patch de Python e dependências sob verificação antes da produção.

| Componente | Versão escolhida | Compatibilidade |
| --- | --- | --- |
| Django | 5.2.19 LTS | Python 3.13 suportado; [documentação](https://docs.djangoproject.com/en/5.2/faq/install/) |
| MySQL | 8.4 LTS recomendado | Django 5.2 suporta 8.0.11+; [banco](https://docs.djangoproject.com/en/5.2/ref/databases/#mysql-notes) |
| MariaDB | 11.4 LTS recomendado | Django 5.2 suporta 10.5+; preferir versão ainda mantida |
| mysqlclient | 2.3.1 | Driver nativo recomendado pelo Django, wheels Windows/Python 3.13; [projeto](https://pypi.org/project/mysqlclient/) |
| WeasyPrint | 70.0 | Python >=3.10, Pango >=1.44; [instalação oficial](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) |
| Waitress | 3.0.2 | Python >=3.9, Windows/Unix; [documentação](https://docs.pylonsproject.org/projects/waitress/en/stable/) |
| Gunicorn | 27.0.0 | Unix, Python >=3.12; [instalação](https://gunicorn.org/install/) |
| Bootstrap | 5.3.8 | Assets locais; licença MIT em static/vendor |
| AG Grid Community | 36.3.0 avaliado | [documentação](https://www.ag-grid.com/javascript-data-grid/installation/); substituído por tabela HTML aberta nesta V1 |

MySQL/MariaDB: InnoDB, utf8mb4, SQL strict e isolamento READ COMMITTED. Não trocar o banco de produção por SQLite. Dependências transitivas são resolvidas pelo pip; `pip freeze` pode registrar o ambiente homologado após validar o sistema operacional alvo.

O ambiente Windows validado foi fixado em `requirements/lock-windows-py313.txt`. O instalador PDF local usa o [pacote oficial 70.0](https://github.com/Kozea/WeasyPrint/releases/tag/v70.0), SHA256 `ab1151f210b4e6bb7aa7a79e91a67e8ddb760094c107bfda55241b6aaefe7d53`. O pacote inclui Pango 1.58.2; nenhuma DLL é versionada no código.

O validador de documentos também aceita CNPJ alfanumérico, além de CPF/CNPJ numéricos. Referência: [manual técnico de dígito verificador da Receita Federal](https://www.gov.br/receitafederal/pt-br/centrais-de-conteudo/publicacoes/documentos-tecnicos/cnpj/manual-dv-cnpj.pdf).
