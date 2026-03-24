// api.ts
//const BACKEND_HOST = window.location.hostname; // automatically matches localhost or LAN IP
//const API_URL = `http://${BACKEND_HOST}:8000/api`;
//console.log(BACKEND_HOST);

//const API_URL = "http://192.168.31.162:8000/api"; // your Mac’s LAN IP

export const API_URL = "/api"; // Use your LAN IP

//export const API_URL = `http://${window.location.hostname}:8000/api`

console.log(API_URL);

//export const UPLOADS_URL = "http://localhost:8000/uploads";

export const UPLOADS_URL = "/uploads"

console.log(UPLOADS_URL);

export async function uploadImage(file: File) {
    const formData = new FormData()
    formData.append("file", file)

    const res = await fetch(`${API_URL}/upload`, {
        method: "POST",
        body: formData
    })

    if (!res.ok) {
        throw new Error("Failed to upload image")
    }

    return await res.json()
}

export async function uploadImagesToDocument(documentId: string, files: File[]) {
    const formData = new FormData()
    for (const file of files) {
        formData.append("files", file)
    }

    const res = await fetch(`${API_URL}/documents/${documentId}/gallery`, {
        method: "POST",
        body: formData
    })

    const data = await res.json().catch(() => ({}))

    if (!res.ok) {
        throw new Error(data.detail || "Failed to upload images to card")
    }

    return data
}

export async function uploadDocumentAttachments(documentId: string, files: File[]) {
    const formData = new FormData()
    for (const file of files) {
        formData.append("files", file)
    }

    const response = await fetch(`${API_URL}/documents/${documentId}/attachments`, {
        method: "POST",
        body: formData
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(data.detail || "Failed to upload files to card")
    }

    return data
}

export async function getDocuments() {
    const res = await fetch(`${API_URL}/documents`)
    if (!res.ok) throw new Error("Failed to fetch documents")
    return await res.json()
}

export async function deleteDocument(id: string) {
    const res = await fetch(`${API_URL}/documents/${id}`, {
        method: "DELETE"
    })

    if (!res.ok) throw new Error("Failed to delete document")
}

export async function updateDocument(id: string, data: any) {
    const response = await fetch(`${API_URL}/documents/${id}`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(data)
    })

    if (!response.ok) {
        throw new Error("Failed to update document")
    }

    return response.json()
}


export async function setDocumentTags(id: string, tags: string[]) {
    return updateDocument(id, { tags })
}

export async function searchDocuments(q: string) {
    const res = await fetch(`${API_URL}/search?q=${encodeURIComponent(q)}`)
    if (!res.ok) throw new Error("Search request failed")
    return await res.json()
}

export function normalizeTag(tag: string) {
    return tag.trim().toLowerCase()
}

export function tagExists(tags: string[], tag: string) {
    const normalized = normalizeTag(tag)
    return tags.some(existing => normalizeTag(existing) === normalized)
}

export async function getTags(): Promise<string[]> {
    const response = await fetch(`${API_URL}/tags`)
    if (!response.ok) {
        throw new Error("Failed to fetch tags")
    }

    const data = await response.json()
    return data.tags ?? []
}


export async function createTag(tag: string) {
    const response = await fetch(`${API_URL}/tags`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ tag })
    })

    const payload = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(payload.detail || "Failed to create tag")
    }

    return payload
}

export async function deleteTag(tag: string) {
    const response = await fetch(`${API_URL}/tags/${encodeURIComponent(normalizeTag(tag))}`, {
        method: "DELETE"
    })

    const payload = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(payload.detail || "Failed to delete tag")
    }

    return payload
}



export interface ImageEditPayload {
    rotate_degrees?: number
    image_filename?: string
    crop?: {
        x_percent: number
        y_percent: number
        width_percent: number
        height_percent: number
    }
}

export async function editDocumentImage(id: string, payload: ImageEditPayload) {
    const response = await fetch(`${API_URL}/documents/${id}/image`, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(data.detail || "Failed to edit image")
    }

    return data
}

export async function deleteDocumentAttachment(id: string, attachmentFilename: string) {
    const response = await fetch(`${API_URL}/documents/${id}/attachments/${encodeURIComponent(attachmentFilename)}`, {
        method: "DELETE"
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(data.detail || "Failed to delete attachment")
    }

    return data
}

export async function deleteDocumentImage(id: string, imageFilename: string) {
    const response = await fetch(`${API_URL}/documents/${id}/gallery/${encodeURIComponent(imageFilename)}`, {
        method: "DELETE"
    })

    const data = await response.json().catch(() => ({}))

    if (!response.ok) {
        throw new Error(data.detail || "Failed to delete image")
    }

    return data
}
