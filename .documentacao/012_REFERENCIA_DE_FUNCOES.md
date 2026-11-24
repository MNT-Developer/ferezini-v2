# 012 — Referência de funções

[Guia](001_GUIA_DA_DOCUMENTACAO.md) · Base documental 1.0.0.

Catálogo conferido com as declarações do código: **212 funções/métodos Python** de execução e manutenção e **52 funções JavaScript nomeadas**. Inclui métodos privados, propriedades calculadas e auxiliares locais nomeados; não altera docstrings do código. As assinaturas identificam entradas. A descrição informa responsabilidade e efeito; contratos e saídas de cada fluxo são detalhados nos documentos 003–010.

Funções herdadas de Django/bibliotecas, lambdas/callbacks anônimos, testes e migrações não são APIs próprias operacionais. Testes e migrações têm seus mapas nos documentos 011 e 003. Arquivos de URLs/settings/AppConfig/entrypoints sem funções próprias são descritos no documento 002. Exceções ConflitoVersao e JustificativaObrigatoria sinalizam erros específicos do fluxo financeiro.

## .codex/scripts/atualizar.py

[Fonte](../.codex/scripts/atualizar.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `main()` | Força produção e executa verificação, migrações, estáticos e pedido de restart sequencialmente. |

## .codex/scripts/formatar_templates.py

[Fonte](../.codex/scripts/formatar_templates.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `main()` | Executa djlint fixado em modo escrita ou verificação e normaliza LF quando formata. |

## .codex/scripts/instalar.py

[Fonte](../.codex/scripts/instalar.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `main()` | Valida ambiente, instala manifesto e cria .env/tmp somente quando necessário, sem exibir segredo. |

## .codex/scripts/preparar_modelo_xlsm.py

[Fonte](../.codex/scripts/preparar_modelo_xlsm.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `main()` | Valida origem/destino e gera cópia limpa do modelo com substituição explícita. |

## .codex/scripts/processar_emails.py

[Fonte](../.codex/scripts/processar_emails.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `main()` | Valida limite e chama o comando de fila em configuração de produção. |

## .codex/scripts/testar.py

[Fonte](../.codex/scripts/testar.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `main()` | Configura isolamento, cria nome MySQL temporário não existente e executa os alvos de testes. |

## .codex/scripts/verificar_ambiente.py

[Fonte](../.codex/scripts/verificar_ambiente.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `verificar()` | Inicializa produção e verifica segurança, conexão/InnoDB e geração de PDF em memória sem transmitir email. |

## apps/accounts/admin.py

[Fonte](../apps/accounts/admin.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `UsuarioAdmin.get_queryset(self, request)` | Filtra contas de Diretoria/superusuário no Django Admin conforme o operador. |
| `UsuarioAdmin.get_fieldsets(self, request, obj=None)` | Oculta a permissão Diretoria para quem não pode concedê-la. |
| `UsuarioAdmin.get_readonly_fields(self, request, obj=None)` | Torna is_superuser somente leitura para administradores que não são superusuários. |
| `UsuarioAdmin.alvo_permitido(request, obj)` | Confere se o operador pode visualizar/alterar o alvo no Admin. |
| `UsuarioAdmin.has_view_permission(self, request, obj=None)` | Combina restrição do alvo com a autorização nativa de visualização. |
| `UsuarioAdmin.has_change_permission(self, request, obj=None)` | Combina restrição do alvo com a autorização nativa de edição. |
| `UsuarioAdmin.has_delete_permission(self, request, obj=None)` | Recusa a exclusão de usuários pelo Admin. |
| `UsuarioAdmin.save_model(self, request, obj, form, change)` | Revalida privilégios bloqueados, impede promoção indevida e audita escrita do Admin. |
| `UsuarioAdmin.user_change_password(self, request, id, form_url='')` | Confere o alvo e os privilégios antes da troca de senha administrativa. |
| `UsuarioAdmin.log_change(self, request, obj, message)` | Mantém o log nativo e adiciona auditoria de alterações do Admin, incluindo troca de senha. |
| `UsuarioAdmin.dados_auditaveis(obj)` | Extrai campos concretos do usuário excluindo password. |

## apps/accounts/context_processors.py

[Fonte](../apps/accounts/context_processors.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `permissoes(request)` | Expõe aos templates o dicionário de acessos operacionais do usuário. |

## apps/accounts/forms.py

[Fonte](../apps/accounts/forms.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `FuncionarioForm.__init__(self, *args, operador=None, **kwargs)` | Configura campos, ordem e disponibilidade da flag Diretoria conforme o operador. |
| `FuncionarioForm.clean(self)` | Rejeita concessão forjada da flag Diretoria por operador sem autorização. |
| `FuncionarioForm.clean_senha(self)` | Exige senha na criação e aplica os validadores configurados quando informada. |

## apps/accounts/hashers.py

[Fonte](../apps/accounts/hashers.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `SenhaSemCaixaHasher.encode(self, password, salt, iterations=None)` | Aplica casefold à senha antes da codificação PBKDF2. |

## apps/accounts/management/commands/criar_gestor.py

[Fonte](../apps/accounts/management/commands/criar_gestor.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `Command.add_arguments(self, parser)` | Declara argumentos do comando de criação do gestor. |
| `Command.handle(self, *args, **options)` | Executa criação do gestor operacional e suas flags. |

## apps/accounts/middleware.py

[Fonte](../apps/accounts/middleware.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `RedefinicaoSenhaMiddleware.__init__(self, get_response)` | Armazena o callable da próxima etapa do processamento HTTP. |
| `RedefinicaoSenhaMiddleware.__call__(self, request)` | Redireciona usuários com senha legada pendente à redefinição e libera somente as exceções previstas. |

## apps/accounts/models.py

[Fonte](../apps/accounts/models.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `UsuarioManager.get_by_natural_key(self, username)` | Localiza username sem distinção de caixa e falha diante de contas ambíguas. |
| `Usuario.delete(self, *args, **kwargs)` | Recusa exclusão física; preserva histórico e orienta inativação quando aplicável. |
| `Usuario.clean(self)` | Rejeita username duplicado sem distinção de caixa. |
| `Usuario.check_password(self, raw_password)` | Confere a senha legada com grafia original enquanto exige redefinição; depois usa o hasher configurado. |
| `Usuario.set_password(self, raw_password)` | Define hash da nova senha e remove a exigência de redefinição. |
| `Usuario.save(self, *args, **kwargs)` | Inclui a exigência de redefinição ao salvar alteração parcial de senha. |

## apps/accounts/permissions.py

[Fonte](../apps/accounts/permissions.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `tem_permissao(usuario, area)` | Decide acesso à área considerando autenticação, atividade e flags aceitas. |
| `pode_gerenciar_diretoria(usuario)` | Autoriza Diretoria ou superusuário ativo a gerenciar contas da Diretoria. |
| `filtrar_diretoria(operador, usuarios)` | Remove contas da Diretoria do queryset quando o operador não pode gerenciá-las. |
| `exigir_gestao_do_usuario(operador, usuario)` | Recusa gestão de uma conta da Diretoria por operador sem autorização. |
| `exigir_concessao_diretoria(operador, diretoria)` | Impede conceder a flag de Diretoria sem privilégio explícito. |
| `exigir_permissao(usuario, area)` | Lança PermissionDenied quando a área não é permitida. |
| `pode_alterar_responsavel(usuario, projeto)` | Permite primeiro vínculo; depois exige acesso a projetos e Diretoria/Administrativo. |
| `permissao_necessaria(area)` | Cria decorador de autorização de uma área. |
| `permissao_necessaria.decorator(view)` | Recebe a view que será protegida pelo decorador da área. |
| `permissao_necessaria.decorator.protegida(request, *args, **kwargs)` | Confere acesso antes de encaminhar a chamada à view original. |

## apps/accounts/utils.py

[Fonte](../apps/accounts/utils.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `redefinir_senha(usuario, senha)` | Bloqueia o usuário, valida a nova senha, grava hash/versão e audita sem conteúdo secreto. |
| `bloquear_usuarios_gestao(operador, usuario_id=None)` | Relê e bloqueia operador/alvo em ordem fixa de ID, verificando atividade e existência. |
| `salvar_funcionario(operador, form)` | Cria/edita usuário com versão, campos permitidos, regras de Diretoria e auditoria transacional. |
| `alterar_estado_usuario(operador, pk, ativo, versao)` | Inativa/reativa usuário com versão atual, autorização e auditoria. |

## apps/accounts/views.py

[Fonte](../apps/accounts/views.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `redefinir_senha_obrigatoria(request)` | Apresenta redefinição obrigatória e atualiza a sessão após gravar a senha. |
| `entrar(request)` | Valida LoginForm, cria sessão e aceita somente redirecionamento next seguro. |
| `sair(request)` | Encerra a sessão em requisição POST. |
| `lista(request)` | Lista usuários permitidos, com busca, situação e paginação de 25. |
| `criar(request)` | Valida formulário de novo usuário e delega a gravação autorizada. |
| `editar(request, pk)` | Obtém alvo visível e delega edição com versão/permissões. |
| `estado(request, pk, ativo)` | Apresenta confirmação e delega inativação/reativação do usuário. |

## apps/auditoria/models.py

[Fonte](../apps/auditoria/models.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `HistoricoQuerySet.update(self, **kwargs)` | Recusa atualizações em massa proibidas ou em campos imutáveis, conforme o queryset deste modelo. |
| `HistoricoAlteracao.save(self, *args, **kwargs)` | Recusa alteração de evento já gravado e persiste novo evento de auditoria. |
| `HistoricoAlteracao.delete(self, *args, **kwargs)` | Recusa exclusão física; preserva histórico e orienta inativação quando aplicável. |

## apps/auditoria/utils.py

[Fonte](../apps/auditoria/utils.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `registrar(usuario, objeto, acao, anteriores=None, novos=None, justificativa='', correlacao=None)` | Cria auditoria com autor, entidade, projeto identificável, antes/depois e correlação. |

## apps/core/models.py

[Fonte](../apps/core/models.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `SemExclusaoQuerySet.delete(self)` | Recusa exclusão física; preserva histórico e orienta inativação quando aplicável. |
| `SemExclusaoQuerySet.update(self, **kwargs)` | Recusa atualizações em massa proibidas ou em campos imutáveis, conforme o queryset deste modelo. |
| `SemExclusaoQuerySet.bulk_create(self, objs, *args, **kwargs)` | Recusa operação em massa que contornaria validação individual e auditoria. |
| `SemExclusaoQuerySet.bulk_update(self, objs, fields, *args, **kwargs)` | Recusa operação em massa que contornaria validação individual e auditoria. |
| `RegistroNegocio.save(self, *args, **kwargs)` | Executa full_clean antes de persistir o registro de negócio. |
| `RegistroNegocio.delete(self, *args, **kwargs)` | Recusa exclusão física; preserva histórico e orienta inativação quando aplicável. |

## apps/core/templatetags/huminize_extras.py

[Fonte](../apps/core/templatetags/huminize_extras.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `numero_br(valor)` | Expõe a formatação brasileira como filtro da biblioteca huminize_extras. |

## apps/core/views.py

[Fonte](../apps/core/views.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `inicio(request)` | Calcula cards agregados e projetos visíveis para quem acessa projetos. |
| `relatorios_gerais(request)` | Renderiza a tela de funcionalidade em desenvolvimento após conferir acesso. |
| `diretoria(request)` | Renderiza a tela de funcionalidade em desenvolvimento da Diretoria. |

## apps/despesas/models.py

[Fonte](../apps/despesas/models.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `Despesa.clean(self)` | Define completude, valida documento e integridade etapa/item/lote e preserva vínculo confirmado. |
| `Despesa.__str__(self)` | Retorna identificação textual de Despesa para exibição e logs. |

## apps/envios/forms.py

[Fonte](../apps/envios/forms.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `PrepararLoteForm.__init__(self, projeto, *args, **kwargs)` | Configura despesas e contatos disponíveis da obra para preparar o lote. |
| `PrepararLoteForm.clean(self)` | Valida seleção, taxa, modalidade e destinatários do preparo. |
| `ReenvioForm.clean_destinatarios(self)` | Converte e valida os destinatários textuais do reenvio. |

## apps/envios/management/commands/processar_emails_pendentes.py

[Fonte](../apps/envios/management/commands/processar_emails_pendentes.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `Command.add_arguments(self, parser)` | Declara argumentos do comando de processamento da fila. |
| `Command.handle(self, *args, **options)` | Recupera reservas expiradas e processa tentativas vencidas até o limite informado. |

## apps/envios/models.py

[Fonte](../apps/envios/models.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `HistoricoQuerySet.delete(self)` | Recusa exclusão física; preserva histórico e orienta inativação quando aplicável. |
| `HistoricoQuerySet.update(self, **kwargs)` | Recusa atualizações em massa proibidas ou em campos imutáveis, conforme o queryset deste modelo. |
| `HistoricoQuerySet.bulk_create(self, objs, *args, **kwargs)` | Recusa operação em massa que contornaria validação individual e auditoria. |
| `HistoricoQuerySet.bulk_update(self, objs, fields, *args, **kwargs)` | Recusa operação em massa que contornaria validação individual e auditoria. |
| `RegistroHistorico.delete(self, *args, **kwargs)` | Recusa exclusão física; preserva histórico e orienta inativação quando aplicável. |
| `RegistroHistorico.save(self, *args, **kwargs)` | Recusa mudanças nos campos confirmados, valida e salva campos operacionais permitidos. |
| `LoteEnvioDespesa.__str__(self)` | Retorna identificação textual de LoteEnvioDespesa para exibição e logs. |
| `LoteEnvioDespesa.clean(self)` | Confere total = notas + taxa aplicada e exige justificativa da taxa ajustada. |
| `LoteEnvioItem.clean(self)` | Confere correspondência entre projeto, despesa e vínculo oficial do lote. |

## apps/envios/utils.py

[Fonte](../apps/envios/utils.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `calcular_taxa_servico(valor, percentual)` | Calcula percentual sobre subtotal com HALF_UP em centavos. |
| `valor_monetario(valor)` | Valida taxa como decimal finito não negativo, no limite e com no máximo duas casas. |
| `validar_destinatarios(destinatarios)` | Normaliza, valida e deduplica uma lista não vazia de emails. |
| `despesas_elegiveis(projeto)` | Consulta notas ativas/completas/positivas, de etapa ativa e sem lote. |
| `snapshot_despesa(despesa)` | Congela nota e referências de etapa/item sem copiar o cadastro da obra. |
| `resumo_selecao(projeto, despesas, valor_taxa=None, justificativa_taxa='')` | Soma notas, calcula/aplica taxa e exige justificativa da divergência. |
| `confirmar_lote(usuario, projeto_id, despesa_ids, modalidade='GERAR', valor_taxa=None, justificativa_taxa='', destinatarios=None, chave_confirmacao=None, versoes_despesas=None, versao_projeto=None)` | Confirma seleção idempotente com bloqueios, snapshots, auditoria e tentativa inicial quando solicitada. |
| `solicitar_reenvio(usuario, lote_id, destinatarios)` | Agenda tentativa manual sobre lote existente sem duplicar notas ou confirmação. |
| `gerar_pdf_lote(lote)` | Recarrega dados atuais da obra e gera PDF dos snapshots/taxa históricos. |
| `reservar_tentativa(tentativa_id)` | Toma reserva exclusiva de tentativa vencida e marca envio sem manter SMTP em transação. |
| `finalizar_tentativa(tentativa_id, resultado, erro='', expirada_antes=None)` | Finaliza a reserva, registra resultado e cancela/agenda pendências segundo a política. |
| `TransporteSMTPRastreado.__init__(self, transporte)` | Encapsula o transporte e inicia o registro de recusas parciais. |
| `TransporteSMTPRastreado.__getattr__(self, nome)` | Delega operações não interceptadas ao transporte SMTP encapsulado. |
| `TransporteSMTPRastreado.sendmail(self, *args, **kwargs)` | Captura recusas parciais devolvidas pelo transporte SMTP. |
| `renovar_reserva_para_smtp(tentativa_id)` | Confere propriedade da reserva e renova os timestamps antes de transmitir. |
| `processar_tentativa(tentativa_id)` | Reserva, gera PDF, envia BCC e classifica sucesso, falha conhecida ou resultado incerto. |
| `recuperar_reservas_expiradas()` | Marca processamentos interrompidos há mais de 15 minutos como incertos. |

## apps/envios/views.py

[Fonte](../apps/envios/views.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `painel(request, projeto_id)` | Mostra notas elegíveis e histórico de lotes do projeto autorizado. |
| `preparar(request, projeto_id)` | Valida seleção e monta prévia com valores/versões antes de confirmar. |
| `confirmar(request, projeto_id)` | Recebe confirmação e delega a criação idempotente do lote. |
| `detalhe(request, lote_id)` | Exibe lote e seus dados históricos. |
| `pdf(request, lote_id)` | Serve download PDF do lote após autorização. |
| `reenviar(request, lote_id)` | Valida destinatários e solicita tentativa manual do lote. |

## apps/orcamentos/models.py

[Fonte](../apps/orcamentos/models.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `Orcamento.clean(self)` | Soma composição, valida precisão, define rascunho e impede criação em etapa inativa. |
| `Orcamento.total(self)` | Retorna zero em rascunho ou quantidade × preço unitário arredondado em centavos. |
| `Orcamento.__str__(self)` | Retorna identificação textual de Orcamento para exibição e logs. |

## apps/projetos/exportacao.py

[Fonte](../apps/projetos/exportacao.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `_etapas(projeto)` | Prepara etapas/itens/notas atuais ativos e representação manual das taxas para exportar. |
| `_nota(aba, linha, nota)` | Preenche D:J da nota exportada com valores, datas e estilos do modelo. |
| `exportar_projeto(usuario, projeto_id)` | Lê modelo, preenche dados/fórmulas/CF e retorna bytes XLSM preservando partes nativas. |

## apps/projetos/forms.py

[Fonte](../apps/projetos/forms.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `PercentualInput.format_value(self, value)` | Exibe percentual decimal com duas casas no campo numérico do projeto. |
| `ProjetoForm.__init__(self, *args, usuario=None, **kwargs)` | Configura seleção permitida, ordem de campos, aparência, contatos e versão inicial. |
| `ProjetoForm.responsavel_selecionado(self)` | Obtém o responsável validado ou a seleção inicial do formulário. |
| `ProjetoForm.nome_responsavel_selecionado(self)` | Retorna primeiro nome, ou username, do colaborador selecionado. |
| `ProjetoForm.clean_responsavel_tecnico(self)` | Valida primeira seleção/troca, atividade, exclusão de superusuários e autorização. |
| `ProjetoForm.clean_tamanho(self)` | Converte tamanho não informado em zero. |
| `ProjetoForm.clean_emails(self)` | Normaliza lista de contatos, valida endereços e rejeita duplicatas. |
| `ImportarProjetoForm.clean_arquivo(self)` | Recusa upload vazio ou acima de 20 MB. |

## apps/projetos/importacao.py

[Fonte](../apps/projetos/importacao.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `_cabecalho(texto)` | Normaliza cabeçalhos removendo diferenças de caixa/espaços/acentos. |
| `_colunas_orcamento(leitor)` | Detecta colunas pelo cabeçalho ou fallback acordado e rejeita ambiguidades. |
| `ler_planilha(conteudo, nome)` | Lê as três abas e constrói plano de projeto, etapas, itens, notas e avisos antes de gravar. |
| `_salvar(objeto, origem, usuario, correlacao)` | Salva registro importado com contexto da célula e auditoria correlacionada. |
| `_lotes_historicos(usuario, projeto, grupos, correlacao)` | Agrupa notas por dia e cria lotes importados sem taxa/email, com snapshots. |
| `importar_projeto(usuario, arquivo)` | Valida arquivo/acesso, deduplica por hash e persiste o plano integralmente ou desfaz tudo. |

## apps/projetos/models.py

[Fonte](../apps/projetos/models.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `Projeto.clean(self)` | Exige nome não vazio e valida CPF/CNPJ do cliente. |
| `Projeto.__str__(self)` | Retorna identificação textual de Projeto para exibição e logs. |
| `Projeto.nome_responsavel_tecnico(self)` | Obtém nome completo/username da FK ou texto legado preservado. |
| `ProjetoEmail.clean(self)` | Normaliza email e verifica unicidade por obra, inclusive sem distinção de caixa. |
| `ProjetoEmail.__str__(self)` | Retorna identificação textual de ProjetoEmail para exibição e logs. |
| `Etapa.clean(self)` | Exige título não vazio e normaliza espaços externos. |
| `Etapa.__str__(self)` | Retorna identificação textual de Etapa para exibição e logs. |

## apps/projetos/utils.py

[Fonte](../apps/projetos/utils.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `api_financeira(view)` | Envolve endpoints financeiros com autorização e tradução dos erros esperados em JSON. |
| `api_financeira.responder(request, *args, **kwargs)` | Mapeia validação, acesso, conflito, ausência e payload inválido para respostas HTTP apropriadas. |
| `ler_json(request)` | Lê objeto JSON preservando decimais e valida justificativa quando presente. |
| `modelo_por_tipo(tipo)` | Resolve somente etapa, orçamento ou despesa na lista de modelos permitidos. |
| `serializar_registro(objeto)` | Serializa campos e atributos úteis do registro para API/auditoria. |
| `consultar_projetos()` | Prepara queryset com responsável e relações financeiras pré-carregadas. |
| `ordenar_registros(registros, campo)` | Respeita ordem manual, com fallback textual sem acentos e ID. |
| `totais_projeto(projeto)` | Soma orçamento, realizado e taxas confirmadas, calculando saldo e execução. |
| `estrutura_projeto(projeto, exibir_inativos=False)` | Monta árvore compartilhada de etapas/itens/despesas, resumos e taxas para HTML/Fetch. |
| `validar_versao(objeto, versao)` | Impede escrita quando a versão informada diverge da persistida. |
| `validar_justificativa(justificativa)` | Exige texto de justificativa com até 4.000 caracteres e normaliza espaços externos. |
| `validar_identificador(valor)` | Aceita apenas ID inteiro positivo, recusando booleanos e formatos inválidos. |
| `bloquear_registro(tipo, pk, projeto_id=None)` | Confere a obra do registro e bloqueia projeto, etapa e linha em ordem consistente. |
| `exigir_ativo(objeto)` | Recusa edição de registro ou etapa pai inativos. |
| `criar_registro(usuario, tipo, projeto, **dados)` | Cria linha financeira permitida, aplica ordem/validação e audita na transação. |
| `atribuir_valor(objeto, campo, valor)` | Converte valor segundo o campo/FK, recusando tipos não permitidos. |
| `editar_celula(usuario, tipo, pk, campo, valor, versao, justificativa='', projeto_id=None)` | Valida campo, versão e justificativa; atualiza célula, composição de custo e auditoria. |
| `alterar_ativo(usuario, tipo, pk, ativo, versao, justificativa='', projeto_id=None)` | Inativa/reativa registro sem excluir, respeitando filhos ativos, versão e justificativa. |
| `reordenar(usuario, tipo, pai_id, ids=None)` | Valida sequência do agrupamento, grava ordem/versões e correlação de auditoria. |
| `salvar_projeto(usuario, form)` | Salva capa e contatos; atribui responsável padrão na criação e protege trocas na edição. |

## apps/projetos/views.py

[Fonte](../apps/projetos/views.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `listar(request)` | Monta abas por responsável/todos, pastas, filtros título/cliente e página de 25 projetos. |
| `importar(request)` | Recebe upload, valida e delega importação; apresenta erros/avisos e abre a obra. |
| `exportar(request, pk)` | Autoriza obra e serve XLSM em memória com nome seguro; falha volta ao detalhe com mensagem. |
| `novo(request)` | Valida capa de novo projeto, delega criação e redireciona ao detalhe. |
| `editar(request, pk)` | Valida capa e delega atualização do projeto com controle de versão. |
| `colaboradores(request, pk=None)` | Pesquisa colaboradores ativos não superusuários; dez iniciais, busca por termos sem esse limite. |
| `detalhe(request, pk)` | Carrega obra e estrutura financeira para renderizar Geral/Orçamento. |
| `orcamento_etapa(request, pk, etapa_id)` | Abre detalhe da obra restrito à etapa de orçamento selecionada. |
| `dados(request, pk)` | Retorna a árvore financeira atual para o cliente. |
| `nova_linha(request, pk)` | Recebe criação financeira e retorna registro/estrutura e link da etapa nova. |
| `atualizar_linha(request, pk, tipo, registro_id)` | Valida payload PATCH e delega a edição de célula. |
| `estado_linha(request, pk, tipo, registro_id)` | Recebe alteração de ativo e delega ao serviço transacional. |
| `ordem(request, pk)` | Recebe arrastar/restaurar e delega a ordenação do agrupamento. |
| `historico(request, pk)` | Lista auditoria do projeto com filtros de entidade/ID e paginação. |

## apps/relatorios/forms.py

[Fonte](../apps/relatorios/forms.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `PeriodoForm.clean(self)` | Confere coerência entre início e fim do período. |

## apps/relatorios/utils.py

[Fonte](../apps/relatorios/utils.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `despesas_por_periodo(projeto, inicio, fim)` | Consulta snapshots por data do lote e soma notas/taxas sem multiplicar por item. |
| `gerar_pdf_periodo(contexto)` | Recarrega a raiz e gera PDF do contexto de período. |

## apps/relatorios/views.py

[Fonte](../apps/relatorios/views.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `despesas(request, projeto_id)` | Valida período e entrega a consulta HTML ou PDF da obra. |

## utils/datas.py

[Fonte](../utils/datas.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `limites_periodo(inicio, fim)` | Produz intervalo São Paulo com início inclusivo e dia posterior ao fim exclusivo. |

## utils/documentos.py

[Fonte](../utils/documentos.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `normalizar_documento(valor)` | Remove pontuação/espaços de CPF/CNPJ e normaliza letras em maiúsculas. |
| `validar_documento(valor)` | Valida estrutura e dígitos de CPF ou CNPJ numérico/alfanumérico. |

## utils/formatacao.py

[Fonte](../utils/formatacao.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `monetario(valor)` | Arredonda Decimal para centavos com HALF_UP. |
| `formatar_numero_br(valor)` | Formata número finito com milhares e duas casas em padrão brasileiro. |
| `chave_alfabetica(valor)` | Produz chave textual sem acentos e sem distinção de caixa. |

## utils/pdf.py

[Fonte](../utils/pdf.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `gerar_relatorio_pdf(projeto, itens, valor_total, valor_taxa, *, confirmacao=None, inicio=None, fim=None, exibir_taxa=True)` | Monta relatório A4 paisagem em memória, grade 75/25, itens, taxa opcional e paginação. |
| `gerar_relatorio_pdf.seguro(valor)` | Escapa texto e converte quebras de linha para parágrafos seguros do PDF. |
| `gerar_relatorio_pdf.paragrafo(valor, estilo=texto)` | Cria Paragraph ReportLab usando texto escapado e estilo informado. |
| `gerar_relatorio_pdf.moeda(valor)` | Formata valor brasileiro com prefixo monetário para o PDF. |
| `gerar_relatorio_pdf.dado(rotulo, valor)` | Cria célula de identificação da obra com rótulo em destaque. |
| `gerar_relatorio_pdf.CanvasNumerado.__init__(self, *args, **kwargs)` | Inicializa canvas e lista de estados de páginas para numeração do total. |
| `gerar_relatorio_pdf.CanvasNumerado.showPage(self)` | Armazena o estado da página para desenhar Página X de Y após conhecer o total. |
| `gerar_relatorio_pdf.CanvasNumerado.save(self)` | Restaura páginas armazenadas, desenha rodapés com total e finaliza o PDF. |
| `gerar_pdf_teste()` | Gera PDF mínimo para validar a instalação ReportLab. |

## utils/planilhas.py

[Fonte](../utils/planilhas.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `chave(texto)` | Normaliza texto NFKC/casefold/espaços para correspondência nas planilhas. |
| `Celula.ler(self)` | Obtém valor da célula recusando erro Excel ou fórmula sem cache utilizável. |
| `Celula.texto(self)` | Converte célula em texto conservando identificadores e zeros conforme a máscara. |
| `numero(celula, casas=2, padrao=None, percentual=False)` | Interpreta célula numérica/BR/US/percentual e quantiza Decimal não negativo. |
| `LeitorExcel.__init__(self, conteudo, nome)` | Armazena bytes/extensão e inicializa os livros que serão abertos. |
| `LeitorExcel.__enter__(self)` | Abre as visões da planilha, valida formato, expansão, abas obrigatórias e limites. |
| `LeitorExcel.fechar(self)` | Libera livros e recursos do leitor Excel. |
| `LeitorExcel.__exit__(self, *args)` | Fecha os recursos do leitor ao sair do contexto. |
| `LeitorExcel.linhas(self, nome, inicio, max_col)` | Itera células de uma aba com referências, formatos, fórmulas e erros. |
| `LeitorExcel.celula(self, nome, referencia)` | Obtém célula do leitor por referência, retornando vazia quando ausente. |
| `LeitorExcel.data(self, celula)` | Converte data nativa, serial Excel ou texto conhecido em date. |

## utils/xlsm.py

[Fonte](../utils/xlsm.py)

| Função / assinatura | Finalidade |
| --- | --- |
| `tag(nome)` | Qualifica nome XML com namespace SpreadsheetML. |
| `xml(elemento)` | Serializa fragmento XML para reinserir no namespace da planilha original. |
| `AbaXlsm.__init__(self, conteudo)` | Lê XML original e indexa linhas para edição pontual. |
| `AbaXlsm.celula(self, referencia)` | Obtém/cria célula XML por coordenada. |
| `AbaXlsm.limpar(celula)` | Retira valor/tipo/fórmula de célula preservando seus atributos de estilo e posição. |
| `AbaXlsm.limpar_corpo(self, inicio)` | Limpa conteúdo e agrupamentos antigos das linhas a partir do início dos dados. |
| `AbaXlsm.escrever(self, referencia, valor=None, *, formula=None, estilo=None)` | Grava célula tipada, fórmula/cache opcional e estilo; texto permanece inlineStr. |
| `AbaXlsm.cache(self, referencia, valor)` | Atualiza resultado salvo de fórmula preservando a fórmula e seus atributos. |
| `AbaXlsm.salvar(self, condicional=None)` | Reinsere sheetData ordenado e atualiza dimensão/CF preservando o XML externo. |
| `AbaXlsm.salvar.substituir(_)` | Troca o primeiro bloco de CF pelo consolidado e remove fragmentos antigos. |
| `gravar_pacote(original, alteracoes, remover=())` | Copia partes ZIP originais e substitui somente as partes alteradas/excluídas. |
| `regras_projeto(fim)` | Gera CF expandida que identifica cabeçalhos pelo ID positivo na coluna A. |
| `regras_orcamento(fim)` | Gera CF expandida com etapa pela coluna B e item pela C. |
| `preparar_modelo(conteudo)` | Limpa dados/caches/spills do exemplo preservando VBA, desenhos e estrutura do modelo. |

## static/js/app.js

[Fonte](../static/js/app.js). Executa inicializador anônimo: Menu lateral e avisos da aplicação. Os callbacks não são uma API nomeada.

| Função / assinatura | Finalidade |
| --- | --- |
| `window.fereziniToast(message, error = false)` | Mostra texto seguro no aviso global, aplica estado de erro e agenda ocultação após seis segundos. |

## static/js/envios.js

[Fonte](../static/js/envios.js)

| Função / assinatura | Finalidade |
| --- | --- |
| `unidades(valor, casas, localizado = false)` | Converte decimal para inteiro escalado, com suporte à entrada localizada. |
| `decimalCentavos(centavos)` | Transforma centavos inteiros em string decimal canônica. |
| `calcularResumo(valores, percentual)` | Soma seleção e calcula taxa em unidades inteiras com arredondamento. |
| `inicializarEnvio(documento, formatarMoeda)` | Conecta seleção, ajuste de taxa, justificativa e submissão do preparo. |
| `atualizarTaxa()` | Atualiza estado do ajuste/justificativa a partir do campo de taxa. |
| `recalcular(limparAjuste = true)` | Recalcula seleção e total, limpando o ajuste quando solicitado. |

## static/js/formatacao.js

[Fonte](../static/js/formatacao.js)

| Função / assinatura | Finalidade |
| --- | --- |
| `decimalParts(value)` | Separa sinal, parte inteira e fração de string decimal. |
| `formatarMoeda(value)` | Arredonda e formata moeda BR com BigInt, preservando centavos grandes. |
| `compararDecimais(first, second)` | Compara duas strings decimais por escala comum sem perder precisão. |

## static/js/projeto.js

[Fonte](../static/js/projeto.js)

| Função / assinatura | Finalidade |
| --- | --- |
| `element(tag, className, text)` | Cria elemento DOM com classe e texto sem interpolar HTML. |
| `button(text, className, action)` | Cria botão e conecta sua ação. |
| `currency(value)` | Delega a apresentação monetária ao módulo de precisão decimal. |
| `record(type, id)` | Localiza registro na estrutura financeira local. |
| `announce(message, error = false)` | Mostra feedback de salvamento ou erro. |
| `errorText(value)` | Converte resposta de erro em mensagem legível. |
| `api(path, method = "GET", body)` | Executa Fetch com CSRF, JSON e tratamento de falhas esperadas. |
| `enqueue(action)` | Serializa mutações para manter a ordem dos salvamentos. |
| `needsResolution()` | Detecta edição/erro local que deve ser resolvido antes da reconstrução. |
| `beforeRender()` | Aguarda fila e protege alterações locais antes de renderizar. |
| `updateTotals()` | Atualiza cards e resumos com valores oficiais retornados. |
| `renderState(node, obj)` | Atualiza indicação de rascunho, envio ou inatividade. |
| `stateCell(obj, type)` | Cria célula com estado do registro. |
| `showReason(title, description, required = true)` | Abre diálogo de justificativa e devolve a decisão do usuário. |
| `clearCellError(input)` | Remove o feedback de erro da célula. |
| `cellError(input, error, type, id, field)` | Exibe erro e opções de recuperação da edição. |
| `editableCell(obj, type, field, label, inputType = "text", disabled = false)` | Monta campo editável e conecta eventos de mudança/salvamento. |
| `saveCell(input, type, id, field)` | Salva campo/versionamento, lida com justificativa e conserva erro/valor local. |
| `mutate(path, body)` | Envia mutação e aplica a estrutura canônica recebida. |
| `changeState(type, obj)` | Solicita inativação/reativação com justificativa e versão. |
| `historyLink(type, id)` | Monta link de auditoria filtrado por tipo e ID. |
| `actionsFor(type, obj, parentActive = true)` | Cria ações permitidas da linha considerando estado do pai. |
| `subtotalNode(type, obj, field)` | Cria elemento associado a um subtotal da estrutura. |
| `groupTotals(type, obj, fields = ["orcado", "realizado", "saldo"])` | Monta conjunto de totais do agrupamento. |
| `trackedDetails(key, className)` | Cria agrupamento que conserva abertura local após interações. |
| `expenseTable(expenses, stage)` | Renderiza notas, campos, filtros/ordenação e ações. |
| `addExpense(stage, item)` | Cria despesa em etapa e opcionalmente item por endpoint financeiro. |
| `generalStage(stage)` | Renderiza Geral da etapa com itens e Demais Despesas. |
| `draggable(node, type, id, parentId)` | Conecta arrastar/soltar à sequência persistida de etapas/itens. |
| `budgetStage(stage)` | Renderiza os itens editáveis e totais do orçamento da etapa. |
| `stageBudgetLink(stage, text)` | Cria link para a tela exclusiva do orçamento da etapa. |
| `feeGroup()` | Renderiza o grupo de taxas confirmadas do projeto. |
| `normalized(value)` | Normaliza texto para comparação visual sem acento/caixa. |
| `applyExpenseView()` | Aplica filtros/ordem visual às notas sem alterar totais oficiais. |
| `openFilter(field, label)` | Abre diálogo de filtro da coluna escolhida. |
| `render()` | Reconstrói a visão Geral/Orçamento e a etapa exclusiva quando definida. |
| `newStage()` | Solicita título, cria etapa e abre seu orçamento exclusivo. |

## static/js/projetos-lista.js

[Fonte](../static/js/projetos-lista.js). Executa inicializador anônimo: Clique em linhas e diálogo multipart de importação, com bloqueio de submissão dupla. Os callbacks não são uma API nomeada.

## static/js/responsavel-tecnico.js

[Fonte](../static/js/responsavel-tecnico.js)

| Função / assinatura | Finalidade |
| --- | --- |
| `inicializarResponsavel(documento, carregar = globalThis.fetch)` | Conecta os campos de leitura, modal, pesquisa e seleção de colaborador. |
| `cancelarBusca()` | Aborta consulta anterior para evitar respostas obsoletas. |
| `selecionar(colaborador)` | Preenche FK/ID/primeiro nome e fecha o seletor. |
| `buscar()` | Consulta colaboradores e renderiza resultado seguro, ignorando respostas antigas. |
| `abrir()` | Abre o modal e inicia a busca adequada. |
