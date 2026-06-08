export function ChunkCitation({ chunkId }: { chunkId: string }) {
  return (
    <span
      style={{
        display: 'inline-block',
        fontFamily: "'SF Mono', monospace",
        fontSize: 10,
        padding: '1px 6px',
        borderRadius: 4,
        background: 'rgba(129,140,248,0.1)',
        color: 'var(--color-primary)',
        border: '1px solid rgba(129,140,248,0.25)',
        cursor: 'default',
      }}
      title={chunkId}
    >
      {chunkId}
    </span>
  )
}
