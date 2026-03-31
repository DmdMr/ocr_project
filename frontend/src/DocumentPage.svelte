<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import {
    getDocumentById,
    UPLOADS_URL,
    updateDocument,
    updateDocumentBodyMarkdown,
    updateDocumentCustomFields,
    uploadImagesToDocument
  } from "./lib/api"
  import type { AttachmentFile, Document, GalleryImage } from "./lib/types"
  import { documentRoute, documentSlug } from "./lib/documentRoutes"

  export let params: { id?: string; slug?: string } = {}

  let documentId = ""
  let doc: Document | null = null
  let loading = true
  let error = ""

  let isEditMode = false
  let isSavingBody = false
  let editedBody = ""
  let originalBody = ""
  let bodyTextarea: HTMLTextAreaElement | null = null

  let isEditingTitle = false
  let titleDraft = ""
  let customFieldDrafts: Record<string, string> = {}
  let savingCustomFields = false

  let galleryIndex = 0

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
    isEditingTitle = false
    try {
      const loadedDoc = await getDocumentById(id) as Document
      doc = loadedDoc
      originalBody = getPreferredBody(loadedDoc)
      editedBody = originalBody
      titleDraft = displayName(loadedDoc)
      customFieldDrafts = buildCustomFieldDrafts(loadedDoc)
      galleryIndex = 0

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

  function displayName(current: Document) {
    return current.display_filename || current.filename
  }

  function getPreferredBody(currentDoc: Document) {
    if ((currentDoc.body_markdown || "").trim()) {
      return currentDoc.body_markdown || ""
    }

    const sections: string[] = []
    const recognized = (currentDoc.recognized_text || "").trim()
    if (recognized) sections.push(recognized)

    const images = currentDoc.gallery_images || []
    if (images.length) {
      sections.push(images.map((image) => `![[${image.filename}]]`).join("\n\n"))
    }

    return sections.join("\n\n")
  }

  function buildCustomFieldDrafts(currentDoc: Document) {
    const drafts: Record<string, string> = {}
    for (const [key, value] of Object.entries(currentDoc.custom_fields || {})) {
      drafts[key] = value === null || value === undefined ? "" : String(value)
    }
    return drafts
  }

  function formatDate(value?: string) {
    if (!value) return "—"
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString()
  }

  function attachmentUrl(file: AttachmentFile) {
    return `${UPLOADS_URL}/${file.filename}`
  }

  function imageByFilename(filename: string) {
    return (doc?.gallery_images || []).find((image) => image.filename === filename) || null
  }

  function imageUrl(image: GalleryImage) {
    const version = encodeURIComponent(image.image_version || image.created_at || "")
    return `${UPLOADS_URL}/${image.filename}${version ? `?v=${version}` : ""}`
  }

  function imageUrlFromFilename(filename: string) {
    const image = imageByFilename(filename)
    if (image) return imageUrl(image)
    return `${UPLOADS_URL}/${filename}`
  }

  function escapeHtml(value: string) {
    return value
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;")
  }

  function renderInlineMarkdown(text: string) {
    // wiki embeds ![[file]] and [[file]] to images
    let html = escapeHtml(text)
    html = html.replace(/!\[\[([^\]]+)\]\]/g, (_match, filename) => {
      const safeFilename = String(filename || "").trim()
      if (!safeFilename) return ""
      const src = escapeHtml(imageUrlFromFilename(safeFilename))
      const alt = escapeHtml(safeFilename)
      return `<figure><img src="${src}" alt="${alt}" loading="lazy" /></figure>`
    })

    html = html.replace(/\[\[([^\]]+)\]\]/g, (_match, filename) => {
      const safeFilename = String(filename || "").trim()
      if (!safeFilename) return ""
      const src = escapeHtml(imageUrlFromFilename(safeFilename))
      const alt = escapeHtml(safeFilename)
      return `<figure><img src="${src}" alt="${alt}" loading="lazy" /></figure>`
    })

    html = html.replace(/!\[(.*?)\]\((.*?)\)/g, (_m, alt, srcRaw) => {
      const src = String(srcRaw || "").trim()
      const resolved = src.startsWith("http") || src.startsWith("/") ? src : `${UPLOADS_URL}/${src}`
      return `<figure><img src="${escapeHtml(resolved)}" alt="${escapeHtml(String(alt || "image"))}" loading="lazy" /></figure>`
    })

    return html
  }

  function renderMarkdown(markdown: string) {
    const lines = (markdown || "").replace(/\r\n/g, "\n").split("\n")
    const html: string[] = []
    let paragraph: string[] = []
    let list: string[] = []

    const flushParagraph = () => {
      if (!paragraph.length) return
      html.push(`<p>${renderInlineMarkdown(paragraph.join(" "))}</p>`)
      paragraph = []
    }

    const flushList = () => {
      if (!list.length) return
      html.push(`<ul>${list.map((item) => `<li>${renderInlineMarkdown(item)}</li>`).join("")}</ul>`)
      list = []
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
        html.push(`<h${level}>${renderInlineMarkdown(heading[2])}</h${level}>`)
        continue
      }

      const listItem = line.match(/^[-*]\s+(.+)$/)
      if (listItem) {
        flushParagraph()
        list.push(listItem[1])
        continue
      }

      flushList()
      paragraph.push(line)
    }

    flushParagraph()
    flushList()
    return html.join("\n")
  }

  function startEditingBody() {
    if (!doc) return
    isEditMode = true
    originalBody = getPreferredBody(doc)
    editedBody = originalBody
  }

  function cancelEditingBody() {
    isEditMode = false
    editedBody = originalBody
  }

  function hasUnsavedBody() {
    return editedBody !== originalBody
  }

  async function saveBody() {
    if (!doc) return
    isSavingBody = true
    try {
      const updatedDoc = await updateDocumentBodyMarkdown(doc._id, editedBody)
      doc = updatedDoc as Document
      originalBody = getPreferredBody(doc)
      editedBody = originalBody
      isEditMode = false
    } catch (saveError) {
      alert(saveError instanceof Error ? saveError.message : "Failed to save note")
    } finally {
      isSavingBody = false
    }
  }

  function startTitleEdit() {
    if (!doc) return
    isEditingTitle = true
    titleDraft = displayName(doc)
  }

  async function saveTitle() {
    if (!doc) return
    const nextTitle = titleDraft.trim()
    if (!nextTitle) return

    try {
      const updatedDoc = await updateDocument(doc._id, { display_filename: nextTitle })
      doc = updatedDoc as Document
      titleDraft = displayName(doc)
      isEditingTitle = false
      push(documentRoute(doc))
    } catch (titleError) {
      alert(titleError instanceof Error ? titleError.message : "Failed to rename document")
    }
  }

  async function saveCustomFields() {
    if (!doc) return
    savingCustomFields = true
    try {
      const payload: Record<string, string | number | null> = {}
      for (const [key, value] of Object.entries(customFieldDrafts)) {
        payload[key] = value === "" ? null : value
      }
      const updatedDoc = await updateDocumentCustomFields(doc._id, payload)
      doc = updatedDoc as Document
      customFieldDrafts = buildCustomFieldDrafts(doc)
    } catch (fieldsError) {
      alert(fieldsError instanceof Error ? fieldsError.message : "Failed to save custom fields")
    } finally {
      savingCustomFields = false
    }
  }

  function galleryImages() {
    return doc?.gallery_images || []
  }

  function currentGalleryImage() {
    const images = galleryImages()
    if (!images.length) return null
    const safeIndex = Math.max(0, Math.min(galleryIndex, images.length - 1))
    return images[safeIndex]
  }

  function goPrevImage() {
    const images = galleryImages()
    if (images.length <= 1) return
    galleryIndex = (galleryIndex - 1 + images.length) % images.length
  }

  function goNextImage() {
    const images = galleryImages()
    if (images.length <= 1) return
    galleryIndex = (galleryIndex + 1) % images.length
  }

  function appendEmbeds(body: string, filenames: string[]) {
    if (!filenames.length) return body
    const tail = filenames.map((name) => `![[${name}]]`).join("\n\n")
    return `${body.trimEnd()}\n\n${tail}\n`
  }

  async function uploadImageToDocument(event: Event) {
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

      const added = (doc?.gallery_images || [])
        .filter((image) => !previousNames.has(image.filename))
        .map((image) => image.filename)

      if (added.length) {
        const base = isEditMode ? editedBody : getPreferredBody(doc as Document)
        const nextBody = appendEmbeds(base, added)
        const updatedWithBody = await updateDocumentBodyMarkdown((doc as Document)._id, nextBody)
        doc = updatedWithBody as Document
        originalBody = getPreferredBody(doc)
        editedBody = isEditMode ? nextBody : originalBody
      }

      galleryIndex = Math.max(0, galleryImages().length - 1)
    } catch (uploadError) {
      alert(uploadError instanceof Error ? uploadError.message : "Failed to upload image")
    } finally {
      input.value = ""
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
      <header class="card-like">
        <div class="top-actions">
          <button on:click={() => push("/")}>← Back</button>
          <label class="upload-btn">
            Upload image
            <input type="file" accept="image/*" on:change={uploadImageToDocument} />
          </label>
        </div>

        {#if isEditingTitle}
          <input
            class="title-input"
            bind:value={titleDraft}
            on:keydown={(event) => event.key === "Enter" && saveTitle()}
            on:blur={saveTitle}
          />
        {:else}
          <button class="title-button" on:click={startTitleEdit}><h1 class="editable-title">{displayName(doc)}</h1></button>
        {/if}
      </header>

      <section class="card-like properties">
        <div><strong>Created:</strong> {formatDate(doc.created_at)}</div>
        {#if (doc as any).created_by || (doc as any).updated_by_username}
          <div><strong>Author:</strong> {(doc as any).created_by || (doc as any).updated_by_username}</div>
        {/if}
        <div><strong>Filename:</strong> {doc.filename}</div>

        {#if doc.tags?.length}
          <div class="tags">
            {#each doc.tags as tag}
              <span class="tag">{tag}</span>
            {/each}
          </div>
        {/if}

        {#if Object.keys(customFieldDrafts).length}
          <div class="custom-fields">
            <h3>Custom fields</h3>
            {#each Object.entries(customFieldDrafts) as [key, value]}
              <label>
                <span>{key}</span>
                <input bind:value={customFieldDrafts[key]} />
              </label>
            {/each}
            <button on:click={saveCustomFields} disabled={savingCustomFields}>
              {savingCustomFields ? "Saving..." : "Save fields"}
            </button>
          </div>
        {/if}
      </section>

      {#if doc.attachments?.length}
        <section class="card-like">
          <h2>Attachments</h2>
          <ul>
            {#each doc.attachments as attachment}
              <li><a href={attachmentUrl(attachment)} target="_blank" rel="noreferrer">{attachment.original_name || attachment.filename}</a></li>
            {/each}
          </ul>
        </section>
      {/if}

      <section class="card-like gallery">
        <h2>Images</h2>
        {#if currentGalleryImage()}
          <div class="slider-row">
            <button on:click={goPrevImage} disabled={galleryImages().length <= 1}>←</button>
            <img src={imageUrl(currentGalleryImage() as GalleryImage)} alt={(currentGalleryImage() as GalleryImage).filename} />
            <button on:click={goNextImage} disabled={galleryImages().length <= 1}>→</button>
          </div>
          <p class="muted">{galleryIndex + 1} / {galleryImages().length} · {(currentGalleryImage() as GalleryImage).filename}</p>
        {:else}
          <p class="muted">No images yet.</p>
        {/if}
      </section>

      <section class="card-like note-body">
        <div class="note-header">
          <h2>Note</h2>
          {#if !isEditMode}
            <button on:click={startEditingBody}>Edit</button>
          {:else}
            <div class="note-actions">
              <button class="secondary" on:click={cancelEditingBody}>Cancel</button>
              <button on:click={saveBody} disabled={isSavingBody || !hasUnsavedBody()}>{isSavingBody ? "Saving..." : "Save"}</button>
            </div>
          {/if}
        </div>

        {#if isEditMode}
          <textarea bind:this={bodyTextarea} bind:value={editedBody} rows="24" class="note-editor"></textarea>
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
    width: min(980px, 100%);
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
    align-items: center;
    gap: 10px;
  }

  .upload-btn {
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 6px 10px;
    cursor: pointer;
  }

  .upload-btn input { display: none; }

  .title-button {
    border: none;
    background: transparent;
    padding: 0;
    text-align: left;
    cursor: text;
  }

  .editable-title {
    margin: 12px 0 0;
  }

  .title-input {
    margin-top: 10px;
    font-size: 1.5rem;
    width: 100%;
  }

  .tags { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
  .tag { padding: 3px 10px; border-radius: 999px; background: var(--surface); }

  .custom-fields {
    margin-top: 12px;
    display: grid;
    gap: 8px;
  }

  .custom-fields label {
    display: grid;
    gap: 4px;
  }

  .slider-row {
    display: grid;
    grid-template-columns: 44px 1fr 44px;
    gap: 10px;
    align-items: center;
  }

  .slider-row img {
    width: 100%;
    max-height: 460px;
    object-fit: contain;
    border: 1px solid var(--border);
    border-radius: var(--radius-md);
    background: #00000008;
  }

  .note-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 8px;
    margin-bottom: 10px;
  }

  .note-actions { display: flex; gap: 8px; }

  .note-editor {
    width: 100%;
    min-height: 62vh;
    resize: vertical;
    line-height: 1.65;
    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace;
  }

  .note-body :global(h1),
  .note-body :global(h2),
  .note-body :global(h3) {
    margin-top: 1.2em;
    margin-bottom: 0.5em;
    line-height: 1.25;
  }

  .note-body :global(p),
  .note-body :global(ul) {
    line-height: 1.7;
    margin: 0 0 1em;
  }

  .note-body :global(ul) { padding-left: 1.2rem; }

  .note-body :global(img) {
    width: 100%;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
    margin: 0.75em 0;
  }

  .muted { color: var(--text-muted); }
</style>
