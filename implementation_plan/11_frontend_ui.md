# Phase 11: Frontend UI (research-agent-front)

## Architecture Context

The frontend (`src/frontend/`) is React + TypeScript + Vite + Material UI (dark theme,
purple `#7c5cff` accent). It talks to `src/backend/` via `services/api.ts` using axios.
All new UI is **additive** — no existing pages or components are modified beyond adding
new navigation entries and a new sidebar section.

Graph visualization library: **`react-force-graph-2d`** (lightweight, canvas-based,
works well with MUI dark theme). Install:
```bash
npm install react-force-graph-2d
npm install --save-dev @types/react-force-graph-2d
```

---

## 1. New Types (`src/frontend/src/types/index.ts`)

Add to the existing types file:

```typescript
export interface GraphNode {
  id: string;
  label: string;
  type: 'paper' | 'concept' | 'method' | 'finding' | 'author' | 'institution';
  properties: Record<string, any>;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  weight: number;
  properties: Record<string, any>;
}

export interface KnowledgeGraph {
  id: string;
  seed_paper_id?: string;
  title: string;
  node_count: number;
  edge_count: number;
  nodes: GraphNode[];
  edges: GraphEdge[];
  metadata: Record<string, any>;
  created_at: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  user_id: number;
}

export interface GraphRequest {
  seed_paper_url?: string;
  seed_paper_id?: string;
  depth?: number;       // 1 or 2
  max_papers?: number;  // 1-100
}

export interface GraphListItem {
  id: string;
  title: string;
  seed_paper_id?: string;
  node_count: number;
  edge_count: number;
  created_at: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}
```

---

## 2. New API Methods (`src/frontend/src/services/api.ts`)

Add to the existing `api.ts`:

```typescript
// ── Knowledge Graph endpoints ────────────────────────────────────────────────

export const createGraph = async (request: GraphRequest): Promise<KnowledgeGraph> => {
  const response = await api.post('/graphs', request);
  return response.data;
};

export const getGraphs = async (): Promise<GraphListItem[]> => {
  const response = await api.get('/graphs');
  return response.data;
};

export const getGraph = async (graphId: string): Promise<KnowledgeGraph> => {
  const response = await api.get(`/graphs/${graphId}`);
  return response.data;
};

export const deleteGraph = async (graphId: string): Promise<void> => {
  await api.delete(`/graphs/${graphId}`);
};

export const downloadGraph = async (graphId: string): Promise<Blob> => {
  const response = await api.get(`/graphs/${graphId}/export`, { responseType: 'blob' });
  return response.data;
};
```

---

## 3. New Page: `GraphsPage.tsx`

**`src/frontend/src/pages/GraphsPage.tsx`**

This is the main graphs page, structured similarly to `DashboardPage` — sidebar list on
the left, main content on the right.

