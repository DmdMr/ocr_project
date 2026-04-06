<script lang="ts">
    import Upload from "./lib/components/Upload.svelte"
    import DocumentList from "./lib/components/DocumentList.svelte"
    import WorkspaceSidebar from "./lib/components/WorkspaceSidebar.svelte"
    import TagManager from "./lib/components/TagManager.svelte"
    import { getTags } from "./lib/api"
    import { onMount } from "svelte"
    import { push } from 'svelte-spa-router'
    import { canEditDocuments, currentUser, isAdmin, isAuthenticated, logout } from './lib/auth'

    type ThemeMode = "system" | "light" | "dark"
    let refreshKey = 0
    let themeMode: ThemeMode = "system"
    let language: "en" | "ru" = "en"
    let viewMode: "grid" | "list" | "folders" = "grid"
    let viewModeLoaded = false
    let columnCount = 5
    let columnsLoaded = false
    let sidebarOpen = true
    let sidebarStateLoaded = false
    let tags: string[] = []
    let activeTag: string | null = null
    let currentFolderId: string | null = null


    onMount(() => {
        const saved = localStorage.getItem("columnCount")
        if (saved) {
        columnCount = Number(saved)
        }
        columnsLoaded = true
    })

    onMount(async () => {
        try {
            tags = await getTags()
        } catch (error) {
            console.error("Failed to load tags for sidebar manager", error)
        }
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
        if (saved === "grid" || saved === "list" || saved === "folders") {
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
    type="button"
    class="sidebar-backdrop"
    class:open={sidebarOpen}
    aria-label="Закрыть боковую панель"
    on:click={toggleSidebar}
  ></button>

  <aside class="workspace-sidebar panel" class:open={sidebarOpen} aria-hidden={!sidebarOpen}>
    <div class="sidebar-scroll">
      <WorkspaceSidebar
        currentUsername={$currentUser?.username ?? null}
        role={$currentUser.role}
        isAuthenticated={$isAuthenticated}
        on:logout={async () => {
          await logout()
          push('/')
        }}
        on:navigateLogin={() => push('/login')}
        on:navigateAbout={() => push('/about')}
        on:navigateArchive={() => push('/archive')}
        on:navigateAssistant={() => push('/assistant')}
        on:navigateSettings={() => push('/settings')}
        on:navigateAdminUsers={() => push('/admin/users')}
        on:navigateActivity={() => push('/admin/activity')}
      />
      <TagManager
        initialTags={tags}
        canManage={$isAdmin}
        on:select={(event) => activeTag = event.detail.tag}
        on:tagsChanged={(event) => tags = event.detail.tags}
      />
      {#if $canEditDocuments}
        <Upload embedded folderId={currentFolderId} on:uploaded={handleUpload} />
      {:else}
        <div class="panel sign-in-hint">Sign in as editor/admin to upload and edit documents.</div>
      {/if}
    </div>
  </aside>

  <div class="workspace-layout">
    <div class="workspace-main">
      <DocumentList
        {refreshKey}
        {viewMode}
        {columnCount}
        {sidebarOpen}
        {activeTag}
        canEdit={$canEditDocuments}
        on:toggleSidebar={toggleSidebar}
        on:viewModeChange={(event) => {
            viewMode = event.detail.mode
        }}
        on:folderChange={(event) => {
            currentFolderId = event.detail.folderId
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
    overflow-x: hidden;
}

.workspace-layout {
    min-width: 0;
}

.workspace-sidebar {
    position: fixed;
    top: 0;
    left: 0;
    width: min(320px, 92vw);
    height: 100vh;
    border-radius: 0;
    padding: 12px;
    transform: translate3d(-100%, 0, 0);
    opacity: 0;
    pointer-events: none;
    z-index: 40;
    will-change: transform, opacity;
    transition: transform 150ms ease, opacity 130ms ease;
}

.workspace-sidebar.open {
    transform: translate3d(0, 0, 0);
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

.sign-in-hint {
    margin-top: 10px;
    padding: 10px;
    color: var(--text-muted);
}

.sidebar-backdrop {
    position: fixed;
    inset: 0;
    border: 0;
    background: rgba(11, 15, 22, 0);
    opacity: 0;
    pointer-events: none;
    z-index: 35;
    transition: opacity 130ms ease;
}

.sidebar-backdrop.open {
    background: rgba(11, 15, 22, 0.2);
    opacity: 1;
    pointer-events: auto;
}

@media (max-width: 640px) {
    .workspace-shell {
        min-height: calc(100vh - 2rem);
    }

    .workspace-sidebar {
        width: min(320px, 94vw);
    }
}
</style>
