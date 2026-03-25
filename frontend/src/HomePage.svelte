<script lang="ts">
    import Upload from "./lib/components/Upload.svelte"
    import DocumentList from "./lib/components/DocumentList.svelte"
    import Settings from "./lib/components/Settings.svelte";
    import { onMount } from "svelte"
    import LifeguardHelp from "./lib/components/LifeguardHelp.svelte"
    import DocumentCard from "./lib/components/DocumentCard.svelte";
    import { push } from 'svelte-spa-router'

    

    type ThemeMode = "system" | "light" | "dark"
    let refreshKey = 0
    let themeMode: ThemeMode = "system"
    let language: "en" | "ru" = "en"
    let viewMode: "grid" | "list" = "grid"
    let viewModeLoaded = false
    let isHelpOpen = false
    let showPreview = false
    let columnCount = 5
    let columnsLoaded = false


    onMount(() => {
        const saved = localStorage.getItem("columnCount")
        if (saved) {
        columnCount = Number(saved)
        }
        columnsLoaded = true
    })

    $: if (columnsLoaded) {
        localStorage.setItem("columnCount", String(columnCount))
    }

    function handleUpload() {
        refreshKey += 1
    }


    function applyTheme(mode: ThemeMode) {
        themeMode = mode

        if (mode === "system") {
            document.body.removeAttribute("data-theme")
        } else {
            document.body.setAttribute("data-theme", mode)
        }

        localStorage.setItem("themeMode", mode)
    }

    function setLanguage(newLanguage: "en" | "ru") {
        language = newLanguage
        localStorage.setItem("language", newLanguage)
        document.documentElement.lang = newLanguage
    }

    

    onMount(() => {
        const savedTheme = (localStorage.getItem("themeMode") as ThemeMode | null) ?? "system"
        const savedLanguage = (localStorage.getItem("language") as "en" | "ru" | null) ?? "en"
        applyTheme(savedTheme)
        setLanguage(savedLanguage)
        const saved = localStorage.getItem("viewMode")
        if (saved === "grid" || saved === "list") {
            viewMode = saved
        }
        viewModeLoaded = true
    })


    $: if (viewModeLoaded) {
        localStorage.setItem("viewMode", viewMode)
    }

</script>


<div class="panel about-manager">
  <div class="quick-actions">
    <button on:click={() => push('/about')}>
      О проекте
    </button>

    <button on:click={() => push('/archive')}>
      Архив
    </button>

    <button class="primary" on:click={() => push('/assistant')}>
      Чат-помощник
    </button>
  </div>
</div>

<!--


<h2>Система распознавания рукописного текста</h2>


<div class="theme-switcher">
    <button on:click={() => setTheme('light')}>☀️</button>
    <button on:click={() => setTheme('dark')}>🌙</button>
</div>


<TopControls
    mode={themeMode}
    {language}
    onThemeChange={applyTheme}
    onLanguageChange={setLanguage}
/>
-->


<Upload on:uploaded={handleUpload} />

<DocumentList {refreshKey} {viewMode} {columnCount} />


<!--
<LifeguardHelp bind:viewMode bind:columnCount />


-->

<style>
.about-manager {
    padding: 14px;
    margin-bottom: 16px;
    text-align: left;
}

@media (max-width: 640px) {
    .about-manager {
        padding: 8px;
        margin-bottom: 12px;
        text-align: center;
    }
}

.quick-actions {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}

@media (max-width: 640px) {
    .quick-actions {
        display: grid;
        grid-template-columns: 1fr 1fr;
        text-align: center;
    }
}


</style>
