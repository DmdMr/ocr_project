<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte"
    import type { Document, GalleryImage } from "../types"
    import { tagHue } from "../tagColors"
    import { UPLOADS_URL, type ImageEditPayload } from "../api"

    export let doc: Document
    export let editedText: string
    export let editing: boolean

    const dispatch = createEventDispatcher()

    type EditTool = "crop" | "rotate"

    let imageEditOpen = false
    let activeTool: EditTool = "crop"
    let previewRotation = 0
    let zoomLevel = 1
    const MIN_ZOOM = 0.5
    const MAX_ZOOM = 3
    const ZOOM_STEP = 0.25

    let activeImageFilename = ""

    let imageEl: HTMLImageElement | null = null
    let imageStageEl: HTMLDivElement | null = null

    let isDrawingCrop = false
    let cropStartX = 0
    let cropStartY = 0
    let cropRect: { x: number; y: number; width: number; height: number } | null = null

    let isRotating = false
    let rotateStartX = 0
    let rotateBase = 0

    const SNAP_STEP = 90
    const SNAP_THRESHOLD = 10

    $: galleryImages = (doc.gallery_images?.length ? doc.gallery_images : [{ filename: doc.filename, image_version: doc.image_version }]) as GalleryImage[]

    $: if (!activeImageFilename || !galleryImages.some(item => item.filename === activeImageFilename)) {
        activeImageFilename = galleryImages[0]?.filename ?? doc.filename
    }

    $: selectedImage = galleryImages.find(item => item.filename === activeImageFilename) ?? galleryImages[0]

    function startImageEdit() {
        imageEditOpen = true
        activeTool = "crop"
        previewRotation = 0
        cropRect = null
        zoomLevel = 1
    }

    function cancelImageEdit() {
        imageEditOpen = false
        previewRotation = 0
        cropRect = null
        zoomLevel = 1
        isDrawingCrop = false
        isRotating = false
    }

    function setTool(tool: EditTool) {
        activeTool = tool
    }

    function normalizeRotation(angle: number) {
        const wrapped = ((angle % 360) + 360) % 360
        return wrapped > 180 ? wrapped - 360 : wrapped
    }

    function snapRotation(angle: number, threshold = SNAP_THRESHOLD) {
        const nearest = Math.round(angle / SNAP_STEP) * SNAP_STEP
        return Math.abs(nearest - angle) <= threshold ? nearest : angle
    }

    function displayRotation() {
        return Math.round(normalizeRotation(previewRotation))
    }

    function displayZoomPercent() {
        return Math.round(zoomLevel * 100)
    }

    function saveRotationValue() {
        const snapped = Math.round(previewRotation / SNAP_STEP) * SNAP_STEP
        return normalizeRotation(snapped)
    }

    function nudgeRotation(direction: -1 | 1) {
        previewRotation = normalizeRotation(saveRotationValue() + direction * SNAP_STEP)
    }

    function clampZoom(value: number) {
        return Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, value))
    }

    function zoomIn() {
        zoomLevel = clampZoom(zoomLevel + ZOOM_STEP)
    }

    function zoomOut() {
        zoomLevel = clampZoom(zoomLevel - ZOOM_STEP)
    }

    function resetZoom() {
        zoomLevel = 1
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

        event.preventDefault()

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

    function onGlobalMouseMove(event: MouseEvent) {
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
            previewRotation = snapRotation(rotateBase + deltaX * 0.55)
        }
    }

    function stopEditorInteraction() {
        if (activeTool === "rotate" && isRotating) {
            previewRotation = snapRotation(previewRotation)
        }
        isDrawingCrop = false
        isRotating = false
    }

    function saveImageEdit() {
        let payload: ImageEditPayload | null = null

        if (activeTool === "rotate") {
            const normalized = saveRotationValue()
            if (normalized === 0) {
                return
            }

            payload = { rotate_degrees: normalized, image_filename: activeImageFilename }
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
                image_filename: activeImageFilename,
                crop: {
                    x_percent: Math.max(0, Math.min(100, xPercent)),
                    y_percent: Math.max(0, Math.min(100, yPercent)),
                    width_percent: Math.max(0.1, Math.min(100, widthPercent)),
                    height_percent: Math.max(0.1, Math.min(100, heightPercent))
                }
            }
        }

        if (!payload) return

        dispatch("imageEdit", { payload })

        cancelImageEdit()
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

    function uploadGalleryFiles(event: Event) {
        const input = event.target as HTMLInputElement
        const files = Array.from(input.files ?? [])
        if (!files.length) return

        dispatch("addImages", { files })
        input.value = ""
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

    const imageSrc = () => `${UPLOADS_URL}/${activeImageFilename}?v=${encodeURIComponent(selectedImage?.image_version ?? doc.image_version ?? doc.created_at ?? "")}`
</script>

<svelte:window on:mousemove={onGlobalMouseMove} on:mouseup={stopEditorInteraction} />

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
            >
                <!-- svelte-ignore a11y_missing_attribute -->
                <img
                    bind:this={imageEl}
                    src={imageSrc()}
                    alt=""
                    draggable="false"
                    on:dragstart|preventDefault
                    style={`transform: scale(${zoomLevel}) rotate(${imageEditOpen && activeTool === 'rotate' ? previewRotation : 0}deg);`}
                />

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

            <div class="preview-tools">
                <button on:click={zoomOut} aria-label="Zoom out">−</button>
                <span class="zoom-badge">{displayZoomPercent()}%</span>
                <button on:click={zoomIn} aria-label="Zoom in">+</button>
                <button on:click={resetZoom}>Reset zoom</button>
            </div>

            <div class="gallery-toolbar">
                <label class="gallery-upload-btn">
                    Add images to this card
                    <input
                        type="file"
                        accept="image/png,image/jpeg,image/jpg"
                        multiple
                        hidden
                        on:change={uploadGalleryFiles}
                    />
                </label>
            </div>

            <div class="gallery-strip">
                {#each galleryImages as image, index}
                    <button
                        class="gallery-item"
                        class:active={image.filename === activeImageFilename}
                        on:click={() => activeImageFilename = image.filename}
                    >
                        <img src={`${UPLOADS_URL}/${image.filename}?v=${encodeURIComponent(image.image_version ?? "")}`} alt="" />
                        <span>{index === 0 ? "Original" : `Image ${index + 1}`}</span>
                    </button>
                {/each}
            </div>

            {#if !imageEditOpen}
                <button class="primary" on:click={startImageEdit}>Edit image</button>
            {:else}
                <div class="tool-switch">
                    <button class:active={activeTool === "crop"} on:click={() => setTool("crop")}>Crop</button>
                    <button class:active={activeTool === "rotate"} on:click={() => setTool("rotate")}>Rotate</button>
                    {#if activeTool === "rotate"}
                        <button on:click={() => nudgeRotation(-1)} aria-label="Rotate left 90 degrees">↺ 90°</button>
                        <button on:click={() => nudgeRotation(1)} aria-label="Rotate right 90 degrees">↻ 90°</button>
                        <span class="angle-badge">{displayRotation()}°</span>
                    {/if}
                </div>
                <p class="tool-hint">
                    {#if activeTool === "crop"}
                        Drag on image to draw crop area.
                    {:else}
                        Hold mouse and drag left/right to rotate (snaps to 90°, 180°, 270°).
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

        <button class="close" on:click={close}>✕</button>
    </div>
</div>

<style>
.overlay {
    position: fixed;
    inset: 0;
    background: rgba(10, 14, 20, 0.9);
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
    grid-template-columns: minmax(360px, 1fr) minmax(460px, 1.2fr);
    border-radius: var(--radius-lg);
    overflow: hidden;
    position: relative;
}

.left {
    overflow: auto;
    display: flex;
    justify-content: center;
    align-items: center;
    padding: 20px;
    background: color-mix(in srgb, var(--surface-elevated), black 45%);
}

.image-stage {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 0;
    display: flex;
    justify-content: center;
    align-items: center;
    user-select: none;
    overflow: auto;
}

.image-stage.editing {
    cursor: crosshair;
}

.image-stage img {
    width: auto;
    height: auto;
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    transition: transform 0.1s linear;
    transform-origin: center center;
}

.crop-box {
    position: absolute;
    border: 2px solid color-mix(in srgb, var(--primary), white 15%);
    background: color-mix(in srgb, var(--primary), transparent 80%);
    pointer-events: none;
}

.right {
    display: grid;
    grid-template-rows: auto auto auto auto auto 1fr auto;
    gap: 10px;
    padding: 18px;
    overflow: hidden;
}

.preview-tools {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.zoom-badge {
    min-width: 62px;
    text-align: center;
    padding: 4px 10px;
    border-radius: 999px;
    border: 1px solid var(--border-strong);
    font-size: 0.84rem;
    color: var(--text-muted);
}

.gallery-toolbar {
    display: flex;
    justify-content: flex-start;
}

.gallery-upload-btn {
    display: inline-flex;
    align-items: center;
    min-height: 36px;
    padding: 0.45rem 0.9rem;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius-md);
    background: var(--surface);
    cursor: pointer;
    font-weight: 600;
}

.gallery-strip {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(92px, 1fr));
    gap: 8px;
    max-height: 132px;
    overflow: auto;
    padding-right: 4px;
}

.gallery-item {
    min-height: 92px;
    padding: 6px;
    border: 1px solid var(--border);
    border-radius: 10px;
    background: color-mix(in srgb, var(--surface), transparent 8%);
    display: grid;
    gap: 6px;
    align-content: start;
    box-shadow: none;
}

.gallery-item img {
    width: 100%;
    height: 54px;
    object-fit: cover;
    border-radius: 8px;
}

.gallery-item span {
    font-size: 0.74rem;
    color: var(--text-muted);
    text-align: left;
}

.gallery-item.active {
    border-color: color-mix(in srgb, var(--primary), white 15%);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 72%);
}

.tool-switch {
    display: flex;
    align-items: center;
    gap: 8px;
}

.tool-switch button {
    min-height: 36px;
    padding: 0.4rem 0.85rem;
}

.tool-switch button.active {
    border-color: color-mix(in srgb, var(--primary), white 15%);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 70%);
}

.angle-badge {
    margin-left: auto;
    padding: 4px 10px;
    border-radius: 999px;
    border: 1px solid var(--border-strong);
    font-size: 0.84rem;
    color: var(--text-muted);
}

.tool-hint {
    margin: 8px 0 4px;
    font-size: 0.9rem;
    color: var(--text-muted);
}

.tool-actions {
    margin-top: 8px;
    display: flex;
    gap: 8px;
    justify-content: flex-start;
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
