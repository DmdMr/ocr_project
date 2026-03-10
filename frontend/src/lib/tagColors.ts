export function tagHue(tag: string): number {
    let hash = 0

    for (let index = 0; index < tag.length; index += 1) {
        hash = (hash * 31 + tag.charCodeAt(index)) % 360
    }

    return Math.abs(hash)
}
