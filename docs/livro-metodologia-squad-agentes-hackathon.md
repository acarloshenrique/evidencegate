# O livro: metodologia completa pra squad multi-agente em hackathon

## Prefácio

Esse documento assume que você não sabe nada. Se você já manja de Git, de agente de IA, de Kanban — pula direto pra Parte 1. Se não manja, lê a Parte 0 primeiro, porque todo o resto depende desses conceitos.

A ideia inteira nasceu de uma coisa que você viveu de verdade: você foi num hackathon, cada pessoa do time rodou seu próprio agente de IA de código ao mesmo tempo, e virou bagunça — conflito de Git, gente pisando no trabalho de gente, ninguém sabendo o que o outro tava fazendo. Esse livro é a solução completa pra isso, do conceito mais básico até o comando de terminal exato que você digita.

---

# Parte 0 — Conceitos básicos, explicados do zero

## 0.1 O que é um hackathon

Hackathon é um evento — geralmente de 24 a 48 horas — onde times pequenos (2 a 5 pessoas, normalmente) tentam construir um produto ou protótipo funcional do zero, dentro do prazo, e no final apresentam pra uma banca de jurados que dá nota e escolhe vencedores. O tempo é o inimigo número um: você não tem semanas pra planejar, tem horas.

## 0.2 O que é um agente de IA de código

É um programa que usa um modelo de linguagem (o motor por trás de ferramentas como o Claude, o ChatGPT etc.) pra escrever, editar, rodar e corrigir código sozinho, seguindo instruções que você dá em texto normal — tipo "cria uma tela de login" — sem você precisar digitar cada linha de código na mão. Exemplos: Claude Code, Cursor, Codex. O agente lê o código existente, decide o que mudar, faz a mudança, roda os testes, e volta pra você com o resultado.

O problema que você viveu acontece quando VÁRIOS agentes desses — um por pessoa do time — mexem no MESMO projeto ao mesmo tempo, sem coordenação. É tipo cinco pedreiros reformando a mesma casa sem planta e sem conversar entre si.

## 0.3 O que é Git, repositório, commit, branch, merge e conflito

**Git** é o programa que guarda o histórico de tudo que já foi mudado no código de um projeto — cada linha, cada arquivo, cada versão. Sem Git, se duas pessoas mexerem no mesmo arquivo, uma simplesmente sobrescreve o trabalho da outra e perde tudo. Com Git, dá pra juntar o trabalho dos dois de forma organizada.

**Repositório** (ou "repo") é a pasta do projeto, com uma pasta escondida dentro dela (chamada `.git`) que guarda toda essa história.

**Commit** é uma "foto" do estado do código num momento específico, com uma mensagem explicando o que mudou. Cada vez que você termina um pedaço de trabalho, você dá um commit — é tipo salvar um checkpoint num jogo.

**Branch** (galho, ou linha do tempo paralela) é uma cópia da história do projeto que você pode mexer sem afetar a versão "oficial" (geralmente chamada `main`). Cada pessoa (ou agente) trabalha na própria branch, faz seus commits ali, e só depois isso volta pra `main`.

**Merge** é o ato de juntar duas branches de volta numa só — pegar o que foi feito numa linha do tempo paralela e trazer pra linha principal.

**Conflito de merge** acontece quando duas branches mudaram a MESMA linha do MESMO arquivo de jeitos diferentes, e o Git não sabe qual das duas versões é a certa — alguém (uma pessoa, não o Git sozinho) precisa olhar e decidir manualmente. É exatamente isso que causa a maior parte do caos que você descreveu no hackathon: dois agentes mexendo no mesmo arquivo, ao mesmo tempo, sem saber um do outro.

## 0.4 O que é um worktree (a peça que faltava nos documentos anteriores)

Normalmente, uma pasta de projeto no seu computador só consegue "olhar" pra uma branch de cada vez — se você quer trabalhar em outra branch, precisa trocar (`git checkout`), e aí a pasta muda de conteúdo na sua frente.

**Worktree** é um recurso do Git que permite ter VÁRIAS pastas do mesmo projeto no seu computador ao mesmo tempo, cada uma "olhando" pra uma branch diferente — mas todas compartilhando a mesma história por trás (`.git`), sem precisar copiar o projeto inteiro pra cada uma.

Analogia: imagina um livro com várias marcas de página. Ao invés de só poder estar em UMA página por vez, o worktree te dá várias cópias físicas do livro aberto, cada uma numa página diferente — mas todas as anotações que você faz em qualquer cópia acabam voltando pro mesmo livro no final.

Isso resolve o problema de raiz: cada agente do seu time trabalha na própria pasta física, sem ver (e sem estragar) o que os outros agentes estão fazendo em tempo real. O conflito só aparece na hora de juntar tudo de volta — que é uma hora controlada, não o tempo todo.

## 0.5 O que é um board (Kanban)

