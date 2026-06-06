"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import { ShieldCheck, AlertTriangle, ClipboardList, BarChart2, Moon, Sun, Activity } from "lucide-react"
import { useTheme } from "next-themes"
import { Button } from "@/components/ui/button"

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: BarChart2 },
  { href: "/incoherences", label: "Incoerenze", icon: AlertTriangle },
  { href: "/hitl", label: "Coda HITL", icon: ClipboardList },
  { href: "/audit", label: "Audit Trail", icon: ShieldCheck },
] as const

export function Nav() {
  const pathname = usePathname()
  const { resolvedTheme, setTheme } = useTheme()

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="container flex h-14 items-center gap-6">
        <Link href="/" className="flex items-center gap-2 mr-1 shrink-0">
          <Activity className="size-4 text-primary" />
          <span className="font-semibold text-sm tracking-tight">
            CCI<span className="text-muted-foreground font-normal"> / </span>AVCS
          </span>
        </Link>

        <nav className="flex items-center gap-0.5 flex-1">
          {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
            const active = pathname === href
            return (
              <Link
                key={href}
                href={href}
                className={cn(
                  "relative flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
                  active
                    ? "text-foreground"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                )}
              >
                <Icon className={cn("size-4", active && "text-primary")} />
                {label}
                {active && (
                  <span className="absolute bottom-0 left-3 right-3 h-0.5 rounded-full bg-primary" />
                )}
              </Link>
            )
          })}
        </nav>

        <Button
          variant="ghost"
          size="icon"
          className="size-8 shrink-0 relative"
          onClick={() => setTheme(resolvedTheme === "dark" ? "light" : "dark")}
          aria-label="Cambia tema"
        >
          <Sun className="size-4 scale-100 transition-all duration-300 dark:scale-0" />
          <Moon className="absolute size-4 scale-0 transition-all duration-300 dark:scale-100" />
        </Button>
      </div>
    </header>
  )
}
