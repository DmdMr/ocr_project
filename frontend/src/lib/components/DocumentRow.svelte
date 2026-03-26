<script lang="ts">
  import { createEventDispatcher, tick } from "svelte"
  import type { CardCustomFieldSetting, Document } from "../types"

  export let doc: Document
  export let selected = false
  export let customFieldSettings: CardCustomFieldSetting[] = []
  export let onSaveFilename: (doc: Document, displayFilename: string) => Promise<Document>
  export let onSaveCustomField: (doc: Document, fieldName: string, value: string) => Promise<Document>
  export let cardImageSrc: (doc: Document) => string

  type DocumentRowEvents = {
    toggleSelect: { id: string }
    openPreview: { id: string }
    updated: { document: Document }
  }

  const dispatch = createEventDispatcher<DocumentRowEvents>()

  let editingFieldKey: string | null = null
  let draftValue = ""
  let skipBlurSave = false
  let savingFieldKey = ""
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

  function fieldType(fieldName: string) {
    return customFieldSettings.find((field) => field.name === fieldName)?.type ?? "text"
  }

  function customFieldValue(fieldName: string) {
    const value = doc.custom_fields?.[fieldName]
    if (value === null || value === undefined || value === "") return "—"
    return String(value)
  }

  function customFieldRawValue(fieldName: string) {
    const value = doc.custom_fields?.[fieldName]
    if (value === null || value === undefined) return ""
    return String(value)
  }

  function getFilenameWithoutExtension(name: string) {
    if (!name) return ""

    const lastDot = name.lastIndexOf(".")
    if (lastDot <= 0) return name

    return name.slice(0, lastDot)
  }

  async function startFilenameEdit(event?: Event) {
    event?.stopPropagation()
    if (editingFieldKey === "filename") return

    if (editingFieldKey) {
      await saveInlineEdit()
    }

    editingFieldKey = "filename"
    draftValue = getFilenameWithoutExtension(doc.display_filename || doc.filename || "")
    skipBlurSave = false
    await tick()
    activeInput?.focus()
    activeInput?.select()
  }

  async function startCustomFieldEdit(fieldName: string, event?: Event) {
    event?.stopPropagation()
    const nextKey = `custom:${fieldName}`
    if (editingFieldKey === nextKey) return

    if (editingFieldKey) {
      await saveInlineEdit()
    }

    editingFieldKey = nextKey
    draftValue = customFieldRawValue(fieldName)
    skipBlurSave = false
    await tick()
    activeInput?.focus()
    activeInput?.select()
  }

  function cancelInlineEdit() {
    skipBlurSave = true
    editingFieldKey = null
    draftValue = ""
  }

  async function saveInlineEdit() {
    if (!editingFieldKey) return

    const targetKey = editingFieldKey
    editingFieldKey = null

    try {
      savingFieldKey = targetKey
      if (targetKey === "filename") {
        const currentValue = getFilenameWithoutExtension(doc.display_filename || doc.filename || "")
        if (draftValue !== currentValue) {
          const updated = await onSaveFilename(doc, draftValue)
          dispatch("updated", { document: updated })
        }
      } else if (targetKey.startsWith("custom:")) {
        const fieldName = targetKey.replace("custom:", "")
        const currentValue = customFieldRawValue(fieldName)
        if (draftValue !== currentValue) {
          const updated = await onSaveCustomField(doc, fieldName, draftValue)
          dispatch("updated", { document: updated })
        }
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Не удалось сохранить значение"
      alert(message)
    } finally {
      draftValue = ""
      savingFieldKey = ""
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

  function isEditingCell(kind: "filename" | "custom", fieldName?: string) {
    if (kind === "filename") return editingFieldKey === "filename"
    return editingFieldKey === `custom:${fieldName ?? ""}`
  }
</script>

<tr class:selected-row={selected}>
  <td class="cell-center">
    <input
      type="checkbox"
      checked={selected}
      on:click|stopPropagation
      on:change={() => dispatch("toggleSelect", { id: doc._id })}
    />
  </td>

  <td>
    <button class="preview-btn" on:click={() => dispatch("openPreview", { id: doc._id })}>
      <img src={cardImageSrc(doc)} alt="" class="row-preview" />
    </button>
  </td>

  <td
    class="editable-cell"
    class:saving={savingFieldKey === "filename"}
    on:click|stopPropagation={startFilenameEdit}
  >
    {#if isEditingCell("filename")}
      <input
        class="inline-input"
        bind:value={draftValue}
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
        on:click|stopPropagation={startFilenameEdit}
      >
        {getFilenameWithoutExtension(doc.display_filename || doc.filename || "")}
      </button>
    {/if}
  </td>

  <td>
    <div class="row-tags">
      {#if doc.tags?.length}
        {#each doc.tags as tag}
          <span class="tag-colored table-tag">{tag}</span>
        {/each}
      {:else}
        <span class="muted">—</span>
      {/if}
    </div>
  </td>

  {#each customFieldSettings as field}
    <td
      class="editable-cell"
      class:saving={savingFieldKey === `custom:${field.name}`}
      title={customFieldValue(field.name)}
      on:click|stopPropagation={(event) => startCustomFieldEdit(field.name, event)}
    >
      {#if isEditingCell("custom", field.name)}
        <input
          class="inline-input"
          type={fieldType(field.name) === "number" ? "number" : "text"}
          bind:value={draftValue}
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
          on:click|stopPropagation={(event) => startCustomFieldEdit(field.name, event)}
        >
          {customFieldValue(field.name)}
        </button>
      {/if}
    </td>
  {/each}
</tr>

<style>
  tr:hover {
    background: color-mix(in srgb, var(--surface), var(--bg-accent) 25%);
  }

  tr.selected-row {
    background: color-mix(in srgb, var(--surface), var(--primary) 10%);
  }

  td {
    border-bottom: 1px solid var(--border);
    padding: 8px 10px;
    vertical-align: middle;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
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
