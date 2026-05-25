<script lang="ts">
import { onMount } from 'svelte'
import { push } from 'svelte-spa-router'
import ProviderCard from './lib/components/ai-ocr/ProviderCard.svelte'
import StatusBadge from './lib/components/ai-ocr/StatusBadge.svelte'
import { getAIOcrConfig, saveAIOcrConfig, getOllamaStatus, getOllamaModels, pullOllamaModel, setActiveOllamaModel, testOllama, testRemoteConnection, getOcrDataset, exportOcrDataset } from './lib/api'

type Tab = 'config'|'models'|'history'|'training'|'diagnostics'|'logs'
const recommendedModel = 'qwen3-vl:2b'
let activeTab: Tab = 'config'
let config:any={provider:'remote', remote_url:'http://90.156.157.68:8000/ocr', ollama_model:recommendedModel, timeout:60}
let ollama:any={installed:false,running:false,installed_models:[]}
let models:string[]=[]
let remote:any={}
let logs=[{ts:'now',level:'INFO',msg:'Dashboard initialized'}]
let dataset:any[]=[]
let saving=false

async function load(){
  const data=await getAIOcrConfig(); config=data.config; ollama=data.ollama; remote=data.remote; models=ollama.installed_models||[]; dataset=await getOcrDataset()
}
async function selectProvider(provider:'remote'|'ollama'){ config={...config,provider}; await save() }
async function save(){ saving=true; await saveAIOcrConfig(config); await load(); saving=false }
async function refreshModels(){ const r=await getOllamaModels(); models=r.ollama.models||[]; const st=await getOllamaStatus(); ollama=st.ollama }
async function pullModel(name?:string){ await pullOllamaModel(name||config.ollama_model||recommendedModel); await refreshModels() }
async function activateModel(name:string){ config.ollama_model=name; await setActiveOllamaModel(name); await load() }
async function doRemoteTest(){ const r=await testRemoteConnection(); remote=r.remote; logs=[{ts:new Date().toISOString(), level:r.success?'INFO':'WARN', msg:`Remote test ${r.success?'ok':'failed'} (${remote.latency_ms ?? '-'}ms)`}, ...logs] }
async function downloadExport(){ const data = await exportOcrDataset(); const blob = new Blob([JSON.stringify(data, null, 2)], {type:'application/json'}); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download='ocr_dataset_export.json'; a.click(); URL.revokeObjectURL(url)}
onMount(load)
</script>

