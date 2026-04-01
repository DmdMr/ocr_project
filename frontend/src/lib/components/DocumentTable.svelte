<script lang="ts">
  import { createEventDispatcher, onMount, tick } from "svelte"
  import { push } from "svelte-spa-router"
  import type { CardCustomFieldSetting, Document } from "../types"
  import CardPreview from "./CardPreview.svelte"
  import { tagHue } from "../tagColors"
  import { documentRoute } from "../documentRoutes"
  import {
    deleteDocument,
    updateDocument,
    uploadImagesToDocument,
    UPLOADS_URL
  } from "../api"

  export let documents: Document[] = []
  export let openInPageMode = true
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

  type SortDirection = "none" | "asc" | "desc"
  type CreatedAtSort = "none" | "newest" | "oldest"
  type CreatedAtRange = "all" | "today" | "last_7_days" | "this_month"

  type TableColumnKind = "select" | "preview" | "filename" | "created_at" | "tags" | "custom"

  type TableColumnDef = {
    id: string
    kind: TableColumnKind
    label: string
    isSystem: boolean
    movable: boolean
    resizable: boolean
    deletable: boolean
    minWidth: number
    defaultWidth: number
    fieldName?: string
    filterFieldName?: string
  }

  export let customFieldFilters: Record<string, CustomFieldFilter> = {}
  export let openFilterField: string | null = null
  export let fieldUniqueTextValues: (fieldName: string) => string[] = () => []
  export let isFieldFilterActive: (fieldName: string) => boolean = () => false
  export let filenameFilterText = ""
  export let filenameSort: SortDirection = "none"
  export let createdAtSort: CreatedAtSort = "none"
  export let createdAtRange: CreatedAtRange = "all"
  export let isFilenameFilterActive: () => boolean = () => false
  export let isCreatedAtFilterActive: () => boolean = () => false

  const dispatch = createEventDispatcher<{
    toggleSelect: { id: string }
    deleted: { id: string }
    updated: { document: Document }
    addProperty: void
    deleteProperty: { fieldName: string }
    toggleFilterPanel: { fieldName: string }
    setTextSort: { fieldName: string; sort: SortDirection }
    setNumberSort: { fieldName: string; sort: SortDirection }
    toggleTextValue: { fieldName: string; value: string }
    selectAllTextValues: { fieldName: string }
    clearTextValues: { fieldName: string }
    setNumberOperator: { fieldName: string; operator: NumberFilter["operator"] }
    setNumberValue: { fieldName: string; key: "value1" | "value2"; value: string }
    clearFieldFilter: { fieldName: string }
    setFilenameFilterText: { value: string }
    setFilenameSort: { sort: SortDirection }
    clearFilenameFilter: void
    setCreatedAtSort: { sort: CreatedAtSort }
    setCreatedAtRange: { range: CreatedAtRange }
    clearCreatedAtFilter: void
    closeFilterPanel: void
  }>()

  const columnPreferencesStorageKey = "documentTableColumnPreferences:v2"

  const systemColumns: TableColumnDef[] = [
    { id: "select", kind: "select", label: "✓", isSystem: true, movable: false, resizable: false, deletable: false, minWidth: 44, defaultWidth: 44 },
    { id: "preview", kind: "preview", label: "Превью", isSystem: true, movable: false, resizable: true, deletable: false, minWidth: 72, defaultWidth: 72 },
    { id: "filename", kind: "filename", label: "Файл", isSystem: true, movable: false, resizable: true, deletable: false, minWidth: 220, defaultWidth: 250, filterFieldName: "system:filename" },
    { id: "created_at", kind: "created_at", label: "Создан", isSystem: true, movable: false, resizable: true, deletable: false, minWidth: 150, defaultWidth: 180, filterFieldName: "system:created_at" },
    { id: "tags", kind: "tags", label: "Теги", isSystem: true, movable: false, resizable: true, deletable: false, minWidth: 160, defaultWidth: 200 }
  ]

  let activeDoc: Document | null = null
  let editing = false
  let editedText = ""
  let galleryUploading = false
  let tableShellElement: HTMLDivElement | null = null
  let tableTopScrollElement: HTMLDivElement | null = null
  let tableTopScrollContentElement: HTMLDivElement | null = null
  let tableScrollElement: HTMLDivElement | null = null
  let overlayPopupElement: HTMLDivElement | null = null

  let columnWidths: Record<string, number> = {}
  let customFieldOrder: string[] = []
  let orderedCustomColumns: TableColumnDef[] = []
  let visibleColumns: TableColumnDef[] = []

  let dragFieldName: string | null = null
  let dragOverFieldName: string | null = null
  let dragOverPosition: "before" | "after" = "after"

  let cleanupResizeListeners: (() => void) | null = null
  let filterTriggerElements: Record<string, HTMLElement | undefined> = {}
  let popupPosition = { top: 0, left: 0 }
  let syncingHorizontalScroll = false
  let hasHorizontalOverflow = false
  const handleTopHorizontalScroll = () => syncHorizontalScroll("top")
  const handleBottomHorizontalScroll = () => syncHorizontalScroll("bottom")

  function widthColumnIdForField(fieldName: string) {
    return `custom:${fieldName}`
  }

  function customColumnFromField(field: CardCustomFieldSetting): TableColumnDef {
    return {
      id: widthColumnIdForField(field.name),
      kind: "custom",
      label: field.name,
      isSystem: false,
      movable: true,
      resizable: true,
      deletable: true,
      minWidth: 140,
      defaultWidth: 160,
      fieldName: field.name,
      filterFieldName: field.name
    }
  }

  function getColumnWidth(column: TableColumnDef) {
    const current = columnWidths[column.id]
    return Math.max(column.minWidth, current ?? column.defaultWidth)
  }

  function persistColumnPreferences() {
    if (typeof window === "undefined") return
    window.localStorage.setItem(
      columnPreferencesStorageKey,
      JSON.stringify({ widths: columnWidths, customFieldOrder })
    )
  }

  function initializeColumnState() {
    const fieldNames = customFieldSettings.map(field => field.name)

    const allowedColumnIds = new Set<string>([
      ...systemColumns.map(column => column.id),
      ...fieldNames.map(name => widthColumnIdForField(name))
    ])

    const nextWidths: Record<string, number> = {}
    for (const column of systemColumns) {
      const width = columnWidths[column.id]
      nextWidths[column.id] = Math.max(column.minWidth, width ?? column.defaultWidth)
    }

    for (const fieldName of fieldNames) {
      const id = widthColumnIdForField(fieldName)
      const width = columnWidths[id]
      nextWidths[id] = Math.max(140, width ?? 160)
    }

    if (Object.keys(columnWidths).some(id => !allowedColumnIds.has(id))) {
      columnWidths = nextWidths
      persistColumnPreferences()
      return
    }

    const widthKeysChanged = Object.keys(nextWidths).some(id => nextWidths[id] !== columnWidths[id])
    if (widthKeysChanged || Object.keys(nextWidths).length !== Object.keys(columnWidths).length) {
      columnWidths = nextWidths
    }
  }

  function customFieldByName(fieldName: string) {
    return customFieldSettings.find(field => field.name === fieldName)
  }

  function arraysEqual(left: string[], right: string[]) {
    if (left.length !== right.length) return false
    return left.every((value, index) => value === right[index])
  }

  function moveCustomField(sourceName: string, targetName: string, position: "before" | "after") {
    if (sourceName === targetName) return

    const current = [...customFieldOrder]
    const sourceIndex = current.indexOf(sourceName)
    const targetIndex = current.indexOf(targetName)
    if (sourceIndex < 0 || targetIndex < 0) return

    current.splice(sourceIndex, 1)
    const adjustedTargetIndex = sourceIndex < targetIndex ? targetIndex - 1 : targetIndex
    const insertIndex = position === "before" ? adjustedTargetIndex : adjustedTargetIndex + 1
    current.splice(insertIndex, 0, sourceName)

    customFieldOrder = current
    persistColumnPreferences()
  }

  function registerFilterTrigger(node: HTMLElement, fieldName: string) {
    filterTriggerElements = { ...filterTriggerElements, [fieldName]: node }
    return {
      destroy() {
        const next = { ...filterTriggerElements }
        delete next[fieldName]
        filterTriggerElements = next
      }
    }
  }

  function updatePopupPosition() {
    if (!openFilterField) return
    const anchor = filterTriggerElements[openFilterField]
    if (!anchor) return

    const rect = anchor.getBoundingClientRect()
    const maxLeft = Math.max(8, window.innerWidth - 340)
    popupPosition = {
      top: rect.bottom + 6,
      left: Math.max(8, Math.min(rect.left, maxLeft))
    }
  }

  function startResize(event: PointerEvent, column: TableColumnDef) {
    event.preventDefault()
    event.stopPropagation()

    if (cleanupResizeListeners) {
      cleanupResizeListeners()
      cleanupResizeListeners = null
    }

    const handle = event.currentTarget as HTMLElement | null
    const startX = event.clientX
    const startWidth = getColumnWidth(column)

    handle?.setPointerCapture?.(event.pointerId)

    const onPointerMove = (moveEvent: PointerEvent) => {
      const deltaX = moveEvent.clientX - startX
      const nextWidth = Math.max(column.minWidth, Math.round(startWidth + deltaX))
      columnWidths = { ...columnWidths, [column.id]: nextWidth }
    }

    const onPointerUp = () => {
      cleanup()
      persistColumnPreferences()
    }

    const cleanup = () => {
      window.removeEventListener("pointermove", onPointerMove)
      window.removeEventListener("pointerup", onPointerUp)
      window.removeEventListener("pointercancel", onPointerUp)
    }

    cleanupResizeListeners = cleanup

    window.addEventListener("pointermove", onPointerMove)
    window.addEventListener("pointerup", onPointerUp)
    window.addEventListener("pointercancel", onPointerUp)
  }

  function syncTopScrollbarWidth() {
    if (!tableTopScrollContentElement || !tableScrollElement) return
    hasHorizontalOverflow = tableScrollElement.scrollWidth > tableScrollElement.clientWidth + 1
    if (!hasHorizontalOverflow) {
      tableScrollElement.scrollLeft = 0
      if (tableTopScrollElement) {
        tableTopScrollElement.scrollLeft = 0
      }
    }
    tableTopScrollContentElement.style.width = `${tableScrollElement.scrollWidth}px`
  }

  function syncHorizontalScroll(source: "top" | "bottom") {
    if (!tableTopScrollElement || !tableScrollElement || syncingHorizontalScroll) return
    syncingHorizontalScroll = true
    if (source === "top") {
      tableScrollElement.scrollLeft = tableTopScrollElement.scrollLeft
    } else {
      tableTopScrollElement.scrollLeft = tableScrollElement.scrollLeft
    }
    syncingHorizontalScroll = false
  }

  function handleHeaderDragStart(event: DragEvent, fieldName: string) {
    dragFieldName = fieldName
    if (event.dataTransfer) {
      event.dataTransfer.effectAllowed = "move"
      event.dataTransfer.setData("text/plain", fieldName)
    }
  }

  function handleHeaderDragOver(event: DragEvent, targetFieldName: string) {
    if (!dragFieldName || dragFieldName === targetFieldName) return

    event.preventDefault()

    const target = event.currentTarget as HTMLElement
    const rect = target.getBoundingClientRect()
    const midpoint = rect.left + rect.width / 2
    dragOverPosition = event.clientX < midpoint ? "before" : "after"
    dragOverFieldName = targetFieldName
  }

  function clearDragState() {
    dragFieldName = null
    dragOverFieldName = null
    dragOverPosition = "after"
  }

  function handleHeaderDrop(event: DragEvent, targetFieldName: string) {
    event.preventDefault()
    if (!dragFieldName) {
      clearDragState()
      return
    }

    moveCustomField(dragFieldName, targetFieldName, dragOverPosition)
    clearDragState()
  }

  function handleDeleteProperty(fieldName: string) {
    const field = customFieldByName(fieldName)
    if (!field) return

    const confirmed = window.confirm(`Удалить свойство «${field.name}»? Это удалит значения поля из всех карточек.`)
    if (!confirmed) return

    dispatch("deleteProperty", { fieldName })
  }

  function openPreview(doc: Document) {
    if (openInPageMode) {
      push(documentRoute(doc))
      return
    }
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

  function formatCreatedAt(value: string) {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return "—"
    return date.toLocaleString("ru-RU", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit"
    })
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
    const clickedInsideTable = tableShellElement.contains(target)
    const clickedInsideOverlay = overlayPopupElement?.contains(target) ?? false
    if (!clickedInsideTable && !clickedInsideOverlay) {
      dispatch("closeFilterPanel")
    }
  }

  function handleEscape(event: KeyboardEvent) {
    if (event.key === "Escape" && openFilterField) {
      dispatch("closeFilterPanel")
    }
  }

  $: {
    const customFieldNames = customFieldSettings.map(field => field.name)
    const existingOrder = customFieldOrder.filter(name => customFieldNames.includes(name))
    const missingNames = customFieldNames.filter(name => !existingOrder.includes(name))
    const nextOrder = [...existingOrder, ...missingNames]

    if (!arraysEqual(customFieldOrder, nextOrder)) {
      customFieldOrder = nextOrder
    }
  }

  $: orderedCustomColumns = customFieldOrder
    .map(name => customFieldByName(name))
    .filter((field): field is CardCustomFieldSetting => Boolean(field))
    .map(customColumnFromField)

  $: visibleColumns = [...systemColumns, ...orderedCustomColumns]

  $: {
    console.debug("[DocumentTable] customFieldSettings loaded:", customFieldSettings)
    console.debug("[DocumentTable] ordered custom field names:", customFieldOrder)
    console.debug("[DocumentTable] visible columns:", visibleColumns.map(column => column.id))
  }

  $: {
    if (documents.length && orderedCustomColumns.length) {
      const sampleDoc = documents[0]
      const sampleMapping = orderedCustomColumns.reduce<Record<string, string | number | null | undefined>>(
        (acc, column) => {
          if (column.fieldName) {
            acc[column.fieldName] = sampleDoc.custom_fields?.[column.fieldName]
          }
          return acc
        },
        {}
      )
      console.debug("[DocumentTable] first row custom-field mapping:", {
        documentId: sampleDoc._id,
        mapping: sampleMapping
      })
    }
  }

  onMount(() => {
    const savedRaw = window.localStorage.getItem(columnPreferencesStorageKey)
    if (savedRaw) {
      try {
        const parsed = JSON.parse(savedRaw) as {
          widths?: Record<string, number>
          customFieldOrder?: string[]
        }
        columnWidths = parsed.widths ?? {}
        customFieldOrder = parsed.customFieldOrder ?? []
      } catch (error) {
        console.warn("Failed to parse table column preferences", error)
      }
    }

    initializeColumnState()
    syncTopScrollbarWidth()
    document.addEventListener("mousedown", handleOutsideClick)
    document.addEventListener("keydown", handleEscape)
    window.addEventListener("resize", updatePopupPosition)
    window.addEventListener("resize", syncTopScrollbarWidth)
    window.addEventListener("scroll", updatePopupPosition, true)
    tableTopScrollElement?.addEventListener("scroll", handleTopHorizontalScroll)
    tableScrollElement?.addEventListener("scroll", updatePopupPosition)
    tableScrollElement?.addEventListener("scroll", handleBottomHorizontalScroll)

    return () => {
      if (cleanupResizeListeners) {
        cleanupResizeListeners()
        cleanupResizeListeners = null
      }
      document.removeEventListener("mousedown", handleOutsideClick)
      document.removeEventListener("keydown", handleEscape)
      window.removeEventListener("resize", updatePopupPosition)
      window.removeEventListener("resize", syncTopScrollbarWidth)
      window.removeEventListener("scroll", updatePopupPosition, true)
      tableTopScrollElement?.removeEventListener("scroll", handleTopHorizontalScroll)
      tableScrollElement?.removeEventListener("scroll", updatePopupPosition)
      tableScrollElement?.removeEventListener("scroll", handleBottomHorizontalScroll)
    }
  })

  $: initializeColumnState()
  $: persistColumnPreferences()
  $: documents, tick().then(syncTopScrollbarWidth)
  $: visibleColumns, tick().then(syncTopScrollbarWidth)
  $: if (openFilterField) {
    tick().then(updatePopupPosition)
  }
