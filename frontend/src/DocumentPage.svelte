<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import { getDocumentById, UPLOADS_URL, updateDocumentBodyMarkdown, uploadImagesToDocument } from "./lib/api"
  import type { AttachmentFile, Document } from "./lib/types"
  import { documentRoute, documentSlug } from "./lib/documentRoutes"

  export let params: { id?: string; slug?: string } = {}

  let documentId = ""
  let doc: Document | null = null
  let loading = true
  let error = ""

  let isEditMode = false
  let isSaving = false
  let editedBody = ""
  let originalBody = ""
  let bodyTextarea: HTMLTextAreaElement | null = null

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
    isEditMode = false
    try {
      const loadedDoc = await getDocumentById(id) as Document
      doc = loadedDoc
      originalBody = getPreferredBody(loadedDoc)
      editedBody = originalBody

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

  function getPreferredBody(currentDoc: Document) {
    if ((currentDoc.body_markdown || "").trim()) {
      return currentDoc.body_markdown || ""
    }

    const recognized = (currentDoc.recognized_text || "").trim()
    const sections: string[] = []
    if (recognized) {
      sections.push(recognized)
    }

    const images = currentDoc.gallery_images || []
    if (images.length) {
      const imageLines = images.map((image) => `![${image.filename}](${UPLOADS_URL}/${image.filename})`)
      sections.push(imageLines.join("\n\n"))
    }

    return sections.join("\n\n")
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

  function attachmentUrl(file: AttachmentFile) {
    return `${UPLOADS_URL}/${file.filename}`
  }

  function escapeHtml(value: string) {
    return value
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;")
  }

  function normalizeImageUrl(url: string) {
    const trimmed = url.trim()
    if (!trimmed) return ""
    if (trimmed.startsWith("http://") || trimmed.startsWith("https://") || trimmed.startsWith("/")) {
      return trimmed
    }
    return `${UPLOADS_URL}/${trimmed}`
  }

  function renderMarkdown(markdown: string) {
    const lines = (markdown || "").replace(/\r\n/g, "\n").split("\n")
    const html: string[] = []
    let paragraphBuffer: string[] = []
    let listBuffer: string[] = []

    const flushParagraph = () => {
      if (!paragraphBuffer.length) return
      const text = escapeHtml(paragraphBuffer.join(" "))
      html.push(`<p>${text}</p>`)
      paragraphBuffer = []
    }

    const flushList = () => {
      if (!listBuffer.length) return
      const items = listBuffer.map((item) => `<li>${escapeHtml(item)}</li>`).join("")
      html.push(`<ul>${items}</ul>`)
      listBuffer = []
    }

    for (const rawLine of lines) {
      const line = rawLine.trim()

      if (!line) {
        flushParagraph()
        flushList()
        continue
      }

      const heading = line.match(/^(#{1,3})\s+(.+)$/)
      if (heading) {
        flushParagraph()
        flushList()
        const level = heading[1].length
        html.push(`<h${level}>${escapeHtml(heading[2])}</h${level}>`)
        continue
      }

      const image = line.match(/^!\[(.*?)\]\((.*?)\)$/)
      if (image) {
        flushParagraph()
        flushList()
        const alt = escapeHtml(image[1] || "image")
        const src = escapeHtml(normalizeImageUrl(image[2] || ""))
        if (src) {
          html.push(`<figure><img src="${src}" alt="${alt}" loading="lazy" /></figure>`)
        }
        continue
      }

      const listItem = line.match(/^[-*]\s+(.+)$/)
      if (listItem) {
        flushParagraph()
        listBuffer.push(listItem[1])
        continue
      }

      flushList()
      paragraphBuffer.push(line)
    }

    flushParagraph()
    flushList()

    return html.join("\n")
  }

  function startEditing() {
    if (!doc) return
    isEditMode = true
    originalBody = getPreferredBody(doc)
    editedBody = originalBody
  }

  function cancelEditing() {
    isEditMode = false
    editedBody = originalBody
  }

  function hasUnsavedChanges() {
    return editedBody !== originalBody
  }

  async function saveBody() {
    if (!doc) return
    isSaving = true
    try {
      const updatedDoc = await updateDocumentBodyMarkdown(doc._id, editedBody)
      doc = updatedDoc as Document
      originalBody = getPreferredBody(doc)
      editedBody = originalBody
      isEditMode = false
    } catch (saveError) {
      alert(saveError instanceof Error ? saveError.message : "Failed to save document body")
    } finally {
      isSaving = false
    }
  }

  async function insertImageAtCursor(event: Event) {
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

      const addedImages = (doc?.gallery_images || []).filter((item) => !previousNames.has(item.filename))
      if (!addedImages.length) return

      const snippets = addedImages.map((image) => `![${image.filename}](${UPLOADS_URL}/${image.filename})`).join("\n\n")
      const insertion = `\n\n${snippets}\n\n`

      const textarea = bodyTextarea
      if (!textarea) {
        editedBody += insertion
        return
      }

      const start = textarea.selectionStart ?? editedBody.length
      const end = textarea.selectionEnd ?? editedBody.length
      editedBody = `${editedBody.slice(0, start)}${insertion}${editedBody.slice(end)}`

      await tickCursor(textarea, start + insertion.length)
    } catch (uploadError) {
      alert(uploadError instanceof Error ? uploadError.message : "Failed to upload image")
    } finally {
      input.value = ""
    }
  }

  async function tickCursor(textarea: HTMLTextAreaElement, nextPos: number) {
    await Promise.resolve()
    textarea.focus()
    textarea.selectionStart = nextPos
    textarea.selectionEnd = nextPos
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
      <header class="document-header card-like">
        <div class="top-actions">
          <button class="back-button" on:click={() => push("/")}>← Back</button>
          {#if !isEditMode}
            <button on:click={startEditing}>Edit</button>
          {:else}
            <div class="editor-actions">
              <label class="insert-image-btn">
                Insert image
                <input type="file" accept="image/*" on:change={insertImageAtCursor} />
              </label>
              <button class="secondary" on:click={cancelEditing}>Cancel</button>
              <button on:click={saveBody} disabled={isSaving || !hasUnsavedChanges()}>{isSaving ? "Saving..." : "Save"}</button>
            </div>
          {/if}
        </div>
        <h1>{displayName(doc)}</h1>
      </header>

      <section class="properties card-like">
        <div><strong>Created:</strong> {formatDate(doc.created_at)}</div>
        {#if (doc as any).created_by || (doc as any).updated_by_username}
          <div><strong>Author:</strong> {(doc as any).created_by || (doc as any).updated_by_username}</div>
        {/if}
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

      <section class="card-like note-body">
        {#if isEditMode}
          <textarea bind:this={bodyTextarea} bind:value={editedBody} rows="24" class="note-editor"></textarea>
          {#if hasUnsavedChanges()}
            <p class="muted">Unsaved changes</p>
          {/if}
        {:else}
          {@html renderMarkdown(getPreferredBody(doc))}
        {/if}
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

  .card-like,
  .state-card {
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--surface-strong);
    padding: 16px;
  }

  .top-actions {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    align-items: center;
  }

  .document-header h1 {
    margin: 12px 0 0;
    line-height: 1.2;
  }

  .editor-actions {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .insert-image-btn {
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 6px 10px;
    cursor: pointer;
  }

  .insert-image-btn input {
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

  .attachment-list { margin: 0; padding-left: 18px; }

  .note-editor {
    width: 100%;
    min-height: 62vh;
    resize: vertical;
    line-height: 1.6;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  }

  .note-body :global(h1),
  .note-body :global(h2),
  .note-body :global(h3) {
    margin-top: 1.3em;
    margin-bottom: 0.5em;
    line-height: 1.25;
  }

  .note-body :global(p),
  .note-body :global(ul) {
    line-height: 1.7;
    margin: 0 0 1em;
  }

  .note-body :global(ul) {
    padding-left: 1.3rem;
  }

  .note-body :global(img) {
    width: 100%;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
    margin: 0.75em 0;
  }

  .muted {
    color: var(--text-muted);
    margin: 8px 0 0;
  }
</style>
