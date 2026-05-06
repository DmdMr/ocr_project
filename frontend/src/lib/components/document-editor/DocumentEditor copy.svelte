<script lang="ts">
  export let value = ""
  export let editing = false
  export let canEdit = true
  export let onToggleEdit: () => void
  export let onSave: () => void

  import { createEventDispatcher } from "svelte"
  import { UPLOADS_URL } from "../../api"
  import type { AttachmentFile } from "../../types"

  export let attachments: AttachmentFile[] = []
  export let uploading = false
  export let uploadProgress = 0
  export let error = ""
  export let successMessage = ""
  export let canEdit = true

  const dispatch = createEventDispatcher<{
    upload: { files: File[] }
    remove: { attachment: AttachmentFile }
  }>()

  function attachmentDownloadUrl(attachment: AttachmentFile) {
    return `${UPLOADS_URL}/${attachment.filename}`
  }

  function attachmentLabel(attachment: AttachmentFile) {
    return attachment.original_name || attachment.filename || "Файл"
  }

  function emitSelectedFiles(event: Event) {
    const input = event.target as HTMLInputElement
    const files = Array.from(input.files ?? [])
    dispatch("upload", { files })
    input.value = ""
  }

  import type { Document } from "../../types"

  export let doc: Document
  export let filenameDraft = ""
  export let filenameEditing = false
  export let filenameError = ""
  export let canEdit = true

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

      import { createEventDispatcher } from "svelte"
  import { UPLOADS_URL } from "../../api"
  import type { GalleryImage } from "../../types"

  export let image: GalleryImage
  export let saving = false

  type Tool = "crop" | "rotate"
  let tool: Tool = "crop"
  let previewRotation = 0

  let imageEl: HTMLImageElement | null = null
  let stageEl: HTMLDivElement | null = null
  let isDrawing = false
  let startX = 0
  let startY = 0
  let cropRect: { x: number; y: number; width: number; height: number } | null = null

  const dispatch = createEventDispatcher<{
    close: void
    saveRotate: { filename: string; rotate: number }
    saveCrop: { filename: string; crop: { x_percent: number; y_percent: number; width_percent: number; height_percent: number } }
  }>()

  $: imageSrc = `${UPLOADS_URL}/${image.filename}?v=${encodeURIComponent(image.image_version ?? "")}`

  function nudge(dir: -1 | 1) {
    previewRotation = (((previewRotation + dir * 90) % 360) + 360) % 360
  }

  function getStageCoords(event: MouseEvent) {
    if (!imageEl || !stageEl) return null
    const imageRect = imageEl.getBoundingClientRect()
    const stageRect = stageEl.getBoundingClientRect()
    const clampedX = Math.min(Math.max(event.clientX, imageRect.left), imageRect.right)
    const clampedY = Math.min(Math.max(event.clientY, imageRect.top), imageRect.bottom)
    return {
      x: clampedX - imageRect.left,
      y: clampedY - imageRect.top,
      width: imageRect.width,
      height: imageRect.height,
      offsetLeft: imageRect.left - stageRect.left,
      offsetTop: imageRect.top - stageRect.top
    }
  }

  function onMouseDown(event: MouseEvent) {
    if (tool !== "crop") return
    event.preventDefault()
    const point = getStageCoords(event)
    if (!point) return
    isDrawing = true
    startX = point.x
    startY = point.y
    cropRect = { x: point.offsetLeft + point.x, y: point.offsetTop + point.y, width: 0, height: 0 }
  }

  function onMouseMove(event: MouseEvent) {
    if (tool !== "crop" || !isDrawing) return
    const point = getStageCoords(event)
    if (!point) return
    const left = Math.min(startX, point.x)
    const top = Math.min(startY, point.y)
    const width = Math.abs(point.x - startX)
    const height = Math.abs(point.y - startY)
    cropRect = { x: point.offsetLeft + left, y: point.offsetTop + top, width, height }
  }

  function onMouseUp() {
    isDrawing = false
  }

  function save() {
    if (tool === "rotate") {
      if (previewRotation === 0) return
      dispatch("saveRotate", { filename: image.filename, rotate: previewRotation })
      return
    }

    if (!cropRect || !imageEl || !stageEl) return
    const imageRect = imageEl.getBoundingClientRect()
    const stageRect = stageEl.getBoundingClientRect()
    const x = cropRect.x - (imageRect.left - stageRect.left)
    const y = cropRect.y - (imageRect.top - stageRect.top)

    const payload = {
      x_percent: Math.max(0, Math.min(100, (x / imageRect.width) * 100)),
      y_percent: Math.max(0, Math.min(100, (y / imageRect.height) * 100)),
      width_percent: Math.max(0.1, Math.min(100, (cropRect.width / imageRect.width) * 100)),
      height_percent: Math.max(0.1, Math.min(100, (cropRect.height / imageRect.height) * 100))
    }

    if (payload.width_percent < 1 || payload.height_percent < 1) return
    dispatch("saveCrop", { filename: image.filename, crop: payload })
  }


    import { createEventDispatcher } from "svelte"
  import type { CardCustomFieldSetting, Document } from "../../types"
  import { tagHue } from "../../tagColors"

  export let doc: Document
  export let customFieldSettings: CardCustomFieldSetting[] = []
  export let customFieldDraft: Record<string, string | number | string[] | null> = {}
  export let customFieldsStatus: "idle" | "saving" | "saved" | "error" = "idle"
  export let canEdit = true

  const dispatch = createEventDispatcher<{
    customFieldInput: { fieldName: string; value: string; saveNow?: boolean }
    manageTags: void
    deleteDoc: void
    addImages: { files: File[] }
  }>()

  function peopleDraftValue(value: string | number | string[] | null | undefined) {
    if (Array.isArray(value)) return value.join(", ")
    if (value === null || value === undefined) return ""
    return String(value)
  }

  function emitSelectedImages(event: Event) {
    const input = event.target as HTMLInputElement
    const files = Array.from(input.files ?? [])
    dispatch("addImages", { files })
    input.value = ""
  }


  import { createEventDispatcher } from "svelte"
  import { UPLOADS_URL } from "../../api"
  import type { GalleryImage } from "../../types"

  export let image: GalleryImage
  export let canDelete = true
  export let canEdit = true

  const dispatch = createEventDispatcher<{
    open: { filename: string }
    delete: { filename: string }
    edit: { filename: string }
  }>()

  $: imageSrc = `${UPLOADS_URL}/${image.filename}?v=${encodeURIComponent(image.image_version ?? "")}`

















