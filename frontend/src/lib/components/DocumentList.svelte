<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte"
    import { getDocuments, getSettings, getTags } from "../api"
    import type { CardCustomFieldSetting, Document } from "../types"
    import DocumentCard from "./DocumentCard.svelte"
    import DocumentTable from "./DocumentTable.svelte"
    import TagManager from "./TagManager.svelte";
    import { 
        normalizeTag,
        setDocumentTags,
        deleteDocument
    
    } from "../api"

    export let refreshKey: number
    export let viewMode: "grid" | "list" = "grid"
    export let columnCount = 5
    const dispatch = createEventDispatcher<{ viewModeChange: { mode: "grid" | "list" } }>()

    let documents: Document[] = []
    let search = ""
    let sortOrder: "date_asc" | "date_desc" | "name_asc" | "name_desc"
    let tags: string[] = []
    let activeTag: string | null = null
    let selectedIds: string[] = []
    let customFieldSettings: CardCustomFieldSetting[] = []
    let openFilterField: string | null = null

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
        const matchesText =
            displayName.toLowerCase().includes(search.toLowerCase()) ||
            doc.filename.toLowerCase().includes(search.toLowerCase()) ||
            doc.recognized_text.toLowerCase().includes(search.toLowerCase()) ||
            doc.tags?.some(tag => tag.toLowerCase().includes(search.toLowerCase()))
        const matchesTag = !activeTag || doc.tags?.includes(activeTag)
        if (!matchesText || !matchesTag) return false

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
    <div class="controls-row">
        <input
            type="text"
            class="my-input"
            placeholder="Поиск документов"
            bind:value={search}
        />

        <select bind:value={sortOrder} class="sort-select">
            <option value="date_desc">Сначала новые</option>
            <option value="date_asc">Сначала старые</option> 
            <option value="name_asc">Имя (A–Z)</option>
            <option value="name_desc">Имя (Z–A)</option>
        </select>

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

{#if customFieldSettings.length}
<div class="panel custom-filters-panel">
    <div class="custom-filters-header">Фильтры по полям карточки</div>
    <div class="custom-filter-buttons">
        {#each customFieldSettings as field}
            <div class="field-filter-item">
                <button
                    class="field-filter-trigger"
                    class:active={isFieldFilterActive(field.name)}
                    on:click={() => toggleFilterPanel(field.name)}
                >
                    {field.name}
                    <span class="filter-icon">▾</span>
                </button>

                {#if openFilterField === field.name}
                    <div class="field-filter-popup">
                        {#if field.type === "text"}
                            <div class="popup-row">
                                <button class="secondary" on:click={() => setTextSort(field.name, "asc")}>A-Z</button>
                                <button class="secondary" on:click={() => setTextSort(field.name, "desc")}>Z-A</button>
                                <button class="secondary" on:click={() => setTextSort(field.name, "none")}>Без сорт.</button>
                            </div>
                            <div class="popup-row">
                                <button class="secondary" on:click={() => selectAllTextValues(field.name)}>Выбрать все</button>
                                <button class="secondary" on:click={() => clearTextValues(field.name)}>Очистить</button>
                            </div>
                            <div class="popup-values">
                                {#each fieldUniqueTextValues(field.name) as value}
                                    <label class="popup-checkbox">
                                        <input
                                            type="checkbox"
                                            checked={customFieldFilters[field.name]?.mode === "text" && customFieldFilters[field.name].selectedValues.includes(value)}
                                            on:change={() => toggleTextValue(field.name, value)}
                                        />
                                        <span>{value}</span>
                                    </label>
                                {/each}
                            </div>
                        {:else}
                            <div class="popup-row">
                                <button class="secondary" on:click={() => setNumberSort(field.name, "asc")}>0-9</button>
                                <button class="secondary" on:click={() => setNumberSort(field.name, "desc")}>9-0</button>
                                <button class="secondary" on:click={() => setNumberSort(field.name, "none")}>Без сорт.</button>
                            </div>
                            <div class="popup-row">
                                <select
                                    value={customFieldFilters[field.name]?.mode === "number" ? customFieldFilters[field.name].operator : "none"}
                                    on:change={(event) => {
                                        const target = event.target as HTMLSelectElement
                                        setNumberOperator(field.name, target.value as NumberFilter["operator"])
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
                                        setNumberValue(field.name, "value1", target.value)
                                    }}
                                />
                                {#if customFieldFilters[field.name]?.mode === "number" && customFieldFilters[field.name].operator === "between"}
                                    <input
                                        type="number"
                                        placeholder="И до"
                                        value={customFieldFilters[field.name]?.mode === "number" ? customFieldFilters[field.name].value2 : ""}
                                        on:input={(event) => {
                                            const target = event.target as HTMLInputElement
                                            setNumberValue(field.name, "value2", target.value)
                                        }}
                                    />
                                {/if}
                            </div>
                        {/if}
                        <div class="popup-row">
                            <button class="secondary" on:click={() => clearFieldFilter(field.name)}>Сбросить</button>
                            <button class="primary" on:click={() => openFilterField = null}>Готово</button>
                        </div>
                    </div>
                {/if}
            </div>
        {/each}
    </div>
</div>
{/if}




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
    on:toggleSelect={(e) => toggleCardSelection(e.detail.id)}
    on:deleted={(e) => removeFromList(e.detail.id)}
    on:updated={(e) => replaceDocumentInList(e.detail.document)}
  />
{/if}



<style>

.search-manager {
    padding: 14px;
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
    gap: 10px;
    flex-wrap: wrap;
}

.view-toggle {
    display: inline-flex;
    gap: 6px;
    align-items: center;
}

.view-toggle button.active {
    border-color: color-mix(in srgb, var(--primary), white 20%);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 75%);
    background: color-mix(in srgb, var(--surface), var(--primary) 10%);
}

.custom-filters-panel {
    margin-bottom: 16px;
    text-align: left;
    padding: 12px;
}

.custom-filters-header {
    font-weight: 600;
    margin-bottom: 8px;
}

.custom-filter-buttons {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.field-filter-item {
    position: relative;
}

.field-filter-trigger {
    display: inline-flex;
    align-items: center;
    gap: 6px;
}

.field-filter-trigger.active {
    border-color: color-mix(in srgb, var(--primary), white 20%);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 75%);
}

.filter-icon {
    font-size: 0.75rem;
    color: var(--text-muted);
}

.field-filter-popup {
    position: absolute;
    top: calc(100% + 6px);
    left: 0;
    z-index: 20;
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
    max-height: 150px;
    overflow: auto;
    padding-right: 2px;
}

.popup-checkbox {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 0.9rem;
}

.number-inputs input {
    width: 100%;
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



.sort-select {
    min-height: 42px;
}





</style>
