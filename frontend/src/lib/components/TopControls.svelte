<script lang="ts">
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






<div class="theme-switcher">
    <button on:click={() => setTheme('light')}>☀️</button>
    <button on:click={() => setTheme('dark')}>🌙</button>
</div>



<style>







</style>