import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { cn } from '@/lib/utils'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
    title: 'FuggerBot Dashboard',
    description: 'AI-Powered Asymmetric Investment Automation',
}

import { Sidebar } from '@/components/sidebar'

export default function RootLayout({
    children,
}: {
    children: React.ReactNode
}) {
    return (
        <html lang="en">
            <body className={cn(inter.className, "min-h-screen bg-background font-sans antialiased")}>
                <div className="h-full relative flex flex-row">
                    <div className="hidden h-full md:flex md:w-72 md:flex-col md:fixed md:inset-y-0 z-80">
                        <Sidebar />
                    </div>
                    <main className="md:pl-72 pb-10 flex-1 min-h-screen">
                        {children}
                    </main>
                </div>
            </body>
        </html>
    )
}
