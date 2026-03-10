<script lang="ts">
    import { createEventDispatcher } from "svelte"
    import type { Document } from "../types"
    import CardPreview from "./CardPreview.svelte"
    import { deleteDocument, getTags, normalizeTag, setDocumentTags, tagExists, updateDocument} from "../api"

    let showPreview = false

    export let doc: Document

    let editing = false
    let editedText = doc.recognized_text


    type DocumentCardEvents = {
        deleted: { id: string },
        tagClick: { tag: string }
    }

    const dispatch = createEventDispatcher<DocumentCardEvents>()

    async function save() {
        await updateDocument(doc._id, {
            recognized_text: editedText
        })

        doc.recognized_text = editedText
        editing = false
    }

    async function addTagToCard() {
        const availableTags = await getTags()
        const currentTags = doc.tags ?? []
        const candidates = availableTags.filter(tag => !currentTags.includes(tag))

        if (candidates.length === 0) {
            alert("No available tags to add")
            return
        }

        const entered = prompt(`Enter one tag to add:\n${candidates.join(", ")}`)
        if (!entered) return

        const normalized = normalizeTag(entered)
        if (!tagExists(candidates, normalized)) {
            alert("Tag is not in available list")
            return
        }

        const updated = await setDocumentTags(doc._id, [...currentTags, normalized])
        doc.tags = updated.tags ?? [...currentTags, normalized]
    }

    async function removeTagFromCard() {
        const currentTags = doc.tags ?? []
        if (currentTags.length === 0) {
            alert("This card has no tags")
            return
        }

        const entered = prompt(`Enter one tag to remove:\n${currentTags.join(", ")}`)
        if (!entered) return

        const normalized = normalizeTag(entered)
        if (!tagExists(currentTags, normalized)) {
            alert("Tag is not attached to this card")
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

</script>


<div class="card">
    <!-- svelte-ignore a11y_click_events_have_key_events -->
    <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
    <img
        src={`http://localhost:8000/uploads/${doc.filename}`}
        alt=""
        on:click={() => showPreview = true}
    />


        {#if showPreview}
        <CardPreview
            {doc}
            bind:editedText
            {editing}
            on:close={() => showPreview = false}
            on:save={save}
            on:delete={remove}
            on:editToggle={() => editing = !editing}
            on:addTag={addTagToCard}
            on:removeTag={removeTagFromCard}
            on:tagClick={handleTagClick}
        />
    {/if}
</div>



<style>




.card {
    border: 1px solid #dddddd84;
    border-radius: 8px;
    padding: 15px;
    background: var(--card);
    display: flex;
    flex-direction: column;
    justify-content: flex-start;
    break-inside: avoid;
    margin-bottom: 20px;
}


img {
    width: 100%;
    border-radius: 6px;
    margin-bottom: 5px;
}



</style>
