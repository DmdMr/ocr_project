<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import type { AttachmentFile, CardCustomFieldSetting, Document, GalleryImage } from "./lib/types"
  import {
    deleteDocument,
    deleteDocumentAttachment,
    deleteDocumentImage,
    editDocumentImage,
    getDocumentById,
    getSettings,
    getTags,
    setDocumentTags,
    updateDocument,
    updateDocumentCustomFields,
    uploadDocumentAttachments,
    uploadImagesToDocument,
    UPLOADS_URL
  } from "./lib/api"
  import CardTagPicker from "./lib/components/CardTagPicker.svelte"
  import DocumentHeader from "./lib/components/document-editor/DocumentHeader.svelte"
  import DocumentMetadataSection from "./lib/components/document-editor/DocumentMetadataSection.svelte"
  import DocumentContentEditor from "./lib/components/document-editor/DocumentContentEditor.svelte"
  import DocumentImageBlock from "./lib/components/document-editor/DocumentImageBlock.svelte"
  import DocumentFilesSection from "./lib/components/document-editor/DocumentFilesSection.svelte"
  import DocumentImageEditorModal from "./lib/components/document-editor/DocumentImageEditorModal.svelte"
  import { canEditDocuments } from "./lib/auth"

  export let params: { id: string }

  let doc: Document | null = null
  let loading = true
  let error = ""

  let editedText = ""
  let editing = false
  let filenameEditing = false
  let filenameDraft = ""
  let filenameError = ""

  let attachmentUploadError = ""
  let attachmentsUploading = false
  let attachmentUploadProgress = 0
  let attachmentUploadSuccess = ""

  let galleryUploading = false
  let galleryUploadProgress = 0
  let galleryUploadSuccess = ""
  let galleryUploadError = ""

  let customFieldSettings: CardCustomFieldSetting[] = []
  let customFieldDraft: Record<string, string | number | string[] | null> = {}
  let customFieldsStatus: "idle" | "saving" | "saved" | "error" = "idle"
  let changedCustomFields = new Set<string>()

  let imageViewerOpen = false
  let selectedImageIndex = 0

  let imageEditorOpen = false
  let imageEditorSaving = false
  let imageBeingEdited: GalleryImage | null = null

  let tagPickerOpen = false
  let allTags: string[] = []
  let tagsLoading = false
  let tagsError = ""
  let saveStatusTimer: ReturnType<typeof setTimeout> | null = null

  $: galleryImages = (doc?.gallery_images?.length ? doc.gallery_images : doc ? [{ filename: doc.filename, image_version: doc.image_version }] : []) as GalleryImage[]
  $: selectedImage = galleryImages[selectedImageIndex] ?? galleryImages[0]
  $: selectedImageSrc = selectedImage ? `${UPLOADS_URL}/${selectedImage.filename}?v=${encodeURIComponent(selectedImage.image_version ?? "")}` : ""

  onMount(async () => {
    await loadDocument()
    await loadTags()
  })



  function goToFolder(folderId: string | null | undefined) {
    if (!folderId) {
      push("/")
      return
    }
    push(`/?folder=${encodeURIComponent(folderId)}`)
  }

  async function loadDocument() {
    loading = true
    error = ""
    try {
      const [found, settings] = await Promise.all([getDocumentById(params.id), getSettings()])
      if (!found?._id) {
        error = "Документ не найден"
        return
      }
      doc = found as Document
      editedText = found.recognized_text ?? ""
      filenameDraft = found.display_filename ?? found.filename
      customFieldSettings = settings.fields_for_cards ?? []
      syncDraftFromDocument(found as Document)
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось загрузить документ"
    } finally {
      loading = false
    }
  }

  function syncDraftFromDocument(value: Document) {
    const nextDraft: Record<string, string | number | string[] | null> = { ...(value.custom_fields ?? {}) }
    for (const field of customFieldSettings) {
      if (!(field.name in nextDraft)) nextDraft[field.name] = null
    }
    customFieldDraft = nextDraft
  }

  function splitFilenameParts(name: string) {
    const trimmed = name.trim()
    const dotIndex = trimmed.lastIndexOf(".")
    if (dotIndex <= 0) return { base: trimmed, extension: "" }
    return { base: trimmed.slice(0, dotIndex), extension: trimmed.slice(dotIndex) }
  }

  function normalizeFilenameDraft(value: string, originalName: string) {
    const trimmed = value.trim()
    if (!trimmed) return { error: "Имя файла не может быть пустым", value: "" }
    const { extension: originalExtension } = splitFilenameParts(originalName)
    if (!originalExtension) return { error: "", value: trimmed }
    const { base, extension } = splitFilenameParts(trimmed)
    const normalizedBase = (extension && extension.toLowerCase() === originalExtension.toLowerCase() ? base : trimmed).trim()
    if (!normalizedBase) return { error: "Имя файла не может быть пустым", value: "" }
    return { error: "", value: `${normalizedBase}${originalExtension}` }
  }

  async function saveText() {
    if (!$canEditDocuments) return
    if (!doc) return
    const updated = await updateDocument(doc._id, { recognized_text: editedText })
    applyDocumentUpdate(updated)
    editing = false
  }

  async function saveFilename() {
    if (!$canEditDocuments) return
    if (!doc) return
    const normalized = normalizeFilenameDraft(filenameDraft, doc.display_filename ?? doc.filename)
    if (normalized.error) {
      filenameError = normalized.error
      return
    }
    const updated = await updateDocument(doc._id, { display_filename: normalized.value })
    applyDocumentUpdate(updated)
    filenameEditing = false
    filenameError = ""
  }

  function normalizeFieldValue(type: "text" | "number" | "people", value: string) {
    if (type === "number") {
      if (!value.trim()) return null
      const parsed = Number(value)
      return Number.isFinite(parsed) ? parsed : null
    }
    if (type === "people") {
      return value.split(/[\n,]/).map((item) => item.trim()).filter(Boolean)
    }
    return value
  }

  function scheduleSavedStateClear() {
    if (saveStatusTimer) clearTimeout(saveStatusTimer)
    saveStatusTimer = setTimeout(() => {
      customFieldsStatus = "idle"
    }, 1300)
  }

  function onCustomFieldInput(fieldName: string, value: string, saveNow = false) {
    const field = customFieldSettings.find((item) => item.name === fieldName)
    if (!field) return

    const normalized = normalizeFieldValue(field.type, value)
    customFieldDraft = { ...customFieldDraft, [fieldName]: normalized }

    const oldValue = doc?.custom_fields?.[fieldName] ?? null
    if (JSON.stringify(oldValue) === JSON.stringify(normalized)) {
      changedCustomFields.delete(fieldName)
    } else {
      changedCustomFields.add(fieldName)
    }

    if (saveNow) {
      saveChangedCustomFields()
    }
  }

  async function saveChangedCustomFields() {
    if (!$canEditDocuments) return
    if (!doc || !changedCustomFields.size) return

    const payload: Record<string, string | number | string[] | null> = {}
    for (const key of changedCustomFields) {
      payload[key] = customFieldDraft[key] ?? null
    }

    customFieldsStatus = "saving"
    try {
      const updated = await updateDocumentCustomFields(doc._id, payload)
      applyDocumentUpdate(updated)
      changedCustomFields = new Set<string>()
      customFieldsStatus = "saved"
      scheduleSavedStateClear()
    } catch {
      customFieldsStatus = "error"
    }
  }

  async function handleAttachmentUpload(event: CustomEvent<{ files: File[] }>) {
    if (!$canEditDocuments) return
    if (!doc) return
    const files = event.detail.files ?? []
    if (!files.length) return
    attachmentUploadSuccess = ""

    const nonImageFiles = files.filter((file) => !file.type.startsWith("image/"))
    if (!nonImageFiles.length) {
      attachmentUploadError = "Изображения добавляйте в секции изображений"
      return
    }

    attachmentsUploading = true
    attachmentUploadProgress = 0
    attachmentUploadError = ""

    try {
      const result = await uploadDocumentAttachments(doc._id, nonImageFiles, (percent) => attachmentUploadProgress = percent)
      if (result.document) applyDocumentUpdate(result.document)
      attachmentUploadSuccess = `Файлы загружены: ${result.added_count ?? nonImageFiles.length}`
      attachmentUploadError = result.skipped_files?.join("; ") ?? ""
    } catch (err) {
      attachmentUploadError = err instanceof Error ? err.message : "Не удалось прикрепить файлы"
    } finally {
      attachmentsUploading = false
    }
  }

  async function handleGalleryUpload(event: CustomEvent<{ files: File[] }>) {
    if (!$canEditDocuments) return
    if (!doc) return
    const files = event.detail.files ?? []
    if (!files.length) return
    galleryUploadSuccess = ""
    galleryUploading = true
    galleryUploadProgress = 0
    galleryUploadError = ""

    try {
      const result = await uploadImagesToDocument(doc._id, files, (percent) => galleryUploadProgress = percent)
      if (result.document) applyDocumentUpdate(result.document)
      galleryUploadSuccess = `Изображения добавлены: ${result.added_count ?? files.length}`
    } catch (err) {
      galleryUploadError = err instanceof Error ? err.message : "Не удалось загрузить изображения"
    } finally {
      galleryUploading = false
    }
  }

  async function removeAttachment(attachment: AttachmentFile) {
    if (!$canEditDocuments) return
    if (!doc || !attachment.filename) return
    const updated = await deleteDocumentAttachment(doc._id, attachment.filename)
    applyDocumentUpdate(updated)
  }

  async function removeImage(filename: string) {
    if (!$canEditDocuments) return
    if (!doc || galleryImages.length <= 1) return
    if (!confirm("Удалить это изображение?")) return
    const updated = await deleteDocumentImage(doc._id, filename)
    applyDocumentUpdate(updated)
  }

  function openImage(filename: string) {
    const idx = galleryImages.findIndex((item) => item.filename === filename)
    selectedImageIndex = idx >= 0 ? idx : 0
    imageViewerOpen = true
  }

  function openImageEditor(filename: string) {
    if (!$canEditDocuments) return
    imageBeingEdited = galleryImages.find((item) => item.filename === filename) ?? null
    imageEditorOpen = Boolean(imageBeingEdited)
  }

  async function applyRotate(event: CustomEvent<{ filename: string; rotate: number }>) {
    if (!$canEditDocuments) return
    if (!doc) return
    imageEditorSaving = true
    try {
      const updated = await editDocumentImage(doc._id, {
        image_filename: event.detail.filename,
        rotate_degrees: event.detail.rotate
      })
      applyDocumentUpdate(updated)
      imageEditorOpen = false
    } finally {
      imageEditorSaving = false
    }
  }

  async function applyCrop(event: CustomEvent<{ filename: string; crop: { x_percent: number; y_percent: number; width_percent: number; height_percent: number } }>) {
    if (!$canEditDocuments) return
    if (!doc) return
    imageEditorSaving = true
    try {
      const updated = await editDocumentImage(doc._id, {
        image_filename: event.detail.filename,
        crop: event.detail.crop
      })
      applyDocumentUpdate(updated)
      imageEditorOpen = false
    } finally {
      imageEditorSaving = false
    }
  }

  function showPreviousImage() {
    if (!galleryImages.length) return
    selectedImageIndex = selectedImageIndex <= 0 ? galleryImages.length - 1 : selectedImageIndex - 1
  }

  function showNextImage() {
    if (!galleryImages.length) return
    selectedImageIndex = selectedImageIndex >= galleryImages.length - 1 ? 0 : selectedImageIndex + 1
  }

  async function loadTags(force = false) {
    if (tagsLoading) return
    if (allTags.length && !force) return
    tagsLoading = true
    try {
      allTags = await getTags()
      tagsError = ""
    } catch (err) {
      tagsError = err instanceof Error ? err.message : "Не удалось загрузить теги"
    } finally {
      tagsLoading = false
    }
  }

  async function handleTagAdded(event: CustomEvent<{ tag: string }>) {
    if (!$canEditDocuments) return
    if (!doc) return
    const normalized = event.detail.tag.trim().toLowerCase()
    const currentTags = doc.tags ?? []
    if (currentTags.some((tag) => tag.trim().toLowerCase() === normalized)) return
    const updated = await setDocumentTags(doc._id, [...currentTags, normalized])
    applyDocumentUpdate(updated)
  }

  async function handleTagRemoved(event: CustomEvent<{ tag: string }>) {
    if (!$canEditDocuments) return
    if (!doc) return
    const normalized = event.detail.tag.trim().toLowerCase()
    const nextTags = (doc.tags ?? []).filter((tag) => tag.trim().toLowerCase() !== normalized)
    const updated = await setDocumentTags(doc._id, nextTags)
    applyDocumentUpdate(updated)
  }

  async function removeDocumentNow() {
    if (!$canEditDocuments) return
    if (!doc) return
    if (!confirm("Удалить карточку?")) return
    await deleteDocument(doc._id)
    push("/")
  }

  function applyDocumentUpdate(updated: Document) {
    doc = updated
    editedText = updated.recognized_text ?? ""
    filenameDraft = updated.display_filename ?? updated.filename
    syncDraftFromDocument(updated)
  }

