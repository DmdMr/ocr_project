<script lang="ts">
  import { createEventDispatcher } from "svelte"
  import { UPLOADS_URL } from "../../api"
  import type { AttachmentFile } from "../../types"

  export let attachments: AttachmentFile[] = []
  export let uploading = false
  export let uploadProgress = 0
  export let error = ""
  export let successMessage = ""

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
    <label class="upload-btn" class:disabled={uploading}>
      {uploading ? `Загрузка ${uploadProgress}%` : "Добавить файлы"}
      <input type="file" multiple hidden disabled={uploading} on:change={(event) => dispatch("upload", event)} />
    </label>
  </div>

  {#if uploading}
    <div class="progress-wrap"><div class="progress" style={`width:${uploadProgress}%`}></div></div>
  {/if}
  {#if successMessage}
    <p class="success">{successMessage}</p>
  {/if}
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
  .upload-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 36px;
    padding: 8px 12px;
    border-radius: 10px;
    border: 1px solid var(--border);
    background: var(--surface-strong);
    cursor: pointer;
    font-weight: 600;
  }
  .upload-btn.disabled { opacity: 0.6; pointer-events: none; }
  .progress-wrap { margin-top: 8px; height: 6px; background: var(--surface); border-radius: 999px; overflow: hidden; }
  .progress { height: 100%; background: #3b82f6; transition: width .18s ease; }
  .row { margin-top: 8px; display: flex; justify-content: space-between; gap: 10px; align-items: center; }
  .error { color: #ef4444; }
  .success { color: #16a34a; }
  .empty { color: var(--muted); }
</style>
