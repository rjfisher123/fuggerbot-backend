"use client";

import { useState, useEffect } from "react";
import Link from "next/link";

interface ReportMetadata {
  report_id: string;
  generated_at: string;
  strategy_version: string;
  research_loop_version: string;
  data_fingerprint: string;
  scenario_count: number;
  insight_count: number;
  simulator_commit_hash: string;
  markdown_path?: string;
  meta_path?: string;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<ReportMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReport, setSelectedReport] = useState<ReportMetadata | null>(null);
  const [reportContent, setReportContent] = useState<string>("");
  const [loadingContent, setLoadingContent] = useState(false);

  useEffect(() => {
    fetchReports();
  }, []);

  const fetchReports = async () => {
    try {
      setLoading(true);
      setError(null);
      
      // Use relative path to API (works with Next.js proxy or direct backend)
      const apiUrl = "/api/reports/";
      console.debug("[Reports] Fetching from", apiUrl);
      
      const response = await fetch(apiUrl, {
        cache: "no-store",
      });
      
      if (!response.ok) {
        const errorDetail = `HTTP ${response.status}: ${response.statusText}`;
        console.error("[Reports] Fetch failed:", errorDetail, "Endpoint:", apiUrl);
        throw new Error(`Failed to fetch reports: ${errorDetail}`);
      }
      
      const data = await response.json();
      setReports(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load reports");
      console.error("Error fetching reports:", err);
    } finally {
      setLoading(false);
    }
  };

  const fetchReportContent = async (reportId: string) => {
    try {
      setLoadingContent(true);
      const apiUrl = `/api/reports/${reportId}?format=markdown`;
      console.debug("[Reports] Fetching content from", apiUrl);
      
      const response = await fetch(apiUrl, {
        cache: "no-store",
      });
      
      if (!response.ok) {
        const errorDetail = `HTTP ${response.status}: ${response.statusText}`;
        console.error("[Reports] Content fetch failed:", errorDetail, "Endpoint:", apiUrl);
        throw new Error(`Failed to fetch report content: ${errorDetail}`);
      }
      
      const content = await response.text();
      setReportContent(content);
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : "Unknown error";
      const attemptedUrl = `/api/reports/${reportId}?format=markdown`;
      console.error("[Reports] Error fetching report content:", err);
      console.error("[Reports] Endpoint attempted:", attemptedUrl);
      setReportContent(`Error loading report: ${errorMsg}`);
    } finally {
      setLoadingContent(false);
    }
  };

  const handleReportClick = (report: ReportMetadata) => {
    setSelectedReport(report);
    fetchReportContent(report.report_id);
  };

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "Unknown";
    try {
      const date = new Date(dateStr);
      return date.toLocaleString();
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Research Reports</h1>
          <p className="text-gray-600">
            View and analyze deterministic research reports. All reports are read-only artifacts.
          </p>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            <div className="font-semibold mb-2">Failed to fetch reports</div>
            <div className="text-sm mb-2">{error}</div>
            <div className="text-xs text-gray-600 mb-2">
              <div>Endpoint: /api/reports/</div>
              <div className="mt-1">Suggested actions:</div>
              <ul className="list-disc list-inside ml-2 mt-1">
                <li>Check API server is running (http://localhost:8000)</li>
                <li>Verify /api/reports endpoint is accessible</li>
                <li>Check browser console for detailed error</li>
              </ul>
            </div>
            <button
              onClick={fetchReports}
              className="mt-2 px-3 py-1 bg-red-600 text-white rounded hover:bg-red-700 text-sm"
            >
              Retry
            </button>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Reports List */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">Available Reports</h2>
              <p className="text-sm text-gray-500 mt-1">
                {reports.length} report{reports.length !== 1 ? "s" : ""} found
              </p>
            </div>

            {loading ? (
              <div className="p-8 text-center text-gray-500">Loading reports...</div>
            ) : reports.length === 0 && !error ? (
              <div className="p-8 text-center text-gray-500">
                <p className="mb-2">No reports found.</p>
                <p className="text-sm mb-4">Generate a report using the CLI:</p>
                <code className="block mt-2 p-2 bg-gray-100 rounded text-sm font-mono">
                  python -m agents.research.report --output reports/my_report.md
                </code>
              </div>
            ) : reports.length > 0 ? (
              <div className="divide-y divide-gray-200 max-h-[600px] overflow-y-auto">
                {reports.map((report) => (
                  <div
                    key={report.report_id}
                    onClick={() => handleReportClick(report)}
                    className={`p-4 cursor-pointer hover:bg-gray-50 transition-colors ${
                      selectedReport?.report_id === report.report_id
                        ? "bg-blue-50 border-l-4 border-blue-500"
                        : ""
                    }`}
                  >
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <h3 className="font-semibold text-gray-900">
                          {report.report_id}
                        </h3>
                        <p className="text-sm text-gray-500 mt-1">
                          {formatDate(report.generated_at)}
                        </p>
                        <div className="flex gap-4 mt-2 text-xs text-gray-600">
                          <span>{report.scenario_count} scenarios</span>
                          <span>{report.insight_count} insights</span>
                          <span>v{report.strategy_version}</span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
          </div>

          {/* Report Detail */}
          <div className="bg-white rounded-lg shadow-sm border border-gray-200">
            <div className="p-4 border-b border-gray-200">
              <h2 className="text-xl font-semibold">
                {selectedReport ? selectedReport.report_id : "Select a Report"}
              </h2>
              {selectedReport && (
                <div className="mt-2 text-sm text-gray-600">
                  <div>Generated: {formatDate(selectedReport.generated_at)}</div>
                  <div className="mt-1">
                    Fingerprint: <code className="text-xs">{selectedReport.data_fingerprint}</code>
                  </div>
                </div>
              )}
            </div>

            <div className="p-4">
              {!selectedReport ? (
                <div className="text-center text-gray-500 py-12">
                  Select a report from the list to view its contents
                </div>
              ) : loadingContent ? (
                <div className="text-center text-gray-500 py-12">Loading report content...</div>
              ) : (
                <div className="prose max-w-none">
                  <pre className="whitespace-pre-wrap font-mono text-sm bg-gray-50 p-4 rounded border overflow-x-auto">
                    {reportContent}
                  </pre>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Navigation */}
        <div className="mt-8 text-center">
          <Link
            href="/"
            className="text-blue-600 hover:text-blue-800 underline"
          >
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    </div>
  );
}

