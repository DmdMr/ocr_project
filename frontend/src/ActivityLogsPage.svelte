<script lang="ts">
  import { onMount } from "svelte"
  import { push } from "svelte-spa-router"
  import { getActivityLogs, type ActivityLogEntry } from "./lib/api"
  import { isAdmin } from "./lib/auth"

  let logs: ActivityLogEntry[] = []
  let loading = false
  let error = ""

  function formatTimestamp(value?: string) {
    if (!value) return "—"
    const parsed = new Date(value)
    if (Number.isNaN(parsed.getTime())) return value
    return parsed.toLocaleString()
  }

  async function loadLogs() {
    loading = true
    error = ""
    try {
      logs = await getActivityLogs(200)
    } catch (err) {
      error = err instanceof Error ? err.message : "Не удалось загрузить активность"
    } finally {
      loading = false
    }
  }

  onMount(loadLogs)
</script>

<div class="panel activity-page">
  <div class="header">
    <h2>Журнал активности</h2>
    <div class="actions">
      <button class="secondary" on:click={loadLogs} disabled={loading}>Обновить</button>
      <button on:click={() => push("/")}>Назад</button>
    </div>
  </div>

  {#if !$isAdmin}
    <p class="error">Доступно только администраторам.</p>
  {:else if loading}
    <p>Загрузка...</p>
  {:else if error}
    <p class="error">{error}</p>
  {:else if !logs.length}
    <p class="muted">Записей пока нет.</p>
  {:else}
    <div class="logs">
      {#each logs as log (log.id)}
        <article class="log-row">
          <div class="line">
            <strong>{log.action}</strong>
            <span>{formatTimestamp(log.created_at || log.timestamp)}</span>
          </div>
          <div class="line">
            <span>Actor: {JSON.stringify(log.actor)}</span>
          </div>
          <pre>{JSON.stringify(log.payload, null, 2)}</pre>
        </article>
      {/each}
    </div>
  {/if}
</div>

<style>
  .activity-page { padding: 16px; }
  .header { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
  .actions { display: flex; gap: 8px; }
  .logs { display: grid; gap: 10px; margin-top: 14px; }
  .log-row { border: 1px solid var(--border); border-radius: var(--radius-md); padding: 10px; background: var(--surface-strong); }
  .line { display: flex; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
  pre { margin: 8px 0 0; white-space: pre-wrap; word-break: break-word; font-size: 0.86rem; }
  .muted { color: var(--text-muted); }
  .error { color: var(--danger); }
</style>
