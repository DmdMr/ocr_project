<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import DocumentCard from "./DocumentCard.svelte"
  import {
    createFolder,
    deleteDocument,
    deleteFolder,
    getFolderContents,
    getFolderTree,
    renameFolder
  } from "../api"
  import type { Document, Folder, FolderPathItem } from "../types"

  export let refreshKey: number
  export let viewMode: "grid" | "list" = "grid"
  export let canEdit = false
  export let isAdmin = false
  export let activeTag: string | null = null
  export let sidebarOpen = true

  const dispatch = createEventDispatcher<{
    viewModeChange: { mode: "grid" | "list" }
    toggleSidebar: void
    folderChange: { folderId: string | null }
  }>()

  let search = ""
  let loading = true
  let error = ""

  let folders: Folder[] = []
  let documents: Document[] = []
  let currentFolder: Folder | null = null
  let currentFolderId: string | null = null
  let breadcrumbs: FolderPathItem[] = []
  let unsortedFolderId: string | null = null

  function setViewMode(mode: "grid" | "list") {
    viewMode = mode
    dispatch("viewModeChange", { mode })
  }

  function getFolderIdFromHash() {
    const rawHash = window.location.hash || "#/"
    const hashWithoutPrefix = rawHash.startsWith("#") ? rawHash.slice(1) : rawHash
    const [pathPart, queryPart] = hashWithoutPrefix.split("?")
    if ((pathPart || "/") !== "/") return null
    const params = new URLSearchParams(queryPart || "")
    return params.get("folder")
  }

  function setFolderInHash(folderId: string | null) {
    const nextHash = folderId ? `#/?folder=${encodeURIComponent(folderId)}` : "#/"
    if (window.location.hash !== nextHash) {
      window.location.hash = nextHash
    }
  }

  function flattenTree(tree: Folder[]): Folder[] {
    const stack = [...tree]
    const flat: Folder[] = []
    while (stack.length) {
      const item = stack.shift()
      if (!item) continue
      flat.push(item)
      if (item.children?.length) {
        stack.unshift(...item.children)
      }
    }
    return flat
  }

  function topLevelFolders(tree: Folder[]) {
    return tree.filter((item) => !item.parent_id)
  }

  async function load(folderOverride?: string | null) {
    loading = true
    error = ""
    try {
      const treeResponse = await getFolderTree()
      const treeFolders = (treeResponse?.folders ?? []) as Folder[]
      const flatFolders = flattenTree(treeFolders)

      const unsorted = flatFolders.find((folder) => folder.system_key === "unsorted")
      unsortedFolderId = unsorted?.id ?? null

      const requestedFolderId = folderOverride ?? currentFolderId ?? getFolderIdFromHash() ?? unsortedFolderId

      if (!requestedFolderId) {
        currentFolderId = null
        currentFolder = null
        breadcrumbs = []
        folders = topLevelFolders(treeFolders)
        documents = []
      } else {
        const contents = await getFolderContents(requestedFolderId)
        currentFolder = contents.folder ?? null
        currentFolderId = contents.folder?.id ?? requestedFolderId
        breadcrumbs = currentFolder?.path ?? []
        folders = (contents.subfolders ?? []) as Folder[]
        documents = (contents.documents ?? []) as Document[]
      }

      dispatch("folderChange", { folderId: currentFolderId ?? unsortedFolderId ?? null })
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось загрузить содержимое"
    } finally {
      loading = false
    }
  }

  function openFolder(folderId: string | null) {
    currentFolderId = folderId
    setFolderInHash(folderId)
    void load(folderId)
  }

  async function handleCreateFolder() {
    if (!canEdit) return
    const name = prompt("Название папки")?.trim()
    if (!name) return
    try {
      await createFolder(name, currentFolderId)
      await load(currentFolderId)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось создать папку")
    }
  }

  async function handleRenameFolder(folder: Folder) {
    if (!canEdit || folder.is_system) return
    const nextName = prompt("Новое имя папки", folder.name)?.trim()
    if (!nextName || nextName === folder.name) return
    try {
      await renameFolder(folder.id, nextName)
      await load(currentFolderId)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось переименовать папку")
    }
  }

  async function handleDeleteFolder(folder: Folder) {
    if (!canEdit || folder.is_system) return
    const confirmed = confirm(`Удалить папку «${folder.name}»?`)
    if (!confirmed) return
    try {
      await deleteFolder(folder.id)
      await load(currentFolderId)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось удалить папку")
    }
  }

  async function handleDeleteDocument(id: string) {
    if (!canEdit) return
    const confirmed = confirm("Удалить карточку?")
    if (!confirmed) return
    try {
      await deleteDocument(id)
      documents = documents.filter((doc) => doc._id !== id)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось удалить карточку")
    }
  }

  function openDocument(doc: Document) {
    push(`/documents/${doc._id}`)
  }

  function folderMatches(folder: Folder) {
    if (!search.trim()) return true
    return folder.name.toLowerCase().includes(search.trim().toLowerCase())
  }

  function documentMatches(doc: Document) {
    const q = search.trim().toLowerCase()
    if (!q) return true
    return (
      (doc.display_filename || doc.filename || "").toLowerCase().includes(q) ||
      (doc.recognized_text || "").toLowerCase().includes(q) ||
      (doc.tags || []).some((tag) => tag.toLowerCase().includes(q))
    )
  }

  $: filteredFolders = folders.filter((folder) => folderMatches(folder))
  $: filteredDocuments = documents.filter((doc) => {
    const matchesTag = !activeTag || doc.tags?.includes(activeTag)
    return matchesTag && documentMatches(doc)
  })

  onMount(() => {
    const hashFolder = getFolderIdFromHash()
    void load(hashFolder)

    const onHashChange = () => {
      const nextFolderId = getFolderIdFromHash()
      if (nextFolderId !== currentFolderId) {
        currentFolderId = nextFolderId
        void load(nextFolderId)
      }
    }
    window.addEventListener("hashchange", onHashChange)

    return () => window.removeEventListener("hashchange", onHashChange)
  })

  $: if (refreshKey) {
    void load(currentFolderId)
  }
