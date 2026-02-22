<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte"
    import type { Document } from "../types"

    export let doc: Document
    export let editedText: string
    export let editing: boolean

    const dispatch = createEventDispatcher()

    let leftWidth = 50 // percent
    let isDragging = false

    function startDrag() {
        isDragging = true
        window.addEventListener("mousemove", onDrag)
        window.addEventListener("mouseup", stopDrag)
    }

    function onDrag(e: MouseEvent) {
        if (!isDragging) return
        const newWidth = (e.clientX / window.innerWidth) * 100
        leftWidth = Math.min(80, Math.max(20, newWidth))
    }

    function stopDrag() {
        isDragging = false
        window.removeEventListener("mousemove", onDrag)
        window.removeEventListener("mouseup", stopDrag)
    }

    function close() {
        dispatch("close")
    }

    function save() {
        dispatch("save", { text: editedText })
    }

    function remove() {
        dispatch("delete")
    }

    function toggleEdit() {
        dispatch("editToggle")
    }
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="overlay" on:click={close}>
    <div class="modal" on:click|stopPropagation>

        <!-- LEFT IMAGE -->
        <div class="left">
            <!-- svelte-ignore a11y_missing_attribute -->
            <img src={`http://localhost:8000/uploads/${doc.filename}`} />
        </div>

        <!-- RIGHT CONTENT -->
        <div class="right">

            <!-- HEADER -->
            <div class="header">
                <h2>{doc.filename}</h2>
                <small>{new Date(doc.created_at).toLocaleString()}</small>

                {#if doc.tags}
                    <div class="tags">
                        {#each doc.tags as tag}
                            <span class="tag">{tag}</span>
                        {/each}
                    </div>
                {/if}
            </div>

            <!-- TEXT -->
            <div class="text">
                {#if editing}
                    <textarea bind:value={editedText}></textarea>
                {:else}
                    <p>{doc.recognized_text}</p>
                {/if}
            </div>

            <!-- FOOTER -->
            <div class="footer">
                {#if editing}
                    <button on:click={save}>Save</button>
                {:else}
                    <button on:click={toggleEdit}>Edit</button>
                {/if}
                <button on:click={remove}>Delete</button>
            </div>

        </div>

        <button class="close" on:click={close}>✕</button>
    </div>
</div>

<style>



.overlay {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.85);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal {
    background: var(--card);
    width: 90vw;
    height: 85vh;
    display: grid;
    grid-template-columns: 1fr 1.5fr;
    border-radius: 12px;
    overflow: hidden;
    position: relative;
}

.left {
    overflow: auto;       /* allow scroll */
    display: flex;
    justify-content: center;
    align-items: flex-start;  /* important */
    padding: 20px;
    background: #000;
}

.left img {
    width: auto;
    height: auto;
    max-width: 100%;
    max-height: none;
    object-fit: contain;
}

.right {
    display: grid;
    grid-template-rows: auto 1fr auto;
    padding: 20px;
}

.text {
    overflow-y: auto;
}

.text textarea {
    width: 100%;
    height: 100%;
    resize: none;
}

.footer {
    display: flex;
    justify-content: flex-end;
    gap: 10px;
}

.close {
    position: absolute;
    top: 15px;
    right: 20px;
    font-size: 24px;
    background: none;
    border: none;
    cursor: pointer;
}

    
</style>