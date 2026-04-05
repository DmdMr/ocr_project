<script lang="ts">
  import { createEventDispatcher } from "svelte"
  import { UPLOADS_URL } from "../../api"
  import type { GalleryImage } from "../../types"

  export let image: GalleryImage
  export let saving = false

  type Tool = "crop" | "rotate"
  let tool: Tool = "crop"
  let previewRotation = 0

  let imageEl: HTMLImageElement | null = null
  let stageEl: HTMLDivElement | null = null
  let isDrawing = false
  let startX = 0
  let startY = 0
  let cropRect: { x: number; y: number; width: number; height: number } | null = null

  const dispatch = createEventDispatcher<{
    close: void
    saveRotate: { filename: string; rotate: number }
    saveCrop: { filename: string; crop: { x_percent: number; y_percent: number; width_percent: number; height_percent: number } }
  }>()

  $: imageSrc = `${UPLOADS_URL}/${image.filename}?v=${encodeURIComponent(image.image_version ?? "")}`

  function nudge(dir: -1 | 1) {
    previewRotation = (((previewRotation + dir * 90) % 360) + 360) % 360
  }

  function getStageCoords(event: MouseEvent) {
    if (!imageEl || !stageEl) return null
    const imageRect = imageEl.getBoundingClientRect()
    const stageRect = stageEl.getBoundingClientRect()
    const clampedX = Math.min(Math.max(event.clientX, imageRect.left), imageRect.right)
    const clampedY = Math.min(Math.max(event.clientY, imageRect.top), imageRect.bottom)
    return {
      x: clampedX - imageRect.left,
      y: clampedY - imageRect.top,
      width: imageRect.width,
      height: imageRect.height,
      offsetLeft: imageRect.left - stageRect.left,
      offsetTop: imageRect.top - stageRect.top
    }
  }

  function onMouseDown(event: MouseEvent) {
    if (tool !== "crop") return
    event.preventDefault()
    const point = getStageCoords(event)
    if (!point) return
    isDrawing = true
    startX = point.x
    startY = point.y
    cropRect = { x: point.offsetLeft + point.x, y: point.offsetTop + point.y, width: 0, height: 0 }
  }

  function onMouseMove(event: MouseEvent) {
    if (tool !== "crop" || !isDrawing) return
    const point = getStageCoords(event)
    if (!point) return
    const left = Math.min(startX, point.x)
    const top = Math.min(startY, point.y)
    const width = Math.abs(point.x - startX)
    const height = Math.abs(point.y - startY)
    cropRect = { x: point.offsetLeft + left, y: point.offsetTop + top, width, height }
  }

  function onMouseUp() {
    isDrawing = false
  }

  function save() {
    if (tool === "rotate") {
      if (previewRotation === 0) return
      dispatch("saveRotate", { filename: image.filename, rotate: previewRotation })
      return
    }

    if (!cropRect || !imageEl || !stageEl) return
    const imageRect = imageEl.getBoundingClientRect()
    const stageRect = stageEl.getBoundingClientRect()
    const x = cropRect.x - (imageRect.left - stageRect.left)
    const y = cropRect.y - (imageRect.top - stageRect.top)

    const payload = {
      x_percent: Math.max(0, Math.min(100, (x / imageRect.width) * 100)),
      y_percent: Math.max(0, Math.min(100, (y / imageRect.height) * 100)),
      width_percent: Math.max(0.1, Math.min(100, (cropRect.width / imageRect.width) * 100)),
      height_percent: Math.max(0.1, Math.min(100, (cropRect.height / imageRect.height) * 100))
    }

    if (payload.width_percent < 1 || payload.height_percent < 1) return
    dispatch("saveCrop", { filename: image.filename, crop: payload })
  }
</script>

<svelte:window on:mousemove={onMouseMove} on:mouseup={onMouseUp} />

<div class="backdrop" on:click={() => dispatch("close")}> 
  <div class="modal panel" on:click|stopPropagation>
    <div class="toolbar">
      <h3>Редактирование: {image.filename}</h3>
      <div class="tool-buttons">
        <button class:active={tool === "crop"} on:click={() => tool = "crop"}>Обрезка</button>
        <button class:active={tool === "rotate"} on:click={() => tool = "rotate"}>Поворот</button>
        {#if tool === "rotate"}
          <button on:click={() => nudge(-1)}>↺ 90°</button>
          <button on:click={() => nudge(1)}>↻ 90°</button>
        {/if}
      </div>
    </div>

    <div class="stage" bind:this={stageEl} on:mousedown={onMouseDown}>
      <img bind:this={imageEl} src={imageSrc} alt={image.filename} style={`transform: rotate(${tool === 'rotate' ? previewRotation : 0}deg);`} />
      {#if tool === "crop" && cropRect}
        <div class="crop" style={`left:${cropRect.x}px; top:${cropRect.y}px; width:${cropRect.width}px; height:${cropRect.height}px;`}></div>
      {/if}
    </div>

    <div class="actions">
      <button class="primary" disabled={saving} on:click={save}>{saving ? "Сохранение..." : "Применить"}</button>
      <button disabled={saving} on:click={() => dispatch("close")}>Отмена</button>
    </div>
  </div>
</div>

<style>
  .backdrop { position: fixed; inset: 0; z-index: 1500; background: rgba(2, 6, 23, 0.72); display: grid; place-items: center; }
  .modal { width: min(1100px, 96vw); max-height: 92vh; overflow: auto; padding: 16px; }
  .toolbar { display: flex; justify-content: space-between; gap: 10px; align-items: center; margin-bottom: 10px; }
  .tool-buttons { display: flex; gap: 8px; flex-wrap: wrap; }
  .tool-buttons button.active { border-color: var(--accent); }
  .stage { position: relative; min-height: 240px; display: grid; place-items: center; background: var(--surface); border-radius: 12px; padding: 10px; }
  .stage img { max-width: 100%; max-height: 70vh; user-select: none; }
  .crop { position: absolute; border: 2px dashed #38bdf8; background: color-mix(in srgb, #38bdf8, transparent 85%); pointer-events: none; }
  .actions { margin-top: 10px; display: flex; gap: 10px; justify-content: flex-end; }
</style>
