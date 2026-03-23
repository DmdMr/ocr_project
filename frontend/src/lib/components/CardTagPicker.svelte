<script lang="ts">
  import { createEventDispatcher } from "svelte"
  import { tagHue } from "../tagColors"

  export let assignedTags: string[] = []
  export let allTags: string[] = []
  export let loading = false
  export let error = ""

  const dispatch = createEventDispatcher<{
    add: { tag: string }
    remove: { tag: string }
    close: undefined
  }>()

  let search = ""

  $: normalizedAssigned = assignedTags.map(tag => tag.trim().toLowerCase())
  $: filteredAssigned = assignedTags.filter(tag =>
    tag.toLowerCase().includes(search.trim().toLowerCase())
  )
  $: availableTags = allTags.filter(tag => !normalizedAssigned.includes(tag.trim().toLowerCase()))
  $: filteredAvailable = availableTags.filter(tag =>
    tag.toLowerCase().includes(search.trim().toLowerCase())
  )

  function close() {
    dispatch("close")
  }

  function addTag(tag: string) {
    dispatch("add", { tag })
  }

  function removeTag(tag: string) {
    dispatch("remove", { tag })
  }
</script>

<div class="picker-shell">
  <div class="picker-header">
    <div>
      <h3>Управление тегами</h3>
      <p>Нажмите на тег, чтобы добавить его к карточке или убрать из неё.</p>
    </div>
    <button class="close-btn" aria-label="Закрыть управление тегами" on:click={close}>✕</button>
  </div>

  <input
    class="search-input"
    type="text"
    placeholder="Поиск тегов"
    bind:value={search}
  />

  {#if error}
    <p class="error-message">{error}</p>
  {/if}

  <div class="picker-grid">
    <section class="picker-column">
      <div class="column-header">
        <h4>На карточке</h4>
        <span>{assignedTags.length}</span>
      </div>

      {#if filteredAssigned.length > 0}
        <div class="tag-list">
          {#each filteredAssigned as tag}
            <button
              class="tag-chip assigned tag-colored"
              style={`--tag-hue: ${tagHue(tag)}`}
              on:click={() => removeTag(tag)}
            >
              <span>{tag}</span>
              <span class="tag-action" aria-hidden="true">×</span>
            </button>
          {/each}
        </div>
      {:else}
        <p class="empty-state">
          {search.trim() ? "Назначенные теги не найдены" : "У этой карточки пока нет тегов"}
        </p>
      {/if}
    </section>

    <section class="picker-column">
      <div class="column-header">
        <h4>Доступные теги</h4>
        <span>{availableTags.length}</span>
      </div>

      {#if loading}
        <p class="empty-state">Загрузка тегов…</p>
      {:else if filteredAvailable.length > 0}
        <div class="tag-list">
          {#each filteredAvailable as tag}
            <button
              class="tag-chip available tag-colored"
              style={`--tag-hue: ${tagHue(tag)}`}
              on:click={() => addTag(tag)}
            >
              <span>{tag}</span>
              <span class="tag-action" aria-hidden="true">+</span>
            </button>
          {/each}
        </div>
      {:else}
        <p class="empty-state">
          {search.trim() ? "Подходящие теги не найдены" : "Все доступные теги уже добавлены"}
        </p>
      {/if}
    </section>
  </div>
</div>

<style>
  .picker-shell {
    width: min(680px, calc(100vw - 48px));
    max-height: min(560px, calc(100vh - 120px));
    overflow: auto;
    padding: 20px;
    border-radius: 24px;
    background: var(--surface-strong);
    border: 1px solid var(--border);
    box-shadow: var(--shadow-soft);
  }

  .picker-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    margin-bottom: 16px;
  }

  .picker-header h3 {
    margin: 0 0 6px;
    font-size: 1.15rem;
  }

  .picker-header p {
    margin: 0;
    color: var(--text-muted);
    line-height: 1.5;
  }

  .close-btn {
    min-width: 40px;
    min-height: 40px;
    border-radius: 999px;
  }

  .search-input {
    width: 100%;
    margin-bottom: 14px;
  }

  .error-message {
    margin: 0 0 14px;
    color: var(--danger);
  }

  .picker-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 16px;
  }

  .picker-column {
    padding: 14px;
    border-radius: 18px;
    background: var(--surface);
    border: 1px solid var(--border);
  }

  .column-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
    margin-bottom: 12px;
  }

  .column-header h4 {
    margin: 0;
    font-size: 0.98rem;
  }

  .column-header span {
    min-width: 28px;
    min-height: 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: var(--surface-elevated);
    color: var(--text-muted);
    font-size: 0.85rem;
  }

  .tag-list {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }

  .tag-chip {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    min-height: 36px;
    padding: 8px 12px;
    border-radius: 999px;
  }

  .tag-chip.assigned {
    border-color: color-mix(in srgb, var(--danger), transparent 40%);
  }

  .tag-chip.available {
    border-color: color-mix(in srgb, var(--primary), transparent 45%);
  }

  .tag-action {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    border-radius: 999px;
    background: rgba(255, 255, 255, 0.16);
    font-weight: 700;
    line-height: 1;
  }

  .empty-state {
    margin: 0;
    color: var(--text-muted);
    line-height: 1.5;
  }

  @media (max-width: 720px) {
    .picker-shell {
      width: min(100vw - 24px, 680px);
      padding: 16px;
    }

    .picker-grid {
      grid-template-columns: 1fr;
    }
  }
</style>
