<script lang="ts">
  import { createEventDispatcher, onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import {
    createFolder,
    deleteFolder,
    getFolderContents,
    getFolderTree,
    moveDocumentToFolder,
    moveFolder,
    renameFolder
  } from "../api"
  import type { Document, Folder, FolderPathItem } from "../types"

  export let canEdit = false

  const dispatch = createEventDispatcher<{ folderChange: { folderId: string | null } }>()

  type DragItem = {
    type: "document" | "folder"
    id: string
    currentParentId?: string | null
    isSystem?: boolean
  }

  let loading = true
  let error = ""
  let search = ""

  let currentFolderId: string | null = null
  let currentFolder: Folder | null = null
  let breadcrumbs: FolderPathItem[] = []
  let unsortedFolderId: string | null = null
  let folders: Folder[] = []
  let documents: Document[] = []
  let allFoldersFlat: Folder[] = []

  let dragItem: DragItem | null = null
  let dropTargetFolderId: string | null = null
  let rootDropActive = false

  let moveDialogOpen = false
  let moveDialogItem: DragItem | null = null
  let moveTargetId = ""

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

  function folderById(folderId: string | null | undefined) {
    if (!folderId) return null
    return allFoldersFlat.find((item) => item.id === folderId) ?? null
  }

  function flattenTree(tree: Folder[]): Folder[] {
    const stack = [...tree]
    const flat: Folder[] = []
    while (stack.length) {
      const item = stack.shift()
      if (!item) continue
      flat.push(item)
      if (item.children?.length) stack.unshift(...item.children)
    }
    return flat
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
    if (dragItem.type === "document") return dragItem.currentParentId !== targetFolderId

    if (dragItem.isSystem) return false
    if (dragItem.id === targetFolderId) return false
    if (isDescendant(dragItem.id, targetFolderId)) return false
    return true
  }

  function canDropToRoot() {
    if (!dragItem) return false
    if (dragItem.type === "document") {
      return Boolean(unsortedFolderId) && dragItem.currentParentId !== unsortedFolderId
    }
    return !dragItem.isSystem && dragItem.currentParentId !== null
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
        folders = treeFolders.filter((item) => !item.parent_id)
        documents = []
      } else {
        const contents = await getFolderContents(requestedFolderId)
        currentFolderId = contents.folder?.id ?? requestedFolderId
        currentFolder = contents.folder ?? null
        breadcrumbs = currentFolder?.path ?? []
        folders = contents.subfolders ?? []
        documents = contents.documents ?? []
      }

      dispatch("folderChange", { folderId: currentFolderId ?? unsortedFolderId ?? null })
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось загрузить папки"
    } finally {
      loading = false
    }
  }

  function openFolder(folderId: string | null) {
    currentFolderId = folderId
    setFolderInHash(folderId)
    void load(folderId)
  }

  async function executeMove(item: DragItem, targetFolderId: string | null) {
    try {
      if (item.type === "document") {
        const destination = targetFolderId || unsortedFolderId
        if (!destination) throw new Error("Папка Unsorted не найдена")
        await moveDocumentToFolder(item.id, destination)
      } else {
        await moveFolder(item.id, targetFolderId)
      }
      await load(currentFolderId)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось переместить")
    } finally {
      dragItem = null
      dropTargetFolderId = null
      rootDropActive = false
      moveDialogOpen = false
      moveDialogItem = null
    }
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
  }

  async function dropOnFolder(event: DragEvent, folderId: string) {
    if (!dragItem || !canDropOnFolder(folderId)) return
    event.preventDefault()
    await executeMove(dragItem, folderId)
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
    const target = dragItem.type === "document" ? unsortedFolderId : null
    await executeMove(dragItem, target)
  }

  function dragEnd() {
    dragItem = null
    dropTargetFolderId = null
    rootDropActive = false
  }

  async function handleCreateFolder() {
    if (!canEdit) return
    const name = prompt("Название папки")?.trim()
    if (!name) return
    await createFolder(name, currentFolderId)
    await load(currentFolderId)
  }

  async function handleRenameFolder(folder: Folder) {
    if (!canEdit || folder.is_system) return
    const name = prompt("Новое имя папки", folder.name)?.trim()
    if (!name || name === folder.name) return
    await renameFolder(folder.id, name)
    await load(currentFolderId)
  }

  async function handleDeleteFolder(folder: Folder) {
    if (!canEdit || folder.is_system) return
    if (!confirm(`Удалить папку «${folder.name}»?`)) return
    await deleteFolder(folder.id)
    await load(currentFolderId)
  }

  function openMoveDialog(item: DragItem) {
    moveDialogItem = item
    moveTargetId = item.type === "document" ? (unsortedFolderId ?? "") : (item.currentParentId ?? "")
    moveDialogOpen = true
  }

  async function confirmMoveDialog() {
    if (!moveDialogItem) return
    await executeMove(moveDialogItem, moveTargetId || null)
  }

  function openDocument(doc: Document) {
    push(`/documents/${doc._id}`)
  }

  $: filteredFolders = folders.filter((folder) => folder.name.toLowerCase().includes(search.trim().toLowerCase()))
  $: filteredDocs = documents.filter((doc) => (doc.display_filename || doc.filename || "").toLowerCase().includes(search.trim().toLowerCase()))
  $: moveCandidates = allFoldersFlat.filter((folder) => {
    if (!moveDialogItem) return true
    if (moveDialogItem.type === "document") return true
    if (folder.id === moveDialogItem.id) return false
    if (isDescendant(moveDialogItem.id, folder.id)) return false
    return true
  })

  onMount(() => {
    void load(getFolderIdFromHash())
  })
