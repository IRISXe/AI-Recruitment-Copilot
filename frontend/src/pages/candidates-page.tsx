import { Button } from "../components/ui/button"

function CandidatesPage() {
  return (
    <div className="space-y-6">
      <section className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight">Candidates</h2>

          <p className="mt-1 text-muted-foreground">
            Upload resumes and review extracted candidate information.
          </p>
        </div>

        <Button>Add candidate</Button>
      </section>

      <section className="flex min-h-80 items-center justify-center rounded-xl border border-dashed bg-card p-6">
        <div className="max-w-md text-center">
          <h3 className="font-semibold">No candidates added</h3>

          <p className="mt-2 text-sm text-muted-foreground">
            Add a candidate and upload their resume to begin processing.
          </p>
        </div>
      </section>
    </div>
  )
}

export default CandidatesPage