Um quadro visual dividido em colunas — normalmente "a fazer", "fazendo", "pronto" — onde cada tarefa é representada por um cartão que vai andando de coluna conforme avança. Serve pra qualquer pessoa do time (ou agente) saber, de relance, o que está sendo feito, por quem, e o que falta.

## 0.6 O que é crítica adversarial / red team

"Red team" vem de exercício militar: um grupo se veste de "inimigo" de propósito, pra atacar o plano da própria equipe e achar os furos antes que o inimigo de verdade os ache. No mundo de produto e negócio, virou prática comum: antes de construir algo, alguém (ou um agente dedicado) tem o único trabalho de questionar a ideia — "isso resolve um problema real?", "que dado sustenta isso?", "onde isso quebra?" — ao invés de todo mundo só concordando animado.

## 0.7 O que é debate multi-agente

É a técnica de colocar dois ou mais agentes de IA discutindo o MESMO problema entre si — um propõe, outro questiona, um terceiro arbitra — ao invés de perguntar pra um agente só e aceitar a primeira resposta como verdade. Pesquisas nessa área mostram algo consistente: agentes que debatem entre si erram menos e inventam menos informação falsa do que um agente sozinho respondendo de primeira. É basicamente formalizar o que acontece quando você pede pra duas pessoas espertas discordarem sobre uma ideia antes de decidir — só que com agentes, e de forma estruturada.

---

# Parte 1 — O problema que você viveu, passo a passo

Reconstruindo o que aconteceu, com os termos da Parte 0:

1. Cada pessoa do time abriu seu próprio agente de IA de código, na mesma pasta do projeto.
2. Sem worktree, todos estavam "olhando" pro mesmo repositório ao mesmo tempo — ou, na melhor das hipóteses, em branches diferentes mas na mesma pasta física.
3. Cada agente, sem saber o que os outros estavam fazendo, foi mexendo em arquivos que às vezes se sobrepunham com o que outro agente também estava mexendo.
4. Na hora de dar merge (juntar tudo de volta pra branch principal), apareceram vários conflitos de merge ao mesmo tempo, porque ninguém tinha combinado antes quem mexia em quê.
5. Sem um board dizendo quem estava em qual tarefa, teve tarefa duplicada e gente descobrindo o trabalho do outro só na hora do conflito.
6. O resultado: tempo do hackathon (que já é curto) queimado resolvendo bagunça de coordenação, ao invés de construir o produto.

Isso não é falha de disciplina do time — é reconhecido hoje como o principal gargalo de produtividade quando várias pessoas rodam agentes de IA no mesmo projeto sem isolamento técnico. A causa raiz tem nome: falta de worktree (Parte 3) e falta de board com dono por tarefa (Parte 4). O resto desse livro resolve isso ponto a ponto.

---

# Parte 2 — Estrutura da equipe

## 2.1 Os papéis, um por um

**Orquestrador.** É quem tem a visão do todo. Dono do board, decide a ordem das tarefas, resolve travamento, corta escopo quando o tempo aperta. NÃO decide detalhe técnico de como cada tarefa é implementada — isso é problema de quem está na tarefa. Numa equipe pequena de hackathon, pode ser a mesma pessoa que faz o pitch no final, porque é quem tem visão de conjunto.

*Exemplo de dia a dia*: o orquestrador olha o board a cada 1-2h, vê que a tarefa de autenticação está travada há 40 minutos, pergunta pro dono da tarefa o que está acontecendo, e decide se vale a pena simplificar o escopo daquela tarefa pra não travar o resto do time.

**Dono de branch/worktree.** Uma pessoa (junto com o agente de IA dela) responsável por UMA tarefa por vez, numa worktree isolada. Decide como implementar a própria tarefa. NÃO mexe no escopo de tarefas de outras pessoas sem avisar.

*Exemplo*: Felipe é dono da tarefa "validação de CPF no cadastro". Ele trabalha só na sua worktree (`../projeto-felipe`), no seu agente, na sua branch. Se ele perceber que precisa mudar algo que outra pessoa está mexendo, ele avisa antes de mexer.

**Integrador (rotativo).** Só essa pessoa faz o merge das branches de volta pra `main`. Isso evita que várias pessoas tentem mesclar ao mesmo tempo e piorem o conflito. Decide a ordem de merge e resolve os conflitos que aparecerem. NÃO tem o poder de rejeitar uma tarefa só porque não gostou — só entra em ação técnica, não em critério de gosto.

*Por que rotativo*: pra ninguém virar gargalo sozinho — a cada ciclo de merge (a cada 1-2h, ver Parte 9), passa o bastão pra outra pessoa do time.

**Crítico adversarial.** Papel dedicado (pode ser uma pessoa OU um agente configurado especificamente pra isso) cujo único trabalho é atacar a proposta antes dela virar código — ver Parte 6 pro manual completo dessa etapa. Decide se a proposta passa pra construção ou volta pra pesquisa. NÃO decide como o time vai construir depois de aprovada — isso já é outro papel.

