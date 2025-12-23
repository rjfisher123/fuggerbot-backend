"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Activity, DollarSign, TrendingUp, TrendingDown, ArrowUpRight, ArrowDownRight } from "lucide-react"

// Types matching Backend Pydantic Models
interface Position {
    symbol: string
    entry_price: number
    current_price: number
    shares: number
    position_value: number
    unrealized_pnl: number
    unrealized_pnl_pct: number
    entry_date: string | null
}

interface PortfolioSummary {
    initial_capital: number
    total_capital: number
    total_return_pct: number
    total_realized_pnl: number
    total_realized_pnl_pct: number
    win_rate: number
    closed_trades: number
    open_positions: Position[]
    trade_history: any[]
    last_updated: string
}

export default function DashboardPage() {
    const [summary, setSummary] = useState<PortfolioSummary | null>(null)
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const fetchPortfolio = async () => {
        try {
            const res = await fetch("http://127.0.0.1:8000/api/portfolio/summary")
            if (!res.ok) throw new Error("Failed to fetch portfolio")
            const data = await res.json()
            setSummary(data)
            setError(null)
        } catch (err) {
            console.error(err)
            setError("Failed to load portfolio data. Is the backend running?")
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchPortfolio()
        const interval = setInterval(fetchPortfolio, 5000) // Refresh every 5s
        return () => clearInterval(interval)
    }, [])

    if (loading && !summary) {
        return <div className="p-8 text-zinc-400">Loading portfolio data...</div>
    }

    if (error && !summary) {
        return <div className="p-8 text-red-500">{error}</div>
    }

    return (
        <div className="p-8 space-y-8">
            <h2 className="text-3xl font-bold tracking-tight text-white">Portfolio Overview</h2>

            {/* Key Metrics Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                <Card className="bg-zinc-900 border-zinc-800 text-white">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-zinc-400">Total Equity</CardTitle>
                        <DollarSign className="h-4 w-4 text-emerald-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            ${summary?.total_capital ? summary.total_capital.toLocaleString(undefined, { minimumFractionDigits: 2 }) : "0.00"}
                        </div>
                        <p className="text-xs text-zinc-500">
                            Initial: ${summary?.initial_capital.toLocaleString()}
                        </p>
                    </CardContent>
                </Card>

                <Card className="bg-zinc-900 border-zinc-800 text-white">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-zinc-400">Total PnL</CardTitle>
                        {summary?.total_realized_pnl && summary.total_realized_pnl >= 0 ? (
                            <TrendingUp className="h-4 w-4 text-emerald-500" />
                        ) : (
                            <TrendingDown className="h-4 w-4 text-rose-500" />
                        )}
                    </CardHeader>
                    <CardContent>
                        <div className={`text-2xl font-bold ${summary?.total_realized_pnl && summary.total_realized_pnl >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                            {summary?.total_realized_pnl && summary.total_realized_pnl >= 0 ? "+" : ""}
                            ${summary?.total_realized_pnl.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                        </div>
                        <p className="text-xs text-zinc-500">
                            {summary?.total_realized_pnl_pct.toFixed(2)}% Return
                        </p>
                    </CardContent>
                </Card>

                <Card className="bg-zinc-900 border-zinc-800 text-white">
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium text-zinc-400">Win Rate</CardTitle>
                        <Activity className="h-4 w-4 text-blue-500" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {summary?.win_rate.toFixed(1)}%
                        </div>
                        <p className="text-xs text-zinc-500">
                            {summary?.closed_trades} Closed Trades
                        </p>
                    </CardContent>
                </Card>
            </div>

            {/* Positions Table */}
            <Card className="bg-zinc-900 border-zinc-800 text-white col-span-4">
                <CardHeader>
                    <CardTitle>Open Positions</CardTitle>
                </CardHeader>
                <CardContent>
                    {summary?.open_positions && summary.open_positions.length > 0 ? (
                        <div className="relative overflow-x-auto">
                            <table className="w-full text-sm text-left rtl:text-right text-zinc-400">
                                <thead className="text-xs text-zinc-500 uppercase bg-zinc-950/50">
                                    <tr>
                                        <th scope="col" className="px-6 py-3">Symbol</th>
                                        <th scope="col" className="px-6 py-3">Shares</th>
                                        <th scope="col" className="px-6 py-3">Avg Cost</th>
                                        <th scope="col" className="px-6 py-3">Price</th>
                                        <th scope="col" className="px-6 py-3">Value</th>
                                        <th scope="col" className="px-6 py-3">Unrealized PnL</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {summary.open_positions.map((pos) => (
                                        <tr key={pos.symbol} className="bg-zinc-900 border-b border-zinc-800 hover:bg-zinc-800/50">
                                            <td className="px-6 py-4 font-medium text-white">{pos.symbol}</td>
                                            <td className="px-6 py-4">{pos.shares}</td>
                                            <td className="px-6 py-4">${pos.entry_price.toFixed(2)}</td>
                                            <td className="px-6 py-4">${pos.current_price.toFixed(2)}</td>
                                            <td className="px-6 py-4">${pos.position_value.toLocaleString(undefined, { minimumFractionDigits: 2 })}</td>
                                            <td className={`px-6 py-4 ${pos.unrealized_pnl >= 0 ? "text-emerald-500" : "text-rose-500"}`}>
                                                {pos.unrealized_pnl >= 0 ? "+" : ""}
                                                ${pos.unrealized_pnl.toFixed(2)}
                                                <span className="text-xs ml-1 opacity-70">({pos.unrealized_pnl_pct.toFixed(2)}%)</span>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="text-center py-8 text-zinc-500">
                            No open positions. Use the Trades tab to place orders.
                        </div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
