<script lang="ts">
    import { createEventDispatcher } from "svelte"
    import { push } from "svelte-spa-router"
    import type { Document } from "../types"
    import { tagHue } from "../tagColors"
    import { UPLOADS_URL } from "../api"
    

    export let doc: Document

    export let search = ""

    export let selected = false
    export let selectionActive = false
    export let canEdit = false

    const dispatch = createEventDispatcher()


    //const dispatch = createEventDispatcher<DocumentCardEvents & {
    //    toggleSelect: undefined
    //}>()

    let editedText = doc.recognized_text

    

    function escapeRegExp(value: string) {
        return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    }

    function handleCardClick() {
        if (canEdit && selectionActive) {
            dispatch("toggleSelect")
            return
        }

        window.location.hash = `#/documents/${doc._id}`
    }

    function handleCheckboxClick(event: MouseEvent) {
        event.stopPropagation()
        dispatch("toggleSelect")
    }



    function highlightedFilename(filename: string, searchText: string) {
        if (!searchText.trim()) return filename

        const escaped = escapeRegExp(searchText.trim())
        const regex = new RegExp(`(${escaped})`, "gi")

        return filename.replace(regex, '<mark class="filename-highlight">$1</mark>')
    }


    type DocumentCardEvents = {
        deleted: { id: string }
        tagClick: { tag: string }
        updated: { document: Document }
        toggleSelection: { id: string }

    }

    function openPreview() {
        if (canEdit && selectionActive) {
            dispatch("toggleSelection", { id: doc._id })
            return
        }

        window.location.hash = `#/documents/${doc._id}`
    }

    function toggleSelection(event: MouseEvent) {
        event.stopPropagation()
        dispatch("toggleSelection", { id: doc._id })
    }

    function handleCardKeydown(event: KeyboardEvent) {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault()
            openPreview()
        }
    }

    //const dispatch = createEventDispatcher<DocumentCardEvents>()

    function cardImageSrc(currentDoc: Document) {
        return `${UPLOADS_URL}/${currentDoc.filename}?v=${encodeURIComponent(currentDoc.image_version ?? currentDoc.created_at ?? "")}`
    }

    function cardImageCount(currentDoc: Document) {
        const galleryCount = currentDoc.gallery_images?.length ?? 0
        return galleryCount > 0 ? galleryCount : 1
    }

    function visibleIndicatorDots(totalImages: number) {
        const safeCount = Math.max(0, totalImages)
        return Math.min(5, safeCount)
    }

    function handleTagClick(event: CustomEvent<{ tag: string }>) {
        dispatch("tagClick", { tag: event.detail.tag })
    }

    function selectTagFromCard(tag: string) {
        dispatch("tagClick", { tag })
    }

    function getFilenameWithoutExtension(name: string) {
        if (!name) return ""

        const lastDot = name.lastIndexOf(".")
        if (lastDot <= 0) return name

        return name.slice(0, lastDot)
    }

    

</script>





<div
    class:selected-card={selected}
    class:selected
    class="card"
    role="button"
    tabindex="0"
    aria-pressed={selectionActive ? selected : undefined}
    on:click={openPreview}
    on:keydown={handleCardKeydown}
>
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="card-media" on:click={handleCardClick}>
        <img src={cardImageSrc(doc)} alt="" on:click={() => window.location.hash = `#/documents/${doc._id}`}/>
        {#if cardImageCount(doc) >= 2}
            <div class="image-count-indicator" aria-label={`Изображений: ${cardImageCount(doc)}`}>
                {#each Array(visibleIndicatorDots(cardImageCount(doc))) as _, idx (idx)}
                    <span class="indicator-dot"></span>
                {/each}
                {#if cardImageCount(doc) > 5}
                    <span class="indicator-more">+{cardImageCount(doc) - 5}</span>
                {/if}
            </div>
        {/if}


        

        {#if canEdit}
            <button
                class="select-checkbox"
                class:visible={selected}
                aria-label="Выбрать карточку"
                on:click={handleCheckboxClick}
            >
                {#if selected}{/if}
            </button>
        {/if}
    </div>
    
    <div class="card-filename">
        {@html highlightedFilename(
            getFilenameWithoutExtension(doc.display_filename || doc.filename || ""),
            search
        )}
    </div>

    <div class="doc-links">
        <a href={`#/documents/${doc._id}`} on:click|stopPropagation>Open document</a>
    </div>


    <div class="card-tags">
        {#if doc.tags?.length}
            {#each doc.tags as tag}
                <button class="card-tag tag-colored" 
                style={`--tag-hue: ${tagHue(tag)}`} 
                on:click={() => selectTagFromCard(tag)}>{tag}</button>
            {/each}
        {:else}
            <!--
        <span class="card-tags-empty">No tags</span>
            -->
            
        {/if}
    </div>
</div>



<style>

.card {
  position: relative;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 14px;
  background: var(--surface-strong);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  break-inside: avoid;
  margin-bottom: 20px;
  transition: box-shadow 0.18s ease, border-color 0.18s ease, transform 0.18s ease;
}

@media (max-width: 640px) {
    .card {
        padding: 8px;
        margin-bottom: 12px;
        text-align: left;
        margin-bottom: 4px;
    }
}


.card-media {
  position: relative;
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
}

.image-count-indicator {
    position: absolute;
    left: 50%;
    bottom: 10px;
    transform: translateX(-50%);
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 4px 8px;
    border-radius: 999px;
    background: color-mix(in srgb, #0f172a, transparent 32%);
    backdrop-filter: blur(3px);
    pointer-events: none;
}

.indicator-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    background: color-mix(in srgb, #ffffff, var(--surface) 20%);
    box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.18);
}

.indicator-more {
    font-size: 0.72rem;
    font-weight: 700;
    color: #fff;
    line-height: 1;
}

@media (max-width: 640px) {
    .image-count-indicator {
        bottom: 8px;
        gap: 4px;
        padding: 3px 7px;
    }

    .indicator-dot {
        width: 5px;
        height: 5px;
    }
}




img {
    width: 100%;
    border-radius: var(--radius-md);
    margin-bottom: 4px;
}

.card-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
}

.card-tag {
    min-height: 30px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.82rem;
}



.card-filename {
    margin-top: 10px;
    margin-bottom: 8px;
    padding: 0 4px;
    font-size: rem;
    font-weight: 600;
    color: var(--text);
    word-break: break-word;
    line-height: 1.35;
}

:global(.filename-highlight) {
    background: #7CFC98;
    color: #0f172a;
    padding: 0 2px;
    border-radius: 4px;
}





.select-checkbox {
  position: absolute;
  top: 10px;
  left: 10px;
  width: 30px;
  height: 30px;
  border-radius: 10px;
  z-index: 3;
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.18s ease, transform 0.18s ease;
}

.card:hover .select-checkbox,
.card.selected-card .select-checkbox,
.select-checkbox.visible {
  opacity: 1;
  pointer-events: auto;
}

.card {
  position: relative;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 14px;
  background: var(--surface-strong);
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  break-inside: avoid;
  margin-bottom: 20px;
  transition: box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.card.selected-card {
  border-color: var(--accent);
  background: color-mix(in srgb, var(--surface-strong), var(--accent) 6%);
  box-shadow:
    0 0 0 3px color-mix(in srgb, var(--accent), transparent 65%),
    var(--shadow-soft);
}


.doc-links { display:flex; gap:8px; padding: 0 4px; margin-bottom: 8px; }
.doc-links a { font-size: .8rem; color: var(--muted); text-decoration: none; }
.doc-links a:hover { color: var(--text); }

</style>
