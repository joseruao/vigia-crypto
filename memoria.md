# Memoria do Projeto - AI Business Auditor

## 1. Visao

O objetivo deste projeto e criar uma plataforma de auditoria empresarial com IA capaz de encontrar dinheiro escondido dentro de uma empresa.

O produto nao deve ser "mais um chatbot".

O produto deve responder sempre a uma pergunta:

> Onde e que esta empresa esta a perder dinheiro sem saber?

A primeira versao com compras semanais para PMEs e apenas uma porta de entrada. A visao maior e auditar empresas maiores, analisando documentos reais, historico financeiro, compras, faturas, fornecedores, contratos, pagamentos, inventario e operacoes.

O objetivo final e entregar relatorios concretos do tipo:

- "Nesta fatura podia ter poupado 842 EUR."
- "Este fornecedor aumentou os precos 18% em 3 meses."
- "Estas duas faturas parecem duplicadas."
- "Este produto esta a ser comprado acima do preco de mercado."
- "Ha fornecedores alternativos melhores para esta categoria."
- "Existe uma oportunidade de renegociacao neste contrato."
- "Esta empresa esta a perder dinheiro todos os meses neste processo."

O principio comercial e simples:

> Find hidden money.

## 2. Filosofia do produto

O produto so deve existir se conseguir gerar valor mensuravel.

Cada modulo deve produzir uma descoberta util:

- poupanca estimada
- risco financeiro
- anomalia
- oportunidade de negociacao
- desperdicio
- processo ineficiente
- custo escondido

Nao construir dashboards bonitos sem uma descoberta concreta.

Nao apresentar texto generico.

Nao fazer "IA a opinar" sem dados.

Nao usar o modelo para fazer contas finais.

A IA serve para:

- ler documentos dificeis
- extrair informacao
- normalizar nomes
- identificar equivalencias
- explicar resultados
- ajudar a gerar relatorios
- sugerir investigacoes

O codigo local serve para:

- calcular
- comparar
- validar
- guardar historico
- gerar evidencias
- produzir numeros auditaveis

## 3. Nova direcao: auditoria de empresas maiores

A partir daqui, o foco deve evoluir de "compras semanais de pequenos negocios" para "auditoria empresarial assistida por IA".

Isto significa analisar dados e documentos mais amplos:

- faturas de compra
- faturas de venda
- extratos bancarios
- mapas de pagamentos
- balancetes
- listagens de fornecedores
- listagens de clientes
- contratos
- encomendas
- guias de transporte
- notas de credito
- inventario
- relatorios internos
- folhas Excel
- PDFs
- emails exportados
- documentos contabilisticos

O sistema deve conseguir funcionar como uma camada inteligente por cima da informacao da empresa.

Nao substitui o ERP.

Nao substitui o contabilista.

Nao substitui o auditor humano.

O objetivo e encontrar sinais que uma pessoa pode nao ver porque ha demasiados documentos, demasiadas linhas e demasiadas rotinas.

## 4. Onde corre

O plano para auditorias maiores e correr no proprio PC.

Isto e importante porque documentos empresariais podem ser sensiveis.

Ambiente principal:

- Windows
- repo atual: `C:\Users\joser\vigia_crypto`
- processamento local sempre que possivel
- dados guardados localmente primeiro
- chamadas externas a modelos so quando necessario

Motores possiveis:

- Azure OpenAI
- Azure AI Document Intelligence, se for preciso OCR/extracao estruturada
- Mistral, quando fizer sentido por custo, privacidade ou performance
- modelos locais no futuro, se forem bons o suficiente

Regra:

> Documentos sensiveis devem ser processados localmente sempre que possivel. Quando for usado Azure/OpenAI/Mistral, o sistema deve deixar claro que conteudo e enviado para fora.

## 5. Arquitetura geral pretendida

A arquitetura deve ser modular.

Cada modulo de auditoria deve encaixar no mesmo nucleo.

Estrutura mental:

```txt
documentos
  -> extracao
  -> normalizacao
  -> armazenamento estruturado
  -> regras e calculos locais
  -> deteccao de anomalias/oportunidades
  -> explicacao por IA
  -> relatorio final
```

Componentes principais:

```txt
ingestion/
  recebe ficheiros e identifica tipo de documento

extractors/
  extrai texto, tabelas, campos e metadados

normalizers/
  normaliza fornecedores, produtos, NIFs, datas, moedas e unidades

core/
  regras de negocio, comparacoes, calculos e scoring

audits/
  modulos especificos de auditoria

storage/
  base de dados local e historico

reports/
  relatorios finais em HTML/PDF/Markdown

ai/
  chamadas a Azure OpenAI, OpenAI, Mistral ou modelos locais

ui/
  interface para carregar documentos, configurar auditorias e ver resultados
```

