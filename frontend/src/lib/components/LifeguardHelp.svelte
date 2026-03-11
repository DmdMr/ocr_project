<script lang="ts">
  import { onMount } from "svelte"

  let open = false

  const projectText = [
    "This project is an OCR workspace for image documents.",
    "1) Upload one or more images.",
    "2) Wait for OCR processing.",
    "3) Open a card to review/edit recognized text.",
    "4) Use tags to organize and quickly filter cards.",
    "5) Use search + sorting to find documents faster."
  ]

  function toggle() {
    open = !open
  }

  function close() {
    open = false
  }

  function handleKey(event: KeyboardEvent) {
    if (event.key === "Escape") {
      close()
    }
  }

  function portal(node: HTMLElement) {
    const target = document.body
    target.appendChild(node)

    return {
      destroy() {
        if (node.parentNode) node.parentNode.removeChild(node)
      }
    }
  }

  onMount(() => {
    window.addEventListener("keydown", handleKey)

    return () => {
      window.removeEventListener("keydown", handleKey)
    }
  })
</script>

<button
  class="lifeguard-btn"
  aria-label="Project help"
  title="Project help"
  on:click={toggle}
>
  🛟
</button>

{#if open}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <div class="help-overlay" use:portal on:click={close}>
    <div class="help-modal panel" on:click|stopPropagation>
      <button class="help-close" on:click={close}>✕</button>

      <h3>Project Lifeguard</h3>
      <p class="intro">
        Use this panel as your quick guide. You can replace this text later with your own project instructions.
      </p>

      <ul>
        {#each projectText as line}
          <li>{line}</li>
        {/each}
      </ul>

      <p class="footnote">
        Tip: start with uploading one test image and assign a tag immediately — this validates your full flow.
      </p>
    </div>
  </div>
{/if}

<style>
  .lifeguard-btn {
    position: fixed;
    right: 18px;
    bottom: 18px;
    width: 64px;
    min-height: 64px;
    border-radius: 999px;
    font-size: 1.9rem;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    line-height: 1;
    z-index: 1100;
    box-shadow: var(--shadow-soft);
  }

  .help-overlay {
    position: fixed;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(10, 14, 20, 0.56);
    z-index: 1200;
  }

  .help-modal {
    width: min(680px, 92vw);
    max-height: 82vh;
    overflow: auto;
    text-align: left;
    padding: 22px;
    position: relative;
  }

  .help-close {
    position: absolute;
    right: 14px;
    top: 14px;
    min-height: 32px;
    width: 32px;
    border-radius: 999px;
    padding: 0;
    box-shadow: none;
  }

  h3 {
    margin-top: 0;
    margin-bottom: 10px;
    padding-right: 40px;
  }

  .intro {
    margin-top: 0;
    color: var(--text-muted);
  }

  ul {
    margin: 10px 0 0;
    padding-left: 20px;
  }

  li {
    margin: 6px 0;
    color: var(--text);
  }

  .footnote {
    margin-top: 14px;
    color: var(--text-muted);
    font-size: 0.92rem;
  }
</style>
