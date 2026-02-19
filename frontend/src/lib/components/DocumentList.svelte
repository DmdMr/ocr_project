<script lang="ts">
    import { onMount } from "svelte"
    import { getDocuments } from "../api"
    import type { Document } from "../types"
    import DocumentCard from "./DocumentCard.svelte"
    import { updateDocument } from "../api"

    export let refreshKey: number

    let documents: Document[] = []

    async function load() {
        documents = await getDocuments()
    }

    function removeFromList(id: string) {
        documents = documents.filter(doc => doc._id !== id)
    }

    onMount(load)

    $: if (refreshKey) {
        load()
    }

    let search = ""

    $: filtered = documents.filter(doc =>
        doc.filename.toLowerCase().includes(search.toLowerCase()) ||
        doc.recognized_text.toLowerCase().includes(search.toLowerCase())
    )

    let sortOrder: "asc" | "desc" = "desc"

    $: sortedDocuments = [...filtered].sort((a, b) => {
    const dateA = new Date(a.created_at).getTime()
    const dateB = new Date(b.created_at).getTime()

    return sortOrder === "asc"
        ? dateA - dateB
        : dateB - dateA
    })

    let activeTag: string | null = null;
    let searchQuery = "";

    function handleTagClick(tag: string) {
        activeTag = tag
    }

    $: filteredDocuments = sortedDocuments.filter(doc =>
        (!activeTag || doc.tags?.includes(activeTag)) &&
        (!searchQuery || 
            doc.filename?.toLowerCase().includes(searchQuery.toLowerCase()) ||
            doc.recognized_text?.toLowerCase().includes(searchQuery.toLowerCase())
        )
    );
    

    $: documents.forEach(doc => console.log(doc.filename, doc.tags))

    let newGlobalTag = ""
    let addingGlobalTag = false

    async function addTagToDoc(docId: string) {
    if (!newGlobalTag.trim()) return

    const doc = documents.find(d => d._id === docId)
        if (!doc) return

        const updatedTags = [...(doc.tags ?? []), newGlobalTag.trim()]

        const updated = await updateDocument(docId, {
            tags: updatedTags
        })

        documents = documents.map(d =>
            d._id === docId ? updated : d
        )

        newGlobalTag = ""
        addingGlobalTag = false
    }


    
    let activeDocId: string | null = null




</script>

<input
    class="search-input"
    placeholder="Search..."
    bind:value={search}
/>

<select bind:value={sortOrder} class="sort-select">
    <option value="desc">Newest first</option>
    <option value="asc">Oldest first</option>
</select>


<div class="top-bar">
    <input
        type="text"
        bind:value={searchQuery}
        placeholder="Search..."
    />

    {#if addingGlobalTag}
        <input
            bind:value={newGlobalTag}
            placeholder="New tag"
            on:keydown={(e) => e.key === "Enter" && addTagToDoc(activeDocId)}
        />
        <button on:click={() => addTagToDoc(activeDocId)}>Save</button>
    {:else}
        <button on:click={() => addingGlobalTag = true}>
            + Tag
        </button>
    {/if}
</div>





{#if activeTag}
    <div class="active-tag">
        Filtering by: {activeTag}
        <button on:click={() => activeTag = null}>×</button>
    </div>
{/if}



<div class="grid">
    {#each filteredDocuments as doc}
        <DocumentCard
            {doc}
            on:deleted={(e) => removeFromList(e.detail.id)}
            on:tagClick={(e) => activeTag = e.detail.tag}
        />
    {/each}
</div>



<style>
    
.grid {
    column-count: 4;
    column-gap: 20px;
    width: 100%;
}

@media (max-width: 1400px) {
    .grid { column-count: 3; }
}

@media (max-width: 1000px) {
    .grid { column-count: 2; }
}

@media (max-width: 600px) {
    .grid { column-count: 1; }
}



.search-input {
    padding: 10px 16px;
    border-radius: 8px;
    border: none;
    background: #2d6cdf;
    color: white;
    margin-bottom: 20px;
    width: 250px;
}

.search-input::placeholder {
    color: rgba(255,255,255,0.7);
}

.sort-select {
    padding: 8px 14px;
    border-radius: 8px;
    border: 1px solid #ccc;
    background: white;
}


</style>
