<script lang="ts">
    import { createEventDispatcher } from "svelte"
    import { uploadImage } from "../api"

    export let galleryUploading = false
    export let embedded = false

    const dispatch = createEventDispatcher()

    type UploadStatus = "pending" | "uploading" | "processing" | "done" | "error"
    type UploadMode = "with_ocr" | "without_ocr"

    interface UploadItem {
        file: File
        name: string
        progress: number
        status: UploadStatus
    }

    let items: UploadItem[] = []
    let message = ""
    let uploading = false
    let fileInput: HTMLInputElement | null = null
    let selectedUploadMode: UploadMode = "with_ocr"

    function setFiles(fileList: FileList | null) {
        if (!fileList) return

        const files = Array.from(fileList)

        items = files.map(f => ({
            file: f,
            name: f.name,
            progress: 0,
            status: "pending"
        }))
    }

    function openFilePicker(mode: UploadMode) {
        if (uploading) return
        selectedUploadMode = mode
        fileInput?.click()
    }

    function modeLabel(mode: UploadMode) {
        return mode === "with_ocr" ? "с распознаванием" : "без распознавания"
    }

    async function handleUpload(files: FileList | null, mode: UploadMode) {
        setFiles(files)
        if (!items.length) return

        uploading = true
        message = ""

        for (const item of items) {
            try {
                item.status = "uploading"
                item.progress = 30
                items = [...items]

                await uploadImage(item.file, mode === "with_ocr")

                item.status = "processing"
                item.progress = 70
                items = [...items]

                // Simulate small processing delay
                await new Promise(r => setTimeout(r, 500))

                item.status = "done"
                item.progress = 100
                items = [...items]

            } catch (e) {
                item.status = "error"
                items = [...items]
            }
        }

        uploading = false
        message = `Загрузка ${modeLabel(mode)} завершена`
        dispatch("uploaded")
    }

    async function handleFileSelection(event: Event) {
        const input = event.target as HTMLInputElement
        const files = input.files
        await handleUpload(files, selectedUploadMode)
        input.value = ""
    }

    async function handleDrop(event: DragEvent) {
        event.preventDefault()
        if (!event.dataTransfer) return
        selectedUploadMode = "with_ocr"
        await handleUpload(event.dataTransfer.files, "with_ocr")
    }

    function handleDragOver(event: DragEvent) {
        event.preventDefault()
    }
</script>

<!-- Upload Area -->
<!-- svelte-ignore a11y_no_static_element_interactions -->

<div class="upload-manager" class:panel={!embedded} class:embedded={embedded}>
<div
    class="upload"
    on:drop={handleDrop}
    on:dragover={handleDragOver}
>
    <input
        bind:this={fileInput}
        type="file"
        accept="image/*"
        multiple
        on:change={handleFileSelection}
        hidden
    />

    <div class="upload-actions">
        <button class="upload-btn upload-action-btn" on:click={() => openFilePicker("with_ocr")} disabled={uploading}>
            {uploading && selectedUploadMode === "with_ocr" ? "Загрузка..." : "Загрузить с распознаванием"}
        </button>

        <button class="secondary upload-action-btn" on:click={() => openFilePicker("without_ocr")} disabled={uploading}>
            {uploading && selectedUploadMode === "without_ocr" ? "Загрузка..." : "Загрузить без распознавания"}
        </button>
    </div>
</div>

<!-- File List -->
{#if items.length > 0}
<ul class="file-list">
    {#each items as item}
        <li class="file-item">
            <div class="file-header">
                <span>{item.name}</span>
                <span class="status {item.status}">
                    {item.status}
                </span>
            </div>

            <div class="progress-container">
                <div
                    class="progress-bar {item.status}"
                    style="width: {item.progress}%">
                </div>
            </div>
        </li>
    {/each}
</ul>
{/if}

{#if message}
<p class="message">{message}</p>
{/if}

    
</div>

<style>

.upload-manager {
    padding: 14px;
    margin-bottom: 16px;
    text-align: left;
}

.upload-manager.embedded {
    padding: 0;
    margin: 10px 0 0;
}

@media (max-width: 640px) {
    .upload-manager {
        padding: 8px;
        margin-bottom: 12px;
        text-align: left;
    }
}

.upload {
    transition: border-color 0.2s ease;
    display: block;
}

.upload-actions {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 8px;
}

.upload-action-btn {
    width: 100%;
    min-height: 56px;
    height: 56px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    line-height: 1.2;
    white-space: normal;
    word-break: break-word;
    padding: 10px 12px;
    box-sizing: border-box;
}

@media (max-width: 640px) {
    .upload-actions {
        grid-template-columns: 1fr;
    }
}

.upload:hover {
    border-color: color-mix(in srgb, var(--primary), var(--border-strong) 50%);
}

.upload-btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
}

.file-list {
    list-style: none;
    padding: 0;
    margin-top: 20px;
}

.file-item {
    margin-bottom: 12px;
    padding: 14px;
    background: var(--surface);
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
}

.file-header {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 8px;
    text-align: left;
}

.status {
    font-size: 0.85rem;
    font-weight: 600;
    text-transform: capitalize;
}

.status.uploading { color: #3b82f6; }
.status.processing { color: #f59e0b; }
.status.done { color: #10b981; }
.status.error { color: var(--danger); }


.progress-container {
    height: 8px;
    background: color-mix(in srgb, var(--surface-elevated), transparent 20%);
    border-radius: 4px;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    transition: width 0.35s ease;
}

.progress-bar.uploading { background: #3b82f6; }
.progress-bar.processing { background: #f59e0b; }
.progress-bar.done { background: #10b981; }
.progress-bar.error { background: var(--danger); }

.message {
    margin-top: 12px;
    font-weight: 600;
    color: #10b981;
}

</style>
