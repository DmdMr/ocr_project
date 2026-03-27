<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte"
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
  type TextFilter = {
    mode: "text"
    selectedValues: string[]
    sort: "none" | "asc" | "desc"
  }

  type NumberFilter = {
    mode: "number"
    sort: "none" | "asc" | "desc"
    operator: "none" | "equals" | "greater_than" | "less_than" | "between"
    value1: string
    value2: string
  }

  type CustomFieldFilter = TextFilter | NumberFilter
  export let customFieldFilters: Record<string, CustomFieldFilter> = {}
  export let openFilterField: string | null = null
  export let fieldUniqueTextValues: (fieldName: string) => string[] = () => []
  export let isFieldFilterActive: (fieldName: string) => boolean = () => false

  const dispatch = createEventDispatcher<{
    toggleSelect: { id: string }
    deleted: { id: string }
    updated: { document: Document }
    toggleFilterPanel: { fieldName: string }
    setTextSort: { fieldName: string; sort: "none" | "asc" | "desc" }
    setNumberSort: { fieldName: string; sort: "none" | "asc" | "desc" }
    toggleTextValue: { fieldName: string; value: string }
    selectAllTextValues: { fieldName: string }
    clearTextValues: { fieldName: string }
    setNumberOperator: { fieldName: string; operator: NumberFilter["operator"] }
    setNumberValue: { fieldName: string; key: "value1" | "value2"; value: string }
    clearFieldFilter: { fieldName: string }
    closeFilterPanel: void
  }>()

  let activeDoc: Document | null = null
  let editing = false
  let editedText = ""
  let galleryUploading = false
  let tableShellElement: HTMLDivElement | null = null

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

  function handleOutsideClick(event: MouseEvent) {
    if (!openFilterField || !tableShellElement) return
    const target = event.target as Node
    if (!tableShellElement.contains(target)) {
      dispatch("closeFilterPanel")
    }
  }

  onMount(() => {
    document.addEventListener("mousedown", handleOutsideClick)
    return () => document.removeEventListener("mousedown", handleOutsideClick)
  })
</script>

<div class="table-shell panel" bind:this={tableShellElement}>
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
            <th class="field-header-cell">
              <button
                class="field-header-trigger"
                class:active={isFieldFilterActive(field.name)}
                on:click={() => dispatch("toggleFilterPanel", { fieldName: field.name })}
              >
                <span>{field.name}</span>
                <span class="filter-icon">▾</span>
              </button>

              {#if openFilterField === field.name}
                <div class="field-filter-popup">
                  {#if customFieldFilters[field.name]?.mode === "text"}
                    <div class="popup-row">
                      <button class="secondary" on:click={() => dispatch("setTextSort", { fieldName: field.name, sort: "asc" })}>A-Z</button>
                      <button class="secondary" on:click={() => dispatch("setTextSort", { fieldName: field.name, sort: "desc" })}>Z-A</button>
                      <button class="secondary" on:click={() => dispatch("setTextSort", { fieldName: field.name, sort: "none" })}>Без сорт.</button>
                    </div>
                    <div class="popup-row">
                      <button class="secondary" on:click={() => dispatch("selectAllTextValues", { fieldName: field.name })}>Выбрать все</button>
                      <button class="secondary" on:click={() => dispatch("clearTextValues", { fieldName: field.name })}>Очистить</button>
                    </div>
                    <div class="popup-values">
                      {#each fieldUniqueTextValues(field.name) as value}
                        <label class="popup-checkbox">
                          <input
                            type="checkbox"
                            checked={customFieldFilters[field.name]?.mode === "text" && customFieldFilters[field.name].selectedValues.includes(value)}
                            on:change={() => dispatch("toggleTextValue", { fieldName: field.name, value })}
                          />
                          <span>{value}</span>
                        </label>
                      {/each}
                    </div>
                  {:else}
                    <div class="popup-row">
                      <button class="secondary" on:click={() => dispatch("setNumberSort", { fieldName: field.name, sort: "asc" })}>0-9</button>
                      <button class="secondary" on:click={() => dispatch("setNumberSort", { fieldName: field.name, sort: "desc" })}>9-0</button>
                      <button class="secondary" on:click={() => dispatch("setNumberSort", { fieldName: field.name, sort: "none" })}>Без сорт.</button>
                    </div>
                    <div class="popup-row">
                      <select
                        value={customFieldFilters[field.name]?.mode === "number" ? customFieldFilters[field.name].operator : "none"}
                        on:change={(event) => {
                          const target = event.target as HTMLSelectElement
                          dispatch("setNumberOperator", { fieldName: field.name, operator: target.value as NumberFilter["operator"] })
                        }}
                      >
                        <option value="none">Без фильтра</option>
                        <option value="equals">Равно</option>
                        <option value="greater_than">Больше</option>
                        <option value="less_than">Меньше</option>
                        <option value="between">Между</option>
                      </select>
                    </div>
                    <div class="popup-row number-inputs">
                      <input
                        type="number"
                        placeholder="Значение"
                        value={customFieldFilters[field.name]?.mode === "number" ? customFieldFilters[field.name].value1 : ""}
                        on:input={(event) => {
                          const target = event.target as HTMLInputElement
                          dispatch("setNumberValue", { fieldName: field.name, key: "value1", value: target.value })
                        }}
                      />
                      {#if customFieldFilters[field.name]?.mode === "number" && customFieldFilters[field.name].operator === "between"}
                        <input
                          type="number"
                          placeholder="И до"
                          value={customFieldFilters[field.name]?.mode === "number" ? customFieldFilters[field.name].value2 : ""}
                          on:input={(event) => {
                            const target = event.target as HTMLInputElement
                            dispatch("setNumberValue", { fieldName: field.name, key: "value2", value: target.value })
                          }}
                        />
                      {/if}
                    </div>
                  {/if}
                  <div class="popup-row">
                    <button class="secondary" on:click={() => dispatch("clearFieldFilter", { fieldName: field.name })}>Сбросить</button>
                    <button class="primary" on:click={() => dispatch("closeFilterPanel")}>Готово</button>
                  </div>
                </div>
              {/if}
            </th>
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

  .field-header-cell {
    position: sticky;
    overflow: visible;
  }

  .field-header-trigger {
    all: unset;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    color: inherit;
    font-weight: 700;
  }

  .field-header-trigger:hover {
    color: var(--text);
  }

  .field-header-trigger.active {
    color: var(--primary);
  }

  .filter-icon {
    font-size: 0.72rem;
    color: var(--text-muted);
  }

  .field-header-trigger.active .filter-icon {
    color: var(--primary);
  }

  .field-filter-popup {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    z-index: 25;
    min-width: 250px;
    max-width: min(86vw, 320px);
    padding: 10px;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--surface-elevated);
    box-shadow: var(--shadow-soft);
    display: grid;
    gap: 8px;
  }

  .popup-row {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }

  .popup-values {
    display: grid;
    gap: 4px;
    max-height: 170px;
    overflow: auto;
    padding-right: 2px;
  }

  .popup-checkbox {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.86rem;
    font-weight: 500;
    color: var(--text);
  }

  .number-inputs input {
    width: 100%;
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
