"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { CheckCircle2, XCircle, RefreshCw, Clock } from "lucide-react"

// Types
interface TradeRequest {
    trade_id: string
    symbol: string
    action: string
    quantity: number
    order_type: string
    limit_price: number | null
    approval_code: string | null
    status: string
    created_at: string | null
    expires_at: string | null
    paper_trading: boolean
}

export default function TradesPage() {
    const [pending, setPending] = useState<TradeRequest[]>([])
    const [history, setHistory] = useState<TradeRequest[]>([])
    const [loading, setLoading] = useState(true)

    const fetchData = async () => {
        setLoading(true)
        try {
            const [pendingRes, historyRes] = await Promise.all([
                fetch("http://127.0.0.1:8000/api/trades/pending"),
                fetch("http://127.0.0.1:8000/api/trades/history")
            ])

            if (pendingRes.ok) setPending(await pendingRes.json())
            if (historyRes.ok) setHistory(await historyRes.json())
        } catch (error) {
            console.error("Failed to fetch trades:", error)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        fetchData()
        const interval = setInterval(fetchData, 10000)
        return () => clearInterval(interval)
    }, [])

    const handleAction = async (tradeId: string, action: "approve" | "reject", code?: string) => {
        try {
            const endpoint = action === "approve" ? "/api/trades/approve" : "/api/trades/reject"
            const body = action === "approve"
                ? { trade_id: tradeId, approval_code: code || tradeId }
                : { trade_id: tradeId }

            const res = await fetch(`http://127.0.0.1:8000${endpoint}`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(body)
            })

            if (res.ok) {
                // Optimistic update
                setPending(prev => prev.filter(t => t.trade_id !== tradeId && t.approval_code !== tradeId))
                fetchData() // Refresh to get updated history
            } else {
                alert("Action failed")
            }
        } catch (e) {
            console.error(e)
            alert("Error performing action")
        }
    }

    return (
        <div className="p-8 space-y-8">
            <div className="flex justify-between items-center">
                <h2 className="text-3xl font-bold tracking-tight text-white">Trade Management</h2>
                <Button onClick={fetchData} variant="outline" size="sm" className="gap-2">
                    <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                    Refresh
                </Button>
            </div>

            {/* Pending Approvals */}
            <Card className="bg-zinc-900 border-zinc-800 text-white border-l-4 border-l-amber-500">
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <Clock className="h-5 w-5 text-amber-500" />
                        <CardTitle>Pending Approvals</CardTitle>
                    </div>
                    <CardDescription className="text-zinc-400">
                        Trades waiting for your confirmation.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    {pending.length > 0 ? (
                        <div className="space-y-4">
                            {pending.map((trade) => (
                                <div key={trade.trade_id} className="flex items-center justify-between p-4 rounded-lg bg-zinc-950 border border-zinc-800">
                                    <div className="flex items-center gap-4">
                                        <div className={`text-lg font-bold ${trade.action === "BUY" ? "text-emerald-500" : "text-rose-500"}`}>
                                            {trade.action}
                                        </div>
                                        <div>
                                            <div className="font-bold text-white text-xl">{trade.quantity} x {trade.symbol}</div>
                                            <div className="text-sm text-zinc-500">
                                                {trade.order_type}
                                                {trade.limit_price ? ` @ $${trade.limit_price}` : ""} •
                                                Code: <span className="font-mono text-zinc-300">{trade.approval_code || trade.trade_id}</span>
                                            </div>
                                        </div>
                                    </div>
                                    <div className="flex gap-2">
                                        <Button
                                            variant="destructive"
                                            onClick={() => handleAction(trade.trade_id, "reject")}
                                            className="gap-2"
                                        >
                                            <XCircle className="h-4 w-4" /> Reject
                                        </Button>
                                        <Button
                                            className="bg-emerald-600 hover:bg-emerald-700 gap-2"
                                            onClick={() => handleAction(trade.trade_id, "approve", trade.approval_code || undefined)}
                                        >
                                            <CheckCircle2 className="h-4 w-4" /> Approve
                                        </Button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="text-center py-12 text-zinc-500">
                            No pending trades. You're all caught up!
                        </div>
                    )}
                </CardContent>
            </Card>

            {/* Trade History */}
            <Card className="bg-zinc-900 border-zinc-800 text-white">
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <CardTitle>Trade History</CardTitle>
                    </div>
                </CardHeader>
                <CardContent>
                    {history.length > 0 ? (
                        <div className="relative overflow-x-auto">
                            <table className="w-full text-sm text-left rtl:text-right text-zinc-400">
                                <thead className="text-xs text-zinc-500 uppercase bg-zinc-950/50">
                                    <tr>
                                        <th className="px-6 py-3">Time</th>
                                        <th className="px-6 py-3">Symbol</th>
                                        <th className="px-6 py-3">Action</th>
                                        <th className="px-6 py-3">Qty</th>
                                        <th className="px-6 py-3">Status</th>
                                        <th className="px-6 py-3">ID</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {history.map((trade) => (
                                        <tr key={trade.trade_id} className="bg-zinc-900 border-b border-zinc-800 hover:bg-zinc-800/50">
                                            <td className="px-6 py-4">{trade.created_at ? new Date(trade.created_at).toLocaleString() : "-"}</td>
                                            <td className="px-6 py-4 font-medium text-white">{trade.symbol}</td>
                                            <td className={`px-6 py-4 font-bold ${trade.action === "BUY" ? "text-emerald-500" : "text-rose-500"}`}>
                                                {trade.action}
                                            </td>
                                            <td className="px-6 py-4">{trade.quantity}</td>
                                            <td className="px-6 py-4">
                                                <Badge variant={trade.status === "filled" || trade.status === "submitted" ? "default" : "secondary"}
                                                    className={
                                                        trade.status === "pending" ? "bg-amber-500/20 text-amber-500" :
                                                            trade.status === "rejected" ? "bg-rose-500/20 text-rose-500" :
                                                                "bg-emerald-500/20 text-emerald-500"
                                                    }>
                                                    {trade.status}
                                                </Badge>
                                            </td>
                                            <td className="px-6 py-4 font-mono text-xs">{trade.trade_id}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="text-center py-8 text-zinc-500">History is empty.</div>
                    )}
                </CardContent>
            </Card>
        </div>
    )
}
