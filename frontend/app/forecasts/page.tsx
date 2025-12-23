"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Wand2, AlertCircle } from "lucide-react"

export default function ForecastPage() {
    const [symbol, setSymbol] = useState("")
    const [horizon, setHorizon] = useState(30)
    const [loading, setLoading] = useState(false)
    const [result, setResult] = useState<any>(null)
    const [error, setError] = useState<string | null>(null)

    const handleGenerate = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!symbol) return

        setLoading(true)
        setError(null)
        setResult(null)

        try {
            const res = await fetch("http://127.0.0.1:8000/api/forecast/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    symbol: symbol,
                    forecast_horizon: horizon
                })
            })

            if (!res.ok) {
                const errData = await res.json()
                throw new Error(errData.detail || "Failed to generate forecast")
            }

            const data = await res.json()
            setResult(data)
        } catch (err: any) {
            setError(err.message)
        } finally {
            setLoading(false)
        }
    }

    return (
        <div className="p-8 space-y-8 max-w-5xl mx-auto">
            <h2 className="text-3xl font-bold tracking-tight text-white">Generate Forecast</h2>

            <Card className="bg-zinc-900 border-zinc-800 text-white">
                <CardHeader>
                    <CardTitle>Configuration</CardTitle>
                    <CardDescription className="text-zinc-400">
                        Enter a ticker symbol to generate an AI-powered market forecast.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <form onSubmit={handleGenerate} className="flex gap-4 items-end">
                        <div className="grid w-full max-w-sm items-center gap-1.5">
                            <Label htmlFor="symbol">Symbol</Label>
                            <Input
                                id="symbol"
                                placeholder="AAPL"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                className="bg-zinc-950 border-zinc-700 text-white"
                            />
                        </div>
                        <div className="grid w-full max-w-xs items-center gap-1.5">
                            <Label htmlFor="horizon">Horizon (Days)</Label>
                            <Input
                                id="horizon"
                                type="number"
                                value={horizon}
                                onChange={(e) => setHorizon(Number(e.target.value))}
                                className="bg-zinc-950 border-zinc-700 text-white"
                                min={1}
                                max={90}
                            />
                        </div>
                        <Button disabled={loading || !symbol} type="submit" className="bg-purple-600 hover:bg-purple-700 w-40">
                            {loading ? (
                                "Analyzing..."
                            ) : (
                                <>
                                    <Wand2 className="mr-2 h-4 w-4" /> Generate
                                </>
                            )}
                        </Button>
                    </form>
                    {error && (
                        <div className="mt-4 p-4 bg-rose-900/20 border border-rose-800 rounded text-rose-300 flex items-center gap-2">
                            <AlertCircle className="h-4 w-4" /> {error}
                        </div>
                    )}
                </CardContent>
            </Card>

            {result && (
                <div className="grid gap-6 md:grid-cols-2">
                    <Card className="bg-zinc-900 border-zinc-800 text-white md:col-span-2">
                        <CardHeader>
                            <div className="flex justify-between items-center">
                                <CardTitle className="text-2xl">{result.symbol} Forecast</CardTitle>
                                <Badge variant="outline" className="text-zinc-400 border-zinc-700">
                                    Trust Score: {(result.trust_score * 100).toFixed(0)}%
                                </Badge>
                            </div>
                        </CardHeader>
                        <CardContent className="space-y-6">
                            {/* Recommendation */}
                            <div className="flex gap-4">
                                <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 flex-1 text-center">
                                    <div className="text-sm text-zinc-500 mb-1">Direction</div>
                                    <div className="text-xl font-bold text-white">
                                        {result.recommendation?.direction || "NEUTRAL"}
                                    </div>
                                </div>
                                <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 flex-1 text-center">
                                    <div className="text-sm text-zinc-500 mb-1">Confidence</div>
                                    <div className="text-xl font-bold text-emerald-400">
                                        {result.recommendation?.confidence ? (result.recommendation.confidence * 100).toFixed(1) : 0}%
                                    </div>
                                </div>
                                <div className="p-4 rounded-lg bg-zinc-950 border border-zinc-800 flex-1 text-center">
                                    <div className="text-sm text-zinc-500 mb-1">Risk Level</div>
                                    <div className="text-xl font-bold text-amber-400">
                                        {result.metadata?.risk_level || "MEDIUM"}
                                    </div>
                                </div>
                            </div>

                            {/* Raw JSON Details */}
                            <div className="space-y-2">
                                <Label>Technical Details</Label>
                                <pre className="bg-black/50 p-4 rounded-lg overflow-x-auto text-xs text-green-400">
                                    {JSON.stringify(result, null, 2)}
                                </pre>
                            </div>
                        </CardContent>
                    </Card>
                </div>
            )}
        </div>
    )
}
