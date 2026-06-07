"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Play, History, Cpu, Sparkles, Shield, ArrowRight, Activity, Terminal } from "lucide-react";
import ParticlesBackground from "@/components/ParticlesBackground";

interface RunHistoryItem {
  id: string;
  seed_domain: string;
  status: string;
  started_at: string;
  completed_at: string | null;
  duration_seconds: number | null;
  contacts_verified: number;
  emails_sent: number;
}

export default function LandingPage() {
  const [history, setHistory] = useState<RunHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  useEffect(() => {
    async function fetchHistory() {
      try {
        const response = await fetch("http://127.0.0.1:8000/api/history");
        if (response.ok) {
          const data = await response.json();
          setHistory(data);
        }
      } catch (err) {
        console.error("Failed to fetch history:", err);
      } finally {
        setLoadingHistory(false);
      }
    }
    fetchHistory();
  }, []);

  const getStatusColor = (status: string) => {
    switch (status.toUpperCase()) {
      case "RUNNING":
        return "text-[#6B9AC4] bg-[#6B9AC4]/10 border-[#6B9AC4]/25";
      case "REVIEWING":
        return "text-[#F5E6CA] bg-[#F5E6CA]/10 border-[#F5E6CA]/20";
      case "COMPLETE":
        return "text-emerald-400 bg-emerald-500/10 border-emerald-500/20";
      case "ERROR":
        return "text-[#B91C35] bg-[#B91C35]/10 border-[#B91C35]/25";
      case "CANCELLED":
        return "text-[#6B9AC4]/50 bg-[#6B9AC4]/5 border-[#6B9AC4]/10";
      default:
        return "text-[#6B9AC4]/50 bg-[#6B9AC4]/5 border-[#6B9AC4]/10";
    }
  };

  const getActionColor = (status: string) => {
    switch (status.toUpperCase()) {
      case "RUNNING":
        return "text-[#6B9AC4] hover:text-[#F5E6CA]";
      case "REVIEWING":
        return "text-[#B91C35] hover:text-[#D4213E]";
      default:
        return "text-[#6B9AC4] hover:text-[#F5E6CA]";
    }
  };

  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden font-sans">
      <ParticlesBackground />

      {/* ── Header ── */}
      <header className="w-full max-w-7xl mx-auto px-6 py-6 flex justify-between items-center z-10 anim-fade-up">
        <div className="flex items-center space-x-3">
          <div className="relative w-9 h-9 rounded-lg bg-[#B91C35] flex items-center justify-center glow-crimson">
            <Cpu className="w-4.5 h-4.5 text-[#F5E6CA]" />
            <div className="absolute inset-0 rounded-lg border border-[#B91C35]/50 anim-pulse-ring pointer-events-none"></div>
          </div>
          <span className="font-display font-extrabold tracking-[0.2em] text-lg bg-gradient-to-r from-[#F5E6CA] to-[#6B9AC4] bg-clip-text text-transparent">
            COLDCHAIN
          </span>
        </div>

        <Link
          href="/input"
          className="px-5 py-2 rounded-lg bg-[#B91C35]/10 border border-[#B91C35]/25 text-[#F5E6CA] text-sm font-medium hover:bg-[#B91C35]/20 hover:border-[#B91C35]/50 transition-all duration-300"
        >
          Console Launch
        </Link>
      </header>

      {/* ── Hero ── */}
      <main className="flex-grow flex flex-col items-center justify-center max-w-6xl mx-auto px-6 py-12 z-10 w-full">
        <div className="text-center max-w-3xl space-y-6 anim-fade-up-d1">
          <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-[#0D3B66]/30 border border-[#6B9AC4]/15 text-xs text-[#6B9AC4] font-mono tracking-wider uppercase">
            <Sparkles className="w-3.5 h-3.5 text-[#B91C35] animate-pulse" />
            <span>Autonomous Pipeline Engine</span>
          </div>

          <h1 className="text-5xl md:text-7xl font-display font-black tracking-tight leading-[1.1] text-[#F5E6CA]">
            Scale B2B Cold Outreach{" "}
            <span className="bg-gradient-to-r from-[#B91C35] via-[#D4213E] to-[#6B9AC4] bg-clip-text text-transparent text-shimmer">
              On Autopilot
            </span>
          </h1>

          <p className="text-base md:text-lg text-[#6B9AC4] leading-relaxed max-w-2xl mx-auto anim-fade-up-d2">
            Find lookalike targets, extract key decision makers, verify emails, score leads, and dispatch hyper-personalized outreach — all in one unified system.
          </p>

          <div className="flex flex-col sm:flex-row justify-center items-center gap-4 pt-6 anim-fade-up-d3">
            <Link
              href="/input"
              className="group relative w-full sm:w-auto px-8 py-4 rounded-xl bg-[#B91C35] text-[#F5E6CA] font-bold text-lg hover:bg-[#D4213E] active:scale-[0.97] transition-all duration-300 flex items-center justify-center space-x-3 anim-glow-pulse"
            >
              <span>Initialize Pipeline</span>
              <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform duration-300" />
            </Link>
          </div>
        </div>

        {/* ── Feature Cards ── */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full mt-24">
          <div className="card-interactive p-6 rounded-2xl glass-navy anim-fade-up-d2">
            <div className="w-10 h-10 rounded-lg bg-[#B91C35]/10 flex items-center justify-center mb-4">
              <Cpu className="w-5 h-5 text-[#B91C35]" />
            </div>
            <h3 className="text-lg font-bold text-[#F5E6CA] mb-2">1. Lookalike Discovery</h3>
            <p className="text-[#6B9AC4] text-sm leading-relaxed">
              AI-powered Serper + Gemini search dynamically identifies competitors and similar domains to expand your target sales universe.
            </p>
          </div>

          <div className="card-interactive p-6 rounded-2xl glass-navy anim-fade-up-d3">
            <div className="w-10 h-10 rounded-lg bg-[#6B9AC4]/10 flex items-center justify-center mb-4">
              <Shield className="w-5 h-5 text-[#6B9AC4]" />
            </div>
            <h3 className="text-lg font-bold text-[#F5E6CA] mb-2">2. Contact Discovery</h3>
            <p className="text-[#6B9AC4] text-sm leading-relaxed">
              Prospeo-verified contact discovery surfaces decision makers with validated business emails in a single API call.
            </p>
          </div>

          <div className="card-interactive p-6 rounded-2xl glass-navy anim-fade-up-d4">
            <div className="w-10 h-10 rounded-lg bg-[#F5E6CA]/8 flex items-center justify-center mb-4">
              <Sparkles className="w-5 h-5 text-[#F5E6CA]" />
            </div>
            <h3 className="text-lg font-bold text-[#F5E6CA] mb-2">3. AI-Powered Outreach</h3>
            <p className="text-[#6B9AC4] text-sm leading-relaxed">
              Gemini model structures lead relevance ratings and personalizes transactional cold pitches using live company search details.
            </p>
          </div>
        </section>

        {/* ── History Log Table ── */}
        <section className="w-full max-w-4xl mx-auto mt-20 p-6 rounded-2xl glass-navy z-10 anim-fade-up-d5">
          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center space-x-2">
              <History className="w-5 h-5 text-[#B91C35]" />
              <h2 className="text-xl font-bold text-[#F5E6CA]">Pipeline Execution History</h2>
            </div>
            <div className="flex items-center space-x-1.5 text-xs text-[#6B9AC4] font-mono">
              <Activity className="w-3.5 h-3.5 text-[#B91C35] animate-pulse" />
              <span>Live Database sync</span>
            </div>
          </div>

          {loadingHistory ? (
            <div className="py-8 text-center text-[#6B9AC4] text-sm font-mono flex items-center justify-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-[#B91C35] animate-ping"></span>
              <span>Syncing run logs...</span>
            </div>
          ) : history.length === 0 ? (
            <div className="py-10 text-center text-[#6B9AC4]/40 text-sm font-mono">
              No historical runs found. Click &quot;Initialize Pipeline&quot; above to launch your first session.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse text-sm">
                <thead>
                  <tr className="border-b border-[#6B9AC4]/10 text-[#6B9AC4]/50 font-mono text-xs uppercase tracking-wider">
                    <th className="pb-3 font-semibold">Seed Domain</th>
                    <th className="pb-3 font-semibold">Started</th>
                    <th className="pb-3 font-semibold text-center">Status</th>
                    <th className="pb-3 font-semibold text-right">Contacts</th>
                    <th className="pb-3 font-semibold text-right">Sent</th>
                    <th className="pb-3 font-semibold text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#6B9AC4]/8 font-mono text-xs">
                  {history.map((run) => (
                    <tr key={run.id} className="group hover:bg-[#B91C35]/[0.03] transition-colors duration-200">
                      <td className="py-3.5 font-bold text-[#F5E6CA] group-hover:text-white transition-colors">{run.seed_domain}</td>
                      <td className="py-3.5 text-[#6B9AC4]">{run.started_at.split(" ")[0]}</td>
                      <td className="py-3.5 text-center">
                        <span className={`px-2.5 py-0.5 rounded border text-[10px] uppercase font-bold tracking-wider ${getStatusColor(run.status)}`}>
                          {run.status}
                        </span>
                      </td>
                      <td className="py-3.5 text-right text-[#6B9AC4]">{run.contacts_verified}</td>
                      <td className="py-3.5 text-right text-emerald-400">{run.emails_sent}</td>
                      <td className="py-3.5 text-right">
                        {run.status === "RUNNING" ? (
                          <Link
                            href={`/pipeline?run_id=${run.id}`}
                            className={`font-bold flex items-center justify-end space-x-1 ${getActionColor(run.status)}`}
                          >
                            <Terminal className="w-3.5 h-3.5" />
                            <span>Monitor</span>
                          </Link>
                        ) : run.status === "REVIEWING" ? (
                          <Link
                            href={`/review?run_id=${run.id}`}
                            className={`font-bold flex items-center justify-end space-x-1 ${getActionColor(run.status)}`}
                          >
                            <Play className="w-3.5 h-3.5" />
                            <span>Resume</span>
                          </Link>
                        ) : (
                          <Link
                            href={`/results?run_id=${run.id}`}
                            className="text-[#6B9AC4] hover:text-[#F5E6CA] font-bold transition-colors"
                          >
                            Stats
                          </Link>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>

      {/* ── Footer ── */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-8 border-t border-[#6B9AC4]/8 text-center text-[#6B9AC4]/35 text-xs font-mono z-10">
        &copy; {new Date().getFullYear()} ColdChain Engine. All rights reserved.
      </footer>
    </div>
  );
}