**Liaison com o time humano.** Registra decisão, leva mudança de rumo pro board, garante que ninguém do time humano ficou "no escuro" sobre uma decisão que um agente tomou sozinho. Não tem poder de decisão de escopo — só de registro e comunicação.

## 2.2 Como dividir numa equipe pequena (2 a 5 pessoas)

Com 2 pessoas: uma cuida de orquestração + crítica adversarial + liaison (os papéis "de fora do código"), a outra + os agentes cuidam de construção.

Com 3-5 pessoas: uma pessoa de "produto" cuidando de visão e falando com organizadores/patrocinadores (larga o teclado por boa parte do tempo), e o resto dividido estritamente por camada técnica — front, back, dados — nunca duas pessoas na mesma camada ao mesmo tempo sem combinar antes. Essa divisão por camada, junto com uma pessoa fora do código garantindo que o time está construindo o que vai ser demonstrado (e não a feature favorita de cada um), é o padrão que mais aparece em relatos de hackathons vencedores.

## 2.3 Tabela-resumo (RACI simplificado)

| Papel | Responsabilidade | Decide sobre | Não decide sobre |
|---|---|---|---|
| Orquestrador | Dono do board, prioridade, remove bloqueio | Ordem das tarefas, corte de escopo | Detalhe técnico de implementação |
| Dono de branch/worktree | 1 pessoa + 1 agente, entrega 1 tarefa | Como implementar a própria tarefa | Escopo de outras tarefas |
| Integrador (rotativo) | Só ele faz merge pra main | Ordem de merge, resolve conflito | Rejeitar tarefa por gosto pessoal |
| Crítico adversarial | Ataca a proposta antes dela virar código | Se a proposta passa ou volta pra pesquisa | Como o time implementa depois de aprovada |
| Liaison com o time | Conversa com humanos, registra decisão | Nada de escopo — só registra e leva adiante | — |

---

# Parte 3 — Git e worktree, passo a passo, comando por comando

Essa é a parte técnica que faltava nos documentos anteriores. Vou explicar cada comando, o que cada palavra dele significa, não só colar o comando.

## 3.1 Criando uma worktree

```bash
git worktree add ../projeto-agente-a feature/agente-a-auth
```

Traduzindo linha por linha:
- `git worktree add` — o comando que cria uma worktree nova.
- `../projeto-agente-a` — o caminho da pasta nova que vai ser criada, um nível acima da pasta atual (`../` significa "sobe uma pasta"). É aqui que o agente A vai trabalhar.
- `feature/agente-a-auth` — o nome da branch que essa worktree vai usar. Se a branch ainda não existe, o Git cria ela nesse mesmo comando.

Depois de rodar isso, você vai ter uma pasta nova (`projeto-agente-a`) com uma cópia completa e funcional do projeto, só que "olhando" pra branch `feature/agente-a-auth`. Você repete esse comando uma vez pra cada agente/pessoa:

```bash
git worktree add ../projeto-agente-b feature/agente-b-checkout
git worktree add ../projeto-agente-c feature/agente-c-design
```

Cada agente entra na sua própria pasta e trabalha lá, sem enxergar as outras.

## 3.2 Ver quais worktrees existem

```bash
git worktree list
```

Mostra todas as worktrees ativas no projeto, com o caminho de cada uma e a branch que cada uma está usando. Útil pra não perder o controle de quantas você já criou.

## 3.3 As três coisas que ainda quebram, mesmo com worktree isolada

Worktree isola o CÓDIGO, mas não isola automaticamente tudo que roda em cima do código:

**Porta do servidor.** Se dois agentes, em duas worktrees diferentes, tentarem rodar o servidor de desenvolvimento na mesma porta (ex: 3000), o segundo vai falhar porque a porta já está em uso. Solução: cada worktree com sua própria porta, configurada no arquivo `.env` de cada pasta (ex: agente A usa 3000, agente B usa 3001).

**Banco de dados.** Se dois agentes rodam uma migration (mudança na estrutura do banco de dados) ao mesmo tempo no mesmo banco, o schema pode corromper. Solução: banco de teste separado por worktree, ou pelo menos um prefixo diferente no nome de cada banco (`agente_a_test`, `agente_b_test`).

**Docker.** Se você usa containers Docker pro ambiente de desenvolvimento, dois containers com o mesmo nome colidem. Solução: prefixar o nome do container com o nome da branch (`docker run --name agente-a-app ...`).

## 3.4 Juntando tudo de volta (merge)

O conflito não desaparece com a worktree — ele só é adiado pra hora certa, que é a hora do merge, ao invés de acontecer em tempo real enquanto todo mundo trabalha. Quem faz esse merge é o Integrador (papel da Parte 2), e ele faz assim:

```bash
git checkout main
git merge --no-ff feature/agente-a-auth
```

- `git checkout main` — muda pra branch principal.
- `git merge --no-ff feature/agente-a-auth` — junta a branch do agente A na main. O `--no-ff` (no fast-forward) garante que fica registrado no histórico que essa branch existiu separadamente, o que ajuda a entender depois quem fez o quê.