```tsx
import React, { useState, useEffect } from 'react';
import { Box, AppBar, Toolbar, Stack, Button, Typography, IconButton, Avatar, Menu, MenuItem } from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import LogoutIcon from '@mui/icons-material/Logout';
import MenuBookIcon from '@mui/icons-material/MenuBook';
import { useAuth } from '../contexts/AuthContext';
import { useResponsive } from '@/hooks';
import Logo from '../components/Logo';
import GraphSidebar from '../components/graph/GraphSidebar';
import GraphViewer from '../components/graph/GraphViewer';
import GraphWelcome from '../components/graph/GraphWelcome';
import { KnowledgeGraph, GraphListItem } from '../types';
import * as api from '../services/api';

const SIDEBAR_WIDTH = 360;

const GraphsPage: React.FC = () => {
  const { user, logout } = useAuth();
  const [graphs, setGraphs] = useState<GraphListItem[]>([]);
  const [selectedGraph, setSelectedGraph] = useState<KnowledgeGraph | null>(null);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const { isLargeDesktop } = useResponsive();

  useEffect(() => { loadGraphs(); }, []);

  const loadGraphs = async () => {
    try {
      const data = await api.getGraphs();
      setGraphs(data);
    } catch (e) {
      console.error('Failed to load graphs:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleNewGraph = async (request: GraphRequest) => {
    const graph = await api.createGraph(request);
    setGraphs(prev => [graph, ...prev]);
    setSelectedGraph(graph);
    return graph;
  };

  const handleGraphSelect = async (item: GraphListItem) => {
    const full = await api.getGraph(item.id);
    setSelectedGraph(full);
  };

  const handleGraphDelete = async (graphId: string) => {
    await api.deleteGraph(graphId);
    setGraphs(prev => prev.filter(g => g.id !== graphId));
    if (selectedGraph?.id === graphId) setSelectedGraph(null);
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column', gap: 2, p: 2 }}>
      {/* AppBar — same style as DashboardPage */}
      <Box sx={{ flexShrink: 0 }}>
        <AppBar position="static" sx={{ background: 'rgba(33,33,33,0.95)', backdropFilter: 'blur(10px)', borderRadius: 2 }}>
          <Toolbar sx={{ flex: 1, gap: 2 }}>
            <Stack direction="row" gap={1} flex={1} alignItems="center">
              {!isLargeDesktop && (
                <IconButton onClick={() => setSidebarOpen(true)} sx={{ p: 1 }}>
                  <MenuIcon />
                </IconButton>
              )}
              <Box sx={{ flexGrow: 1, display: 'flex', alignItems: 'center' }}>
                <Logo sx={{ maxWidth: '100%' }} height={32} />
              </Box>
              <Button component="a" href="/" startIcon={<ScienceIcon />}
                sx={{ color: 'white', textTransform: 'none', fontSize: '0.875rem' }}>
                Research
              </Button>
              <Button component="a" href="/manual" startIcon={<MenuBookIcon />}
                sx={{ color: 'white', textTransform: 'none', fontSize: '0.875rem' }}>
                Manual
              </Button>
            </Stack>
            <Stack direction="row" alignItems="center" gap={1}>
              <Typography variant="body2" sx={{ color: 'white', display: { xs: 'none', sm: 'block' } }}>
                {user?.first_name || 'User'}
              </Typography>
              <IconButton onClick={(e) => setAnchorEl(e.currentTarget)} sx={{ p: 1 }}>
                <Avatar src={user?.photo_url} sx={{ width: 32, height: 32 }}>
                  {user?.first_name?.[0]}
                </Avatar>
              </IconButton>
            </Stack>
            <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={() => setAnchorEl(null)}>
              <MenuItem onClick={() => { setAnchorEl(null); logout(); }}>
                <LogoutIcon sx={{ mr: 1 }} /> Logout
              </MenuItem>
            </Menu>
          </Toolbar>
        </AppBar>
      </Box>

      <Stack flex={1} sx={{ flexDirection: 'row', minHeight: 0, overflow: 'hidden' }}>
        <GraphSidebar
          isOpen={sidebarOpen}
          onClose={() => setSidebarOpen(false)}
          graphs={graphs}
          selectedGraph={selectedGraph}
          onGraphSelect={handleGraphSelect}
          onGraphDelete={handleGraphDelete}
          onNewGraph={() => setSelectedGraph(null)}
          loading={loading}
          width={SIDEBAR_WIDTH}
        />
        <Box component="main" sx={{ flexGrow: 1, display: 'flex', flexDirection: 'column' }}>
          {selectedGraph
            ? <GraphViewer graph={selectedGraph} />
            : <GraphWelcome onNewGraph={handleNewGraph} />
          }
        </Box>
      </Stack>
    </Box>
  );
};

export default GraphsPage;
```

---

## 4. New Component: `GraphWelcome.tsx`

**`src/frontend/src/components/graph/GraphWelcome.tsx`**

Mirrors `WelcomeScreen.tsx` but for graph generation. Has a URL/DOI input, depth selector,
and example seed papers.

```tsx
// Key UI elements:
// - Title: "Build a Knowledge Graph"
// - Subtitle: "Enter a paper URL or DOI to generate a semantic knowledge graph of related research"
// - TextField: placeholder "https://elifesciences.org/articles/93796 or DOI:10.xxx"
// - ToggleButtonGroup: depth 1 (Fast, ~30 papers) vs depth 2 (Deep, ~100 papers)
// - Submit Button: "Generate Graph"
// - Example chips: the two Wyss Institute papers + 2-3 others
// - Loading state with LinearProgress and "Building graph... this takes 1-2 minutes"

interface GraphWelcomeProps {
  onNewGraph: (request: GraphRequest) => Promise<KnowledgeGraph>;
}
```

---

## 5. New Component: `GraphViewer.tsx`

**`src/frontend/src/components/graph/GraphViewer.tsx`**

The main graph visualization component using `react-force-graph-2d`.

```tsx
import ForceGraph2D from 'react-force-graph-2d';

// Node color by type:
const NODE_COLORS: Record<string, string> = {
  paper:       '#7c5cff',  // purple — primary brand color
  concept:     '#10a37f',  // green
  method:      '#f59e0b',  // amber
  finding:     '#ef4444',  // red
  author:      '#3b82f6',  // blue
  institution: '#8b5cf6',  // violet
};

// Features:
// - Header: graph title, node/edge counts, Download JSON button, Share button
// - ForceGraph2D canvas fills remaining height
// - Node tooltip on hover: shows label, type, properties
// - Click node: opens NodeDetailPanel (right drawer) with full properties
// - Edge labels on hover
// - Legend: colored dots for each node type
// - "Processing" overlay if graph.status === 'processing'
```

**NodeDetailPanel** (sub-component, right drawer):
```tsx
// Shows:
// - Node label + type chip
// - All properties as key-value pairs
// - If type === 'paper': DOI link, year, authors list
// - If type === 'finding': full finding text
// - "Find related papers" button → triggers new research with node label as query
```

---

## 6. New Component: `GraphSidebar.tsx`

**`src/frontend/src/components/graph/GraphSidebar.tsx`**

