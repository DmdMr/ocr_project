<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import {
    getDocumentById,
    UPLOADS_URL,
    updateDocumentContentBlocks,
    uploadImagesToDocument
  } from "./lib/api"
  import type { AttachmentFile, ContentBlock, Document, ImageContentBlock } from "./lib/types"
  import { documentRoute, documentSlug } from "./lib/documentRoutes"

  export let params: { id?: string; slug?: string } = {}

  let documentId = ""
  let doc: Document | null = null
  let loading = true
  let error = ""

  let isEditMode = false
  let isSaving = false
  let editorBlocks: ContentBlock[] = []
  let hasUnsavedChanges = false

  $: nextId = (params?.id || "").trim()
  $: if (nextId && nextId !== documentId) {
    documentId = nextId
    void loadDocument(documentId)
  }

  onMount(async () => {
    if (nextId && !doc) {
      documentId = nextId
      await loadDocument(nextId)
    }
  })

  async function loadDocument(id: string) {
    loading = true
    error = ""
    hasUnsavedChanges = false
    isEditMode = false
    try {
      const loadedDoc = await getDocumentById(id) as Document
      doc = loadedDoc
      editorBlocks = materializeBlocks(loadedDoc)

      const expectedSlug = documentSlug(loadedDoc)
      const currentSlug = (params?.slug || "").trim()
      if (!currentSlug || decodeURIComponent(currentSlug) !== expectedSlug) {
        push(documentRoute(loadedDoc))
      }
    } catch (err) {
      doc = null
      error = err instanceof Error ? err.message : "Failed to load document"
    } finally {
      loading = false
    }
  }

  function blockId() {
    if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
      return crypto.randomUUID()
    }
    return `block_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`
  }

  function materializeBlocks(currentDoc: Document): ContentBlock[] {
    if (Array.isArray(currentDoc.content_blocks) && currentDoc.content_blocks.length > 0) {
      return currentDoc.content_blocks.map((block) => ({ ...block }))
    }

    const derivedBlocks: ContentBlock[] = []
    const recognized = (currentDoc.recognized_text || "").trim()
    if (recognized) {
      derivedBlocks.push({ id: blockId(), type: "text", text: recognized })
    }

    for (const image of currentDoc.gallery_images || []) {
      derivedBlocks.push({
        id: blockId(),
        type: "image",
        image_filename: image.filename,
        image_path: image.path,
        caption: (image as any).caption || (image as any).caption_text || ""
      })
    }

    return derivedBlocks
  }

  function displayBlocks() {
    if (!doc) return []
    return isEditMode ? editorBlocks : materializeBlocks(doc)
  }

  function formatDate(value?: string) {
    if (!value) return "—"
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString()
  }

  function displayName(current: Document) {
    return current.display_filename || current.filename
  }

  function imageUrlByFilename(filename: string, fallbackPath?: string) {
    if (!filename && fallbackPath) return fallbackPath
    return `${UPLOADS_URL}/${filename}`
  }


  function attachmentUrl(file: AttachmentFile) {
    return `${UPLOADS_URL}/${file.filename}`
  }

  function startEditing() {
    if (!doc) return
    isEditMode = true
    editorBlocks = materializeBlocks(doc)
    hasUnsavedChanges = false
  }

  function cancelEditing() {
    if (!doc) return
    isEditMode = false
    editorBlocks = materializeBlocks(doc)
    hasUnsavedChanges = false
  }

  function setDirty(nextBlocks: ContentBlock[]) {
    editorBlocks = nextBlocks
    hasUnsavedChanges = true
  }

  function updateBlock(index: number, patch: Partial<ContentBlock>) {
    const current = editorBlocks[index]
    if (!current) return
    const next = [...editorBlocks]
    next[index] = { ...current, ...patch } as ContentBlock
    setDirty(next)
  }

  function removeBlock(index: number) {
    const next = editorBlocks.filter((_, idx) => idx !== index)
    setDirty(next)
  }

  function moveBlock(index: number, direction: -1 | 1) {
    const targetIndex = index + direction
    if (targetIndex < 0 || targetIndex >= editorBlocks.length) return
    const next = [...editorBlocks]
    const [item] = next.splice(index, 1)
    next.splice(targetIndex, 0, item)
    setDirty(next)
  }

  function addTextBlock() {
    setDirty([...editorBlocks, { id: blockId(), type: "text", text: "" }])
  }

  function addHeadingBlock(level: 1 | 2 | 3 = 2) {
    setDirty([...editorBlocks, { id: blockId(), type: "heading", level, text: "" }])
  }

  function addDividerBlock() {
    setDirty([...editorBlocks, { id: blockId(), type: "divider" }])
  }

  async function addImageBlock(event: Event) {
    if (!doc) return
    const input = event.currentTarget as HTMLInputElement
    const files = Array.from(input.files || [])
    if (!files.length) return

    try {
      const previousNames = new Set((doc.gallery_images || []).map((item) => item.filename))
      const result = await uploadImagesToDocument(doc._id, files)
      if (result?.document) {
        doc = result.document as Document
      }

      const currentImages = doc?.gallery_images || []
      const added = currentImages.filter((item) => !previousNames.has(item.filename))
      const imageBlocks: ImageContentBlock[] = added.map((item) => ({
        id: blockId(),
        type: "image",
        image_filename: item.filename,
        image_path: item.path,
        caption: ""
      }))
      if (imageBlocks.length > 0) {
        setDirty([...editorBlocks, ...imageBlocks])
      }
    } catch (uploadError) {
      alert(uploadError instanceof Error ? uploadError.message : "Failed to upload image block")
    } finally {
      input.value = ""
    }
  }

  async function saveBlocks() {
    if (!doc) return
    isSaving = true
    try {
      const updatedDoc = await updateDocumentContentBlocks(doc._id, editorBlocks)
      doc = updatedDoc as Document
      editorBlocks = materializeBlocks(doc)
      hasUnsavedChanges = false
      isEditMode = false
    } catch (saveError) {
      alert(saveError instanceof Error ? saveError.message : "Failed to save blocks")
    } finally {
      isSaving = false
    }
  }
