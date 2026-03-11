<script lang="ts">
  import { afterUpdate, createEventDispatcher, onMount, tick } from "svelte"
  import { createTag, deleteTag, getTags, normalizeTag, tagExists } from "../api"
  import { tagHue } from "../tagColors"

  export let initialTags: string[] = []
  export let selectedTag: string | null = null

  const dispatch = createEventDispatcher<{
    select: { tag: string | null }
    tagsChanged: { tags: string[] }
  }>()

  let tags: string[] = []
  let createInput = ""
  let searchInput = ""
  let createError = ""
  let deleteMode = false
  let isExpanded = false
  let hasOverflow = false
  let tagsListEl: HTMLDivElement | null = null

  $: tags = [...initialTags]

  $: filteredTags = tags.filter(tag =>
    tag.toLowerCase().includes(searchInput.trim().toLowerCase())
  )

  async function updateOverflow() {
    await tick()

    if (!tagsListEl || isExpanded) return

    hasOverflow = tagsListEl.scrollWidth > tagsListEl.clientWidth + 1
  }

  function toggleExpanded() {
    isExpanded = !isExpanded

    if (!isExpanded) {
      void updateOverflow()
    }
  }

  async function submitTag() {
    const normalized = normalizeTag(createInput)
    createError = ""

    if (!normalized) return

    if (tagExists(tags, normalized)) {
      createError = "Tag already exists"
      return
    }

    try {
      await createTag(normalized)
      tags = [...tags, normalized]
      createInput = ""
      createError = ""
      dispatch("tagsChanged", { tags })
      void updateOverflow()
    } catch (error) {
      console.error("Failed to create tag", error)

      const latestTags = await getTags().catch(() => tags)
      const existsAfterFailure = tagExists(latestTags, normalized)

      if (existsAfterFailure) {
        tags = latestTags
        createInput = ""
        createError = ""
        dispatch("tagsChanged", { tags })
        void updateOverflow()
        return
      }

      createError = error instanceof Error ? error.message : "Failed to create tag"
    }
  }

  function handleCreateKeydown(event: KeyboardEvent) {
    if (event.key === "Enter") {
      event.preventDefault()
      submitTag()
    }
  }

  function selectTag(tag: string) {
    const nextSelected = selectedTag === tag ? null : tag

    dispatch("select", { tag: nextSelected })
  }

  async function removeTag(tag: string) {
    try {
      await deleteTag(tag)
      tags = tags.filter(existing => existing !== tag)
      const nextSelected = selectedTag === tag ? null : selectedTag

      dispatch("select", { tag: nextSelected })
      dispatch("tagsChanged", { tags })
      void updateOverflow()
    } catch (error) {
      console.error("Failed to delete tag", error)
      createError = error instanceof Error ? error.message : "Failed to delete tag"
    }
  }

  onMount(() => {
    const observer = new ResizeObserver(() => {
      if (!isExpanded) {
        void updateOverflow()
      }
    })

    if (tagsListEl) {
      observer.observe(tagsListEl)
    }

    void updateOverflow()

    return () => observer.disconnect()
  })

  afterUpdate(() => {
    if (!isExpanded) {
      void updateOverflow()
    }
  })
</script>

<div class="tag-manager panel">
  <div class="create-row">
    <input
      type="text"
      placeholder="Create tag"
      bind:value={createInput}
      on:keydown={handleCreateKeydown}
    />
    <button class="primary" on:click={submitTag}>Create Tag</button>
  </div>

  {#if createError}
    <p class="error">{createError}</p>
  {/if}

  <div class="toolbar">
    <input
      class="search"
      type="text"
      placeholder="Search tags"
      bind:value={searchInput}
    />
    <button class="mode-toggle" on:click={() => deleteMode = !deleteMode}>
      {deleteMode ? "Done" : "Select to delete"}
    </button>
  </div>

  <div class:expanded={isExpanded} bind:this={tagsListEl} class="tags-list">
    {#if filteredTags.length === 0}
      <p class="empty">No tags found</p>
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
            <button class="delete-tag" aria-label={`Delete ${tag}`} on:click={() => removeTag(tag)}>X</button>
          {/if}
        </div>
      {/each}
    {/if}
  </div>

  {#if hasOverflow}
    <div class="expand-row">
      <button class="expand-btn" on:click={toggleExpanded}>
        {isExpanded ? "Collapse tags" : "Expand tags"}
      </button>
    </div>
  {/if}
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
  }

  .create-row input,
  .search {
    flex: 1;
    min-height: 34px;
    padding: 0.38rem 0.7rem;
    font-size: 0.92rem;
  }

  .toolbar {
    display: flex;
    gap: 10px;
    align-items: center;
  }

  .mode-toggle {
    white-space: nowrap;
    min-height: 34px;
    padding: 0.35rem 0.75rem;
    font-size: 0.86rem;
  }

  .create-row button {
    min-height: 34px;
    padding: 0.35rem 0.8rem;
    font-size: 0.86rem;
  }

  .error {
    margin: 0 0 8px;
    color: var(--danger);
    font-size: 0.9rem;
  }

  .tags-list {
    display: flex;
    gap: 8px;
    flex-wrap: nowrap;
    overflow: hidden;
    margin-top: 8px;
    padding-bottom: 2px;
  }

  .tags-list.expanded {
    flex-wrap: wrap;
    overflow: visible;
  }

  .tag-chip-row {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    flex: 0 0 auto;
  }

  .tag-chip-row.deleting .tag-chip {
    cursor: default;
  }

  .tag-chip {
    border-radius: 999px;
    min-height: 30px;
    padding: 4px 11px;
    font-size: 0.85rem;
  }

  .tag-chip.selected {
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 68%);
    border-color: color-mix(in srgb, var(--primary), white 12%);
    transform: translateY(-1px);
  }

  .delete-tag {
    border-radius: 999px;
    min-height: 30px;
    padding: 4px 9px;
    min-width: auto;
    font-size: 0.82rem;
    background: linear-gradient(180deg, color-mix(in srgb, var(--danger), white 12%), var(--danger));
    color: #fff;
    border-color: transparent;
  }

  .expand-row {
    display: flex;
    justify-content: flex-end;
    margin-top: 8px;
  }

  .expand-btn {
    min-height: 30px;
    padding: 4px 10px;
    font-size: 0.8rem;
  }

  .empty {
    margin: 4px 0;
    opacity: 0.7;
  }
</style>
