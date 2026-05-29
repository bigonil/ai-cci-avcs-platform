import { Badge } from "@/components/ui/badge"

interface ChunkCitationProps {
  chunkId: string
}

export function ChunkCitation({ chunkId }: ChunkCitationProps) {
  return (
    <Badge variant="outline" className="font-mono text-xs">
      {chunkId}
    </Badge>
  )
}
