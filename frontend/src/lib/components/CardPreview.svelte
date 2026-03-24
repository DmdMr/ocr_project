<script lang="ts">
    import { createEventDispatcher, onMount } from "svelte"
    import type { AttachmentFile, Document, GalleryImage } from "../types"
    import { tagHue } from "../tagColors"
    import CardTagPicker from "./CardTagPicker.svelte"
    import {
        UPLOADS_URL,
        deleteDocumentAttachment,
        editDocumentImage,
        getTags,
        setDocumentTags,
        uploadDocumentAttachments,
        type ImageEditPayload
    } from "../api"

    export let doc: Document
    export let editedText: string
    export let editing: boolean
    export let galleryUploading = false

    const dispatch = createEventDispatcher()

    let leftWidth = 50 // percent
    let isDragging = false


    type EditTool = "crop" | "rotate"

    let imageEditOpen = false
    let activeTool: EditTool = "crop"
    let previewRotation = 0
    let zoomLevel = 1
    const MIN_ZOOM = 0.5
    const MAX_ZOOM = 3
    const ZOOM_STEP = 0.25

    let activeImageFilename = ""
    let filenameEditing = false
    let filenameDraft = ""
    let filenameError = ""
    let tagPickerOpen = false
    let imageViewerOpen = false
    let allTags: string[] = []
    let tagsLoading = false
    let tagsError = ""
    let attachmentUploadError = ""
    let attachmentsUploading = false

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
    $: attachments = (doc.attachments ?? []) as AttachmentFile[]
    $: displayFilename = doc.display_filename ?? doc.filename
    $: if (!filenameEditing) {
        filenameDraft = displayFilename
        filenameError = ""
    }

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

    async function saveImageEdit() {
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

        try {
            const updated = await editDocumentImage(doc._id, payload)
            doc = updated
            dispatch("documentUpdated", { document: updated })
            cancelImageEdit()
        } catch (error) {
            const message = error instanceof Error ? error.message : "Не удалось обновить изображение"
            alert(message)
            console.error("Не удалось обновить изображение", error)
        }
    }

    function openImageViewer() {
        if (!selectedImage) return
        imageViewerOpen = true
    }

    function closeImageViewer() {
        imageViewerOpen = false
    }

    function currentGalleryIndex() {
        return galleryImages.findIndex(item => item.filename === activeImageFilename)
    }

    function showPreviousImage() {
        if (!galleryImages.length) return
        const index = currentGalleryIndex()
        const nextIndex = index <= 0 ? galleryImages.length - 1 : index - 1
        activeImageFilename = galleryImages[nextIndex]?.filename ?? activeImageFilename
    }

    function showNextImage() {
        if (!galleryImages.length) return
        const index = currentGalleryIndex()
        const nextIndex = index >= galleryImages.length - 1 ? 0 : index + 1
        activeImageFilename = galleryImages[nextIndex]?.filename ?? activeImageFilename
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

    function startFilenameEdit() {
        filenameEditing = true
        filenameDraft = displayFilename
        filenameError = ""
    }

    function cancelFilenameEdit() {
        filenameEditing = false
        filenameDraft = displayFilename
        filenameError = ""
    }

    function splitFilenameParts(name: string) {
        const trimmed = name.trim()
        const dotIndex = trimmed.lastIndexOf(".")
        if (dotIndex <= 0) {
            return { base: trimmed, extension: "" }
        }

        return {
            base: trimmed.slice(0, dotIndex),
            extension: trimmed.slice(dotIndex),
        }
    }

    function normalizeFilenameDraft(value: string, originalName: string) {
        const trimmed = value.trim()
        if (!trimmed) {
            return { error: "Имя файла не может быть пустым", value: "" }
        }

        const { extension: originalExtension } = splitFilenameParts(originalName)
        if (!originalExtension) {
            return { error: "", value: trimmed }
        }

        const { base, extension } = splitFilenameParts(trimmed)
        const normalizedBase = (extension && extension.toLowerCase() === originalExtension.toLowerCase() ? base : trimmed).trim()

        if (!normalizedBase) {
            return { error: "Имя файла не может быть пустым", value: "" }
        }

        return { error: "", value: `${normalizedBase}${originalExtension}` }
    }

    function saveFilename() {
        const normalized = normalizeFilenameDraft(filenameDraft, displayFilename)
        if (normalized.error) {
            filenameError = normalized.error
            return
        }

        dispatch("saveFilename", { display_filename: normalized.value })
        filenameEditing = false
    }

    function remove() {
        dispatch("delete")
    }

    function toggleEdit() {
        dispatch("editToggle")
    }
    function selectTag(tag: string) {
        dispatch("tagClick", { tag })
    }

    async function loadTags(force = false) {
        if (tagsLoading) return
        if (allTags.length && !force) return

        tagsLoading = true
        tagsError = ""

        try {
            allTags = await getTags()
        } catch (error) {
            tagsError = error instanceof Error ? error.message : "Не удалось загрузить теги"
        } finally {
            tagsLoading = false
        }
    }

    async function openTagPicker() {
        tagPickerOpen = true
        await loadTags()
    }

    function closeTagPicker() {
        tagPickerOpen = false
        tagsError = ""
    }

    async function saveDocumentTags(nextTags: string[]) {
        tagsError = ""

        try {
            const updated = await setDocumentTags(doc._id, nextTags)
            doc = updated
            dispatch("documentUpdated", { document: updated })
        } catch (error) {
            tagsError = error instanceof Error ? error.message : "Не удалось обновить теги"
        }
    }

    async function handleTagAdded(event: CustomEvent<{ tag: string }>) {
        const normalized = event.detail.tag.trim().toLowerCase()
        const currentTags = doc.tags ?? []
        if (currentTags.some(tag => tag.trim().toLowerCase() === normalized)) return

        await saveDocumentTags([...currentTags, normalized])
    }

    async function handleTagRemoved(event: CustomEvent<{ tag: string }>) {
        const normalized = event.detail.tag.trim().toLowerCase()
        const nextTags = (doc.tags ?? []).filter(tag => tag.trim().toLowerCase() !== normalized)
        await saveDocumentTags(nextTags)
    }

    async function handleAttachmentFiles(event: Event) {
        const input = event.target as HTMLInputElement
        const files = Array.from(input.files ?? [])
        input.value = ""

        if (!files.length) return

        const nonImageFiles = files.filter(file => !file.type.startsWith("image/"))
        if (!nonImageFiles.length) {
            attachmentUploadError = "Изображения нужно добавлять через галерею"
            return
        }

        attachmentsUploading = true
        attachmentUploadError = ""

        try {
            const result = await uploadDocumentAttachments(doc._id, nonImageFiles)
            if (!result.document) {
                throw new Error("Сервер не вернул обновлённые данные карточки")
            }

            doc = result.document
            dispatch("documentUpdated", { document: result.document })

            if (result.skipped_files?.length) {
                attachmentUploadError = result.skipped_files.join("; ")
            }
        } catch (error) {
            attachmentUploadError = error instanceof Error ? error.message : "Не удалось прикрепить файлы"
        } finally {
            attachmentsUploading = false
        }
    }

    async function removeAttachment(attachment: AttachmentFile) {
        if (!attachment.filename) return

        try {
            const updated = await deleteDocumentAttachment(doc._id, attachment.filename)
            doc = updated
            dispatch("documentUpdated", { document: updated })
            attachmentUploadError = ""
        } catch (error) {
            attachmentUploadError = error instanceof Error ? error.message : "Не удалось удалить файл"
        }
    }

    function uploadGalleryFiles(event: Event) {
        const input = event.target as HTMLInputElement
        const files = Array.from(input.files ?? [])
        if (!files.length) return

        dispatch("addImages", { files })
        input.value = ""
    }

    function attachmentDownloadUrl(attachment: AttachmentFile) {
        return `${UPLOADS_URL}/${attachment.filename}`
    }

    function attachmentLabel(attachment: AttachmentFile) {
        return attachment.original_name || attachment.filename || "Файл"
    }

    function formatFileSize(value?: number) {
        if (!value || value <= 0) return "Размер неизвестен"
        if (value < 1024) return `${value} Б`
        if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} КБ`
        return `${(value / (1024 * 1024)).toFixed(1)} МБ`
    }

    function handleKey(e: KeyboardEvent) {
        if (e.key === "Escape") {
            if (imageViewerOpen) {
                closeImageViewer()
                return
            }
            if (imageEditOpen) {
                cancelImageEdit()
                return
            }
            close()
        }

        if (imageViewerOpen && e.key === "ArrowLeft") {
            showPreviousImage()
        }

        if (imageViewerOpen && e.key === "ArrowRight") {
            showNextImage()
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
        loadTags()
        window.addEventListener("keydown", handleKey)
        return () => window.removeEventListener("keydown", handleKey)
    })


    const imageSrc = () => `${UPLOADS_URL}/${activeImageFilename}?v=${encodeURIComponent(selectedImage?.image_version ?? doc.image_version ?? doc.created_at ?? "")}`

    function cardImageSrc(currentDoc: Document) {
        return `${UPLOADS_URL}/${currentDoc.filename}?v=${encodeURIComponent(currentDoc.image_version ?? currentDoc.created_at ?? "")}`
    }


    function getFilenameWithoutExtension(name: string) {
        if (!name) return ""

        const lastDot = name.lastIndexOf(".")
        if (lastDot <= 0) return name

        return name.slice(0, lastDot)
    }
    
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
                {#key imageSrc()}
                    <!-- svelte-ignore a11y_missing_attribute -->
                    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
                    <img
                        bind:this={imageEl}
                        src={imageSrc()}
                        alt=""
                        draggable="false"
                        on:dragstart|preventDefault
                        style={`transform: scale(${zoomLevel}) rotate(${imageEditOpen && activeTool === 'rotate' ? previewRotation : 0}deg);`}
                        on:click={!imageEditOpen ? openImageViewer : undefined}
                    />
                {/key}

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
                <div class="title-row">
                    {#if filenameEditing}
                        <div class="filename-editor">
                            <input
                                bind:value={filenameDraft}
                                aria-label="Имя файла"
                                on:keydown={(event) => {
                                    if (event.key === "Enter") {
                                        event.preventDefault()
                                        saveFilename()
                                    }

                                    if (event.key === "Escape") {
                                        event.preventDefault()
                                        cancelFilenameEdit()
                                    }
                                }}
                            />
                            <div class="filename-actions">
                                <button class="primary" on:click={saveFilename}>Сохранить</button>
                                <button on:click={cancelFilenameEdit}>Отмена</button>
                            </div>
                        </div>
                    {:else}
                        <div class="title-display">
                            <h3>{getFilenameWithoutExtension(displayFilename)}</h3>
                            <button class="icon-button" on:click={startFilenameEdit} aria-label="Редактировать имя файла">✎</button>
                        </div>
                    {/if}
                </div>
                <!--
                <small>{new Date(doc.created_at).toLocaleString()}</small>
                -->
                {#if filenameError}
                    <p class="filename-error">{filenameError}</p>
                {/if}

                
            </div>

            <div class="preview-tools">

                <!--
                <button on:click={zoomOut} aria-label="Уменьшить">−</button>
                
                <span class="zoom-badge">{displayZoomPercent()}%</span>
         
                <button on:click={zoomIn} aria-label="Увеличить">+</button>
                <button on:click={resetZoom}>Сбросить масштаб</button>


                <span class="toolbar-divider" aria-hidden="true"></span>

            -->

                {#if !imageEditOpen}
                    <button class="primary" on:click={startImageEdit}>Редактировать изображение</button>
                {:else}
                    <div class="edit-toolbar-inline">
                        <button class:active={activeTool === "crop"} on:click={() => setTool("crop")}>Обрезка</button>
                        <button class:active={activeTool === "rotate"} on:click={() => setTool("rotate")}>Поворот</button>
                        {#if activeTool === "rotate"}
                            <button on:click={() => nudgeRotation(-1)} aria-label="Повернуть влево на 90 градусов">↺ 90°</button>
                            <button on:click={() => nudgeRotation(1)} aria-label="Повернуть вправо на 90 градусов">↻ 90°</button>
                            <span class="angle-badge">{displayRotation()}°</span>
                        {/if}
                        <button class="primary" on:click={saveImageEdit}>Сохранить</button>
                        <button on:click={cancelImageEdit}>Отмена</button>
                    </div>
                {/if}
            </div>

            <div class="gallery-toolbar">
                <label class="gallery-upload-btn" class:disabled={galleryUploading}>
                    {galleryUploading ? "Добавление изображений..." : "Добавить изображения в карточку"}
                    <input
                        type="file"
                        accept="image/png,image/jpeg,image/jpg"
                        multiple
                        hidden
                        disabled={galleryUploading}
                        on:change={uploadGalleryFiles}
                    />
                </label>

                <label class="gallery-upload-btn secondary" class:disabled={attachmentsUploading}>
                    {attachmentsUploading ? "Прикрепление файлов..." : "Добавить PDF и другие файлы"}
                    <input
                        type="file"
                        multiple
                        hidden
                        disabled={attachmentsUploading}
                        on:change={handleAttachmentFiles}
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
                        <span>{index === 0 ? "Оригинал" : `Изображение ${index + 1}`}</span>
                    </button>
                {/each}
            </div>


            <div class="attachments-panel">
                <div class="attachments-header">
                    <h4>Файлы карточки</h4>
                    <span>{attachments.length}</span>
                </div>

                {#if attachmentUploadError}
                    <p class="attachment-error">{attachmentUploadError}</p>
                {/if}

                {#if attachments.length}
                    <div class="attachment-list">
                        {#each attachments as attachment}
                            <div class="attachment-item">
                                <div class="attachment-meta">
                                    <strong>{attachmentLabel(attachment)}</strong>
                                    <span>{attachment.content_type || "Файл"} · {formatFileSize(attachment.size)}</span>
                                </div>

                                <div class="attachment-actions">
                                    <a
                                        class="attachment-link"
                                        href={attachmentDownloadUrl(attachment)}
                                        download={attachment.original_name || attachment.filename}
                                        target="_blank"
                                        rel="noreferrer"
                                    >
                                        Скачать
                                    </a>
                                    <button class="danger" on:click={() => removeAttachment(attachment)}>Удалить</button>
                                </div>
                            </div>
                        {/each}
                    </div>
                {:else}
                    <p class="attachment-empty">Дополнительных файлов пока нет.</p>
                {/if}
            </div>


            <!--
            {#if imageEditOpen}
                <p class="tool-hint">
                    {#if activeTool === "crop"}
                        Перетащите курсор по изображению, чтобы выделить область обрезки
                    {:else}
                        Зажмите кнопку мыши и ведите влево/вправо для поворота
                    {/if}
                </p>
            {/if}
            -->

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
                        <span class="empty-tags">Нет тегов</span>
                    {/if}
                </div>

                <div class="actions">
                    <button on:click={openTagPicker}>Управлять тегами</button>
                    {#if editing}
                        <button on:click={save}>Сохранить</button>
                    {:else}
                        <button on:click={toggleEdit}>Редактировать</button>
                    {/if}
                    <button class="delete" on:click={remove}>Удалить</button>
                </div>
            </div>

            {#if tagPickerOpen}
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div class="tag-picker-backdrop" on:click={closeTagPicker}>
                    <div class="tag-picker-modal" on:click|stopPropagation>
                        <CardTagPicker
                            assignedTags={doc.tags ?? []}
                            allTags={allTags}
                            loading={tagsLoading}
                            error={tagsError}
                            on:add={handleTagAdded}
                            on:remove={handleTagRemoved}
                            on:close={closeTagPicker}
                        />
                    </div>
                </div>
            {/if}

            {#if imageViewerOpen}
                <!-- svelte-ignore a11y_click_events_have_key_events -->
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <div class="lightbox-backdrop" on:click={closeImageViewer}>
                    <div class="lightbox-modal" on:click|stopPropagation>
                        <button class="lightbox-close" on:click={closeImageViewer}>✕</button>
                        <button class="lightbox-nav left" on:click={showPreviousImage} disabled={galleryImages.length < 2}>←</button>
                        <img src={imageSrc()} alt="" />
                        <button class="lightbox-nav right" on:click={showNextImage} disabled={galleryImages.length < 2}>→</button>
                        <div class="lightbox-caption">
                            <strong>{currentGalleryIndex() + 1} / {galleryImages.length}</strong>
                            <span>{selectedImage?.filename || ""}</span>
                        </div>
                    </div>
                </div>
            {/if}



            </div>

        </div>

        <button class="close" on:click={close}>✕</button>
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

.tag-picker-backdrop {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: rgba(10, 14, 20, 0.66);
    z-index: 5;
}

.tag-picker-modal {
    max-width: 100%;
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
    grid-template-rows: auto auto auto auto 1fr auto;    
    gap: 10px;
    padding: 18px;
    overflow: hidden;
}

.preview-tools {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.header {
    display: grid;
    gap: 6px;
}

.title-row {
    display: flex;
    align-items: flex-start;
    gap: 8px;
    min-width: 0;
}

.title-row h3 {
    margin: 0;
    min-width: 0;
    overflow-wrap: anywhere;
}

.title-display {
    display: flex;
    align-items: center;
    gap: 8px;
    min-width: 0;
}

.filename-editor {
    display: grid;
    gap: 8px;
    width: 100%;
}

.filename-editor input {
    width: 100%;
    min-height: 40px;
    background: var(--surface);
}

.filename-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

.filename-error {
    margin: 0;
    color: var(--danger);
    font-size: 0.9rem;
}

.icon-button {
    min-width: 34px;
    min-height: 34px;
    padding: 0.35rem 0.55rem;
    border-radius: 999px;
    align-self: center;
    box-shadow: none;
}



.edit-toolbar-inline {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
}

.edit-toolbar-inline button.active {
    border-color: color-mix(in srgb, var(--primary), white 15%);
    box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 70%);
}



.gallery-toolbar {
    display: flex;
    justify-content: flex-start;
    gap: 10px;
    flex-wrap: wrap;
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

.gallery-upload-btn.secondary {
    background: color-mix(in srgb, var(--surface), transparent 5%);
}

.gallery-upload-btn.disabled {
    opacity: 0.65;
    cursor: wait;
    pointer-events: none;
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



.attachments-panel {
    display: grid;
    gap: 10px;
    padding: 12px;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: color-mix(in srgb, var(--surface), transparent 6%);
}

.attachments-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
}

.attachments-header h4 {
    margin: 0;
}

.attachments-header span {
    min-width: 28px;
    min-height: 28px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    border-radius: 999px;
    background: var(--surface-elevated);
    color: var(--text-muted);
    font-size: 0.85rem;
}

.attachment-list {
    display: grid;
    gap: 10px;
}

.attachment-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 10px 12px;
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface);
}

.attachment-meta {
    display: grid;
    gap: 4px;
    min-width: 0;
}

.attachment-meta strong {
    overflow-wrap: anywhere;
}

.attachment-meta span {
    color: var(--text-muted);
    font-size: 0.84rem;
}

.attachment-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    align-items: center;
}

.attachment-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-height: 40px;
    padding: 0.55rem 1rem;
    border-radius: var(--radius-md);
    border: 1px solid var(--border-strong);
    background: var(--surface);
    color: var(--text);
    font-weight: 600;
    text-decoration: none;
}

.attachment-empty,
.attachment-error {
    margin: 0;
}

.attachment-empty {
    color: var(--text-muted);
}

.attachment-error {
    color: var(--danger);
}

.lightbox-backdrop {
    position: absolute;
    inset: 0;
    z-index: 6;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: rgba(10, 14, 20, 0.82);
}

.lightbox-modal {
    position: relative;
    width: min(100%, 980px);
    height: min(100%, 760px);
    display: flex;
    align-items: center;
    justify-content: center;
}

.lightbox-modal img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    margin: 0;
}

.lightbox-close,
.lightbox-nav {
    position: absolute;
    z-index: 1;
    min-width: 42px;
    min-height: 42px;
    border-radius: 999px;
    background: rgba(16, 22, 32, 0.72);
    color: #fff;
    border-color: transparent;
}

.lightbox-close {
    top: 0;
    right: 0;
}

.lightbox-nav.left {
    left: 0;
}

.lightbox-nav.right {
    right: 0;
}

.lightbox-caption {
    position: absolute;
    left: 50%;
    bottom: 0;
    transform: translateX(-50%);
    display: grid;
    gap: 4px;
    padding: 10px 14px;
    border-radius: 14px;
    background: rgba(16, 22, 32, 0.72);
    color: #fff;
    text-align: center;
}



.angle-badge {
    margin-left: auto;
    padding: 4px 10px;
    border-radius: 999px;
    border: 1px solid var(--border-strong);
    font-size: 0.84rem;
    color: var(--text-muted);
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





@media (max-width: 768px) {
    .modal {
        width: 96vw;
        height: 92vh;
        grid-template-columns: 1fr;
        grid-template-rows: auto 1fr;
    }

    .left {
        min-height: 280px;
        max-height: 40vh;
        padding: 12px;
    }

    .right {
        min-height: 0;
        overflow-y: auto;
        padding: 14px;
    }
}




    
</style>