Se aparecer um conflito nesse momento, o Git avisa quais arquivos têm linhas conflitantes, e o Integrador (ou quem estiver revisando) abre o arquivo, escolhe qual versão fica (ou combina as duas manualmente), e finaliza com:

```bash
git add <arquivo-resolvido>
git commit
```

Depois de resolver a primeira branch, roda os testes automatizados pra garantir que nada quebrou, e só então mescla a próxima:

```bash
git merge --no-ff feature/agente-b-checkout
```

**Regra de ordem**: mescle primeiro quem depende de menos coisa. Se a tarefa do agente B depende do que o agente A fez, o A entra primeiro — senão o merge do B vai conflitar contra uma `main` que ainda não tem a base que ele precisa.

## 3.5 Atualizando sua worktree antes de pedir merge

Antes de avisar que sua tarefa está pronta pra entrar na `main`, é boa prática trazer as mudanças mais recentes da `main` pra dentro da sua branch primeiro — assim quem for revisar já vê seu código compatível com o que está atualizado:

```bash
git fetch origin
git rebase origin/main
```

- `git fetch origin` — busca as atualizações mais recentes do repositório remoto (`origin`), sem misturar ainda com seu código.
- `git rebase origin/main` — reorganiza seus commits em cima da versão mais atual da `main`. Se der conflito aqui, é melhor resolver agora, sozinho na sua worktree, do que deixar pro Integrador descobrir na hora do merge geral.

## 3.6 Limpando depois

Worktree não se apaga sozinha. Depois que uma tarefa é mesclada e não precisa mais daquela pasta separada, alguém tem que remover manualmente:

```bash
git worktree remove ../projeto-agente-a
```

Isso é importante porque relatos de quem usa esse fluxo mostram que worktrees esquecidas acumulam gigabytes de espaço em disco rapidinho, especialmente em projetos que geram muito arquivo de build (cache de compilação, `node_modules`, etc.) — bota isso no checklist de fim de ciclo (Parte 11).

## 3.7 Ferramentas que automatizam esse fluxo, se não quiser fazer tudo na mão

- **agentree** — um CLI leve só pra criar e gerenciar worktree por tarefa. Um comando tipo `agentree -b nome-da-tarefa` já cria a worktree, configura o ambiente e deixa pronta pro agente entrar.
- **Claude Squad** — ferramenta que já isola cada sessão de agente numa worktree própria automaticamente, sem você precisar rodar os comandos da Parte 3.1 na mão.
- **OpenClaw** (a partir da versão 0.8) tem um "Worktree Dispatcher" nativo — você entrega uma lista de tarefas, e ele distribui automaticamente pra worktrees livres, respeitando ordem de dependência.

---

# Parte 4 — O board e o cartão de tarefa

## 4.1 Por que granularidade importa

O erro mais comum é criar uma tarefa gigante tipo "fazer o cadastro de usuário" e jogar pra um agente resolver sozinho. Isso é ruim por dois motivos: primeiro, ninguém mais sabe exatamente o que está dentro dessa tarefa, então é fácil duas pessoas mexerem em partes que se sobrepõem sem perceber. Segundo, fica difícil saber quando está "pronto" de verdade.

A solução é quebrar por função ou teste específico — uma unidade pequena o suficiente pra caber numa única branch/worktree, com um critério claro de quando está terminada.

Errado: "Fazer o cadastro de usuário" (uma tarefa gigante, vaga, vira várias pessoas mexendo no mesmo lugar)
Certo: "Validar CPF no formulário", "Salvar usuário no banco", "Enviar e-mail de confirmação" (três tarefas pequenas, cada uma com um dono, uma worktree, um critério de pronto)

## 4.2 O cartão de tarefa, campo por campo

```
ID: T014
Título: Validar CPF no formulário de cadastro
Dono: Felipe + Agente A
Worktree: ../projeto-agente-a
Branch: feature/agente-a-validacao-cpf
Depende de: T009 (schema do formulário)
Pronto quando: função valida CPF real, rejeita CPF inválido, tem teste automatizado passando
```

- **ID**: um código curto só pra referenciar a tarefa em qualquer lugar (commit, conversa, board) sem precisar reescrever o título inteiro.
- **Título**: frase curta, específica, que qualquer pessoa do time entende sem precisar perguntar.
- **Dono**: quem (pessoa + agente) é responsável — nunca deixe uma tarefa sem dono, é isso que gera duplicidade.
- **Worktree/branch**: onde fisicamente esse trabalho está acontecendo (ver Parte 3).
- **Depende de**: se essa tarefa só faz sentido depois de outra estar pronta, isso fica registrado aqui — é o que dá a "ordem de dependência" usada na hora do merge (Parte 3.4).
- **Pronto quando**: o critério objetivo de conclusão. Sem isso, "pronto" vira opinião de cada um, e é aí que sobra trabalho pela metade.

## 4.3 Onde colocar o board

