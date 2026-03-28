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

  {#if sidebarOpen}
    <button
      type="button"
      class="sidebar-backdrop"
      aria-label="Закрыть боковую панель"
      on:click={toggleSidebar}
    ></button>
  {/if}

  <aside class="workspace-sidebar panel" class:open={sidebarOpen} aria-hidden={!sidebarOpen}>
    <div class="sidebar-scroll">
      <WorkspaceSidebar
        on:navigateAbout={() => push('/about')}
        on:navigateArchive={() => push('/archive')}
        on:navigateAssistant={() => push('/assistant')}
        on:navigateSettings={() => push('/settings')}
      />
      <Upload embedded on:uploaded={handleUpload} />
    </div>
  </aside>

  <div class="workspace-layout">
    <div class="workspace-main">
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
    position: relative;
    min-height: calc(100vh - 4rem);
}

.sidebar-toggle {
    position: fixed;
    top: 1.15rem;
    left: max(1rem, calc((100vw - min(90%, 100%)) / 2 + 0.2rem));
    width: 34px;
    height: 34px;
    padding: 0;
    border-radius: 10px;
    border-color: transparent;
    background: color-mix(in srgb, var(--surface), transparent 10%);
    color: var(--text-muted);
    font-size: 1rem;
    line-height: 1;
    z-index: 45;
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
    min-width: 0;
}

.workspace-sidebar {
    position: fixed;
    top: 0.8rem;
    left: max(0.8rem, calc((100vw - min(90%, 100%)) / 2));
    width: min(320px, calc(100vw - 1.6rem));
    max-height: calc(100vh - 1.6rem);
    padding: 12px;
    transform: translateX(calc(-100% - 20px));
    opacity: 0;
    pointer-events: none;
    z-index: 40;
    transition: transform 170ms ease, opacity 140ms ease;
}

.workspace-sidebar.open {
    transform: translateX(0);
    opacity: 1;
    pointer-events: auto;
}

.sidebar-scroll {
    max-height: calc(100vh - 4rem);
    overflow: auto;
}

.workspace-main {
    min-width: 0;
}

.sidebar-backdrop {
    position: fixed;
    inset: 0;
    border: 0;
    background: rgba(11, 15, 22, 0.24);
    backdrop-filter: blur(1px);
    z-index: 35;
}

@media (max-width: 640px) {
    .workspace-shell {
        min-height: calc(100vh - 2rem);
    }

    .sidebar-toggle {
        top: 0.7rem;
        left: 0.65rem;
    }

    .workspace-sidebar {
        top: 0.4rem;
        left: 0.4rem;
        width: calc(100vw - 0.8rem);
        max-height: calc(100vh - 0.8rem);
    }
}
</style>
