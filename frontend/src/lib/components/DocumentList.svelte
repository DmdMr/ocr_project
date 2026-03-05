<script lang="ts">
    import { onMount } from "svelte"
    import { getDocuments } from "../api"
    import type { Document } from "../types"
    import DocumentCard from "./DocumentCard.svelte"
    import { updateDocument } from "../api"
    import {createTag } from "../api"

    export let refreshKey: number

    let documents: Document[] = []



    async function load() {
        documents = await getDocuments()
        const response = await fetch("http://localhost:8000/api/tags")
        const data = await response.json()

        // Ensure you're correctly receiving the tags and assigning them to the 'tags' array
        if (data && data.tags) {
            tags = data.tags
        } else {
            console.error("Error fetching tags:", data);
        }
    }

    function removeFromList(id: string) {
        documents = documents.filter(doc => doc._id !== id)
    }

 

    let tags: string[] = []  // Store all tags fetched from the backend
    let newGlobalTag = ""  // Bind the input field for the new tag

    async function createNewTag() {
        if (!newGlobalTag.trim()) return;

        // Check if the tag already exists
        if (tags.includes(newGlobalTag.trim())) {
            console.log('Tag already exists');
            return;
        }

        // Make a POST request to add the new tag to the backend
        const response = await fetch('http://localhost:8000/api/tags', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ tag: newGlobalTag.trim() })
        });

        if (response.ok) {
            const data = await response.json();

            console.log('Tag added:', data);  // Log the backend response to ensure it's correct

            // If tag was added successfully, update tags in the frontend
            tags = [...tags, newGlobalTag.trim()]; // Ensure the tags are updated reactively

            newGlobalTag = ""; // Clear the input field
        } else {
            console.error('Failed to create tag');
        }
    }

    onMount(async () => {
        await load();  // Fetch and load tags initially

        // Optionally listen for new tags added and reload
        const savedTags = localStorage.getItem("tags");
        if (savedTags) {
            tags = JSON.parse(savedTags);
        }
    });

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





<div class="tags">

    <div class="tags-list">
        {#each tags as tag}
            <button class="tag-button" on:click={() => handleTagClick(tag)}>{tag}</button>
        {/each}
    </div>
    <div>
        <input type="text" bind:value={newGlobalTag} placeholder="Enter new tag" />
        <button on:click={createNewTag}>Create Tag</button>
    </div>
</div>




<div class="grid">
    {#each filteredDocuments as doc}
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
