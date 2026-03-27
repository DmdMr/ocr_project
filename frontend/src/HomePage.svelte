<script lang="ts">
    import Upload from "./lib/components/Upload.svelte"
    import DocumentList from "./lib/components/DocumentList.svelte"
    import WorkspaceSidebar from "./lib/components/WorkspaceSidebar.svelte"
    import { onMount } from "svelte"
    import { push } from 'svelte-spa-router'

    type ThemeMode = "system" | "light" | "dark"
    let refreshKey = 0
    let themeMode: ThemeMode = "system"
    let language: "en" | "ru" = "en"
    let viewMode: "grid" | "list" = "grid"
    let viewModeLoaded = false
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

<div class="workspace-layout">
  <aside class="workspace-sidebar panel">
    <WorkspaceSidebar
      on:navigateAbout={() => push('/about')}
      on:navigateArchive={() => push('/archive')}
      on:navigateAssistant={() => push('/assistant')}
      on:navigateSettings={() => push('/settings')}
    />
  </aside>

  <div class="workspace-main">
    <Upload on:uploaded={handleUpload} />

    <DocumentList
      {refreshKey}
      {viewMode}
      {columnCount}
      on:viewModeChange={(event) => {
          viewMode = event.detail.mode
      }}
    />
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


<!--
<LifeguardHelp bind:viewMode bind:columnCount />


-->

<style>
.workspace-layout {
    display: grid;
    grid-template-columns: 240px minmax(0, 1fr);
    gap: 16px;
    align-items: start;
}

.workspace-sidebar {
    position: sticky;
    top: 1rem;
    padding: 12px;
}

.workspace-main {
    min-width: 0;
}

@media (max-width: 640px) {
    .workspace-layout {
        grid-template-columns: 1fr;
        gap: 12px;
    }

    .workspace-sidebar {
        position: static;
    }
}
</style>
