'use client'

import { useEffect, useState } from 'react'
import dynamic from 'next/dynamic'
import type { PlotParams } from 'react-plotly.js'

// Use a typed dynamic import
const Plot = dynamic(
  () => import('react-plotly.js').then((mod) => mod.default),
  {
    ssr: false,
    loading: () => (
      <div className="h-48 flex items-center justify-center text-muted-foreground text-sm">
        Loading chart...
      </div>
    ),
  }
) as React.ComponentType<PlotParams>

interface Props {
  chartJson: string
}

interface PlotlyFigure {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  data: any[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  layout: any
}

export function ChartRenderer({ chartJson }: Props) {
  const [figure, setFigure] = useState<PlotlyFigure | null>(null)

  useEffect(() => {
    try {
      const parsed = JSON.parse(chartJson)
      setFigure(parsed)
    } catch {
      console.error('Failed to parse chart JSON')
    }
  }, [chartJson])

  if (!figure) return null

  return (
    <Plot
      data={figure.data}
      layout={{
        ...figure.layout,
        paper_bgcolor: 'transparent',
        plot_bgcolor: 'transparent',
        font: { color: '#94a3b8', size: 11 },
        margin: { t: 20, r: 10, b: 40, l: 40 },
        xaxis: { ...figure.layout?.xaxis, gridcolor: '#1e293b', zerolinecolor: '#1e293b' },
        yaxis: { ...figure.layout?.yaxis, gridcolor: '#1e293b', zerolinecolor: '#1e293b' },
        autosize: true,
      }}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%', minHeight: 250 }}
      useResizeHandler
    />
  )
}
