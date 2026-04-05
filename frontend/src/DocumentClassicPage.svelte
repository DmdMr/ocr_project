<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import type { Document } from "./lib/types"
  import { getDocuments, updateDocument, uploadImagesToDocument, deleteDocument } from "./lib/api"
  import CardPreview from "./lib/components/CardPreview.svelte"
  import DocumentViewSwitcher from "./lib/components/document-editor/DocumentViewSwitcher.svelte"

  export let params: { id: string }

  let doc: Document | null = null
  let loading = true
  let error = ""
  let editedText = ""
  let editing = false
  let galleryUploading = false

  onMount(async () => {
    try {
      const docs = await getDocuments()
      doc = docs.find((item: Document) => item._id === params.id) ?? null
      if (!doc) {
        error = "Документ не найден"
      } else {
        editedText = doc.recognized_text ?? ""
      }
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось загрузить документ"
    } finally {
      loading = false
    }
  })

  async function save() {
    if (!doc) return
    const updated = await updateDocument(doc._id, { recognized_text: editedText })
    doc = updated
    editedText = updated.recognized_text
    editing = false
  }

  async function saveFilename(event: CustomEvent<{ display_filename: string }>) {
    if (!doc) return
    const updated = await updateDocument(doc._id, { display_filename: event.detail.display_filename })
    doc = updated
  }

  async function uploadToCard(event: CustomEvent<{ files: File[] }>) {
    if (!doc) return
    galleryUploading = true
    try {
      const result = await uploadImagesToDocument(doc._id, event.detail.files)
      if (result.document) doc = result.document
    } finally {
      galleryUploading = false
    }
  }

  async function remove() {
    if (!doc) return
    await deleteDocument(doc._id)
    push("/")
  }
</script>

<div class="classic-page">
  {#if doc}
    <div class="switcher-wrap">
      <DocumentViewSwitcher documentId={doc._id} activeView="classic" />
    </div>
  {/if}

  {#if loading}
    <p>Загрузка документа...</p>
  {:else if error || !doc}
    <p>{error || "Документ не найден"}</p>
  {:else}
    <CardPreview
      {doc}
      bind:editedText
      {editing}
      on:close={() => push('/')}
      on:save={save}
      on:saveFilename={saveFilename}
      on:delete={remove}
      on:editToggle={() => editing = !editing}
      on:documentUpdated={(event) => doc = event.detail.document}
      on:addImages={uploadToCard}
      {galleryUploading}
    />
  {/if}
</div>

<style>
  .classic-page { padding: 10px; }
  .switcher-wrap { position: fixed; top: 10px; right: 14px; z-index: 1400; }
</style>
