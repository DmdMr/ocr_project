<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import {
    createFolder,
    deleteFolderById,
    getFolderContents,
    getFolderPath,
    getFolderTree,
    moveDocumentToFolder,
    moveFolder,
    renameFolder
  } from "../api"
  import type { Document, FolderNode } from "../types"

  export let canEdit = false
  export let initialFolderId: string | null = null

  type FolderPathNode = { id: string; name: string }
  type FlatFolderNode = FolderNode & { depth: number }

  let folderTree: FolderNode[] = []
  let flatTree: FlatFolderNode[] = []
  let currentFolderId = ""
  let currentFolderPath: FolderPathNode[] = []
  let childFolders: FolderNode[] = []
  let folderDocuments: Document[] = []
  let loading = false
  let error = ""

  onMount(async () => {
    await refreshTree()
    if (!currentFolderId) return
    await refreshFolderData(currentFolderId)
  })

  function flattenTree(nodes: FolderNode[], depth = 0): FlatFolderNode[] {
    const result: FlatFolderNode[] = []
    for (const node of nodes) {
      result.push({ ...node, depth })
      if (node.children?.length) result.push(...flattenTree(node.children, depth + 1))
    }
    return result
  }

  function findUnsorted(nodes: FolderNode[]): FolderNode | null {
    for (const node of nodes) {
      if (node.is_system && node.name === "Unsorted") return node
      const nested = findUnsorted(node.children || [])
      if (nested) return nested
    }
    return null
  }

  async function refreshTree() {
    try {
      const data = await getFolderTree()
      folderTree = data.folders ?? []
      flatTree = flattenTree(folderTree)

      const selected = initialFolderId
        ? flatTree.find((node) => node.id === initialFolderId)?.id
        : ""
      currentFolderId = selected || currentFolderId || findUnsorted(folderTree)?.id || flatTree[0]?.id || ""
      error = ""
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось загрузить дерево папок"
    }
  }

  async function refreshFolderData(folderId: string) {
    loading = true
    try {
      const [contents, pathPayload] = await Promise.all([
        getFolderContents(folderId),
        getFolderPath(folderId)
      ])
      childFolders = contents.folders ?? []
      folderDocuments = contents.documents ?? []
      currentFolderPath = pathPayload.path ?? []
      currentFolderId = folderId
      error = ""
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось загрузить содержимое папки"
    } finally {
      loading = false
    }
  }

  async function openFolder(folderId: string) {
    await refreshFolderData(folderId)
  }

  async function handleCreateFolder() {
    if (!canEdit || !currentFolderId) return
    const name = prompt("Название новой папки")
    if (!name?.trim()) return
    try {
      await createFolder(name.trim(), currentFolderId)
      await refreshTree()
      await refreshFolderData(currentFolderId)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось создать папку")
    }
  }

  async function handleRenameFolder(folderId: string, currentName: string) {
    if (!canEdit) return
    const name = prompt("Новое имя папки", currentName)
    if (!name?.trim() || name.trim() === currentName) return
    try {
      await renameFolder(folderId, name.trim())
      await refreshTree()
      await refreshFolderData(currentFolderId)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось переименовать папку")
    }
  }

  async function handleDeleteFolder(folderId: string) {
    if (!canEdit) return
    if (!confirm("Удалить папку? Папка должна быть пустой.")) return
    try {
      await deleteFolderById(folderId)
      await refreshTree()
      if (!flatTree.find((node) => node.id === currentFolderId)) {
        currentFolderId = findUnsorted(folderTree)?.id || flatTree[0]?.id || ""
      }
      if (currentFolderId) await refreshFolderData(currentFolderId)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось удалить папку")
    }
  }

  async function handleMoveFolder(folderId: string) {
    if (!canEdit) return
    const target = prompt("ID папки назначения (пусто = верхний уровень)", "")
    try {
      await moveFolder(folderId, target?.trim() ? target.trim() : null)
      await refreshTree()
      await refreshFolderData(currentFolderId)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось переместить папку")
    }
  }

  async function handleMoveDocument(documentId: string) {
    if (!canEdit) return
    const target = prompt("ID папки назначения для документа")
    if (!target?.trim()) return
    try {
      await moveDocumentToFolder(documentId, target.trim())
      await refreshFolderData(currentFolderId)
    } catch (err) {
      alert(err instanceof Error ? err.message : "Не удалось переместить документ")
    }
  }
