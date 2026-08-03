"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import Markdown from "markdown-to-jsx";
import {
  Sparkles,
  Terminal,
  Wrench,
  Cpu,
  ArrowRight,
  CornerDownLeft,
  Play,
  Trash2,
  RefreshCw,
  ShieldAlert,
  Code,
  Scroll,
  ArrowDown,
  Check,
  Copy,
  ChevronDown,
  Layers,
  User,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface ToolResult {
  name: string;
  content: string;
}

interface AgentStep {
  role: string;
  content?: string;
  node_name?: string;
  tool_calls?: any[];
  is_parallel?: boolean;
  tool_results?: ToolResult[];
}

const fastapiUrl =
  process.env.NEXT_PUBLIC_BACKEND_API_URL || "http://localhost:8000";
const SCROLL_BOTTOM_THRESHOLD_PX = 120;

function isNearPageBottom() {
  return (
    window.innerHeight + window.scrollY >=
    document.documentElement.scrollHeight - SCROLL_BOTTOM_THRESHOLD_PX
  );
}

function CopyButton({ content }: { content: any }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      const textToCopy =
        typeof content === "string"
          ? content
          : JSON.stringify(content, null, 2);

      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy:", err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      type="button"
      className="flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded-md bg-zinc-800/80 hover:bg-zinc-700 border border-zinc-700/60 text-zinc-300 transition-all duration-200"
    >
      {copied ? (
        <>
          <Check className="size-3.5 text-emerald-400" />
          <span className="text-emerald-400">Copied</span>
        </>
      ) : (
        <>
          <Copy className="size-3.5" />
          <span>Copy</span>
        </>
      )}
    </button>
  );
}