Mirrors `Sidebar.tsx` structure exactly. Shows list of graphs grouped by seed paper.

```tsx
// Each list item shows:
// - Graph title (truncated)
// - Node count + edge count badges
// - Status indicator (same emoji pattern as research sidebar)
// - Created time (formatDistanceToNow)
// - Delete icon on hover

// Top button: "New Graph" (opens GraphWelcome)
// Section label: "Recent Graphs"
```

---

## 7. Route Addition (`src/frontend/src/App.tsx`)

Add the `/graphs` route:

```tsx
import GraphsPage from './pages/GraphsPage';

// Inside <Routes>:
<Route path="/graphs/*" element={user ? <GraphsPage /> : <Navigate to="/login" replace />} />
```

---

## 8. Navigation Link in `DashboardPage.tsx`

Add a "Knowledge Graphs" button to the AppBar next to "User Manual":

```tsx
<Button
  component="a"
  href="/graphs"
  startIcon={<AccountTreeIcon />}  // import from @mui/icons-material
  sx={{ color: 'white', textTransform: 'none', fontSize: '0.875rem', ... }}
>
  Knowledge Graphs
</Button>
```

---

## 9. Graph Status Polling Hook

**`src/frontend/src/hooks/useGraphStatus.ts`**

Mirrors the existing `useResearchStatus` hook pattern:

```typescript
export function useGraphStatus({ graphId, enabled }: { graphId: string | null; enabled: boolean }) {
  const [graph, setGraph] = useState<KnowledgeGraph | null>(null);

  useEffect(() => {
    if (!enabled || !graphId) return;
    const interval = setInterval(async () => {
      const updated = await api.getGraph(graphId);
      setGraph(updated);
      if (updated.status === 'completed' || updated.status === 'failed') {
        clearInterval(interval);
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [graphId, enabled]);

  return { graph };
}
```

Use in `GraphsPage` the same way `useResearchStatus` is used in `DashboardPage`.

---

## 10. Download Helper

In `GraphViewer.tsx`, the "Download JSON" button:

```typescript
const handleDownload = async () => {
  const blob = await api.downloadGraph(graph.id);
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `graph_${graph.id.slice(0, 8)}.json`;
  a.click();
  URL.revokeObjectURL(url);
};
```

---

## 11. Manual Page Update (`ManualPage.tsx`)

Add a new `ManualSection` for Knowledge Graphs after the existing "Advanced features" section:

```tsx
<ManualSection id="graphs" title="Knowledge Graphs">
  <Typography variant="body1" sx={{ mb: 2 }}>
    The Knowledge Graph feature lets you visualize the network of scientific papers,
    concepts, methods, and findings connected to any seed paper.
  </Typography>
  <Box component="ol" sx={{ pl: 3, mb: 2 }}>
    <li>Click <strong>Knowledge Graphs</strong> in the top navigation</li>
    <li>Paste a paper URL (eLife, ACS, PubMed, arXiv) or DOI</li>
    <li>Choose depth: <strong>Fast</strong> (1 hop, ~30 papers) or <strong>Deep</strong> (2 hops, ~100 papers)</li>
    <li>Click <strong>Generate Graph</strong> and wait 1–2 minutes</li>
    <li>Explore the interactive graph — click any node for details</li>
    <li>Download the graph as JSON for use in other tools</li>
  </Box>
  // Add ManualTOC entry: { id: 'graphs', label: 'Knowledge Graphs' }
</ManualSection>
```

Also add `{ id: 'graphs', label: 'Knowledge Graphs' }` to the TOC items in `ManualTOC.tsx`.

---

## File Summary

| File | Action |
|---|---|
| `src/frontend/src/types/index.ts` | Add `GraphNode`, `GraphEdge`, `KnowledgeGraph`, `GraphListItem`, `GraphRequest` |
| `src/frontend/src/services/api.ts` | Add `createGraph`, `getGraphs`, `getGraph`, `deleteGraph`, `downloadGraph` |
| `src/frontend/src/pages/GraphsPage.tsx` | **New** — main graphs page |
| `src/frontend/src/components/graph/GraphWelcome.tsx` | **New** — seed paper input form |
| `src/frontend/src/components/graph/GraphViewer.tsx` | **New** — force-directed graph canvas |
| `src/frontend/src/components/graph/GraphSidebar.tsx` | **New** — graphs list sidebar |
| `src/frontend/src/components/graph/NodeDetailPanel.tsx` | **New** — node detail right drawer |
| `src/frontend/src/hooks/useGraphStatus.ts` | **New** — polling hook for graph build status |
| `src/frontend/src/App.tsx` | Add `/graphs` route |
| `src/frontend/src/pages/DashboardPage.tsx` | Add "Knowledge Graphs" nav button |
| `src/frontend/src/pages/ManualPage.tsx` | Add graphs section |
| `src/frontend/src/components/manual/ManualTOC.tsx` | Add graphs TOC entry |
| `package.json` | Add `react-force-graph-2d` dependency |
