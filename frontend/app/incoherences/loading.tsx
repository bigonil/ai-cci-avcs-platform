import { Skeleton } from "@/components/ui/skeleton"

export function IncoherenceListSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="rounded-lg border overflow-hidden">
          <div className="h-1 bg-muted" />
          <Skeleton className="h-20 rounded-none" />
        </div>
      ))}
    </div>
  )
}

export default function Loading() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-60" />
      <IncoherenceListSkeleton />
    </div>
  )
}
