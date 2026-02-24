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
    gap: 20px;
    margin-bottom: 20px;
    padding: 20px;
    border: 2px dashed transparent;
    border-radius: 8px;
    transition: 0.2s ease;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 20px;
}


.upload:hover {
    border-color: #ccc;
}

.file-btn {
    padding: 10px 18px;
    border-radius: 8px;
    background: #f0f0f0;
    border: 1px solid #ccc;
    cursor: pointer;
    font-weight: 500;
    transition: 0.2s ease;
}

.file-btn:hover {
    background: #e4e4e4;
}

.upload-btn {
    padding: 10px 22px;
    border-radius: 8px;
    border: none;
    background: linear-gradient(135deg, #3b6eea, #5b8cff);
    color: white;
    font-weight: 500;
    cursor: pointer;
    transition: 0.2s ease;
}

.upload-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 14px rgba(0,0,0,0.15);
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
    margin-bottom: 14px;
    padding: 14px;
    background: #f8f9fb;
    border-radius: 8px;
    border: 1px solid #eee;
}

.file-header {
    display: flex;
    justify-content: space-between;
    font-size: 14px;
    margin-bottom: 8px;
}

.status {
    font-size: 12px;
    text-transform: capitalize;
}

.status.uploading { color: #3b82f6; }
.status.processing { color: #f59e0b; }
.status.done { color: #10b981; }
.status.error { color: #ef4444; }

.progress-container {
    width: 100%;
    height: 6px;
    background: #e5e7eb;
    border-radius: 4px;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    transition: width 0.3s ease;
}

.progress-bar.uploading { background: #3b82f6; }
.progress-bar.processing { background: #f59e0b; }
.progress-bar.done { background: #10b981; }
.progress-bar.error { background: #ef4444; }

.message {
    margin-top: 12px;
    font-size: 14px;
    color: #10b981;
}
</style>