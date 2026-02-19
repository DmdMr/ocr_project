<script lang="ts">
    import { createEventDispatcher } from "svelte"
    import { uploadImage } from "../api"

    const dispatch = createEventDispatcher()

    let files: File[] = []
    let fileNames: string[] = []
    let message = ""
    let uploading = false

    function setFiles(fileList: FileList | null) {
        if (!fileList) return

        files = Array.from(fileList)
        fileNames = files.map(f => f.name)
    }

    function handleChange(event: Event) {
        const input = event.target as HTMLInputElement
        setFiles(input.files)
    }

    async function handleUpload() {
        if (!files.length) return

        uploading = true
        message = ""

        for (const file of files) {
            await uploadImage(file)
        }

        uploading = false
        message = "Upload completed"

        files = []
        fileNames = []

        dispatch("uploaded")
    }

    // 🔥 DRAG & DROP SUPPORT
    function handleDrop(event: DragEvent) {
        event.preventDefault()

        if (!event.dataTransfer) return

        setFiles(event.dataTransfer.files)
        handleUpload()
    }

    function handleDragOver(event: DragEvent) {
        event.preventDefault()
    }
</script>

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

    <span class="file-text">
        {fileNames.length > 0
            ? `${fileNames.length} file(s) selected`
            : "No file chosen"}
    </span>

    <button class="upload-btn" on:click={handleUpload} disabled={uploading}>
        {uploading ? "Uploading..." : "Upload"}
    </button>
</div>

{#if fileNames.length > 0}
<ul>
    {#each fileNames as name}
        <li>{name}</li>
    {/each}
</ul>
{/if}

{#if message}
<p>{message}</p>
{/if}

<style>
.upload {
    align-items: center;
    gap: 20px;
    margin-bottom: 20px;
    padding: 20px;
    border: 2px dashed transparent;
    border-radius: 8px;
    transition: 0.2s ease;
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

.file-text {
    color: #666;
    font-size: 14px;
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
    margin-right: 20px;
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
</style>