Pode ser qualquer ferramenta visual (Notion, Linear, Trello) ou, mais simples ainda pra um hackathon curto, um arquivo `.md` dentro do próprio repositório, com uma lista de tarefas em três blocos: "a fazer", "fazendo", "pronto". A vantagem do arquivo dentro do repo é que ele fica versionado junto com o código, e o próprio agente consegue ler o board direto (sem precisar de outra ferramenta conectada).

A regra mais importante, independente da ferramenta: **cada agente marca "peguei" no cartão ANTES de começar a mexer**, não depois. É esse hábito, sozinho, que evita a maior parte da duplicidade de trabalho.

---

# Parte 5 — O pipeline de agentes, do zero até o código

Isso é a parte que decide se o produto final resolve um problema de verdade ou é só "bonito por fora". São 8 etapas em sequência. Vou explicar cada uma com um exemplo prático, imaginando um time de hackathon tentando resolver "gente esquece de tomar remédio no horário certo".

## 5.1 Pesquisa (multi-perspectiva)

Ao invés de um agente só pesquisando o problema de um jeito só, você coloca vários agentes pesquisando o MESMO problema de ângulos diferentes ao mesmo tempo — um do ângulo técnico (o que já existe tecnicamente?), um do ângulo do usuário (quem sofre com isso e como?), um do ângulo de negócio (alguém pagaria por isso?), um do ângulo da concorrência (quem já tentou resolver isso e por que não pegou?).

Isso é o mesmo princípio por trás do STORM, um sistema de pesquisa da Universidade de Stanford: pesquisa feita a partir de várias perspectivas simuladas gera resultado mais completo do que um agente perguntando de forma linear e sozinha.

*No exemplo do remédio*: um agente pesquisa apps existentes de lembrete de remédio (concorrência), outro pesquisa por que idosos especificamente esquecem (usuário), outro pesquisa se dá pra integrar com notificação de celular sem app novo (técnico).

## 5.2 Debate

Os agentes que pesquisaram trazem o que acharam e debatem entre si — um defende uma direção, outro questiona, um terceiro tenta achar o meio-termo ou aponta uma contradição que ninguém tinha visto. Essa técnica de "multi-agent debate" tem estudo publicado mostrando que agentes que debatem entre si cometem menos erro e inventam menos informação falsa do que um agente sozinho respondendo de primeira — o mecanismo é parecido com o motivo de duas pessoas discordando produtivamente chegarem numa ideia melhor do que uma pessoa sozinha decidindo na primeira impressão.

*No exemplo*: um agente defende "o problema é lembrar", outro questiona "não, o problema é a pessoa lembrar mas não ter o remédio por perto" — e esse questionamento muda a direção do produto.

## 5.3 Lobby (consolidação)

Depois do debate, alguém (ou um agente dedicado a isso) pega tudo que sobrou — os pontos em que os agentes concordaram, as contradições resolvidas — e fecha numa proposta única e objetiva, com as premissas explícitas por escrito. É o documento de decisão antes de ir pra crítica.

*No exemplo*: a proposta que sai do lobby é algo tipo "vamos resolver o problema de esquecimento combinando lembrete por notificação + confirmação de que o remédio está fisicamente por perto, porque a pesquisa mostrou que lembrete sozinho não resolve".

## 5.4 Crítica adversarial (red team)

Ver o manual completo dessa etapa na Parte 6 — é a etapa mais importante do pipeline inteiro pra evitar entregar algo "bonito mas vazio".

## 5.5 Design + biblioteca de UX em Markdown

Depois que a proposta sobrevive à crítica, um agente de design trabalha em cima dela, consultando uma biblioteca de padrões de interface já documentados (ver Parte 7). A saída dele não é um desenho no Figma — é uma especificação em texto (`.md`) que o agente de desenvolvimento consegue ler direto, sem precisar de alguém "traduzindo" um desenho visual pra código.

## 5.6 Desenvolvimento

Aqui entra tudo da Parte 3 e da Parte 4: 1 branch/worktree por tarefa, dono fixo, PR pequeno e frequente, merge em ordem de dependência. O agente de dev implementa a partir da spec de design + da proposta validada — não do "achismo" da primeira hora.

## 5.7 Acompanhamento de projeto (backlog)

Alguém (pessoa ou agente) mantém o board atualizado, cruza o que foi prometido com o que foi entregue, e avisa cedo quando algo está atrasado — não na hora em que já é tarde pra ajustar.

## 5.8 Liaison com o time humano

Um agente (ou pessoa) cujo trabalho é conversar com o time, registrar toda decisão importante, e trazer de volta pro pipeline quando o time humano decide mudar de rumo — normalmente isso significa reabrir a etapa de pesquisa ou de debate, não simplesmente jogar a mudança direto pro código.

---

# Parte 6 — Crítica adversarial: o manual completo

Essa é a etapa que mais separa "produto que resolve problema real" de "produto bonito e vazio" — que era exatamente a sua reclamação original sobre "fuleiragem". Por isso ela merece a própria parte do livro, não só um parágrafo.

## 6.1 De onde vem esse método

