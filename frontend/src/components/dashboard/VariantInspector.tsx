import type { TreeNode } from '../../lib/api'

export function VariantInspector({ variant }: { variant?: TreeNode | null }) {
  if (!variant)
    return (
      <aside className="rounded-md bg-muted/50 p-4 text-sm text-muted-foreground">
        Select a node to inspect its full text and provenance.
      </aside>
    )
  return (
    <aside className="rounded-md border border-border p-4">
      <p className="text-sm leading-relaxed">{variant.text || variant.label}</p>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
        <div>
          <dt className="text-muted-foreground">Platform</dt>
          <dd>{variant.platform || 'Unknown'}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Language</dt>
          <dd>{variant.language || 'Unknown'}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Mutation</dt>
          <dd>{variant.mutation_type || 'Unknown'}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Seen</dt>
          <dd>{variant.ts ? new Date(variant.ts).toLocaleString() : 'Unknown'}</dd>
        </div>
      </dl>
      {variant.evidence_url && (
        <a
          className="mt-4 inline-block text-sm font-medium text-primary underline-offset-4 hover:underline"
          href={variant.evidence_url}
          target="_blank"
          rel="noreferrer"
        >
          Review evidence
        </a>
      )}
    </aside>
  )
}
