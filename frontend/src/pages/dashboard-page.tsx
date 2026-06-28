import { RefreshCw } from "lucide-react"

import { Button } from "@/components/ui/button"
import { useHealthQuery } from "@/features/health/use-health-query"
import { cn } from "@/lib/utils"

const dashboardStats = [
  {
    label: "Total jobs",
    value: "0",
    description: "No jobs created yet",
  },
  {
    label: "Total candidates",
    value: "0",
    description: "No candidates uploaded yet",
  },
  {
    label: "Pending analyses",
    value: "0",
    description: "No analyses waiting",
  },
  {
    label: "Reports awaiting approval",
    value: "0",
    description: "No reports require review",
  },
]

function DashboardPage() {
  const healthQuery = useHealthQuery()

  const isConnected =
    healthQuery.isSuccess &&
    healthQuery.data.status === "ok"

  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">
            Recruiter dashboard
          </h2>

          <p className="mt-1 text-muted-foreground">
            Review jobs, candidates, analyses and approval requests.
          </p>
        </div>

        <Button>Create job</Button>
      </section>

      <section className="rounded-xl border bg-card p-5 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span
                className={cn(
                  "size-2.5 rounded-full",
                  healthQuery.isPending && "bg-muted-foreground",
                  isConnected && "bg-green-500",
                  healthQuery.isError && "bg-destructive",
                )}
              />

              <h3 className="font-semibold">
                Backend connection
              </h3>
            </div>

            {healthQuery.isPending && (
              <p className="mt-2 text-sm text-muted-foreground">
                Checking the FastAPI backend...
              </p>
            )}

            {healthQuery.isError && (
              <p className="mt-2 text-sm text-destructive">
                The backend is unavailable. Make sure FastAPI is running.
              </p>
            )}

            {isConnected && (
              <div className="mt-2 text-sm text-muted-foreground">
                <p>{healthQuery.data.service} is connected.</p>
                <p>
  Running in {healthQuery.data.environment.toUpperCase()} mode
</p>
              </div>
            )}
          </div>

          <Button
            variant="outline"
            onClick={() => healthQuery.refetch()}
            disabled={healthQuery.isFetching}
          >
            <RefreshCw
              className={cn(
                "size-4",
                healthQuery.isFetching && "animate-spin",
              )}
            />
            Check again
          </Button>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {dashboardStats.map((stat) => (
          <article
            key={stat.label}
            className="rounded-xl border bg-card p-5 text-card-foreground shadow-sm"
          >
            <p className="text-sm font-medium text-muted-foreground">
              {stat.label}
            </p>

            <p className="mt-3 text-3xl font-bold">
              {stat.value}
            </p>

            <p className="mt-2 text-xs text-muted-foreground">
              {stat.description}
            </p>
          </article>
        ))}
      </section>

      <section className="rounded-xl border bg-card p-6 shadow-sm">
        <h3 className="font-semibold">Recent activity</h3>

        <div className="mt-6 flex min-h-48 items-center justify-center rounded-lg border border-dashed">
          <div className="max-w-sm text-center">
            <p className="font-medium">
              No recruitment activity yet
            </p>

            <p className="mt-1 text-sm text-muted-foreground">
              Create your first job and upload candidates to begin an
              analysis.
            </p>
          </div>
        </div>
      </section>
    </div>
  )
}

export default DashboardPage