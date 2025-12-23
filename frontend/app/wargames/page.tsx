"use client"

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Play, TrendingUp, AlertTriangle, Activity, BarChart2 } from "lucide-react";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { JobMonitor } from "@/components/JobMonitor";

interface CampaignResult {
    campaign_name: string;
    symbol: string;
    total_return_pct: number;
    win_rate: number;
    max_drawdown_pct: number;
    sharpe_ratio: number;
    total_trades: number;
    scenario_description?: string;
}

export default function WarGamesPage() {
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState<CampaignResult[]>([]);
    const [jobId, setJobId] = useState<string | null>(null);
    const [lastRun, setLastRun] = useState<string | null>(null);

    const fetchResults = async () => {
        try {
            const res = await fetch('/api/simulation/results');
            const data = await res.json();
            if (data.results) {
                setResults(data.results);
                setLastRun(data.run_timestamp);
            }
        } catch (error) {
            console.error("Failed to fetch simulation results:", error);
        }
    };

    useEffect(() => {
        fetchResults();
    }, []);

    const runSimulation = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/simulation/run', { method: 'POST' });
            const data = await res.json();
            if (data.job_id) {
                setJobId(data.job_id);
            }
        } catch (error) {
            console.error("Failed to start simulation:", error);
            alert("Failed to start simulation.");
            setLoading(false);
        }
        // Note: Loading state is managed by JobMonitor existence or own logic
    };

    const onJobComplete = () => {
        setLoading(false);
        setJobId(null);
        fetchResults();
        alert("✅ Simulation Complete!");
    };

    const runOptimizer = async () => {
        try {
            await fetch('/api/optimizer/run', { method: 'POST' });
            alert("Optimizer started in background!");
        } catch (error) {
            console.error("Failed to start optimizer:", error);
        }
    };

    return (
        <div className="p-8 space-y-8">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">War Games</h1>
                    <p className="text-muted-foreground mt-2">
                        Stress-test strategies against historical scenarios.
                        {lastRun && <span className="ml-2 text-xs bg-muted px-2 py-1 rounded">Last Run: {new Date(lastRun).toLocaleString()}</span>}
                    </p>
                </div>
                <div className="flex gap-2">
                    <Button variant="outline" onClick={runOptimizer}>
                        <Activity className="mr-2 h-4 w-4" />
                        Run Optimizer
                    </Button>
                    <Button variant="destructive" onClick={async () => {
                        if (confirm("Reset simulation state?")) {
                            await fetch('/api/simulation/reset', { method: 'POST' });
                            setJobId(null);
                            setLoading(false);
                            alert("Reset complete.");
                        }
                    }}>
                        Reset
                    </Button>
                    <Button onClick={runSimulation} disabled={loading} className={loading ? "animate-pulse" : ""}>
                        <Play className="mr-2 h-4 w-4" />
                        {loading ? "Simulating..." : "Run Simulation"}
                    </Button>
                </div>
            </div>

            <JobMonitor jobId={jobId} onComplete={onJobComplete} />

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Total Campaigns</CardTitle>
                        <BarChart2 className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{results.length}</div>
                        <p className="text-xs text-muted-foreground">
                            Scenarios tested
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Avg Return</CardTitle>
                        <TrendingUp className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {results.length > 0
                                ? (results.reduce((acc, r) => acc + r.total_return_pct, 0) / results.length).toFixed(1)
                                : 0}%
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Across all scenarios
                        </p>
                    </CardContent>
                </Card>
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">Risk Flag</CardTitle>
                        <AlertTriangle className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">
                            {results.filter(r => r.max_drawdown_pct > 20).length}
                        </div>
                        <p className="text-xs text-muted-foreground">
                            Strategies with &gt;20% DD
                        </p>
                    </CardContent>
                </Card>
            </div>

            <Card>
                <CardHeader>
                    <CardTitle>Campaign Leaderboard</CardTitle>
                    <CardDescription>
                        Performance metrics by scenario and symbol.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Campaign</TableHead>
                                <TableHead>Symbol</TableHead>
                                <TableHead className="text-right">Return</TableHead>
                                <TableHead className="text-right">Win Rate</TableHead>
                                <TableHead className="text-right">Max DD</TableHead>
                                <TableHead className="text-right">Sharpe</TableHead>
                                <TableHead className="text-right">Trades</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {results.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={7} className="text-center h-24 text-muted-foreground">
                                        No simulation results found. Click "Run Simulation" to start.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                results.map((r, i) => (
                                    <TableRow key={i}>
                                        <TableCell className="font-medium">
                                            {r.campaign_name}
                                            <div className="text-xs text-muted-foreground">{r.scenario_description}</div>
                                        </TableCell>
                                        <TableCell>
                                            <Badge variant="outline">{r.symbol}</Badge>
                                        </TableCell>
                                        <TableCell className={`text-right ${r.total_return_pct >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                            {r.total_return_pct.toFixed(1)}%
                                        </TableCell>
                                        <TableCell className="text-right">{(r.win_rate * 100).toFixed(1)}%</TableCell>
                                        <TableCell className="text-right text-red-500">-{r.max_drawdown_pct.toFixed(1)}%</TableCell>
                                        <TableCell className="text-right">{r.sharpe_ratio.toFixed(2)}</TableCell>
                                        <TableCell className="text-right">{r.total_trades}</TableCell>
                                    </TableRow>
                                ))
                            )}
                        </TableBody>
                    </Table>
                </CardContent>
            </Card>
        </div>
    );
}
