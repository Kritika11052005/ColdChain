/* eslint-disable @typescript-eslint/no-explicit-any */
"use client";

import React, { useState, useRef } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Globe, Zap, AlertCircle, Loader2 } from "lucide-react";
import Link from "next/link";
import { Turnstile } from "@marsidev/react-turnstile";
import ParticlesBackground from "@/components/ParticlesBackground";

const SAMPLE_DOMAINS = [
  { domain: "razorpay.com", name: "Razorpay (Fintech)" },
  { domain: "stripe.com", name: "Stripe (Payments)" },
  { domain: "clevertap.com", name: "CleverTap (SaaS)" }
];

export default function InputPage() {
  const router = useRouter();
  const [domain, setDomain] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [turnstileToken, setTurnstileToken] = useState<string | null>(null);
  const turnstileRef = useRef<any>(null);

  const validateDomain = (val: string) => {
    const clean = val
      .trim()
      .toLowerCase()
      .replace(/^https?:\/\//, "")
      .replace(/^www\./, "")
      .split("/")[0];

    const pattern = /^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$/;
    if (!pattern.test(clean)) {
      return null;
    }
    return clean;
  };

  const handleChipClick = (selected: string) => {
    setDomain(selected);
    setError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const cleanedDomain = validateDomain(domain);
    if (!cleanedDomain) {
      setError("Please enter a valid domain name (e.g., company.com).");
      return;
    }

    if (!turnstileToken) {
      setError("Please complete the Turnstile security verification.");
      return;
    }

    setLoading(true);

    try {
      const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const response = await fetch(`${apiBaseUrl}/api/pipeline/start`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-Turnstile-Token": turnstileToken
        },
        body: JSON.stringify({ seed_domain: cleanedDomain })
      });

      if (response.ok) {
        const data = await response.json();
        router.push(`/pipeline?run_id=${data.run_id}`);
      } else {
        const errData = await response.json();
        setError(errData.detail || "An error occurred while launching the pipeline.");
        setLoading(false);
        turnstileRef.current?.reset();
        setTurnstileToken(null);
      }
    } catch (err) {
      setError("Unable to connect to the backend server. Make sure it is running.");
      setLoading(false);
      turnstileRef.current?.reset();
      setTurnstileToken(null);
    }
  };

  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden font-sans">
      <ParticlesBackground />

      {/* ── Header ── */}
      <header className="w-full max-w-7xl mx-auto px-6 py-6 flex items-center z-10 anim-fade-up">
        <Link
          href="/"
          className="flex items-center space-x-2 text-[#6B9AC4] hover:text-[#F5E6CA] transition-colors font-mono text-sm"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to Home</span>
        </Link>
      </header>

      {/* ── Console Card ── */}
      <main className="flex-grow flex items-center justify-center px-4 py-8 z-10">
        <div className="w-full max-w-lg p-8 rounded-2xl glass-navy glow-crimson space-y-6 anim-fade-up-d1">
          <div className="space-y-2 text-center">
            <div className="mx-auto w-12 h-12 rounded-xl bg-[#6B9AC4]/10 border border-[#6B9AC4]/20 flex items-center justify-center">
              <Globe className="w-6 h-6 text-[#6B9AC4]" />
            </div>
            <h2 className="text-2xl font-display font-black text-[#F5E6CA]">Target Specification</h2>
            <p className="text-sm text-[#6B9AC4]">
              Provide a seed domain. The engine will discover its industry lookalikes.
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Input field */}
            <div className="space-y-2 anim-fade-up-d2">
              <label className="block text-xs font-mono text-[#6B9AC4]/50 uppercase tracking-wider">
                Seed Domain
              </label>
              <div className="relative">
                <input
                  type="text"
                  placeholder="e.g. razorpay.com"
                  value={domain}
                  onChange={(e) => {
                    setDomain(e.target.value);
                    if (error) setError(null);
                  }}
                  disabled={loading}
                  className="w-full px-4 py-3.5 pl-10 rounded-xl bg-[#060A12] border border-[#6B9AC4]/12 focus:border-[#B91C35] text-[#F5E6CA] font-mono text-sm placeholder-[#6B9AC4]/30 transition-all duration-300 outline-none focus:ring-1 focus:ring-[#B91C35]/30"
                />
                <Globe className="absolute left-3.5 top-4 w-4 h-4 text-[#6B9AC4]/40" />
              </div>
            </div>

            {/* Quick Chips */}
            <div className="space-y-2 anim-fade-up-d3">
              <span className="block text-xs font-mono text-[#6B9AC4]/50 uppercase tracking-wider">
                Quick Start Presets
              </span>
              <div className="flex flex-wrap gap-2">
                {SAMPLE_DOMAINS.map((item) => (
                  <button
                    key={item.domain}
                    type="button"
                    onClick={() => handleChipClick(item.domain)}
                    disabled={loading}
                    className={`px-3 py-1.5 rounded-lg border text-xs font-mono transition-all duration-200 ${domain === item.domain
                        ? "bg-[#B91C35]/15 border-[#B91C35]/50 text-[#F5E6CA]"
                        : "bg-[#060A12] border-[#6B9AC4]/12 text-[#6B9AC4] hover:border-[#6B9AC4]/30 hover:text-[#F5E6CA]"
                      }`}
                  >
                    {item.name}
                  </button>
                ))}
              </div>
            </div>

            {/* Turnstile Captcha */}
            <div className="flex justify-center py-2">
              <Turnstile
                ref={turnstileRef}
                siteKey="1x00000000000000000000AA"
                onSuccess={(token) => {
                  setTurnstileToken(token);
                  setError(null);
                }}
                onError={() => setError("CAPTCHA validation failed. Please try again.")}
                onExpire={() => setTurnstileToken(null)}
                options={{
                  theme: "dark",
                  size: "normal"
                }}
              />
            </div>

            {/* Error Message */}
            {error && (
              <div className="p-3 rounded-lg bg-[#6B0F1A]/20 border border-[#B91C35]/30 text-[#B91C35] text-xs font-mono flex items-start space-x-2 animate-fade-in">
                <AlertCircle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {/* Execute Button */}
            <button
              type="submit"
              disabled={loading}
              className="w-full py-4 rounded-xl bg-[#B91C35] hover:bg-[#D4213E] text-[#F5E6CA] font-bold text-sm transition-all duration-300 flex items-center justify-center space-x-2 glow-crimson glow-crimson-hover disabled:opacity-50 disabled:cursor-not-allowed active:scale-[0.97]"
            >
              {loading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Launching Pipeline...</span>
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4" />
                  <span>Execute Pipeline</span>
                </>
              )}
            </button>
          </form>
        </div>
      </main>

      {/* ── Footer ── */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-6 text-center text-[#6B9AC4]/35 text-xs font-mono z-10">
        Secured by Cloudflare Turnstile verification.
      </footer>
    </div>
  );
}
