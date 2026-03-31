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


export type TextContentBlock = {
    id: string
    type: "text"
    text: string
}

export type HeadingContentBlock = {
    id: string
    type: "heading"
    text: string
    level: 1 | 2 | 3
}

export type DividerContentBlock = {
    id: string
    type: "divider"
}

export type ImageContentBlock = {
    id: string
    type: "image"
    image_filename: string
    image_path?: string
    caption?: string
}

export type ContentBlock = TextContentBlock | HeadingContentBlock | DividerContentBlock | ImageContentBlock

export interface Document {
    _id: string
    filename: string
    display_filename?: string
    recognized_text: string
    body_markdown?: string
    created_at: string
    is_archived?: boolean
    archived_at?: string | null
    tags?: string[]  
    image_version?: string
    gallery_images?: GalleryImage[]
    attachments?: AttachmentFile[]
    custom_fields?: Record<string, string | number | null>
    content_blocks?: ContentBlock[]
}

export interface CardCustomFieldSetting {
    name: string
    type: "text" | "number"
    created_at?: string
}
