import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { Activity, Radio, AlertCircle, RefreshCw } from 'lucide-react';

interface IBKRStatus {
    connected: boolean;
    host?: string;
    port?: number;
    paper_trading?: boolean;
    client_id?: number;
    error?: string;
}

const IBKRStatusCard: React.FC = () => {
    const [status, setStatus] = useState<IBKRStatus | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [connecting, setConnecting] = useState<boolean>(false);
    const [error, setError] = useState<string | null>(null);

    const fetchStatus = async () => {
        try {
            const response = await fetch('/api/ibkr/status');
            if (!response.ok) throw new Error('Failed to fetch status');
            const data = await response.json();
            setStatus(data);
            setError(null);
        } catch (err) {
            console.error('Error fetching IBKR status:', err);
            // Don't set global error to avoid flashing, just keep old status or null
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchStatus();
        const interval = setInterval(fetchStatus, 3000);
        return () => clearInterval(interval);
    }, []);

    const [manualPort, setManualPort] = useState<string>("7497");

    const handleConnect = async () => {
        setConnecting(true);
        setError(null);
        try {
            const response = await fetch('/api/ibkr/connect', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ port: parseInt(manualPort) })
            });
            const data = await response.json();

            if (!data.success) {
                throw new Error(data.message || 'Connection failed');
            }

            // Refresh status immediately
            fetchStatus();
        } catch (err: any) {
            setError(err.message || 'Failed to connect');
        } finally {
            setConnecting(false);
        }
    };

    const getStatusBadge = () => {
        if (loading && !status) return <Badge variant="outline">Loading...</Badge>;
        if (status?.connected) {
            return (
                <Badge variant="success" className="bg-green-500 hover:bg-green-600">
                    <Radio className="w-3 h-3 mr-1 animate-pulse" />
                    Connected ({status.paper_trading ? 'Paper' : 'Live'})
                </Badge>
            );
        }
        if (connecting) {
            return (
                <Badge variant="warning" className="bg-yellow-500 hover:bg-yellow-600">
                    <RefreshCw className="w-3 h-3 mr-1 animate-spin" />
                    Connecting...
                </Badge>
            );
        }
        return (
            <Badge variant="destructive" className="bg-red-500 hover:bg-red-600">
                <AlertCircle className="w-3 h-3 mr-1" />
                Disconnected
            </Badge>
        );
    };

    return (
        <Card className="w-full max-w-md shadow-lg">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">IBKR Gateway</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
                <div className="flex flex-col gap-4">
                    <div className="flex items-center justify-between">
                        <span className="text-2xl font-bold">
                            {status?.port ? `Port ${status.port}` : 'No Connection'}
                        </span>
                        {getStatusBadge()}
                    </div>

                    <p className="text-xs text-muted-foreground">
                        {status?.connected
                            ? `Client ID: ${status.client_id} • Host: ${status.host || 'localhost'}`
                            : 'Gateway connection required for trading execution.'}
                    </p>

                    {error && (
                        <Alert variant="destructive">
                            <AlertCircle className="h-4 w-4" />
                            <AlertTitle>Error</AlertTitle>
                            <AlertDescription>{error}</AlertDescription>
                        </Alert>
                    )}

                    {!status?.connected && !loading && (
                        <div className="space-y-4">
                            <div className="rounded-md bg-muted p-3 text-xs">
                                <p className="font-semibold mb-2">Instructions:</p>
                                <ol className="list-decimal list-inside space-y-1 text-muted-foreground">
                                    <li>Start TWS or IB Gateway application</li>
                                    <li>Enable API (File &gt; Settings &gt; API)</li>
                                    <li>Uncheck &quot;Read-Only API&quot;</li>
                                    <li>Verify Socket Port below matches TWS</li>
                                </ol>
                            </div>

                            <div className="flex items-center gap-4">
                                <div className="grid gap-1.5 flex-1">
                                    <label className="text-xs font-medium text-muted-foreground">Socket Port</label>
                                    <input
                                        type="number"
                                        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                                        value={manualPort}
                                        onChange={(e) => setManualPort(e.target.value)}
                                        placeholder="7497"
                                    />
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            </CardContent>
            <CardFooter>
                <Button
                    className="w-full"
                    onClick={handleConnect}
                    disabled={status?.connected || connecting}
                    variant={status?.connected ? "secondary" : "default"}
                >
                    {connecting ? 'Connecting...' : status?.connected ? 'Connected' : 'Connect to IBKR'}
                </Button>
            </CardFooter>
        </Card>
    );
};

export default IBKRStatusCard;
