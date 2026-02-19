<script lang="ts">
    import { createEventDispatcher } from "svelte"
    import type { Document } from "../types"
    import { deleteDocument } from "../api"
    import { updateDocument } from "../api"
    import ImagePreview from "./ImagePreview.svelte"

    let showPreview = false

    export let doc: Document

    let editing = false
    let editedText = doc.recognized_text

    async function save() {
        await updateDocument(doc._id, editedText)

        doc.recognized_text = editedText  // ← THIS LINE FIXES IT

        editing = false
    }

    let activeTag: string | null = null;
    let searchQuery = "";

    //import { createEventDispatcher } from "svelte"

    

    type DocumentCardEvents = {
        deleted: { id: string },
        tagClick: { tag: string }
    }

    const dispatch = createEventDispatcher<DocumentCardEvents>()

    function handleTagClick(tag: string) {
        dispatch("tagClick", { tag })
    }


    async function remove() {
        await deleteDocument(doc._id)
        dispatch("deleted", { id: doc._id })
    }

    let addingTag = false
    let newTag = ""
    
    async function addTag() {
        if (!newTag.trim()) return

        const updatedTags = [...(doc.tags ?? []), newTag.trim()]

        await updateDocument(doc._id, {
            tags: updatedTags
        })

        doc.tags = updatedTags

        newTag = ""
        addingTag = false
    }



</script>


<div class="card">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <img
        src={`http://localhost:8000/uploads/${doc.filename}`}
        alt=""
        on:click={() => showPreview = true}
    />


    <h3>{doc.filename}</h3>

    <small>{new Date(doc.created_at).toLocaleString()}</small>

    <div class="edit-buttons">
        {#if editing}
            <!-- svelte-ignore element_invalid_self_closing_tag -->
            <textarea
                bind:value={editedText}
            />

            <button on:click={save}>Save</button>
        {:else}
            <p class="text-preview">
                {doc.recognized_text}
            </p>
            <button on:click={() => editing = true}>Edit</button>
        {/if}


        <button class="delete" on:click={remove}>
            Delete
        </button>
    </div>

        {#if showPreview}
        <ImagePreview
            imageUrl={`http://localhost:8000/uploads/${doc.filename}`}
            on:close={() => showPreview = false}
        />
    {/if}
        <!-- TAGS DISPLAY -->
    {#if doc.tags && doc.tags.length > 0}
        <div class="tags">
            {#each doc.tags as tag}
                <span class="tag">{tag}</span>
            {/each}
        </div>
    {/if}

    <!-- ADD TAG -->
    {#if addingTag}
        <div class="add-tag">
            <input
                bind:value={newTag}
                placeholder="Enter tag"
                on:keydown={(e) => e.key === "Enter" && addTag()}
            />
            <button on:click={addTag}>Save</button>
        </div>
    {:else}
        <button class="add-tag-btn" on:click={() => addingTag = true}>
            + Add tag
        </button>
    {/if}




</div>



<style>
.card {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    background: white;
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    break-inside: avoid;
    margin-bottom: 20px;
}



img {
    width: 100%;
    border-radius: 6px;
    margin-bottom: 5px;
}

h3 {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}

.text-preview {
    display: -webkit-box;
    -webkit-line-clamp: 4;
    -webkit-box-orient: vertical;
    overflow: hidden;

    line-height: 1.4;
    min-height: calc(1.4em * 4);

    margin: 0;
}


button {
    margin-top: auto;
    padding: 6px 12px;
    border-radius: 6px;
    border: none;
    cursor: pointer;
    margin-bottom: 10px;
}

.delete {
    background: #d9534f;
    color: white;
}

textarea {
    width: 100%;
    resize: vertical;      /* allow manual vertical resize */
    overflow-y: auto;      /* allow scroll inside */
    overflow-x: hidden;

    line-height: 1.4;

    min-height: calc(1.4em * 4);   /* minimum 4 rows */
    max-height: 300px;            /* stops infinite growth */

    border-radius: 6px;
    padding: 8px;
    font: inherit;
}


.edit-buttons {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
  margin-bottom: 0px;
}

.edit-buttons button,
.edit-buttons textarea {
  width: 100%;
  margin: 0;
  box-sizing: border-box;
}

.tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    margin: 6px 0 4px 0;
}

.tag {
    background: #eef2ff;
    color: #3730a3;
    padding: 4px 8px;
    border-radius: 20px;
    font-size: 12px;
    cursor: pointer;
    border: none;           /* buttons have default borders */
    outline: none;          /* optional: remove default outline */
    transition: 0.15s;
}

.tag:hover,
.tag:focus {
    background: #c7d2fe;
    outline: none;
}

.add-tag {
    display: flex;
    gap: 6px;
    margin-top: 6px;
}

.add-tag input {
    flex: 1;
    padding: 4px 8px;
    border-radius: 6px;
    border: 1px solid #ddd;
}

.add-tag-btn {
    margin-top: 6px;
    font-size: 12px;
    background: #f3f4f6;
}


</style>
