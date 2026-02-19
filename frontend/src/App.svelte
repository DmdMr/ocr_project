<script lang="ts">
    import Upload from "./lib/components/Upload.svelte"
    import DocumentList from "./lib/components/DocumentList.svelte"

    let refreshKey = 0

    function handleUpload() {
        refreshKey += 1
    }
</script>

<h2>OCR System</h2>

<Upload on:uploaded={handleUpload} />

<DocumentList {refreshKey} />


