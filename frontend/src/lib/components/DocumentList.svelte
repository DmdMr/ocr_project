<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte"
    import { getDocuments, getSettings, getTags } from "../api"
    import type { CardCustomFieldSetting, Document } from "../types"
    //import SettingsPage from "../SettingsPage.svelte";
    import DocumentCard from "./DocumentCard.svelte"
    import DocumentTable from "./DocumentTable.svelte"
    import TagManager from "./TagManager.svelte";
    import { 
        normalizeTag,
        setDocumentTags,
        deleteDocument,
        createCardField
    
    } from "../api"

    export let refreshKey: number
    export let viewMode: "grid" | "list" = "grid"
    export let columnCount = 5
    const dispatch = createEventDispatcher<{
        viewModeChange: { mode: "grid" | "list" }
        toggleSidebar: void
    }>()

    let documents: Document[] = []
    let search = ""
    let sortOrder: "date_asc" | "date_desc" | "name_asc" | "name_desc" = "date_desc"
    let tags: string[] = []
    let activeTag: string | null = null
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
        if (selectedIds.includes(id)) {
            selectedIds = selectedIds.filter(item => item !== id)
        } else {
            selectedIds = [...selectedIds, id]
        }
    }

    function setViewMode(mode: "grid" | "list") {
        viewMode = mode
        dispatch("viewModeChange", { mode })
    }

    function clearSelection() {
        selectedIds = []
    }

    async function bulkDelete() {
        if (!selectedIds.length) return

        const confirmed = confirm(`Удалить ${selectedIds.length} карточек?`)
        if (!confirmed) return

        await Promise.all(selectedIds.map(id => deleteDocument(id)))

        documents = documents.filter(doc => !selectedIds.includes(doc._id))
        clearSelection()
    }

    async function bulkAddTag() {

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
        tags = await getTags()
        const settings = await getSettings()
        customFieldSettings = settings.fields_for_cards ?? []
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

    function handleTagSelect(event: CustomEvent<{ tag: string | null }>) {
        activeTag = event.detail.tag
    }
    
    function handleTagsChanged(event: CustomEvent<{ tags: string[] }>) {
        tags = event.detail.tags
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
        const name = prompt("Название нового свойства")
        if (!name || !name.trim()) return

        const typePrompt = prompt("Тип свойства: text или number", "text")
        if (!typePrompt) return
        const normalizedType = typePrompt.trim().toLowerCase()
        if (normalizedType !== "text" && normalizedType !== "number") {
            alert("Поддерживаются только типы: text или number")
            return
        }

        try {
            await createCardField(name.trim(), normalizedType as "text" | "number")
            await load()
        } catch (error) {
            const message = error instanceof Error ? error.message : "Не удалось создать свойство"
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
        </div>
    </div>
</div>

<TagManager
    initialTags={tags}
    on:select={handleTagSelect}
    on:tagsChanged={handleTagsChanged}
/>


{#if selectedIds.length > 0}
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
{/if}




{#if viewMode === "grid"}
  {#if masonryFailed}
    <div class="grid-fallback">
      {#each sortedDocuments as doc (doc._id)}
        <DocumentCard
          {doc}
          search={search}
          selected={selectedIds.includes(doc._id)}
          selectionActive={selectedIds.length > 0}
          on:toggleSelect={() => toggleCardSelection(doc._id)}
          on:deleted={(e) => removeFromList(e.detail.id)}
          on:updated={(e) => replaceDocumentInList(e.detail.document)}
        />
      {/each}
    </div>
  {:else}
    <div class="masonry-grid" style={`--masonry-columns: ${Math.max(1, masonryColumns.length)};`}>
      {#each masonryColumns as column, index (index)}
        <div class="masonry-column">
          {#each column as doc (doc._id)}
            <DocumentCard
              {doc}
              search={search}
              selected={selectedIds.includes(doc._id)}
              selectionActive={selectedIds.length > 0}
              on:toggleSelect={() => toggleCardSelection(doc._id)}
              on:deleted={(e) => removeFromList(e.detail.id)}
              on:updated={(e) => replaceDocumentInList(e.detail.document)}
            />
          {/each}
        </div>
      {/each}
    </div>
  {/if}
{:else}
  <DocumentTable
    documents={sortedDocuments}
    {selectedIds}
    {customFieldSettings}
    {customFieldFilters}
    {openFilterField}
    {fieldUniqueTextValues}
    {isFieldFilterActive}
    {filenameFilterText}
    {filenameSort}
    {createdAtSort}
    {createdAtRange}
    {isFilenameFilterActive}
    {isCreatedAtFilterActive}
    on:toggleSelect={(e) => toggleCardSelection(e.detail.id)}
    on:addProperty={handleAddProperty}
    on:toggleFilterPanel={(e) => toggleFilterPanel(e.detail.fieldName)}
    on:setFilenameFilterText={(e) => setFilenameFilterText(e.detail.value)}
    on:setFilenameSort={(e) => setFilenameSort(e.detail.sort)}
    on:clearFilenameFilter={clearFilenameFilter}
    on:setCreatedAtSort={(e) => setCreatedAtSort(e.detail.sort)}
    on:setCreatedAtRange={(e) => setCreatedAtRange(e.detail.range)}
    on:clearCreatedAtFilter={clearCreatedAtFilter}
    on:setTextSort={(e) => setTextSort(e.detail.fieldName, e.detail.sort)}
    on:setNumberSort={(e) => setNumberSort(e.detail.fieldName, e.detail.sort)}
    on:toggleTextValue={(e) => toggleTextValue(e.detail.fieldName, e.detail.value)}
    on:selectAllTextValues={(e) => selectAllTextValues(e.detail.fieldName)}
    on:clearTextValues={(e) => clearTextValues(e.detail.fieldName)}
    on:setNumberOperator={(e) => setNumberOperator(e.detail.fieldName, e.detail.operator)}
    on:setNumberValue={(e) => setNumberValue(e.detail.fieldName, e.detail.key, e.detail.value)}
    on:clearFieldFilter={(e) => clearFieldFilter(e.detail.fieldName)}
    on:closeFilterPanel={() => openFilterField = null}
    on:deleted={(e) => removeFromList(e.detail.id)}
    on:updated={(e) => replaceDocumentInList(e.detail.document)}
  />
{/if}



<style>

.search-manager {
    padding: 10px 12px;
    margin-bottom: 16px;
    text-align: left;
}

@media (max-width: 640px) {
    .search-manager {
        padding: 8px;
        margin-bottom: 12px;
        text-align: left;
    }
}


.controls-row {
    display: flex;
    justify-content: left;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.compact-toolbar {
    gap: 6px;
}

.compact-search {
    min-width: min(340px, 100%);
    flex: 1 1 260px;
}

.sidebar-toggle-inline {
    width: 34px;
    min-width: 34px;
    height: 34px;
    padding: 0;
    border-radius: 10px;
    border-color: transparent;
    background: color-mix(in srgb, var(--surface), transparent 12%);
    color: var(--text-muted);
    line-height: 1;
}

.sidebar-toggle-inline:hover {
    background: color-mix(in srgb, var(--surface), var(--bg-accent) 45%);
    color: var(--text);
}

.sidebar-toggle-inline.active {
    color: var(--text);
}

.view-toggle {
    display: inline-flex;
    gap: 4px;
    align-items: center;
}

.view-toggle button {
    padding-inline: 0.7rem;
    min-height: 30px;
}

.view-toggle button.active {
    border-color: color-mix(in srgb, var(--primary), white 20%);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 75%);
    background: color-mix(in srgb, var(--surface), var(--primary) 10%);
}

@media (max-width: 640px) {
    .controls-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        text-align: center;
    }

    .my-input {
        flex: 0 1 auto;
        width: auto;
        min-width: 0;
    }
}






.bulk-actions-manager {
    padding: 14px;
    margin-bottom: 16px;
    text-align: left;
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
}

@media (max-width: 640px) {
    .bulk-actions-manager {
        padding: 8px;
        margin-bottom: 12px;
        text-align: left;
    }
}




/*

.grid {
    columns: 250px;
}

*/

.masonry-grid {
    display: grid;
    grid-template-columns: repeat(var(--masonry-columns), minmax(0, 1fr));
    gap: 10px;
    align-items: start;
}

.masonry-column {
    display: grid;
    gap: 10px;
    align-content: start;
}

.grid-fallback {
    display: grid;
    gap: 10px;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
}



</style>
