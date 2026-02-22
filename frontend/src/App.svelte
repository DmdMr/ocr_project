<script lang="ts">
    import Upload from "./lib/components/Upload.svelte"
    import DocumentList from "./lib/components/DocumentList.svelte"
    import Settings from "./lib/components/Settings.svelte";
    import { onMount } from "svelte"

    let refreshKey = 0

    function handleUpload() {
        refreshKey += 1
    }

    let theme = "light"

    function setTheme(newTheme: string) {
        theme = newTheme
        document.body.setAttribute("data-theme", newTheme)
        localStorage.setItem("theme", newTheme)
    }

    onMount(() => {
        const saved = localStorage.getItem("theme") || "light"
        setTheme(saved)
    })

</script>


<h2>OCR System</h2>



<div class="theme-switcher">
    <button on:click={() => setTheme('light')}>☀️</button>
    <button on:click={() => setTheme('dark')}>🌙</button>
</div>


<Upload on:uploaded={handleUpload} />

<DocumentList {refreshKey} />



