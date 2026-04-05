<script lang="ts">
    import { createEventDispatcher } from "svelte"
    import type { Document } from "../types"
    import CardPreview from "./CardPreview.svelte"
    import { tagHue } from "../tagColors"
    import {
        deleteDocument,
        updateDocument,
        uploadImagesToDocument,
        UPLOADS_URL
    } from "../api"

    let showPreview = false

    export let doc: Document
    export let search = ""
    export let selected = false
    export let selectionActive = false

    let editing = false
    let editedText = doc.recognized_text
    let galleryUploading = false

    function escapeRegExp(value: string) {
        return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    }

    function highlightedFilename(filename: string, searchText: string) {
        if (!searchText.trim()) return filename

        const escaped = escapeRegExp(searchText.trim())
        const regex = new RegExp(`(${escaped})`, "gi")

        return filename.replace(regex, '<mark class="filename-highlight">$1</mark>')
    }

    type DocumentRowEvents = {
        deleted: { id: string }
        tagClick: { tag: string }
        updated: { document: Document }
        toggleSelect: undefined
        toggleSelection: { id: string }
    }

    const dispatch = createEventDispatcher<DocumentRowEvents>()

    function openPreview() {
        if (selectionActive) {
            dispatch("toggleSelection", { id: doc._id })
            return
        }

        showPreview = true
    }

    function handleRowClick() {
        if (selectionActive) {
            dispatch("toggleSelect")
            return
        }

        showPreview = true
    }

    function handleCheckboxClick(event: MouseEvent) {
        event.stopPropagation()
        dispatch("toggleSelect")
    }

    function handleRowKeydown(event: KeyboardEvent) {
        if (event.key === "Enter" || event.key === " ") {
            event.preventDefault()
            openPreview()
        }
    }

    function applyDocumentUpdate(updated: Document) {
        doc = updated
        editedText = updated.recognized_text
        dispatch("updated", { document: updated })
    }

    function cardImageSrc(currentDoc: Document) {
        return `${UPLOADS_URL}/${currentDoc.filename}?v=${encodeURIComponent(currentDoc.image_version ?? currentDoc.created_at ?? "")}`
    }

    async function save() {
        const updated = await updateDocument(doc._id, {
            recognized_text: editedText
        })

        applyDocumentUpdate(updated)
        editing = false
    }

    async function saveFilename(event: CustomEvent<{ display_filename: string }>) {
        const updated = await updateDocument(doc._id, {
            display_filename: event.detail.display_filename
        })

        applyDocumentUpdate(updated)
    }

    async function uploadToCard(event: CustomEvent<{ files: File[] }>) {
        const files = event.detail.files
        if (!files.length) return

        galleryUploading = true

        try {
            const result = await uploadImagesToDocument(doc._id, files)

            if (!result.document) {
                throw new Error("Сервер не вернул обновленные данные карточки")
            }

            applyDocumentUpdate(result.document)

            const addedCount = Number(result.added_count ?? 0)
            if (addedCount > 0) {
                alert(`Добавлено ${addedCount} изображений ${addedCount > 1 ? "s" : ""}`)
            }
        } catch (error) {
            const message = error instanceof Error ? error.message : "Не удалось добавить изображения в карточку"
            alert(message)
            console.error("Не удалось загрузить изображения в галерею", error)
        } finally {
            galleryUploading = false
        }
    }

    function handleDocumentUpdated(event: CustomEvent<{ document: Document }>) {
        applyDocumentUpdate(event.detail.document)
    }

    async function remove() {
        await deleteDocument(doc._id)
        dispatch("deleted", { id: doc._id })
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
    class="row-card"
    class:selected-row={selected}
    role="button"
    tabindex="0"
    aria-pressed={selectionActive ? selected : undefined}
    on:click={openPreview}
    on:keydown={handleRowKeydown}
>
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="row-media" on:click={handleRowClick}>
        <img
            class="row-thumb"
            src={cardImageSrc(doc)}
            alt=""
            on:click={() => showPreview = true}
        />

        <button
            class="select-checkbox"
            class:visible={selected}
            aria-label="Выбрать карточку"
            on:click={handleCheckboxClick}
        >
            {#if selected}{/if}
        </button>
    </div>

    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="row-main" on:click={handleRowClick}>
        <div class="row-filename">
            {@html highlightedFilename(
                getFilenameWithoutExtension(doc.display_filename || doc.filename || ""),
                search
            )}
        </div>

    <div class="row-links">
        <a href={`#/documents/${doc._id}/editor`} on:click|stopPropagation>New doc view</a>
        <a href={`#/documents/${doc._id}/classic`} on:click|stopPropagation>Classic page</a>
    </div>

        <div class="row-tags">
            {#if doc.tags?.length}
                {#each doc.tags as tag}
                    <button
                        class="row-tag tag-colored"
                        style={`--tag-hue: ${tagHue(tag)}`}
                        on:click|stopPropagation={() => selectTagFromCard(tag)}
                    >
                        {tag}
                    </button>
                {/each}
            {/if}
        </div>
    </div>

    {#if showPreview}
        <CardPreview
            {doc}
            bind:editedText
            {editing}
            on:close={() => showPreview = false}
            on:save={save}
            on:saveFilename={saveFilename}
            on:delete={remove}
            on:editToggle={() => editing = !editing}
            on:tagClick={handleTagClick}
            on:documentUpdated={handleDocumentUpdated}
            on:addImages={uploadToCard}
            {galleryUploading}
        />
    {/if}
</div>


<style>

.row-card {
    position: relative;
    display: flex;
    align-items: center;
    gap: 14px;
    width: 100%;
    padding: 12px 14px;
    margin-bottom: 12px;

    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    background: var(--surface-strong);
    box-shadow: var(--shadow-soft);
    backdrop-filter: blur(16px) saturate(1.15);
    -webkit-backdrop-filter: blur(16px) saturate(1.15);
    transition: box-shadow 0.18s ease, border-color 0.18s ease, background 0.18s ease;
}

.row-card.selected-row {
    border-color: var(--accent);
    background: color-mix(in srgb, var(--surface-strong), var(--accent) 6%);
    box-shadow:
        0 0 0 3px color-mix(in srgb, var(--accent), transparent 65%),
        var(--shadow-soft);
}

.row-media {
    position: relative;
    border-radius: 12px;
    overflow: hidden;
    cursor: pointer;
}

.row-thumb {
    width: 56px;
    height: 56px;
    object-fit: cover;
    border-radius: 12px;
    flex-shrink: 0;
    margin: 0;
    cursor: pointer;
}

.row-main {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
    width: 100%;
    cursor: pointer;
}

.row-filename {
    flex: left;
    min-width: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text);
    line-height: 1.3;
    word-break: break-word;
}

.row-tags {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: nowrap;
    overflow: hidden;
    flex-shrink: 1;
    min-width: 0;
}

.row-tag {
    min-height: 30px;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 0.82rem;
    flex-shrink: 0;
    white-space: nowrap;
}

.select-checkbox {
    position: absolute;
    top: 8px;
    left: 8px;
    width: 24px;
    height: 24px;
    border-radius: 8px;
    z-index: 3;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.18s ease, transform 0.18s ease;
}

.row-card:hover .select-checkbox,
.row-card.selected-row .select-checkbox,
.select-checkbox.visible {
    opacity: 1;
    pointer-events: auto;
}

:global(.filename-highlight) {
    background: #7CFC98;
    color: #0f172a;
    padding: 0 2px;
    border-radius: 4px;
}

@media (max-width: 768px) {
    .row-card {
        gap: 10px;
        padding: 10px 12px;
    }

    .row-thumb {
        width: 48px;
        height: 48px;
        border-radius: 10px;
    }

    .row-main {
        gap: 10px;
    }

    .row-filename {
        font-size: 0.95rem;
    }

    .row-tags {
        overflow-x: auto;
        overflow-y: hidden;
        scrollbar-width: none;
        -webkit-overflow-scrolling: touch;
    }

    .row-tags::-webkit-scrollbar {
        display: none;
    }
}



.row-links { display:flex; gap:8px; margin-bottom: 6px; }
.row-links a { font-size: .8rem; color: var(--muted); text-decoration: none; }
.row-links a:hover { color: var(--text); }
</style>
