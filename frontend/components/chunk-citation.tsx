import { Badge } from "@/components/ui/badge"

interface ChunkCitationProps {
  chunkId: string
}

export function ChunkCitation({ chunkId }: ChunkCitationProps) {
  return (
    <Badge
      variant="outline"
      className="font-mono text-[11px] text-primary/80 border-primary/25 bg-primary/5 hover:bg-primary/10 transition-colors"
    >
      {chunkId}
    </Badge>
  )
}
