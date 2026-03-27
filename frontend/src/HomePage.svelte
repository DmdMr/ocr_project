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
    let sidebarOpen = true
    let sidebarStateLoaded = false


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

    function toggleSidebar() {
        sidebarOpen = !sidebarOpen
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
        const savedSidebar = localStorage.getItem("workspaceSidebarOpen")
        if (savedSidebar === "true" || savedSidebar === "false") {
            sidebarOpen = savedSidebar === "true"
        }
        sidebarStateLoaded = true
        viewModeLoaded = true
    })


    $: if (viewModeLoaded) {
        localStorage.setItem("viewMode", viewMode)
    }

    $: if (sidebarStateLoaded) {
        localStorage.setItem("workspaceSidebarOpen", String(sidebarOpen))
    }

</script>

<div class="workspace-shell">
  <button
    class="sidebar-toggle"
    class:collapsed={!sidebarOpen}
    type="button"
    aria-label={sidebarOpen ? "Скрыть боковую панель" : "Показать боковую панель"}
    title={sidebarOpen ? "Скрыть боковую панель" : "Показать боковую панель"}
    on:click={toggleSidebar}
  >
    ☰
  </button>

  <div class="workspace-layout">
    <aside class="workspace-sidebar panel" class:collapsed={!sidebarOpen} aria-hidden={!sidebarOpen}>
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
.workspace-shell {
    display: grid;
    gap: 10px;
}

.sidebar-toggle {
    justify-self: start;
    width: 34px;
    height: 34px;
    padding: 0;
    border-radius: 10px;
    border-color: transparent;
    background: color-mix(in srgb, var(--surface), transparent 10%);
    color: var(--text-muted);
    font-size: 1rem;
    line-height: 1;
}

.sidebar-toggle:hover {
    background: color-mix(in srgb, var(--surface), var(--bg-accent) 45%);
    color: var(--text);
}

.sidebar-toggle:active {
    transform: translateY(1px);
}

.sidebar-toggle.collapsed {
    color: var(--text);
}

.workspace-layout {
    display: flex;
    gap: 16px;
    align-items: start;
}

.workspace-sidebar {
    width: 240px;
    flex: 0 0 240px;
    position: sticky;
    top: 1rem;
    padding: 12px;
    overflow: hidden;
    transition: width 160ms ease, flex-basis 160ms ease, padding 160ms ease, opacity 140ms ease, transform 160ms ease, border-width 140ms ease;
}

.workspace-sidebar.collapsed {
    width: 0;
    flex-basis: 0;
    padding: 0;
    border-width: 0;
    opacity: 0;
    transform: translateX(-8px);
    pointer-events: none;
}

.workspace-main {
    flex: 1 1 auto;
    min-width: 0;
    transition: max-width 160ms ease;
}

@media (max-width: 640px) {
    .workspace-shell {
        gap: 8px;
    }

    .workspace-layout {
        gap: 10px;
    }

    .workspace-sidebar {
        position: static;
    }
}
</style>
