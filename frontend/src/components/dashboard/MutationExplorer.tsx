import { useMemo, useState } from 'react'
import ReactFlow, {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  type Edge,
  type Node,
  type NodeProps,
} from 'reactflow'
import type { ClaimTree, TreeNode } from '../../lib/api'
import { VariantInspector } from './VariantInspector'

interface VariantNodeData {
  item: TreeNode
  origin: boolean
}

function time(item: TreeNode): number {
  if (!item.ts) return Number.POSITIVE_INFINITY
  const parsed = Date.parse(item.ts)
  return Number.isNaN(parsed) ? Number.POSITIVE_INFINITY : parsed
}

function compareNodes(a: TreeNode, b: TreeNode): number {
  return time(a) - time(b) || a.id.localeCompare(b.id)
}

function VariantNode({ data }: NodeProps<VariantNodeData>) {
  const { item, origin } = data
  return (
    <div
      className={`w-60 rounded-lg bg-card p-3 text-left shadow-sm ${
        origin ? 'border-2 border-primary' : 'border border-border'
      }`}
    >
      <Handle type="target" position={Position.Left} className="!bg-muted-foreground" />
      <div className="flex items-center justify-between gap-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
        <span>{origin ? 'Origin' : item.mutation_type || 'Unknown mutation'}</span>
        <span>{item.language || 'Unknown language'}</span>
      </div>
      <p className="mt-2 line-clamp-3 text-xs font-medium leading-relaxed text-foreground">
        {item.text || item.label}
      </p>
      <div className="mt-2 flex flex-wrap gap-x-2 gap-y-1 text-[10px] text-muted-foreground">
        <span>{item.platform || 'Platform unknown'}</span>
        <span>{item.ts ? new Date(item.ts).toLocaleString() : 'Time not recorded'}</span>
      </div>
      <Handle type="source" position={Position.Right} className="!bg-muted-foreground" />
    </div>
  )
}

const nodeTypes = { variant: VariantNode }

export function layoutMutationTree(tree: ClaimTree) {
  const unique = new Map(tree.nodes.map((node) => [node.id, node]))
  const items = [...unique.values()].sort(compareNodes).slice(0, 80)
  const ids = new Set(items.map((item) => item.id))
  const edgeKeys = new Set<string>()
  const validEdges = tree.edges
    .filter((edge) => {
      const key = `${edge.source}:${edge.target}`
      if (
        edge.source === edge.target ||
        !ids.has(edge.source) ||
        !ids.has(edge.target) ||
        edgeKeys.has(key)
      ) {
        return false
      }
      edgeKeys.add(key)
      return true
    })
    .sort((a, b) => a.target.localeCompare(b.target) || a.source.localeCompare(b.source))
  const parent = new Map<string, string>()
  validEdges.forEach((edge) => {
    if (!parent.has(edge.target)) parent.set(edge.target, edge.source)
  })
  const byId = new Map(items.map((item) => [item.id, item]))
  const neighbors = new Map(items.map((item) => [item.id, new Set<string>()]))
  validEdges.forEach((edge) => {
    neighbors.get(edge.source)?.add(edge.target)
    neighbors.get(edge.target)?.add(edge.source)
  })
  const visited = new Set<string>()
  const roots: TreeNode[] = []
  items.forEach((item) => {
    if (visited.has(item.id)) return
    const pending = [item.id]
    const component: TreeNode[] = []
    while (pending.length) {
      const id = pending.pop()!
      if (visited.has(id)) continue
      visited.add(id)
      const node = byId.get(id)
      if (node) component.push(node)
      neighbors.get(id)?.forEach((neighbor) => pending.push(neighbor))
    }
    const detected = component.filter((node) => !parent.has(node.id)).sort(compareNodes)
    if (detected.length) {
      roots.push(...detected)
    } else if (component.length) {
      const fallback = component.sort(compareNodes)[0]
      parent.delete(fallback.id)
      roots.push(fallback)
    }
  })
  const rootIds = new Set(roots.map((item) => item.id))
  const memo = new Map<string, number>()
  const depth = (id: string, path = new Set<string>()): number => {
    if (memo.has(id)) return memo.get(id)!
    if (path.has(id)) return 0
    const parentId = parent.get(id)
    if (!parentId || !ids.has(parentId)) {
      memo.set(id, 0)
      return 0
    }
    const nextPath = new Set(path)
    nextPath.add(id)
    const value = Math.min(items.length, depth(parentId, nextPath) + 1)
    memo.set(id, value)
    return value
  }
  const ordered = [...items].sort((a, b) => {
    const depthDifference = depth(a.id) - depth(b.id)
    if (depthDifference) return depthDifference
    const parentDifference = (parent.get(a.id) || '').localeCompare(parent.get(b.id) || '')
    return parentDifference || compareNodes(a, b)
  })
  const rows = new Map<number, number>()
  const nodes: Node<VariantNodeData>[] = ordered.map((item) => {
    const column = depth(item.id)
    const row = rows.get(column) || 0
    rows.set(column, row + 1)
    return {
      id: item.id,
      type: 'variant',
      position: { x: column * 300, y: row * 170 },
      data: { item, origin: rootIds.has(item.id) },
    }
  })
  const edges: Edge[] = validEdges
    .filter((edge) => parent.get(edge.target) === edge.source)
    .map((edge) => ({
      id: `${edge.source}-${edge.target}`,
      ...edge,
      markerEnd: { type: MarkerType.ArrowClosed },
    }))
  return { nodes, edges, roots, truncated: unique.size > items.length }
}

