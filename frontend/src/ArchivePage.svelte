<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import type { Document } from "./lib/types"
  import {
    getArchivedDocuments,
    restoreArchivedDocument,
    permanentlyDeleteArchivedDocument,
    bulkRestoreArchivedDocuments,
    bulkPermanentlyDeleteArchivedDocuments
  } from "./lib/api"

  let archivedDocs: Document[] = []
  let selectedIds: string[] = []
  let loading = false

  function toggleSelection(id: string) {
    selectedIds = selectedIds.includes(id)
      ? selectedIds.filter(item => item !== id)
      : [...selectedIds, id]
  }

  function clearSelection() {
    selectedIds = []
  }

  async function loadArchived() {
    loading = true
    try {
      archivedDocs = await getArchivedDocuments()
    } finally {
      loading = false
    }
  }

  async function restoreOne(id: string) {
    await restoreArchivedDocument(id)
    archivedDocs = archivedDocs.filter(doc => doc._id !== id)
    selectedIds = selectedIds.filter(item => item !== id)
  }

  async function deleteOnePermanently(id: string) {
    const confirmed = confirm("Удалить карточку навсегда?")
    if (!confirmed) return
    await permanentlyDeleteArchivedDocument(id)
    archivedDocs = archivedDocs.filter(doc => doc._id !== id)
    selectedIds = selectedIds.filter(item => item !== id)
  }

  async function restoreSelected() {
    if (!selectedIds.length) return
    await bulkRestoreArchivedDocuments(selectedIds)
    archivedDocs = archivedDocs.filter(doc => !selectedIds.includes(doc._id))
    clearSelection()
  }

  async function deleteSelectedPermanently() {
    if (!selectedIds.length) return
    const confirmed = confirm(`Удалить навсегда ${selectedIds.length} карточек?`)
    if (!confirmed) return
    await bulkPermanentlyDeleteArchivedDocuments(selectedIds)
    archivedDocs = archivedDocs.filter(doc => !selectedIds.includes(doc._id))
    clearSelection()
  }

  function displayName(doc: Document) {
    return doc.display_filename || doc.filename || "Без имени"
  }

  onMount(loadArchived)
</script>

<div class="panel nav-panel">
  <button on:click={() => push("/")}>Главная</button>
  <button on:click={() => push("/about")}>О проекте</button>
</div>

<div class="panel archive-panel">
  <h2>Архив карточек</h2>
  <p>Карточки хранятся в архиве до 30 дней, затем удаляются автоматически.</p>
</div>

{#if selectedIds.length > 0}
  <div class="panel actions">
    <span>Выбрано: {selectedIds.length}</span>
    <button on:click={restoreSelected}>Восстановить выбранные</button>
    <button class="danger" on:click={deleteSelectedPermanently}>Удалить выбранные навсегда</button>
    <button on:click={clearSelection}>Отмена</button>
  </div>
{/if}

{#if loading}
  <div class="panel">Загрузка архива...</div>
{:else if !archivedDocs.length}
  <div class="panel">Архив пуст.</div>
{:else}
  <div class="archive-list">
    {#each archivedDocs as doc (doc._id)}
      <div class="panel archive-item">
        <label>
          <input
            type="checkbox"
            checked={selectedIds.includes(doc._id)}
            on:change={() => toggleSelection(doc._id)}
          />
          {displayName(doc)}
        </label>
        <small>Архивировано: {doc.archived_at ? new Date(doc.archived_at).toLocaleString() : "—"}</small>
        <div class="item-actions">
          <button on:click={() => restoreOne(doc._id)}>Восстановить</button>
          <button class="danger" on:click={() => deleteOnePermanently(doc._id)}>Удалить навсегда</button>
        </div>
      </div>
    {/each}
  </div>
{/if}

<style>
  .nav-panel, .archive-panel, .actions { margin-bottom: 12px; }
  .archive-list { display: grid; gap: 10px; }
  .archive-item { display: flex; flex-direction: column; gap: 8px; }
  .item-actions { display: flex; gap: 8px; flex-wrap: wrap; }
</style>
