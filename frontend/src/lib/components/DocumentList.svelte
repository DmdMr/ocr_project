<script lang="ts">
    import { onMount } from "svelte"
    import { getDocuments, getTags } from "../api"
    import type { Document } from "../types"
    import DocumentCard from "./DocumentCard.svelte"
    import { updateDocument } from "../api"
    import TagManager from "./TagManager.svelte";
    import { UPLOADS_URL, API_URL} from "../api"

    export let refreshKey: number

    let documents: Document[] = []
    let search = ""
    let sortOrder: "asc" | "desc" = "desc"
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
        const matchesText =
            doc.filename.toLowerCase().includes(search.toLowerCase()) ||
            doc.recognized_text.toLowerCase().includes(search.toLowerCase())
        const matchesTag = !activeTag || doc.tags?.includes(activeTag)
        return matchesText && matchesTag
    })

  

    $: sortedDocuments = [...filtered].sort((a, b) => {
        const dateA = new Date(a.created_at).getTime()
        const dateB = new Date(b.created_at).getTime()
        return sortOrder === "asc" ? dateA - dateB : dateB - dateA
    })





</script>

<div class="controls-row">
    <input
        class="search-input"
        placeholder="Search documents"
        bind:value={search}
    />

    <select bind:value={sortOrder} class="sort-select">
        <option value="desc">Newest first</option>
        <option value="asc">Oldest first</option>
    </select>
</div>





<!--
<TagManager
    initialTags={tags}
    on:select={handleTagSelect}
    on:tagsChanged={handleTagsChanged}
/>
-->



<div class="grid">
    {#each sortedDocuments as doc}
        <DocumentCard
            {doc}
            on:deleted={(e) => removeFromList(e.detail.id)}
        />
    {/each}
</div>



<style>
.controls-row {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
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
