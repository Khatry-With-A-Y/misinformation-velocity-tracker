import type { TreeNode } from '../../lib/api'

export function VariantInspector({ variant }: { variant?: TreeNode | null }) {
  if (!variant)
    return (
      <aside className="flex items-center justify-center rounded-md border border-dashed border-border p-6 text-center text-sm text-muted-foreground">
        Select a node in the tree to inspect its full text and provenance.
      </aside>
    )
  return (
    <aside className="self-start rounded-md border border-border bg-background p-4">
      <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
        Variant detail
      </p>
      <p className="mt-2 text-sm leading-relaxed text-foreground">
        {variant.text || variant.label}
      </p>
      <dl className="mt-4 grid grid-cols-2 gap-3 text-xs">
        <div>
          <dt className="text-muted-foreground">Platform</dt>
          <dd className="mt-0.5 font-medium">{variant.platform || 'Unknown'}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Language</dt>
          <dd className="mt-0.5 font-medium">{variant.language || 'Unknown'}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Mutation</dt>
          <dd className="mt-0.5 font-medium">{variant.mutation_type || 'Unknown'}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Seen</dt>
          <dd className="mt-0.5 font-medium">
            {variant.ts ? new Date(variant.ts).toLocaleString() : 'Unknown'}
          </dd>
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
