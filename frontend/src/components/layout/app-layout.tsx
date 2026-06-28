import {
  Bot,
  BriefcaseBusiness,
  LayoutDashboard,
  Users,
} from "lucide-react"
import { NavLink, Outlet } from "react-router"

import { cn } from "@/lib/utils"

const navigationItems = [
  {
    label: "Dashboard",
    path: "/dashboard",
    icon: LayoutDashboard,
  },
  {
    label: "Jobs",
    path: "/jobs",
    icon: BriefcaseBusiness,
  },
  {
    label: "Candidates",
    path: "/candidates",
    icon: Users,
  },
]

function AppLayout() {
  return (
    <div className="min-h-screen bg-muted/30 md:grid md:grid-cols-[240px_minmax(0,1fr)]">
      <aside className="hidden border-r bg-background md:flex md:flex-col">
        <div className="flex h-16 items-center gap-3 border-b px-5">
          <div className="flex size-9 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Bot className="size-5" />
          </div>

          <div>
            <p className="font-semibold leading-none">Recruitment Copilot</p>
            <p className="mt-1 text-xs text-muted-foreground">
              AI-assisted hiring
            </p>
          </div>
        </div>

        <nav className="flex flex-1 flex-col gap-1 p-3">
          {navigationItems.map((item) => {
            const Icon = item.icon

            return (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )
                }
              >
                <Icon className="size-4" />
                {item.label}
              </NavLink>
            )
          })}
        </nav>
      </aside>

      <div className="min-w-0">
        <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
          <div className="flex h-16 items-center justify-between px-4 sm:px-6">
            <div>
              <h1 className="font-semibold">AI Recruitment Copilot</h1>
              <p className="text-xs text-muted-foreground">
                Human-controlled recruitment intelligence
              </p>
            </div>

            <div className="flex size-9 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
              HV
            </div>
          </div>

          <nav className="flex gap-2 overflow-x-auto border-t px-4 py-2 md:hidden">
            {navigationItems.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  cn(
                    "whitespace-nowrap rounded-md px-3 py-2 text-sm font-medium",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : "text-muted-foreground",
                  )
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>
        </header>

        <main className="p-4 sm:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default AppLayout