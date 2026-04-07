<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import {
    createFolder,
    deleteFolderById,
    getFolderContents,
    getFolderTree,
    moveDocumentToFolder,
    moveFolder,
    renameFolder
  } from "../api"
  import type { Document, FolderNode } from "../types"

  export let canEdit = false
  export let initialFolderId: string | null = null

  type FolderMap = Record<string, FolderNode>
  type FolderChildrenMap = Record<string, string[]>
  type DocsByFolderMap = Record<string, Document[]>
  type MoveState = { type: "folder" | "document"; id: string; name: string } | null
  type FolderPathNode = { id: string; name: string }
  type TreeRow =
    | { kind: "folder"; depth: number; folder: FolderNode }
    | { kind: "document"; depth: number; folderId: string; document: Document }

  let foldersById: FolderMap = {}
  let folderChildren: FolderChildrenMap = {}
  let docsByFolder: DocsByFolderMap = {}
  let expanded = new Set<string>()
  let loadedFolderContents = new Set<string>()
  let loadingFolderContents = new Set<string>()
  let selectedFolderId = ""
  let selectedDocument: Document | null = null
  let loading = false
  let error = ""

  let editingFolderId: string | null = null
  let renameDraft = ""
  let creatingUnderParentId: string | null = null
  let createDraft = ""

  let moveState: MoveState = null
  let moveTargetFolderId = ""
  let initialSelectionApplied = false

  const ROOT_ID = "__root__"
  let currentFolders: FolderNode[] = []
  let currentDocuments: Document[] = []

  function folderIdFrom(input: any): string {
    const raw = input?.id ?? input?._id ?? ""
    return typeof raw === "string" ? raw.trim() : ""
  }

  function normalizeFolderNode(input: any): FolderNode {
    const id = folderIdFrom(input)
    return {
      id,
      name: input?.name ?? "",
      parent_id: (input?.parent_id ?? null) as string | null,
      is_system: Boolean(input?.is_system),
      created_at: input?.created_at,
      updated_at: input?.updated_at,
      created_by_user_id: input?.created_by_user_id,
      created_by_username: input?.created_by_username,
      children: Array.isArray(input?.children) ? input.children.map(normalizeFolderNode) : []
    }
  }

  function indexTree(nodes: FolderNode[], parentId: string | null = null) {
    const key = parentId ?? ROOT_ID
    if (!folderChildren[key]) {
      folderChildren[key] = []
    }
    for (const node of nodes) {
      if (!node.id) continue
      foldersById[node.id] = { ...node, parent_id: node.parent_id ?? parentId }
      folderChildren[key].push(node.id)
      if (!folderChildren[node.id]) {
        folderChildren[node.id] = []
      }
      indexTree(node.children ?? [], node.id)
    }
  }

  function sortedFolderIds(parentId: string | null) {
    const ids = folderChildren[parentId ?? ROOT_ID] ?? []
    return [...ids].sort((left, right) => (foldersById[left]?.name || "").localeCompare(foldersById[right]?.name || ""))
  }

  function folderPath(folderId: string): FolderPathNode[] {
    const path: FolderPathNode[] = []
    let current = foldersById[folderId]
    const visited = new Set<string>()
    while (current && !visited.has(current.id)) {
      visited.add(current.id)
      path.push({ id: current.id, name: current.name })
      current = current.parent_id ? foldersById[current.parent_id] : null
    }
    return path.reverse()
  }

  async function loadTree() {
    loading = true
    error = ""
    try {
      const data = await getFolderTree()
      const normalized = (data.folders ?? []).map(normalizeFolderNode).filter((node: FolderNode) => Boolean(node.id))
      foldersById = {}
      folderChildren = {}
      indexTree(normalized)

      const unsorted = Object.values(foldersById).find((node) => node.is_system && node.name === "Unsorted")
      const currentStillExists = selectedFolderId && foldersById[selectedFolderId]
      const initial = (initialFolderId && foldersById[initialFolderId]?.id) || (currentStillExists ? selectedFolderId : "") || unsorted?.id || sortedFolderIds(null)[0] || ""
      selectedFolderId = initial
      selectedDocument = null
      loadedFolderContents = new Set()
      docsByFolder = {}
      if (initial) {
        expandAncestors(initial)
        await ensureFolderLoaded(initial)
      }
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось загрузить файловое дерево"
    } finally {
      loading = false
    }
  }

  function expandAncestors(folderId: string) {
    let current = foldersById[folderId]
    while (current?.parent_id) {
      expanded.add(current.parent_id)
      current = foldersById[current.parent_id]
    }
    expanded.add(folderId)
    expanded = new Set(expanded)
  }

  async function ensureFolderLoaded(folderId: string) {
    if (!folderId || loadedFolderContents.has(folderId) || loadingFolderContents.has(folderId)) return
    loadingFolderContents.add(folderId)
    try {
      const data = await getFolderContents(folderId)
      const rawFolders = data.folders ?? data.subfolders ?? []
      const rawDocuments = data.documents ?? data.docs ?? []
      const childFolders = rawFolders.map(normalizeFolderNode).filter((node: FolderNode) => Boolean(node.id))

      const nextFoldersById: FolderMap = { ...foldersById }
      const nextChildren: FolderChildrenMap = { ...folderChildren, [folderId]: [] }
      for (const child of childFolders) {
        nextFoldersById[child.id] = { ...child, parent_id: folderId }
        nextChildren[folderId].push(child.id)
        if (!nextChildren[child.id]) {
          nextChildren[child.id] = []
        }
      }
      foldersById = nextFoldersById
      folderChildren = nextChildren
      docsByFolder = { ...docsByFolder, [folderId]: rawDocuments }
      loadedFolderContents.add(folderId)
    } finally {
      loadingFolderContents.delete(folderId)
    }
  }

  async function toggleFolder(folderId: string) {
    if (expanded.has(folderId)) {
      expanded.delete(folderId)
      expanded = new Set(expanded)
      return
    }
    expanded.add(folderId)
    expanded = new Set(expanded)
    await ensureFolderLoaded(folderId)
  }

  async function selectFolder(folderId: string) {
    selectedFolderId = folderId
    selectedDocument = null
    expandAncestors(folderId)
    await ensureFolderLoaded(folderId)
  }

  async function openDocument(doc: Document) {
    selectedDocument = doc
    selectedFolderId = doc.folder_id || selectedFolderId
    push(`/documents/${doc._id}`)
  }

  function beginCreate(parentId: string | null) {
    creatingUnderParentId = parentId
    createDraft = ""
  }

  async function submitCreate() {
    if (!createDraft.trim()) return
    try {
      await createFolder(createDraft.trim(), creatingUnderParentId)
      creatingUnderParentId = null
      createDraft = ""
      await loadTree()
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось создать папку")
    }
  }

  function beginRename(folderId: string, currentName: string) {
    editingFolderId = folderId
    renameDraft = currentName
  }

  async function submitRename(folderId: string) {
    if (!renameDraft.trim()) return
    try {
      await renameFolder(folderId, renameDraft.trim())
      editingFolderId = null
      renameDraft = ""
      await loadTree()
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось переименовать папку")
    }
  }

  async function removeFolder(folderId: string) {
    if (!confirm("Удалить папку? Папка должна быть пустой.")) return
    try {
      await deleteFolderById(folderId)
      await loadTree()
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось удалить папку")
    }
  }

  function beginMoveFolder(folderId: string) {
    const folder = foldersById[folderId]
    if (!folder) return
    moveState = { type: "folder", id: folderId, name: folder.name }
    moveTargetFolderId = folder.parent_id ?? ""
  }

  function beginMoveDocument(doc: Document) {
    moveState = { type: "document", id: doc._id, name: doc.display_filename || doc.filename }
    moveTargetFolderId = doc.folder_id || selectedFolderId || ""
  }

  async function submitMove() {
    if (!moveState) return
    try {
      if (moveState.type === "folder") {
        await moveFolder(moveState.id, moveTargetFolderId || null)
      } else {
        if (!moveTargetFolderId) return
        await moveDocumentToFolder(moveState.id, moveTargetFolderId)
      }
      moveState = null
      moveTargetFolderId = ""
      await loadTree()
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось переместить")
    }
  }

  function folderOptions(excludeId?: string) {
    return Object.values(foldersById)
      .filter((folder) => folder.id !== excludeId)
      .sort((left, right) => left.name.localeCompare(right.name))
  }

  function buildVisibleRows(parentId: string | null = null, depth = 0): TreeRow[] {
    const rows: TreeRow[] = []
    for (const folderId of sortedFolderIds(parentId)) {
      const folder = foldersById[folderId]
      if (!folder) continue
      rows.push({ kind: "folder", depth, folder })
      if (expanded.has(folderId)) {
        rows.push(...buildVisibleRows(folderId, depth + 1))
        for (const doc of docsByFolder[folderId] ?? []) {
          rows.push({ kind: "document", depth: depth + 1, folderId, document: doc })
        }
      }
    }
    return rows
  }

  onMount(async () => {
    await loadTree()
    initialSelectionApplied = true
  })

  $: if (initialSelectionApplied && initialFolderId && foldersById[initialFolderId] && initialFolderId !== selectedFolderId) {
    void selectFolder(initialFolderId)
  }

  $: {
    const childIds = selectedFolderId ? (folderChildren[selectedFolderId] ?? []) : []
    currentFolders = childIds.map((id) => foldersById[id]).filter(Boolean)
    currentDocuments = selectedFolderId ? (docsByFolder[selectedFolderId] ?? []) : []
  }
