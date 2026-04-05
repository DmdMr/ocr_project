<script lang="ts">
  import { createEventDispatcher } from "svelte"
  import { UPLOADS_URL } from "../../api"
  import type { GalleryImage } from "../../types"

  export let image: GalleryImage
  export let canDelete = true

  const dispatch = createEventDispatcher<{
    open: { filename: string }
    delete: { filename: string }
    edit: { filename: string }
  }>()

  $: imageSrc = `${UPLOADS_URL}/${image.filename}?v=${encodeURIComponent(image.image_version ?? "")}`
</script>

<div class="image-block" id={`image-${image.filename}`} data-image-id={image.filename}>
  <button class="image-click" on:click={() => dispatch("open", { filename: image.filename })}>
    <img src={imageSrc} alt={image.filename} />
  </button>
  <div class="caption">![[{image.filename}]]</div>
  <div class="image-actions">
    <button on:click={() => dispatch("edit", { filename: image.filename })}>Edit image</button>
    <button class="danger" disabled={!canDelete} on:click={() => dispatch("delete", { filename: image.filename })}>Delete</button>
  </div>
</div>

<style>
  .image-block { border-top: 1px solid var(--border); padding-top: 14px; margin-top: 16px; }
  .image-click { border: 0; padding: 0; background: transparent; width: 100%; cursor: zoom-in; }
  .image-click img { width: 100%; border-radius: 12px; display: block; }
  .caption { margin-top: 8px; color: var(--muted); font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 0.82rem; }
  .image-actions { margin-top: 10px; display: flex; flex-wrap: wrap; gap: 8px; }
</style>