</script>


























<section class="content panel">
  <div class="content-toolbar">
    <h2>Recognized text</h2>
    <div class="actions">
      {#if canEdit && editing}
        <button class="primary" on:click={onSave}>Сохранить OCR текст</button>
      {/if}
      {#if canEdit}
        <button on:click={onToggleEdit}>{editing ? "Просмотр" : "Редактировать"}</button>
      {/if}
    </div>
  </div>

  {#if editing}
    <textarea bind:value class="editor"></textarea>
  {:else}
    <article class="preview">{value || "Пусто"}</article>
  {/if}
</section>




<section class="panel files-section">
  <div class="head">
    <h3>Файлы</h3>
    {#if canEdit}
    <label class="upload-btn" class:disabled={uploading}>
      {uploading ? `Загрузка ${uploadProgress}%` : "Добавить файлы"}
      <input type="file" multiple hidden disabled={uploading} on:change={emitSelectedFiles} />
    </label>
    {/if}
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
        {#if canEdit}
          <button class="danger" on:click={() => dispatch("remove", { attachment })}>Удалить</button>
        {/if}
      </div>
    {/each}
  {:else}
    <p class="empty">Пока нет прикрепленных файлов.</p>
  {/if}
</section>


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
      {#if canEdit}
        <button on:click={onStartEdit}>✎</button>
      {/if}
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


<svelte:window on:mousemove={onMouseMove} on:mouseup={onMouseUp} />

<div class="backdrop" on:click={() => dispatch("close")}> 
  <div class="modal panel" on:click|stopPropagation>
    <div class="toolbar">
      <h3>Редактирование: {image.filename}</h3>
      <div class="tool-buttons">
        <button class:active={tool === "crop"} on:click={() => tool = "crop"}>Обрезка</button>
        <button class:active={tool === "rotate"} on:click={() => tool = "rotate"}>Поворот</button>
        {#if tool === "rotate"}
          <button on:click={() => nudge(-1)}>↺ 90°</button>
          <button on:click={() => nudge(1)}>↻ 90°</button>
        {/if}
      </div>
    </div>

    <div class="stage" bind:this={stageEl} on:mousedown={onMouseDown}>
      <img bind:this={imageEl} src={imageSrc} alt={image.filename} style={`transform: rotate(${tool === 'rotate' ? previewRotation : 0}deg);`} />
      {#if tool === "crop" && cropRect}
        <div class="crop" style={`left:${cropRect.x}px; top:${cropRect.y}px; width:${cropRect.width}px; height:${cropRect.height}px;`}></div>
      {/if}
    </div>

    <div class="actions">
      <button class="primary" disabled={saving} on:click={save}>{saving ? "Сохранение..." : "Применить"}</button>
      <button disabled={saving} on:click={() => dispatch("close")}>Отмена</button>
    </div>
  </div>
</div>


<section class="panel metadata">
  <div class="metadata-block">
    <div class="section-head">
      <h3>Теги</h3>
      {#if canEdit}
        <button on:click={() => dispatch("manageTags")}>Управлять</button>
      {/if}
    </div>
    <div class="tags">
      {#if doc.tags?.length}
        {#each doc.tags as tag}
          <span class="tag tag-colored" style={`--tag-hue: ${tagHue(tag)}`}>{tag}</span>
        {/each}
      {:else}
        <span class="muted">Нет тегов</span>
      {/if}
    </div>
  </div>

  <div class="metadata-block">
    <div class="section-head">
      <h3>Пользовательские поля</h3>
      <span class="save-state" data-state={customFieldsStatus}>
        {#if customFieldsStatus === "saving"}Saving...{/if}
        {#if customFieldsStatus === "saved"}Saved{/if}
        {#if customFieldsStatus === "error"}Error{/if}
      </span>
    </div>
    <div class="fields-grid">
      {#each customFieldSettings as field}
        <label>
          <span>{field.name}</span>
          <input
            type={field.type === "number" ? "number" : "text"}
            disabled={!canEdit}
            value={field.type === "people" ? peopleDraftValue(customFieldDraft[field.name]) : (customFieldDraft[field.name] ?? "")}
            on:input={(event) => dispatch("customFieldInput", { fieldName: field.name, value: (event.target as HTMLInputElement).value })}
            on:blur={(event) => dispatch("customFieldInput", { fieldName: field.name, value: (event.target as HTMLInputElement).value, saveNow: true })}
          />
        </label>
      {/each}
    </div>
  </div>

  <div class="metadata-block">
    <div class="section-head">
      <h3>Изображения</h3>
      {#if canEdit}
        <label class="upload-btn">
          Добавить изображения
          <input type="file" accept="image/png,image/jpeg,image/jpg" multiple hidden on:change={emitSelectedImages} />
        </label>
      {/if}
    </div>
  </div>

  <div class="metadata-block">
    <div class="section-head">
      <h3>Действия</h3>
      {#if canEdit}
        <button class="danger" on:click={() => dispatch("deleteDoc")}>Удалить документ</button>
      {/if}
    </div>
  </div>
</section>



<div class="image-block" id={`image-${image.filename}`} data-image-id={image.filename}>
  <button class="image-click" on:click={() => dispatch("open", { filename: image.filename })}>
    <img src={imageSrc} alt={image.filename} />
  </button>
  <div class="image-actions">
    {#if canEdit}
      <button on:click={() => dispatch("edit", { filename: image.filename })}>Edit image</button>
      <button class="danger" disabled={!canDelete} on:click={() => dispatch("delete", { filename: image.filename })}>Delete</button>
    {/if}
  </div>
</div>
































<style>
  .content { padding: 20px; min-height: 320px; }
  .content-toolbar { display: flex; justify-content: space-between; gap: 10px; align-items: center; margin-bottom: 12px; }
  .actions { display: flex; gap: 8px; }
  .editor {
    width: 100%;
    min-height: 420px;
    resize: vertical;
    font-size: 1rem;
    line-height: 1.6;
    padding: 12px;
  }
  .preview { white-space: pre-wrap; line-height: 1.65; min-height: 240px; }


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



  .backdrop { position: fixed; inset: 0; z-index: 1500; background: rgba(2, 6, 23, 0.72); display: grid; place-items: center; }
  .modal { width: min(1100px, 96vw); max-height: 92vh; overflow: auto; padding: 16px; }
  .toolbar { display: flex; justify-content: space-between; gap: 10px; align-items: center; margin-bottom: 10px; }
  .tool-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
  .tool-buttons button.active { border-color: var(--accent); }
  .stage { position: relative; min-height: 240px; display: grid; place-items: center; background: var(--surface); border-radius: 12px; padding: 10px; }
  .stage img { max-width: 100%; max-height: 70vh; user-select: none; }
  .crop { position: absolute; border: 2px dashed #38bdf8; background: color-mix(in srgb, #38bdf8, transparent 85%); pointer-events: none; }
  .actions { margin-top: 10px; display: flex; gap: 10px; justify-content: flex-end; }




  .metadata { padding: 14px; display: grid; gap: 12px; }
  .metadata-block { display: grid; gap: 8px; }
  .section-head { display: flex; justify-content: space-between; gap: 10px; align-items: center; }
  .tags { display: flex; flex-wrap: wrap; gap: 8px; }
  .fields-grid { display: grid; gap: 8px; }
  .fields-grid label { display: grid; gap: 4px; }
  .muted { color: var(--muted); }
  .save-state { font-size: 0.82rem; color: var(--muted); min-height: 18px; }
  .save-state[data-state="saving"] { color: #3b82f6; }
  .save-state[data-state="saved"] { color: #16a34a; }
  .save-state[data-state="error"] { color: #ef4444; }
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




  .image-block { border: 1px solid var(--border); border-radius: 12px; padding: 12px; display: grid; gap: 10px; }
  .image-click { border: 0; padding: 0; background: transparent; width: 100%; cursor: zoom-in; }
  .image-click img { width: 100%; border-radius: 12px; display: block; }
  .image-actions { display: flex; flex-wrap: wrap; gap: 8px; }



























</style>














