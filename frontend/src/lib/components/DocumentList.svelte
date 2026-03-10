<script lang="ts">
    import { onMount } from "svelte"
    import { getDocuments, getTags } from "../api"
    import type { Document } from "../types"
    import DocumentCard from "./DocumentCard.svelte"
    import { updateDocument } from "../api"
    import TagManager from "./TagManager.svelte";

    export let refreshKey: number

    let documents: Document[] = []
    let search = ""
    let sortOrder: "asc" | "desc" = "desc"
    let tags: string[] = []
    let activeTag: string | null = null



    async function load() {
        documents = await getDocuments()
        const response = await fetch("http://localhost:8000/api/tags")
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

<input
    class="search-input"
    placeholder="Search documents"
    bind:value={search}
/>

<select bind:value={sortOrder} class="sort-select">
    <option value="desc">Newest first</option>
    <option value="asc">Oldest first</option>
</select>





<TagManager
    initialTags={tags}
    on:select={handleTagSelect}
    on:tagsChanged={handleTagsChanged}
/>




<div class="grid">
    {#each sortedDocuments as doc}
        <DocumentCard
            {doc}
            on:deleted={(e) => removeFromList(e.detail.id)}
        />
    {/each}
</div>



<style>
    
.grid {
  column-count: 6;
  column-gap: 1em;
}



.search-input {
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

.tags{
    margin-bottom: 20px;
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

.tag-button {
    display: inline-block;
    background-color: blue;
    padding: 10px;
    border-radius: 5px;
    cursor: pointer;
    color: white;
    transition: background-color 0.3s ease;
}
</style>
