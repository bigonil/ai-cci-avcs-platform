"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { ShieldCheck, AlertTriangle, ClipboardList, BarChart2 } from "lucide-react"

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: BarChart2 },
  { href: "/incoherences", label: "Incoerenze", icon: AlertTriangle },
  { href: "/hitl", label: "Coda HITL", icon: ClipboardList },
  { href: "/audit", label: "Audit Trail", icon: ShieldCheck },
] as const

export function Nav() {
  const pathname = usePathname()
  return (
    <header className="sticky top-0 z-40 border-b bg-background">
      <div className="container flex h-14 items-center gap-6">
        <span className="font-semibold tracking-tight text-sm">
          CCI / AVCS
        </span>
        <nav className="flex items-center gap-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                "hover:bg-muted hover:text-foreground",
                pathname === href
                  ? "bg-muted text-foreground"
                  : "text-muted-foreground"
              )}
            >
              <Icon className="size-4" />
              {label}
            </Link>
          ))}
        </nav>
      </div>
    </header>
  )
}