</script>

<div class="table-shell panel" bind:this={tableShellElement}>
  <div class="table-top-scroll" class:hidden={!hasHorizontalOverflow} bind:this={tableTopScrollElement}>
    <div class="table-top-scroll-content" bind:this={tableTopScrollContentElement}></div>
  </div>
  <div class="table-scroll" bind:this={tableScrollElement}>
    <table class="documents-table">
      <colgroup>
        {#each visibleColumns as column (column.id)}
          <col style={`width: ${getColumnWidth(column)}px; min-width: ${column.minWidth}px;`} />
        {/each}
        <col style="width: 44px; min-width: 44px;" />
      </colgroup>
      <thead>
        <tr>
          {#each visibleColumns as column (column.id)}
            {#if column.kind === "select"}
              <th>{column.label}</th>
            {:else if column.kind === "preview" || column.kind === "tags"}
              <th>
                {column.label}
                {#if column.resizable}
                  <button
                    type="button"
                    class="column-resizer"
                    aria-label={`Изменить ширину колонки ${column.label.toLowerCase()}`}
                    on:pointerdown={(event) => startResize(event, column)}
                  ></button>
                {/if}
              </th>
            {:else if column.kind === "filename"}
              <th class="field-header-cell">
                <button
                  class="field-header-trigger"
                  class:active={isFilenameFilterActive()}
                  use:registerFilterTrigger={"system:filename"}
                  on:click={() => dispatch("toggleFilterPanel", { fieldName: "system:filename" })}
                >
                  <span>{column.label}</span>
                  <span class="filter-icon">▾</span>
                </button>
                <button
                  type="button"
                  class="column-resizer"
                  aria-label="Изменить ширину колонки файл"
                  on:pointerdown={(event) => startResize(event, column)}
                ></button>
              </th>
            {:else if column.kind === "created_at"}
              <th class="field-header-cell">
                <button
                  class="field-header-trigger"
                  class:active={isCreatedAtFilterActive()}
                  use:registerFilterTrigger={"system:created_at"}
                  on:click={() => dispatch("toggleFilterPanel", { fieldName: "system:created_at" })}
                >
                  <span>{column.label}</span>
                  <span class="filter-icon">▾</span>
                </button>
                <button
                  type="button"
                  class="column-resizer"
                  aria-label="Изменить ширину колонки дата создания"
                  on:pointerdown={(event) => startResize(event, column)}
                ></button>
              </th>
            {:else}
              <th
                class="field-header-cell custom-header"
                draggable={column.movable}
                class:drag-source={dragFieldName === column.fieldName}
                class:drop-before={dragOverFieldName === column.fieldName && dragOverPosition === "before"}
                class:drop-after={dragOverFieldName === column.fieldName && dragOverPosition === "after"}
                on:dragstart={(event) => column.fieldName && handleHeaderDragStart(event, column.fieldName)}
                on:dragover={(event) => column.fieldName && handleHeaderDragOver(event, column.fieldName)}
                on:drop={(event) => column.fieldName && handleHeaderDrop(event, column.fieldName)}
                on:dragleave={() => {
                  if (dragOverFieldName === column.fieldName) {
                    dragOverFieldName = null
                  }
                }}
                on:dragend={clearDragState}
              >
                <button
                  class="field-header-trigger"
                  class:active={column.fieldName ? isFieldFilterActive(column.fieldName) : false}
                  use:registerFilterTrigger={column.fieldName ?? ""}
                  on:click={() => column.fieldName && dispatch("toggleFilterPanel", { fieldName: column.fieldName })}
                >
                  <span class="drag-indicator" aria-hidden="true">⋮⋮</span>
                  <span>{column.label}</span>
                  <span class="filter-icon">▾</span>
                </button>
                <button
                  type="button"
                  class="column-resizer"
                  aria-label={`Изменить ширину колонки ${column.label}`}
                  on:pointerdown={(event) => startResize(event, column)}
                ></button>
              </th>
            {/if}
          {/each}
          <th class="add-property-cell">
            <button
              type="button"
              class="add-property-btn"
              aria-label="Добавить свойство"
              title="Добавить свойство"
              on:click={() => dispatch("addProperty")}
            >
              +
            </button>
          </th>
        </tr>
      </thead>
      <tbody>
        {#each documents as doc (doc._id)}
          <tr class:selected-row={selectedIds.includes(doc._id)}>
            {#each visibleColumns as column (column.id)}
              {#if column.kind === "select"}
                <td class="cell-center">
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(doc._id)}
                    on:change={() => dispatch("toggleSelect", { id: doc._id })}
                  />
                </td>
              {:else if column.kind === "preview"}
                <td>
                  <button class="preview-btn" on:click={() => openPreview(doc)}>
                    <img src={cardImageSrc(doc)} alt="" class="row-preview" />
                  </button>
                </td>
              {:else if column.kind === "filename"}
                <td>
                  <button class="filename-btn" on:click={() => openPreview(doc)} title={doc.display_filename || doc.filename}>
                    {getFilenameWithoutExtension(doc.display_filename || doc.filename || "")}
                  </button>
                </td>
              {:else if column.kind === "created_at"}
                <td title={formatCreatedAt(doc.created_at)}>{formatCreatedAt(doc.created_at)}</td>
              {:else if column.kind === "tags"}
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
              {:else}
                <td title={customFieldValue(doc, column.fieldName ?? "")}>{customFieldValue(doc, column.fieldName ?? "")}</td>
              {/if}
            {/each}
            <td class="add-property-spacer"></td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
</div>

{#if openFilterField}
  <div
    class="field-filter-popup-overlay"
    bind:this={overlayPopupElement}
    style={`top: ${popupPosition.top}px; left: ${popupPosition.left}px;`}
  >
    {#if openFilterField === "system:filename"}
      <div class="popup-row">
        <button class="secondary" class:active={filenameSort === "asc"} on:click={() => dispatch("setFilenameSort", { sort: "asc" })}>A-Z</button>
        <button class="secondary" class:active={filenameSort === "desc"} on:click={() => dispatch("setFilenameSort", { sort: "desc" })}>Z-A</button>
        <button class="secondary" class:active={filenameSort === "none"} on:click={() => dispatch("setFilenameSort", { sort: "none" })}>Без сорт.</button>
      </div>
      <div class="popup-row">
        <input
          type="text"
          placeholder="Фильтр по имени файла"
          value={filenameFilterText}
          on:input={(event) => {
            const target = event.target as HTMLInputElement
            dispatch("setFilenameFilterText", { value: target.value })
          }}
        />
      </div>
      <div class="popup-row">
        <button class="secondary" on:click={() => dispatch("clearFilenameFilter")}>Сбросить</button>
        <button class="primary" on:click={() => dispatch("closeFilterPanel")}>Готово</button>
      </div>
    {:else if openFilterField === "system:created_at"}
      <div class="popup-row">
        <button class="secondary" class:active={createdAtSort === "newest"} on:click={() => dispatch("setCreatedAtSort", { sort: "newest" })}>Сначала новые</button>
        <button class="secondary" class:active={createdAtSort === "oldest"} on:click={() => dispatch("setCreatedAtSort", { sort: "oldest" })}>Сначала старые</button>
        <button class="secondary" class:active={createdAtSort === "none"} on:click={() => dispatch("setCreatedAtSort", { sort: "none" })}>Без сорт.</button>
      </div>
      <div class="popup-row">
        <button class="secondary" class:active={createdAtRange === "today"} on:click={() => dispatch("setCreatedAtRange", { range: "today" })}>Сегодня</button>
        <button class="secondary" class:active={createdAtRange === "last_7_days"} on:click={() => dispatch("setCreatedAtRange", { range: "last_7_days" })}>7 дней</button>
        <button class="secondary" class:active={createdAtRange === "this_month"} on:click={() => dispatch("setCreatedAtRange", { range: "this_month" })}>Этот месяц</button>
        <button class="secondary" class:active={createdAtRange === "all"} on:click={() => dispatch("setCreatedAtRange", { range: "all" })}>Все</button>
      </div>
      <div class="popup-row">
        <button class="secondary" on:click={() => dispatch("clearCreatedAtFilter")}>Сбросить</button>
        <button class="primary" on:click={() => dispatch("closeFilterPanel")}>Готово</button>
      </div>
    {:else}
      {#if customFieldFilters[openFilterField]?.mode === "text"}
        <div class="popup-row">
          <button class="secondary" on:click={() => dispatch("setTextSort", { fieldName: openFilterField, sort: "asc" })}>A-Z</button>
          <button class="secondary" on:click={() => dispatch("setTextSort", { fieldName: openFilterField, sort: "desc" })}>Z-A</button>
          <button class="secondary" on:click={() => dispatch("setTextSort", { fieldName: openFilterField, sort: "none" })}>Без сорт.</button>
        </div>
        <div class="popup-row">
          <button class="secondary" on:click={() => dispatch("selectAllTextValues", { fieldName: openFilterField })}>Выбрать все</button>
          <button class="secondary" on:click={() => dispatch("clearTextValues", { fieldName: openFilterField })}>Очистить</button>
        </div>
        <div class="popup-values">
          {#each fieldUniqueTextValues(openFilterField) as value}
            <label class="popup-checkbox">
              <input
                type="checkbox"
                checked={customFieldFilters[openFilterField]?.mode === "text" && customFieldFilters[openFilterField].selectedValues.includes(value)}
                on:change={() => dispatch("toggleTextValue", { fieldName: openFilterField, value })}
              />
              <span>{value}</span>
            </label>
          {/each}
        </div>
      {:else}
        <div class="popup-row">
          <button class="secondary" on:click={() => dispatch("setNumberSort", { fieldName: openFilterField, sort: "asc" })}>0-9</button>
          <button class="secondary" on:click={() => dispatch("setNumberSort", { fieldName: openFilterField, sort: "desc" })}>9-0</button>
          <button class="secondary" on:click={() => dispatch("setNumberSort", { fieldName: openFilterField, sort: "none" })}>Без сорт.</button>
        </div>
        <div class="popup-row">
          <select
            value={customFieldFilters[openFilterField]?.mode === "number" ? customFieldFilters[openFilterField].operator : "none"}
            on:change={(event) => {
              const target = event.target as HTMLSelectElement
              dispatch("setNumberOperator", { fieldName: openFilterField, operator: target.value as NumberFilter["operator"] })
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
            value={customFieldFilters[openFilterField]?.mode === "number" ? customFieldFilters[openFilterField].value1 : ""}
            on:input={(event) => {
              const target = event.target as HTMLInputElement
              dispatch("setNumberValue", { fieldName: openFilterField, key: "value1", value: target.value })
            }}
          />
          {#if customFieldFilters[openFilterField]?.mode === "number" && customFieldFilters[openFilterField].operator === "between"}
            <input
              type="number"
              placeholder="И до"
              value={customFieldFilters[openFilterField]?.mode === "number" ? customFieldFilters[openFilterField].value2 : ""}
              on:input={(event) => {
                const target = event.target as HTMLInputElement
                dispatch("setNumberValue", { fieldName: openFilterField, key: "value2", value: target.value })
              }}
            />
          {/if}
        </div>
      {/if}
      <div class="popup-row">
        <button class="secondary" on:click={() => dispatch("clearFieldFilter", { fieldName: openFilterField })}>Сбросить</button>
        <button class="danger" on:click={() => handleDeleteProperty(openFilterField)}>Удалить свойство</button>
        <button class="primary" on:click={() => dispatch("closeFilterPanel")}>Готово</button>
      </div>
    {/if}
  </div>
{/if}

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

  .table-top-scroll {
    overflow-x: auto;
    overflow-y: hidden;
    width: 100%;
    margin-bottom: 2px;
    border-bottom: 1px solid color-mix(in srgb, var(--border), transparent 20%);
    background: var(--surface);
    border-top-left-radius: inherit;
    border-top-right-radius: inherit;
  }

  .table-top-scroll.hidden {
    display: none;
  }

  .table-top-scroll-content {
    height: 1px;
  }

  .table-scroll {
    overflow: auto;
    width: 100%;
    max-height: min(70vh, 760px);
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
    padding: 7px 9px;
    vertical-align: middle;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .documents-table th {
    position: sticky;
    top: 0;
    background: var(--surface-strong);
    z-index: 12;
    font-weight: 700;
    color: var(--text-muted);
    overflow: visible;
    padding-right: 14px;
    box-shadow: inset 0 -1px 0 var(--border);
  }

  .documents-table th.field-header-cell {
    position: sticky;
    overflow: visible;
    z-index: 16;
  }

  .field-header-trigger {
    all: unset;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    cursor: pointer;
    color: inherit;
    font-weight: 700;
    max-width: calc(100% - 14px);
  }

  .field-header-trigger:hover {
    color: var(--text);
  }

  .field-header-trigger.active {
    color: var(--primary);
  }

  .drag-indicator {
    font-size: 0.7rem;
    color: var(--text-muted);
    opacity: 0.6;
    transform: translateY(-1px);
  }

  .custom-header:hover .drag-indicator,
  .custom-header.drag-source .drag-indicator {
    opacity: 1;
  }

  .custom-header {
    user-select: none;
  }

  .custom-header.drag-source {
    opacity: 0.55;
  }

  .custom-header.drop-before {
    box-shadow: inset 3px 0 0 color-mix(in srgb, var(--primary), white 20%);
  }

  .custom-header.drop-after {
    box-shadow: inset -3px 0 0 color-mix(in srgb, var(--primary), white 20%);
  }

  .filter-icon {
    font-size: 0.72rem;
    color: var(--text-muted);
  }

  .field-header-trigger.active .filter-icon {
    color: var(--primary);
  }

  .field-filter-popup-overlay {
    position: fixed;
    z-index: 1200;
    min-width: 220px;
    max-width: min(86vw, 320px);
    padding: 8px;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: var(--surface-elevated);
    box-shadow: var(--shadow-soft);
    display: grid;
    gap: 6px;
  }

  .popup-row {
    display: flex;
    gap: 5px;
    flex-wrap: wrap;
  }

  .field-filter-popup-overlay :global(button),
  .field-filter-popup-overlay :global(select),
  .field-filter-popup-overlay :global(input) {
    min-height: 28px;
    padding: 0.32rem 0.56rem;
    font-size: 0.84rem;
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

  .add-property-cell {
    text-align: center;
    width: 44px;
    min-width: 44px;
    padding-right: 8px;
  }

  .add-property-btn {
    all: unset;
    width: 26px;
    height: 26px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    border: 1px dashed var(--border-strong);
    color: var(--text-muted);
    cursor: pointer;
    font-weight: 600;
    line-height: 1;
  }

  .add-property-btn:hover {
    color: var(--text);
    border-color: color-mix(in srgb, var(--primary), var(--border-strong) 50%);
    background: color-mix(in srgb, var(--surface), var(--bg-accent) 25%);
  }

  .add-property-spacer {
    width: 44px;
    min-width: 44px;
  }

  .column-resizer {
    all: unset;
    position: absolute;
    top: 0;
    right: -4px;
    width: 10px;
    height: 100%;
    cursor: col-resize;
    z-index: 30;
    touch-action: none;
  }

  .column-resizer::after {
    content: "";
    position: absolute;
    top: 18%;
    bottom: 18%;
    right: 4px;
    width: 2px;
    border-radius: 2px;
    background: color-mix(in srgb, var(--border-strong), transparent 35%);
    opacity: 0;
    transition: opacity 120ms ease;
  }

  .documents-table th:hover .column-resizer::after {
    opacity: 1;
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
