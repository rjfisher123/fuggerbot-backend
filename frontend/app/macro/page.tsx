"use client"

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Globe, TrendingUp, Zap, Newspaper, BarChart } from "lucide-react";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";

interface NewsItem {
    title: string;
    source: string;
    category: string;
}

interface MacroData {
    regime: string;
    name: string;
    risk_on: boolean;
    vibe_score: number;
    timestamp: string;
}

interface MacroResponse {
    regime: MacroData;
    news: NewsItem[];
}

export default function MacroPage() {
    const [data, setData] = useState<MacroResponse | null>(null);
    const [loading, setLoading] = useState(false);

    const fetchData = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/macro/');
            const json = await res.json();
            setData(json);
        } catch (e) {
            console.error(e);
        }
        setLoading(false);
    };

    const handleRefresh = async () => {
        await fetch('/api/macro/refresh', { method: 'POST' });
        fetchData();
    };

    useEffect(() => {
        fetchData();
    }, []);

    const macro = data?.regime;
    const news = data?.news || [];

    return (
        <div className="p-8 space-y-8">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Macro Control Room</h1>
                    <p className="text-muted-foreground mt-2">
                        Global market regime analysis and context tracking.
                    </p>
                </div>
                <Button variant="outline" onClick={handleRefresh} disabled={loading}>
                    <Zap className={`mr-2 h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
                    Force Refresh
                </Button>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
                <Card className="col-span-2">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Globe className="h-5 w-5 text-blue-500" />
                            Active Regime
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            <div>
                                <h2 className="text-4xl font-extrabold tracking-tight">
                                    {macro?.regime || "LOADING..."}
                                </h2>
                                <p className="text-xl text-muted-foreground mt-1">
                                    {macro?.name}
                                </p>
                            </div>
                            <div className="flex gap-3">
                                <div className={`px-3 py-1 rounded-full text-sm font-bold ${macro?.risk_on
                                    ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
                                    : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300"
                                    }`}>
                                    {macro?.risk_on ? "RISK ON ✅" : "RISK OFF 🛑"}
                                </div>
                                <div className="px-3 py-1 rounded-full bg-slate-100 dark:bg-slate-800 text-sm font-medium">
                                    Vibe Score: {macro?.vibe_score.toFixed(2)}
                                </div>
                            </div>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <TrendingUp className="h-5 w-5 text-purple-500" />
                            Market Volatility
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="text-center py-6">
                            <div className="text-5xl font-bold text-slate-700 dark:text-slate-200">
                                14.2
                            </div>
                            <p className="text-muted-foreground mt-2">VIX Index (Delayed)</p>
                        </div>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-4 md:grid-cols-2">
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Newspaper className="h-5 w-5" />
                            Top Headlines
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <ul className="space-y-4">
                            {news.length === 0 ? (
                                <li className="text-muted-foreground">No recent headlines.</li>
                            ) : (
                                news.map((item, i) => (
                                    <li key={i} className="flex justify-between items-start border-b last:border-0 pb-2">
                                        <div className="flex flex-col">
                                            <span className="text-sm font-medium">{item.title}</span>
                                            <span className="text-xs text-muted-foreground">{item.source}</span>
                                        </div>
                                        <Badge variant={item.source === 'IBKR' ? "default" : "secondary"}>
                                            {item.source}
                                        </Badge>
                                    </li>
                                ))
                            )}
                        </ul>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <BarChart className="h-5 w-5" />
                            Asset Parameters
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <Table>
                            <TableHeader>
                                <TableRow>
                                    <TableHead>Asset</TableHead>
                                    <TableHead>Trust Threshold</TableHead>
                                    <TableHead>Min Conf</TableHead>
                                </TableRow>
                            </TableHeader>
                            <TableBody>
                                <TableRow>
                                    <TableCell className="font-medium">BTC-USD</TableCell>
                                    <TableCell>0.65</TableCell>
                                    <TableCell>0.75</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell className="font-medium">ETH-USD</TableCell>
                                    <TableCell>0.65</TableCell>
                                    <TableCell>0.75</TableCell>
                                </TableRow>
                                <TableRow>
                                    <TableCell className="font-medium">NVDA</TableCell>
                                    <TableCell>0.70</TableCell>
                                    <TableCell>0.80</TableCell>
                                </TableRow>
                            </TableBody>
                        </Table>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
