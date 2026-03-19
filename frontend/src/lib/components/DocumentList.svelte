<script lang="ts">
    import { onMount } from "svelte"
    import { getDocuments, getTags } from "../api"
    import type { Document } from "../types"
    import DocumentCard from "./DocumentCard.svelte"
    import DocumentRow from "./DocumentRow.svelte"
    import { updateDocument } from "../api"
    import TagManager from "./TagManager.svelte";
    import { UPLOADS_URL, API_URL} from "../api"
    import LifeguardHelp from "./LifeguardHelp.svelte"

    export let refreshKey: number
    export let viewMode: "grid" | "list" = "grid"

    let documents: Document[] = []
    let search = ""
    let sortOrder: "date_asc" | "date_desc" | "name_asc" | "name_desc"
    let tags: string[] = []
    let activeTag: string | null = null

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
            doc.recognized_text.toLowerCase().includes(search.toLowerCase())
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
            <option value="name_asc">Имя (A–Z)</option>
            <option value="name_desc">Имя (Z–A)</option>
            <option value="date_desc">Сначала новые</option>
            <option value="date_asc">Сначала старые</option>
            
        </select>
    </div>

    
</div>






<TagManager
    initialTags={tags}
    on:select={handleTagSelect}
    on:tagsChanged={handleTagsChanged}
/>


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


{#if viewMode === "grid"}
  <div class="grid">
    {#each sortedDocuments as doc (doc._id)}
      <DocumentCard
        {doc}
        search={search}
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


.controls-row {
    display: flex;
    justify-content: left;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}



.grid {
  column-count: 2;
  column-gap: 1em;
}

@media (min-width: 600px) {
    .grid{
        column-count: 3;
    }    
}

@media (min-width: 1024px) {
    .grid{
        column-count: 5;
    }    
}


.search-input {
    width: min(560px, 100%);
    min-height: 42px;
    padding: 0.58rem 0.92rem;
    border-radius: 14px;
    border-color: color-mix(in srgb, var(--border-strong), var(--primary) 20%);
    box-shadow:
      inset 0 1px 0 color-mix(in srgb, white, transparent 35%),
      0 8px 24px color-mix(in srgb, var(--primary), transparent 88%);
}

.search-input::placeholder {
    color: color-mix(in srgb, var(--text-muted), transparent 12%);
}


.sort-select {
    
    min-width: 180px;
    min-height: 42px;
}


.search-input {
    width: 250px;
}


</style>
