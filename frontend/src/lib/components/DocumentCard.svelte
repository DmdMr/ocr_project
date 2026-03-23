<script lang="ts">
    import { createEventDispatcher } from "svelte"
    import type { Document } from "../types"
    import CardPreview from "./CardPreview.svelte"
    import { tagHue } from "../tagColors"
    import {
        deleteDocument,
        getTags,
        normalizeTag,
        setDocumentTags,
        tagExists,
        updateDocument,
        uploadImagesToDocument,
        UPLOADS_URL
    } from "../api"
    

    export let showPreview = false

    export let doc: Document

    export let search = ""

    export let selected = false
    export let selectionActive = false

    const dispatch = createEventDispatcher()


    //const dispatch = createEventDispatcher<DocumentCardEvents & {
    //    toggleSelect: undefined
    //}>()

    let editing = false
    let editedText = doc.recognized_text
    let galleryUploading = false

    

    function escapeRegExp(value: string) {
        return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
    }

    function handleCardClick() {
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
        if (selectionActive) {
            dispatch("toggleSelection", { id: doc._id })
            return
        }

        showPreview = true
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

    async function addTagToCard() {
        const availableTags = await getTags()
        const currentTags = doc.tags ?? []
        const candidates = availableTags.filter(tag => !currentTags.includes(tag))

        if (candidates.length === 0) {
            alert("Нет доступных тегов для добавления")
            return
        }

        const entered = prompt(`Введите тег для добавления:\n${candidates.join(", ")}`)
        if (!entered) return

        const normalized = normalizeTag(entered)
        if (!tagExists(candidates, normalized)) {
            alert("Тега нет в списке доступных")
            return
        }

        const updated = await setDocumentTags(doc._id, [...currentTags, normalized])
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

    async function removeTagFromCard() {
        const currentTags = doc.tags ?? []
        if (currentTags.length === 0) {
            alert("У этой карточки нет тегов")
            return
        }

        const entered = prompt(`Введите тег для удаления:\n${currentTags.join(", ")}`)
        if (!entered) return

        const normalized = normalizeTag(entered)
        if (!tagExists(currentTags, normalized)) {
            alert("Тег не привязан к этой карточке")
            return
        }

        const nextTags = currentTags.filter(tag => normalizeTag(tag) !== normalized)
        const updated = await setDocumentTags(doc._id, nextTags)
        applyDocumentUpdate(updated)
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
        <img src={cardImageSrc(doc)} alt="" on:click={() => showPreview = true}/>


        

        <button
            class="select-checkbox"
            class:visible={selected}
            aria-label="Выбрать карточку"
            on:click={handleCheckboxClick}
        >
            {#if selected}{/if}
        </button>
    </div>
    
    <div class="card-filename">
        {@html highlightedFilename(
            getFilenameWithoutExtension(doc.display_filename || doc.filename || ""),
            search
        )}
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


    {#if showPreview}
        <CardPreview
            {doc}
            //on:openPreview={() => isPreviewOpen = true}
            //on:closePreview={() => isPreviewOpen = false}
            bind:editedText
            {editing}
            on:close={() => showPreview = false}
            on:save={save}
            on:saveFilename={saveFilename}
            on:delete={remove}
            on:editToggle={() => editing = !editing}
            on:addTag={addTagToCard}
            on:removeTag={removeTagFromCard}
            on:tagClick={handleTagClick}
            on:documentUpdated={handleDocumentUpdated}
            on:addImages={uploadToCard}
            {galleryUploading}
        />
    {/if}
    
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


.card-media {
  position: relative;
  border-radius: var(--radius-md);
  overflow: hidden;
  cursor: pointer;
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


</style>
