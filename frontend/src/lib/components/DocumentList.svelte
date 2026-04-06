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
    moveDocumentToFolder,
    moveFolder,
    renameFolder
  } from "../api"
  import type { Document, Folder, FolderPathItem } from "../types"

  export let refreshKey: number
  export let viewMode: "grid" | "list" = "grid"
  export let canEdit = false
  export let activeTag: string | null = null
  export let sidebarOpen = true

  const dispatch = createEventDispatcher<{
    viewModeChange: { mode: "grid" | "list" }
    toggleSidebar: void
    folderChange: { folderId: string | null }
  }>()

  type DragItem = {
    type: "document" | "folder"
    id: string
    currentParentId?: string | null
    isSystem?: boolean
  }

  let search = ""
  let loading = true
  let error = ""

  let folders: Folder[] = []
  let documents: Document[] = []
  let currentFolder: Folder | null = null
  let currentFolderId: string | null = null
  let breadcrumbs: FolderPathItem[] = []
  let unsortedFolderId: string | null = null
  let allFoldersFlat: Folder[] = []

  let dragItem: DragItem | null = null
  let dropTargetFolderId: string | null = null
  let rootDropActive = false
  let moving = false

  let moveDialogOpen = false
  let moveDialogItem: DragItem | null = null
  let moveTargetId = ""

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

  function folderById(folderId: string | null | undefined) {
    if (!folderId) return null
    return allFoldersFlat.find((item) => item.id === folderId) ?? null
  }

  function isDescendant(ancestorFolderId: string, candidateFolderId: string) {
    let current = folderById(candidateFolderId)
    const visited = new Set<string>()
    while (current?.parent_id) {
      if (visited.has(current.id)) return false
      visited.add(current.id)
      if (current.parent_id === ancestorFolderId) return true
      current = folderById(current.parent_id)
    }
    return false
  }

  function canDropOnFolder(targetFolderId: string) {
    if (!dragItem) return false

    if (dragItem.type === "document") {
      return dragItem.currentParentId !== targetFolderId
    }

    if (dragItem.type === "folder") {
      if (dragItem.isSystem) return false
      if (dragItem.id === targetFolderId) return false
      if (isDescendant(dragItem.id, targetFolderId)) return false
      return true
    }

    return false
  }

  function canDropToRoot() {
    if (!dragItem) return false

    if (dragItem.type === "document") {
      return Boolean(unsortedFolderId) && dragItem.currentParentId !== unsortedFolderId
    }

    if (dragItem.type === "folder") {
      return !dragItem.isSystem && dragItem.currentParentId !== null
    }

    return false
  }

  async function executeMove(item: DragItem, targetFolderId: string | null) {
    if (moving) return
    moving = true
    error = ""

    try {
      if (item.type === "document") {
        const destinationId = targetFolderId || unsortedFolderId
        if (!destinationId) throw new Error("Папка Unsorted не найдена")
        await moveDocumentToFolder(item.id, destinationId)
      } else {
        await moveFolder(item.id, targetFolderId)
      }

      await load(currentFolderId)
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось переместить"
    } finally {
      moving = false
      dragItem = null
      dropTargetFolderId = null
      rootDropActive = false
    }
  }

  async function load(folderOverride?: string | null) {
    loading = true
    error = ""
    try {
      const treeResponse = await getFolderTree()
      const treeFolders = (treeResponse?.folders ?? []) as Folder[]
      allFoldersFlat = flattenTree(treeFolders)

      const unsorted = allFoldersFlat.find((folder) => folder.system_key === "unsorted")
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

  function openMoveDialog(item: DragItem) {
    moveDialogItem = item
    moveDialogOpen = true
    moveTargetId = item.type === "document" ? (unsortedFolderId ?? "") : (item.currentParentId ?? "")
  }

  async function confirmMoveDialog() {
    if (!moveDialogItem) return
    const target = moveTargetId || null
    await executeMove(moveDialogItem, target)
    moveDialogOpen = false
    moveDialogItem = null
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

  function dragStartDocument(event: DragEvent, doc: Document) {
    dragItem = { type: "document", id: doc._id, currentParentId: currentFolderId }
    event.dataTransfer?.setData("text/plain", doc._id)
    if (event.dataTransfer) event.dataTransfer.effectAllowed = "move"
  }

  function dragStartFolder(event: DragEvent, folder: Folder) {
    dragItem = { type: "folder", id: folder.id, currentParentId: folder.parent_id, isSystem: folder.is_system }
    event.dataTransfer?.setData("text/plain", folder.id)
    if (event.dataTransfer) event.dataTransfer.effectAllowed = "move"
  }

  function dragOverFolder(event: DragEvent, folderId: string) {
    if (!canDropOnFolder(folderId)) return
    event.preventDefault()
    dropTargetFolderId = folderId
    if (event.dataTransfer) event.dataTransfer.dropEffect = "move"
  }

  function dragLeaveFolder(folderId: string) {
    if (dropTargetFolderId === folderId) dropTargetFolderId = null
  }

  async function dropOnFolder(event: DragEvent, folderId: string) {
    if (!dragItem || !canDropOnFolder(folderId)) return
    event.preventDefault()
    const item = dragItem
    await executeMove(item, folderId)
  }

  function dragOverRoot(event: DragEvent) {
    if (!canDropToRoot()) return
    event.preventDefault()
    rootDropActive = true
  }

  function dragLeaveRoot() {
    rootDropActive = false
  }

  async function dropOnRoot(event: DragEvent) {
    if (!dragItem || !canDropToRoot()) return
    event.preventDefault()
    rootDropActive = false
    const target = dragItem.type === "document" ? unsortedFolderId : null
    await executeMove(dragItem, target)
  }

  function dragEnd() {
    dragItem = null
    dropTargetFolderId = null
    rootDropActive = false
  }

  $: filteredFolders = folders.filter((folder) => folderMatches(folder))
  $: filteredDocuments = documents.filter((doc) => {
    const matchesTag = !activeTag || doc.tags?.includes(activeTag)
    return matchesTag && documentMatches(doc)
  })

  $: moveCandidates = allFoldersFlat.filter((folder) => {
    if (!moveDialogItem) return true
    if (moveDialogItem.type === "document") return true
    if (moveDialogItem.id === folder.id) return false
    if (isDescendant(moveDialogItem.id, folder.id)) return false
    return true
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

  <div
    class="root-drop-zone"
    class:active={rootDropActive}
    class:disabled={!canDropToRoot()}
    role="region"
    aria-label="Drop zone"
    on:dragover={dragOverRoot}
    on:dragleave={dragLeaveRoot}
    on:drop={dropOnRoot}
  >
    Drop here to move to {dragItem?.type === "folder" ? "Root" : "Unsorted"}
  </div>

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
      <article
        class="folder-card panel"
        class:drop-target={dropTargetFolderId === folder.id}
        draggable={canEdit && !folder.is_system}
        on:dragstart={(event) => dragStartFolder(event, folder)}
        on:dragend={dragEnd}
        on:dragover={(event) => dragOverFolder(event, folder.id)}
        on:dragleave={() => dragLeaveFolder(folder.id)}
        on:drop={(event) => dropOnFolder(event, folder.id)}
      >
        <button class="folder-open" on:click={() => openFolder(folder.id)}>📁 {folder.name}</button>
        <div class="folder-meta">
          {#if folder.is_system}<span class="system-pill">system</span>{/if}
          <span class="drag-tip">⇅</span>
          {#if canEdit && !folder.is_system}
            <button class="secondary tiny" on:click={() => openMoveDialog({ type: "folder", id: folder.id, currentParentId: folder.parent_id, isSystem: folder.is_system })}>Move to…</button>
            <button class="secondary tiny" on:click={() => handleRenameFolder(folder)}>Rename</button>
            <button class="danger tiny" on:click={() => handleDeleteFolder(folder)}>Delete</button>
          {/if}
        </div>
      </article>
    {/each}

    {#each filteredDocuments as doc (doc._id)}
      <div
        class="doc-draggable"
        draggable={canEdit}
        role="group"
        aria-label={`Document ${doc.display_filename || doc.filename}`}
        on:dragstart={(event) => dragStartDocument(event, doc)}
        on:dragend={dragEnd}
      >
        <DocumentCard
          {doc}
          {canEdit}
          search={search}
          selected={false}
          selectionActive={false}
          on:deleted={(e) => handleDeleteDocument(e.detail.id)}
        />
        {#if canEdit}
          <div class="doc-card-actions">
            <button class="secondary tiny" on:click={() => openMoveDialog({ type: "document", id: doc._id, currentParentId: currentFolderId })}>Move to…</button>
          </div>
        {/if}
      </div>
    {/each}
  </div>
{:else}
  <div class="panel table-wrap">
    <table class="mixed-table finder-like">
      <thead>
        <tr>
          <th style="width: 44px"></th>
          <th>Имя</th>
          <th>Тип</th>
          <th>Создано</th>
          <th>Теги</th>
          <th>Действия</th>
        </tr>
      </thead>
      <tbody>
        {#each filteredFolders as folder (folder.id)}
          <tr
            class="folder-row"
            class:drop-target={dropTargetFolderId === folder.id}
            draggable={canEdit && !folder.is_system}
            on:dragstart={(event) => dragStartFolder(event, folder)}
            on:dragend={dragEnd}
            on:dragover={(event) => dragOverFolder(event, folder.id)}
            on:dragleave={() => dragLeaveFolder(folder.id)}
            on:drop={(event) => dropOnFolder(event, folder.id)}
          >
            <td class="drag-col">{#if canEdit && !folder.is_system}<span class="drag-tip">⋮⋮</span>{/if}</td>
            <td>
              <button class="linkish main-link" on:click={() => openFolder(folder.id)}>📁 {folder.name}</button>
              {#if folder.is_system}<span class="system-pill">system</span>{/if}
            </td>
            <td><span class="type-pill folder">Folder</span></td>
            <td>{folder.created_at ? new Date(folder.created_at).toLocaleString() : "—"}</td>
            <td>—</td>
            <td class="actions">
              <button class="secondary tiny" on:click={() => openFolder(folder.id)}>Open</button>
              {#if canEdit && !folder.is_system}
                <button class="secondary tiny" on:click={() => openMoveDialog({ type: "folder", id: folder.id, currentParentId: folder.parent_id, isSystem: folder.is_system })}>Move to…</button>
                <button class="secondary tiny" on:click={() => handleRenameFolder(folder)}>Rename</button>
                <button class="danger tiny" on:click={() => handleDeleteFolder(folder)}>Delete</button>
              {/if}
            </td>
          </tr>
        {/each}

        {#each filteredDocuments as doc (doc._id)}
          <tr class="doc-row" draggable={canEdit} on:dragstart={(event) => dragStartDocument(event, doc)} on:dragend={dragEnd}>
            <td class="drag-col">{#if canEdit}<span class="drag-tip">⋮⋮</span>{/if}</td>
            <td><button class="linkish main-link" on:click={() => openDocument(doc)}>📄 {doc.display_filename || doc.filename}</button></td>
            <td><span class="type-pill doc">Document</span></td>
            <td>{doc.created_at ? new Date(doc.created_at).toLocaleString() : "—"}</td>
            <td>{doc.tags?.join(", ") || "—"}</td>
            <td class="actions">
              <button class="secondary tiny" on:click={() => openDocument(doc)}>Open</button>
              {#if canEdit}
                <button class="secondary tiny" on:click={() => openMoveDialog({ type: "document", id: doc._id, currentParentId: currentFolderId })}>Move to…</button>
                <button class="danger tiny" on:click={() => handleDeleteDocument(doc._id)}>Delete</button>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  </div>
{/if}

{#if moveDialogOpen && moveDialogItem}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="move-modal-backdrop" on:click={() => moveDialogOpen = false}>
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="move-modal panel" on:click|stopPropagation>
      <h3>Move {moveDialogItem.type === "folder" ? "folder" : "document"}</h3>
      <select bind:value={moveTargetId}>
        {#if moveDialogItem.type === "folder"}
          <option value="">Root</option>
        {:else if unsortedFolderId}
          <option value={unsortedFolderId}>Unsorted</option>
        {/if}
        {#each moveCandidates as folder (folder.id)}
          <option value={folder.id}>{folder.name}</option>
        {/each}
      </select>
      <div class="move-modal-actions">
        <button class="primary" on:click={confirmMoveDialog} disabled={moving}>Move</button>
        <button on:click={() => moveDialogOpen = false}>Cancel</button>
      </div>
    </div>
  </div>
{/if}

<style>
.search-manager { padding: 10px 12px; margin-bottom: 16px; text-align: left; }
.controls-row { display: flex; justify-content: left; align-items: center; gap: 8px; flex-wrap: wrap; }
.compact-search { min-width: min(340px, 100%); flex: 1 1 260px; }
.sidebar-toggle-inline { width: 34px; min-width: 34px; height: 34px; padding: 0; border-radius: 10px; }
.breadcrumbs { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.crumb { background: transparent; border: 0; padding: 0; text-decoration: underline; color: var(--text-muted); }
.root-drop-zone { margin-top: 10px; border: 1px dashed var(--border); border-radius: 10px; padding: 8px 10px; color: var(--text-muted); }
.root-drop-zone.active { border-color: var(--primary); background: color-mix(in srgb, var(--primary), transparent 88%); }
.root-drop-zone.disabled { opacity: .6; }
.current-folder-row { margin-top: 8px; display: flex; align-items: center; gap: 8px; }
.grid-fallback { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: 12px; }
.folder-card { padding: 14px; display: grid; gap: 10px; transition: border-color .12s ease, background .12s ease; }
.folder-card.drop-target,
tr.drop-target { border: 1px solid color-mix(in srgb, var(--primary), var(--border) 30%); background: color-mix(in srgb, var(--primary), transparent 90%); }
.folder-open { text-align: left; font-weight: 700; }
.folder-meta { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.drag-tip { color: var(--text-muted); cursor: grab; }
.system-pill { font-size: .72rem; border: 1px solid var(--border); border-radius: 999px; padding: 2px 8px; color: var(--text-muted); }
.table-wrap { overflow-x: auto; }
.mixed-table { width: 100%; border-collapse: collapse; }
.mixed-table th, .mixed-table td { padding: 10px; border-bottom: 1px solid var(--border); text-align: left; vertical-align: middle; }
.finder-like tbody tr { transition: background .12s ease; }
.finder-like tbody tr:hover { background: color-mix(in srgb, var(--surface), var(--primary) 6%); }
.drag-col { width: 40px; text-align: center; }
.main-link { font-weight: 500; }
.type-pill { font-size: .72rem; border-radius: 999px; padding: 3px 8px; border: 1px solid var(--border); }
.type-pill.folder { background: color-mix(in srgb, var(--primary), transparent 80%); }
.type-pill.doc { background: color-mix(in srgb, #7cfc98, transparent 78%); }
.linkish { border: 0; background: transparent; padding: 0; text-decoration: none; color: inherit; }
.linkish:hover { text-decoration: underline; }
.actions { white-space: nowrap; }
.tiny { font-size: .78rem; padding: 5px 8px; }
.error { color: var(--danger); }
.doc-draggable { position: relative; }
.doc-card-actions { margin-top: -6px; margin-bottom: 8px; display: flex; justify-content: flex-end; }

.move-modal-backdrop { position: fixed; inset: 0; background: rgba(8, 11, 19, 0.44); display: grid; place-items: center; z-index: 1200; }
.move-modal { width: min(480px, calc(100vw - 28px)); display: grid; gap: 12px; }
.move-modal select { width: 100%; min-height: 38px; }
.move-modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
