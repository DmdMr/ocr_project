<script lang="ts">
  import { createEventDispatcher } from "svelte"
  import { UPLOADS_URL } from "../../api"
  import type { AttachmentFile } from "../../types"

  export let attachments: AttachmentFile[] = []
  export let uploading = false
  export let error = ""

  const dispatch = createEventDispatcher<{
    upload: Event
    remove: { attachment: AttachmentFile }
  }>()

  function attachmentDownloadUrl(attachment: AttachmentFile) {
    return `${UPLOADS_URL}/${attachment.filename}`
  }

  function attachmentLabel(attachment: AttachmentFile) {
    return attachment.original_name || attachment.filename || "Файл"
  }
</script>

<section class="panel files-section">
  <div class="head">
    <h3>Файлы</h3>
    <label class="btn" class:disabled={uploading}>
      {uploading ? "Загрузка..." : "Добавить файлы"}
      <input type="file" multiple hidden disabled={uploading} on:change={(event) => dispatch("upload", event)} />
    </label>
  </div>
  {#if error}
    <p class="error">{error}</p>
  {/if}
  {#if attachments.length}
    {#each attachments as attachment}
      <div class="row">
        <a href={attachmentDownloadUrl(attachment)} target="_blank" rel="noreferrer">{attachmentLabel(attachment)}</a>
        <button class="danger" on:click={() => dispatch("remove", { attachment })}>Удалить</button>
      </div>
    {/each}
  {:else}
    <p class="empty">Пока нет прикрепленных файлов.</p>
  {/if}
</section>

<style>
  .files-section { padding: 14px; }
  .head { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
  .row { margin-top: 8px; display: flex; justify-content: space-between; gap: 10px; align-items: center; }
  .error { color: #ef4444; }
  .empty { color: var(--muted); }
</style>
