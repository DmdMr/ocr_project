<script lang="ts">
    import { createEventDispatcher } from "svelte"
    import { uploadImage } from "../api"

    const dispatch = createEventDispatcher()

    type UploadStatus = "pending" | "uploading" | "processing" | "done" | "error"

    interface UploadItem {
        file: File
        name: string
        progress: number
        status: UploadStatus
    }

    let items: UploadItem[] = []
    let message = ""
    let uploading = false

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

    function handleChange(event: Event) {
        const input = event.target as HTMLInputElement
        setFiles(input.files)
    }

    async function handleUpload() {
        if (!items.length) return

        uploading = true
        message = ""

        for (const item of items) {
            try {
                item.status = "uploading"
                item.progress = 30
                items = [...items]

                await uploadImage(item.file)

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
        message = "Upload completed"
        dispatch("uploaded")
    }

    function handleDrop(event: DragEvent) {
        event.preventDefault()
        if (!event.dataTransfer) return
        setFiles(event.dataTransfer.files)
    }

    function handleDragOver(event: DragEvent) {
        event.preventDefault()
    }
</script>

<!-- Upload Area -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
    class="upload"
    on:drop={handleDrop}
    on:dragover={handleDragOver}
>
    <label class="file-btn">
        Choose Files
        <input
            type="file"
            accept="image/png,image/jpeg,image/jpg,image/gif"
            multiple
            on:change={handleChange}
            hidden
        />
    </label>

    <button class="upload-btn" on:click={handleUpload} disabled={uploading}>
        {uploading ? "Uploading..." : "Upload"}
    </button>
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

<style>
.upload {
    margin-bottom: 20px;
    padding: 18px;
    border: 1px dashed var(--border-strong);
    border-radius: var(--radius-lg);
    transition: border-color 0.2s ease;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 16px;
}


.upload:hover {
    border-color: color-mix(in srgb, var(--primary), var(--border-strong) 50%);
}

.file-btn {
    padding: 10px 16px;
    border-radius: var(--radius-md);
    background: var(--surface);
    border: 1px solid var(--border-strong);
    cursor: pointer;
    transition: 0.2s ease;
    font-weight: 600;
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