</script>

<div class="document-page-shell">
  {#if loading}
    <p>Loading document…</p>
  {:else if error}
    <div class="state-card error">
      <p>{error}</p>
      <button on:click={() => push("/")}>Back to documents</button>
    </div>
  {:else if doc}
    <article class="document-reading-layout">
      <header class="document-header">
        <div class="header-row">
          <button class="back-button" on:click={() => push("/")}>← Back</button>
          {#if !isEditMode}
            <button on:click={startEditing}>Edit blocks</button>
          {:else}
            <div class="editor-actions">
              <button class="secondary" on:click={cancelEditing}>Cancel</button>
              <button on:click={saveBlocks} disabled={isSaving}>{isSaving ? "Saving..." : "Save blocks"}</button>
            </div>
          {/if}
        </div>
        <h1>{displayName(doc)}</h1>
      </header>

      <section class="properties card-like">
        <div><strong>Created:</strong> {formatDate(doc.created_at)}</div>
        <div><strong>Filename:</strong> {doc.filename}</div>
        {#if doc.tags?.length}
          <div class="tags-wrap">
            <strong>Tags:</strong>
            <div class="tags">
              {#each doc.tags as tag}
                <span class="tag">{tag}</span>
              {/each}
            </div>
          </div>
        {/if}

        {#if doc.custom_fields && Object.keys(doc.custom_fields).length}
          <div class="custom-fields">
            <strong>Custom fields:</strong>
            <dl>
              {#each Object.entries(doc.custom_fields) as [key, value]}
                <div>
                  <dt>{key}</dt>
                  <dd>{value ?? "—"}</dd>
                </div>
              {/each}
            </dl>
          </div>
        {/if}
      </section>

      {#if doc.attachments?.length}
        <section class="card-like">
          <h2>Attachments</h2>
          <ul class="attachment-list">
            {#each doc.attachments as attachment}
              <li>
                <a href={attachmentUrl(attachment)} target="_blank" rel="noreferrer">{attachment.original_name || attachment.filename}</a>
              </li>
            {/each}
          </ul>
        </section>
      {/if}

      {#if isEditMode}
        <section class="card-like block-toolbar">
          <strong>Add block:</strong>
          <div class="toolbar-buttons">
            <button on:click={addTextBlock}>Add text</button>
            <button on:click={() => addHeadingBlock(2)}>Add heading</button>
            <button on:click={addDividerBlock}>Add divider</button>
            <label class="file-button">
              Add image
              <input type="file" accept="image/*" on:change={addImageBlock} />
            </label>
          </div>
          {#if hasUnsavedChanges}
            <p class="muted">You have unsaved block changes.</p>
          {/if}
        </section>
      {/if}

      <section class="card-like content-blocks">
        {#if displayBlocks().length === 0}
          <p class="muted">No content blocks yet. Add one in edit mode.</p>
        {/if}

        {#each displayBlocks() as block, index (block.id)}
          <div class="block-item">
            {#if block.type === "heading"}
              {#if isEditMode}
                <div class="block-controls">
                  <select value={String(block.level || 1)} on:change={(event) => updateBlock(index, { level: Number((event.currentTarget as HTMLSelectElement).value) as 1 | 2 | 3 })}>
                    <option value="1">H1</option>
                    <option value="2">H2</option>
                    <option value="3">H3</option>
                  </select>
                  <input value={block.text} placeholder="Heading" on:input={(event) => updateBlock(index, { text: (event.currentTarget as HTMLInputElement).value })} />
                </div>
              {:else if block.level === 1}
                <h1>{block.text}</h1>
              {:else if block.level === 2}
                <h2>{block.text}</h2>
              {:else}
                <h3>{block.text}</h3>
              {/if}
            {:else if block.type === "text"}
              {#if isEditMode}
                <textarea
                  rows="5"
                  value={block.text}
                  placeholder="Write text..."
                  on:input={(event) => updateBlock(index, { text: (event.currentTarget as HTMLTextAreaElement).value })}
                ></textarea>
              {:else}
                <pre>{block.text}</pre>
              {/if}
            {:else if block.type === "image"}
              <figure>
                <img src={imageUrlByFilename(block.image_filename, block.image_path)} alt={block.image_filename} loading="lazy" />
                {#if isEditMode}
                  <input value={block.caption || ""} placeholder="Image caption" on:input={(event) => updateBlock(index, { caption: (event.currentTarget as HTMLInputElement).value })} />
                {:else if block.caption}
                  <figcaption>{block.caption}</figcaption>
                {/if}
              </figure>
            {:else if block.type === "divider"}
              <hr />
            {/if}

            {#if isEditMode}
              <div class="reorder-controls">
                <button on:click={() => moveBlock(index, -1)} disabled={index === 0}>↑</button>
                <button on:click={() => moveBlock(index, 1)} disabled={index === displayBlocks().length - 1}>↓</button>
                <button class="danger" on:click={() => removeBlock(index)}>Delete</button>
              </div>
            {/if}
          </div>
        {/each}
      </section>

      
    </article>
  {/if}
</div>

<style>
  .document-page-shell {
    padding: 24px 16px 48px;
    display: flex;
    justify-content: center;
  }

  .document-reading-layout {
    width: min(920px, 100%);
    display: grid;
    gap: 16px;
  }

  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
  }

  .editor-actions { display: flex; gap: 8px; }

  .document-header h1 {
    margin: 10px 0 0;
    line-height: 1.2;
  }

  .card-like,
  .state-card {
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--surface-strong);
    padding: 16px;
  }

  .toolbar-buttons {
    margin-top: 8px;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }

  .file-button {
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 6px 12px;
    cursor: pointer;
  }

  .file-button input {
    display: none;
  }

  .tags { display: flex; flex-wrap: wrap; gap: 8px; }
  .tag { padding: 3px 10px; border-radius: 999px; background: var(--surface); }

  .custom-fields dl {
    margin: 8px 0 0;
    display: grid;
    gap: 8px;
  }

  .custom-fields dt { font-weight: 600; }
  .custom-fields dd { margin: 0; color: var(--text-muted); }

  .content-blocks {
    display: grid;
    gap: 12px;
  }

  .block-item {
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    padding: 12px;
    background: var(--surface);
    display: grid;
    gap: 8px;
  }

  .block-controls,
  .reorder-controls {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }

  input,
  select,
  textarea {
    width: 100%;
    max-width: 100%;
  }

  pre {
    white-space: pre-wrap;
    word-break: break-word;
    margin: 0;
    line-height: 1.55;
    font-family: inherit;
  }

  .attachment-list { margin: 0; padding-left: 18px; }

  figure { margin: 0; }

  img {
    width: 100%;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
    display: block;
  }

  .muted { color: var(--text-muted); }
</style>