</script>

<div class="files-layout">
  <aside class="tree panel">
    <h3>Folders</h3>
    {#if flatTree.length === 0}
      <p class="muted">Нет папок</p>
    {:else}
      <div class="tree-list">
        {#each flatTree as node (node.id)}
          <button
            class="tree-item"
            class:active={currentFolderId === node.id}
            on:click={() => openFolder(node.id)}
            style={`padding-left: ${10 + node.depth * 14}px;`}
          >
            {node.is_system ? "🛡️" : "📁"} {node.name}
          </button>
        {/each}
      </div>
    {/if}
  </aside>

  <section class="contents panel">
    <div class="top-bar">
      <div class="breadcrumbs">
        {#each currentFolderPath as item, index (item.id)}
          <button class="crumb" on:click={() => openFolder(item.id)}>{item.name}</button>
          {#if index < currentFolderPath.length - 1}<span>/</span>{/if}
        {/each}
      </div>
      {#if canEdit}
        <button on:click={handleCreateFolder}>+ Folder</button>
      {/if}
    </div>

    {#if error}
      <p class="error">{error}</p>
    {:else if loading}
      <p>Загрузка…</p>
    {:else}
      <div class="section">
        <h4>Subfolders</h4>
        {#if childFolders.length === 0}
          <p class="muted">Нет подпапок</p>
        {:else}
          <ul>
            {#each childFolders as folder (folder.id)}
              <li>
                <button class="link-like" on:click={() => openFolder(folder.id)}>📁 {folder.name}</button>
                {#if canEdit && !folder.is_system}
                  <button class="secondary" on:click={() => handleRenameFolder(folder.id, folder.name)}>Rename</button>
                  <button class="secondary" on:click={() => handleMoveFolder(folder.id)}>Move</button>
                  <button class="danger" on:click={() => handleDeleteFolder(folder.id)}>Delete</button>
                {/if}
              </li>
            {/each}
          </ul>
        {/if}
      </div>

      <div class="section">
        <h4>Documents</h4>
        {#if folderDocuments.length === 0}
          <p class="muted">Нет документов</p>
        {:else}
          <ul>
            {#each folderDocuments as doc (doc._id)}
              <li>
                <button class="link-like" on:click={() => push(`/documents/${doc._id}`)}>📄 {doc.display_filename || doc.filename}</button>
                {#if canEdit}
                  <button class="secondary" on:click={() => handleMoveDocument(doc._id)}>Move</button>
                {/if}
              </li>
            {/each}
          </ul>
        {/if}
      </div>
    {/if}
  </section>
</div>

<style>
  .files-layout { display: grid; grid-template-columns: 280px 1fr; gap: 12px; }
  .tree, .contents { padding: 12px; }
  .tree-list { display: grid; gap: 4px; }
  .tree-item { text-align: left; border-radius: 8px; }
  .tree-item.active { background: color-mix(in srgb, var(--surface), var(--primary) 15%); }
  .top-bar { display: flex; justify-content: space-between; gap: 10px; align-items: center; margin-bottom: 8px; }
  .breadcrumbs { display: flex; gap: 6px; flex-wrap: wrap; align-items: center; }
  .crumb, .link-like { background: none; border: 0; padding: 0; color: var(--text); text-decoration: underline; cursor: pointer; }
  .section { margin-top: 12px; }
  .section ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
  .section li { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
  .muted { color: var(--text-muted); }
  .error { color: #d12f2f; }
</style>