"Red team" é uma prática que vem de exercício militar e de inteligência (times que fingem ser o inimigo pra testar a própria defesa antes do combate de verdade), e hoje é usada rotineiramente em planejamento estratégico de empresa e em validação de produto antes de construir. A lógica é a mesma em qualquer um desses contextos: um time que só concorda com a própria ideia não enxerga os furos dela — é preciso alguém, ou algo, estruturalmente contrário, cujo trabalho seja discordar de propósito.

## 6.2 As quatro etapas do checklist

**1. Checagem de premissas.** Antes de qualquer coisa, liste TODA premissa que precisa ser verdadeira pra ideia funcionar. Depois separe cada premissa num destes três baldes:
- **Desejável**: alguém realmente quer isso? (não "acho que", quer de verdade)
- **Viável**: dá pra sustentar isso como produto ou negócio depois do hackathon?
- **Factível**: dá pra construir isso a tempo, com a equipe e as ferramentas que vocês têm?

*No exemplo do remédio*: premissa "idosos vão instalar um app novo" — desejável? talvez não, idosos resistem a instalar apps novos. Essa premissa sozinha já pode derrubar a direção do produto, e é melhor descobrir isso na hora 5, não na hora 20.

**2. E se / contra-argumento.** Pra cada premissa que sobrou, alguém do time (ou um agente configurado especificamente pra isso) argumenta ativamente o lado oposto — não como retórica vazia, mas puxando um motivo concreto. A pergunta certa não é "você concorda?", é "por que isso pode estar errado?".

**3. Qualidade da informação.** Todo dado que sustenta uma decisão precisa ter origem rastreável. A pergunta é literal: "esse número/fato veio de onde?" Se a resposta for "o agente falou" sem uma fonte por trás, isso é um alerta vermelho — agente de IA pode inventar informação com total confiança (isso é chamado de alucinação), então todo dado crítico pra decisão precisa ser checado contra uma fonte real antes de virar base de decisão.

**4. Furo em produção.** Pergunta final: onde isso quebra? Com usuário real, em escala, ou na frente do jurado que vai perguntar "e se X acontecer?". Esse exercício de imaginar o pior caso é o que evita ser pego de surpresa no pitch.

## 6.3 Quem faz esse papel

Pode ser uma pessoa do time dedicada só a isso (que larga o teclado por essa etapa), ou um agente de IA configurado especificamente com a instrução de atacar, não de ajudar a construir. O importante é que essa pessoa/agente NÃO seja quem teve a ideia original — quem criou a proposta tem viés natural de defendê-la, então o papel de atacar precisa vir de fora.

## 6.4 Critério de saída

Só avança pra etapa de design (5.5) quem sobreviveu as quatro perguntas acima com resposta concreta — não "acho que sim", uma resposta com dado ou lógica por trás. Se uma premissa central não sobrevive, a proposta volta pra pesquisa (5.1) ou debate (5.2), não segue adiante só porque "já gastamos tempo nisso".

---

# Parte 7 — Biblioteca de design em Markdown, tutorial completo

## 7.1 Por que documentar design em texto, não em desenho

Numa equipe com agente de IA fazendo o desenvolvimento, um desenho no Figma não ajuda muito — o agente de código lê texto, não interpreta imagem visual de forma confiável. A solução é ter os padrões de interface documentados em arquivos `.md`, que tanto humano quanto agente conseguem ler direto.

## 7.2 Estrutura de pastas sugerida

```
/design/
  principios.md          → tom, voz, princípios gerais do produto
  componentes/
    formulario.md         → quando usar, estados, erro, acessibilidade
    tabela.md
    botao.md
  fluxos/
    cadastro.md            → passo a passo do fluxo, decisões de UX
    checkout.md
```

Essa pasta fica dentro do próprio repositório do código, versionada junto — quando alguém muda um padrão de design, isso vira um commit normal, com histórico, igual qualquer mudança de código.

## 7.3 Exemplo de arquivo preenchido

```markdown
# Componente: Formulário

## Quando usar
Sempre que o usuário precisa fornecer informação estruturada (cadastro, configurações, busca avançada).

## Estados
- Vazio: campo com placeholder claro do que é esperado, nunca vazio sem indicação
- Preenchendo: validação em tempo real só depois que o usuário sai do campo, nunca a cada tecla
- Erro: mensagem específica embaixo do campo (não um alerta genérico no topo da tela), em texto vermelho, explicando o que precisa mudar
- Sucesso: confirmação visual clara antes de navegar pra próxima tela

## Acessibilidade
- Todo campo tem um `label` associado, nunca só placeholder
- Contraste mínimo de texto sobre fundo: 4.5:1
- Navegável 100% por teclado, sem depender de mouse
```

## 7.4 Como o pipeline usa isso

O agente de design (etapa 5.5) consulta essa pasta ANTES de propor qualquer coisa nova — só cria um padrão novo se nenhum dos existentes resolve o caso. O agente de desenvolvimento (etapa 5.6) lê a spec que sai dali direto, sem precisar de ninguém "traduzindo" visual pra código.

