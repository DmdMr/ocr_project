<script lang="ts">
  import { createEventDispatcher } from "svelte"
  import { createTag, getTags, deleteTag, normalizeTag, tagExists } from "../api"
  import { tagHue } from "../tagColors"

  export let initialTags: string[] = []

  const dispatch = createEventDispatcher<{
    select: { tag: string | null }
    tagsChanged: { tags: string[] }
  }>()

  let tags: string[] = []
  let createInput = ""
  let searchInput = ""
  let selectedTag: string | null = null
  let createError = ""
  let deleteMode = false

  $: tags = [...initialTags]

  $: filteredTags = tags.filter(tag =>
    tag.toLowerCase().includes(searchInput.trim().toLowerCase())
  )

  async function submitTag() {
    const normalized = normalizeTag(createInput)
    createError = ""

    if (!normalized) return

    if (tagExists(tags, normalized)) {
      createError = "Тег уже существует"
      return
    }

    try {
      await createTag(normalized)
      tags = [...tags, normalized]
      createInput = ""
      createError = ""
      dispatch("tagsChanged", { tags })
    } catch (error) {
      console.error("Не удалось создать тег", error)
      
      const latestTags = await getTags().catch(() => tags)
      const existsAfterFailure = tagExists(latestTags, normalized)

      if (existsAfterFailure) {
        tags = latestTags
        createInput = ""
        createError = ""
        dispatch("tagsChanged", { tags })
        return
      }

      createError = error instanceof Error ? error.message : "Не удалось создать тег"
    }
  }

  function handleCreateKeydown(event: KeyboardEvent) {
    if (event.key === "Enter") {
      event.preventDefault()
      submitTag()
    }
  }

  function selectTag(tag: string) {
    selectedTag = selectedTag === tag ? null : tag
    dispatch("select", { tag: selectedTag })
  }

  async function removeTag(tag: string) {
    try {
      await deleteTag(tag)
      tags = tags.filter(existing => existing !== tag)

      if (selectedTag === tag) {
        selectedTag = null
        dispatch("select", { tag: null })
      }

      dispatch("tagsChanged", { tags })
    } catch (error) {
      console.error("Не удалось создать тег", error)
      createError = error instanceof Error ? error.message : "Не удалось создать тег"
    }
  }


</script>

<div class="tag-manager panel">
  <div class="create-row">
    <input
      type="text"
      placeholder="Создать тег"
      bind:value={createInput}
      on:keydown={handleCreateKeydown}
    />
    <button class="primary" on:click={submitTag}>Создать тег</button>
  </div>

  {#if createError}
    <p class="error">{createError}</p>
  {/if}

  <div class="toolbar">
    <input
      class="search"
      type="text"
      placeholder="Поиск тегов"
      bind:value={searchInput}
    />
    <button class="mode-toggle" on:click={() => deleteMode = !deleteMode}>
      {deleteMode ? "Готово" : "Выбрать для удаления"}
    </button>
  </div>



  <div class="tags-list">
    {#if filteredTags.length === 0}
      <p class="empty">Теги не найдены</p>
    {:else}
      {#each filteredTags as tag}
        <div class:deleting={deleteMode} class="tag-chip-row">
          <button
            class:selected={selectedTag === tag}
            class="tag-chip tag-colored"
            style={`--tag-hue: ${tagHue(tag)}`}
            on:click={() => !deleteMode && selectTag(tag)}
          >
            {tag}
          </button>

          {#if deleteMode}
            <button class="delete-tag" aria-label={`Удалить ${tag}`} on:click={() => removeTag(tag)}>X</button>
          {/if}
        </div>
      {/each}
    {/if}
  </div>
</div>

<style>
  .tag-manager {
    padding: 14px;
    margin-bottom: 16px;
    text-align: left;
  }

  .create-row {
    display: flex;
    gap: 10px;
    margin-bottom: 8px;
    flex-wrap: wrap;
  }

  .create-row input,
  .search {
    flex: 1;
    min-width: 0;
  }

  .error {
    margin: 0 0 8px;
    color: var(--danger);
    font-size: 0.9rem;
  }

  .tags-list {
    display: flex;
    flex-wrap: nowrap;
    gap: 8px;
    overflow: hidden;
    margin-top: 8px;
    padding-bottom: 0;
    align-items: center;
    min-height: 42px;
    position: relative;
  }


  .tag-chip {
    border-radius: 999px;
    padding: 8px 14px;
    max-width: 100%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .tag-chip.selected {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 68%);
    border-color: color-mix(in srgb, var(--primary), white 12%);
    transform: translateY(-1px);
  }

  .empty {
    margin: 4px 0;
    opacity: 0.7;
  }

  .toolbar {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
  }

  .mode-toggle {
    white-space: nowrap;
  }

  .tag-chip-row {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex-shrink: 0;
  }

  .tag-chip-row.deleting .tag-chip {
    cursor: default;
  }

  .delete-tag {
    border-radius: 999px;
    padding: 6px 10px;
    background: linear-gradient(180deg, color-mix(in srgb, var(--danger), white 12%), var(--danger));
    color: #fff;
    border-color: transparent;
  }

  .tags-list::-webkit-scrollbar {
    height: 6px;
  }

  .tags-list::-webkit-scrollbar-thumb {
    background: color-mix(in srgb, var(--text-muted), transparent 45%);
    border-radius: 999px;
  }

  @media (max-width: 640px) {
    .tag-manager {
      padding: 12px;
    }

    .create-row,
    .toolbar {
      display: grid;
      grid-template-columns: minmax(0, 1fr);
    }

    .create-row button,
    .mode-toggle {
      width: 100%;
    }
  }


  @media (max-width: 768px) {
  .tags-list {
    overflow-x: auto;
    overflow-y: hidden;
    -webkit-overflow-scrolling: touch; /* smooth iOS scroll */
    scrollbar-width: none; /* Firefox */
  }

  .tags-list::-webkit-scrollbar {
    display: none; /* Chrome/Safari */
  }
}

</style>
