import {
  CandlestickSeries,
  LineStyle,
  createChart,
  type IChartApi,
  type IPriceLine,
  type ISeriesApi,
  type UTCTimestamp,
} from 'lightweight-charts'
import { useEffect, useRef } from 'react'
import type { Candle } from '../types/api'

/** Twelve Data (and this backend) store UTC timestamps as "YYYY-MM-DD
 * HH:MM:SS" for intraday candles or plain "YYYY-MM-DD" for daily/weekly -
 * neither parses reliably as-is across browsers, so normalize to ISO+Z. */
function toUnixSeconds(timestamp: string): UTCTimestamp {
  const iso = /^\d{4}-\d{2}-\d{2}$/.test(timestamp)
    ? `${timestamp}T00:00:00Z`
    : `${timestamp.replace(' ', 'T')}Z`
  return Math.floor(new Date(iso).getTime() / 1000) as UTCTimestamp
}

export function PriceChart({
  candles,
  entry,
  stopLoss,
  takeProfit,
}: {
  candles: Candle[]
  entry?: number | null
  stopLoss?: number | null
  takeProfit?: number | null
}) {
  const containerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)
  const seriesRef = useRef<ISeriesApi<'Candlestick'> | null>(null)
  const priceLinesRef = useRef<IPriceLine[]>([])

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    const chart: IChartApi = createChart(container, {
      autoSize: true,
      layout: { background: { color: 'transparent' }, textColor: '#5b6169' },
      grid: {
        vertLines: { color: '#dcdfd8' },
        horzLines: { color: '#dcdfd8' },
      },
      timeScale: { timeVisible: true, secondsVisible: false },
    })
    const series = chart.addSeries(CandlestickSeries, {
      upColor: '#146c43',
      downColor: '#a63d1f',
      borderVisible: false,
      wickUpColor: '#146c43',
      wickDownColor: '#a63d1f',
    })
    chartRef.current = chart
    seriesRef.current = series

    return () => {
      chart.remove()
      chartRef.current = null
      seriesRef.current = null
    }
  }, [])

  useEffect(() => {
    const series = seriesRef.current
    if (!series || candles.length === 0) return

    const data = candles
      .map((c) => ({
        time: toUnixSeconds(c.timestamp),
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }))
      .sort((a, b) => a.time - b.time)

    series.setData(data)
    chartRef.current?.timeScale().fitContent()
  }, [candles])

  useEffect(() => {
    const series = seriesRef.current
    if (!series) return

    for (const line of priceLinesRef.current) series.removePriceLine(line)
    priceLinesRef.current = []

    const levels: [number | null | undefined, string, string][] = [
      [entry, '#1b3a6b', 'Entry'],
      [stopLoss, '#a63d1f', 'Stop loss'],
      [takeProfit, '#146c43', 'Take profit'],
    ]
    for (const [price, color, title] of levels) {
      if (price == null) continue
      priceLinesRef.current.push(
        series.createPriceLine({
          price,
          color,
          lineWidth: 2,
          lineStyle: LineStyle.Dashed,
          axisLabelVisible: true,
          title,
        }),
      )
    }
  }, [entry, stopLoss, takeProfit])

  return <div ref={containerRef} className="h-80 w-full" />
}