---

# Parte 8 — Critérios de julgamento de hackathon, explicados

## 8.1 Como bancas de hackathon avaliam, na prática

Hackathons bem organizados publicam o critério de julgamento ANTES da inscrição abrir — isso é considerado boa prática porque o time constrói pro que vai ser avaliado, ao invés de descobrir o critério só na hora da apresentação. Normalmente a nota é dividida em 4 a 5 categorias, cada uma com um peso:

- **Inovação**: o quão original é a solução, ou o ângulo que ela encontrou
- **Viabilidade técnica / execução**: o produto realmente funciona, ou é só uma tela bonita sem nada por trás?
- **Usabilidade**: alguém consegue usar isso sem manual de instrução?
- **Impacto real**: isso resolve um problema que existe de verdade, pra gente de verdade?
- **Qualidade do pitch**: o time consegue explicar, em poucos minutos, por que isso importa?

## 8.2 Por que isso importa pro seu pipeline

A ideia é simples: se cada etapa do pipeline (Parte 5) já gera evidência pra uma dessas categorias, o pitch final não precisa ser inventado às pressas na última hora — ele já nasce pronto, porque cada critério tem prova concreta por trás.

| Categoria de julgamento | Etapa do pipeline que gera a evidência |
|---|---|
| Inovação | Pesquisa multi-perspectiva (5.1) + debate (5.2) — o ângulo que ninguém mais achou |
| Viabilidade técnica | Desenvolvimento (5.6) nos worktrees + testes passando |
| Usabilidade | Design + biblioteca de UX (5.5 / Parte 7) |
| Impacto real | Crítica adversarial (5.4 / Parte 6) — sobreviveu ao checklist de desejável/viável/factível |
| Pitch | Liaison (5.8) + orquestrador — narrativa costurada com as evidências acima |

---

# Parte 9 — Cronograma sugerido pra um hackathon de 24 horas, hora a hora

Sua régua de "80% pesquisa, 20% construção" é o princípio certo — mas vale ser honesto: 80% do relógio de um hackathon de 24h gasto só pesquisando não deixa tempo suficiente pra construir algo que dê pra demonstrar. O ganho real da régua 80/20 não é literalmente o tempo — é o RIGOR concentrado no início, antes de qualquer linha de código. Aqui está como isso se traduz na prática, comprimido pra caber num hackathon real:

**Hora 0 – 1: Kickoff.** Time se reúne, escolhe o problema, define quem assume qual papel da Parte 2.

**Hora 1 – 4: Pesquisa + debate (5.1 e 5.2).** Várias frentes de pesquisa rodando em paralelo, seguidas do debate entre o que cada frente achou.

**Hora 4 – 5: Lobby (5.3).** Fecha numa proposta única, por escrito.

**Hora 5 – 6: Crítica adversarial (Parte 6).** Roda o checklist completo. Se a proposta não sobreviver, volta pra hora 1 com o que sobrou de tempo — é melhor descobrir agora do que na hora 20.

**Hora 6 – 8: Design (5.5 / Parte 7) + quebra do board.** Specs de interface em `.md`, e o board (Parte 4) já com as tarefas quebradas por função.

**Hora 8 – 20: Desenvolvimento (5.6).** Cada pessoa/agente na própria worktree (Parte 3), merge em ordem de dependência a cada 1 a 2 horas.

**Hora 20 – 22: Integração final.** Testes de ponta a ponta, ajustes finais, `git worktree remove` de tudo que já foi mesclado.

**Hora 22 – 24: Pitch.** Liaison (5.8) e orquestrador montam a apresentação já mapeada na tabela da Parte 8.2 — cada critério de julgamento com prova concreta, não improviso.

Isso deixa cerca de 25% do tempo total (6 das 24 horas) pra pesquisa, crítica e design antes de qualquer linha de código de produto — muito mais rigor do que a maioria dos times faz (que costuma ser zero), sem sacrificar as 14 horas de construção que um demo de verdade exige.

---

# Parte 10 — Ferramentas que já existem no mercado

Antes de construir algo do zero, vale saber o que já existe — talvez parte do problema já esteja resolvida por uma ferramenta pronta.

**Agor** (agor.live) — um "canvas" multiplayer construído em cima de branches de Git, com presença em tempo real (você vê o cursor de cada pessoa do time ao vivo), worktree isolada por sessão, e os próprios agentes conseguem ler e escrever no board através de um protocolo chamado MCP. É "source-available" (o código é visível, mas com licença restrita — BSL 1.1), ainda em estágio inicial.

**Claude Squad** — isola cada sessão de agente numa worktree própria automaticamente, sem você precisar rodar os comandos da Parte 3 na mão.

**Agent View, Minion Orchestra, biomelab** — dashboards que mostram o que vários agentes estão fazendo em tempo real, mas pensados pra UMA pessoa monitorando vários agentes seus — não pra um TIME inteiro de várias pessoas coordenado.

