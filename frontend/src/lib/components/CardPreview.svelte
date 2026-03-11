<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte"
    import type { Document } from "../types"
    import { UPLOADS_URL, type ImageEditPayload } from "../api"
    import { tagHue } from "../tagColors"

    export let doc: Document
    export let editedText: string
    export let editing: boolean

    const dispatch = createEventDispatcher()

    let rotateDegrees = 0
    let cropX = 0
    let cropY = 0
    let cropWidth = 100
    let cropHeight = 100

    function close() {
        dispatch("close")
    }

    function save() {
        dispatch("save")
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

    function applyImageEdit() {
        const payload: ImageEditPayload = {
            rotate_degrees: rotateDegrees,
            crop: {
                x_percent: cropX,
                y_percent: cropY,
                width_percent: cropWidth,
                height_percent: cropHeight
            }
        }

        dispatch("imageEdit", payload)
    }

    function resetEditor() {
        rotateDegrees = 0
        cropX = 0
        cropY = 0
        cropWidth = 100
        cropHeight = 100
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

    const imageSrc = () => `${UPLOADS_URL}/${doc.filename}?v=${encodeURIComponent(doc.image_version ?? doc.created_at ?? "")}`

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
            <img src={imageSrc()} />
        </div>

        <div class="right">
            <div class="header">
                <h3>{doc.filename}</h3>
                <small>{new Date(doc.created_at).toLocaleString()}</small>
            </div>

            <div class="image-tools panel">
                <h4>Image editor</h4>
                <div class="row">
                    <label for="rotate-deg">Rotate (°)</label>
                    <input id="rotate-deg" type="number" step="90" min="-270" max="270" bind:value={rotateDegrees} />
                </div>
                <div class="crop-grid">
                    <label>X % <input type="number" min="0" max="100" bind:value={cropX} /></label>
                    <label>Y % <input type="number" min="0" max="100" bind:value={cropY} /></label>
                    <label>Width % <input type="number" min="1" max="100" bind:value={cropWidth} /></label>
                    <label>Height % <input type="number" min="1" max="100" bind:value={cropHeight} /></label>
                </div>
                <div class="tool-actions">
                    <button class="primary" on:click={applyImageEdit}>Apply image edit</button>
                    <button on:click={resetEditor}>Reset</button>
                </div>
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

        <button class="close" on:click={close}>✕</button>
    </div>
</div>

<style>
.overlay {
    position: fixed;
    inset: 0;
    background: rgba(10, 14, 20, 0.58);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.modal {
    background: color-mix(in srgb, var(--surface-elevated), transparent 8%);
    width: 92vw;
    height: 88vh;
    display: grid;
    grid-template-columns: minmax(320px, 1fr) minmax(440px, 1.2fr);
    border-radius: var(--radius-lg);
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
    object-fit: contain;
}

.right {
    display: grid;
    grid-template-rows: auto auto 1fr auto;
    gap: 10px;
    padding: 16px;
    overflow: hidden;
}

.image-tools {
    padding: 10px;
}

.image-tools h4 {
    margin: 0 0 8px;
}

.row {
    display: grid;
    grid-template-columns: 90px 1fr;
    gap: 8px;
    align-items: center;
    margin-bottom: 8px;
}

.crop-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
}

.crop-grid label {
    font-size: 0.82rem;
    color: var(--text-muted);
    display: grid;
    gap: 4px;
}

.crop-grid input,
.row input {
    min-height: 32px;
}

.tool-actions {
    margin-top: 10px;
    display: flex;
    gap: 8px;
    justify-content: flex-end;
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
