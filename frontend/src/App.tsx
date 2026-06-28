import { Button } from "@/components/ui/button"

function App() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 bg-muted/40 p-6">
      <div className="max-w-xl space-y-4 text-center">
        <h1 className="text-4xl font-bold tracking-tight">
          AI Recruitment Copilot
        </h1>

        <p className="text-muted-foreground">
          Recruitment intelligence powered by controlled AI workflows.
        </p>

        <Button>Open recruiter dashboard</Button>
      </div>
    </main>
  )
}

export default App