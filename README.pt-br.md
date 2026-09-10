<img src="views/logo.svg" alt="" width="64" height="64">

# dendrograph

*[English](README.md) · **Português***

**Um grafo de conhecimento do que você construiu.** Aponte para os seus repositórios git e
receba um mapa navegável de Artifacts, Tools, Techniques e tempo — um que responde *há
quanto tempo eu realmente uso Rust?* com uma data em vez de um palpite.

![Um grafo do dendrograph: Artifacts ligados aos Tools e Techniques que usam](docs/example-graph.svg)

<sup>Uma varredura real de uma organização pública do GitHub — 23 repositórios, sem
credencial, sem configuração. Regenere com `python3 tools/render_svg.py
<archive>/site/graph.json docs/example-graph.svg`.</sup>

Sem servidor. Sem banco de dados. Sem conta. Python 3.11+ e mais nada — o site publicado é
uma pasta que você abre de um pen drive com a rede desligada.

```bash
git clone https://github.com/Wolfloiz/dendrograph.git ~/dendrograph
cd ~/dendrograph
python3 cli.py scan github:tinygrad --root ~/my-archive   # qualquer conta pública
python3 cli.py build --root ~/my-archive
xdg-open ~/my-archive/site/index.html                     # macOS: open · Windows: start
```

**No Windows**, use o PowerShell e troque duas palavras: `py` no lugar de `python3`, e
`Select-String` no lugar de `grep`. O resto desta página é igual, inclusive os caminhos —
o PowerShell entende `~`.

Nenhuma credencial é necessária para uma conta pública. A primeira varredura clona a
história completa num diretório temporário e o joga fora — nada fica em cache entre
execuções.

`pip install -e .` põe os mesmos comandos no seu PATH como `dendro`, que é o nome curto
usado no resto deste arquivo. Todo passo abaixo escreve `python3 .../cli.py` por extenso,
para que nada que você precise colar dependa de ter instalado alguma coisa.

Ou pule a varredura e abra um arquivo de verdade:
[`examples/site/index.html`](examples/site/) é um acervo publicado de 57 repositórios
públicos, versionado neste repositório. Sem instalação, sem conta, e renderiza com a rede
desligada. O `examples/README.md` diz o que o padrão de privacidade deixou de fora dele.

---

## A máquina propõe, o Author dispõe

Esta é a regra de que o resto do desenho decorre, e vale dizê-la antes da lista de
funcionalidades.

O dendrograph é **confiante sobre o que observou e deferente sobre o que interpretou.** Ele
vai te dizer que o primeiro commit de um repositório foi em março de 2019, porque leu isso.
Ele **não** vai te dizer que um projeto sucedeu outro — vai notar a semelhança, imprimir a
linha de configuração que diria isso, e esperar. Se você nunca colar a linha, a relação
nunca existe, e nada no acervo fica bloqueado esperando por você.

A mesma regra, nos lugares onde você vai encontrá-la:

- `dendro suggest` propõe sucessões, Collections e fusões de identidade. **Ele não cria
  nada.**
- `dendro prune` lista o que parece entulho e imprime as linhas que o esconderiam. **Ele
  não apaga nada.** Excluir um Artifact o omite do grafo e o deixa no store; apague a linha
  e ele volta intacto. Uma ferramenta feita porque a memória é falha não pode oferecer
  amnésia em um comando.
- A identidade é sobrescrevível. Se a ferramenta decidir que dois repositórios são um só
  Artifact e você discordar, diga isso na configuração e você vence.
- Epoch Markers — as linhas datadas atravessando a sua timeline, como *AI assistants
  arrive* — são declarados por você e nunca inferidos.

## Duas coisas que ele se recusa a fazer

Não é "ainda não". É recusa:

1. **Ele não julga o seu trabalho.** Nenhuma nota de qualidade, nenhum conceito, nenhuma
   medida de complexidade, nenhum palpite sobre se foi uma pessoa ou um modelo que
   escreveu algo. Ele registra o que foi construído e quando. Um teste varre todo arquivo
   gerado atrás desse vocabulário e quebra o build se ele aparecer.
2. **Ele não superestima.** Onde um número poderia ser lido de duas formas, ele fica com o
   menor. Um fork em que você nunca commitou não contribui data nenhuma para os seus
   períodos de Tool, mesmo estando no seu acervo — senão forkar um projeto de 2009 te faria
   reivindicar dezessete anos de C++.

## O que o site publicado contém, e o que não contém

O padrão é o modo `public`, e sob ele o site não contém **nenhum Artifact privado**: nem
nome, nem descrição, nem URL, nem locator de origem, nem caminho de evidência de Technique,
nem hash de conteúdo.

