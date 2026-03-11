<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte"
    import type { Document } from "../types"
    import { tagHue } from "../tagColors"
    import { UPLOADS_URL, type ImageEditPayload } from "../api"

    export let doc: Document
    export let editedText: string
    export let editing: boolean

    const dispatch = createEventDispatcher()

    let leftWidth = 50 // percent
    let isDragging = false


    type EditTool = "crop" | "rotate"

    let imageEditOpen = false
    let activeTool: EditTool = "crop"
    let previewRotation = 0

    let imageEl: HTMLImageElement | null = null
    let imageStageEl: HTMLDivElement | null = null

    let isDrawingCrop = false
    let cropStartX = 0
    let cropStartY = 0
    let cropRect: { x: number; y: number; width: number; height: number } | null = null

    let isRotating = false
    let rotateStartX = 0
    let rotateBase = 0


    function startImageEdit() {
        imageEditOpen = true
        activeTool = "crop"
        previewRotation = 0
        cropRect = null
    }

    function cancelImageEdit() {
        imageEditOpen = false
        previewRotation = 0
        cropRect = null
        isDrawingCrop = false
        isRotating = false
    }

    function setTool(tool: EditTool) {
        activeTool = tool
        if (tool === "rotate") {
            cropRect = null
        } else {
            previewRotation = 0
        }
    }

    function getStageCoords(event: MouseEvent) {
        if (!imageEl || !imageStageEl) return null

        const imageRect = imageEl.getBoundingClientRect()
        const stageRect = imageStageEl.getBoundingClientRect()

        const clampedX = Math.min(Math.max(event.clientX, imageRect.left), imageRect.right)
        const clampedY = Math.min(Math.max(event.clientY, imageRect.top), imageRect.bottom)

        const relativeX = clampedX - imageRect.left
        const relativeY = clampedY - imageRect.top

        return {
            x: relativeX,
            y: relativeY,
            width: imageRect.width,
            height: imageRect.height,
            offsetLeft: imageRect.left - stageRect.left,
            offsetTop: imageRect.top - stageRect.top
        }
    }

    function onEditorMouseDown(event: MouseEvent) {
        if (!imageEditOpen) return

        if (activeTool === "crop") {
            const point = getStageCoords(event)
            if (!point) return

            isDrawingCrop = true
            cropStartX = point.x
            cropStartY = point.y
            cropRect = {
                x: point.offsetLeft + point.x,
                y: point.offsetTop + point.y,
                width: 0,
                height: 0
            }
            return
        }

        isRotating = true
        rotateStartX = event.clientX
        rotateBase = previewRotation
    }

    function onEditorMouseMove(event: MouseEvent) {
        if (!imageEditOpen) return

        if (activeTool === "crop" && isDrawingCrop) {
            const point = getStageCoords(event)
            if (!point) return

            const left = Math.min(cropStartX, point.x)
            const top = Math.min(cropStartY, point.y)
            const width = Math.abs(point.x - cropStartX)
            const height = Math.abs(point.y - cropStartY)

            cropRect = {
                x: point.offsetLeft + left,
                y: point.offsetTop + top,
                width,
                height
            }
            return
        }

        if (activeTool === "rotate" && isRotating) {
            const deltaX = event.clientX - rotateStartX
            previewRotation = rotateBase + deltaX * 0.4
        }
    }

    function stopEditorInteraction() {
        isDrawingCrop = false
        isRotating = false
    }

    function saveImageEdit() {
        let payload: ImageEditPayload | null = null

        if (activeTool === "rotate") {
            const normalized = Math.round(previewRotation)
            if (normalized === 0) {
                cancelImageEdit()
                return
            }

            payload = { rotate_degrees: normalized }
        }

        if (activeTool === "crop") {
            if (!cropRect || !imageEl || !imageStageEl) {
                return
            }

            const imageRect = imageEl.getBoundingClientRect()
            const stageRect = imageStageEl.getBoundingClientRect()

            const x = cropRect.x - (imageRect.left - stageRect.left)
            const y = cropRect.y - (imageRect.top - stageRect.top)

            const xPercent = (x / imageRect.width) * 100
            const yPercent = (y / imageRect.height) * 100
            const widthPercent = (cropRect.width / imageRect.width) * 100
            const heightPercent = (cropRect.height / imageRect.height) * 100

            if (widthPercent < 1 || heightPercent < 1) {
                return
            }

            payload = {
                crop: {
                    x_percent: Math.max(0, Math.min(100, xPercent)),
                    y_percent: Math.max(0, Math.min(100, yPercent)),
                    width_percent: Math.max(0.1, Math.min(100, widthPercent)),
                    height_percent: Math.max(0.1, Math.min(100, heightPercent))
                }
            }
        }

        if (payload) {
            dispatch("imageEdit", payload)
        }

        cancelImageEdit()
    }


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
        if (e.key === "Escape") {
            if (imageEditOpen) {
                cancelImageEdit()
                return
            }
            close()
        }
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

    const imageSrc = () => `${UPLOADS_URL}/${doc.filename}?v=${encodeURIComponent(doc.image_version ?? doc.created_at ?? "")}`
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<!-- svelte-ignore a11y_click_events_have_key_events -->
<div class="overlay" use:portal on:click={close}>
    <div class="modal" on:click|stopPropagation>

        <div class="left">
            <!-- svelte-ignore a11y_missing_attribute -->
            <div
                class:editing={imageEditOpen}
                bind:this={imageStageEl}
                class="image-stage"
                on:mousedown={onEditorMouseDown}
                on:mousemove={onEditorMouseMove}
                on:mouseup={stopEditorInteraction}
                on:mouseleave={stopEditorInteraction}
            >
                <!-- svelte-ignore a11y_missing_attribute -->
                <img bind:this={imageEl} src={imageSrc()} style={`transform: rotate(${imageEditOpen && activeTool === 'rotate' ? previewRotation : 0}deg);`} />

                {#if imageEditOpen && activeTool === "crop" && cropRect}
                    <div
                        class="crop-box"
                        style={`left:${cropRect.x}px; top:${cropRect.y}px; width:${cropRect.width}px; height:${cropRect.height}px;`}
                    ></div>
                {/if}
            </div>
        </div>

        <div class="right">

            <div class="header">
                <h3>{doc.filename}</h3>
                <small>{new Date(doc.created_at).toLocaleString()}</small>

                
            </div>

            {#if !imageEditOpen}
                    <button class="primary" on:click={startImageEdit}>Edit image</button>
                {:else}
                    <div class="tool-switch">
                        <button class:active={activeTool === "crop"} on:click={() => setTool("crop")}>Crop</button>
                        <button class:active={activeTool === "rotate"} on:click={() => setTool("rotate")}>Rotate</button>
                    </div>
                    <p class="tool-hint">
                        {#if activeTool === "crop"}
                            Drag on the image to select crop area.
                        {:else}
                            Click and drag left/right on the image to rotate.
                        {/if}
                    </p>
                    <div class="tool-actions">
                        <button class="primary" on:click={saveImageEdit}>Save changes</button>
                        <button on:click={cancelImageEdit}>Cancel</button>
                    </div>
                {/if}

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

.image-stage {
    position: relative;
    max-width: 100%;
    user-select: none;
}

.image-stage.editing {
    cursor: crosshair;
}

.image-stage img {
    width: auto;
    height: auto;
    max-width: 100%;
    object-fit: contain;
    transition: transform 0.1s linear;
    transform-origin: center center;
}

.crop-box {
    position: absolute;
    border: 2px solid color-mix(in srgb, var(--primary), white 10%);
    background: color-mix(in srgb, var(--primary), transparent 82%);
    pointer-events: none;
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


.tool-switch {
    display: flex;
    gap: 8px;
}

.tool-switch button.active {
    border-color: color-mix(in srgb, var(--primary), white 15%);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 70%);
}

.tool-hint {
    margin: 8px 0;
    font-size: 0.9rem;
    color: var(--text-muted);
}
    
</style>