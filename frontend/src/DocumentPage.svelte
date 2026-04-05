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
        <button class="back-button" on:click={() => push("/")}>← Back</button>
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
              <figure>
                <img src={imageUrl(image)} alt={image.filename} loading="lazy" />
                {#if (image as any).caption || (image as any).caption_text}
                  <figcaption>{(image as any).caption || (image as any).caption_text}</figcaption>
                {/if}
              </figure>
            {/each}
          </div>
        </section>
      {/if}
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

  .tags { display: flex; flex-wrap: wrap; gap: 8px; }
  .tag { padding: 3px 10px; border-radius: 999px; background: var(--surface); }

  .custom-fields dl {
    margin: 8px 0 0;
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
    gap: 14px;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  }

  .gallery-grid figure { margin: 0; }
  .gallery-grid img {
    width: 100%;
    border-radius: var(--radius-md);
    border: 1px solid var(--border);
    display: block;
  }

  .muted { color: var(--text-muted); }
</style>
