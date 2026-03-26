<script lang="ts">
  import { createEventDispatcher } from "svelte"
  import type { CardCustomFieldSetting, Document } from "../types"
  import CardPreview from "./CardPreview.svelte"
  import DocumentRow from "./DocumentRow.svelte"
  import {
    deleteDocument,
    updateDocument,
    updateDocumentCustomFields,
    uploadImagesToDocument,
    UPLOADS_URL
  } from "../api"

  export let documents: Document[] = []
  export let selectedIds: string[] = []
  export let customFieldSettings: CardCustomFieldSetting[] = []

  const dispatch = createEventDispatcher<{
    toggleSelect: { id: string }
    deleted: { id: string }
    updated: { document: Document }
  }>()

  let activeDoc: Document | null = null
  let editing = false
  let editedText = ""
  let galleryUploading = false

  function openPreview(doc: Document) {
    activeDoc = doc
    editedText = doc.recognized_text
    editing = false
  }

  function closePreview() {
    activeDoc = null
    editing = false
    galleryUploading = false
  }

  function cardImageSrc(currentDoc: Document) {
    return `${UPLOADS_URL}/${currentDoc.filename}?v=${encodeURIComponent(currentDoc.image_version ?? currentDoc.created_at ?? "")}`
  }

  function applyDocumentUpdate(updated: Document) {
    dispatch("updated", { document: updated })
    if (activeDoc && activeDoc._id === updated._id) {
      activeDoc = updated
      editedText = updated.recognized_text
    }
  }

  function fieldType(fieldName: string) {
    return customFieldSettings.find((field) => field.name === fieldName)?.type ?? "text"
  }

  async function saveInlineFilename(doc: Document, displayFilename: string) {
    const updated = await updateDocument(doc._id, { display_filename: displayFilename })
    applyDocumentUpdate(updated)
    return updated
  }

  async function saveInlineCustomField(doc: Document, fieldName: string, editingValue: string) {
    const type = fieldType(fieldName)

    let nextValue: string | number | null = editingValue
    if (editingValue === "") {
      nextValue = null
    } else if (type === "number") {
      const parsed = Number(editingValue)
      nextValue = Number.isFinite(parsed) ? parsed : null
    }

    const updated = await updateDocumentCustomFields(doc._id, { [fieldName]: nextValue })
    applyDocumentUpdate(updated)
    return updated
  }

  async function savePreviewText() {
    if (!activeDoc) return
    const updated = await updateDocument(activeDoc._id, {
      recognized_text: editedText
    })
    applyDocumentUpdate(updated)
    editing = false
  }

  async function savePreviewFilename(event: CustomEvent<{ display_filename: string }>) {
    if (!activeDoc) return
    const updated = await updateDocument(activeDoc._id, {
      display_filename: event.detail.display_filename
    })
    applyDocumentUpdate(updated)
  }

  async function uploadToCard(event: CustomEvent<{ files: File[] }>) {
    if (!activeDoc) return
    const files = event.detail.files
    if (!files.length) return

    galleryUploading = true
    try {
      const result = await uploadImagesToDocument(activeDoc._id, files)
      if (!result.document) {
        throw new Error("Сервер не вернул обновленные данные карточки")
      }
      applyDocumentUpdate(result.document)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось добавить изображения"
      alert(message)
    } finally {
      galleryUploading = false
    }
  }

  async function removeActiveDoc() {
    if (!activeDoc) return
    const id = activeDoc._id
    await deleteDocument(id)
    dispatch("deleted", { id })
    closePreview()
  }
</script>

<div class="table-shell panel">
  <div class="table-scroll">
    <table class="documents-table">
      <colgroup>
        <col style="width: 44px" />
        <col style="width: 72px" />
        <col style="width: 240px" />
        <col style="width: 200px" />
        {#each customFieldSettings as _}
          <col style="width: 160px" />
        {/each}
      </colgroup>
      <thead>
        <tr>
          <th>✓</th>
          <th>Превью</th>
          <th>Файл</th>
          <th>Теги</th>
          {#each customFieldSettings as field}
            <th>{field.name}</th>
          {/each}
        </tr>
      </thead>
      <tbody>
        {#each documents as doc (doc._id)}
          <DocumentRow
            {doc}
            selected={selectedIds.includes(doc._id)}
            {customFieldSettings}
            onSaveFilename={saveInlineFilename}
            onSaveCustomField={saveInlineCustomField}
            {cardImageSrc}
            on:toggleSelect={(event) => dispatch("toggleSelect", event.detail)}
            on:openPreview={() => openPreview(doc)}
            on:updated={(event) => applyDocumentUpdate(event.detail.document)}
          />
        {/each}
      </tbody>
    </table>
  </div>
</div>

{#if activeDoc}
  <CardPreview
    doc={activeDoc}
    bind:editedText
    {editing}
    on:close={closePreview}
    on:save={savePreviewText}
    on:saveFilename={savePreviewFilename}
    on:delete={removeActiveDoc}
    on:editToggle={() => editing = !editing}
    on:documentUpdated={(event) => applyDocumentUpdate(event.detail.document)}
    on:addImages={uploadToCard}
    {galleryUploading}
  />
{/if}

<style>
  .table-shell {
    padding: 0;
    overflow: hidden;
  }

  .table-scroll {
    overflow-x: auto;
    width: 100%;
  }

  .documents-table {
    width: 100%;
    min-width: 780px;
    border-collapse: collapse;
    table-layout: fixed;
    text-align: left;
  }

  .documents-table th {
    position: sticky;
    top: 0;
    background: var(--surface-elevated);
    z-index: 1;
    font-weight: 700;
    color: var(--text-muted);
  }

</style>