**agentree** — CLI leve só pra criar e gerenciar worktree por tarefa, sem toda a complexidade de uma plataforma completa.

**OpenClaw** — tem, desde a versão 0.8, um "Worktree Dispatcher" nativo que distribui tarefa automaticamente pra worktree livre, respeitando ordem de dependência entre elas.

Nenhuma dessas ferramentas junta as 10 partes desse livro verticalizado especificamente pra hackathon — cronograma, critério de julgamento mapeado, checklist de red team e biblioteca de design, tudo junto. Se quiser seguir essa ideia como produto, é exatamente aí que mora a diferenciação.

---

# Parte 11 — Estudo de caso completo, do início ao fim

Pra fechar, um exemplo fictício aplicando o livro inteiro, do zero até o pitch. Time de 4 pessoas, hackathon de 24h, tema livre em saúde.

**Hora 0-1.** O time define papéis: Ana é orquestradora, Bruno é integrador, Carla assume crítica adversarial, Diego é liaison — e todos os quatro, junto com seus agentes, também vão dividir tarefas de pesquisa e depois de dev.

**Hora 1-4.** Quatro agentes pesquisam em paralelo o problema "idosos esquecem de tomar remédio": um pesquisa apps concorrentes, um pesquisa por que idosos especificamente esquecem, um pesquisa dados de adesão a tratamento, um pesquisa se dá pra usar notificação nativa do celular sem exigir app novo. No debate que segue, surge a contradição chave: a pesquisa de usuário mostra que idosos não confiam em lembrete de app, mas confiam em ligação de um familiar — o produto muda de rumo ali mesmo.

**Hora 4-5.** Lobby fecha a proposta: "sistema que avisa um familiar quando o idoso não confirma que tomou o remédio, ao invés de só notificar o próprio idoso".

**Hora 5-6.** Carla roda o checklist da Parte 6. Premissa "familiar vai querer receber esse tipo de notificação" — checado contra os dados de pesquisa, sobrevive. Premissa "idoso vai confirmar manualmente que tomou o remédio" — contra-argumento forte: por que ele confirmaria uma coisa que já esqueceu de fazer? O time ajusta: em vez de confirmação manual, usam um sensor de abertura de caixa de remédio (mais barato e simples de simular no hackathon do que parecia de início). Passa no checklist.

**Hora 6-8.** Agente de design documenta em `/design/fluxos/confirmacao.md` como funciona a tela do familiar recebendo o alerta, os estados de erro, e o board é quebrado em 12 tarefas pequenas (T001 a T012), cada uma com dono.

**Hora 8-20.** Cada pessoa/agente na própria worktree — `../projeto-ana`, `../projeto-bruno`, etc. Bruno mescla a cada 1h30, sempre respeitando ordem de dependência (o schema do banco entra antes da tela que depende dele).

**Hora 20-22.** Integração final, testes end-to-end, worktrees antigas removidas.

**Hora 22-24.** Diego e Ana montam o pitch usando a tabela da Parte 8.2: inovação (o ângulo do familiar, não do idoso), viabilidade técnica (demo funcionando ao vivo), usabilidade (fluxo simples documentado), impacto real (premissa validada com dado, não achismo), pitch (a história do "por que família, não app" contada em 90 segundos).

---

# Parte 12 — Checklist final e glossário

## 12.1 Checklist rápido de execução

**Antes do hackathon**
- [ ] Papéis da Parte 2 definidos
- [ ] Board criado (Parte 4)
- [ ] Critério de "pronto" (Parte 8.2) publicado pro time inteiro

**Durante**
- [ ] 1 worktree por tarefa (Parte 3)
- [ ] Cada agente marca "peguei" antes de começar
- [ ] Sync de 5 minutos a cada 1-2h
- [ ] Merge em ordem de dependência
- [ ] `git worktree remove` depois de cada merge concluído

**No fim**
- [ ] Checklist de crítica adversarial (Parte 6) rodado ANTES do pitch, não depois
- [ ] Pitch já nasce mapeado nas 5 categorias da Parte 8.1

## 12.2 Glossário rápido

- **Repositório**: pasta do projeto com histórico completo guardado
- **Commit**: uma "foto" salva do código num momento
- **Branch**: linha do tempo paralela dentro do mesmo repositório
- **Merge**: juntar duas branches de volta numa só
- **Conflito de merge**: quando duas branches mudaram a mesma linha do mesmo arquivo de jeitos diferentes
- **Worktree**: várias pastas físicas do mesmo projeto, cada uma numa branch, compartilhando a mesma história
- **Agente de IA de código**: programa que escreve/edita código sozinho a partir de instrução em texto
- **Board/Kanban**: quadro visual de tarefas por coluna de status
- **Red team / crítica adversarial**: papel dedicado a atacar uma ideia de propósito antes dela virar produto
- **Debate multi-agente**: técnica de colocar agentes de IA discutindo entre si o mesmo problema
- **Desejável / viável / factível**: os três testes que toda premissa de produto precisa passar