## 6. Regra de ouro da IA

A IA nao deve decidir sozinha.

Ela pode ajudar a interpretar, mas a conclusao deve ser rastreavel.

Errado:

> "A IA diz que este fornecedor e melhor."

Certo:

> "O sistema calculou que este fornecedor e 7,8% mais barato em 42 linhas comparaveis. A IA explica a razao em linguagem humana."

Todos os achados devem ter:

- fonte
- documento
- linha ou evidencia
- calculo
- nivel de confianca
- explicacao
- proximo passo recomendado

## 7. Tipos de auditoria que queremos suportar

### 7.1 Compras e fornecedores

Objetivo:

Encontrar onde a empresa compra caro, compra mal, perde descontos ou podia negociar melhor.

Deteccoes:

- produto comprado acima do melhor preco disponivel
- fornecedor que aumentou preco de forma anormal
- fornecedor mais caro de forma recorrente
- produtos equivalentes com melhor condicao comercial
- ofertas nao aproveitadas
- descontos perdidos
- condicoes de pagamento piores
- custos de entrega escondidos
- concentracao excessiva num fornecedor
- oportunidade de consolidar compras
- oportunidade de negociar volume

Este modulo nasceu do MVP `/pme`.

O MVP atual compara catalogos e listas de compra.

Proximo passo natural:

- upload de faturas antigas
- dizer "na semana passada teria poupado X"
- comparar fatura paga contra catalogos/alternativas
- criar historico de precos

### 7.2 Faturas duplicadas

Objetivo:

Encontrar faturas iguais ou quase iguais pagas mais de uma vez.

Campos importantes:

- fornecedor
- NIF
- numero da fatura
- data
- total
- IVA
- linhas
- referencia de pagamento

Deteccoes:

- mesmo numero de fatura repetido
- mesmo fornecedor, mesmo total, datas proximas
- mesmas linhas com outro numero
- duplicados por erro de OCR
- duplicados entre centros de custo

### 7.3 Pagamentos duplicados

Objetivo:

Encontrar dinheiro pago duas vezes.

Fontes:

- extratos bancarios
- ficheiros SEPA
- mapa de pagamentos
- faturas

Deteccoes:

- mesmo montante para o mesmo fornecedor em datas proximas
- pagamento sem fatura associada
- fatura marcada como paga duas vezes
- pagamento com referencia repetida

### 7.4 Faturas em falta

Objetivo:

Encontrar compras/pagamentos sem documento ou documentos sem pagamento.

Deteccoes:

- pagamento sem fatura
- fatura sem pagamento
- nota de credito sem ligacao
- fornecedor com saldo estranho
- documento fora da sequencia esperada

### 7.5 Contratos

Objetivo:

Encontrar custos escondidos e oportunidades de renegociacao.

Documentos:

- contratos de telecomunicacoes
- energia
- seguros
- rendas
- software
- manutencao
- leasing
- limpeza
- seguranca
- logistica

Deteccoes:

- renovacao automatica proxima
- preco acima de mercado
- penalizacao escondida
- clausula desfavoravel
- servico nao utilizado
- contrato duplicado
- aumento anual automatico
- oportunidade de renegociar

### 7.6 Inventario e consumo

Objetivo:

Encontrar desperdicio, desvios e compras anormais.

Deteccoes:

- consumo acima do normal
- quebras anormais
- compra sem saida correspondente
- produto parado
- stock excessivo
- produto comprado de novo apesar de haver stock
- rotacao anormal

### 7.7 Clientes e recebimentos

Objetivo:

Encontrar dinheiro por receber, atrasos e risco comercial.

Deteccoes:

- cliente que paga cada vez mais tarde
- faturas vencidas
- notas de credito recorrentes
- concentracao de receita
- descontos excessivos
- margem baixa por cliente

### 7.8 Margens

Objetivo:

Perceber onde a empresa vende muito mas ganha pouco.

Deteccoes:

- produto com margem negativa
- cliente pouco rentavel
- campanha com prejuizo
- fornecedor a corroer margem
- aumento de custo nao refletido no preco de venda

## 8. Estrutura de dados pretendida

No inicio pode ser SQLite local.

Mais tarde pode ser Postgres/Supabase.

Para auditorias no PC, SQLite e suficiente para comecar.

Tabelas nucleares:

