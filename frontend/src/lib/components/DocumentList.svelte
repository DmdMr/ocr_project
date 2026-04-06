<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte"
    import { getDocuments, getSettings, getTags } from "../api"
    import type { CardCustomFieldSetting, Document } from "../types"
    //import SettingsPage from "../SettingsPage.svelte";
    import DocumentCard from "./DocumentCard.svelte"
    import DocumentTable from "./DocumentTable.svelte"
    import FolderView from "./FolderView.svelte"
    import { 
        normalizeTag,
        setDocumentTags,
        deleteDocument,
        createCardField,
        deleteCardField
    
    } from "../api"

    export let refreshKey: number
    export let viewMode: "grid" | "list" | "folders" = "grid"
    export let columnCount = 5
    export let canEdit = false
    export let isAdmin = false
    const dispatch = createEventDispatcher<{
        viewModeChange: { mode: "grid" | "list" | "folders" }
        toggleSidebar: void
        folderChange: { folderId: string | null }
    }>()

    let documents: Document[] = []
    let search = ""
    let sortOrder: "date_asc" | "date_desc" | "name_asc" | "name_desc" = "date_desc"
    export let activeTag: string | null = null
    let selectedIds: string[] = []
    let customFieldSettings: CardCustomFieldSetting[] = []
    let openFilterField: string | null = null
    let filenameFilterText = ""
    let filenameSort: "none" | "asc" | "desc" = "none"
    let createdAtSort: "none" | "newest" | "oldest" = "none"
    let createdAtRange: "all" | "today" | "last_7_days" | "this_month" = "all"
    export let sidebarOpen = true

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
    let customFieldFilters: Record<string, CustomFieldFilter> = {}
    let masonryColumns: Document[][] = []
    let masonryFailed = false
    let viewportWidth = 1280

    function toggleCardSelection(id: string) {
        if (!canEdit) return
        if (selectedIds.includes(id)) {
            selectedIds = selectedIds.filter(item => item !== id)
        } else {
            selectedIds = [...selectedIds, id]
        }
    }

    function setViewMode(mode: "grid" | "list" | "folders") {
        viewMode = mode
        dispatch("viewModeChange", { mode })
    }

    function clearSelection() {
        selectedIds = []
    }

    async function bulkDelete() {
        if (!canEdit) return
        if (!selectedIds.length) return

        const confirmed = confirm(`Удалить ${selectedIds.length} карточек?`)
        if (!confirmed) return

        await Promise.all(selectedIds.map(id => deleteDocument(id)))

        documents = documents.filter(doc => !selectedIds.includes(doc._id))
        clearSelection()
    }

    async function bulkAddTag() {
        if (!canEdit) return

        const availableTags = await getTags()

        if (!selectedIds.length) return

        const entered = prompt(`Введите тег для выбранных карточек:\n${availableTags.join(", ")}`)
        if (!entered) return

        const normalized = normalizeTag(entered)

        const selectedDocs = documents.filter(doc => selectedIds.includes(doc._id))

        const updatedDocs = await Promise.all(
            selectedDocs.map(async (doc) => {
            const currentTags = doc.tags ?? []
            const nextTags = currentTags.includes(normalized)
                ? currentTags
                : [...currentTags, normalized]

            return await setDocumentTags(doc._id, nextTags)
            })
        )

        documents = documents.map(doc => {
            const updated = updatedDocs.find(item => item._id === doc._id)
            return updated ?? doc
        })

        clearSelection()
    }

    async function load() {
        documents = await getDocuments()
        const settings = await getSettings()
        customFieldSettings = settings.fields_for_cards ?? []
        console.debug("[DocumentList] fields_for_cards from backend:", settings.fields_for_cards)
        console.debug("[DocumentList] customFieldSettings state:", customFieldSettings)
        console.debug("[DocumentList] first document custom_fields:", documents[0]?.custom_fields ?? null)
        for (const field of customFieldSettings) {
            if (customFieldFilters[field.name]) continue
            customFieldFilters[field.name] = field.type === "number"
                ? {
                    mode: "number",
                    sort: "none",
                    operator: "none",
                    value1: "",
                    value2: ""
                }
                : {
                    mode: "text",
                    selectedValues: [],
                    sort: "none"
                }
        }
    }

    function removeFromList(id: string) {
        documents = documents.filter(doc => doc._id !== id)
    }

    function replaceDocumentInList(updatedDocument: Document) {
        documents = documents.map(doc => doc._id === updatedDocument._id ? updatedDocument : doc)
    }

    function getFieldRawValue(doc: Document, fieldName: string) {
        return doc.custom_fields?.[fieldName]
    }

    function getFieldTextValue(doc: Document, fieldName: string) {
        const value = getFieldRawValue(doc, fieldName)
        if (value === null || value === undefined || value === "") return "(пусто)"
        return String(value)
    }

    function getFieldNumberValue(doc: Document, fieldName: string) {
        const value = getFieldRawValue(doc, fieldName)
        if (value === null || value === undefined || value === "") return null
        const parsed = Number(value)
        return Number.isFinite(parsed) ? parsed : null
    }

    function fieldUniqueTextValues(fieldName: string) {
        const values = new Set<string>()
        for (const doc of documents) {
            values.add(getFieldTextValue(doc, fieldName))
        }
        return Array.from(values).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: "base" }))
    }

    function toggleFilterPanel(fieldName: string) {
        openFilterField = openFilterField === fieldName ? null : fieldName
    }

    function setFilenameFilterText(value: string) {
        filenameFilterText = value
    }

    function setFilenameSort(sort: "none" | "asc" | "desc") {
        filenameSort = sort
    }

    function clearFilenameFilter() {
        filenameFilterText = ""
        filenameSort = "none"
    }

    function setCreatedAtSort(sort: "none" | "newest" | "oldest") {
        createdAtSort = sort
    }

    function setCreatedAtRange(range: "all" | "today" | "last_7_days" | "this_month") {
        createdAtRange = range
    }

    function clearCreatedAtFilter() {
        createdAtSort = "none"
        createdAtRange = "all"
    }

    function isSameLocalDay(date: Date, reference: Date) {
        return (
            date.getFullYear() === reference.getFullYear() &&
            date.getMonth() === reference.getMonth() &&
            date.getDate() === reference.getDate()
        )
    }

    function matchesCreatedAtRange(createdAt: string) {
        if (createdAtRange === "all") return true
        const created = new Date(createdAt)
        if (Number.isNaN(created.getTime())) return false

        const now = new Date()
        if (createdAtRange === "today") {
            return isSameLocalDay(created, now)
        }

        if (createdAtRange === "last_7_days") {
            const threshold = new Date(now)
            threshold.setDate(threshold.getDate() - 6)
            threshold.setHours(0, 0, 0, 0)
            return created.getTime() >= threshold.getTime()
        }

        if (createdAtRange === "this_month") {
            return (
                created.getFullYear() === now.getFullYear() &&
                created.getMonth() === now.getMonth()
            )
        }

        return true
    }

    function isFilenameFilterActive() {
        return filenameSort !== "none" || filenameFilterText.trim().length > 0
    }

    function isCreatedAtFilterActive() {
        return createdAtSort !== "none" || createdAtRange !== "all"
    }

    async function handleAddProperty() {
        if (!isAdmin) return
        const name = prompt("Название нового свойства")
        if (!name || !name.trim()) return

        const typePrompt = prompt("Тип свойства: text, number или people", "text")
        if (!typePrompt) return
        const normalizedType = typePrompt.trim().toLowerCase()
        if (normalizedType !== "text" && normalizedType !== "number" && normalizedType !== "people") {
            alert("Поддерживаются только типы: text, number или people")
            return
        }

        try {
            await createCardField(name.trim(), normalizedType as "text" | "number" | "people")
            await load()
        } catch (error) {
            const message = error instanceof Error ? error.message : "Не удалось создать свойство"
            alert(message)
        }
    }

    async function handleDeleteProperty(fieldName: string) {
        if (!isAdmin) return
        const field = customFieldSettings.find(item => item.name === fieldName)
        if (!field) return

        try {
            await deleteCardField(fieldName)
            customFieldSettings = customFieldSettings.filter(item => item.name !== fieldName)
            documents = documents.map(doc => {
                if (!doc.custom_fields || !(fieldName in doc.custom_fields)) return doc
                const nextCustomFields = { ...doc.custom_fields }
                delete nextCustomFields[fieldName]
                return { ...doc, custom_fields: nextCustomFields }
            })
            const nextFilters = { ...customFieldFilters }
            delete nextFilters[fieldName]
            customFieldFilters = nextFilters
            if (openFilterField === fieldName) {
                openFilterField = null
            }
        } catch (error) {
            const message = error instanceof Error ? error.message : "Не удалось удалить свойство"
            alert(message)
        }
    }

    function setTextSort(fieldName: string, sort: "none" | "asc" | "desc") {
        const current = customFieldFilters[fieldName]
        if (!current || current.mode !== "text") return
        customFieldFilters = {
            ...customFieldFilters,
            [fieldName]: { ...current, sort }
        }
    }

    function setNumberSort(fieldName: string, sort: "none" | "asc" | "desc") {
        const current = customFieldFilters[fieldName]
        if (!current || current.mode !== "number") return
        customFieldFilters = {
            ...customFieldFilters,
            [fieldName]: { ...current, sort }
        }
    }

    function toggleTextValue(fieldName: string, value: string) {
        const current = customFieldFilters[fieldName]
        if (!current || current.mode !== "text") return
        const hasValue = current.selectedValues.includes(value)
        customFieldFilters = {
            ...customFieldFilters,
            [fieldName]: {
                ...current,
                selectedValues: hasValue
                    ? current.selectedValues.filter(item => item !== value)
                    : [...current.selectedValues, value]
            }
        }
    }

    function selectAllTextValues(fieldName: string) {
        const current = customFieldFilters[fieldName]
        if (!current || current.mode !== "text") return
        customFieldFilters = {
            ...customFieldFilters,
            [fieldName]: { ...current, selectedValues: fieldUniqueTextValues(fieldName) }
        }
    }

    function clearTextValues(fieldName: string) {
        const current = customFieldFilters[fieldName]
        if (!current || current.mode !== "text") return
        customFieldFilters = {
            ...customFieldFilters,
            [fieldName]: { ...current, selectedValues: [] }
        }
    }

    function setNumberOperator(fieldName: string, operator: NumberFilter["operator"]) {
        const current = customFieldFilters[fieldName]
        if (!current || current.mode !== "number") return
        customFieldFilters = {
            ...customFieldFilters,
            [fieldName]: { ...current, operator }
        }
    }

    function setNumberValue(fieldName: string, key: "value1" | "value2", value: string) {
        const current = customFieldFilters[fieldName]
        if (!current || current.mode !== "number") return
        customFieldFilters = {
            ...customFieldFilters,
            [fieldName]: { ...current, [key]: value }
        }
    }

    function clearFieldFilter(fieldName: string) {
        const field = customFieldSettings.find(item => item.name === fieldName)
        if (!field) return
        customFieldFilters = {
            ...customFieldFilters,
            [fieldName]: field.type === "number"
                ? { mode: "number", sort: "none", operator: "none", value1: "", value2: "" }
                : { mode: "text", sort: "none", selectedValues: [] }
        }
    }

    function isFieldFilterActive(fieldName: string) {
        const filter = customFieldFilters[fieldName]
        if (!filter) return false
        if (filter.mode === "text") {
            return filter.sort !== "none" || filter.selectedValues.length > 0
        }
        return filter.sort !== "none" || filter.operator !== "none" || Boolean(filter.value1 || filter.value2)
    }

    function matchesNumberFilter(value: number | null, filter: NumberFilter) {
        if (filter.operator === "none") return true
        const first = Number(filter.value1)
        const second = Number(filter.value2)

        if (value === null) return false
        if (filter.operator === "equals") return Number.isFinite(first) ? value === first : true
        if (filter.operator === "greater_than") return Number.isFinite(first) ? value > first : true
        if (filter.operator === "less_than") return Number.isFinite(first) ? value < first : true
        if (filter.operator === "between") {
            if (!Number.isFinite(first) || !Number.isFinite(second)) return true
            const min = Math.min(first, second)
            const max = Math.max(first, second)
            return value >= min && value <= max
        }
        return true
    }

    function getActiveCustomSort() {
        for (const field of customFieldSettings) {
            const filter = customFieldFilters[field.name]
            if (filter && filter.sort !== "none") {
                return { fieldName: field.name, mode: filter.mode, direction: filter.sort }
            }
        }
        return null
    }

    function estimateCardHeight(doc: Document) {
        const filename = (doc.display_filename || doc.filename || "").length
        const tags = doc.tags?.length ?? 0
        const tagRows = Math.ceil(tags / 3)
        return 280 + Math.min(120, filename * 1.8) + tagRows * 18
    }

    function getResponsiveColumnCount() {
        if (viewportWidth < 420) return 1
        if (viewportWidth < 640) return 2
        if (viewportWidth < 880) return 3
        if (viewportWidth < 1180) return 4
        return Math.max(1, Math.min(columnCount || 5, 6))
    }

    function buildMasonryColumns(items: Document[], columnsCount: number) {
        const count = Math.max(1, columnsCount)
        const columns: Document[][] = Array.from({ length: count }, () => [])
        const heights: number[] = Array.from({ length: count }, () => 0)

        for (const item of items) {
            let targetIndex = 0
            let minHeight = heights[0]
            for (let index = 1; index < heights.length; index++) {
                if (heights[index] < minHeight) {
                    minHeight = heights[index]
                    targetIndex = index
                }
            }
            columns[targetIndex].push(item)
            heights[targetIndex] += estimateCardHeight(item)
        }

        return columns
    }

    function handleResize() {
        viewportWidth = window.innerWidth
    }




    onMount(() => {
        load()
        handleResize()
        window.addEventListener("resize", handleResize)
        return () => window.removeEventListener("resize", handleResize)
    })

    $: if (refreshKey) {
        load()
    }

    $: if (viewMode !== "folders") {
        dispatch("folderChange", { folderId: null })
    }

 
    $: filtered = documents.filter(doc => {
        const displayName = doc.display_filename ?? doc.filename
        const filenameValue = (displayName || doc.filename || "").toLowerCase()
        const matchesText =
            displayName.toLowerCase().includes(search.toLowerCase()) ||
            doc.filename.toLowerCase().includes(search.toLowerCase()) ||
            doc.recognized_text.toLowerCase().includes(search.toLowerCase()) ||
            doc.tags?.some(tag => tag.toLowerCase().includes(search.toLowerCase()))
        const matchesTag = !activeTag || doc.tags?.includes(activeTag)
        const matchesFilenameText = !filenameFilterText.trim() || filenameValue.includes(filenameFilterText.trim().toLowerCase())
        const matchesDateRange = matchesCreatedAtRange(doc.created_at)
        if (!matchesText || !matchesTag || !matchesFilenameText || !matchesDateRange) return false

        for (const field of customFieldSettings) {
            const filter = customFieldFilters[field.name]
            if (!filter) continue
            if (filter.mode === "text" && filter.selectedValues.length) {
                const value = getFieldTextValue(doc, field.name)
                if (!filter.selectedValues.includes(value)) return false
            }
            if (filter.mode === "number") {
                const numberValue = getFieldNumberValue(doc, field.name)
                if (!matchesNumberFilter(numberValue, filter)) return false
            }
        }

        return true
    })


    $: sortedDocuments = [...filtered].sort((a, b) => {
        if (filenameSort !== "none") {
            const aName = (a.display_filename || a.filename || "")
            const bName = (b.display_filename || b.filename || "")
            const compared = aName.localeCompare(bName, undefined, { sensitivity: "base" })
            if (compared !== 0) return filenameSort === "asc" ? compared : -compared
        }

        if (createdAtSort !== "none") {
            const dateA = new Date(a.created_at).getTime()
            const dateB = new Date(b.created_at).getTime()
            if (dateA !== dateB) {
                return createdAtSort === "newest" ? dateB - dateA : dateA - dateB
            }
        }

        const customSort = getActiveCustomSort()
        if (customSort) {
            const directionMultiplier = customSort.direction === "asc" ? 1 : -1
            if (customSort.mode === "text") {
                const aValue = getFieldTextValue(a, customSort.fieldName)
                const bValue = getFieldTextValue(b, customSort.fieldName)
                const compared = aValue.localeCompare(bValue, undefined, { sensitivity: "base" })
                if (compared !== 0) return compared * directionMultiplier
            } else {
                const aValue = getFieldNumberValue(a, customSort.fieldName)
                const bValue = getFieldNumberValue(b, customSort.fieldName)
                const safeA = aValue ?? Number.NEGATIVE_INFINITY
                const safeB = bValue ?? Number.NEGATIVE_INFINITY
                if (safeA !== safeB) return (safeA - safeB) * directionMultiplier
            }
        }

        const dateA = new Date(a.created_at).getTime() 
        const dateB = new Date(b.created_at).getTime()

        if (sortOrder === "date_asc") {
            return dateA - dateB
        }

        if (sortOrder === "date_desc") {
            return dateB - dateA
        }

        if (sortOrder === "name_asc") {
            return (a.display_filename || a.filename || "").localeCompare(b.display_filename || b.filename || "")
        }

        if (sortOrder === "name_desc") {
            return (b.display_filename || b.filename || "").localeCompare(a.display_filename || a.filename || "")
        }

        return 0
    })

    $: {
        if (masonryFailed) {
            masonryColumns = []
        } else {
            try {
                masonryColumns = buildMasonryColumns(sortedDocuments, getResponsiveColumnCount())
            } catch (error) {
                console.error("Masonry layout fallback to grid", error)
                masonryFailed = true
                masonryColumns = []
            }
        }
    }