export default function AgentWorkbench() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [trace, setTrace] = useState<AgentStep[]>([]);
  const [systemReady, setSystemReady] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);
  const stickToBottomRef = useRef(true);

  useEffect(() => {
    const onScroll = () => {
      stickToBottomRef.current = isNearPageBottom();
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!stickToBottomRef.current) return;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [trace]);

  // Health check polling
  useEffect(() => {
    const checkHealth = async () => {
      try {
        const res = await fetch(`${fastapiUrl}/health`);
        setSystemReady(res.ok);
      } catch (err) {
        setSystemReady(false);
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // 30s interval
    return () => clearInterval(interval);
  }, []);

  const scrollToLatest = () => {
    stickToBottomRef.current = true;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleExecute = async (
    e?: React.FormEvent,
    overridePrompt?: string,
  ) => {
    e?.preventDefault();
    const activePrompt = overridePrompt || prompt;
    if (!activePrompt.trim()) return;

    setLoading(true);
    setPrompt(""); // Clear input box
    setTrace([{ role: "User", content: activePrompt }]); // Start trace with user prompt
    stickToBottomRef.current = true;

    try {
      const response = await fetch(`${fastapiUrl}/api/agent/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt: activePrompt }),
      });

      if (!response.ok) throw new Error("Server communication broken.");
      if (!response.body) return;

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          const trimmedPart = part.trim();
          if (trimmedPart.startsWith("data: ")) {
            const jsonString = trimmedPart.replace("data: ", "").trim();
            try {
              const newStep: AgentStep = JSON.parse(jsonString);
              setTrace((prev) => [...prev, newStep]);
            } catch (err) {
              console.error("Failed parsing stream token:", err);
            }
          }
        }
      }
    } catch (err) {
      console.error("Connection failed:", err);
      setTrace((prev) => [
        ...prev,
        {
          role: "System Error",
          content: `Could not reach the FastAPI backend. Ensure it is running at \`${fastapiUrl}\`.`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-50 selection:bg-blue-500/30">
      {/* Background Decor */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden opacity-20">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-blue-500/10 blur-[120px] rounded-full translate-x-1/2 -translate-y-1/2" />
        <div className="absolute bottom-0 left-0 w-[500px] h-[500px] bg-indigo-500/10 blur-[120px] rounded-full -translate-x-1/2 translate-y-1/2" />
      </div>

      <div className="relative max-w-4xl mx-auto px-6 py-12 space-y-10">
        {/* Header Section */}
        <header className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 border-b border-zinc-900">
          <div className="space-y-1">
            <div className="flex items-center gap-2 mb-1">
              <div
                className={cn(
                  "size-2 rounded-full shadow-[0_0_8px_rgba(16,185,129,0.5)] animate-pulse",
                  systemReady
                    ? "bg-emerald-500"
                    : "bg-rose-500 shadow-rose-500/50",
                )}
              />
              <span
                className={cn(
                  "text-[10px] font-bold tracking-widest uppercase",
                  systemReady ? "text-emerald-500/80" : "text-rose-500/80",
                )}
              >
                {systemReady ? "System Ready" : "System Offline"}
              </span>
            </div>
            <h1 className="text-4xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 animate-gradient-slow">
              AgentDesk{" "}
              <span className="font-light text-zinc-400/80">Workbench</span>
            </h1>
            <p className="text-zinc-500 text-sm font-medium">
              Multi-node MCP Agent Orchestrator & Trace Visualizer.
            </p>
          </div>
          <div className="flex items-center gap-3 h-10 px-4 rounded-full bg-zinc-900/50 border border-zinc-800/80 text-zinc-400 text-xs font-mono">
            <Layers className="size-3.5 text-blue-500" />
            {fastapiUrl.replace("http://", "").replace("https://", "")}
          </div>
        </header>

        {/* Prompt Input Section */}
        <section className="space-y-4">
          <form
            onSubmit={handleExecute}
            className="group relative bg-zinc-900/40 border border-zinc-800/60 rounded-2xl p-1 focus-within:ring-2 focus-within:ring-blue-500/20 focus-within:border-blue-500/40 transition-all duration-300"
          >
            <div className="flex items-center gap-3 px-4 pt-3">
              <Terminal className="size-4 text-zinc-500 group-focus-within:text-blue-400 transition-colors" />
              <span className="text-xs font-mono font-bold text-zinc-600 group-focus-within:text-zinc-500 uppercase tracking-wider">
                Session Console
              </span>
            </div>
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleExecute(undefined, prompt);
                }
              }}
              placeholder="Enter a multi-step analytical command..."
              disabled={loading}
              rows={6}
              className="w-full bg-transparent border-0 ring-0 focus-visible:ring-0 text-lg leading-relaxed py-4 px-4 placeholder:text-zinc-600 font-default resize-none overflow-y-auto max-h-21"
            />
            <div className="flex items-center justify-between p-3 bg-zinc-900/20 rounded-xl mt-1">
              <div className="flex items-center gap-2 text-[10px] text-zinc-600 font-mono px-2">
                <span className="bg-zinc-800 px-1 rounded text-zinc-400">
                  ENTER
                </span>{" "}
                to execute
                <span className="mx-1 text-zinc-700">·</span>
                <span className="bg-zinc-800 px-1 rounded text-zinc-400">
                  SHIFT+ENTER
                </span>{" "}
                for newline
              </div>
              <div className="flex gap-2">
                <Button
                  type="button"
                  onClick={() => {
                    setTrace([]);
                    setPrompt("");
                  }}
                  variant="ghost"
                  className="h-9 w-9 p-0 text-zinc-500 hover:text-rose-400 hover:bg-rose-400/10 rounded-lg"
                >
                  <Trash2 className="size-4" />
                </Button>
                <Button
                  type="submit"
                  disabled={loading || !prompt.trim()}
                  className="bg-blue-600 hover:bg-blue-500 text-white rounded-lg h-9 px-5 gap-2 transition-all duration-300 font-bold shadow-lg shadow-blue-900/20"
                >
                  {loading ? (
                    <RefreshCw className="size-4 animate-spin" />
                  ) : (
                    <>
                      <span>Run</span>
                      <Play className="size-3.5 fill-current" />
                    </>
                  )}
                </Button>
              </div>
            </div>
          </form>
        </section>

        {/* Trace Timeline */}
        <section className="space-y-8 relative">
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-zinc-600 flex items-center gap-2">
              <Scroll className="size-4" />
              Agent Workflow Trace
            </h2>
            {trace.length > 0 && (
              <Badge
                variant="outline"
                className="bg-blue-500/5 text-blue-400 border-blue-500/20 text-[10px] py-0.5 px-2.5 font-mono"
              >
                {trace.length} Node{trace.length !== 1 ? "s" : ""} recorded
              </Badge>
            )}
          </div>

          {trace.length === 0 && !loading && (
            <div className="flex flex-col items-center justify-center py-20 border border-dashed border-zinc-900 rounded-2xl bg-zinc-950/40 group">
              <div className="size-12 rounded-full bg-zinc-900 border border-zinc-800 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                <Cpu className="size-6 text-zinc-700" />
              </div>
              <p className="text-zinc-600 font-medium tracking-tight">
                Awaiting model orchestration loops...
              </p>
            </div>
          )}

          <div className="relative space-y-6">
            {/* The Timeline Line */}
            {trace.length > 1 && (
              <div className="absolute left-[19px] top-4 bottom-4 w-px bg-gradient-to-b from-blue-500/20 via-zinc-800 to-zinc-900/10" />
            )}

            {trace.map((step, idx) => {
              const isTool = step.tool_calls && step.tool_calls.length > 0;
              const isToolResult =
                step.tool_results && step.tool_results.length > 0;
              const isParallel =
                step.is_parallel ||
                (isToolResult && step.tool_results!.length > 1) ||
                (isTool && (step.tool_calls?.length ?? 0) > 1);
              const isError = step.role.toLowerCase().includes("error");

              let Icon = Cpu;
              let iconColor = "text-blue-400";
              let iconBg = "bg-blue-950/30";
              let iconBorder = "border-blue-500/30";

              if (isToolResult || isTool) {
                Icon = isParallel ? Layers : Wrench;
                iconColor = "text-amber-400";
                iconBg = "bg-amber-950/30";
                iconBorder = "border-amber-500/30";
              } else if (step.role === "User") {
                Icon = User;
                iconColor = "text-emerald-400";
                iconBg = "bg-emerald-950/30";
                iconBorder = "border-emerald-500/30";
              } else if (isError) {
                Icon = ShieldAlert;
                iconColor = "text-rose-400";
                iconBg = "bg-rose-950/30";
                iconBorder = "border-rose-500/30";
              } else if (step.role.toLowerCase() === "system") {
                Icon = Terminal;
                iconColor = "text-zinc-400";
                iconBg = "bg-zinc-900";
                iconBorder = "border-zinc-700";
              }

              return (
                <div
                  key={idx}
                  className="group relative pl-12 animate-in fade-in slide-in-from-left-2 duration-500 ease-out"
                >
                  {/* Timeline Node Icon */}
                  <div
                    className={cn(
                      "absolute left-0 top-1 size-10 rounded-xl border flex items-center justify-center z-10 transition-transform duration-300 group-hover:scale-110",
                      iconBg,
                      iconBorder,
                    )}
                  >
                    <Icon className={cn("size-5", iconColor)} />
                  </div>

                  <Card className="bg-zinc-900/40 border-zinc-800/80 overflow-hidden shadow-sm hover:shadow-md hover:border-zinc-700 transition-all">
                    <div className="flex items-center justify-between px-4 py-3 bg-zinc-900/60 border-b border-zinc-800/80">
                      <div className="flex items-center gap-3">
                        <span className="text-[10px] font-mono font-bold text-zinc-500 uppercase tracking-widest bg-zinc-800/50 px-1.5 py-0.5 rounded">
                          Node {idx + 1}
                        </span>
                        <h3 className="text-sm font-semibold text-zinc-300 capitalize">
                          {step.role === "User"
                            ? "Your Request"
                            : isParallel
                              ? "Parallel Tool Execution"
                              : step.role}
                        </h3>
                      </div>
                      <div className="flex items-center gap-3">
                        {isParallel && (
                          <Badge
                            variant="secondary"
                            className="bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px] font-mono hover:bg-amber-500/20"
                          >
                            {step.tool_calls
                              ? `Invoke: ${step.tool_calls.length} tools`
                              : `${step.tool_results!.length} tools`}
                          </Badge>
                        )}
                        {isTool && !isParallel && (
                          <Badge
                            variant="secondary"
                            className="bg-amber-500/10 text-amber-500 border-amber-500/20 text-[10px] font-mono hover:bg-amber-500/20"
                          >
                            Invoke: {step.tool_calls?.[0]?.name}
                          </Badge>
                        )}
                        {step.content && <CopyButton content={step.content} />}
                      </div>
                    </div>

                    <CardContent className="p-4">
                      <div className="text-sm leading-relaxed text-zinc-300 font-sans space-y-4">
                        {(() => {
                          const hasContent =
                            typeof step.content === "string" &&
                            step.content.trim().length > 0;
                          const hasToolCalls =
                            step.tool_calls && step.tool_calls.length > 0;

                          return (
                            <div className="space-y-4">
                              {hasContent && (
                                <div className="markdown-content">
                                  <Markdown>{step.content as string}</Markdown>
                                </div>
                              )}

                              {/* Pending/Invocation: render every parallel tool call */}
                              {hasToolCalls && (
                                <div
                                  className={cn(
                                    "space-y-2",
                                    hasContent &&
                                      "pt-4 border-t border-zinc-800/50",
                                  )}
                                >
                                  <div className="flex items-center gap-2 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                                    <Code className="size-3" />
                                    {hasContent
                                      ? "Parallel Invocation / Tool Parameters"
                                      : isParallel
                                        ? "Parallel Tool Invocations"
                                        : "Tool Parameters"}
                                  </div>
                                  <div className="grid gap-2 sm:grid-cols-2">
                                    {(step.tool_calls ?? []).map(
                                      (tc: any, ti: number) => (
                                        <div
                                          key={ti}
                                          className="rounded-xl border border-zinc-800/60 bg-zinc-950 overflow-hidden shadow-inner"
                                        >
                                          <div className="px-3 py-1.5 bg-zinc-900/70 border-b border-zinc-800/60 text-[11px] font-mono text-amber-400/90 flex items-center justify-between">
                                            <span>{tc?.name}</span>
                                            <span className="text-zinc-600">
                                              #{ti + 1}
                                            </span>
                                          </div>
                                          <pre className="p-3 text-[12.5px] font-mono text-amber-300/90 overflow-x-auto">
                                            {JSON.stringify(tc?.args, null, 2)}
                                          </pre>
                                        </div>
                                      ),
                                    )}
                                  </div>
                                </div>
                              )}
                            </div>
                          );
                        })()}

                        {/* Batched Tool Results (parallel execution outputs) */}
                        {isToolResult && (
                          <div className="space-y-2 pt-4 border-t border-zinc-800/50">
                            <div className="flex items-center gap-2 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                              <Layers className="size-3" />
                              {isParallel
                                ? "Parallel Tool Results"
                                : "Tool Result"}
                            </div>
                            <div
                              className={cn(
                                "grid gap-2",
                                step.tool_results!.length > 1
                                  ? "sm:grid-cols-2"
                                  : "grid-cols-1",
                              )}
                            >
                              {step.tool_results!.map((tr, ri) => (
                                <div
                                  key={ri}
                                  className="rounded-xl border border-zinc-800/60 bg-zinc-950 overflow-hidden shadow-inner"
                                >
                                  <div className="px-3 py-1.5 bg-zinc-900/70 border-b border-zinc-800/60 text-[11px] font-mono text-emerald-400/90 flex items-center justify-between">
                                    <span>{tr.name}</span>
                                    <span className="text-zinc-600">
                                      #{ri + 1}
                                    </span>
                                  </div>
                                  <pre className="p-3 text-[12.5px] font-mono text-emerald-300/90 overflow-x-auto max-h-[400px]">
                                    {typeof tr.content === "string"
                                      ? tr.content
                                      : JSON.stringify(tr.content, null, 2)}
                                  </pre>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {/* Data Payloads (Objects/Arrays) */}
                        {step.content && typeof step.content !== "string" && (
                          <div className="space-y-2">
                            <div className="flex items-center gap-2 text-[10px] font-bold text-zinc-500 uppercase tracking-wider">
                              <ChevronDown className="size-3" />
                              Payload Response
                            </div>
                            <pre className="p-3.5 bg-zinc-950 rounded-xl border border-zinc-800/60 text-[13px] font-mono text-emerald-400/90 overflow-x-auto shadow-inner max-h-[500px]">
                              {JSON.stringify(step.content, null, 2)}
                            </pre>
                          </div>
                        )}

                        {/* Fallback */}
                        {!step.content &&
                          !isToolResult &&
                          (!step.tool_calls ||
                            step.tool_calls.length === 0) && (
                            <div className="flex items-center gap-2 text-zinc-600 italic py-2">
                              <RefreshCw className="size-3 animate-spin" />
                              <span className="text-xs">
                                Processing internal graph node...
                              </span>
                            </div>
                          )}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              );
            })}
            <div ref={bottomRef} className="h-4" aria-hidden="true" />
          </div>
        </section>
      </div>

      {/* Floating Status Indicator */}
      {loading && (
        <button
          type="button"
          onClick={scrollToLatest}
          className="fixed bottom-8 right-8 z-50 flex items-center gap-3 rounded-2xl bg-zinc-950/85 backdrop-blur-md border border-blue-500/30 pl-4 pr-5 py-3 text-xs font-bold text-white shadow-[0_8px_32px_rgba(0,0,0,0.4),0_0_20px_rgba(59,130,246,0.1)] hover:bg-zinc-900 transition-all duration-300 animate-in fade-in slide-in-from-bottom-4 group"
        >
          <div className="relative flex size-2.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-blue-400 opacity-75" />
            <span className="relative inline-flex size-2.5 rounded-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.6)]" />
          </div>
          <span className="tracking-wide text-zinc-200">
            Agent executing pipeline…
          </span>
          <ArrowDown className="size-3 text-blue-400 group-hover:translate-y-0.5 transition-transform" />
        </button>
      )}
    </main>
  );
}
