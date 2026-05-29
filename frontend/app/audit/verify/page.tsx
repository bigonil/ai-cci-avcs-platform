import { AuditChainStatus } from "@/components/audit-chain-status"
import { buttonVariants } from "@/components/ui/button"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"

export default function AuditVerifyPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link href="/audit" className={buttonVariants({ variant: "ghost", size: "sm" })}>
          <ArrowLeft className="size-4" />
          Audit Trail
        </Link>
        <h1 className="text-2xl font-semibold">Verifica integrità hash chain</h1>
      </div>
      <p className="text-sm text-muted-foreground max-w-prose">
        Ricalcola l&apos;intera catena SHA-256 del log di audit e verifica che nessun documento sia
        stato modificato o cancellato.
      </p>
      <AuditChainStatus />
    </div>
  )
}
