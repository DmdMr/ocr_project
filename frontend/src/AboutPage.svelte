<script lang="ts">
  import { push } from "svelte-spa-router"
  import { onMount } from "svelte"

  let isHelpOpen = false

  function toggle() {
    isHelpOpen = !isHelpOpen
  }

  function close() {
    isHelpOpen = false
  }

  function handleKey(event: KeyboardEvent) {
    if (event.key === "Escape") {
      close()
    }
  }

  function portal(node: HTMLElement) {
    const target = document.body
    target.appendChild(node)

    return {
      destroy() {
        if (node.parentNode) node.parentNode.removeChild(node)
      }
    }
  }

  onMount(() => {
    window.addEventListener("keydown", handleKey)

    return () => {
      window.removeEventListener("keydown", handleKey)
    }
  })
</script>

<div class="about-page">
  <section class="about-hero card">
    <div class="about-hero-top">
      <button class="back-btn" on:click={() => push("/")}>
        ← Назад к рабочему пространству
      </button>
    </div>

    <div class="hero-icon">📄</div>
    <h1 class="about-heading">OCR Project</h1>
    <p class="about-subheading">
      Удобное веб-приложение для распознавания текста на изображениях,
      хранения файлов и управления документами в одном рабочем пространстве.
    </p>
  </section>

  <div class="about-grid">
    <section class="about-card card">
      <h2>✨ Что это за проект</h2>
      <p>
        OCR Project помогает превращать текст на изображениях в редактируемый цифровой текст.
        Пользователь загружает изображение, система распознаёт содержимое, а затем сохраняет
        результат в карточке документа.
      </p>
      <p>
        Это не просто OCR-инструмент, а полноценное пространство для работы с документами:
        здесь можно просматривать файлы, искать их, редактировать распознанный текст,
        присваивать теги и поддерживать коллекцию в порядке.
      </p>
    </section>

    <section class="about-card card">
      <h2>🧩 Что умеет приложение</h2>
      <ul class="about-list">
        <li>загружать изображения в форматах PNG, JPG и JPEG;</li>
        <li>распознавать текст автоматически после загрузки;</li>
        <li>сохранять документы и результаты распознавания;</li>
        <li>искать документы по имени файла, тексту и тегам;</li>
        <li>сортировать документы по дате и имени;</li>
        <li>открывать подробный просмотр карточки документа;</li>
        <li>редактировать распознанный текст;</li>
        <li>переименовывать отображаемое имя файла;</li>
        <li>добавлять и удалять теги;</li>
        <li>выполнять групповые действия с несколькими карточками;</li>
        <li>обнаруживать дубликаты файлов;</li>
        <li>поворачивать и обрезать изображения прямо в интерфейсе.</li>
      </ul>
    </section>

    <section class="about-card card">
      <h2>⚙️ Как это работает</h2>
      <p>
        После загрузки изображения система анализирует его содержимое и запускает
        процесс распознавания текста. В зависимости от типа изображения могут использоваться
        разные подходы: отдельно для печатного и отдельно для рукописного текста.
      </p>
      <p>
        После обработки создаётся карточка документа. В ней пользователь может посмотреть
        изображение, проверить результат распознавания, при необходимости исправить текст,
        добавить теги и продолжить работу с файлом позже.
      </p>
    </section>

    <section class="about-card card">
      <h2>🖼️ Работа с карточками</h2>
      <p>
        Каждая карточка документа содержит изображение, имя файла и связанные теги.
        При открытии карточки доступен расширенный просмотр: можно приблизить изображение,
        изменить его, обновить имя файла, отредактировать распознанный текст и управлять тегами.
      </p>
      <p>
        Такой подход делает работу с документами более наглядной: пользователь видит и сам файл,
        и текстовый результат, и дополнительные метки для удобной фильтрации.
      </p>
    </section>

    <section class="about-card card">
      <h2>🔎 Поиск и организация</h2>
      <p>
        Когда документов становится много, важна не только загрузка, но и удобная навигация.
        В проекте можно искать документы сразу по нескольким признакам: по имени файла,
        по распознанному тексту и по тегам.
      </p>
      <p>
        Для дополнительного порядка используются сортировка и теги. Это позволяет быстрее
        находить нужные материалы и объединять документы по темам, категориям или назначению.
      </p>
    </section>

    <section class="about-card card">
      <h2>👥 Для кого подходит проект</h2>
      <p>
        OCR Project может быть полезен студентам, преподавателям, исследователям,
        офисным сотрудникам и всем пользователям, которым нужно быстро перевести
        текст с изображения в цифровой формат.
      </p>
      <p>
        Проект особенно удобен в тех случаях, когда важно не только распознать текст,
        но и сохранить документ, отсортировать его, присвоить теги и вернуться к нему позже.
      </p>
    </section>

    <section class="about-card card">
      <h2>🛠️ Используемые технологии</h2>
      <ul class="about-list">
        <li><strong>Frontend:</strong> Svelte, TypeScript, Vite</li>
        <li><strong>Backend:</strong> FastAPI, Python, Uvicorn</li>
        <li><strong>База данных:</strong> MongoDB</li>
        <li><strong>OCR и ML:</strong> DocTR, TrOCR, PyTorch, Transformers</li>
        <li><strong>Обработка изображений:</strong> OpenCV, Pillow</li>
      </ul>
    </section>

    <section class="about-card card about-card-wide">
      <h2>🚀 Запуск проекта</h2>
      <p>
        Проект можно запускать локально в режиме разработки. Для этого обычно требуются
        Node.js для frontend-части, Python для backend-части, а также база данных MongoDB.
      </p>
      <p>
        После запуска пользователь получает доступ к интерфейсу, где можно загружать изображения,
        работать с карточками документов, выполнять поиск, редактировать результаты OCR и
        организовывать материалы с помощью тегов.
      </p>
      <p>
        В будущем проект может быть упакован в более удобный формат распространения,
        чтобы запуск был проще и не требовал ручной установки большого числа зависимостей.
      </p>
    </section>

    <section class="about-card card about-card-wide">
      <h2>📌 Основная цель проекта</h2>
      <p>
        Главная идея OCR Project — сделать работу с изображениями документов простой,
        понятной и удобной даже для пользователя, который не знаком с OCR-технологиями.
      </p>
      <p>
        Пользователь должен иметь возможность загрузить файл, получить текст,
        проверить результат и организовать документы без сложных действий и лишних настроек.
      </p>
    </section>
  </div>