```txt
companies
  empresa auditada

documents
  ficheiros carregados

document_pages
  texto/OCR por pagina

document_tables
  tabelas extraidas

suppliers
  fornecedores normalizados

customers
  clientes normalizados

invoices
  cabecalho das faturas

invoice_lines
  linhas das faturas

payments
  pagamentos/extratos

products
  produtos normalizados

product_aliases
  equivalencias de nomes

contracts
  contratos extraidos

audit_runs
  execucoes de auditoria

audit_findings
  achados concretos

audit_evidence
  evidencias ligadas a cada achado

recommendations
  recomendacoes finais
```

Cada achado deve ter pelo menos:

```txt
id
empresa
tipo
titulo
descricao
impacto_estimado_eur
confianca
documentos_origem
evidencia
calculo
proximo_passo
estado
criado_em
```

## 9. Pipeline detalhado

### Passo 1 - Ingestao

O utilizador cria uma auditoria e carrega ficheiros.

Tipos aceites:

- PDF
- DOCX
- XLSX
- CSV
- TXT
- imagens
- ZIP com varios documentos

O sistema guarda:

- nome original
- tipo de ficheiro
- tamanho
- hash
- data de upload
- categoria prevista
- estado de processamento

### Passo 2 - Classificacao do documento

O sistema tenta perceber o que e:

- fatura
- recibo
- contrato
- extrato
- catalogo
- encomenda
- guia
- mapa contabilistico
- documento desconhecido

Esta classificacao pode usar:

- regras locais
- nomes de ficheiro
- texto extraido
- IA, se necessario

### Passo 3 - Extracao

Extrair:

- texto
- tabelas
- campos
- metadados
- entidades

Para PDF textual:

- extracao local com bibliotecas Python

Para scan/imagem:

- OCR local ou Azure Document Intelligence

Para documentos complexos:

- IA para transformar em JSON validado

### Passo 4 - Normalizacao

Normalizar:

- datas
- moedas
- NIFs
- fornecedores
- produtos
- unidades
- quantidades
- numeros de fatura
- referencias

Exemplo:

```txt
"Coca-Cola 24x33cl"
"Coca Cola lata 33 cl cx24"
"CC 24*0.33"
```

Podem ser o mesmo produto.

A IA pode sugerir equivalencias.

O sistema deve guardar a equivalencia e permitir corrigir.

### Passo 5 - Regras locais

Aqui vivem os calculos.

Exemplos:

- preco unitario
- preco por kg/litro/unidade
- custo efetivo apos descontos/ofertas
- variacao percentual
- diferenca face ao historico
- duplicacao provavel
- margem estimada
- impacto anualizado

### Passo 6 - Deteccao

Cada modulo gera findings.

Exemplo:

```txt
Tipo: Compra acima do melhor preco
Produto: Coca-Cola 24x33cl
Fatura paga: 18,91 EUR
Melhor alternativa: 18,40 EUR
Quantidade: 20
Poupanca: 10,20 EUR
Confianca: alta
```

### Passo 7 - Explicacao

A IA recebe os achados ja calculados e transforma em relatorio claro.

Ela nao deve inventar valores.

Ela deve receber:

- dados estruturados
- calculos
- evidencias
- limite de incerteza
- idioma

### Passo 8 - Relatorio

Relatorio deve ter:

- resumo executivo
- dinheiro encontrado
- top 10 oportunidades
- top riscos
- evidencias
- recomendacoes
- proximos passos

Formato:

- HTML no browser
- PDF exportavel
- Markdown interno

## 10. Interface pretendida

A interface deve ser simples e operacional.

Nao deve parecer landing page.

Primeiro ecra:

```txt
Nova auditoria
Upload de documentos
Estado de processamento
Achados encontrados
Relatorio
```

Vistas principais:

- Auditorias
- Documentos
- Achados
- Fornecedores
- Produtos
- Faturas
- Contratos
- Relatorios
- Configuracao

Cada achado deve mostrar:

- impacto em EUR
- confianca
- documentos usados
- explicacao
- acao recomendada

## 11. Modos de funcionamento

### Modo local privado

Corre no PC.

Ideal para:

- documentos sensiveis
- testes
- auditorias grandes
- validacao manual

Dados ficam locais.

IA externa so se for escolhida.

### Modo cloud controlado

Futuro.

Ideal para:

- clientes que aceitam cloud
- processamento recorrente
- equipas
- historico partilhado

Exige:

- autenticacao
- permissoes
- logs
- isolamento por empresa
- backups
- politica clara de dados

## 12. Configuracao de IA

Deve existir uma camada unica de providers.

Exemplo:

```txt
AI_PROVIDER=azure_openai
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=...

AI_PROVIDER=mistral
MISTRAL_API_KEY=...
MISTRAL_MODEL=...
```

