<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import { getDocumentById, UPLOADS_URL } from "./lib/api"
  import type { Document, GalleryImage, AttachmentFile } from "./lib/types"
  import { documentRoute, documentSlug } from "./lib/documentRoutes"

  export let params: { id?: string; slug?: string } = {}

  let documentId = ""
  let doc: Document | null = null
  let loading = true
  let error = ""

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
    try {
      const loadedDoc = await getDocumentById(id) as Document
      doc = loadedDoc

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

  function formatDate(value?: string) {
    if (!value) return "—"
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString()
  }

  function displayName(current: Document) {
    return current.display_filename || current.filename
  }

  function imageUrl(image: GalleryImage) {
    const version = encodeURIComponent(image.image_version || image.created_at || "")
    return `${UPLOADS_URL}/${image.filename}${version ? `?v=${version}` : ""}`
  }

  function attachmentUrl(file: AttachmentFile) {
    return `${UPLOADS_URL}/${file.filename}`
  }

  function openEditor() {
    if (!doc) return
    push(`/documents/${doc._id}/editor`)
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
        <div class="header-top-row">
          <button class="back-button" on:click={() => push("/")}>← Back</button>
          <div class="header-actions">
            <button class="action-button" on:click={openEditor}>Edit</button>
            <button class="action-button danger" on:click={openEditor}>Delete</button>
          </div>
        </div>
        <h1>{displayName(doc)}</h1>
        <div class="header-meta">
          <span><strong>Created:</strong> {formatDate(doc.created_at)}</span>
          <span><strong>Updated:</strong> {formatDate((doc as any).updated_at)}</span>
          <span><strong>Author:</strong> {(doc as any).author || "—"}</span>
        </div>
      </header>

      <div class="layout-columns">
        <aside class="left-panel">
          <section class="card-like">
            <h2>File location</h2>
            <p class="muted">{doc.folder || "—"}</p>
          </section>

          {#if doc.tags?.length}
            <section class="card-like">
              <h2>Tags</h2>
              <div class="tags">
                {#each doc.tags as tag}
                  <span class="tag">{tag}</span>
                {/each}
              </div>
            </section>
          {/if}

          {#if doc.attachments?.length}
            <section class="card-like">
              <h2>Attached files</h2>
              <ul class="attachment-list">
                {#each doc.attachments as attachment}
                  <li>
                    <a href={attachmentUrl(attachment)} target="_blank" rel="noreferrer">{attachment.original_name || attachment.filename}</a>
                  </li>
                {/each}
              </ul>
            </section>
          {/if}

          {#if doc.custom_fields && Object.keys(doc.custom_fields).length}
            <section class="card-like custom-fields">
              <h2>Custom fields</h2>
              <dl>
                {#each Object.entries(doc.custom_fields) as [key, value]}
                  <div>
                    <dt>{key}</dt>
                    <dd>{value ?? "—"}</dd>
                  </div>
                {/each}
              </dl>
            </section>
          {/if}
        </aside>

        <main class="right-panel">
          <section class="card-like">
            <h2>Recognized text</h2>
            {#if doc.recognized_text?.trim()}
              <pre>{doc.recognized_text}</pre>
            {:else}
              <p class="muted">No recognized text available.</p>
            {/if}
          </section>

          {#if doc.gallery_images?.length}
            <section class="card-like">
              <h2>Images</h2>
              <div class="gallery-grid">
                {#each doc.gallery_images as image}
                  <article class="image-card">
                    <img src={imageUrl(image)} alt={image.filename} loading="lazy" />
                    <div class="image-actions">
                      <button class="action-button" on:click={openEditor}>Edit</button>
                      <button class="action-button danger" on:click={openEditor}>Delete</button>
                    </div>
                  </article>
                {/each}
              </div>
            </section>
          {/if}
        </main>
      </div>
    </article>
  {/if}
</div>

<style>
  .document-page-shell {
    padding: 20px 16px 48px;
    display: flex;
    justify-content: center;
  }

  .document-reading-layout {
    width: min(1200px, 100%);
    display: grid;
    gap: 16px;
  }

  .layout-columns {
    display: grid;
    grid-template-columns: 300px minmax(0, 1fr);
    gap: 16px;
    align-items: start;
  }

  .left-panel,
  .right-panel {
    display: grid;
    gap: 16px;
  }

  .document-header {
    display: grid;
    gap: 12px;
  }

  .header-top-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 12px;
  }

  .header-actions,
  .image-actions {
    display: flex;
    gap: 8px;
  }

  .document-header h1 {
    margin: 0;
    line-height: 1.2;
  }

  .header-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px 16px;
    color: var(--text-muted);
  }

  .card-like,
  .state-card {
    border: 1px solid var(--border);
    border-radius: 12px;
    background: var(--surface-strong);
    padding: 16px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
  }

  h2 {
    margin: 0 0 12px;
    font-size: 1rem;
  }

  .tags { display: flex; flex-wrap: wrap; gap: 8px; }
  .tag { padding: 3px 10px; border-radius: 999px; background: var(--surface); }

  .custom-fields dl {
    margin: 0;
    display: grid;
    gap: 8px;
  }

  .custom-fields dt { font-weight: 600; }
  .custom-fields dd { margin: 0; color: var(--text-muted); }

  pre {
    white-space: pre-wrap;
    word-break: break-word;
    margin: 0;
    line-height: 1.55;
    font-family: inherit;
  }

  .attachment-list { margin: 0; padding-left: 18px; }
  .gallery-grid {
    display: grid;
    gap: 16px;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  }

  .image-card {
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 12px;
    display: grid;
    gap: 10px;
    background: var(--surface);
  }

  .image-card img {
    width: 100%;
    border-radius: 10px;
    border: 1px solid var(--border);
    display: block;
  }

  .action-button {
    border: 1px solid var(--border);
    background: var(--surface-strong);
    border-radius: 10px;
    padding: 6px 12px;
    cursor: pointer;
  }

  .action-button.danger {
    color: #b91c1c;
  }

  .muted { color: var(--text-muted); margin: 0; }

  @media (max-width: 900px) {
    .layout-columns {
      grid-template-columns: 1fr;
    }
  }
</style>
