<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import type { Document } from "./lib/types"
  import {
    UPLOADS_URL,
    getArchivedDocuments,
    restoreArchivedDocument,
    permanentlyDeleteArchivedDocument,
    bulkRestoreArchivedDocuments,
    bulkPermanentlyDeleteArchivedDocuments
  } from "./lib/api"
  import { canEditDocuments } from "./lib/auth"

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

<div class="panel actions-bar">
  <span>Выбрано: {selectedIds.length}</span>
  <div class="bulk-actions">
    {#if $canEditDocuments}
      <button class="secondary" on:click={restoreSelected} disabled={!selectedIds.length}>Восстановить выбранные</button>
      <button class="danger" on:click={deleteSelectedPermanently} disabled={!selectedIds.length}>Удалить выбранные</button>
      <button class="secondary" on:click={clearSelection} disabled={!selectedIds.length}>Снять выбор</button>
    {:else}
      <span class="muted">Только просмотр. Войдите как editor/admin для изменения архива.</span>
    {/if}
  </div>
</div>

{#if loading}
  <div class="panel">Загрузка архива...</div>
{:else if !archivedDocs.length}
  <div class="panel">Архив пуст.</div>
{:else}
  <div class="archive-list">
    {#each archivedDocs as doc (doc._id)}
      <div class="document-card archive-card">
        <div class="archive-left">
          {#if $canEditDocuments}
            <input
              type="checkbox"
              checked={selectedIds.includes(doc._id)}
              on:change={() => toggleSelection(doc._id)}
            />
          {/if}
          <img
            src={`${UPLOADS_URL}/${doc.filename}?v=${encodeURIComponent(doc.image_version ?? doc.created_at ?? "")}`}
            alt={displayName(doc)}
            class="card-image"
            loading="lazy"
          />
        </div>

        <div class="card-content">
          <div class="card-title">{displayName(doc)}</div>
          <div class="card-meta">Архивировано: {doc.archived_at ? new Date(doc.archived_at).toLocaleString() : "—"}</div>
        </div>

        <div class="card-actions">
          {#if $canEditDocuments}
            <button class="secondary" on:click={() => restoreOne(doc._id)}>Восстановить</button>
            <button class="danger" on:click={() => deleteOnePermanently(doc._id)}>Удалить навсегда</button>
          {/if}
        </div>
      </div>
    {/each}
  </div>
{/if}

<style>
  .nav-panel,
  .archive-panel,
  .actions-bar {
    margin-bottom: 12px;
    padding: 14px;
  }

  .actions-bar {
    display: flex;
    justify-content: space-between;
    gap: 12px;
    align-items: center;
    flex-wrap: wrap;
    text-align: left;
  }

  .bulk-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .archive-list {
    display: grid;
    gap: 12px;
  }

  .archive-card {
    display: grid;
    grid-template-columns: auto 1fr auto;
    gap: 12px;
    align-items: center;
    padding: 12px;
    text-align: left;
    transition: transform 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
  }

  .archive-card:hover {
    transform: translateY(-1px);
    border-color: var(--border-strong);
    box-shadow: 0 6px 18px rgba(28, 39, 56, 0.12);
  }

  .archive-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .card-actions {
    display: flex;
    gap: 8px;
    align-items: center;
    justify-content: flex-end;
    flex-wrap: wrap;
  }

  @media (max-width: 700px) {
    .archive-card {
      grid-template-columns: 1fr;
      gap: 10px;
    }

    .card-actions {
      justify-content: flex-start;
    }
  }
</style>