O codigo da app nao deve ficar preso a um fornecedor.

Interface desejada:

```python
ai.extract_json(prompt, schema)
ai.summarize(context)
ai.explain_findings(findings)
ai.match_products(product_a, product_b)
```

Por baixo, pode usar Azure OpenAI, OpenAI, Mistral ou outro motor.

## 13. Privacidade e seguranca

Isto e essencial.

Regras:

- nunca enviar documentos para IA sem o utilizador saber
- separar processamento local de processamento cloud
- guardar logs do que foi enviado
- permitir apagar auditoria
- nao guardar chaves no codigo
- usar `.env`
- nao commitar documentos de clientes
- nao commitar bases de dados com dados reais
- mascarar dados sensiveis quando possivel

Para empresas maiores, isto tem de ser levado a serio desde cedo.

## 14. O que nao fazer

Nao construir tudo de uma vez.

Nao criar um ERP.

Nao criar um dashboard generico.

Nao depender 100% da IA.

Nao apresentar achados sem evidencia.

Nao dizer "poupou X" se o calculo nao e rastreavel.

Nao automatizar emails ou decisoes sem aprovacao humana.

Nao enviar dados sensiveis para cloud por defeito.

## 15. Ordem de desenvolvimento recomendada

### Fase 1 - Auditoria de compras retroativa

Objetivo:

Pegar em faturas antigas + catalogos/fornecedores e dizer:

> Nesta fatura podia ter poupado X.

Entradas:

- faturas antigas
- catalogos de fornecedores
- lista de produtos equivalentes

Saidas:

- poupanca por produto
- poupanca por fatura
- poupanca total
- fornecedor alternativo
- evidencia

### Fase 2 - Historico de precos

Objetivo:

Mostrar evolucao de precos por fornecedor/produto.

Perguntas:

- quem aumentou preco?
- qual produto ficou caro?
- quando aconteceu?
- quanto custou esse aumento?

### Fase 3 - Duplicados e pagamentos

Objetivo:

Encontrar dinheiro pago a mais.

Entradas:

- faturas
- extratos
- mapas de pagamentos

Saidas:

- duplicados provaveis
- pagamentos sem fatura
- faturas sem pagamento

### Fase 4 - Contratos

Objetivo:

Encontrar custos recorrentes escondidos e renegociacoes.

### Fase 5 - Auditoria empresarial completa

Objetivo:

Unir compras, pagamentos, contratos, inventario, clientes e margens.

## 16. Como avaliar se o produto esta a resultar

Metricas:

- dinheiro encontrado por auditoria
- % de achados confirmados pelo humano
- tempo poupado ao analisar documentos
- numero de falsos positivos
- valor potencial anualizado
- facilidade de explicar ao cliente

O produto so esta bom se o cliente disser algo como:

> Eu nao sabia que estava a perder este dinheiro.

## 17. Estado atual no repo

Existe um MVP em `/pme`.

Ele faz:

- upload de catalogos
- comparacao de compras
- valorizacao de ofertas
- lista de compras semanal
- recomendacoes com poupanca estimada

O ficheiro de SQL inicial esta em:

```txt
nova_db/create_pme_procurement_tables.sql
```

Ha tambem uma nota mais pequena em:

```txt
docs/ai_business_auditor_pme.md
```

Mas a nova direcao e mais ampla:

> passar de compras semanais para auditoria empresarial local no PC.

## 18. Proximo passo pratico

Criar um modo local de auditoria com uma pasta de trabalho.

Exemplo:

```txt
audits/
  empresa_x/
    input/
      faturas/
      contratos/
      extratos/
      catalogos/
    extracted/
    db/
    reports/
```

Depois criar um comando:

```txt
python -m auditor run audits/empresa_x
```

Esse comando deve:

1. ler os documentos
2. extrair informacao
3. guardar em base local
4. correr os modulos de auditoria
5. gerar relatorio

## 19. Forma ideal de trabalhar

Sempre que houver uma ideia nova:

1. escrever o caso de uso real
2. definir documentos necessarios
3. definir output esperado
4. implementar o minimo
5. testar com documentos reais
6. so depois automatizar mais

Exemplo:

```txt
Caso: faturas antigas
Entrada: 10 faturas + 3 catalogos
Pergunta: onde teria poupado?
Output: tabela de poupanca por produto/fatura
```

## 20. Frase norte

O produto deve fazer uma empresa sentir isto:

> Acabei de descobrir dinheiro que estava a perder sem saber.

Se uma funcionalidade nao ajuda a chegar a esta frase, provavelmente ainda nao e prioridade.