</div>

<style>
  .about-page {
    max-width: 1100px;
    margin: 0 auto;
    padding: 1.5rem 0 3rem;
    text-align: left;
  }

  .about-hero {
    padding: 2rem;
    margin-bottom: 1.5rem;
    background: var(--surface-elevated);
    text-align: center;
  }

  .about-hero-top {
    display: flex;
    justify-content: flex-start;
    margin-bottom: 1rem;
  }

  .back-btn {
    min-height: 40px;
  }

  .hero-icon {
    font-size: 2.4rem;
    margin-bottom: 0.4rem;
  }

  .about-heading {
    margin: 0 0 0.75rem;
    font-size: clamp(2rem, 4vw, 2.8rem);
    line-height: 1.1;
    text-align: center;
  }

  .about-subheading {
    max-width: 760px;
    margin: 0 auto;
    color: var(--text-muted);
    font-size: 1.05rem;
    text-align: center;
    line-height: 1.7;
  }

  .about-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 1.25rem;
  }

  .about-card {
    padding: 1.5rem;
    text-align: left;
  }

  .about-card-wide {
    grid-column: 1 / -1;
  }

  .about-card h2 {
    margin: 0 0 1rem;
    font-size: 1.18rem;
    line-height: 1.35;
  }

  .about-card p {
    margin: 0 0 0.9rem;
    color: var(--text);
    line-height: 1.7;
  }

  .about-card p:last-child {
    margin-bottom: 0;
  }

  .about-list {
    margin: 0;
    padding-left: 1.1rem;
    text-align: left;
  }

  .about-list li {
    margin-bottom: 0.7rem;
    color: var(--text);
    line-height: 1.6;
  }

  .about-list li:last-child {
    margin-bottom: 0;
  }

  @media (max-width: 820px) {
    .about-grid {
      grid-template-columns: 1fr;
    }

    .about-card-wide {
      grid-column: auto;
    }

    .about-page {
      padding: 1rem 0 2rem;
    }

    .about-hero,
    .about-card {
      padding: 1.25rem;
    }

    .about-hero-top {
      justify-content: center;
    }
  }
</style>