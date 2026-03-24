<script lang="ts">
    import { onMount } from "svelte"
    import { getDocuments, getTags } from "../api"
    import type { Document } from "../types"
    import DocumentCard from "./DocumentCard.svelte"
    import DocumentRow from "./DocumentRow.svelte"
    import { updateDocument } from "../api"
    import TagManager from "./TagManager.svelte";
    import { 
        UPLOADS_URL, 
        API_URL,
        normalizeTag,
        setDocumentTags,
        deleteDocument
    
    } from "../api"
    import LifeguardHelp from "./LifeguardHelp.svelte"

    export let refreshKey: number
    export let viewMode: "grid" | "list" = "grid"
    export let columnCount = 5

    let documents: Document[] = []
    let search = ""
    let sortOrder: "date_asc" | "date_desc" | "name_asc" | "name_desc"
    let tags: string[] = []
    let activeTag: string | null = null
    let selectedIds: string[] = []

    console.log(selectedIds);

    function isSelected(id: string) {
        return selectedIds.includes(id)
    }


    function toggleCardSelection(id: string) {
        if (selectedIds.includes(id)) {
            selectedIds = selectedIds.filter(item => item !== id)
        } else {
            selectedIds = [...selectedIds, id]
        }
        console.log(selectedIds);
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
        const response = await fetch(`${API_URL}/tags`)
        const data = await response.json()
        tags = await getTags()
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




    onMount(load)

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
        return matchesText && matchesTag
    })


    $: sortedDocuments = [...filtered].sort((a, b) => {
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





</script>


<div class="search-manager panel">
    <div class="controls-row">
        <input
            type="text"
            placeholder="Поиск документов"
            bind:value={search}
        />

        <select bind:value={sortOrder} class="sort-select">
            <option value="date_desc">Сначала новые</option>
            <option value="date_asc">Сначала старые</option> 
            <option value="name_asc">Имя (A–Z)</option>
            <option value="name_desc">Имя (Z–A)</option>
        </select>
    </div>
</div>


<!--
<div class="grid">
    {#each sortedDocuments as doc (doc._id)}
        <DocumentCard
            {doc}
            search = {search}
            on:deleted={(e) => removeFromList(e.detail.id)}
            on:updated={(e) => replaceDocumentInList(e.detail.document)}
        />
    {/each}
</div>

-->



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
<div class="grid" style={`--column-count: ${columnCount};`}>
    {#each sortedDocuments as doc (doc._id)}
      <DocumentCard
        {doc}
        search={search}
        //selected={isSelected(doc._id)}
        selected={selectedIds.includes(doc._id)}
        selectionActive={selectedIds.length > 0}
        on:toggleSelect={() => toggleCardSelection(doc._id)}
        on:deleted={(e) => removeFromList(e.detail.id)}
        on:updated={(e) => replaceDocumentInList(e.detail.document)}
      />
    {/each}
  </div>
{:else}
  <div class="list-view">
    {#each sortedDocuments as doc (doc._id)}
      <DocumentRow
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

.grid {
  column-count: var(--column-count);
  column-gap: 1em;
}

@media (min-width: 320px) {
    .grid{
        column-count: 2;
    }    
}


@media (min-width: 480px) {
    .grid{
        column-count: 3;
    }    
}

@media (min-width: 640px) {
    .grid{
        column-count: 4;
    }    
}

@media (min-width: 1024px) {
    .grid{
        column-count: 5;
    }    
}






.sort-select {
    
    min-width: 180px;
    min-height: 42px;
}





</style>