</script>

<div class="files-shell panel">
  <div class="files-toolbar">
    <div class="breadcrumbs">
      <span class="crumb">Root</span>
      {#if selectedFolderId}
        {#each folderPath(selectedFolderId) as item (item.id)}
          <span>/</span>
          <button class="crumb-button" on:click={() => selectFolder(item.id)}>{item.name}</button>
        {/each}
      {/if}
      {#if selectedDocument}
        <span>/</span>
        <span class="doc-crumb">{selectedDocument.display_filename || selectedDocument.filename}</span>
      {/if}
    </div>
    {#if canEdit}
      <button class="new-folder" on:click={() => beginCreate(selectedFolderId || null)}>+ New folder</button>
    {/if}
  </div>

  {#if error}
    <p class="error">{error}</p>
  {:else if loading}
    <p class="muted">Loading files…</p>
  {:else if !buildVisibleRows().length && !currentFolders.length && !currentDocuments.length}
    <p class="muted">No folders yet.</p>
  {:else if selectedFolderId && !foldersById[selectedFolderId]}
    <p class="error">Selected folder no longer exists. Reload the page.</p>
  {:else}
    <div class="tree">
      {#if creatingUnderParentId === null}
        <div class="inline-editor root-create">
          <input bind:value={createDraft} placeholder="Folder name" on:keydown={(e) => e.key === "Enter" && submitCreate()} />
          <button on:click={submitCreate}>Create</button>
          <button class="secondary" on:click={() => creatingUnderParentId = "__cancel__"}>Cancel</button>
        </div>
      {/if}

      {#each buildVisibleRows() as row (row.kind === "folder" ? `folder:${row.folder.id}` : `doc:${row.document._id}`)}
        {#if row.kind === "folder"}
          <div class="row" class:selected={selectedFolderId === row.folder.id} style={`--depth:${row.depth};`}>
            <button class="toggle" on:click={() => toggleFolder(row.folder.id)}>{expanded.has(row.folder.id) ? "▾" : "▸"}</button>
            <span class="icon">{row.folder.is_system ? "🛡️" : "📁"}</span>
            {#if editingFolderId === row.folder.id}
              <input class="inline-input" bind:value={renameDraft} on:keydown={(e) => e.key === "Enter" && submitRename(row.folder.id)} />
            {:else}
              <button class="name" on:click={() => selectFolder(row.folder.id)}>{row.folder.name}</button>
            {/if}

            {#if canEdit}
              <div class="row-actions">
                {#if editingFolderId === row.folder.id}
                  <button class="mini" on:click={() => submitRename(row.folder.id)}>✓</button>
                  <button class="mini" on:click={() => editingFolderId = null}>✕</button>
                {:else}
                  <button class="mini" title="New subfolder" on:click={() => beginCreate(row.folder.id)}>＋</button>
                  {#if !row.folder.is_system}
                    <button class="mini" title="Rename" on:click={() => beginRename(row.folder.id, row.folder.name)}>✎</button>
                    <button class="mini" title="Move" on:click={() => beginMoveFolder(row.folder.id)}>↕</button>
                    <button class="mini danger" title="Delete" on:click={() => removeFolder(row.folder.id)}>🗑</button>
                  {/if}
                {/if}
              </div>
            {/if}
          </div>

          {#if creatingUnderParentId === row.folder.id}
            <div class="inline-editor child" style={`--depth:${row.depth + 1};`}>
              <input bind:value={createDraft} placeholder="Folder name" on:keydown={(e) => e.key === "Enter" && submitCreate()} />
              <button on:click={submitCreate}>Create</button>
              <button class="secondary" on:click={() => creatingUnderParentId = "__cancel__"}>Cancel</button>
            </div>
          {/if}
        {:else}
          <div class="row file-row" class:selected={selectedDocument?._id === row.document._id} style={`--depth:${row.depth};`}>
            <span class="toggle-placeholder"></span>
            <span class="icon">📄</span>
            <button class="name" on:click={() => openDocument(row.document)}>{row.document.display_filename || row.document.filename}</button>
            {#if canEdit}
              <div class="row-actions">
                <button class="mini" title="Move" on:click={() => beginMoveDocument(row.document)}>↕</button>
              </div>
            {/if}
          </div>
        {/if}
      {/each}
    </div>

    {#if selectedFolderId}
      <div class="current-contents">
        <h4>Current folder contents</h4>
        {#if currentFolders.length}
          {#each currentFolders as folder (folder.id)}
            <div class="content-row">
              <button class="name" on:click={() => selectFolder(folder.id)}>📁 {folder.name}</button>
            </div>
          {/each}
        {/if}
        {#if currentDocuments.length}
          {#each currentDocuments as doc (doc._id)}
            <div class="content-row">
              <button class="name" on:click={() => openDocument(doc)}>📄 {doc.display_filename || doc.filename}</button>
            </div>
          {/each}
        {/if}
      </div>
    {/if}

    {#if selectedFolderId && loadedFolderContents.has(selectedFolderId) && !currentFolders.length && !currentDocuments.length}
      <p class="muted">This folder is empty.</p>
    {/if}
  {/if}

  {#if moveState}
    <div class="move-modal-backdrop" on:click={() => moveState = null}>
      <div class="move-modal panel" on:click|stopPropagation>
        <h4>Move: {moveState.name}</h4>
        <select bind:value={moveTargetFolderId}>
          {#if moveState.type === "folder"}
            <option value="">Top level</option>
          {/if}
          {#each folderOptions(moveState.type === "folder" ? moveState.id : undefined) as folder (folder.id)}
            <option value={folder.id}>{folder.name}</option>
          {/each}
        </select>
        <div class="move-actions">
          <button on:click={submitMove}>Move</button>
          <button class="secondary" on:click={() => moveState = null}>Cancel</button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .files-shell { padding: 10px; }
  .files-toolbar { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-bottom: 10px; }
  .breadcrumbs { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; color: var(--text-muted); font-size: 0.92rem; }
  .crumb-button, .name { background: none; border: 0; padding: 0; text-align: left; color: var(--text); cursor: pointer; }
  .crumb-button:hover, .name:hover { text-decoration: underline; }
  .new-folder { min-height: 30px; padding: 0 10px; font-size: 0.85rem; }

  .tree { display: grid; gap: 2px; }
  .row { display: grid; grid-template-columns: 20px 18px minmax(0, 1fr) auto; gap: 8px; align-items: center; min-height: 28px; border-radius: 8px; padding: 2px 6px; padding-left: calc(6px + var(--depth, 0) * 16px); }
  .row:hover { background: color-mix(in srgb, var(--surface), var(--primary) 8%); }
  .row.selected { background: color-mix(in srgb, var(--surface), var(--primary) 13%); }
  .toggle { width: 20px; min-width: 20px; height: 20px; border: 0; padding: 0; background: transparent; color: var(--text-muted); }
  .toggle-placeholder { width: 20px; display: inline-block; }
  .icon { font-size: 0.95rem; opacity: 0.9; }
  .name { font-size: 0.92rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

  .row-actions { display: inline-flex; gap: 4px; opacity: 0; transition: opacity .12s ease; }
  .row:hover .row-actions, .row.selected .row-actions { opacity: 1; }
  .mini { border: 0; background: color-mix(in srgb, var(--surface), var(--bg-accent) 35%); width: 22px; height: 22px; border-radius: 6px; padding: 0; font-size: 0.75rem; }
  .mini.danger { color: #c32626; }

  .file-row { grid-template-columns: 20px 18px minmax(0, 1fr) auto; }
  .current-contents { margin-top: 10px; border-top: 1px solid var(--border); padding-top: 8px; display: grid; gap: 4px; }
  .current-contents h4 { margin: 0 0 2px; font-size: .85rem; color: var(--text-muted); font-weight: 600; }
  .content-row { min-height: 24px; display: flex; align-items: center; }

  .inline-editor { display: flex; gap: 6px; align-items: center; margin: 4px 0 6px 26px; padding-left: calc(var(--depth, 0) * 16px); }
  .inline-editor.root-create { margin-left: 0; }
  .inline-editor input, .inline-input { height: 28px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface); color: var(--text); padding: 0 8px; }
  .inline-input { width: 100%; }
  .inline-editor button { min-height: 28px; padding: 0 8px; font-size: 0.8rem; }

  .move-modal-backdrop { position: fixed; inset: 0; background: rgba(5, 10, 20, .35); display: grid; place-items: center; z-index: 60; }
  .move-modal { width: min(420px, 94vw); padding: 12px; display: grid; gap: 10px; }
  .move-modal h4 { margin: 0; font-size: 1rem; }
  .move-modal select { min-height: 34px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface); color: var(--text); padding: 0 8px; }
  .move-actions { display: flex; justify-content: flex-end; gap: 8px; }

  .error { color: #c32626; }
  .muted { color: var(--text-muted); }
</style>
