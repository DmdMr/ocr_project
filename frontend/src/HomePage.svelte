<script lang="ts">
    import Upload from "./lib/components/Upload.svelte"
    import DocumentList from "./lib/components/DocumentList.svelte"
    import WorkspaceSidebar from "./lib/components/WorkspaceSidebar.svelte"
    import TagManager from "./lib/components/TagManager.svelte"
    import { getSystemNetwork, getTags, type SystemNetworkInfo } from "./lib/api"
    import { t } from "./lib/i18n"
    import { onMount } from "svelte"
    import { push } from 'svelte-spa-router'
    import { canEditDocuments, currentUser, isAdmin, isAuthenticated, logout } from './lib/auth'

    type ThemeMode = "system" | "light" | "dark"
    let refreshKey = 0
    let themeMode: ThemeMode = "system"
    let viewMode: "grid" | "list" | "files" = "grid"
    let viewModeLoaded = false
    let initialFolderId: string | null = null
    let columnCount = 5
    let columnsLoaded = false
    let sidebarOpen = true
    let sidebarStateLoaded = false
    let tags: string[] = []
    let activeTag: string | null = null
    let networkInfo: SystemNetworkInfo | null = null
    let networkStatus: "loading" | "online" | "offline" = "loading"
    let networkCopyStatus = ""


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

    onMount(async () => {
        try {
            networkInfo = await getSystemNetwork()
            networkStatus = "online"
        } catch (error) {
            console.error("Failed to load LAN network info", error)
            networkStatus = "offline"
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

    async function copyNetworkUrl() {
        if (!networkInfo?.url) return

        try {
            await navigator.clipboard.writeText(networkInfo.url)
            networkCopyStatus = $t("common.copied")
        } catch {
            networkCopyStatus = $t("common.copyFailed")
        }

        setTimeout(() => {
            networkCopyStatus = ""
        }, 1500)
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

    onMount(() => {
        const savedTheme = (localStorage.getItem("themeMode") as ThemeMode | null) ?? "system"
        applyTheme(savedTheme)
        const saved = localStorage.getItem("viewMode")
        if (saved === "grid" || saved === "list" || saved === "files") {
            viewMode = saved
        }
        const hash = window.location.hash || "#/"
        const [, rawQuery = ""] = hash.split("?")
        const params = new URLSearchParams(rawQuery)
        const viewParam = params.get("view")
        if (viewParam === "grid" || viewParam === "list" || viewParam === "files") {
            viewMode = viewParam
        }
        const folderParam = (params.get("folder") || "").trim()
        initialFolderId = folderParam || null
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
    aria-label={$t("common.close")}
    on:click={toggleSidebar}
  ></button>

  <aside class="workspace-sidebar panel" class:open={sidebarOpen} aria-hidden={!sidebarOpen}>
    <div class="sidebar-scroll">
      <section class="sidebar-section-group">
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
      </section>

      <section class="sidebar-section">
        <div class="sidebar-title">{$t("network.title")}</div>
        <div class="network-panel panel">
          <!-- Electron binds FastAPI to 0.0.0.0; this panel shows the LAN URL
            returned by /api/system/network so nearby devices can open the same
            SQLite-backed OCR workspace in a browser. -->
          <div class="network-url">{networkInfo?.url ?? $t("network.detecting")}</div>
          <div class:online={networkStatus === "online"} class:offline={networkStatus === "offline"} class="network-status">
            {$t("network.status")}: {networkStatus === "loading" ? $t("network.checking") : networkStatus === "online" ? $t("network.online") : $t("network.offline")}
          </div>
          <button type="button" on:click={copyNetworkUrl} disabled={!networkInfo?.url}>{$t("common.copy")}</button>
          {#if networkCopyStatus}
            <span class="copy-status">{networkCopyStatus}</span>
          {/if}
        </div>
      </section>

      <section class="sidebar-section">
        <div class="sidebar-title">{$t("sidebar.primaryActions")}</div>
        {#if $canEditDocuments}
          <Upload embedded on:uploaded={handleUpload} />
        {:else}
          <div class="panel sign-in-hint">{$t("sidebar.signInHint")}</div>
        {/if}
      </section>

      <section class="sidebar-section">
        <div class="sidebar-title">{$t("sidebar.tagsBlock")}</div>
        <TagManager
          initialTags={tags}
          canManage={$canEditDocuments}
          on:select={(event) => activeTag = event.detail.tag}
          on:tagsChanged={(event) => tags = event.detail.tags}
        />
      </section>

      
    </div>
  </aside>

  <div class="workspace-layout">
    <div class="workspace-main">
      <DocumentList
        {refreshKey}
        {viewMode}
        {initialFolderId}
        {columnCount}
        {sidebarOpen}
        {activeTag}
        canEdit={$canEditDocuments}
        isAdmin={$isAdmin}
        on:toggleSidebar={toggleSidebar}
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
    display: grid;
    gap: 18px;
    text-align: left;
}

.sidebar-section {
    display: grid;
    gap: 8px;
}

.sidebar-title {
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin-bottom: 2px;
    color: var(--text-muted);
}

.workspace-main {
    min-width: 0;
}

.sign-in-hint {
    margin-top: 10px;
    padding: 10px;
    color: var(--text-muted);
}

.network-panel {
    display: grid;
    gap: 8px;
    padding: 10px;
}

.network-url {
    overflow-wrap: anywhere;
    font-weight: 700;
}

.network-status {
    font-size: 0.9rem;
    color: var(--text-muted);
}

.network-status.online {
    color: #16a34a;
}

.network-status.offline {
    color: #ef4444;
}

.copy-status {
    font-size: 0.85rem;
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
