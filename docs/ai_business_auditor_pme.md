# AI Business Auditor - PME Procurement MVP

## Objetivo

Encontrar dinheiro escondido nas compras semanais de pequenas empresas.

Nesta fase, o cliente nao usa a plataforma diretamente. Os catalogos chegam ao operador, que os carrega manualmente em `/pme`.

## Regra central

O sistema nao escolhe o produto mais barato. Escolhe a melhor compra.

Para isso, separa:

- preco bruto
- ofertas e condicoes comerciais
- valor economico estimado dessas ofertas
- custo efetivo
- quantidade que a empresa vai comprar nessa semana
- poupanca semanal estimada

Exemplo:

- Fornecedor A: Coca-Cola a 18,90 EUR
- Fornecedor B: Coca-Cola a 18,91 EUR + 10 copos
- Valor estimado dos copos: 8,00 EUR
- Custo efetivo B: 10,91 EUR
- Recomendacao: Fornecedor B

## Papel da IA

A IA deve ajudar apenas onde acrescenta valor:

- ler PDFs, imagens e catalogos dificeis
- normalizar nomes de produto
- identificar produtos equivalentes
- extrair ofertas comerciais de texto livre
- explicar a recomendacao ao cliente

A IA nao deve fazer as contas finais. Precos, descontos, ofertas, custos efetivos e poupancas devem ser calculados em codigo local.

## Persistencia

O SQL base esta em `nova_db/create_pme_procurement_tables.sql`.

As entidades principais sao:

- fornecedores
- uploads de catalogos
- itens de catalogo
- termos comerciais/ofertas
- listas de compra
- necessidades de compra
- runs de recomendacao
- recomendacoes finais

## Segurança

`/pme` nao esta ligado na navegacao publica.

Em producao, configurar:

- `PME_ACCESS_CODE`
- opcionalmente `PME_REQUIRE_ACCESS_CODE=true`

Sem `PME_ACCESS_CODE`, o endpoint deve falhar fechado em ambientes de producao.
