<script lang="ts">
  export let label = ''
  export let value = ''
  export let tone: 'success'|'warn'|'error'|'neutral' = 'neutral'
</script>

<div class="badge {tone}"><span>{label}</span><strong>{value}</strong></div>

<style>
.badge { display:inline-flex; gap:8px; align-items:center; border:1px solid var(--border-color,#333); border-radius:999px; padding:4px 10px; font-size:.8rem; }
.success { border-color:#2b8a57; color:#95f2c0; }
.warn { border-color:#8a7a2b; color:#f3df95; }
.error { border-color:#8a2b2b; color:#ffb0b0; }
.neutral { color:var(--text-muted); }
</style>
