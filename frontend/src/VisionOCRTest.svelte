<script lang="ts">
  import { visionOcr } from "./lib/api"

  let file: File | null = null
  let loading = false
  let error = ""
  let resultText = ""

  async function onSubmit() {
    if (!file) {
      error = "Please choose an image file."
      return
    }

    loading = true
    error = ""
    resultText = ""

    try {
      const data = await visionOcr(file)
      resultText = data.text || ""
    } catch (e) {
      error = e instanceof Error ? e.message : "Vision OCR request failed"
    } finally {
      loading = false
    }
  }
</script>

<div class="panel" style="max-width: 760px; margin: 24px auto; display:grid; gap: 12px;">
  <h2>Vision OCR</h2>
  <input type="file" accept="image/*" on:change={(event) => file = (event.currentTarget as HTMLInputElement).files?.[0] ?? null} />
  <button on:click={onSubmit} disabled={loading}>{loading ? "Processing..." : "Run Vision OCR"}</button>

  {#if error}
    <div style="color:#b42318; white-space: pre-wrap;">{error}</div>
  {/if}

  {#if resultText}
    <textarea rows="12" readonly value={resultText}></textarea>
  {/if}
</div>
