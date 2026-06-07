"use client";

import React, { useEffect, useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ArrowLeft, Check, X, ShieldCheck, Mail, Send, Award, Filter, RefreshCw, Loader2, CheckCircle2 } from "lucide-react";
import Link from "next/link";
import ParticlesBackground from "@/components/ParticlesBackground";

interface Contact {
  id: string;
  full_name: string;
  title: string;
  company_name: string;
  company_domain: string;
  email: string;
  email_verified: boolean;
  lead_score: number;
  score_reason: string;
  included: boolean;
}

export default function ReviewPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const runId = searchParams.get("run_id");

  const [contacts, setContacts] = useState<Contact[]>([]);
  const [selectedContact, setSelectedContact] = useState<Contact | null>(null);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [scoreFilter, setScoreFilter] = useState(65);
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
  const wsBaseUrl = apiBaseUrl.replace(/^http/, "ws");

  const [showOverlay, setShowOverlay] = useState(false);
  const [deploymentStatus, setDeploymentStatus] = useState<Record<string, 'queued' | 'sending' | 'sent' | 'failed'>>({});
  const [deployLogs, setDeployLogs] = useState<string[]>([]);
  const [deployError, setDeployError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;

    async function fetchContacts() {
      try {
        const res = await fetch(`${apiBaseUrl}/api/pipeline/${runId}/contacts`);
        if (res.ok) {
          const data = await res.json();
          const updatedContacts = data.contacts.map((c: Contact) => ({
            ...c,
            included: c.lead_score >= scoreFilter
          }));
          setContacts(updatedContacts);
          if (updatedContacts.length > 0) {
            setSelectedContact(updatedContacts[0]);
          }
        } else {
          setError("Failed to load contacts for review.");
        }
      } catch (err) {
        setError("Error loading contacts. Make sure the backend server is running.");
      } finally {
        setLoading(false);
      }
    }

    fetchContacts();
  }, [runId]);

  const toggleContact = (id: string) => {
    setContacts(prev =>
      prev.map(c => (c.id === id ? { ...c, included: !c.included } : c))
    );
  };

  const handleScoreFilterChange = (val: number) => {
    setScoreFilter(val);
    setContacts(prev =>
      prev.map(c => ({
        ...c,
        included: c.lead_score >= val
      }))
    );
  };

  const handleSend = async () => {
    const selectedContacts = contacts.filter(c => c.included);
    const checkedIds = selectedContacts.map(c => c.id);
    if (checkedIds.length === 0) {
      alert("Please check at least one contact to send emails.");
      return;
    }

    setSending(true);
    setShowOverlay(true);
    setDeployError(null);
    setDeployLogs(["Initializing outreach pipeline..."]);

    // Initialize all checked contacts to 'queued'
    const initialStatus: Record<string, 'queued' | 'sending' | 'sent' | 'failed'> = {};
    selectedContacts.forEach(c => {
      initialStatus[c.id] = 'queued';
    });
    setDeploymentStatus(initialStatus);

    // Establish WebSocket connection for real-time Stage 4 logs
    let ws: WebSocket | null = null;
    try {
      ws = new WebSocket(`${wsBaseUrl}/ws/pipeline/${runId}`);

      ws.onmessage = (event) => {
        try {
          const log = JSON.parse(event.data);
          const msg = log.message;
          setDeployLogs(prev => [...prev, msg]);

          // Parse sending state
          if (msg.includes("Firing email to ")) {
            const parts = msg.split("Firing email to ");
            if (parts.length > 1) {
              const emailPart = parts[1].replace("...", "").trim();
              const contact = selectedContacts.find(c => c.email.toLowerCase() === emailPart.toLowerCase());
              if (contact) {
                setDeploymentStatus(prev => ({ ...prev, [contact.id]: 'sending' }));
              }
            }
          }
          // Parse sent state
          else if (msg.includes("Email sent successfully via Brevo to ")) {
            const parts = msg.split("Email sent successfully via Brevo to ");
            if (parts.length > 1) {
              const emailPart = parts[1].split(". Msg ID:")[0].trim();
              const contact = selectedContacts.find(c => c.email.toLowerCase() === emailPart.toLowerCase());
              if (contact) {
                setDeploymentStatus(prev => ({ ...prev, [contact.id]: 'sent' }));
              }
            }
          }
          // Parse failure state
          else if (msg.includes("Brevo rejected send") || msg.includes("Brevo connection failed")) {
            setDeploymentStatus(prev => {
              const next = { ...prev };
              const sendingId = Object.keys(next).find(id => next[id] === 'sending');
              if (sendingId) {
                next[sendingId] = 'failed';
              }
              return next;
            });
          }
        } catch (err) {
          console.error("Failed to parse log message:", err);
        }
      };

      ws.onerror = () => {
        console.warn("WebSocket connection failed. Falling back to log updates from stats.");
      };
    } catch (err) {
      console.error("Failed to initialize WebSocket:", err);
    }

    try {
      const res = await fetch(`${apiBaseUrl}/api/pipeline/${runId}/send`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          run_id: runId,
          contact_ids: checkedIds
        })
      });

      if (!res.ok) {
        const errData = await res.json();
        setDeployError(errData.detail || "Error initiating email sendout.");
        setSending(false);
        ws?.close();
        return;
      }

      // Start polling status
      const interval = setInterval(async () => {
        try {
          const statsRes = await fetch(`${apiBaseUrl}/api/history/${runId}/stats`);
          if (statsRes.ok) {
            const statsData = await statsRes.json();

            if (statsData.status === "COMPLETE") {
              clearInterval(interval);
              ws?.close();

              // Set all remaining 'sending' or 'queued' to 'sent'
              setDeploymentStatus(prev => {
                const next = { ...prev };
                Object.keys(next).forEach(id => {
                  if (next[id] === 'sending' || next[id] === 'queued') {
                    next[id] = 'sent';
                  }
                });
                return next;
              });

              setDeployLogs(prev => [...prev, "Outreach campaign successfully deployed!"]);

              // Wait 1.5 seconds for visual feedback
              setTimeout(() => {
                router.push(`/results?run_id=${runId}`);
              }, 1500);
            } else if (statsData.status === "ERROR") {
              clearInterval(interval);
              ws?.close();
              setDeployError(statsData.error_message || "An error occurred during pipeline execution.");
              setSending(false);
            }
          }
        } catch (err) {
          console.error("Error polling stats:", err);
        }
      }, 2000);

    } catch (err) {
      setDeployError("Failed to initiate email sendout. Make sure the backend is active.");
      setSending(false);
      ws?.close();
    }
  };

  const closeOverlay = () => {
    setShowOverlay(false);
    setSending(false);
    setDeployError(null);
  };

  const getEmailPreview = (contact: Contact) => {
    const firstName = contact.full_name.split(" ")[0];
    const company = contact.company_name || contact.company_domain.split(".")[0].toUpperCase();

    let keyword = "scaling up your digital initiatives";
    if (contact.company_domain.includes("pay") || contact.company_domain.includes("checkout")) {
      keyword = "streamlining merchant transactions and developer-friendly onboarding";
    } else if (contact.company_domain.includes("market") || contact.company_domain.includes("campaign")) {
      keyword = "boosting user retention and automating targeted push notifications";
    }

    const subject = `Quick question regarding ${company}'s ${contact.title} roadmap`;
    const bodyHtml = `
      <div style="font-family: 'Inter', sans-serif; font-size: 14px; color: #2D3748; line-height: 1.7;">
        <p>Hi ${firstName},</p>
        <p>I was researching ${company} and noted your focus on <strong>${keyword}</strong>.</p>
        <p>As the ${contact.title}, I imagine keeping checkout conversions high and churn rates low are top priorities heading into next quarter.</p>
        <p>We've recently helped teams similar to ${company} build high-speed integrations that reduce engineering latency by up to 35% without breaking existing dependencies.</p>
        <p>Would you be open to a brief 5-minute introductory call next Tuesday at 10 AM? If not, no worries at all.</p>
        <p>Best regards,<br/>
        <strong>Kritzzz</strong><br/>
        ColdChain Automation</p>
      </div>
    `;
    return { subject, bodyHtml };
  };

  if (loading) {
    return (
      <div className="relative min-h-screen flex flex-col justify-center items-center font-mono z-10 text-[#6B9AC4]">
        <ParticlesBackground />
        <RefreshCw className="w-8 h-8 animate-spin text-[#B91C35] mb-4" />
        <span>Loading lead records...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="relative min-h-screen flex flex-col justify-center items-center px-4 font-mono z-10">
        <ParticlesBackground />
        <div className="p-8 rounded-xl bg-[#6B0F1A]/15 border border-[#B91C35]/25 text-[#B91C35] max-w-md text-center space-y-4">
          <p>{error}</p>
          <Link href="/input" className="inline-block px-4 py-2 bg-[#B91C35]/15 border border-[#B91C35]/30 rounded text-xs font-bold hover:bg-[#B91C35]/25 transition-all text-[#F5E6CA]">
            Return to Specifications
          </Link>
        </div>
      </div>
    );
  }

  const selectedPreview = selectedContact ? getEmailPreview(selectedContact) : null;
  const checkedCount = contacts.filter(c => c.included).length;

  const selectedContacts = contacts.filter(c => c.included);
  const totalChecked = selectedContacts.length;
  const sentCount = Object.values(deploymentStatus).filter(s => s === 'sent').length;
  const failedCount = Object.values(deploymentStatus).filter(s => s === 'failed').length;
  const progressPercentage = totalChecked > 0 ? ((sentCount + failedCount) / totalChecked) * 100 : 0;

  return (
    <div className="relative min-h-screen flex flex-col justify-between overflow-x-hidden font-sans">
      <ParticlesBackground />

      {/* ── Header ── */}
      <header className="w-full max-w-7xl mx-auto px-6 py-4 flex justify-between items-center z-10 border-b border-[#6B9AC4]/10 bg-[#060A12]/80 backdrop-blur-md sticky top-0">
        <div className="flex items-center space-x-4">
          <Link href="/input" className="p-2 rounded-lg bg-[#0A1628] border border-[#6B9AC4]/12 text-[#6B9AC4] hover:text-[#F5E6CA] hover:border-[#6B9AC4]/30 transition-all">
            <ArrowLeft className="w-4 h-4" />
          </Link>
          <div>
            <h2 className="text-lg font-bold text-[#F5E6CA] font-display">Review Sourced Leads</h2>
            <p className="text-xs text-[#6B9AC4] font-mono">Stage 3 Verification completed.</p>
          </div>
        </div>

        <button
          onClick={handleSend}
          disabled={sending || checkedCount === 0}
          className="px-6 py-2.5 rounded-xl bg-[#B91C35] hover:bg-[#D4213E] text-[#F5E6CA] font-bold text-xs flex items-center space-x-2 transition-all duration-300 glow-crimson disabled:opacity-50 active:scale-[0.97]"
        >
          {sending ? (
            <>
              <RefreshCw className="w-4 h-4 animate-spin" />
              <span>Sending...</span>
            </>
          ) : (
            <>
              <Send className="w-4 h-4" />
              <span>Deploy Outreach ({checkedCount})</span>
            </>
          )}
        </button>
      </header>

      {/* ── Content Split Screen ── */}
      <main className="flex-grow max-w-7xl mx-auto px-6 py-6 z-10 w-full grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">

        {/* Left Column: Leads list */}
        <div className="lg:col-span-5 flex flex-col space-y-4 anim-fade-up">
          {/* Filters */}
          <div className="p-4 rounded-xl glass-navy flex justify-between items-center font-mono text-xs text-[#6B9AC4]">
            <div className="flex items-center space-x-2">
              <Filter className="w-4 h-4 text-[#B91C35]" />
              <span>Lead Score Cutoff:</span>
            </div>
            <div className="flex items-center space-x-2">
              {[
                { val: 0, label: "All" },
                { val: 65, label: "≥ 65" },
                { val: 80, label: "≥ 80" },
              ].map((opt) => (
                <button
                  key={opt.val}
                  onClick={() => handleScoreFilterChange(opt.val)}
                  className={`px-2.5 py-1 rounded border text-[11px] transition-all ${scoreFilter === opt.val
                      ? "border-[#B91C35]/50 text-[#F5E6CA] bg-[#B91C35]/10"
                      : "border-[#6B9AC4]/12 hover:border-[#6B9AC4]/25 text-[#6B9AC4]"
                    }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Contact List */}
          <div className="flex-grow overflow-y-auto space-y-2 max-h-[600px] lg:max-h-[calc(100vh-220px)] scrollbar-thin pr-1">
            {contacts.length === 0 ? (
              <div className="p-8 text-center text-[#6B9AC4]/30 font-mono text-xs">
                No contacts sourced for this run.
              </div>
            ) : (
              contacts.map(contact => (
                <div
                  key={contact.id}
                  onClick={() => setSelectedContact(contact)}
                  className={`p-4 rounded-xl border cursor-pointer transition-all duration-200 ${selectedContact?.id === contact.id
                      ? "bg-[#0A1628] border-[#B91C35]/30 border-l-2 border-l-[#B91C35]"
                      : "bg-[#0A1628]/60 border-[#6B9AC4]/8 hover:border-[#6B9AC4]/20"
                    }`}
                >
                  <div className="flex items-start justify-between space-x-2">
                    <div className="flex items-start space-x-3">
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          toggleContact(contact.id);
                        }}
                        className={`mt-0.5 w-4.5 h-4.5 rounded flex items-center justify-center border transition-all ${contact.included
                            ? "bg-[#B91C35] border-[#B91C35] text-[#F5E6CA]"
                            : "border-[#6B9AC4]/20 hover:border-[#6B9AC4]/40 bg-transparent"
                          }`}
                      >
                        {contact.included && <Check className="w-3 h-3 stroke-[3]" />}
                      </button>

                      <div className="space-y-0.5">
                        <h4 className="font-bold text-[#F5E6CA] text-sm leading-none">{contact.full_name}</h4>
                        <p className="text-[#6B9AC4] text-xs leading-tight">{contact.title}</p>
                        <p className="text-[#6B9AC4]/35 font-mono text-[10px]">{contact.company_name || contact.company_domain}</p>
                      </div>
                    </div>

                    <div className="text-right flex flex-col items-end space-y-1">
                      <div className={`px-2 py-0.5 rounded text-[10px] font-bold font-mono border flex items-center space-x-1 ${contact.lead_score >= 80 ? "text-emerald-400 bg-emerald-500/10 border-emerald-500/20" :
                          contact.lead_score >= 65 ? "text-[#6B9AC4] bg-[#6B9AC4]/10 border-[#6B9AC4]/20" :
                            "text-[#6B9AC4]/40 bg-[#6B9AC4]/5 border-[#6B9AC4]/10"
                        }`}>
                        <Award className="w-3 h-3" />
                        <span>{contact.lead_score}</span>
                      </div>

                      {contact.email_verified && (
                        <div className="text-[10px] text-emerald-400 font-mono flex items-center space-x-0.5">
                          <ShieldCheck className="w-3 h-3" />
                          <span>verified</span>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Email Preview */}
        <div className="lg:col-span-7 flex flex-col min-h-[450px] anim-fade-up-d1">
          {selectedContact && selectedPreview ? (
            <div className="flex-grow flex flex-col rounded-2xl bg-[#040810] border border-[#6B9AC4]/10 overflow-hidden shadow-2xl">
              {/* Preview Header */}
              <div className="px-4 py-3 bg-[#0A1628] border-b border-[#6B9AC4]/10 flex justify-between items-center text-xs font-mono text-[#6B9AC4]">
                <div className="flex items-center space-x-2">
                  <Mail className="w-4 h-4 text-[#B91C35]" />
                  <span className="text-[#F5E6CA]/80">Outreach Personalizer</span>
                </div>
                <div className="text-[10px] text-[#6B9AC4]/40 font-mono">
                  Score rationale: {selectedContact.score_reason.split("|")[0]}
                </div>
              </div>

              {/* Email details */}
              <div className="p-4 border-b border-[#6B9AC4]/10 space-y-2 text-xs font-mono text-[#6B9AC4]">
                <div>
                  <span className="text-[#6B9AC4]/40">From:</span>{" "}
                  <span className="text-[#F5E6CA]">Kritzzz &lt;ananya.benjwal@gmail.com&gt;</span>
                </div>
                <div>
                  <span className="text-[#6B9AC4]/40">To:</span>{" "}
                  <span className="text-[#F5E6CA]">{selectedContact.full_name} &lt;{selectedContact.email}&gt;</span>
                </div>
                <div>
                  <span className="text-[#6B9AC4]/40">Subject:</span>{" "}
                  <span className="text-[#B91C35] font-bold">{selectedPreview.subject}</span>
                </div>
              </div>

              {/* Email body — warm cream background */}
              <div className="flex-grow bg-[#FAF5EB] p-6 overflow-y-auto min-h-[250px] scrollbar-thin">
                <div dangerouslySetInnerHTML={{ __html: selectedPreview.bodyHtml }} />
              </div>

              {/* Bottom panel */}
              <div className="p-4 bg-[#0A1628] border-t border-[#6B9AC4]/10 flex justify-between items-center text-[10px] font-mono text-[#6B9AC4]/30">
                <span>Status: Preview Mode</span>
                <span className="text-[#6B9AC4]/50">Will deliver via Brevo API on confirm.</span>
              </div>
            </div>
          ) : (
            <div className="flex-grow flex flex-col items-center justify-center rounded-2xl glass-navy p-8 text-center text-[#6B9AC4]/30 font-mono text-xs">
              Select a contact from the list to preview their personalized email campaign.
            </div>
          )}
        </div>

      </main>

      {/* ── Footer ── */}
      <footer className="w-full max-w-7xl mx-auto px-6 py-6 text-center text-[#6B9AC4]/30 text-xs font-mono z-10">
        Review emails prior to final deployment. Deselected contacts will be excluded.
      </footer>

      {/* ── Deployment Progress Overlay ── */}
      {showOverlay && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#040810]/85 backdrop-blur-md animate-fade-in animate-duration-300">
          <div className="w-full max-w-2xl p-6 md:p-8 rounded-2xl bg-[#0A1628]/95 border border-[#6B9AC4]/15 shadow-2xl space-y-6 relative overflow-hidden glow-crimson animate-scale-up">

            {/* Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-3">
                {deployError ? (
                  <div className="p-2 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-500">
                    <X className="w-5 h-5" />
                  </div>
                ) : progressPercentage === 100 ? (
                  <div className="p-2 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
                    <CheckCircle2 className="w-5 h-5 animate-bounce" />
                  </div>
                ) : (
                  <div className="p-2 rounded-lg bg-[#B91C35]/10 border border-[#B91C35]/20 text-[#B91C35]">
                    <Loader2 className="w-5 h-5 animate-spin" />
                  </div>
                )}
                <div>
                  <h3 className="text-lg font-bold text-[#F5E6CA] font-display">
                    {deployError ? "Outreach Deployment Failed" :
                      progressPercentage === 100 ? "Campaign Dispatched!" :
                        "Deploying Outreach Campaign"}
                  </h3>
                  <p className="text-xs text-[#6B9AC4] font-mono">
                    {deployError ? "Orchestrator encountered an issue." :
                      progressPercentage === 100 ? "Redirecting to campaign summary..." :
                        "ColdChain AI is dispatching personalized emails..."}
                  </p>
                </div>
              </div>

              {deployError && (
                <button
                  aria-label="button"
                  onClick={closeOverlay}
                  className="p-1.5 rounded-lg bg-[#060A12] border border-[#6B9AC4]/10 hover:border-[#B91C35]/30 text-[#6B9AC4] hover:text-[#F5E6CA] transition-all"
                >
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* Error Message */}
            {deployError && (
              <div className="p-4 rounded-xl bg-rose-950/20 border border-rose-500/30 text-rose-400 font-mono text-xs">
                <strong>Error:</strong> {deployError}
              </div>
            )}

            {/* Progress Bar */}
            <div className="space-y-2">
              <div className="flex justify-between text-xs font-mono text-[#6B9AC4]">
                <span>Campaign Progress</span>
                <span className="text-[#F5E6CA] font-bold">
                  {sentCount + failedCount} / {totalChecked} Sent
                </span>
              </div>
              <div className="w-full bg-[#060A12] h-2.5 rounded-full overflow-hidden border border-[#6B9AC4]/10 p-[1px]">
                <div
                  className="bg-gradient-to-r from-[#B91C35] to-[#D4213E] h-full transition-all duration-500 rounded-full"
                  style={{ width: `${progressPercentage}%` }}
                />
              </div>
            </div>

            {/* Recipients List Grid */}
            <div className="space-y-2">
              <h4 className="text-xs font-mono font-bold text-[#6B9AC4]/60 uppercase tracking-wider">Recipients List</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2 max-h-40 overflow-y-auto pr-1 scrollbar-thin">
                {selectedContacts.map(c => {
                  const status = deploymentStatus[c.id] || 'queued';
                  return (
                    <div
                      key={c.id}
                      className={`p-2.5 rounded-xl border flex items-center justify-between text-xs font-mono transition-all ${status === 'sending' ? 'bg-[#B91C35]/5 border-[#B91C35]/30' :
                          status === 'sent' ? 'bg-emerald-500/5 border-emerald-500/20' :
                            status === 'failed' ? 'bg-rose-500/5 border-rose-500/20' :
                              'bg-[#060A12]/40 border-[#6B9AC4]/5'
                        }`}
                    >
                      <div className="overflow-hidden mr-2">
                        <div className="font-bold text-[#F5E6CA] truncate">{c.full_name}</div>
                        <div className="text-[10px] text-[#6B9AC4]/50 truncate">{c.email}</div>
                      </div>

                      <div>
                        {status === 'queued' && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-gray-500/10 border border-gray-500/20 text-gray-400">
                            Queued
                          </span>
                        )}
                        {status === 'sending' && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-[#B91C35]/15 border border-[#B91C35]/30 text-[#B91C35] flex items-center space-x-1 animate-pulse">
                            <span className="w-1 h-1 rounded-full bg-[#B91C35] animate-ping" />
                            <span>Sending</span>
                          </span>
                        )}
                        {status === 'sent' && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/15 border border-emerald-500/30 text-emerald-400 flex items-center space-x-1">
                            <span>✓</span>
                            <span>Sent</span>
                          </span>
                        )}
                        {status === 'failed' && (
                          <span className="text-[10px] px-2 py-0.5 rounded bg-rose-500/15 border border-rose-500/30 text-rose-400 flex items-center space-x-1">
                            <span>✕</span>
                            <span>Failed</span>
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Live Terminal Log */}
            <div className="space-y-2">
              <h4 className="text-xs font-mono font-bold text-[#6B9AC4]/60 uppercase tracking-wider">Live Logs</h4>
              <div className="bg-[#040810] border border-[#6B9AC4]/10 rounded-xl p-4 h-28 overflow-y-auto font-mono text-[10px] text-[#6B9AC4] space-y-1.5 scrollbar-thin select-none">
                {deployLogs.map((logMsg, i) => (
                  <div key={i} className="flex items-start space-x-1">
                    <span className="text-[#6B9AC4]/30 select-none">&gt;</span>
                    <span>{logMsg}</span>
                  </div>
                ))}
                {/* Dummy element for scrolling to bottom */}
                <div ref={(el) => el?.scrollIntoView({ behavior: 'smooth' })} />
              </div>
            </div>

            {/* Close / Action Button */}
            {deployError && (
              <button
                onClick={closeOverlay}
                className="w-full py-3 rounded-xl bg-[#0A1628] border border-[#6B9AC4]/15 hover:border-[#B91C35]/30 text-[#F5E6CA] font-bold text-xs transition-all text-center"
              >
                Close Overlay and Review Leads
              </button>
            )}

          </div>
        </div>
      )}
    </div>
  );
}
