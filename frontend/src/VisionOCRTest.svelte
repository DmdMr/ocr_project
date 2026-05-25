<script lang="ts">
  import { visionOcr, saveOcrCorrection } from "./lib/api"

  type OCRItem = {
    file: File
    imagePath: string
    provider: "ollama" | "vps" | "qwen3-vl"
    ocrText: string
    correctedText: string
    saved: boolean
  }

  let files: File[] = []
  let loading = false
  let error = ""
  let items: OCRItem[] = []

  async function onSubmit() {
    if (!files.length) {
      error = "Please choose image files."
      return
    }

    loading = true
    error = ""
    items = []

    try {
      for (const file of files) {
        const data = await visionOcr(file)
        const provider = ((data.provider || "ollama") as "ollama" | "vps" | "qwen3-vl")
        const imagePath = URL.createObjectURL(file)
        const text = data.text || ""
        items = [...items, { file, imagePath, provider, ocrText: text, correctedText: text, saved: false }]
      }
    } catch (e) {
      error = e instanceof Error ? e.message : "Vision OCR request failed"
    } finally {
      loading = false
    }
  }

  async function saveCorrection(item: OCRItem) {
    await saveOcrCorrection({
      image_path: item.file.name,
      ocr_text: item.ocrText,
      corrected_text: item.correctedText,
      provider: item.provider
    })
    item.saved = true
    items = [...items]
  }
</script>

<div class="panel" style="max-width: 900px; margin: 24px auto; display:grid; gap: 12px;">
  <h2>Vision OCR</h2>
  <input type="file" accept="image/*" multiple on:change={(event) => files = Array.from((event.currentTarget as HTMLInputElement).files ?? [])} />
  <button on:click={onSubmit} disabled={loading}>{loading ? "Processing..." : "Run Vision OCR"}</button>

  {#if error}
    <div style="color:#b42318; white-space: pre-wrap;">{error}</div>
  {/if}

  {#each items as item}
    <div class="panel" style="display:grid; gap:8px; padding:10px;">
      <img src={item.imagePath} alt={item.file.name} style="max-height:220px; object-fit:contain; border:1px solid #ddd;" />
      <div><strong>{item.file.name}</strong> · Provider: {item.provider}</div>
      <textarea rows="8" bind:value={item.correctedText}></textarea>
      <button on:click={() => saveCorrection(item)} disabled={item.saved}>{item.saved ? "Saved" : "Save correction"}</button>
    </div>
  {/each}
</div>
