"use client"

import React, { useEffect, useState } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Badge } from "@/components/ui/badge";
import { Loader2, CheckCircle, XCircle } from "lucide-react";

interface Job {
    id: string;
    type: string;
    status: "PENDING" | "RUNNING" | "COMPLETED" | "FAILED";
    progress: number;
    message: string;
    result?: any;
    updated_at: number;
}

interface JobMonitorProps {
    jobId: string | null;
    onComplete?: (result: any) => void;
}

export function JobMonitor({ jobId, onComplete }: JobMonitorProps) {
    const [job, setJob] = useState<Job | null>(null);
    const [polling, setPolling] = useState(false);

    useEffect(() => {
        if (!jobId) return;

        setPolling(true);
        const interval = setInterval(async () => {
            try {
                const res = await fetch(`/api/simulation/status/${jobId}`);
                if (res.ok) {
                    const data = await res.json();
                    setJob(data);

                    if (data.status === "COMPLETED" || data.status === "FAILED") {
                        clearInterval(interval);
                        setPolling(false);
                        if (data.status === "COMPLETED" && onComplete) {
                            onComplete(data.result);
                        }
                    }
                }
            } catch (e) {
                console.error("Job poll failed", e);
            }
        }, 1000);

        return () => clearInterval(interval);
    }, [jobId]);

    if (!job && !jobId) return null;
    if (!job) return <div className="text-sm text-muted-foreground animate-pulse">Initializing monitor...</div>;

    const isRunning = job.status === "RUNNING" || job.status === "PENDING";
    const isFailed = job.status === "FAILED";
    const isSuccess = job.status === "COMPLETED";

    return (
        <Card className="mb-4 border-l-4 border-l-blue-500 shadow-sm">
            <CardContent className="pt-4 pb-4 flex items-center gap-4">
                <div className="flex-1 space-y-2">
                    <div className="flex justify-between items-center mb-1">
                        <span className="font-semibold text-sm flex items-center gap-2">
                            {isRunning && <Loader2 className="h-4 w-4 animate-spin text-blue-500" />}
                            {isSuccess && <CheckCircle className="h-4 w-4 text-green-500" />}
                            {isFailed && <XCircle className="h-4 w-4 text-red-500" />}
                            {job.type.toUpperCase()} JOB
                        </span>
                        <Badge variant={isSuccess ? "outline" : (isFailed ? "destructive" : "secondary")}>
                            {job.status}
                        </Badge>
                    </div>

                    <Progress value={job.progress} className="h-2" />

                    <p className="text-xs text-muted-foreground font-mono truncate">
                        {job.message}
                    </p>
                </div>
            </CardContent>
        </Card>
    );
}