<div class="page">
  <button on:click={() => push('/')} class="back">← Back</button>
  <h1>AI OCR Dashboard</h1>
  <div class="tabs">{#each [['config','Configuration'],['models','Model Management'],['history','Recognition History'],['training','Training Data'],['diagnostics','Diagnostics'],['logs','Logs']] as [k,l]}<button class:active={activeTab===k} on:click={()=>activeTab=k as Tab}>{l}</button>{/each}</div>

  {#if activeTab==='config'}
  <section class="grid2">
    <ProviderCard title="Local Ollama" description="Use local vision model through Ollama" selected={config.provider==='ollama'} on:select={() => selectProvider('ollama')} statuses={[{label:'Installed',value:ollama.installed?'Yes':'No',tone:ollama.installed?'success':'error'},{label:'Running',value:ollama.running?'Yes':'No',tone:ollama.running?'success':'warn'},{label:'Model',value:models.includes(config.ollama_model)?'Ready':'Missing',tone:models.includes(config.ollama_model)?'success':'warn'}]} />
    <ProviderCard title="Remote VPS" description="Use remote OCR endpoint" selected={config.provider==='remote'} on:select={() => selectProvider('remote')} statuses={[{label:'Connected',value:remote.connected?'Yes':'No',tone:remote.connected?'success':'warn'},{label:'Latency',value:`${remote.latency_ms ?? '-'} ms`,tone:'neutral'}]} />
  </section>

  <section class="panel section">
  {#if config.provider==='ollama'}
    <div class="row"><StatusBadge label="Installed" value={ollama.installed?'Yes':'No'} tone={ollama.installed?'success':'error'}/><StatusBadge label="Running" value={ollama.running?'Yes':'No'} tone={ollama.running?'success':'warn'}/><StatusBadge label="Selected" value={config.ollama_model} tone="neutral"/></div>
    <label>Model name <input bind:value={config.ollama_model} /></label>
    <label>Installed models<select bind:value={config.ollama_model}><option value="">Custom...</option>{#each models as m}<option value={m}>{m}</option>{/each}</select></label>
    {#if !models.includes(recommendedModel)}<div class="panel warn">Recommended OCR model not installed. <button on:click={() => pullModel(recommendedModel)}>Pull {recommendedModel}</button></div>{/if}
    <div class="actions"><button on:click={refreshModels}>Refresh Models</button><button on:click={() => pullModel()}>Pull Model</button><button on:click={testOllama}>Test OCR</button><button on:click={save} disabled={saving}>Save Configuration</button></div>
  {:else}
    <label>VPS URL <input bind:value={config.remote_url} /></label>
    <label>Timeout (s) <input type="number" bind:value={config.timeout} min="1"/></label>
    <div class="actions"><button on:click={doRemoteTest}>Test Connection</button><button on:click={save} disabled={saving}>Save</button></div>
  {/if}
  </section>
  {/if}

  {#if activeTab==='models'}
  <section class="panel section"><h3>Model Management</h3><div class="actions"><button on:click={refreshModels}>Refresh</button><button on:click={() => pullModel()}>Pull</button></div>{#each models as m}<div class="row"><StatusBadge label="Model" value={m} tone="neutral"/><StatusBadge label="Provider" value="ollama" tone="neutral"/><button on:click={() => activateModel(m)}>Set Active</button><button disabled>Remove</button></div>{/each}</section>
  {/if}
  {#if activeTab==='history'}<section class='panel section'><h3>Recognition History</h3>{#if !dataset.length}<div>No OCR records yet.</div>{/if}{#each dataset as item}<div class='panel' style='display:grid;gap:6px;padding:10px;'><img src={item.image_path} alt={item.filename} style='max-height:140px;object-fit:contain;border:1px solid #ddd;'/><div><strong>{item.filename}</strong> · {item.provider} · {item.timestamp}</div><div><b>OCR:</b> {item.ocr_text}</div><div><b>Corrected:</b> {item.corrected_text}</div></div>{/each}</section>{/if}
  {#if activeTab==='training'}<section class='panel section'><h3>Training Data</h3><button on:click={downloadExport}>Export Dataset JSON</button><div>Total records: {dataset.length}</div></section>{/if}
  {#if activeTab==='diagnostics'}<section class="grid2"><div class="panel section">Provider status: {config.provider}</div><div class="panel section">GPU status: N/A</div><div class="panel section">Inference timing: {remote.latency_ms ?? '-'} ms</div><div class="panel section">Model loading: ready</div></section>{/if}
  {#if activeTab==='logs'}<section class="panel section logs">{#each logs as l}<div>[{l.ts}] {l.level}: {l.msg}</div>{/each}</section>{/if}
</div>

<style>
.page{display:grid;gap:14px;padding:12px}.back{justify-self:start}.tabs{display:flex;gap:8px;flex-wrap:wrap}.tabs button.active{border-color:var(--accent,#7a78ff);font-weight:700}.grid2{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(260px,1fr))}.section{padding:14px;display:grid;gap:10px}.row{display:flex;gap:8px;flex-wrap:wrap;align-items:center}.actions{display:flex;gap:8px;flex-wrap:wrap}.warn{padding:10px}.preview{width:80px;height:60px;border:1px dashed var(--border-color,#333);display:grid;place-items:center}.logs{max-height:300px;overflow:auto}
</style>
