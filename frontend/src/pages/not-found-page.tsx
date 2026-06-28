import { Link } from "react-router"

function NotFoundPage() {
  return (
    <div className="flex min-h-[60vh] items-center justify-center">
      <div className="text-center">
        <p className="text-sm font-semibold text-primary">404</p>

        <h2 className="mt-2 text-3xl font-bold">Page not found</h2>

        <p className="mt-2 text-muted-foreground">
          The page you requested does not exist.
        </p>

        <Link
          to="/dashboard"
          className="mt-6 inline-flex rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
        >
          Return to dashboard
        </Link>
      </div>
    </div>
  )
}

export default NotFoundPage