<script lang="ts">
  import type { Document } from "../../types"

  export let doc: Document
  export let filenameDraft = ""
  export let filenameEditing = false
  export let filenameError = ""

  export let onStartEdit: () => void
  export let onSave: () => void
  export let onCancel: () => void

  function formatCreatedAt(value?: string) {
    if (!value) return "—"
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return "—"
    return parsed.toLocaleString()
  }

  function getFilenameWithoutExtension(name: string) {
    if (!name) return ""
    const idx = name.lastIndexOf(".")
    return idx <= 0 ? name : name.slice(0, idx)
  }
</script>

<section class="doc-header panel">
  {#if filenameEditing}
    <div class="editor-row">
      <input bind:value={filenameDraft} aria-label="Document title" />
      <button class="primary" on:click={onSave}>Сохранить</button>
      <button on:click={onCancel}>Отмена</button>
    </div>
  {:else}
    <div class="title-row">
      <h1>{getFilenameWithoutExtension(doc.display_filename || doc.filename || "")}</h1>
      <button on:click={onStartEdit}>✎</button>
    </div>
  {/if}

  {#if filenameError}
    <p class="error">{filenameError}</p>
  {/if}

  <div class="meta-row">
    <span><strong>Создано:</strong> {formatCreatedAt(doc.created_at)}</span>
    <span><strong>Создал:</strong> {doc.created_by_username || "—"}</span>
    <span><strong>Изменил:</strong> {doc.updated_by_username || "—"}</span>
  </div>
</section>

<style>
  .doc-header {
    padding: 18px;
    margin-bottom: 14px;
  }
  .title-row { display: flex; align-items: center; gap: 10px; margin-top: 4px; }
  h1 { margin: 0; font-size: clamp(1.25rem, 2vw, 1.65rem); }
  .editor-row { display: flex; gap: 10px; margin-top: 6px; }
  .editor-row input { flex: 1; min-width: 180px; }
  .meta-row { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 12px; color: var(--muted); font-size: 0.9rem; }
  .error { color: #ef4444; margin: 8px 0 0; }
</style>
