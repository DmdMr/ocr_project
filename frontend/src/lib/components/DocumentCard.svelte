<script lang="ts">
    import { createEventDispatcher } from "svelte"
    import type { Document } from "../types"
    import CardPreview from "./CardPreview.svelte"
    import { tagHue } from "../tagColors"
    import {
        deleteDocument,
        editDocumentImage,
        getTags,
        normalizeTag,
        setDocumentTags,
        tagExists,
        updateDocument,
        uploadImagesToDocument,
        UPLOADS_URL
    } from "../api"
    

    let showPreview = false

    export let doc: Document

    let editing = false
    let editedText = doc.recognized_text
    let galleryUploading = false


    type DocumentCardEvents = {
        deleted: { id: string }
        tagClick: { tag: string }
    }

    const dispatch = createEventDispatcher<DocumentCardEvents>()

    async function save() {
        const updated = await updateDocument(doc._id, {
            recognized_text: editedText
        })

        doc = updated
        editedText = updated.recognized_text
        editing = false
    }

    async function saveFilename(event: CustomEvent<{ display_filename: string }>) {
        const updated = await updateDocument(doc._id, {
            display_filename: event.detail.display_filename
        })

        doc = updated
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
        doc.tags = updated.tags ?? [...currentTags, normalized]
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

            doc = result.document
            editedText = doc.recognized_text

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

    async function handleImageEdit(event: CustomEvent<{ payload: { rotate_degrees?: number; image_filename?: string; crop?: { x_percent: number; y_percent: number; width_percent: number; height_percent: number } } }>) {
        const updated = await editDocumentImage(doc._id, event.detail.payload)
        doc = updated
        editedText = updated.recognized_text
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
        doc.tags = updated.tags ?? nextTags
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

</script>


<div class="card">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <img src={`${UPLOADS_URL}/${doc.filename}`} alt="" on:click={() => showPreview = true}/>


    <div class="card-tags">
        {#if doc.tags?.length}
            {#each doc.tags as tag}
                <button class="card-tag tag-colored" style={`--tag-hue: ${tagHue(tag)}`} on:click={() => selectTagFromCard(tag)}>{tag}</button>
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
            on:imageEdit={handleImageEdit}
            on:addImages={uploadToCard}
            {galleryUploading}
        />
    {/if}
</div>



<style>




.card {
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    padding: 14px;
    background: var(--surface-strong);
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    break-inside: avoid;
    margin-bottom: 20px;
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

.card-tags-empty {
    font-size: 0.82rem;
    color: var(--text-muted);
}



</style>
