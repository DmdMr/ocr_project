<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import type { AttachmentFile, CardCustomFieldSetting, Document, GalleryImage } from "./lib/types"
  import {
    deleteDocument,
    deleteDocumentAttachment,
    deleteDocumentImage,
    editDocumentImage,
    createCardField,
    formatSkippedFileError,
    getCardFields,
    getDocumentById,
    getDocumentPath,
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
  import { canEditDocuments, isAdmin } from "./lib/auth"
  import { t } from "./lib/i18n"

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
  let galleryUploadMode: "with_ocr" | "without_ocr" = "with_ocr"

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
  let folderPath: Array<{ id: string; name: string }> = []

  $: galleryImages = (doc?.gallery_images ?? []) as GalleryImage[]
  $: selectedImage = galleryImages[selectedImageIndex] ?? galleryImages[0]
  $: selectedImageSrc = selectedImage ? `${UPLOADS_URL}/${selectedImage.filename}?v=${encodeURIComponent(selectedImage.image_version ?? "")}` : ""

  onMount(async () => {
    await loadDocument()
    await loadTags()
  })

  async function loadDocument() {
    loading = true
    error = ""
    try {
      const [found, fields] = await Promise.all([getDocumentById(params.id) as Promise<Document>, getCardFields()])
      doc = found
      try {
        const pathPayload = await getDocumentPath(found._id)
        folderPath = pathPayload.folder_path ?? []
      } catch {
        folderPath = []
      }
      editedText = found.recognized_text ?? ""
      filenameDraft = found.display_filename ?? found.filename
      customFieldSettings = fields
      syncDraftFromDocument(found)
    } catch (err) {
      error = err instanceof Error ? err.message : $t("document.notFound")
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
    if (!trimmed) return { error: $t("document.filenameRequired"), value: "" }
    const { extension: originalExtension } = splitFilenameParts(originalName)
    if (!originalExtension) return { error: "", value: trimmed }
    const { base, extension } = splitFilenameParts(trimmed)
    const normalizedBase = (extension && extension.toLowerCase() === originalExtension.toLowerCase() ? base : trimmed).trim()
    if (!normalizedBase) return { error: $t("document.filenameRequired"), value: "" }
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

    customFieldsStatus = "saving"
    try {
      const updated = await updateDocumentCustomFields(doc._id, customFieldDraft)
      applyDocumentUpdate(updated)
      changedCustomFields = new Set<string>()
      customFieldsStatus = "saved"
      scheduleSavedStateClear()
    } catch {
      customFieldsStatus = "error"
    }
  }

  async function createDocumentEditorField(payload: { name: string; value: string; type?: "text" | "number" | "people" }) {
    if (!$canEditDocuments || !$isAdmin) {
      throw new Error("Only administrators can create custom fields")
    }
    if (!doc) return

    const requestedName = payload.name.trim()
    const fieldType = payload.type ?? "text"
    if (!requestedName) {
      throw new Error("Field name is required")
    }

    // Field creation reuses the existing settings API used by the table view.
    // The backend registers the field definition and seeds every document with
    // the default value, keeping the current custom_fields database structure.
    const created = await createCardField(requestedName, fieldType)
    const createdField = created.field ?? { name: requestedName.toLowerCase(), type: fieldType }
    const fieldName = createdField.name

    const nextDraft = {
      ...customFieldDraft,
      [fieldName]: normalizeFieldValue(createdField.type, payload.value)
    }

    customFieldSettings = [...customFieldSettings, createdField]
    customFieldDraft = nextDraft
    customFieldsStatus = "saving"

    // Persist the new field's value on the current document immediately after
    // the global field definition exists. Existing document save behavior stays
    // unchanged because updateDocumentCustomFields already handles custom_fields.
    const updated = await updateDocumentCustomFields(doc._id, nextDraft)
    applyDocumentUpdate(updated)
    changedCustomFields = new Set<string>()
    customFieldsStatus = "saved"
    scheduleSavedStateClear()
  }

  async function handleAttachmentUpload(event: CustomEvent<{ files: File[] }>) {
    if (!$canEditDocuments) return
    if (!doc) return
    const files = event.detail.files ?? []
    if (!files.length) return
    attachmentUploadSuccess = ""

    const nonImageFiles = files.filter((file) => !file.type.startsWith("image/"))
    if (!nonImageFiles.length) {
      attachmentUploadError = $t("document.imagesInGalleryHint")
      return
    }

    attachmentsUploading = true
    attachmentUploadProgress = 0
    attachmentUploadError = ""

    try {
      const result = await uploadDocumentAttachments(doc._id, nonImageFiles, (percent) => attachmentUploadProgress = percent)
      if (result.document) applyDocumentUpdate(result.document)
      attachmentUploadSuccess = `${$t("document.attachmentsUploaded")}: ${result.added_count ?? nonImageFiles.length}`
      attachmentUploadError = result.skipped_files?.map(formatSkippedFileError).join("; ") ?? ""
    } catch (err) {
      attachmentUploadError = err instanceof Error ? err.message : $t("document.attachmentError")
    } finally {
      attachmentsUploading = false
    }
  }

  async function handleGalleryUpload(event: CustomEvent<{ files: File[]; performOcr?: boolean }>) {
    if (!$canEditDocuments) return
    if (!doc) return
    const files = event.detail.files ?? []
    if (!files.length) return
    const performOcr = event.detail.performOcr ?? true
    galleryUploadMode = performOcr ? "with_ocr" : "without_ocr"
    galleryUploadSuccess = ""
    galleryUploading = true
    galleryUploadProgress = 0
    galleryUploadError = ""

    try {
      // Reuse the same gallery upload endpoint; perform_ocr=false stores images
      // with empty OCR-compatible fields and leaves existing recognized text unchanged.
      const result = await uploadImagesToDocument(doc._id, files, (percent) => galleryUploadProgress = percent, performOcr)
      if (result.document) applyDocumentUpdate(result.document)
      const message = performOcr ? $t("document.uploadedWithRecognition") : $t("document.uploadedWithoutRecognition")
      galleryUploadSuccess = `${message}: ${result.added_count ?? files.length}`
      galleryUploadError = result.skipped_files?.map(formatSkippedFileError).join("; ") ?? ""
    } catch (err) {
      galleryUploadError = err instanceof Error ? err.message : $t("document.uploadError")
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
    if (!confirm($t("document.deleteImageConfirm"))) return
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

  function openFilesLocation(folderId?: string) {
    const query = folderId ? `?view=files&folder=${encodeURIComponent(folderId)}` : "?view=files"
    push(`/${query}`)
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
      tagsError = err instanceof Error ? err.message : $t("tags.loadFailed")
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
    if (!confirm($t("document.deleteConfirm"))) return
    await deleteDocument(doc._id)
    push("/")
  }

  function applyDocumentUpdate(updated: Document) {
    doc = updated
    editedText = updated.recognized_text ?? ""
    filenameDraft = updated.display_filename ?? updated.filename
    syncDraftFromDocument(updated)
  }

  function goBack() {
    if (window.history.length > 1) {
      window.history.back()
      return
    }
    push("/")
  }
</script>

{#if loading}
  <div class="page"><p>{$t("document.loading")}</p></div>
{:else if error || !doc}
  <div class="page"><p>{error || $t("document.notFound")}</p></div>
{:else}
  <div class="page document-editor-page">
    <header class="workspace-header panel">
      <button class="back-btn" on:click={goBack}>← {$t("common.back")}</button>
      <div class="header-center">
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
        <div class="header-meta-line">
          <span><strong>{$t("common.created")}:</strong> {new Date(doc.created_at).toLocaleString()}</span>
          <span><strong>{$t("common.updated")}:</strong> {new Date((doc as any).updated_at || doc.created_at).toLocaleString()}</span>
        </div>
      </div>
      <div class="header-actions">
        <button class="back-btn" on:click={() => filenameEditing = true} disabled={!$canEditDocuments}>{$t("common.edit")}</button>
        <button class="back-btn" on:click={removeDocumentNow} disabled={!$canEditDocuments}>{$t("common.delete")}</button>
      </div>
    </header>

    <section class="editor-layout">
      <aside class="editor-sidebar">
        <section class="panel folder-path-panel">
          <strong>{$t("document.location")}</strong>
          <div class="path-items">
            <button class="path-link" on:click={() => openFilesLocation()}>{$t("common.root")}</button>
            <span>/</span>
            {#if folderPath.length}
              {#each folderPath as item (item.id)}
                <button class="path-link" on:click={() => openFilesLocation(item.id)}>{item.name}</button>
                <span>/</span>
              {/each}
            {:else}
              <span>{$t("common.unsorted")}</span>
              <span>/</span>
            {/if}
            <span>{doc.display_filename || doc.filename}</span>
          </div>
          <div class="gallery-upload-actions">
            <button class="back-btn" on:click={() => document.getElementById('gallery-upload-with-ocr')?.click()} disabled={!$canEditDocuments || galleryUploading}>{$t("upload.withRecognition")}</button>
            <button class="back-btn" on:click={() => document.getElementById('gallery-upload-without-ocr')?.click()} disabled={!$canEditDocuments || galleryUploading}>{$t("upload.withoutRecognition")}</button>
          </div>
        </section>

        <DocumentMetadataSection
          {doc}
          canEdit={$canEditDocuments}
          {customFieldSettings}
          {customFieldDraft}
          {customFieldsStatus}
          canCreateFields={$isAdmin}
          onCreateCustomField={createDocumentEditorField}
          on:customFieldInput={(event) => onCustomFieldInput(event.detail.fieldName, event.detail.value, event.detail.saveNow ?? false)}
          on:manageTags={() => tagPickerOpen = true}
          on:deleteDoc={removeDocumentNow}
          on:addImages={(event) => handleGalleryUpload({ detail: { files: event.detail.files, performOcr: true } } as CustomEvent<{ files: File[]; performOcr?: boolean }>)}
        />
        <div class="visually-hidden-upload">
          <input id="gallery-upload-with-ocr" type="file" accept="image/*" multiple on:change={(event) => { handleGalleryUpload({ detail: { files: Array.from((event.currentTarget as HTMLInputElement).files ?? []), performOcr: true } } as CustomEvent<{ files: File[]; performOcr?: boolean }>); (event.currentTarget as HTMLInputElement).value = "" }} />
          <input id="gallery-upload-without-ocr" type="file" accept="image/*" multiple on:change={(event) => { handleGalleryUpload({ detail: { files: Array.from((event.currentTarget as HTMLInputElement).files ?? []), performOcr: false } } as CustomEvent<{ files: File[]; performOcr?: boolean }>); (event.currentTarget as HTMLInputElement).value = "" }} />
        </div>

        <section class="panel files-panel">
          <h3>{$t("document.files")}</h3>
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
          <button class="back-btn" on:click={() => document.getElementById('file-upload')?.click()} disabled={!$canEditDocuments}>{$t("document.addFile")}</button>
          <div class="visually-hidden-upload">
            <input id="file-upload" type="file" multiple on:change={(event) => handleAttachmentUpload({ detail: { files: Array.from((event.currentTarget as HTMLInputElement).files ?? []) } } as CustomEvent<{ files: File[] }>)} />
          </div>
        </section>

        {#if galleryUploading}
          <div class="panel progress-panel">
            <p>{galleryUploadMode === "with_ocr" ? $t("document.uploadingWithRecognition") : $t("document.uploadingWithoutRecognition")}... {galleryUploadProgress}%</p>
            <div class="progress-wrap"><div class="progress" style={`width:${galleryUploadProgress}%`}></div></div>
          </div>
        {/if}
        {#if galleryUploadSuccess}
          <p class="success-inline">{galleryUploadSuccess}</p>
        {/if}
        {#if galleryUploadError}
          <p class="error-inline">{galleryUploadError}</p>
        {/if}
      </aside>

      <main class="editor-content">
        <section class="working-block">
          {#if !$canEditDocuments}
            <p class="hint">{$t("document.readOnlyHint")}</p>
          {/if}
          <div class="document-blocks">
            <!-- Document editor reading order: metadata fields stay in the sidebar,
              then OCR text is shown before gallery images so users can read notes
              without scrolling past large uploads first. -->
            <section class="ocr-card">
              <DocumentContentEditor
                bind:value={editedText}
                canEdit={$canEditDocuments}
                {editing}
                onToggleEdit={() => editing = !editing}
                onSave={saveText}
              />
            </section>

            <section class="gallery-section" aria-label={$t("metadata.images")}>
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
          </div>
        </section>
      </main>
    </section>

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
  .page {
    --editor-page-padding: 16px;
    --editor-gap-sm: 12px;
    --editor-gap-md: 16px;
    --editor-panel-padding: 16px;
    --editor-radius: 12px;

    padding: var(--editor-page-padding);
    max-width: 1400px;
    margin: 0 auto 40px;
  }

  :global(.document-editor-page .panel) { border-radius: var(--editor-radius); }
  :global(.document-editor-page label.upload-btn) {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 36px;
    padding: 8px 12px;
    border-radius: var(--editor-radius);
    border: 1px solid var(--border);
    background: var(--surface-strong);
    cursor: pointer;
    font-weight: 600;
  }

  .workspace-header { display: grid; grid-template-columns: auto minmax(0, 1fr) auto; gap: var(--editor-gap-md); align-items: center; margin-bottom: var(--editor-gap-md); padding: var(--editor-panel-padding); box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05); }
  .header-center { min-width: 0; display: grid; gap: var(--editor-gap-sm); }
  .header-meta-line { display: flex; flex-wrap: wrap; gap: var(--editor-gap-sm) var(--editor-gap-md); color: var(--muted); font-size: 0.9rem; }
  .header-actions { display: flex; gap: var(--editor-gap-sm); }
  .back-btn { min-height: 36px; padding: 8px 14px; border-radius: var(--editor-radius); }
  .editor-layout { display: grid; grid-template-columns: minmax(280px, 320px) minmax(0, 1fr); gap: var(--editor-gap-md); align-items: start; }
  .editor-sidebar { display: flex; flex-direction: column; gap: var(--editor-gap-sm); }
  .editor-content { display: flex; flex-direction: column; gap: var(--editor-gap-md); }
  .document-blocks, .gallery-section { display: grid; gap: var(--editor-gap-md); }
  .folder-path-panel { padding: var(--editor-panel-padding); display: grid; gap: var(--editor-gap-sm); box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05); }
  .path-items { display: flex; gap: var(--editor-gap-sm); flex-wrap: wrap; align-items: center; }
  .path-link { background: none; border: 0; padding: 0; text-decoration: underline; cursor: pointer; color: var(--text); }
  .gallery-upload-actions { display: grid; gap: var(--editor-gap-sm); }
  .files-panel { display: grid; gap: var(--editor-gap-sm); padding: var(--editor-panel-padding); box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05); }
  .files-panel h3 { margin: 0; }
  .visually-hidden-upload { display: none; }
  .hint { color: var(--muted); margin: 0 0 8px; }
  .progress-panel { padding: var(--editor-panel-padding); }
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
    padding: var(--editor-panel-padding);
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
    .workspace-header,
    .editor-layout { grid-template-columns: 1fr; }
    .tag-picker-modal { width: calc(100vw - 32px); }
    :global(.tag-picker-modal .picker-shell) { width: calc(100vw - 24px); }
  }
</style>
