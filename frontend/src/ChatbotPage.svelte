<script lang="ts">
  import { push } from "svelte-spa-router"
  import { knowledgeBase, type ChatKnowledgeEntry } from "./lib/chatbot/knowledgeBase"

  type ChatMessage = {
    id: string
    role: "assistant" | "user"
    text: string
    related?: ChatKnowledgeEntry[]
  }

  const STOP_WORDS = new Set([
    "и", "в", "во", "на", "по", "с", "со", "к", "ко", "о", "об", "про", "для", "как",
    "что", "это", "ли", "же", "а", "но", "или", "у", "из", "от", "до", "если", "не",
    "нужно", "можно", "есть", "мне", "мой", "моя", "мои", "ваш", "ваша", "ваши",
  ])

  const suggestedQuestions = [
    "Как загрузить документ в систему?",
    "Как добавить или убрать тег у карточки?",
    "Как искать документы?",
    "Можно ли обрезать или повернуть изображение?",
    "Как запустить проект локально?",
  ]

  let query = ""
  let messageCounter = 1
  let messages: ChatMessage[] = [
    {
      id: "assistant-welcome",
      role: "assistant",
      text:
        "Привет! Я помощник по OCR Project. Задайте вопрос на русском языке — я найду самые релевантные ответы в базе знаний проекта и подскажу, где что находится.",
      related: suggestedQuestions
        .map(question => knowledgeBase.find(entry => entry.question === question))
        .filter(Boolean) as ChatKnowledgeEntry[],
    },
  ]

  function normalizeText(value: string) {
    return value
      .toLowerCase()
      .replace(/ё/g, "е")
      .replace(/[^a-zа-я0-9\s]/gi, " ")
      .replace(/\s+/g, " ")
      .trim()
  }

  function tokenize(value: string) {
    return normalizeText(value)
      .split(" ")
      .filter(token => token.length > 1 && !STOP_WORDS.has(token))
  }

  function scoreEntry(entry: ChatKnowledgeEntry, userQuestion: string) {
    const normalizedQuestion = normalizeText(userQuestion)
    const userTokens = tokenize(userQuestion)

    if (!normalizedQuestion || userTokens.length === 0) return 0

    const questionText = normalizeText(entry.question)
    const answerText = normalizeText(entry.answer)
    const keywordText = normalizeText(entry.keywords.join(" "))

    let score = 0

    if (questionText.includes(normalizedQuestion)) score += 12
    if (answerText.includes(normalizedQuestion)) score += 7
    if (keywordText.includes(normalizedQuestion)) score += 6

    for (const token of userTokens) {
      if (questionText.includes(token)) score += 5
      if (answerText.includes(token)) score += 2
      if (keywordText.includes(token)) score += 4
    }

    const tokenSet = new Set(userTokens)
    const overlapInQuestion = tokenize(entry.question).filter(token => tokenSet.has(token)).length
    const overlapInAnswer = tokenize(entry.answer).filter(token => tokenSet.has(token)).length
    score += overlapInQuestion * 3 + overlapInAnswer

    return score
  }

  function searchKnowledgeBase(userQuestion: string) {
    return knowledgeBase
      .map(entry => ({ entry, score: scoreEntry(entry, userQuestion) }))
      .filter(item => item.score > 0)
      .sort((a, b) => b.score - a.score)
      .slice(0, 3)
      .map(item => item.entry)
  }

  function composeAssistantReply(userQuestion: string) {
    const results = searchKnowledgeBase(userQuestion)

    if (results.length === 0) {
      return {
        text:
          "Я не нашёл точного ответа в базе знаний. Попробуйте переформулировать вопрос короче или спросить, например, про загрузку документов, OCR, теги, поиск, карточки, галерею, редактирование изображения или локальный запуск проекта.",
        related: [],
      }
    }

    const [primary, ...others] = results
    const lines = [
      `Похоже, наиболее релевантный ответ такой: ${primary.answer}`,
    ]

    if (primary.relatedQuestions?.length) {
      lines.push(`Также рядом по смыслу: ${primary.relatedQuestions.join("; ")}.`)
    }

    if (others.length > 0) {
      lines.push(
        `Дополнительно может пригодиться: ${others.map(entry => entry.question).join("; ")}.`
      )
    }

    return {
      text: lines.join("\n\n"),
      related: results,
    }
  }

  function ask(questionText: string) {
    const trimmed = questionText.trim()
    if (!trimmed) return

    messages = [
      ...messages,
      {
        id: `user-${messageCounter++}`,
        role: "user",
        text: trimmed,
      },
    ]

    const reply = composeAssistantReply(trimmed)
    messages = [
      ...messages,
      {
        id: `assistant-${messageCounter++}`,
        role: "assistant",
        text: reply.text,
        related: reply.related,
      },
    ]

    query = ""
  }

  function submit() {
    ask(query)
  }
</script>