</script>

<div class="search-manager panel">
    <div class="controls-row compact-toolbar">
        <button
            type="button"
            class="sidebar-toggle-inline"
            class:active={sidebarOpen}
            aria-label={sidebarOpen ? "Скрыть боковую панель" : "Показать боковую панель"}
            title={sidebarOpen ? "Скрыть боковую панель" : "Показать боковую панель"}
            on:click={() => dispatch("toggleSidebar")}
        >
            ☰
        </button>

        <input
            type="text"
            class="my-input compact-search"
            placeholder="Поиск документов"
            bind:value={search}
        />

        <div class="view-toggle" role="group" aria-label="Режим отображения">
            <button
                class="secondary"
                class:active={viewMode === "grid"}
                on:click={() => setViewMode("grid")}
            >
                Сетка
            </button>
            <button
                class="secondary"
                class:active={viewMode === "list"}
                on:click={() => setViewMode("list")}
            >
                Таблица
            </button>
            <button
                class="secondary"
                class:active={viewMode === "folders"}
                on:click={() => setViewMode("folders")}
            >
                Папки
            </button>
        </div>
    </div>

{#if viewMode !== "folders" && canEdit && selectedIds.length > 0}
  <div class="bulk-actions-manager panel">
    <div class="bulk-left">
      Выбрано: {selectedIds.length}
    </div>

    <div class="bulk-right">
      <button on:click={bulkAddTag}>Добавить тег</button>
      <button class="danger" on:click={bulkDelete}>Удалить</button>
      <button on:click={clearSelection}>Отмена</button>
    </div>
  </div>

  <nav class="breadcrumbs" aria-label="Путь папки">
    <button class="crumb" on:click={() => openFolder(null)}>Root</button>
    {#if unsortedFolderId}
      <span>/</span>
      <button class="crumb" on:click={() => openFolder(unsortedFolderId)}>Unsorted</button>
    {/if}
    {#if breadcrumbs.length}
      {#each breadcrumbs as crumb}
        {#if !unsortedFolderId || crumb.id !== unsortedFolderId}
          <span>/</span>
          <button class="crumb" on:click={() => openFolder(crumb.id)}>{crumb.name}</button>
        {/if}
      {/each}
    {/if}
  </nav>

  <div
    class="root-drop-zone"
    class:active={rootDropActive}
    class:disabled={!canDropToRoot()}
    role="region"
    aria-label="Drop zone"
    on:dragover={dragOverRoot}
    on:dragleave={dragLeaveRoot}
    on:drop={dropOnRoot}
  >
    Drop here to move to {dragItem?.type === "folder" ? "Root" : "Unsorted"}
  </div>

  {#if currentFolder}
    <div class="current-folder-row">
      <strong>Текущая папка:</strong> {currentFolder.name}
      {#if currentFolder.is_system}
        <span class="system-pill">system</span>
      {/if}
    </div>
  {/if}
</div>

{#if viewMode === "folders"}
  <FolderView canEdit={canEdit} on:folderChange={(event) => dispatch("folderChange", event.detail)} />
{:else if viewMode === "grid"}
  {#if masonryFailed}
    <div class="grid-fallback">
      {#each sortedDocuments as doc (doc._id)}
        <DocumentCard
          {doc}
          {canEdit}
          search={search}
          selected={false}
          selectionActive={false}
          on:deleted={(e) => handleDeleteDocument(e.detail.id)}
        />
        {#if canEdit}
          <div class="doc-card-actions">
            <button class="secondary tiny" on:click={() => openMoveDialog({ type: "document", id: doc._id, currentParentId: currentFolderId })}>Move to…</button>
          </div>
        {/if}
      </div>
    {/each}
  </div>
{:else}
  <div class="panel table-wrap">
    <table class="mixed-table finder-like">
      <thead>
        <tr>
          <th style="width: 44px"></th>
          <th>Имя</th>
          <th>Тип</th>
          <th>Создано</th>
          <th>Теги</th>
          <th>Действия</th>
        </tr>
      </thead>
      <tbody>
        {#each filteredFolders as folder (folder.id)}
          <tr
            class="folder-row"
            class:drop-target={dropTargetFolderId === folder.id}
            draggable={canEdit && !folder.is_system}
            on:dragstart={(event) => dragStartFolder(event, folder)}
            on:dragend={dragEnd}
            on:dragover={(event) => dragOverFolder(event, folder.id)}
            on:dragleave={() => dragLeaveFolder(folder.id)}
            on:drop={(event) => dropOnFolder(event, folder.id)}
          >
            <td class="drag-col">{#if canEdit && !folder.is_system}<span class="drag-tip">⋮⋮</span>{/if}</td>
            <td>
              <button class="linkish main-link" on:click={() => openFolder(folder.id)}>📁 {folder.name}</button>
              {#if folder.is_system}<span class="system-pill">system</span>{/if}
            </td>
            <td><span class="type-pill folder">Folder</span></td>
            <td>{folder.created_at ? new Date(folder.created_at).toLocaleString() : "—"}</td>
            <td>—</td>
            <td class="actions">
              <button class="secondary tiny" on:click={() => openFolder(folder.id)}>Open</button>
              {#if canEdit && !folder.is_system}
                <button class="secondary tiny" on:click={() => openMoveDialog({ type: "folder", id: folder.id, currentParentId: folder.parent_id, isSystem: folder.is_system })}>Move to…</button>
                <button class="secondary tiny" on:click={() => handleRenameFolder(folder)}>Rename</button>
                <button class="danger tiny" on:click={() => handleDeleteFolder(folder)}>Delete</button>
              {/if}
            </td>
          </tr>
        {/each}

        {#each filteredDocuments as doc (doc._id)}
          <tr class="doc-row" draggable={canEdit} on:dragstart={(event) => dragStartDocument(event, doc)} on:dragend={dragEnd}>
            <td class="drag-col">{#if canEdit}<span class="drag-tip">⋮⋮</span>{/if}</td>
            <td><button class="linkish main-link" on:click={() => openDocument(doc)}>📄 {doc.display_filename || doc.filename}</button></td>
            <td><span class="type-pill doc">Document</span></td>
            <td>{doc.created_at ? new Date(doc.created_at).toLocaleString() : "—"}</td>
            <td>{doc.tags?.join(", ") || "—"}</td>
            <td class="actions">
              <button class="secondary tiny" on:click={() => openDocument(doc)}>Open</button>
              {#if canEdit}
                <button class="secondary tiny" on:click={() => openMoveDialog({ type: "document", id: doc._id, currentParentId: currentFolderId })}>Move to…</button>
                <button class="danger tiny" on:click={() => handleDeleteDocument(doc._id)}>Delete</button>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}

{#if moveDialogOpen && moveDialogItem}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="move-modal-backdrop" on:click={() => moveDialogOpen = false}>
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="move-modal panel" on:click|stopPropagation>
      <h3>Move {moveDialogItem.type === "folder" ? "folder" : "document"}</h3>
      <select bind:value={moveTargetId}>
        {#if moveDialogItem.type === "folder"}
          <option value="">Root</option>
        {:else if unsortedFolderId}
          <option value={unsortedFolderId}>Unsorted</option>
        {/if}
        {#each moveCandidates as folder (folder.id)}
          <option value={folder.id}>{folder.name}</option>
        {/each}
      </select>
      <div class="move-modal-actions">
        <button class="primary" on:click={confirmMoveDialog} disabled={moving}>Move</button>
        <button on:click={() => moveDialogOpen = false}>Cancel</button>
      </div>
    </div>
  </div>
{/if}

<style>
.search-manager { padding: 10px 12px; margin-bottom: 16px; text-align: left; }
.controls-row { display: flex; justify-content: left; align-items: center; gap: 8px; flex-wrap: wrap; }
.compact-search { min-width: min(340px, 100%); flex: 1 1 260px; }
.sidebar-toggle-inline { width: 34px; min-width: 34px; height: 34px; padding: 0; border-radius: 10px; }
.breadcrumbs { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.crumb { background: transparent; border: 0; padding: 0; text-decoration: underline; color: var(--text-muted); }
.root-drop-zone { margin-top: 10px; border: 1px dashed var(--border); border-radius: 10px; padding: 8px 10px; color: var(--text-muted); }
.root-drop-zone.active { border-color: var(--primary); background: color-mix(in srgb, var(--primary), transparent 88%); }
.root-drop-zone.disabled { opacity: .6; }
.current-folder-row { margin-top: 8px; display: flex; align-items: center; gap: 8px; }
.grid-fallback { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.folder-card { padding: 14px; display: grid; gap: 10px; transition: border-color .12s ease, background .12s ease; }
.folder-card.drop-target,
tr.drop-target { border: 1px solid color-mix(in srgb, var(--primary), var(--border) 30%); background: color-mix(in srgb, var(--primary), transparent 90%); }
.folder-open { text-align: left; font-weight: 700; }
.folder-meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.drag-tip { color: var(--text-muted); cursor: grab; }
.system-pill { font-size: .72rem; border: 1px solid var(--border); border-radius: 999px; padding: 2px 8px; color: var(--text-muted); }
.table-wrap { overflow-x: auto; }
.mixed-table { width: 100%; border-collapse: collapse; }
.mixed-table th, .mixed-table td { padding: 10px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: middle; }
.finder-like tbody tr { transition: background .12s ease; }
.finder-like tbody tr:hover { background: color-mix(in srgb, var(--surface), var(--primary) 6%); }
.drag-col { width: 40px; text-align: center; }
.main-link { font-weight: 500; }
.type-pill { font-size: .72rem; border-radius: 999px; padding: 3px 8px; border: 1px solid var(--border); }
.type-pill.folder { background: color-mix(in srgb, var(--primary), transparent 80%); }
.type-pill.doc { background: color-mix(in srgb, #7cfc98, transparent 78%); }
.linkish { border: 0; background: transparent; padding: 0; text-decoration: none; color: inherit; }
.linkish:hover { text-decoration: underline; }
.actions { white-space: nowrap; }
.tiny { font-size: .78rem; padding: 5px 8px; }
.error { color: var(--danger); }
.doc-draggable { position: relative; }
.doc-card-actions { margin-top: -6px; margin-bottom: 8px; display: flex; justify-content: flex-end; }

.move-modal-backdrop { position: fixed; inset: 0; background: rgba(8, 11, 19, 0.44); display: grid; place-items: center; z-index: 1200; }
.move-modal { width: min(480px, calc(100vw - 28px)); display: grid; gap: 12px; }
.move-modal select { width: 100%; min-height: 38px; }
.move-modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