Isso não é um filtro que você liga. Artifacts privados ficam de fora até que você opte por
cada um pelo nome, um de cada vez.

| | `public` (padrão) | `redacted` | `full` |
|---|---|---|---|
| Artifacts públicos | sim | sim | sim |
| Artifacts privados | não | não, mas contados | sim |
| Artifacts sob alias | nó + datas, mais o que `reveal` nomear | igual | nome real |
| Escreve em | `site/` | `site/` | `.dendro-local/` |

O `full` escreve em outro diretório de propósito. Não é uma flag que um passo de publicação
precisa lembrar de checar — um build completo não tem caminho nenhum até o `site/`.

### Publicar trabalho privado sem nomeá-lo

Trabalho de cliente que você não pode nomear ainda é trabalho que você fez. Um **alias**
publica o nó e as suas datas sob um rótulo que você escolhe (ou um *Private project 3*
gerado), e não revela nada além disso até você nomear cada campo:

Primeiro varra os repositórios privados — `login` uma vez, depois a varredura normal; um
repositório privado entra no store e fica fora do site publicado até você dizer o
contrário:

```bash
python3 ~/dendrograph/cli.py login --root .
python3 ~/dendrograph/cli.py scan github:SUA-CONTA --root .
```

Depois encontre o `id`. Ele é o nome do arquivo no store, e o nome lá dentro diz qual é
qual — os dois espaços iniciais ancoram no nome do próprio Artifact, e não no de um
contribuinte:

```bash
grep -l '^  "name": "o-projeto"' store/artifacts/*.json
```

Ponha esse id no `dendrograph.toml` e reconstrua:

```toml
[[publish.alias]]
id = "root-a1b2c3..."
label = "Projeto fintech anônimo"
reveal = ["period", "tools"]        # a autoria continua escondida
```

A divulgação é opt-in por campo. Não existe redação opt-out, porque o modo de falha do
opt-out é o campo que você esqueceu. Algumas coisas nunca atravessam, em ajuste nenhum: o
nome real, a descrição, a URL, os locators de origem, os caminhos de evidência de
Technique, os hashes de conteúdo e as arestas de linhagem.

**Isto não te torna inidentificável.** Quem conhece o seu trabalho ainda pode reconhecer um
projeto pelas datas e pelos Tools. Um alias é para o leitor que já não sabe — não é
anonimato contra um palpite determinado. Veja `docs/adr/0011`.

**Uma divulgação dita com todas as letras, para não ficar por conta de palpite.** O nó
mantém o seu id, e o id é o SHA do commit raiz do repositório (ADR-0003). Quem tiver um
clone reproduz o valor com `git rev-list --max-parents=0 HEAD` e confirma a
correspondência; um fork privado de um repositório público já tem o SHA raiz público. O
alias esconde o projeto de um leitor que não tem o repositório. Ele não o esconde de quem
tem — um cliente, um ex-colaborador, um contratante. Se é desse leitor que você está se
escondendo, não publique o Artifact. Esse é o padrão, e mantê-lo não custa nada.

## Três passos até o seu próprio acervo

A ferramenta não guarda dado nenhum seu. Os seus Artifacts, a sua configuração e as suas
decisões vivem num repositório de acervo que é seu, e que pode ser privado enquanto o site
que ele publica é público (ADR-0010).

Você não precisa ler nenhum arquivo de código para fazer isto. Cada passo diz o que você
vai ver quando ele funcionou, para que uma falha apareça onde aconteceu em vez de no fim.

**1. Pegue o template.**

```bash
git clone https://github.com/Wolfloiz/dendrograph.git ~/dendrograph  # pule se já tiver
cp -r ~/dendrograph/templates/archive ~/my-archive
cd ~/my-archive && git init
```

Uma cópia, não um fork: o acervo é seu desde o primeiro commit e nada dentro dele aponta
para cá. Funciona sem tocar em nada — uma configuração ausente é válida. Para mantê-lo no
GitHub, privado, `gh repo create my-archive --private --source .` assim que tiver o que
commitar.

*Você deve ver* um repositório com `store/`, `site/` e um `dendrograph.toml` cujos exemplos
estão todos comentados — e cada um deles é válido no instante em que você o descomentar.

**2. Aponte para o seu trabalho.**

```bash
python3 ~/dendrograph/cli.py scan github:SUA-CONTA --root .
python3 ~/dendrograph/cli.py build --root .
```

