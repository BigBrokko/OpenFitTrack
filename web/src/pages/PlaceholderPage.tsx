/** A page that exists in the navigation but gets its content in a later step. */
export function PlaceholderPage({ title }: { title: string }) {
  return (
    <section>
      <h2 className="text-xl font-semibold">{title}</h2>
      <p className="mt-2 text-slate-600 dark:text-slate-400">
        Deze pagina komt in de volgende stap.
      </p>
    </section>
  )
}
