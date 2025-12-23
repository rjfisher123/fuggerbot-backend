"use client"

import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
    Zap, Lock, Unlock, Activity, AlertTriangle,
    ArrowUpCircle, ArrowDownCircle, RefreshCw
} from "lucide-react";

interface TradeStatus {
    connected: boolean;
    account_id: string;
    mode: string;
    port: number;
}

export default function TradePage() {
    const [status, setStatus] = useState<TradeStatus>({
        connected: false, account_id: '...', mode: 'UNKNOWN', port: 0
    });
    const [liveEnabled, setLiveEnabled] = useState(false);

    // Form State
    const [symbol, setSymbol] = useState("");
    const [quantity, setQuantity] = useState("1");
    const [action, setAction] = useState<"BUY" | "SELL">("BUY");
    const [orderType, setOrderType] = useState<"MARKET" | "LIMIT">("MARKET");
    const [price, setPrice] = useState("");

    const [loading, setLoading] = useState(false);
    const [orderLog, setOrderLog] = useState<any[]>([]);

    useEffect(() => {
        fetchStatus();
        fetchSettings();
    }, []);

    const fetchStatus = async () => {
        try {
            const res = await fetch('/api/trade/status');
            const data = await res.json();
            setStatus(data);
        } catch (e) {
            console.error("Status fetch failed", e);
        }
    };

    const fetchSettings = async () => {
        try {
            const res = await fetch('/api/settings');
            const data = await res.json();
            setLiveEnabled(data.live_trading_enabled);
        } catch (e) {
            console.error("Settings fetch failed", e);
        }
    };

    const toggleLiveTrading = async () => {
        const newState = !liveEnabled;
        // Require confirmation to enable
        if (newState && !confirm("⚠️ DANGER: Enabling LIVE execution will allow real orders to be placed. Are you sure?")) {
            return;
        }

        try {
            const res = await fetch('/api/settings/toggle_trading', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ enabled: newState })
            });
            const data = await res.json();
            setLiveEnabled(data.live_trading_enabled);
            fetchStatus(); // Update mode status
        } catch (e) {
            console.error("Toggle failed", e);
        }
    };

    const executeTrade = async () => {
        if (!symbol) return;
        setLoading(true);
        try {
            const payload = {
                symbol: symbol.toUpperCase(),
                action,
                quantity: parseFloat(quantity),
                order_type: orderType,
                price: price ? parseFloat(price) : undefined
            };

            const res = await fetch('/api/trade/execute', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            const data = await res.json();

            if (res.ok) {
                // Add to log
                setOrderLog(prev => [{
                    timestamp: new Date().toLocaleTimeString(),
                    ...payload,
                    status: 'SUBMITTED',
                    id: data.order_id
                }, ...prev]);
                alert(`✅ Order Submitted: ${data.message}`);
            } else {
                alert(`❌ Execution Failed: ${data.detail}`);
            }

        } catch (e) {
            console.error("Execution error", e);
            alert("Execution error (check console)");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="p-8 space-y-8 max-w-5xl mx-auto">
            <div className="flex justify-between items-center">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
                        Trade Command Center
                        {liveEnabled ? (
                            <Badge variant="destructive" className="animate-pulse">LIVE EXECUTION ON</Badge>
                        ) : (
                            <Badge variant="outline" className="bg-slate-100 text-slate-500">SIMULATION / PAPER</Badge>
                        )}
                    </h1>
                    <p className="text-muted-foreground mt-2">
                        Manual execution gateway and safety controls.
                    </p>
                </div>
            </div>

            {/* Status & Safety Switch */}
            <div className="grid gap-6 md:grid-cols-2">
                <Card className={status.connected ? "border-green-500/50" : "border-red-500/50"}>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground flex justify-between">
                            Gateway Status
                            <RefreshCw className="h-4 w-4 cursor-pointer hover:spin" onClick={fetchStatus} />
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="flex items-center gap-3 mb-2">
                            <div className={`h-3 w-3 rounded-full ${status.connected ? "bg-green-500" : "bg-red-500"}`} />
                            <span className="text-2xl font-bold">
                                {status.connected ? "CONNECTED" : "DISCONNECTED"}
                            </span>
                        </div>
                        <div className="text-xs text-muted-foreground font-mono">
                            ID: {status.account_id} | Port: {status.port} | Mode: {status.mode}
                        </div>
                    </CardContent>
                </Card>

                <Card className={liveEnabled ? "bg-red-950/10 border-red-500/30" : ""}>
                    <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium text-muted-foreground">
                            Master Safety Switch
                        </CardTitle>
                    </CardHeader>
                    <CardContent className="flex justify-between items-center">
                        <div className="space-y-1">
                            <div className="font-medium">Live Execution</div>
                            <div className="text-xs text-muted-foreground">
                                {liveEnabled
                                    ? "⚠️ REAL ORDERS will be sent to broker."
                                    : "🔒 Orders blocked / Paper only."}
                            </div>
                        </div>
                        <Button
                            variant={liveEnabled ? "destructive" : "outline"}
                            onClick={toggleLiveTrading}
                            className="w-32"
                        >
                            {liveEnabled ? (
                                <><Unlock className="mr-2 h-4 w-4" /> ARMED</>
                            ) : (
                                <><Lock className="mr-2 h-4 w-4" /> SAFE</>
                            )}
                        </Button>
                    </CardContent>
                </Card>
            </div>

            <div className="grid gap-6 md:grid-cols-3">
                {/* Manual Order Form */}
                <Card className="col-span-2">
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Zap className="h-5 w-5 text-yellow-500" />
                            Manual Entry
                        </CardTitle>
                        <CardDescription>Execute a single order immediately.</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-6">
                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Symbol</Label>
                                <Input
                                    placeholder="e.g. NVDA"
                                    value={symbol}
                                    onChange={e => setSymbol(e.target.value.toUpperCase())}
                                    className="font-mono uppercase text-lg"
                                />
                            </div>
                            <div className="space-y-2">
                                <Label>Quantity</Label>
                                <Input
                                    type="number"
                                    value={quantity}
                                    onChange={e => setQuantity(e.target.value)}
                                />
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4">
                            <div className="space-y-2">
                                <Label>Action</Label>
                                <div className="flex gap-2">
                                    <Button
                                        className="flex-1"
                                        variant={action === "BUY" ? "default" : "outline"}
                                        onClick={() => setAction("BUY")}
                                    >
                                        BUY
                                    </Button>
                                    <Button
                                        className="flex-1"
                                        variant={action === "SELL" ? "destructive" : "outline"} // Shadcn doesn't strictly have red variant except destructive
                                        onClick={() => setAction("SELL")}
                                    >
                                        SELL
                                    </Button>
                                </div>
                            </div>
                            <div className="space-y-2">
                                <Label>Order Type</Label>
                                <div className="flex gap-2">
                                    <Button
                                        className="flex-1"
                                        variant={orderType === "MARKET" ? "secondary" : "ghost"}
                                        onClick={() => setOrderType("MARKET")}
                                    >
                                        MKT
                                    </Button>
                                    <Button
                                        className="flex-1"
                                        variant={orderType === "LIMIT" ? "secondary" : "ghost"}
                                        onClick={() => setOrderType("LIMIT")}
                                    >
                                        LMT
                                    </Button>
                                </div>
                            </div>
                        </div>

                        {orderType === "LIMIT" && (
                            <div className="space-y-2 animate-in fade-in slide-in-from-top-2">
                                <Label>Limit Price ($)</Label>
                                <Input
                                    type="number"
                                    placeholder="0.00"
                                    value={price}
                                    onChange={e => setPrice(e.target.value)}
                                />
                            </div>
                        )}

                        <div className="pt-4">
                            <Button
                                className={`w-full h-12 text-lg font-bold ${action === 'BUY'
                                        ? 'bg-green-600 hover:bg-green-700'
                                        : 'bg-red-600 hover:bg-red-700'
                                    }`}
                                onClick={executeTrade}
                                disabled={loading || !symbol}
                            >
                                {loading ? "SENDING..." : (
                                    <>
                                        {action === 'BUY' ? <ArrowUpCircle className="mr-2" /> : <ArrowDownCircle className="mr-2" />}
                                        {action} {quantity} {symbol || '...'}
                                    </>
                                )}
                            </Button>
                            {liveEnabled && (
                                <p className="text-center text-xs text-red-500 mt-2 font-bold">
                                    ⚠️ LIVE ORDER - REAL MONEY AT RISK
                                </p>
                            )}
                        </div>
                    </CardContent>
                </Card>

                {/* Recent Activity Log (Local Session) */}
                <Card>
                    <CardHeader>
                        <CardTitle className="flex items-center gap-2">
                            <Activity className="h-5 w-5" />
                            Session Log
                        </CardTitle>
                    </CardHeader>
                    <CardContent>
                        <div className="space-y-4">
                            {orderLog.length === 0 && (
                                <div className="text-center text-muted-foreground py-8 text-sm">
                                    No orders placed this session.
                                </div>
                            )}
                            {orderLog.map((order, i) => (
                                <div key={i} className="flex justify-between items-center border-b pb-2 last:border-0">
                                    <div>
                                        <div className="font-bold text-sm">
                                            {order.action} {order.quantity} {order.symbol}
                                        </div>
                                        <div className="text-xs text-muted-foreground">{order.timestamp}</div>
                                    </div>
                                    <Badge variant={order.status === 'SUBMITTED' ? 'outline' : 'secondary'}>
                                        {order.status}
                                    </Badge>
                                </div>
                            ))}
                        </div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
