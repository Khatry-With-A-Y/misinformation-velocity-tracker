interface TechItemProps {
  title: string
  description: string
}

export default function About() {
  return (
    <div className="max-w-3xl mx-auto">
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-4 text-foreground">About the Tracker</h1>
        <p className="text-xl text-muted-foreground">
          Misinformation Velocity Tracker helps journalists and fact-checkers in Nepal understand
          how a claim travels and changes across public platforms.
        </p>
      </div>

      <div className="bg-card text-card-foreground rounded-lg shadow-sm p-8 mb-8">
        <h2 className="text-2xl font-semibold mb-6 text-card-foreground">What it does</h2>
        <ul className="space-y-4">
          <TechItem
            title="Mutation Tree"
            description="Visualize how a claim mutates as it is reshared, quoted, and rephrased across platforms."
          />
          <TechItem
            title="Velocity"
            description="Track the speed of spread over time so you can spot surges early."
          />
          <TechItem
            title="Platform Breakdown"
            description="See which public platforms are driving reach for a given claim."
          />
          <TechItem
            title="Verdict"
            description="Attach a fact-check verdict to give readers clear, sourced guidance."
          />
        </ul>
      </div>

      <div className="bg-card text-card-foreground rounded-lg shadow-sm p-8">
        <h2 className="text-2xl font-semibold mb-6 text-card-foreground">Project Goals</h2>
        <ul className="list-disc list-inside space-y-3 text-muted-foreground">
          <li>Help newsrooms respond to viral misinformation faster</li>
          <li>Make the spread and mutation of a claim easy to see at a glance</li>
          <li>Support both Nepali and English claims</li>
          <li>Keep the workflow simple: paste a claim, analyze, and share the verdict</li>
        </ul>
      </div>
    </div>
  )
}

function TechItem({ title, description }: TechItemProps) {
  return (
    <li className="flex items-start space-x-4 p-4 rounded-lg bg-muted/50">
      <div className="flex-1">
        <h3 className="font-semibold text-card-foreground">{title}</h3>
        <p className="text-muted-foreground">{description}</p>
      </div>
    </li>
  )
}
