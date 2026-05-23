<script lang="ts">
import { onMount } from 'svelte'
import { push } from 'svelte-spa-router'
import ProviderCard from './lib/components/ai-ocr/ProviderCard.svelte'
import StatusBadge from './lib/components/ai-ocr/StatusBadge.svelte'
import { getAIOcrConfig, saveAIOcrConfig, getOllamaStatus, pullOllamaModel, testRemoteConnection } from './lib/api'

let config:any={provider:'remote', remote_url:'http://111.88.113.136:8000/ocr', ollama_model:'qwen3-vl:2b', timeout:60}
let ollama:any={}; let remote:any={}; let saving=false
const load = async()=>{ const data=await getAIOcrConfig(); config=data.config; ollama=data.ollama; remote=data.remote }
onMount(load)
const save = async()=>{ saving=true; await saveAIOcrConfig(config); await load(); saving=false }
</script>
<div class="page">
  <button on:click={() => push('/')} class="back">← Back</button>
  <h1>AI OCR Dashboard</h1>
  <section class="grid2">
    <ProviderCard title="Local Ollama" description="Use local vision model through Ollama" selected={config.provider==='ollama'} on:click={()=>config.provider='ollama'} statuses={[{label:'Installed',value:ollama.installed?'Yes':'No',tone:ollama.installed?'success':'error'},{label:'Running',value:ollama.running?'Yes':'No',tone:ollama.running?'success':'warn'},{label:'Model',value:ollama.model_installed?'Ready':'Missing',tone:ollama.model_installed?'success':'warn'}]} />
    <ProviderCard title="Remote VPS" description="Use remote OCR endpoint" selected={config.provider==='remote'} on:click={()=>config.provider='remote'} statuses={[{label:'Connected',value:remote.connected?'Yes':'No',tone:remote.connected?'success':'error'},{label:'Latency',value:`${remote.latency_ms ?? '-'} ms`,tone:remote.connected?'success':'warn'}]} />
  </section>

  <section class="panel section">
    <h3>Provider Status</h3>
    {#if config.provider==='ollama'}
    <div class="row"><StatusBadge label="Installed" value={ollama.installed?'Yes':'No'} tone={ollama.installed?'success':'error'} /><StatusBadge label="Running" value={ollama.running?'Yes':'No'} tone={ollama.running?'success':'warn'} /><StatusBadge label="Model Installed" value={ollama.model_installed?'Yes':'No'} tone={ollama.model_installed?'success':'warn'} /><StatusBadge label="Model Name" value={config.ollama_model} tone="neutral" /></div>
    {:else}
    <div class="row"><StatusBadge label="Connected" value={remote.connected?'Yes':'No'} tone={remote.connected?'success':'error'} /><StatusBadge label="Server URL" value={config.remote_url} tone="neutral" /><StatusBadge label="Response" value={`${remote.latency_ms ?? '-'} ms`} tone={remote.connected?'success':'warn'} /></div>
    {/if}
  </section>

  <section class="panel section">
    <h3>Configuration</h3>
    {#if config.provider==='ollama'}
      <label>Model name <input bind:value={config.ollama_model} /></label>
      <div class="actions"><button on:click={getOllamaStatus}>Check Ollama</button><button on:click={pullOllamaModel}>Pull Model</button><button on:click={getOllamaStatus}>Test OCR</button><button on:click={save} disabled={saving}>Save</button></div>
    {:else}
      <label>VPS URL <input bind:value={config.remote_url} /></label>
      <label>Timeout <input type="number" bind:value={config.timeout} min="1"/></label>
      <div class="actions"><button on:click={testRemoteConnection}>Test Connection</button><button on:click={save} disabled={saving}>Save</button></div>
    {/if}
  </section>

  <section class="grid4">{#each ['Recognition History','Training Data','Diagnostics','Logs'] as item}<div class="panel placeholder"><h4>{item}</h4><p>Coming soon</p></div>{/each}</section>
</div>
<style>
.page{display:grid;gap:14px;padding:12px}.back{justify-self:start}.grid2{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}.section{padding:14px;display:grid;gap:10px}.row{display:flex;gap:8px;flex-wrap:wrap}label{display:grid;gap:6px}input{max-width:520px}.actions{display:flex;gap:8px;flex-wrap:wrap}.grid4{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(170px,1fr))}.placeholder{padding:14px;opacity:.75}
</style>
