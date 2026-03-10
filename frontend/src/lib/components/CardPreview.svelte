<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte"
    import type { Document } from "../types"
    import { tagHue } from "../tagColors"

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
    function addTag() {
        dispatch("addTag")
    }

    function removeTag() {
        dispatch("removeTag")
    }

    function selectTag(tag: string) {
        dispatch("tagClick", { tag })
    }

    function handleKey(e: KeyboardEvent) {
        if (e.key === "Escape") close()
    }

    function portal(node: HTMLElement) {
        const target = document.body
        target.appendChild(node)

        return {
            destroy() {
                if (node.parentNode) node.parentNode.removeChild(node)
            }
        }
    }

    onMount(() => {
        window.addEventListener("keydown", handleKey)
        return () => window.removeEventListener("keydown", handleKey)
    })
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="overlay" use:portal on:click={close}>
    <div class="modal" on:click|stopPropagation>

        <div class="left">
            <!-- svelte-ignore a11y_missing_attribute -->
            <img src={`http://localhost:8000/uploads/${doc.filename}`} />
        </div>

        <div class="right">

            <div class="header">
                <h3>{doc.filename}</h3>
                <small>{new Date(doc.created_at).toLocaleString()}</small>

                
            </div>

            <div class="text">
                {#if editing}
                    <textarea bind:value={editedText}></textarea>
                {:else}
                    <p>{doc.recognized_text}</p>
                {/if}
            </div>

            <div class="footer">
                <div class="tags">
                    {#if doc.tags?.length}
                        {#each doc.tags as tag}
                            <button class="tag tag-colored" style={`--tag-hue: ${tagHue(tag)}`} on:click={() => selectTag(tag)}>{tag}</button>
                        {/each}
                    {:else}
                        <span class="empty-tags">No tags</span>
                    {/if}
                </div>

                <div class="actions">
                    <button on:click={addTag}>Add Tag</button>
                    <button on:click={removeTag}>Remove Tag</button>
                    {#if editing}
                        <button on:click={save}>Save</button>
                    {:else}
                        <button on:click={toggleEdit}>Edit</button>
                    {/if}
                    <button class="delete" on:click={remove}>Delete</button>
                </div>
            </div>



            </div>

        </div>

        <button class="close" on:click={close}>✕</button>
    </div>


<style>



.overlay {
    position: fixed;
    inset: 0;
    background: rgba(10, 14, 20);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal {
    background: color-mix(in srgb, var(--surface-elevated), transparent 8%);
    width: 90vw;
    height: 85vh;
    display: grid;
    grid-template-columns: 1fr 1.5fr;
    border-radius: 12px;
    overflow: hidden;
    position: relative;
}

.left {
    overflow: auto;       
    display: flex;
    justify-content: center;
    align-items: flex-start;  
    padding: 20px;
    background: color-mix(in srgb, var(--surface-elevated), black 40%);
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
    background: var(--surface);
}

.footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}

.tags {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
}

.tag {
    border-radius: 999px;
    padding: 6px 10px;
}

.empty-tags {
    opacity: 0.72;
}

.actions {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
    justify-content: flex-end;
}

.close {
    position: absolute;
    top: 15px;
    right: 20px;
    font-size: 24px;
    background: transparent;
    border: 1px solid transparent;
    cursor: pointer;
    color: var(--text);
    box-shadow: none;
}

.close:hover {
    background: var(--surface);
}
    
</style>