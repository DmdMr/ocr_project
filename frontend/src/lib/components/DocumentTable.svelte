<script lang="ts">
  import { createEventDispatcher } from "svelte"
  import type { CardCustomFieldSetting, Document } from "../types"
  import CardPreview from "./CardPreview.svelte"
  import { tagHue } from "../tagColors"
  import {
    deleteDocument,
    updateDocument,
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

  function customFieldValue(doc: Document, fieldName: string) {
    const value = doc.custom_fields?.[fieldName]
    if (value === null || value === undefined || value === "") return "—"
    return String(value)
  }

  function tagList(doc: Document) {
    return doc.tags ?? []
  }

  function getFilenameWithoutExtension(name: string) {
    if (!name) return ""
    const lastDot = name.lastIndexOf(".")
    if (lastDot <= 0) return name
    return name.slice(0, lastDot)
  }

  function applyDocumentUpdate(updated: Document) {
    dispatch("updated", { document: updated })
    if (activeDoc && activeDoc._id === updated._id) {
      activeDoc = updated
      editedText = updated.recognized_text
    }
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
          <tr class:selected-row={selectedIds.includes(doc._id)}>
            <td class="cell-center">
              <input
                type="checkbox"
                checked={selectedIds.includes(doc._id)}
                on:change={() => dispatch("toggleSelect", { id: doc._id })}
              />
            </td>
            <td>
              <button class="preview-btn" on:click={() => openPreview(doc)}>
                <img src={cardImageSrc(doc)} alt="" class="row-preview" />
              </button>
            </td>
            <td>
              <button class="filename-btn" on:click={() => openPreview(doc)} title={doc.display_filename || doc.filename}>
                {getFilenameWithoutExtension(doc.display_filename || doc.filename || "")}
              </button>
            </td>
            <td>
              <div class="row-tags">
                {#if tagList(doc).length}
                  {#each tagList(doc) as tag}
                    <span class="tag-colored table-tag" style={`--tag-hue: ${tagHue(tag)}`}>{tag}</span>
                  {/each}
                {:else}
                  <span class="muted">—</span>
                {/if}
              </div>
            </td>
            {#each customFieldSettings as field}
              <td title={customFieldValue(doc, field.name)}>{customFieldValue(doc, field.name)}</td>
            {/each}
          </tr>
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

  .documents-table th,
  .documents-table td {
    border-bottom: 1px solid var(--border);
    padding: 8px 10px;
    vertical-align: middle;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .documents-table th {
    position: sticky;
    top: 0;
    background: var(--surface-elevated);
    z-index: 1;
    font-weight: 700;
    color: var(--text-muted);
  }

  .documents-table tbody tr:hover {
    background: color-mix(in srgb, var(--surface), var(--bg-accent) 25%);
  }

  .documents-table tbody tr.selected-row {
    background: color-mix(in srgb, var(--surface), var(--primary) 10%);
  }

  .cell-center {
    text-align: center;
  }

  .preview-btn,
  .filename-btn {
    all: unset;
    cursor: pointer;
    display: inline-block;
    max-width: 100%;
  }

  .row-preview {
    width: 52px;
    height: 52px;
    border-radius: 8px;
    object-fit: cover;
    border: 1px solid var(--border);
    display: block;
  }

  .filename-btn {
    font-weight: 600;
    color: var(--text);
  }

  .filename-btn:hover {
    text-decoration: underline;
  }

  .row-tags {
    display: flex;
    gap: 4px;
    flex-wrap: nowrap;
    overflow: hidden;
  }

  .table-tag {
    display: inline-flex;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.78rem;
    max-width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .muted {
    color: var(--text-muted);
  }
</style>