`SUA-CONTA` é o seu usuário ou organização do GitHub — `octocat`, não um endereço de e-mail
e não uma URL. Uma conta errada não passa em silêncio: a varredura a reporta como
inalcançável com o status HTTP, e a registra como inalcançável em vez de apagada.

Nenhuma credencial é necessária para repositórios públicos. `python3
~/dendrograph/cli.py login` — um device flow OAuth do GitHub, sem token para emitir ou
guardar — acrescenta os seus repositórios privados ao store, e eles ficam fora do site
publicado a menos que você opte por cada um.

Defina `[archive].emails` com os endereços sob os quais você commita antes de construir.
Sem eles não existe um "seu" a medir, e todo período de Tool diz isso em vez de passar as
datas de um fork por experiência sua.

*Você deve ver* uma linha dizendo quantos Artifacts foram adicionados, uma linha de
progresso por repositório enquanto ele varre, e um diretório `site/` depois.

**3. Abra, depois publique.**

```bash
xdg-open site/index.html          # macOS: open · Windows: start
```

Ou clique duas vezes. É um arquivo HTML comum: abre do disco, em qualquer sistema
operacional, sem servidor e sem rede.

**Antes de publicar, isto é o que o site contém e o que ele não contém.** É a única
afirmação neste README que custa caro errar:

- **Artifacts privados não estão nele.** Nem o nome, nem a descrição, nem a URL, nem o
  locator de origem, nem o caminho de evidência de Technique. Eles estão no seu `store/`,
  que é o repositório que você pode manter privado.
- **Nenhum endereço de e-mail de contribuinte está nele.** Um nó Author é rotulado pelo
  nome com que a pessoa assina os commits, ou pela parte local do endereço quando o coletor
  não tem nome — nunca pelo endereço em si (ADR-0012).
- **Nenhum caminho da sua máquina está nele.** Locators de origem locais não atravessam
  para um build publicado.
- **O que está nele**: cada repositório que você varreu e que foi observado como público,
  as suas datas, os Tools e Techniques inferidos dos seus arquivos com um ponteiro para o
  arquivo de onde cada um veio, e as pessoas que commitaram nele.

Se parte do seu trabalho privado deve ser visível como *forma* sem ser nomeada, ponha um
alias — veja [Publicar trabalho privado sem
nomeá-lo](#publicar-trabalho-privado-sem-nomeá-lo).

```bash
python3 ~/dendrograph/cli.py publish --root .
```

Depois sirva o `site/` com o GitHub Pages, ou empurre-o para
`[publish].target_repository`, ou deixe-o no disco. É uma pasta de arquivos estáticos sem
servidor nenhum atrás.

*Você deve ver* `Site ready in site/.` e, assim que o Pages o pegar, o seu acervo numa URL
que você pode pôr num currículo.

## O que acaba no acervo

`store/artifacts/<id>.json`, um arquivo por Artifact, versionado e legível num diff. Essa é
a fonte da verdade; `graph.json`, `graph.sqlite`, `llms.txt` e as duas views são todos
derivados dela e regenerados a cada build.

**Varreduras acumulam.** Elas nunca reconstroem. Um disco que morre, uma conta que fecha,
um repositório que é apagado — o Artifact fica, e a fonte é marcada como inalcançável com a
data em que foi vista pela última vez. É esse o ponto: o acervo sobrevive às coisas de que
foi feito.

A identidade de um Artifact é o SHA do seu commit raiz, então ela sobrevive a ser clonado,
renomeado, re-hospedado e movido entre discos. Um fork compartilha esse SHA e **é** o mesmo
Artifact — é daí que vem a detecção de fork de graça, e por isso *quanto dele é seu* é uma
pergunta separada com uma resposta separada.

## Para programas e agentes

Todo build escreve um `llms.txt` — o acervo em prosa, incluindo o que ele deliberadamente
não contém — junto do `graph.json`, que é autodescritivo: a chave `schema` dele lista cada
tipo de nó e de aresta, então ninguém precisa deste README para lê-lo. O `graph.sqlite`
guarda os mesmos dados em tabelas.

## Rodando

```bash
python3 -m unittest discover -s tests
```

Nenhuma dependência para instalar, e nenhuma em tempo de execução também.

## Contribuindo

Veja [CONTRIBUTING.md](CONTRIBUTING.md). A versão curta: `.specify/memory/constitution.md`
é vinculante e `docs/adr/` registra por que cada decisão foi tomada — trabalho que
contradiga qualquer um dos dois ainda pode estar certo, mas tem que dizer isso em voz alta.

## Licença

MIT. Veja [LICENSE](LICENSE) e `docs/adr/0006`, que explica por que não é AGPL e pede que a
questão não seja reaberta sem informação nova.