<div class="assistant-page">
  <section class="assistant-hero card">
    <div class="assistant-topbar">
      <button class="back-btn" on:click={() => push("/")}>← Назад на главную</button>
      <button class="ghost-btn" on:click={() => push("/about")}>О проекте</button>
    </div>

    <div class="hero-copy">
      <div class="hero-badge">Чат-помощник</div>
      <h1>Помощник по OCR Project</h1>
      <p>
        Этот чат отвечает на вопросы о загрузке документов, OCR, тегах, карточках,
        поиске, галерее и локальном запуске проекта. Ответы подбираются из встроенной
        русскоязычной базы знаний по наиболее релевантному совпадению.
      </p>
    </div>
  </section>

  <div class="assistant-layout">
    <aside class="assistant-sidebar panel">
      <h2>Что можно спросить</h2>
      <div class="suggestion-list">
        {#each suggestedQuestions as suggestion}
          <button class="suggestion-btn" on:click={() => ask(suggestion)}>
            {suggestion}
          </button>
        {/each}
      </div>

      <div class="knowledge-note">
        <h3>Как это работает</h3>
        <p>
          Помощник ищет совпадения по тексту вопроса, ключевым словам и содержимому
          ответов. Затем он выбирает самые релевантные записи из базы знаний и
          формирует ответ в удобном виде.
        </p>
        <p>
          Сейчас база знаний заполнена вручную и ориентирована именно на OCR Project.
        </p>
      </div>
    </aside>

    <section class="assistant-chat panel">
      <div class="chat-header">
        <div>
          <h2>Диалог</h2>
          <p>Задайте вопрос на русском языке.</p>
        </div>
      </div>

      <div class="chat-thread">
        {#each messages as message}
          <article class:assistant={message.role === "assistant"} class:user={message.role === "user"} class="chat-message">
            <div class="message-role">{message.role === "assistant" ? "Помощник" : "Вы"}</div>
            <p>{message.text}</p>

            {#if message.role === "assistant" && message.related?.length}
              <div class="related-box">
                <span>Похожие темы:</span>
                <div class="related-list">
                  {#each message.related as entry}
                    <button class="related-chip" on:click={() => ask(entry.question)}>
                      {entry.question}
                    </button>
                  {/each}
                </div>
              </div>
            {/if}
          </article>
        {/each}
      </div>

      <form
        class="chat-input"
        on:submit|preventDefault={submit}
      >
        <textarea
          rows="3"
          bind:value={query}
          placeholder="Например: как добавить тег к карточке?"
        ></textarea>
        <div class="chat-actions">
          <button type="button" on:click={() => (query = "")}>Очистить</button>
          <button class="primary" type="submit">Спросить</button>
        </div>
      </form>
    </section>
  </div>
</div>

<style>
  .assistant-page {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    text-align: left;
  }

  .assistant-hero {
    padding: 1.5rem;
  }

  .assistant-topbar {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    flex-wrap: wrap;
    margin-bottom: 1.25rem;
  }

  .hero-copy h1 {
    margin-bottom: 0.75rem;
  }

  .hero-copy p {
    margin: 0;
    max-width: 760px;
    color: var(--text-muted);
  }

  .hero-badge {
    display: inline-flex;
    margin-bottom: 0.75rem;
    padding: 0.35rem 0.75rem;
    border-radius: 999px;
    background: color-mix(in srgb, var(--primary), white 86%);
    color: var(--primary);
    font-weight: 700;
    font-size: 0.9rem;
  }

  .assistant-layout {
    display: grid;
    grid-template-columns: minmax(260px, 320px) minmax(0, 1fr);
    gap: 1.25rem;
    align-items: start;
  }

  .assistant-sidebar,
  .assistant-chat {
    padding: 1.25rem;
  }

  .assistant-sidebar h2,
  .assistant-chat h2,
  .knowledge-note h3 {
    margin-top: 0;
  }

  .suggestion-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  .suggestion-btn,
  .related-chip {
    text-align: left;
  }

  .knowledge-note {
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--border);
    color: var(--text-muted);
  }

  .assistant-chat {
    min-height: 70vh;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }

  .chat-header p {
    margin: 0;
    color: var(--text-muted);
  }

  .chat-thread {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    flex: 1;
    min-height: 420px;
  }

  .chat-message {
    max-width: min(88%, 760px);
    padding: 1rem 1rem 0.9rem;
    border-radius: 20px;
    border: 1px solid var(--border);
    box-shadow: var(--shadow-soft);
  }

  .chat-message.assistant {
    align-self: flex-start;
    background: var(--surface-elevated);
  }

  .chat-message.user {
    align-self: flex-end;
    background: color-mix(in srgb, var(--primary), white 88%);
    border-color: color-mix(in srgb, var(--primary), white 70%);
  }

  .message-role {
    margin-bottom: 0.45rem;
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--text-muted);
  }

  .chat-message p {
    margin: 0;
    white-space: pre-line;
  }

  .related-box {
    margin-top: 0.9rem;
    padding-top: 0.9rem;
    border-top: 1px solid var(--border);
  }

  .related-box span {
    display: block;
    margin-bottom: 0.5rem;
    font-size: 0.9rem;
    color: var(--text-muted);
  }

  .related-list {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
  }

  .chat-input {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    padding-top: 0.5rem;
    border-top: 1px solid var(--border);
  }

  .chat-input textarea {
    min-height: 110px;
    resize: vertical;
  }

  .chat-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.75rem;
  }

  .ghost-btn {
    background: transparent;
  }

  @media (max-width: 900px) {
    .assistant-layout {
      grid-template-columns: 1fr;
    }

    .assistant-chat {
      min-height: auto;
    }

    .chat-message {
      max-width: 100%;
    }
  }
</style>