</script>

<div class="folder-view panel">
  <div class="folder-toolbar">
    <input class="my-input" placeholder="Поиск в папке" bind:value={search} />
    {#if canEdit}
      <button class="primary" on:click={handleCreateFolder}>+ Папка</button>
    {/if}
  </div>

  <nav class="breadcrumbs">
    <button class="crumb" on:click={() => openFolder(null)}>Root</button>
    {#if unsortedFolderId}
      <span>/</span>
      <button class="crumb" on:click={() => openFolder(unsortedFolderId)}>Unsorted</button>
    {/if}
    {#each breadcrumbs as crumb}
      {#if !unsortedFolderId || crumb.id !== unsortedFolderId}
        <span>/</span>
        <button class="crumb" on:click={() => openFolder(crumb.id)}>{crumb.name}</button>
      {/if}
    {/each}
  </nav>

  <div class="root-drop-zone" class:active={rootDropActive} on:dragover={dragOverRoot} on:dragleave={dragLeaveRoot} on:drop={dropOnRoot}>
    Drop here to move to {dragItem?.type === "folder" ? "Root" : "Unsorted"}
  </div>

  {#if loading}
    <p>Загрузка…</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else}
    <table class="finder-table">
      <thead>
        <tr><th></th><th>Имя</th><th>Тип</th><th>Действия</th></tr>
      </thead>
      <tbody>
        {#each filteredFolders as folder (folder.id)}
          <tr class:drop-target={dropTargetFolderId === folder.id} draggable={canEdit && !folder.is_system} on:dragstart={(e)=>dragStartFolder(e, folder)} on:dragend={dragEnd} on:dragover={(e)=>dragOverFolder(e, folder.id)} on:drop={(e)=>dropOnFolder(e, folder.id)}>
            <td>⋮⋮</td>
            <td><button class="linkish" on:click={() => openFolder(folder.id)}>📁 {folder.name}</button> {#if folder.is_system}<span class="system-pill">system</span>{/if}</td>
            <td>Folder</td>
            <td>
              <button on:click={() => openFolder(folder.id)}>Open</button>
              {#if canEdit && !folder.is_system}
                <button on:click={() => openMoveDialog({ type: 'folder', id: folder.id, currentParentId: folder.parent_id, isSystem: folder.is_system })}>Move to…</button>
                <button on:click={() => handleRenameFolder(folder)}>Rename</button>
                <button class="danger" on:click={() => handleDeleteFolder(folder)}>Delete</button>
              {/if}
            </td>
          </tr>
        {/each}

        {#each filteredDocs as doc (doc._id)}
          <tr draggable={canEdit} on:dragstart={(e)=>dragStartDocument(e, doc)} on:dragend={dragEnd}>
            <td>⋮⋮</td>
            <td><button class="linkish" on:click={() => openDocument(doc)}>📄 {doc.display_filename || doc.filename}</button></td>
            <td>Document</td>
            <td>
              <button on:click={() => openDocument(doc)}>Open</button>
              {#if canEdit}
                <button on:click={() => openMoveDialog({ type: 'document', id: doc._id, currentParentId: currentFolderId })}>Move to…</button>
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
  {/if}
</div>

{#if moveDialogOpen && moveDialogItem}
  <div class="modal-bg" on:click={() => moveDialogOpen = false}>
    <div class="panel modal" on:click|stopPropagation>
      <h3>Move {moveDialogItem.type}</h3>
      <select bind:value={moveTargetId}>
        {#if moveDialogItem.type === 'folder'}
          <option value="">Root</option>
        {:else if unsortedFolderId}
          <option value={unsortedFolderId}>Unsorted</option>
        {/if}
        {#each moveCandidates as folder (folder.id)}
          <option value={folder.id}>{folder.name}</option>
        {/each}
      </select>
      <div class="modal-actions">
        <button class="primary" on:click={confirmMoveDialog}>Move</button>
        <button on:click={() => moveDialogOpen = false}>Cancel</button>
      </div>
    </div>
  </div>
{/if}

<style>
  .folder-view { padding: 12px; }
  .folder-toolbar { display: flex; gap: 8px; margin-bottom: 8px; }
  .breadcrumbs { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }
  .crumb { border: 0; background: transparent; text-decoration: underline; color: var(--text-muted); padding: 0; }
  .root-drop-zone { border: 1px dashed var(--border); border-radius: 10px; padding: 8px; margin-bottom: 10px; }
  .root-drop-zone.active { border-color: var(--primary); background: color-mix(in srgb, var(--primary), transparent 90%); }
  .finder-table { width: 100%; border-collapse: collapse; }
  .finder-table th, .finder-table td { padding: 9px; border-bottom: 1px solid var(--border); text-align: left; }
  .finder-table tr.drop-target { background: color-mix(in srgb, var(--primary), transparent 88%); }
  .linkish { border: 0; background: transparent; padding: 0; text-decoration: none; }
  .linkish:hover { text-decoration: underline; }
  .system-pill { font-size: .72rem; border: 1px solid var(--border); border-radius: 999px; padding: 2px 8px; color: var(--text-muted); }
  .modal-bg { position: fixed; inset: 0; background: rgba(0,0,0,.35); display: grid; place-items: center; z-index: 1200; }
  .modal { width: min(420px, calc(100vw - 24px)); display: grid; gap: 10px; }
  .modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
  .error { color: var(--danger); }
</style>
