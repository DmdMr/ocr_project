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
      Веб-приложение для работы с карточками документов: загрузка изображений,
      автоматическое распознавание текста (OCR), быстрый поиск и удобная организация данных.
    </p>
  </section>

  <div class="about-grid">
    <section class="about-card card">
      <h2>✨ Что это за проект</h2>
      <p>
        OCR Project — это система для перевода бумажных карточек в цифровой формат.
        Пользователь загружает изображение, система автоматически распознаёт текст
        и сохраняет результат в виде карточки документа.
      </p>
      <p>
        Приложение объединяет несколько функций в одном интерфейсе:
        хранение документов, поиск по данным, редактирование текста и работа с тегами.
        Это позволяет быстро находить и обрабатывать нужную информацию.
      </p>
    </section>

    <section class="about-card card">
      <h2>📌 Как начать работу</h2>
      <ul class="about-list">
        <li>загрузите изображение карточки;</li>
        <li>дождитесь распознавания текста;</li>
        <li>откройте карточку и проверьте данные;</li>
        <li>добавьте теги для удобства;</li>
        <li>используйте поиск для быстрого доступа.</li>
      </ul>
    </section>

    <section class="about-card card">
      <h2>🧩 Что умеет приложение</h2>
      <ul class="about-list">
        <li>загрузка изображений (PNG, JPG, JPEG);</li>
        <li>автоматическое распознавание текста (OCR);</li>
        <li>сохранение карточек документов;</li>
        <li>поиск по имени файла, тексту и тегам;</li>
        <li>сортировка по дате и названию;</li>
        <li>просмотр и редактирование карточек;</li>
        <li>редактирование распознанного текста;</li>
        <li>переименование документов;</li>
        <li>добавление и удаление тегов;</li>
        <li>групповые операции с карточками;</li>
        <li>обнаружение дубликатов;</li>
        <li>поворот и обрезка изображений.</li>
      </ul>
    </section>

    <section class="about-card card">
      <h2>⚙️ Как это работает</h2>
      <p>
        После загрузки изображения система автоматически запускает распознавание текста.
        В зависимости от типа изображения используются разные модели для печатного
        и рукописного текста.
      </p>
      <p>
        Результат сохраняется в карточке документа, где пользователь может проверить
        распознанный текст, отредактировать его и добавить теги.
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
        Система поиска позволяет находить документы по нескольким параметрам:
        имени файла, распознанному тексту и тегам.
        Это значительно ускоряет работу с большим количеством карточек.
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
        Основная цель проекта — упростить работу с бумажными карточками,
        переведя их в цифровой формат с возможностью быстрого поиска,
        редактирования и организации данных.
      </p>
      <p>
        Пользователь должен иметь возможность загрузить файл, получить текст,
        проверить результат и организовать документы без сложных действий и лишних настроек.
      </p>
    </section>

    <section class="about-card card about-card-wide">
      <h2>💾 Экспорт и импорт данных</h2>

      <p>
        Система позволяет переносить данные между компьютерами. Для этого необходимо
        сохранить папку с загруженными файлами и базу данных, а затем восстановить их
        на новом устройстве.
      </p>

      <h3>📤 Экспорт данных</h3>

      <p><strong>1. Архивация изображений (uploads):</strong></p>
      <pre class="code-block">tar -czvf uploads.tar.gz backend/uploads/</pre>

      <p><strong>2. Экспорт базы данных MongoDB:</strong></p>
      <ul class="about-list">
        <li>открыть терминал и запустить mongosh;</li>
        <li>выполнить команду <strong>show dbs</strong> для просмотра баз данных;</li>
        <li>выбрать нужную базу: <strong>use имя_базы</strong>;</li>
        <li>выйти из mongosh (команда <strong>exit</strong> или Ctrl+D);</li>
      </ul>

      <pre class="code-block">mongodump --db ocr_database --out dump/</pre>

      <p>После выполнения команды будет создана структура:</p>

      <pre class="code-block">
    dump/
    └── ocr_database/
        ├── documents.bson
        ├── documents.metadata.json
      </pre>

      <h3>📥 Импорт на новом компьютере</h3>

      <p><strong>1. Восстановление изображений:</strong></p>
      <pre class="code-block">tar -xzvf uploads.tar.gz</pre>

      <p><strong>2. Восстановление базы данных:</strong></p>
      <pre class="code-block">mongorestore --db ocr_database dump/ocr_database</pre>

      <p>
        После выполнения этих действий все карточки, изображения и данные будут
        доступны в системе на новом устройстве.
      </p>
    </section>

    <section class="about-card card about-card-wide">
      <h2>🛠️ Установка и настройка окружения</h2>

      <p>
        Для корректной работы проекта необходимо установить несколько компонентов:
        Python, Node.js, MongoDB и вспомогательные инструменты.
        Ниже приведена пошаговая инструкция для Windows (через winget).
      </p>

      <h3>🔍 Проверка наличия winget</h3>
      <p>Перед началом убедитесь, что у вас установлен пакетный менеджер winget:</p>

      <pre class="code-block">winget --version</pre>

      <p>
        Если команда не работает — обновите Windows или установите App Installer из Microsoft Store.
      </p>

      <h3>🐍 Установка Python</h3>

      <pre class="code-block">winget install -e --id Python.Python.3.12</pre>

      <p><strong>Проверка установки:</strong></p>

      <pre class="code-block">
    python --version
    pip --version
      </pre>

      <p>
        Python используется для backend-части и OCR-модулей.
      </p>

      <h3>🟢 Установка Node.js</h3>

      <pre class="code-block">winget install -e --id OpenJS.NodeJS</pre>

      <p><strong>Проверка:</strong></p>

      <pre class="code-block">
    node -v
    npm -v
      </pre>

      <p>
        Node.js необходим для запуска frontend-приложения.
      </p>

      <h3>🍃 Установка MongoDB</h3>

      <pre class="code-block">
    winget install -e --id MongoDB.Server
    winget install -e --id MongoDB.Shell
    winget install -e --id MongoDB.DatabaseTools
      </pre>

      <p>
        MongoDB используется для хранения карточек документов и тегов.
      </p>

      <h4>▶️ Запуск MongoDB</h4>

      <pre class="code-block">
    net start MongoDB
    mongosh
      </pre>

      <p>
        После запуска можно подключиться к базе данных через mongosh.
      </p>

      <h3>🔧 Установка Git</h3>

      <pre class="code-block">winget install -e --id Git.Git</pre>

      <p>
        Git используется для работы с репозиторием проекта.
      </p>

      <h3>💻 Установка Visual Studio Code</h3>

      <pre class="code-block">winget install -e --id Microsoft.VisualStudioCode</pre>

      <p>
        VS Code рекомендуется как основная среда разработки.
      </p>

      <h3>🚀 Настройка проекта после установки</h3>

      <p><strong>1. Создание виртуального окружения Python:</strong></p>

      <pre class="code-block">
    python -m venv venv
    venv\Scripts\activate
      </pre>

      <p><strong>2. Установка зависимостей backend:</strong></p>

      <pre class="code-block">pip install -r requirements.txt</pre>

      <p style="color: var(--text-muted); font-size: 0.9rem;">
        Если установка не проходит — проверьте версию Python и наличие pip.
      </p>

      <p><strong>3. Установка frontend-зависимостей:</strong></p>

      <pre class="code-block">
    cd frontend
    npm install
      </pre>

      <h3>⚡ Быстрая установка (одной командой)</h3>

      <p>
        Можно установить основные зависимости сразу:
      </p>

      <pre class="code-block">
    winget install -e --id Python.Python.3.12 `
    && winget install -e --id OpenJS.NodeJS `
    && winget install -e --id MongoDB.Server `
    && winget install -e --id MongoDB.Shell `
    && winget install -e --id MongoDB.DatabaseTools `
    && winget install -e --id Git.Git
      </pre>

      <p>
        После выполнения всех шагов система будет готова к запуску.
      </p>
    </section>

    <section class="about-card card about-card-wide">
      <h2>🔄 Оптимизация работы с карточками</h2>

      <p>
        В процессе разработки был проанализирован текущий процесс работы с карточками.
        Он оказался сложным, трудоёмким и требующим большого количества ручных действий.
      </p>

      <h3>📉 Текущий процесс (как было)</h3>

      <ul class="about-list">
        <li>сканирование документов с помощью принтера;</li>
        <li>получение PDF-файла и разбиение его на отдельные изображения;</li>
        <li>загрузка каждого изображения по отдельности;</li>
        <li>определение, какие изображения относятся к одной карточке;</li>
        <li>ручное распределение изображений по карточкам;</li>
        <li>переименование карточек вручную.</li>
      </ul>

      <p style="color: var(--text-muted);">
        Такой процесс занимает много времени, увеличивает вероятность ошибок
        и усложняет работу с документами.
      </p>

      <h3>📈 Улучшенный процесс (как стало)</h3>

      <ul class="about-list">
        <li>выбор конкретной карточки для работы;</li>
        <li>добавление лицевой стороны с помощью телефона;</li>
        <li>автоматическое создание карточки в системе;</li>
        <li>переход в карточку и добавление дополнительных изображений;</li>
        <li>редактирование данных на компьютере (название, обрезка и т.д.).</li>
      </ul>

      <p>
        Новый подход упрощает работу пользователя: вместо сложной обработки
        множества файлов система позволяет работать с каждой карточкой отдельно
        и последовательно.
      </p>

      <p style="font-weight: 500;">
        В результате снижается время обработки документов и уменьшается
        количество ошибок при работе с данными.
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
    transition: transform 0.15s ease, box-shadow 0.15s ease;
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

  .about-card:hover {
    transform: translateY(-2px);
  }

  .code-block {
    background: rgba(0, 0, 0, 0.35);
    padding: 0.75rem 1rem;
    border-radius: 10px;
    font-family: monospace;
    font-size: 0.9rem;
    overflow-x: auto;
    margin: 0.5rem 0 1rem;
    color: #e6edf3;
  }

  @media (max-width: 820px) {
    .about-grid {
      grid-template-columns: 1fr;
      gap: 1rem;
    }

    .about-card-wide {
      grid-column: auto;
    }

    .about-page {
      padding: 0.75rem 0 1.5rem;
    }

    .about-hero,
    .about-card {
      padding: 1rem;
    }

    .about-hero {
      margin-bottom: 1rem;
    }

    .about-hero-top {
      justify-content: center;
      margin-bottom: 0.75rem;
    }

    .hero-icon {
      font-size: 2rem;
      margin-bottom: 0.35rem;
    }

    .about-heading {
      margin-bottom: 0.5rem;
      font-size: 1.7rem;
      line-height: 1.15;
    }

    .about-subheading {
      font-size: 0.95rem;
      line-height: 1.5;
    }

    .about-card h2 {
      margin-bottom: 0.75rem;
      font-size: 1.05rem;
      line-height: 1.3;
    }

    .about-card p {
      margin-bottom: 0.7rem;
      font-size: 0.95rem;
      line-height: 1.55;
    }

    .about-list {
      padding-left: 1rem;
    }

    .about-list li {
      margin-bottom: 0.5rem;
      font-size: 0.95rem;
      line-height: 1.5;
    }

    .back-btn {
      width: 100%;
      justify-content: center;
    }

    .code-block {
      padding: 0.65rem 0.8rem;
      font-size: 0.82rem;
      border-radius: 8px;
      margin-bottom: 0.75rem;
    }
  }

  @media (max-width: 480px) {
    .about-page {
      padding: 0.5rem 0 1rem;
    }

    .about-hero,
    .about-card {
      padding: 0.85rem;
    }

    .about-grid {
      gap: 0.75rem;
    }

    .about-heading {
      font-size: 1.45rem;
    }

    .about-subheading,
    .about-card p,
    .about-list li {
      font-size: 0.9rem;
    }

    .about-card h2 {
      font-size: 1rem;
    }

    .hero-icon {
      font-size: 1.7rem;
    }

    .code-block {
      font-size: 0.78rem;
      padding: 0.6rem 0.7rem;
    }
  }
</style>