# dendrograph

> Grafo de conhecimento do que você construiu. Aponte para o seu acervo —
> comece pelo GitHub — e receba um mapa navegável de projetos, ferramentas,
> técnicas e linha do tempo. Gerado automaticamente, publicado como site
> estático, sem servidor.

*Não confundir com **dendrograma** (diagrama de agrupamento hierárquico).
O nome vem de dendro — árvore: ramifica, cresce e guarda o tempo em camadas.*

---

## O problema

Todo profissional com mais de cinco anos de carreira tem o mesmo buraco:
**não sabe o que tem.** O trabalho está espalhado entre contas, discos
antigos, repositórios privados e pastas de empresa. Cada ferramenta mostra
um projeto por vez, nunca o conjunto.

E quando chega a hora de escrever um currículo, preencher "anos de
experiência" ou decidir o que fazer em seguida, a resposta sai da memória —
que é a fonte menos confiável disponível.

O registro existe. Ele só não é legível.

## Para quem

- **Quem monta currículo ou perfil** e precisa de números que sustentem uma
  entrevista, não de estimativa.
- **Quem faz arqueologia do próprio acervo** e quer saber o que existe antes
  de decidir o que fazer com isso.
- **Agentes de IA**, que ganham contexto sobre uma pessoa específica — algo
  que nenhum modelo tem por treinamento.

---

## Arquitetura: coletores sobre um grafo genérico

Essa é a decisão que permite o produto crescer sem ser reescrito.

```
  coletores            grafo genérico              visualizações
┌────────────┐      ┌──────────────────┐        ┌────────────────┐
│ git   v0.1 │─────▶│ artefato         │───────▶│ linha do tempo │
│ figma      │      │ coleção          │        │ grafo          │
│ drive      │      │ ferramenta       │        │ perfil         │
│ …          │      │ técnica          │        │ JSON + llms.txt│
└────────────┘      │ período · autor  │        └────────────────┘
                    └──────────────────┘
```

O grafo **não fala de repositório, linguagem e commit**. Fala de artefato,
ferramenta e período. Isso não é abstração gratuita: é o que permite um
coletor de Figma ou de Drive entrar depois sem redesenhar nada.

### Esquema

| Nó | O que é |
|---|---|
| `artefato` | uma unidade de trabalho |
| `colecao` | agrupamento — família, cliente, disciplina |
| `ferramenta` | o que foi usado para construir |
| `tecnica` | como foi construído — padrão, método, abordagem |
| `periodo` | ano ou mês |
| `autor` | identidade que assina |
| `dependencia` | o que foi reaproveitado de terceiros |

| Aresta | Sentido |
|---|---|
| `PERTENCE_A` | artefato → autor |
| `USA_FERRAMENTA` | artefato → ferramenta |
| `APLICA_TECNICA` | artefato → técnica *(com confiança e evidência)* |
| `DA_COLECAO` | artefato → coleção |
| `NO_PERIODO` | artefato → período |
| `DERIVA_DE` | artefato → artefato *(material compartilhado)* |
| `SUCEDE` | artefato → artefato *(um começou quando o outro parou)* |

### Como cada coletor preenche o mesmo esquema

| | coletor **git** (v0.1) | coletor **figma** (futuro) |
|---|---|---|
| `artefato` | repositório | arquivo |
| `colecao` | família de projetos | projeto ou cliente |
| `ferramenta` | linguagem, framework | plugin, biblioteca de componentes |
| `tecnica` | padrão de projeto, marcador de complexidade | grid, design token, auto-layout |
| `periodo` | data do commit | data da versão |
| `autor` | identidade do git | conta |
| `DERIVA_DE` | arquivos de fonte idênticos | componente reaproveitado |

**Aviso honesto sobre a expansão.** O git é um substrato universal: cada
commit tem autor, data e diff. Design e arquitetura não têm equivalente —
versão de Figma não tem autoria granular, `.psd` no Drive não tem histórico.
Os coletores futuros vão preencher menos campos e com menos precisão. A
arquitetura comporta; a qualidade do dado vai variar por domínio, e a UI tem
que mostrar isso em vez de esconder.

---

## O que faz

```
descobre  →  escaneia  →  analisa  →  monta o grafo  →  publica
```

1. **Descobre** os artefatos — via API do GitHub (público e privado) ou
   varredura de pastas locais.
2. **Escaneia** cada um: estrutura, manifestos, dependências, convenções,
   hashes de conteúdo.
3. **Analisa**: separa autoral de fork, deduplica cópias, conta linhas e
   commits por autor, reconhece padrões de projeto e marcadores de
   complexidade.
