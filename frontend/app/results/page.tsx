"use client";

import React, { useEffect, useState, useRef } from "react";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, ChevronRight, Clock, Award, Users, Mail, Building2, Play, Home } from "lucide-react";
import Link from "next/link";
import ParticlesBackground from "@/components/ParticlesBackground";

interface RunStats {
  run_id: string;
  status: string;
  seed_domain: string;
  companies_found: number;
  prospects_found: number;
  contacts_verified: number;
  contacts_scored: number;
  duration_seconds: number | null;
  emails_sent: number;
  emails_failed: number;
}

export default function ResultsPage() {
  const searchParams = useSearchParams();
  const runId = searchParams.get("run_id");

  const [stats, setStats] = useState<RunStats | null>(null);
  const [loading, setLoading] = useState(true);
  const confettiCanvasRef = useRef<HTMLCanvasElement>(null);

  // Stats retrieval
  useEffect(() => {
    if (!runId) return;
    async function fetchStats() {
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/history/${runId}/stats`);
        if (res.ok) {
          const data = await res.json();
          setStats(data);
        }
      } catch (err) {
        console.error("Failed to load results stats:", err);
      } finally {
        setLoading(false);
      }
    }
    fetchStats();
  }, [runId]);

  // Confetti celebration — Fiery Ocean colors
  useEffect(() => {
    const canvas = confettiCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;

    let animationFrameId: number;
    const colors = ["#B91C35", "#6B0F1A", "#6B9AC4", "#F5E6CA", "#10B981", "#0D3B66"];
    
    const confetti: Array<{
      x: number;
      y: number;
      size: number;
      color: string;
      speedY: number;
      speedX: number;
      rotation: number;
      rotationSpeed: number;
    }> = [];

    for (let i = 0; i < 120; i++) {
      confetti.push({
        x: Math.random() * canvas.width,
        y: Math.random() * -canvas.height - 20,
        size: Math.random() * 6 + 4,
        color: colors[Math.floor(Math.random() * colors.length)],
        speedY: Math.random() * 3 + 2,
        speedX: (Math.random() - 0.5) * 2,
        rotation: Math.random() * 360,
        rotationSpeed: (Math.random() - 0.5) * 5,
      });
    }

    const animateConfetti = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      
      let activePieces = 0;
      confetti.forEach((c) => {
        c.y += c.speedY;
        c.x += c.speedX;
        c.rotation += c.rotationSpeed;

        if (c.y < canvas.height) {
          activePieces++;
          ctx.save();
          ctx.translate(c.x, c.y);
          ctx.rotate((c.rotation * Math.PI) / 180);
          ctx.fillStyle = c.color;
          ctx.fillRect(-c.size / 2, -c.size / 2, c.size, c.size);
          ctx.restore();
        }
      });

      if (activePieces > 0) {
        animationFrameId = requestAnimationFrame(animateConfetti);
      }
    };

    animateConfetti();

    const handleResize = () => {
      canvas.width = window.innerWidth;
      canvas.height = window.innerHeight;
    };
    window.addEventListener("resize", handleResize);

    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener("resize", handleResize);
    };
  }, [loading]);

  if (loading) {
    return (
      <div className="relative min-h-screen flex flex-col justify-center items-center font-mono z-10 text-[#6B9AC4]">
        <ParticlesBackground />
        <span>Compiling final statistics...</span>
      </div>
    );
  }

  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden font-sans">
      <ParticlesBackground />
      <canvas ref={confettiCanvasRef} className="fixed inset-0 pointer-events-none z-50" />

      {/* ── Header ── */}
      <header className="w-full max-w-7xl mx-auto px-6 py-6 flex justify-between items-center z-10 anim-fade-up">
        <Link href="/" className="flex items-center space-x-2 text-[#6B9AC4] hover:text-[#F5E6CA] transition-colors font-mono text-sm">
          <Home className="w-4 h-4" />
          <span>Home Dashboard</span>
        </Link>
      </header>

      {/* ── Stats Card ── */}
      <main className="flex-grow flex items-center justify-center px-4 py-8 z-10">
        <div className="w-full max-w-2xl p-8 rounded-2xl glass-navy glow-crimson text-center space-y-8 anim-fade-up-d1">
          
          {/* Congrats Header */}
          <div className="space-y-3">
            <div className="mx-auto w-16 h-16 rounded-full bg-emerald-500/10 border-2 border-emerald-400 flex items-center justify-center anim-pulse-ring">
              <CheckCircle2 className="w-8 h-8 text-emerald-400" />
            </div>
            <h2 className="text-3xl font-display font-black text-[#F5E6CA]">Campaign Dispatched</h2>
            <p className="text-[#6B9AC4] max-w-md mx-auto text-sm">
              ColdChain has processed decision-makers and launched custom outreach.
            </p>
          </div>

          {/* Stats Grid */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 py-4">
              <div className="p-4 bg-[#060A12] border border-[#6B9AC4]/10 rounded-xl">
                <Mail className="w-5 h-5 text-emerald-400 mx-auto mb-2" />
                <div className="text-[10px] font-mono text-[#6B9AC4]/40 uppercase tracking-wider">Sent</div>
                <div className="text-2xl font-bold text-[#F5E6CA] mt-1">{stats.emails_sent}</div>
              </div>

              <div className="p-4 bg-[#060A12] border border-[#6B9AC4]/10 rounded-xl">
                <Users className="w-5 h-5 text-[#B91C35] mx-auto mb-2" />
                <div className="text-[10px] font-mono text-[#6B9AC4]/40 uppercase tracking-wider">Verified</div>
                <div className="text-2xl font-bold text-[#F5E6CA] mt-1">{stats.contacts_verified}</div>
              </div>

              <div className="p-4 bg-[#060A12] border border-[#6B9AC4]/10 rounded-xl">
                <Building2 className="w-5 h-5 text-[#6B9AC4] mx-auto mb-2" />
                <div className="text-[10px] font-mono text-[#6B9AC4]/40 uppercase tracking-wider">Companies</div>
                <div className="text-2xl font-bold text-[#F5E6CA] mt-1">{stats.companies_found}</div>
              </div>

              <div className="p-4 bg-[#060A12] border border-[#6B9AC4]/10 rounded-xl">
                <Clock className="w-5 h-5 text-[#F5E6CA]/60 mx-auto mb-2" />
                <div className="text-[10px] font-mono text-[#6B9AC4]/40 uppercase tracking-wider">Duration</div>
                <div className="text-xl font-bold text-[#F5E6CA] mt-2">
                  {stats.duration_seconds ? `${stats.duration_seconds.toFixed(1)}s` : "--"}
                </div>
              </div>
            </div>
          )}

          {/* Detailed Stats */}
          {stats && (
            <div className="p-5 rounded-xl bg-[#060A12] border border-[#6B9AC4]/10 text-left font-mono text-xs text-[#6B9AC4] space-y-3">
              <div className="flex justify-between">
                <span>Seed Target Domain:</span>
                <span className="text-[#F5E6CA] font-bold">{stats.seed_domain}</span>
              </div>
              <div className="flex justify-between">
                <span>Prospect Sourcing Reach:</span>
                <span className="text-[#F5E6CA]">{stats.prospects_found} decision-makers</span>
              </div>
              <div className="flex justify-between">
                <span>AI scoring count:</span>
                <span className="text-[#F5E6CA]">{stats.contacts_scored} rated</span>
              </div>
              <div className="flex justify-between">
                <span>Outreach failure status:</span>
                <span className={stats.emails_failed > 0 ? "text-[#B91C35]" : "text-emerald-400"}>
                  {stats.emails_failed} errors
                </span>
              </div>
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row justify-center items-center gap-4 pt-2">
            <Link
              href="/input"
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-[#B91C35] hover:bg-[#D4213E] text-[#F5E6CA] font-bold text-sm flex items-center justify-center space-x-2 transition-all duration-300 glow-crimson active:scale-[0.97]"
            >
              <Play className="w-4 h-4 fill-[#F5E6CA]" />
              <span>Launch New Pipeline</span>
            </Link>
            
            <Link
              href="/"
              className="w-full sm:w-auto px-6 py-3.5 rounded-xl bg-[#0A1628] border border-[#6B9AC4]/15 hover:border-[#6B9AC4]/30 text-[#6B9AC4] hover:text-[#F5E6CA] font-bold text-sm flex items-center justify-center space-x-2 transition-all duration-300"
            >
              <span>Back to Dashboard</span>
            </Link>
          </div>
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-6 text-center text-[#6B9AC4]/30 text-xs font-mono z-10">
        ColdChain Outreach Automation Engine.
      </footer>
    </div>
  );
}
