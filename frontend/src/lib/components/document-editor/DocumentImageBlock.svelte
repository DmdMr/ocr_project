<script lang="ts">
  import { createEventDispatcher } from "svelte"
  import { UPLOADS_URL } from "../../api"
  import type { GalleryImage } from "../../types"

  export let image: GalleryImage
  export let canDelete = true
  export let canEdit = true

  const dispatch = createEventDispatcher<{
    open: { filename: string }
    delete: { filename: string }
    edit: { filename: string }
  }>()

  //$: imageSrc = `${UPLOADS_URL}/${image.filename}?v=${encodeURIComponent(image.image_version ?? "")}`
  // imageUtils.ts
  export function getImageUrl(image: { filename: string; image_version?: string }) {
    return `${UPLOADS_URL}/${image.filename}?v=${encodeURIComponent(image.image_version ?? "")}`
  }
  $: imageSrc = getImageUrl(image)

</script>

<div class="image-block" id={`image-${image.filename}`} data-image-id={image.filename}>
  <button class="image-click" on:click={() => dispatch("open", { filename: image.filename })}>
    <img src={imageSrc} alt={image.filename} />
  </button>
  <div class="image-actions">
    {#if canEdit}
      <button on:click={() => dispatch("edit", { filename: image.filename })}>Edit image</button>
      <button class="danger" disabled={!canDelete} on:click={() => dispatch("delete", { filename: image.filename })}>Delete</button>
    {/if}
  </div>
</div>

<style>
  .image-block { border: 1px solid var(--border); border-radius: 12px; padding: 12px; display: grid; gap: 10px; }
  .image-click { border: 0; padding: 0; background: transparent; width: 100%; cursor: zoom-in; }
  .image-click img { width: 100%; border-radius: 12px; display: block; }
  .image-actions { display: flex; flex-wrap: wrap; gap: 8px; }
</style>
