# 008 — Importação e exportação Excel

[Guia](001_GUIA_DA_DOCUMENTACAO.md) · [Importação](../apps/projetos/importacao.py) · [Exportação](../apps/projetos/exportacao.py) · [Leitor](../utils/planilhas.py) · [OOXML](../utils/xlsm.py).

## Importar

Início/Projetos → modal multipart com CSRF → ImportarProjetoForm → `importar_projeto`. Exige acesso a projetos, aceita XLSM/XLSX/XLS até 20 MB e lê no máximo 20.000 linhas em cada aba obrigatória. OOXML: até 10.000 entradas ZIP e 100 MB descompactados.

`LeitorExcel` usa openpyxl somente leitura em duas visões (valores salvos e fórmulas) ou xlrd para XLS. Não executa macros, links ou fórmulas. `Celula.ler` recusa erro Excel e fórmula importada sem resultado salvo; pede recalcular/salvar no Excel. Totalizadores ignorados não precisam ser lidos. Dates respeitam o epoch do arquivo e aceitam texto brasileiro/ISO. Dinheiro, quantidade e percentuais são Decimal; documentos e NF são texto, incluindo zeros conservados em máscaras conhecidas.

### Painel

| Célula | Campo |
| --- | --- |
| H8 | Cliente |
| H9 | Tipo de obra |
| H10 | Endereço |
| H11 | CPF/CNPJ |
| U11 | RG/IE |
| AL8 | Taxa; número com formato percentual é multiplicado por 100 ao importar |
| AL9 | Tamanho |
| AH11 | Arquiteto |

Nome = Tipo − Cliente, omitindo partes vazias; exige pelo menos uma. Taxa/tamanho vazios assumem zero. Cadastrante torna-se responsável.

### Serviços e Custos

Linha inicial 11. B preenchida abre etapa, C é seu título; B vira detalhe/código da etapa. B vazia e C preenchida representam orçamento da etapa. Cabeçalhos das linhas 8/9 identificam as colunas: no modelo, D unidade, E quantidade, F mão de obra e G material. Sem cabeçalhos, fallback acordado: D quantidade, E mão de obra, G material, unidade vazia. Cabeçalho conflitante é erro.

H:J são totalizadores ignorados. Valor unitário = mão de obra + material; total = quantidade × unitário. Total/subtotal sem item é desconsiderado.

### Projeto

Linha inicial 9. A preenchida abre etapa pelo título B; títulos duplicados são desambiguados por código. Etapa só nesta aba é criada sem orçamento e com aviso. Na mesma linha pode existir uma nota: é preservada sem orçamento.

| Coluna | Campo da nota |
| --- | --- |
| B | Descrição; procura orçamento único dentro da etapa |
| D | Emissão |
| E | Fornecedor |
| F | Observação |
| G | NF/pedido |
| H | Valor |
| I | Vencimento |
| J | Data de envio histórico |

Descrição não encontrada/ambígua gera nota diretamente na etapa e aviso. Nota com J exige fornecedor e valor positivo. Sem J, permanece sem lote, completa ou em rascunho. Um lote histórico é criado por dia, à meia-noite do fuso da aplicação, com taxa zero e sem emails/tentativas.

### Integridade

O plano é lido antes da escrita. A transação cria projeto, etapas, itens, despesas, snapshots, lotes e auditoria correlacionada; falha desfaz tudo. SHA-256 único dos bytes impede duplicar o mesmo arquivo, inclusive na disputa de criação. Arquivo regravado com bytes diferentes não é semanticamente deduplicado. Upload não é arquivado permanentemente. Novos envios posteriores usam taxa normal.

## Exportar

Detalhe → Exportar XLSM → `exportar_projeto` → FileResponse em memória, privado, sem efeitos financeiros. Modelo fixo: [media/modelos/projeto.xlsm](../media/modelos/projeto.xlsm). Os dados atuais ativos de etapas ativas são ordenados como na aplicação; notas por ID definem a primeira despesa.

- Painel usa o mapeamento inverso, taxa dividida por 100. Sem tipo nem cliente, H9 recebe o nome da obra.
- Serviços e Custos: B recebe ID real da etapa e C seu título. Item fica nas linhas seguintes; custos sem composição são exportados em mão de obra, material zero. H/I/J são fórmulas com caches; J da etapa é seu subtotal.
- Projeto: A recebe ID real, B título e C total orçado da etapa. C não é repetido nos detalhes. A primeira nota fica na linha do orçamento; outras seguem abaixo repetindo B para reimportar vínculo. Notas sem orçamento, ou de item inativo, ficam diretamente na etapa. J usa a data local do lote, ou vazio se pendente.
- Taxas aplicadas confirmadas dos lotes normais viram itens/notas na etapa sintética Taxa de Serviço. ID positivo maior que os da obra evita colisão sem criar registro no banco. Não recalcular taxa atual nem duplicar taxa de importados.

`AbaXlsm` altera dados/CF dentro do XML, sem reserializar VBA, desenhos, imagens ou relações de controles. Formatação de Projeto reconhece `$A9>0` e se expande; orçamento reconhece B preenchida. Documentos/NF são texto; conteúdo começando com `=` continua texto. As dez abas e codenames são preservados. Limite de saída também é 20.000 linhas por aba.

O modelo em branco remove dados de exemplo, strings órfãs, caches e spills antigos, preserva fórmulas e solicita recálculo completo. A cadeia antiga é removida. Sua preparação é feita por [preparar_modelo_xlsm.py](../.codex/scripts/preparar_modelo_xlsm.py), sem sobrescrever origem; destino existente exige `--substituir`. O runtime Linux não precisa de Excel instalado.

## Limites do formato

Descrições duplicadas dentro da etapa tornam o vínculo ambíguo; nota sem item cuja descrição coincide com um orçamento pode ser vinculada na reimportação. Nome livre, descrição própria de nota vinculada e campos sem coluna correspondente não têm representação independente no modelo. Rascunhos exportados ainda precisam satisfazer as validações para serem reimportados. Não prometer um backup/restauração integral do banco via Excel.

Macros são preservadas byte a byte, mas sua execução não foi homologada. O modelo tem macros antigas sem vínculo a botões que mencionam aba inexistente `teste`; não foram corrigidas nesta consolidação. A abertura/recálculo nativo foi conferida com macros desabilitadas. Evidências no [011](011_TESTES_VALIDACAO_E_LIMITACOES.md); funções no [012](012_REFERENCIA_DE_FUNCOES.md).
