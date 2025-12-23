"use client"

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, BrainCircuit, Globe, Zap } from "lucide-react";
import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from "@/components/ui/table";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

interface MacroData {
    regime: string;
    name: string;
    risk_on: boolean;
    vibe_score: number;
    timestamp: string;
    source: string;
}

interface HallucinationItem {
    entry_date?: string;
    symbol?: string;
    outcome?: string;
    pnl?: number;
    meta?: {
        reason?: string;
        delusion?: boolean;
    };
    decision?: string;
}

export default function DiagnosticsPage() {
    const [macro, setMacro] = useState<MacroData | null>(null);
    const [hallucinations, setHallucinations] = useState<HallucinationItem[]>([]);

    useEffect(() => {
        // Fetch Macro Data
        fetch('/api/diagnostics/macro')
            .then(res => res.json())
            .then(data => setMacro(data))
            .catch(err => console.error("Macro fetch error", err));

        // Fetch Hallucinations
        fetch('/api/diagnostics/hallucinations')
            .then(res => res.json())
            .then(data => {
                if (data.items) setHallucinations(data.items);
            })
            .catch(err => console.error("Diagnostics fetch error", err));
    }, []);

    return (
        <div className="p-8 space-y-8">
            <div>
                <h1 className="text-3xl font-bold tracking-tight">System Diagnostics</h1>
                <p className="text-muted-foreground mt-2">
                    Inspect internal state, agent memory, and macroeconomic context.
                </p>
            </div>

            {/* Macro Regime Section */}
            <div className="grid gap-4 md:grid-cols-2">
                <Card className="border-l-4 border-blue-500">
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Current Macro Regime
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-baseline space-x-3">
                            <span className="text-3xl font-bold">
                                {macro?.regime || "LOADING..."}
                            </span>
                            <span className="text-sm text-muted-foreground">
                                {macro?.name}
                            </span>
                        </div>
                        <div className="mt-4 flex gap-2">
                            {macro?.risk_on ? (
                                <Badge className="bg-green-600">Risk On</Badge>
                            ) : (
                                <Badge variant="destructive">Risk Off</Badge>
                            )}
                            <Badge variant="outline">
                                Vibe: {macro?.vibe_score.toFixed(2)}
                            </Badge>
                            <Badge variant="secondary">
                                Source: {macro?.source}
                            </Badge>
                        </div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Agent Health
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-sm">Delusions Detected</span>
                                <span className="font-bold text-red-500">{hallucinations.length}</span>
                            </div>
                            <div className="flex items-center justify-between">
                                <span className="text-sm">Macro Tracker Status</span>
                                <span className="font-bold text-green-500">Active</span>
                            </div>
                        </div>
                    </CardContent>
                </Card>
            </div>

            {/* Hallucination Log */}
            <Card>
                <CardHeader>
                    <div className="flex items-center gap-2">
                        <BrainCircuit className="h-5 w-5 text-purple-500" />
                        <CardTitle>Hallucination Log</CardTitle>
                    </div>
                    <CardDescription>
                        Instances where the model experienced delusions or hallucinations during simulation.
                    </CardDescription>
                </CardHeader>
                <CardContent>
                    <Table>
                        <TableHeader>
                            <TableRow>
                                <TableHead>Date</TableHead>
                                <TableHead>Symbol</TableHead>
                                <TableHead>Type</TableHead>
                                <TableHead>Outcome</TableHead>
                                <TableHead>Meta / Reason</TableHead>
                            </TableRow>
                        </TableHeader>
                        <TableBody>
                            {hallucinations.length === 0 ? (
                                <TableRow>
                                    <TableCell colSpan={5} className="text-center h-24 text-muted-foreground">
                                        No hallucinations detected in recent memory. System is stable.
                                    </TableCell>
                                </TableRow>
                            ) : (
                                hallucinations.map((h, i) => (
                                    <TableRow key={i}>
                                        <TableCell>{h.entry_date || "N/A"}</TableCell>
                                        <TableCell className="font-bold">{h.symbol || "Unknown"}</TableCell>
                                        <TableCell>
                                            <Badge variant="outline" className="text-purple-500 border-purple-500">
                                                DELUSION
                                            </Badge>
                                        </TableCell>
                                        <TableCell>
                                            <span className={h.pnl && h.pnl > 0 ? "text-green-500" : "text-red-500"}>
                                                {h.outcome} {h.pnl ? `($${h.pnl.toFixed(0)})` : ""}
                                            </span>
                                        </TableCell>
                                        <TableCell className="text-sm text-muted-foreground max-w-md truncate">
                                            {h.meta?.reason || JSON.stringify(h.meta)}
                                        </TableCell>
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
