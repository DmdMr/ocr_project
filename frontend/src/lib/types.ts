export interface GalleryImage {
    filename: string
    path?: string
    file_hash?: string
    recognized_text?: string
    image_version?: string
    created_at?: string
}

export interface AttachmentFile {
    filename: string
    path?: string
    original_name?: string
    content_type?: string
    size?: number
    created_at?: string
}


export interface Document {
    _id: string
    filename: string
    display_filename?: string
    recognized_text: string
    created_at: string
    is_archived?: boolean
    archived_at?: string | null
    tags?: string[]  
    image_version?: string
    gallery_images?: GalleryImage[]
    attachments?: AttachmentFile[]
    custom_fields?: Record<string, string | number | null>
    created_by_user_id?: string
    created_by_username?: string
    updated_by_user_id?: string
    updated_by_username?: string
}

export interface CardCustomFieldSetting {
    name: string
    type: "text" | "number"
    created_at?: string
}