</script>

{#if loading}
  <div class="page"><p>Загрузка документа...</p></div>
{:else if error || !doc}
  <div class="page"><p>{error || "Документ не найден"}</p></div>
{:else}
  <div class="page">
    <div class="page-top-row">
      <button class="back-btn" on:click={() => goToFolder(doc.folder_id)}>← Back to folder</button>
    </div>

    <nav class="doc-breadcrumbs" aria-label="Путь документа">
      <button class="crumb" on:click={() => goToFolder(null)}>Root</button>
      {#each doc.folder_path ?? [] as crumb}
        <span>/</span>
        <button class="crumb" on:click={() => goToFolder(crumb.id)}>{crumb.name}</button>
      {/each}
    </nav>

    <DocumentHeader
      {doc}
      canEdit={$canEditDocuments}
      bind:filenameDraft
      {filenameEditing}
      {filenameError}
      onStartEdit={() => filenameEditing = true}
      onSave={saveFilename}
      onCancel={() => {
        filenameEditing = false
        filenameDraft = doc?.display_filename ?? doc?.filename ?? ""
      }}
    />

    <div class="layout">
      <aside class="left-column">
        <DocumentMetadataSection
          {doc}
          canEdit={$canEditDocuments}
          {customFieldSettings}
          {customFieldDraft}
          {customFieldsStatus}
          on:customFieldInput={(event) => onCustomFieldInput(event.detail.fieldName, event.detail.value, event.detail.saveNow ?? false)}
          on:manageTags={() => tagPickerOpen = true}
          on:deleteDoc={removeDocumentNow}
          on:addImages={handleGalleryUpload}
        />

        {#if galleryUploading}
          <div class="panel progress-panel">
            <p>Uploading images... {galleryUploadProgress}%</p>
            <div class="progress-wrap"><div class="progress" style={`width:${galleryUploadProgress}%`}></div></div>
          </div>
        {/if}
        {#if galleryUploadSuccess}
          <p class="success-inline">{galleryUploadSuccess}</p>
        {/if}
        {#if galleryUploadError}
          <p class="error-inline">{galleryUploadError}</p>
        {/if}

        <DocumentFilesSection
          attachments={doc.attachments ?? []}
          canEdit={$canEditDocuments}
          uploading={attachmentsUploading}
          uploadProgress={attachmentUploadProgress}
          successMessage={attachmentUploadSuccess}
          error={attachmentUploadError}
          on:upload={handleAttachmentUpload}
          on:remove={(event) => removeAttachment(event.detail.attachment)}
        />
      </aside>

      <main class="center-column">
        <DocumentContentEditor
          bind:value={editedText}
          canEdit={$canEditDocuments}
          {editing}
          onToggleEdit={() => editing = !editing}
          onSave={saveText}
        />

        <section class="panel images-section">
          <h2>Image blocks</h2>
          <p class="hint">Изображения рендерятся как блоки внизу документа. Идентификатор: filename.</p>
          {#if !$canEditDocuments}
            <p class="hint">Sign in as editor/admin to modify images, tags, fields, files, or OCR text.</p>
          {/if}
          {#each galleryImages as image}
            <DocumentImageBlock
              {image}
              canEdit={$canEditDocuments}
              canDelete={galleryImages.length > 1}
              on:open={(event) => openImage(event.detail.filename)}
              on:delete={(event) => removeImage(event.detail.filename)}
              on:edit={(event) => openImageEditor(event.detail.filename)}
            />
          {/each}
        </section>
      </main>
    </div>

    {#if $canEditDocuments && tagPickerOpen}
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="tag-picker-backdrop" on:click={() => tagPickerOpen = false}>
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="tag-picker-modal" on:click|stopPropagation>
          <CardTagPicker
            assignedTags={doc.tags ?? []}
            allTags={allTags}
            loading={tagsLoading}
            error={tagsError}
            on:add={handleTagAdded}
            on:remove={handleTagRemoved}
            on:close={() => tagPickerOpen = false}
          />
        </div>
      </div>
    {/if}

    {#if imageViewerOpen}
      <!-- svelte-ignore a11y_click_events_have_key_events -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="lightbox" on:click={() => imageViewerOpen = false}>
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div class="lightbox-inner" on:click|stopPropagation>
          <button class="lightbox-close" on:click={() => imageViewerOpen = false}>✕</button>
          <button class="lightbox-nav left" on:click={showPreviousImage} disabled={galleryImages.length < 2}>‹</button>
          <img src={selectedImageSrc} alt={selectedImage?.filename || ""} />
          <button class="lightbox-nav right" on:click={showNextImage} disabled={galleryImages.length < 2}>›</button>
        </div>
      </div>
    {/if}

    {#if $canEditDocuments && imageEditorOpen && imageBeingEdited}
      <DocumentImageEditorModal
        image={imageBeingEdited}
        saving={imageEditorSaving}
        on:close={() => imageEditorOpen = false}
        on:saveRotate={applyRotate}
        on:saveCrop={applyCrop}
      />
    {/if}
  </div>
{/if}

<style>
  .page { padding: 18px; max-width: 1400px; margin: 0 auto 40px; }
  .page-top-row { display: flex; justify-content: flex-start; margin-bottom: 10px; }
  .doc-breadcrumbs { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 0 0 10px; }
  .crumb { border: 0; background: transparent; padding: 0; text-decoration: underline; color: var(--text-muted); }
  .back-btn { min-height: 36px; padding: 8px 14px; border-radius: 10px; }
  .layout { display: grid; grid-template-columns: 320px minmax(0, 1fr); gap: 16px; align-items: start; }
  .left-column { display: grid; gap: 10px; position: sticky; top: 10px; }
  .images-section { margin-top: 14px; padding: 18px; }
  .hint { color: var(--muted); margin: 0 0 8px; }
  .progress-panel { padding: 10px; }
  .progress-wrap { margin-top: 6px; height: 6px; background: var(--surface); border-radius: 999px; overflow: hidden; }
  .progress { height: 100%; background: #3b82f6; transition: width .2s ease; }
  .success-inline { color: #16a34a; margin: 0; font-size: 0.85rem; }
  .error-inline { color: #ef4444; margin: 0; font-size: 0.85rem; }

  .lightbox {
    position: fixed;
    inset: 0;
    background: rgba(3, 7, 18, 0.72);
    display: grid;
    place-items: center;
    z-index: 1200;
  }
  .lightbox-inner { position: relative; max-width: min(92vw, 1100px); max-height: 90vh; }
  .lightbox-inner img { max-width: 100%; max-height: 90vh; border-radius: 12px; display: block; margin: 0 auto; }
  .lightbox-close { position: fixed; top: 16px; right: 20px; z-index: 1220; }
  .lightbox-nav { position: fixed; top: 50%; transform: translateY(-50%); z-index: 1220; }
  .lightbox-nav.left { left: 16px; }
  .lightbox-nav.right { right: 16px; }

  .tag-picker-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(4, 7, 16, 0.55);
    display: flex;
    justify-content: center;
    align-items: flex-start;
    z-index: 1300;
    padding: 34px 20px 20px;
  }

  .tag-picker-modal {
    width: min(980px, calc(100vw - 40px));
    max-height: min(88vh, 860px);
    overflow: auto;
    background: transparent;
    border: 0;
    border-radius: 0;
    padding: 0;
    display: flex;
    justify-content: center;
  }

  :global(.tag-picker-modal .picker-shell) {
    width: min(940px, calc(100vw - 56px));
    max-height: min(84vh, 820px);
    margin: 0;
    border-radius: 18px;
  }

  @media (max-width: 980px) {
    .layout { grid-template-columns: 1fr; }
    .left-column { position: static; }
    .tag-picker-modal { width: calc(100vw - 20px); }
    :global(.tag-picker-modal .picker-shell) { width: calc(100vw - 24px); }
  }
</style>
