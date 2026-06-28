import { Button } from "../components/ui/button"

function JobsPage() {
  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Jobs</h2>

          <p className="mt-1 text-muted-foreground">
            Create and manage job openings and their requirements.
          </p>
        </div>

        <Button>Create job</Button>
      </section>

      <section className="flex min-h-80 items-center justify-center rounded-xl border border-dashed bg-card p-6">
        <div className="max-w-md text-center">
          <h3 className="font-semibold">No jobs created</h3>

          <p className="mt-2 text-sm text-muted-foreground">
            Create a job opening before uploading and comparing candidates.
          </p>
        </div>
      </section>
    </div>
  )
}

export default JobsPage