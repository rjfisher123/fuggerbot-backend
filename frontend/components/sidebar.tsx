"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { cn } from "@/lib/utils"
import {
    LayoutDashboard,
    LineChart,
    History,
    Activity,
    Settings,
    PlugZap,
    BookOpen,
    Zap
} from "lucide-react"

const routes = [
    {
        label: "Status",
        icon: PlugZap,
        href: "/",
        color: "text-sky-500",
    },
    {
        label: "Portfolio",
        icon: LayoutDashboard,
        href: "/dashboard",
        color: "text-emerald-500",
    },
    {
        label: "Trades",
        icon: History,
        href: "/trades",
        color: "text-violet-500",
    },
    {
        label: "Forecasts",
        icon: LineChart,
        href: "/forecasts",
        color: "text-pink-700",
    },
    {
        label: "Execute",
        icon: Zap,
        href: "/trade",
        color: "text-yellow-500",
    },
    {
        label: "War Games",
        icon: Activity,
        href: "/wargames",
        color: "text-orange-700",
    },
    {
        label: "Macro",
        icon: BookOpen,
        href: "/macro",
        color: "text-blue-700",
    },
    {
        label: "Diagnostics",
        icon: Settings,
        href: "/diagnostics",
        color: "text-gray-500",
    },
]

export function Sidebar() {
    const pathname = usePathname()

    return (
        <div className="space-y-4 py-4 flex flex-col h-full bg-[#111827] text-white">
            <div className="px-3 py-2 flex-1">
                <Link href="/" className="flex items-center pl-3 mb-14">
                    <Activity className="h-8 w-8 mr-4 text-emerald-500" />
                    <span className="text-2xl font-bold bg-gradient-to-r from-emerald-400 to-cyan-500 bg-clip-text text-transparent">
                        FuggerBot
                    </span>
                </Link>
                <div className="space-y-1">
                    {routes.map((route) => (
                        <Link
                            key={route.href}
                            href={route.href}
                            className={cn(
                                "text-sm group flex p-3 w-full justify-start font-medium cursor-pointer hover:text-white hover:bg-white/10 rounded-lg transition",
                                pathname === route.href ? "text-white bg-white/10" : "text-zinc-400"
                            )}
                        >
                            <div className="flex items-center flex-1">
                                <route.icon className={cn("h-5 w-5 mr-3", route.color)} />
                                {route.label}
                            </div>
                        </Link>
                    ))}
                </div>
            </div>
            <div className="px-3 py-2">
                {/* Footer or version info */}
                <div className="text-xs text-zinc-500 text-center">
                    v2.0.0 (Async Core)
                </div>
            </div>
        </div>
    )
}