</script>

<div class="search-manager panel">
  <div class="controls-row compact-toolbar">
    <button
      type="button"
      class="sidebar-toggle-inline"
      class:active={sidebarOpen}
      aria-label={sidebarOpen ? "Скрыть боковую панель" : "Показать боковую панель"}
      title={sidebarOpen ? "Скрыть боковую панель" : "Показать боковую панель"}
      on:click={() => dispatch("toggleSidebar")}
    >☰</button>

    <input type="text" class="my-input compact-search" placeholder="Поиск в текущей папке" bind:value={search} />

    <div class="view-toggle" role="group" aria-label="Режим отображения">
      <button class="secondary" class:active={viewMode === "grid"} on:click={() => setViewMode("grid")}>Сетка</button>
      <button class="secondary" class:active={viewMode === "list"} on:click={() => setViewMode("list")}>Таблица</button>
    </div>

    {#if canEdit}
      <button class="primary" on:click={handleCreateFolder}>+ Папка</button>
    {/if}
  </div>

  <nav class="breadcrumbs" aria-label="Путь папки">
    <button class="crumb" on:click={() => openFolder(null)}>Root</button>
    {#if unsortedFolderId}
      <span>/</span>
      <button class="crumb" on:click={() => openFolder(unsortedFolderId)}>Unsorted</button>
    {/if}
    {#if breadcrumbs.length}
      {#each breadcrumbs as crumb}
        {#if !unsortedFolderId || crumb.id !== unsortedFolderId}
          <span>/</span>
          <button class="crumb" on:click={() => openFolder(crumb.id)}>{crumb.name}</button>
        {/if}
      {/each}
    {/if}
  </nav>

  {#if currentFolder}
    <div class="current-folder-row">
      <strong>Текущая папка:</strong> {currentFolder.name}
      {#if currentFolder.is_system}
        <span class="system-pill">system</span>
      {/if}
    </div>
  {/if}
</div>

{#if loading}
  <div class="panel">Загрузка...</div>
{:else if error}
  <div class="panel error">{error}</div>
{:else if viewMode === "grid"}
  <div class="grid-fallback">
    {#each filteredFolders as folder (folder.id)}
      <article class="folder-card panel">
        <button class="folder-open" on:click={() => openFolder(folder.id)}>
          📁 {folder.name}
        </button>
        <div class="folder-meta">
          {#if folder.is_system}<span class="system-pill">system</span>{/if}
          {#if canEdit && !folder.is_system}
            <button class="secondary tiny" on:click={() => handleRenameFolder(folder)}>Rename</button>
            <button class="danger tiny" on:click={() => handleDeleteFolder(folder)}>Delete</button>
          {/if}
        </div>
      </article>
    {/each}

    {#each filteredDocuments as doc (doc._id)}
      <DocumentCard
        {doc}
        {canEdit}
        search={search}
        selected={false}
        selectionActive={false}
        on:deleted={(e) => handleDeleteDocument(e.detail.id)}
      />
    {/each}
  </div>
{:else}
  <div class="panel table-wrap">
    <table class="mixed-table">
      <thead>
        <tr>
          <th>Тип</th>
          <th>Название</th>
          <th>Создано</th>
          <th>Теги</th>
          <th>Действия</th>
        </tr>
      </thead>
      <tbody>
        {#each filteredFolders as folder (folder.id)}
          <tr>
            <td><span class="type-pill folder">Folder</span></td>
            <td>
              <button class="linkish" on:click={() => openFolder(folder.id)}>📁 {folder.name}</button>
              {#if folder.is_system}<span class="system-pill">system</span>{/if}
            </td>
            <td>{folder.created_at ? new Date(folder.created_at).toLocaleString() : "—"}</td>
            <td>—</td>
            <td class="actions">
              <button class="secondary tiny" on:click={() => openFolder(folder.id)}>Open</button>
              {#if canEdit && !folder.is_system}
                <button class="secondary tiny" on:click={() => handleRenameFolder(folder)}>Rename</button>
                <button class="danger tiny" on:click={() => handleDeleteFolder(folder)}>Delete</button>
              {/if}
            </td>
          </tr>
        {/each}

        {#each filteredDocuments as doc (doc._id)}
          <tr>
            <td><span class="type-pill doc">Document</span></td>
            <td>
              <button class="linkish" on:click={() => openDocument(doc)}>{doc.display_filename || doc.filename}</button>
            </td>
            <td>{doc.created_at ? new Date(doc.created_at).toLocaleString() : "—"}</td>
            <td>{doc.tags?.join(", ") || "—"}</td>
            <td class="actions">
              <button class="secondary tiny" on:click={() => openDocument(doc)}>Open</button>
              {#if canEdit}
                <button class="danger tiny" on:click={() => handleDeleteDocument(doc._id)}>Delete</button>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}

<style>
.search-manager { padding: 10px 12px; margin-bottom: 16px; text-align: left; }
.controls-row { display: flex; justify-content: left; align-items: center; gap: 8px; flex-wrap: wrap; }
.compact-search { min-width: min(340px, 100%); flex: 1 1 260px; }
.sidebar-toggle-inline { width: 34px; min-width: 34px; height: 34px; padding: 0; border-radius: 10px; }
.breadcrumbs { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.crumb { background: transparent; border: 0; padding: 0; text-decoration: underline; color: var(--text-muted); }
.current-folder-row { margin-top: 8px; display: flex; align-items: center; gap: 8px; }
.grid-fallback { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.folder-card { padding: 14px; display: grid; gap: 10px; }
.folder-open { text-align: left; font-weight: 700; }
.folder-meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.system-pill { font-size: .72rem; border: 1px solid var(--border); border-radius: 999px; padding: 2px 8px; color: var(--text-muted); }
.table-wrap { overflow-x: auto; }
.mixed-table { width: 100%; border-collapse: collapse; }
.mixed-table th, .mixed-table td { padding: 10px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: middle; }
.type-pill { font-size: .72rem; border-radius: 999px; padding: 3px 8px; border: 1px solid var(--border); }
.type-pill.folder { background: color-mix(in srgb, var(--primary), transparent 80%); }
.type-pill.doc { background: color-mix(in srgb, #7cfc98, transparent 78%); }
.linkish { border: 0; background: transparent; padding: 0; text-decoration: underline; color: inherit; }
.actions { white-space: nowrap; }
.tiny { font-size: .78rem; padding: 5px 8px; }
.error { color: var(--danger); }
</style>
