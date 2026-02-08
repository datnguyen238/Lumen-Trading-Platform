"use client"

import * as React from "react"
import {
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  Legend as RechartsLegend,
} from "recharts"

import { cn } from "@/lib/utils"

export type ChartConfig = Record<
  string,
  {
    label?: string
    color?: string
  }
>

type ChartContainerProps = React.ComponentProps<"div"> & {
  config: ChartConfig
}

export function ChartContainer({ config, className, children, ...props }: ChartContainerProps) {
  const style = Object.fromEntries(
    Object.entries(config).map(([key, value]) => [
      `--color-${key}`,
      value.color ?? "currentColor",
    ])
  ) as React.CSSProperties

  return (
    <div
      data-chart
      className={cn(
        "flex h-[250px] w-full items-center justify-center text-xs",
        className
      )}
      style={style}
      {...props}
    >
      <ResponsiveContainer>{children}</ResponsiveContainer>
    </div>
  )
}

export function ChartTooltip(props: React.ComponentProps<typeof RechartsTooltip>) {
  return <RechartsTooltip {...props} />
}

export function ChartLegend(props: React.ComponentProps<typeof RechartsLegend>) {
  return <RechartsLegend {...props} />
}

type ChartTooltipContentProps = React.HTMLAttributes<HTMLDivElement> & {
  labelFormatter?: (label: string) => React.ReactNode
  nameKey?: string
}

export function ChartTooltipContent({
  active,
  payload,
  label,
  className,
  labelFormatter,
  nameKey,
}: ChartTooltipContentProps) {
  if (!active || !payload?.length) return null

  return (
    <div
      className={cn(
        "rounded-md border bg-background px-2.5 py-1.5 text-xs shadow-md",
        className
      )}
    >
      <div className="mb-1 text-muted-foreground">
        {labelFormatter ? labelFormatter(String(label)) : label}
      </div>
      <div className="space-y-1">
        {payload.map((item) => {
          const key = nameKey ?? (item.dataKey as string)
          const name = (item.payload && (item.payload[key] as string)) || item.name || item.dataKey
          return (
            <div key={String(item.dataKey)} className="flex items-center gap-2">
              <span
                className="h-2 w-2 rounded-sm"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-muted-foreground">{name}</span>
              <span className="font-medium tabular-nums">
                {formatNumber(item.value as number)}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function formatNumber(value: number) {
  if (!Number.isFinite(value)) return "—"
  return value.toLocaleString(undefined, { maximumFractionDigits: 2 })
}