export function MutationExplorer({ tree }: { tree: ClaimTree }) {
  const flow = useMemo(() => layoutMutationTree(tree), [tree])
  const [selected, setSelected] = useState<TreeNode | null>(null)
  const mutationTypes = useMemo(
    () =>
      [...new Set(tree.nodes.map((node) => node.mutation_type || 'Unknown'))].sort((a, b) =>
        a.localeCompare(b)
      ),
    [tree.nodes]
  )
  return (
    <section className="rounded-lg border border-border bg-card p-5">
      <div>
        <h2 className="text-lg font-semibold">Mutation explorer</h2>
        <p className="mt-1 text-sm text-muted-foreground">
          Read left to right from each detected origin. Arrows show inferred parent-to-child
          relationships, not proof of direct transmission.
        </p>
      </div>
      <div className="mt-4 flex flex-wrap gap-3 text-xs text-muted-foreground">
        <span>Origins: {flow.roots.length || 'Unknown'}</span>
        <span>Observed variants shown: {flow.nodes.length}</span>
        <span>
          {flow.truncated ? 'Limited to the earliest 80 variants' : 'Complete recorded tree'}
        </span>
      </div>
      <div className="mt-2 flex flex-wrap gap-2 text-xs" aria-label="Mutation type legend">
        {mutationTypes.map((type) => (
          <span key={type} className="rounded bg-muted px-2 py-1 text-muted-foreground">
            {type}
          </span>
        ))}
      </div>
      {flow.nodes.length === 0 ? (
        <p className="py-10 text-center text-sm text-muted-foreground">No mutations recorded.</p>
      ) : (
        <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,2fr)_minmax(240px,1fr)]">
          <div className="h-[28rem] rounded-md border border-border">
            <ReactFlow
              nodes={flow.nodes}
              edges={flow.edges}
              nodeTypes={nodeTypes}
              fitView
              onNodeClick={(_, node) =>
                setSelected(tree.nodes.find((item) => item.id === node.id) || null)
              }
            >
              <Background />
              <Controls />
            </ReactFlow>
          </div>
          <VariantInspector variant={selected} />
        </div>
      )}
      {flow.nodes.length > 0 && (
        <table className="sr-only">
          <caption>Mutation lineage text alternative</caption>
          <thead>
            <tr>
              <th>Variant</th>
              <th>Origin</th>
              <th>Platform</th>
              <th>Observed</th>
            </tr>
          </thead>
          <tbody>
            {flow.nodes.map((node) => (
              <tr key={node.id}>
                <td>{node.data.item.text || node.data.item.label}</td>
                <td>{node.data.origin ? 'Yes' : 'No'}</td>
                <td>{node.data.item.platform || 'Unknown'}</td>
                <td>{node.data.item.ts || 'Not recorded'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}
