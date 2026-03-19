<script lang="ts">
  import { onMount } from "svelte"


  export let viewMode: "grid" | "list" = "grid"


  let open = false

  const projectText = [
    "📄 Это приложение помогает извлекать текст с изображений документов (например, фото, сканов, чеков или заметок).",
    "📤 Загрузите один или несколько файлов, и система автоматически распознает текст на них.",
    "🧾 Для каждого изображения создаётся отдельная карточка документа.",
    "👁️ В карточке можно открыть изображение и посмотреть результат распознавания.",
    "✏️ При необходимости вы можете исправить текст вручную.",
    "📝 Также можно изменить название документа, чтобы его было легче найти.",
    "🏷️ Добавляйте теги (например: «договор», «чек», «личное») для удобной организации.",
    "🔍 Используйте поиск, чтобы находить документы по названию или тексту.",
    "↕️ Сортируйте документы по дате или по имени.",
    "💾 Все документы сохраняются, и вы можете вернуться к ним в любое время."
  ]

  function toggle() {
    open = !open
  }

  function close() {
    open = false
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

<button
  class="lifeguard-btn"
  aria-label="Справка по проекту"
  title="Справка по проекту"
  on:click={toggle}
>
  🆘
</button>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="help-overlay" use:portal on:click={close}>
    <div class="help-modal panel" on:click|stopPropagation>
      <button class="help-close" on:click={close}>✕</button>

      <h3>Навигатор по проекту</h3>

      <div class="setting-row">
      <span>Режим отображения</span>

      <div class="view-switch">
        <button
          class:active={viewMode === "grid"}
          on:click={() => viewMode = "grid"}
        >
          Сетка
        </button>

        <button
          class:active={viewMode === "list"}
          on:click={() => viewMode = "list"}
        >
          Список
        </button>
      </div>
    </div>

      <p class="intro">
        Этот блок помогает быстро понять, что делает проект и с чего начать работу.
      </p>

      <ul>
        {#each projectText as line}
          <li>{line}</li>
        {/each}
      </ul>

      <p class="footnote">
        Совет: начните с одного тестового изображения и сразу добавьте тег — так вы быстро проверите полный рабочий сценарий.
      </p>
    </div>
  </div>

  
{/if}








<style>
  .lifeguard-btn {
    position: fixed;
    right: 18px;
    bottom: 18px;
    width: 64px;
    min-height: 64px;
    border-radius: 999px;
    font-size: 1.9rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    line-height: 1;
    z-index: 1100;
    box-shadow: var(--shadow-soft);
  }

  .help-overlay {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(10, 14, 20, 0.56);
    z-index: 1200;
  }

  .help-modal {
    width: min(780px, 92vw);
    max-height: 82vh;
    overflow: auto;
    text-align: left;
    padding: 22px;
    position: relative;
  }

  .help-close {
    position: absolute;
    right: 14px;
    top: 14px;
    min-height: 32px;
    width: 32px;
    border-radius: 999px;
    padding: 0;
    box-shadow: none;
  }

  h3 {
    margin-top: 0;
    margin-bottom: 10px;
    padding-right: 40px;
  }

  .intro {
    margin-top: 0;
    color: var(--text-muted);
  }

  ul {
    margin: 10px 0 0;
    padding-left: 20px;
  }

  li {
    margin: 8px 0;
    color: var(--text);
    line-height: 1.4;
  }

  .footnote {
    margin-top: 14px;
    color: var(--text-muted);
    font-size: 0.92rem;
  }

</style>
