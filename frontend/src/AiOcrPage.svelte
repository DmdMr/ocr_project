<script lang="ts">
  import { onMount } from 'svelte'
  import { getAiOcrStatus, setAiOcrProvider, getAiOcrHistory, saveAiOcrCorrection } from './lib/api'
  let tab: 'config'|'history'|'fine' = 'config'
  let status: any = null
  let history: any[] = []
  let correction = { image_path:'', ocr_text:'', corrected_text:'' }
  async function load(){ status = await getAiOcrStatus(); const h = await getAiOcrHistory(); history=h.items||[] }
  async function switchProvider(p:"remote"|"ollama"){ await setAiOcrProvider(p); await load() }
  async function saveCorrection(){ await saveAiOcrCorrection(correction); correction.corrected_text='' }
  onMount(load)
</script>

<h2>AI OCR</h2>
<div><button on:click={()=>tab='config'}>Configuration</button><button on:click={()=>tab='history'}>Recognized Images</button><button on:click={()=>tab='fine'}>Fine-tuning</button></div>
{#if tab==='config'}
  <h3>Provider</h3>
  <button on:click={()=>switchProvider('ollama')}>Local Ollama</button>
  <button on:click={()=>switchProvider('remote')}>Remote VPS</button>
  <pre>{JSON.stringify(status, null, 2)}</pre>
{/if}
{#if tab==='history'}
  {#each history as item}
    <div class="card">
      <div>{item.image_path}</div><div>{item.provider} · {item.timestamp} · {item.processing_time_ms}ms</div>
      <textarea rows="4" bind:value={item.text}></textarea>
      <div>OCR regions / bounding boxes / confidence overlays (placeholder)</div>
    </div>
  {/each}
{/if}
{#if tab==='fine'}
  <div>image crop preview (placeholder)</div>
  <input placeholder="image path" bind:value={correction.image_path}>
  <textarea placeholder="ocr text" bind:value={correction.ocr_text}></textarea>
  <textarea placeholder="corrected text" bind:value={correction.corrected_text}></textarea>
  <button on:click={saveCorrection}>save correction</button>
{/if}
