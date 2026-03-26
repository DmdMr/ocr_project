<script lang="ts">
  import { createEventDispatcher, tick } from "svelte"
  import type { CardCustomFieldSetting, Document } from "../types"
  import CardPreview from "./CardPreview.svelte"
  import { tagHue } from "../tagColors"
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
  let editingCell: { docId: string; kind: "filename" | "custom"; fieldName?: string } | null = null
  let editingValue = ""
  let savingCellKey = ""
  let skipBlurSave = false
  let activeInput: HTMLInputElement | null = null

  function focusAndSelect(node: HTMLInputElement) {
    requestAnimationFrame(() => {
      node.focus()
      node.select()
    })
    return {
      destroy() {
        if (activeInput === node) {
          activeInput = null
        }
      }
    }
  }

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

  function customFieldRawValue(doc: Document, fieldName: string) {
    const value = doc.custom_fields?.[fieldName]
    if (value === null || value === undefined) return ""
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

  function isEditingCell(docId: string, kind: "filename" | "custom", fieldName?: string) {
    if (!editingCell) return false
    if (editingCell.docId !== docId || editingCell.kind !== kind) return false
    if (kind === "custom") return editingCell.fieldName === fieldName
    return true
  }

  async function startFilenameEdit(doc: Document) {
    if (isEditingCell(doc._id, "filename")) return
    if (editingCell) {
      await saveInlineEdit()
    }
    editingCell = { docId: doc._id, kind: "filename" }
    editingValue = getFilenameWithoutExtension(doc.display_filename || doc.filename || "")
    skipBlurSave = false
    await tick()
    activeInput?.focus()
    activeInput?.select()
  }

  async function startCustomFieldEdit(doc: Document, fieldName: string) {
    if (isEditingCell(doc._id, "custom", fieldName)) return
    if (editingCell) {
      await saveInlineEdit()
    }
    editingCell = { docId: doc._id, kind: "custom", fieldName }
    editingValue = customFieldRawValue(doc, fieldName)
    skipBlurSave = false
    await tick()
    activeInput?.focus()
    activeInput?.select()
  }

  function cancelInlineEdit() {
    skipBlurSave = true
    editingCell = null
    editingValue = ""
  }

  function fieldType(fieldName: string) {
    return customFieldSettings.find((field) => field.name === fieldName)?.type ?? "text"
  }

  async function saveInlineEdit() {
    if (!editingCell) return
    const targetCell = editingCell
    const currentDoc = documents.find((item) => item._id === targetCell.docId)
    editingCell = null
    if (!currentDoc) return

    try {
      savingCellKey = targetCell.kind === "filename"
        ? `${targetCell.docId}:filename`
        : `${targetCell.docId}:custom:${targetCell.fieldName ?? ""}`
      if (targetCell.kind === "filename") {
        const currentValue = getFilenameWithoutExtension(currentDoc.display_filename || currentDoc.filename || "")
        if (editingValue === currentValue) return
        const updated = await updateDocument(currentDoc._id, { display_filename: editingValue })
        applyDocumentUpdate(updated)
        return
      }

      const fieldName = targetCell.fieldName ?? ""
      if (!fieldName) return
      const type = fieldType(fieldName)
      const previousRaw = customFieldRawValue(currentDoc, fieldName)
      if (editingValue === previousRaw) return

      let nextValue: string | number | null = editingValue
      if (editingValue === "") {
        nextValue = null
      } else if (type === "number") {
        const parsed = Number(editingValue)
        nextValue = Number.isFinite(parsed) ? parsed : null
      }

      const updated = await updateDocumentCustomFields(currentDoc._id, { [fieldName]: nextValue })
      applyDocumentUpdate(updated)
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось сохранить значение"
      alert(message)
    } finally {
      editingValue = ""
      savingCellKey = ""
    }
  }

  async function handleInlineBlur() {
    if (skipBlurSave) {
      skipBlurSave = false
      return
    }
    await saveInlineEdit()
  }

  async function handleInlineKeydown(event: KeyboardEvent) {
    if (event.key === "Enter") {
      event.preventDefault()
      await saveInlineEdit()
      return
    }

    if (event.key === "Escape") {
      event.preventDefault()
      cancelInlineEdit()
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
            <td
              class="editable-cell"
              class:saving={savingCellKey === `${doc._id}:filename`}
              on:click|stopPropagation={() => startFilenameEdit(doc)}
            >
              {#if isEditingCell(doc._id, "filename")}
                <input
                  class="inline-input"
                  bind:value={editingValue}
                  bind:this={activeInput}
                  use:focusAndSelect
                  on:click|stopPropagation
                  on:keydown={handleInlineKeydown}
                  on:blur={handleInlineBlur}
                />
              {:else}
                <button
                  type="button"
                  class="filename-btn"
                  title={doc.display_filename || doc.filename}
                  on:click|stopPropagation={() => startFilenameEdit(doc)}
                >
                  {getFilenameWithoutExtension(doc.display_filename || doc.filename || "")}
                </button>
              {/if}
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
              <td
                class="editable-cell"
                class:saving={savingCellKey === `${doc._id}:custom:${field.name}`}
                title={customFieldValue(doc, field.name)}
                on:click|stopPropagation={() => startCustomFieldEdit(doc, field.name)}
              >
                {#if isEditingCell(doc._id, "custom", field.name)}
                  <input
                    class="inline-input"
                    type={field.type === "number" ? "number" : "text"}
                    bind:value={editingValue}
                    bind:this={activeInput}
                    use:focusAndSelect
                    on:click|stopPropagation
                    on:keydown={handleInlineKeydown}
                    on:blur={handleInlineBlur}
                  />
                {:else}
                  <button
                    type="button"
                    class="cell-value-btn"
                    on:click|stopPropagation={() => startCustomFieldEdit(doc, field.name)}
                  >
                    {customFieldValue(doc, field.name)}
                  </button>
                {/if}
              </td>
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
  .filename-btn,
  .cell-value-btn {
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
    width: 100%;
    text-align: left;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .filename-btn:hover {
    text-decoration: underline;
  }

  .editable-cell {
    position: relative;
    cursor: text;
  }

  .editable-cell.saving::after {
    content: "";
    position: absolute;
    right: 6px;
    top: 50%;
    width: 6px;
    height: 6px;
    transform: translateY(-50%);
    border-radius: 999px;
    background: var(--primary);
    opacity: 0.7;
  }

  .cell-value-btn {
    width: 100%;
    text-align: left;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .inline-input {
    display: block;
    width: 100%;
    min-width: 0;
    box-sizing: border-box;
    background: var(--surface);
    border: 1px solid var(--border-strong);
    border-radius: 8px;
    color: var(--text);
    padding: 6px 8px;
    font: inherit;
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
