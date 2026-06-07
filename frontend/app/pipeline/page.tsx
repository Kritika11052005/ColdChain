"use client";

import React, { useEffect, useState, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Terminal as TerminalIcon, Cpu, Loader2, Sparkles, CheckCircle2, ChevronRight, Play } from "lucide-react";
import Link from "next/link";
import ParticlesBackground from "@/components/ParticlesBackground";

interface LogMessage {
  timestamp: string;
  level: string;
  stage: number | null;
  message: string;
}

interface RunStats {
  run_id: string;
  status: string;
  seed_domain: string;
  companies_found: number;
  prospects_found: number;
  contacts_verified: number;
  contacts_scored: number;
  duration_seconds: number | null;
  error_message?: string | null;
}

export default function PipelinePage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const runId = searchParams.get("run_id");

  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [stats, setStats] = useState<RunStats | null>(null);
  const [error, setError] = useState<string | null>(null);
  
  const terminalEndRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  // Poll for stats and check transition status
  useEffect(() => {
    if (!runId) return;

    const fetchStats = async () => {
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/history/${runId}/stats`);
        if (res.ok) {
          const data = await res.json();
          setStats(data);
          
          // If pipeline is in REVIEWING, redirect to the review page
          if (data.status === "REVIEWING") {
            setTimeout(() => {
              router.push(`/review?run_id=${runId}`);
            }, 1500);
          }
        }
      } catch (err) {
        console.error("Error fetching run stats:", err);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 2000);
    return () => clearInterval(interval);
  }, [runId, router]);

  // WebSocket connection for real-time logs
  useEffect(() => {
    if (!runId) {
      setError("No pipeline Run ID specified.");
      return;
    }

    const ws = new WebSocket(`ws://127.0.0.1:8000/ws/pipeline/${runId}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      try {
        const log = JSON.parse(event.data);
        setLogs((prev) => [...prev, log]);
      } catch (err) {
        console.error("Failed to parse log message:", err);
      }
    };

    ws.onerror = () => {
      console.warn("WebSocket connection failed. Falling back to polling logs.");
    };

    ws.onclose = () => {
      console.log("WebSocket closed");
    };

    // If WebSocket fails, poll logs manually
    const pollLogs = async () => {
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/history/${runId}/logs`);
        if (res.ok) {
          const data = await res.json();
          setLogs(data);
        }
      } catch (e) {
        console.error("Failed to poll logs:", e);
      }
    };

    const interval = setInterval(() => {
      if (ws.readyState !== WebSocket.OPEN) {
        pollLogs();
      }
    }, 4000);

    return () => {
      ws.close();
      clearInterval(interval);
    };
  }, [runId]);

  // Scroll to bottom of terminal
  useEffect(() => {
    terminalEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  const getLogLevelColor = (level: string) => {
    switch (level.toUpperCase()) {
      case "SUCCESS":
        return "text-emerald-400";
      case "ERROR":
        return "text-[#B91C35]";
      case "WARNING":
        return "text-amber-400";
      case "INFO":
        return "text-[#6B9AC4]";
      default:
        return "text-[#F5E6CA]";
    }
  };

  const getStageNodeStatus = (stageNum: number) => {
    if (!stats) return "pending";
    const status = stats.status.toUpperCase();
    
    if (status === "ERROR") return "error";
    if (status === "COMPLETE") return "completed";
    
    if (stageNum === 1) {
      if (stats.companies_found > 0) return "completed";
      if (status === "RUNNING") return "active";
    }
    if (stageNum === 2) {
      if (stats.prospects_found > 0) return "completed";
      if (stats.companies_found > 0 && status === "RUNNING") return "active";
    }
    if (stageNum === 3) {
      if (status === "REVIEWING") return "completed";
      if (stats.prospects_found > 0 && status === "RUNNING") return "active";
    }
    
    return "pending";
  };

  const stageNodeClass = (stageNum: number) => {
    const s = getStageNodeStatus(stageNum);
    if (s === "completed") return "bg-[#B91C35]/20 border-[#B91C35] text-[#B91C35]";
    if (s === "active") return "bg-[#6B9AC4]/10 border-[#6B9AC4] text-[#6B9AC4] animate-pulse";
    if (s === "error") return "bg-[#6B0F1A]/20 border-[#B91C35]/50 text-[#B91C35]/60";
    return "border-[#6B9AC4]/15 text-[#6B9AC4]/30";
  };

  const stageTitleClass = (stageNum: number) => {
    const s = getStageNodeStatus(stageNum);
    if (s === "active") return "text-[#6B9AC4]";
    return "text-[#F5E6CA]";
  };

  if (error) {
    return (
      <div className="relative min-h-screen flex flex-col justify-center items-center px-4 font-mono z-10">
        <ParticlesBackground />
        <div className="p-8 rounded-xl bg-[#6B0F1A]/15 border border-[#B91C35]/25 text-[#B91C35] max-w-md text-center space-y-4 animate-fade-in">
          <p>{error}</p>
          <Link href="/input" className="inline-block px-4 py-2 bg-[#B91C35]/15 border border-[#B91C35]/30 rounded text-xs font-bold hover:bg-[#B91C35]/25 transition-all text-[#F5E6CA]">
            Return to Specifications
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden font-sans">
      <ParticlesBackground />

      {/* ── Header ── */}
      <header className="w-full max-w-7xl mx-auto px-6 py-6 flex justify-between items-center z-10 anim-fade-up">
        <div className="flex items-center space-x-2 font-mono text-sm text-[#6B9AC4]">
          <span>Pipeline ID:</span>
          <span className="text-[#F5E6CA] font-bold">{runId?.split("-")[0]}...</span>
        </div>
        
        {stats && (
          <div className="flex items-center space-x-2 px-3 py-1 rounded glass-navy font-mono text-xs text-[#6B9AC4]">
            <span>Domain:</span>
            <span className="text-[#B91C35] font-bold">{stats.seed_domain}</span>
          </div>
        )}
      </header>

      {/* ── Error Alert Banner ── */}
      {stats && stats.status.toUpperCase() === "ERROR" && (
        <div className="w-full max-w-6xl mx-auto px-6 mb-2 z-10 animate-fade-in">
          <div className="p-4 rounded-xl bg-[#6B0F1A]/20 border border-[#B91C35]/30 font-mono text-xs flex flex-col space-y-1">
            <span className="font-bold text-sm text-[#B91C35]">❌ Pipeline Execution Aborted</span>
            <span className="text-[#6B9AC4]">Error details: {stats.error_message || "Stage execution failed without description."}</span>
          </div>
        </div>
      )}

      {/* ── Main Execution View ── */}
      <main className="flex-grow max-w-6xl mx-auto px-6 py-6 z-10 w-full grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        
        {/* Left column: Stage Indicators and Stats */}
        <div className="lg:col-span-4 flex flex-col space-y-6 anim-fade-up-d1">
          <div className="p-6 rounded-2xl glass-navy space-y-6">
            <h2 className="text-lg font-bold text-[#F5E6CA] flex items-center space-x-2">
              <Cpu className="w-4 h-4 text-[#B91C35]" />
              <span>Orchestrator Nodes</span>
            </h2>

            {/* Stages Tracker */}
            <div className="space-y-4 font-mono text-xs">
              {[
                { num: 1, title: "Company Discovery", desc: "Identify lookalike companies", stat: stats?.companies_found, statLabel: "competitors" },
                { num: 2, title: "Decision Makers", desc: "Sourcing prospect profiles", stat: stats?.prospects_found, statLabel: "leads" },
                { num: 3, title: "Scoring & Validation", desc: "AI lead scoring & validation", stat: stats?.contacts_verified, statLabel: "emails" },
              ].map((stage) => (
                <div key={stage.num} className="flex items-start space-x-3">
                  <div className={`mt-0.5 w-5 h-5 rounded-full flex items-center justify-center border font-bold text-[10px] ${stageNodeClass(stage.num)}`}>
                    {getStageNodeStatus(stage.num) === "completed" ? "✓" : stage.num}
                  </div>
                  <div>
                    <h4 className={`font-bold ${stageTitleClass(stage.num)}`}>{stage.title}</h4>
                    <p className="text-[#6B9AC4]/50 text-[10px]">{stage.desc}</p>
                    {stats && stage.stat !== undefined && stage.stat > 0 && (
                      <span className="text-emerald-400 text-[10px]">Found {stage.stat} {stage.statLabel}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Running Dashboard Stats */}
          {stats && (
            <div className="p-6 rounded-2xl glass-navy space-y-4 font-mono text-xs anim-fade-up-d2">
              <h3 className="font-bold text-[#6B9AC4]/60 uppercase tracking-wider">Metrics Dashboard</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="p-3 bg-[#060A12] border border-[#6B9AC4]/10 rounded-xl text-center">
                  <div className="text-[#6B9AC4]/40 mb-1">Lookalikes</div>
                  <div className="text-xl font-bold text-[#F5E6CA]">{stats.companies_found}</div>
                </div>
                <div className="p-3 bg-[#060A12] border border-[#6B9AC4]/10 rounded-xl text-center">
                  <div className="text-[#6B9AC4]/40 mb-1">Leads Sourced</div>
                  <div className="text-xl font-bold text-[#F5E6CA]">{stats.prospects_found}</div>
                </div>
                <div className="p-3 bg-[#060A12] border border-[#6B9AC4]/10 rounded-xl text-center">
                  <div className="text-[#6B9AC4]/40 mb-1">Verified</div>
                  <div className="text-xl font-bold text-emerald-400">{stats.contacts_verified}</div>
                </div>
                <div className="p-3 bg-[#060A12] border border-[#6B9AC4]/10 rounded-xl text-center">
                  <div className="text-[#6B9AC4]/40 mb-1">Run State</div>
                  {stats.status.toUpperCase() === "ERROR" ? (
                    <div className="text-xs font-bold text-[#B91C35] flex items-center justify-center space-x-1 mt-1">
                      <span className="w-2 h-2 rounded-full bg-[#B91C35] animate-pulse"></span>
                      <span>ERROR</span>
                    </div>
                  ) : stats.status.toUpperCase() === "REVIEWING" || stats.status.toUpperCase() === "COMPLETE" ? (
                    <div className="text-xs font-bold text-emerald-400 flex items-center justify-center space-x-1 mt-1">
                      <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                      <span>{stats.status}</span>
                    </div>
                  ) : (
                    <div className="text-xs font-bold text-[#6B9AC4] flex items-center justify-center space-x-1 mt-1 animate-pulse">
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                      <span>{stats.status}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Right column: Live Terminal */}
        <div className="lg:col-span-8 flex flex-col h-[500px] lg:h-auto min-h-[450px] anim-fade-up-d2">
          <div className="flex-grow flex flex-col rounded-2xl bg-[#040810] border border-[#6B9AC4]/10 overflow-hidden terminal-scanline shadow-2xl">
            {/* Terminal Header */}
            <div className="px-4 py-3 bg-[#0A1628] border-b border-[#6B9AC4]/10 flex justify-between items-center text-xs font-mono text-[#6B9AC4]">
              <div className="flex items-center space-x-2">
                <TerminalIcon className="w-4 h-4 text-[#B91C35]" />
                <span className="font-bold text-[#F5E6CA]/80">coldchain-orchestrator@engine.sh</span>
              </div>
              <div className="flex items-center space-x-1.5">
                <span className="w-2.5 h-2.5 rounded-full bg-[#6B0F1A] border border-[#B91C35]/50"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-[#B91C35]/40 border border-[#B91C35]/60"></span>
                <span className="w-2.5 h-2.5 rounded-full bg-[#6B9AC4]/30 border border-[#6B9AC4]/50"></span>
              </div>
            </div>

            {/* Terminal Log Output */}
            <div className="flex-grow overflow-y-auto p-4 space-y-2 font-mono-custom text-xs scrollbar-thin">
              {logs.length === 0 ? (
                <div className="text-[#6B9AC4]/30 italic py-2 animate-pulse">
                  Establishing secure pipeline handshake...
                </div>
              ) : (
                logs.map((log, index) => (
                  <div key={index} className="flex items-start space-x-2 leading-relaxed">
                    <span className="text-[#6B9AC4]/25 select-none">[{log.timestamp.split(" ")[1]}]</span>
                    {log.stage !== null && (
                      <span className="text-[#6B9AC4]/60 font-bold select-none">[STAGE-{log.stage}]</span>
                    )}
                    <span className={getLogLevelColor(log.level)}>{log.message}</span>
                  </div>
                ))
              )}
              <div ref={terminalEndRef} />
            </div>
            
            {/* Terminal Footer */}
            <div className="px-4 py-2.5 bg-[#060A12] border-t border-[#6B9AC4]/10 flex justify-between items-center text-[10px] font-mono text-[#6B9AC4]/30">
              <span>Ctrl+C to Terminate Run</span>
              <span className="animate-pulse text-[#B91C35]">■ Streaming Logs</span>
            </div>
          </div>
        </div>

      </main>

      {/* ── Footer ── */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-6 text-center text-[#6B9AC4]/30 text-xs font-mono z-10">
        Automatic redirection triggers when stages 1-3 complete.
      </footer>
    </div>
  );
}
