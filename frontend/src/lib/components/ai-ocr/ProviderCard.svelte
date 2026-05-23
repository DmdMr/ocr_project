<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import StatusBadge from './StatusBadge.svelte'

  export let title = ''
  export let description = ''
  export let selected = false
  export let statuses: { label: string; value: string; tone: 'success' | 'warn' | 'error' | 'neutral' }[] = []

  const dispatch = createEventDispatcher<{ select: void }>()
</script>

<button type="button" class="panel card" class:selected aria-pressed={selected} on:click={() => dispatch('select')}>
  <div class="head">
    <h3>{title}</h3>
    {#if selected}<StatusBadge label="State" value="Active" tone="success" />{/if}
  </div>
  <p>{description}</p>
  <div class="statuses">{#each statuses as s}<StatusBadge {...s} />{/each}</div>
  <slot />
</button>

<style>
.card{display:grid;gap:10px;text-align:left;padding:14px;cursor:pointer;background:transparent}
.card.selected{border-color:var(--accent,#7a78ff);box-shadow:0 0 0 1px var(--accent,#7a78ff) inset}
.head{display:flex;justify-content:space-between;align-items:center;gap:8px}
.statuses{display:flex;gap:8px;flex-wrap:wrap}
p{margin:0;color:var(--text-muted)}
</style>
