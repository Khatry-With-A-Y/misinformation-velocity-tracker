interface TechItemProps {
  title: string
  description: string
}

export default function About() {
  return (
    <div className="mx-auto max-w-3xl space-y-14 py-6">
      <div>
        <p className="text-xs font-semibold uppercase tracking-widest text-primary">About</p>
        <h1 className="mt-3 text-3xl font-bold tracking-tight text-foreground sm:text-4xl">
          What GuffGuard does
        </h1>
        <p className="mt-4 text-base leading-relaxed text-muted-foreground sm:text-lg">
          GuffGuard helps journalists and fact-checkers in Nepal understand how a claim travels
          and changes across public platforms: its velocity, its mutations, and the evidence
          behind each verdict.
        </p>
      </div>

      <section aria-labelledby="capabilities-title">
        <h2
          id="capabilities-title"
          className="text-sm font-semibold uppercase tracking-widest text-muted-foreground"
        >
          Capabilities
        </h2>
        <ul className="mt-5 space-y-6">
          <TechItem
            title="Mutation tree"
            description="Visualize how a claim mutates as it is reshared, quoted, and rephrased across platforms."
          />
          <TechItem
            title="Velocity"
            description="Track the speed of spread over time so you can spot surges early."
          />
          <TechItem
            title="Platform breakdown"
            description="See which public platforms are driving reach for a given claim."
          />
          <TechItem
            title="Verdict"
            description="Attach a fact-check verdict to give readers clear, sourced guidance. AI flags stay labeled as signals, not verified facts."
          />
        </ul>
      </section>

      <section aria-labelledby="goals-title">
        <h2
          id="goals-title"
          className="text-sm font-semibold uppercase tracking-widest text-muted-foreground"
        >
          Project goals
        </h2>
        <ul className="mt-5 space-y-3 text-muted-foreground">
          <li className="flex gap-3">
            <span aria-hidden="true" className="mt-2 h-1 w-1 shrink-0 rounded-full bg-primary" />
            Help newsrooms respond to viral misinformation faster
          </li>
          <li className="flex gap-3">
            <span aria-hidden="true" className="mt-2 h-1 w-1 shrink-0 rounded-full bg-primary" />
            Make the spread and mutation of a claim easy to see at a glance
          </li>
          <li className="flex gap-3">
            <span aria-hidden="true" className="mt-2 h-1 w-1 shrink-0 rounded-full bg-primary" />
            Support both Nepali and English claims
          </li>
          <li className="flex gap-3">
            <span aria-hidden="true" className="mt-2 h-1 w-1 shrink-0 rounded-full bg-primary" />
            Keep the workflow simple: paste a claim, analyze, and share the verdict
          </li>
        </ul>
      </section>
    </div>
  )
}

function TechItem({ title, description }: TechItemProps) {
  return (
    <li className="border-t border-border pt-4">
      <h3 className="font-semibold text-foreground">{title}</h3>
      <p className="mt-1.5 text-sm leading-relaxed text-muted-foreground">{description}</p>
    </li>
  )
}