4. **Monta o grafo** com as arestas de linhagem e sucessão.
5. **Publica**: site estático com linha do tempo e grafo, mais `grafo.json`,
   `grafo.sqlite` e `llms.txt` para consumo por máquina.

## O que NÃO faz — decisão, não falta

- **Não hospeda nada.** Roda no Actions de quem usa e publica no Pages de quem
  usa. Nenhum dado de terceiro passa por servidor nosso.
- **Não julga qualidade.** Não é code review, não dá nota.
- **Não prova complexidade.** Reconhece marcadores de custo conhecido com
  confiança declarada. Provar O(log n) é indecidível; fingir que não é seria
  mentir para quem usa.
- **Não exige chave de LLM.** A camada de IA, se existir, é opcional e
  desligada por padrão.

---

## Por que sem servidor e sem banco de grafo

**Sem backend.** É a decisão que define o produto. Com servidor você precisa
hospedar, autenticar, pagar e virar processador de dados alheios — inclusive
de repositórios privados. Sem servidor, a ferramenta se distribui e os dados
nunca saem da conta de quem rodou.

**Sem banco de grafo.** Um acervo de 500 repositórios dá cerca de 3 mil nós —
menos de 1 MB, que o navegador carrega e desenha sem esforço. Neo4j resolve
travessia em milhões de nós; aqui o grafo cabe na memória da aba. O precedente
é o Obsidian, cujo graph view não tem banco nenhum. Se um dia agregar vários
acervos num corpus único, `grafo.json` importa para Neo4j numa tarde — a porta
fica aberta, mas não se entra por ela agora.

**Sem dependência externa na página.** Nem CDN, nem biblioteca de grafo. A
simulação de forças são 90 linhas e o desenho é canvas 2D. Não é purismo: é o
que faz a página funcionar offline, num pendrive e no Pages sem configuração.

**Só stdlib no Python.** Quem forka não instala nada.

---

## Diferencial

As ferramentas existentes de código-como-grafo resolvem **um repositório**,
para alguém entender código alheio rápido. Nenhuma resolve **o acervo de uma
pessoa ao longo dos anos**.

| | Ferramentas de codebase | dendrograph |
|---|---|---|
| Escopo | 1 repositório | acervo inteiro, várias contas e discos |
| Objetivo | entender código alheio | conhecer o próprio histórico |
| Eixo | estrutura do código | tempo, ferramenta, linhagem, técnica |
| Infra | servidor e banco de grafo | site estático |
| Privados | precisa confiar no serviço | nunca saem da sua conta |

---

## Fases

**v0.1 — coletor git** *(o que já existe e funciona)*
Pipeline em Python stdlib: descoberta pela API, clonagem, varredura, análise,
contagem por autor, detecção de padrões, montagem do grafo, duas visões HTML.
Workflow do Actions. Saída em JSON, SQLite e `llms.txt`.

**v0.2 — usável por estranho**
Uma tela com seletor de visão. `README` com o fork em três passos. Busca sobre
o FTS5 que já está no SQLite. Perfil de ferramenta: clicar em "Rust" e ver
desde quando, quanto e em quê.

**v0.3 — robustez**
Barnes-Hut acima de 3 mil nós. GitLab e Bitbucket. Detecção de padrão por AST
em vez de regex, começando por TypeScript e Python.

**v0.4 — além do código**
Primeiro coletor não-git. Servidor MCP sobre o SQLite. Camada de LLM opcional
para o que a heurística não alcança, marcando na origem o que veio de modelo.

---

## Estrutura

```
dendrograph/
├─ .github/workflows/atualizar.yml
├─ coletores/
│  └─ git/                    descoberta, clone, varredura, contagem
├─ nucleo/                    análise, grafo, esquema genérico
├─ visoes/                    linha do tempo, grafo, perfil
├─ docs/                      site publicado (Pages)
├─ exemplos/                  acervo de demonstração
├─ CONTRIBUTING.md
└─ README.md
```

---

## Três decisões antes do primeiro commit público

**Idioma.** Todo o código e os comentários estão em português. Para alcance
open source, `README` e mensagens de CLI precisam ser em inglês. Sugestão:
interface e documentação em inglês, comentários em português como assinatura.
Não faça meio a meio.

**Licença.** MIT se o objetivo é adoção. AGPL se quer impedir que alguém monte
um SaaS fechado por cima.

**A imagem na primeira dobra.** Ninguém dá estrela em ferramenta de
visualização sem ver a visualização. Use o seu próprio acervo como exemplo —
é honesto e prova que funciona em dado real.
