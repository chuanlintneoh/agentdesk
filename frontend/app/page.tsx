"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import Markdown from "markdown-to-jsx";

interface AgentStep {
  role: string;
  content: string;
  tool_calls?: any[];
}

const SCROLL_BOTTOM_THRESHOLD_PX = 80;

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
      // Ensure we extract the pure string text if the content is an object or array
      const textToCopy =
        typeof content === "string"
          ? content
          : JSON.stringify(content, null, 2);

      await navigator.clipboard.writeText(textToCopy);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error("Failed to copy text layout: ", err);
    }
  };

  return (
    <button
      onClick={handleCopy}
      type="button"
      className="ml-3 px-2 py-1 text-xs font-mono rounded bg-zinc-800 border border-zinc-700 text-zinc-300 hover:bg-zinc-700 transition-colors"
    >
      {copied ? "Copied! 👍" : "Copy"}
    </button>
  );
}

export default function AgentWorkbench() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [trace, setTrace] = useState<AgentStep[]>([]);
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

  const scrollToLatest = () => {
    stickToBottomRef.current = true;
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  const handleExecute = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;

    setLoading(true);
    setTrace([]);
    stickToBottomRef.current = true;

    try {
      const response = await fetch("http://localhost:8001/api/agent/stream", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ prompt: prompt }),
      });

      if (!response.ok) throw new Error("Server communication broken.");
      if (!response.body) return;

      // 🔌 Initialize the chunk-by-chunk stream reader
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        // Decode the binary stream chunk into plain text
        buffer += decoder.decode(value, { stream: true });

        // SSE streams separate events with double newlines (\n\n)
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || ""; // Save any incomplete line back to the buffer

        for (const part of parts) {
          const trimmedPart = part.trim();
          if (trimmedPart.startsWith("data: ")) {
            // Strip out the "data: " prefix to extract just the raw JSON string
            const jsonString = trimmedPart.replace("data: ", "").trim();
            try {
              const newStep: AgentStep = JSON.parse(jsonString);

              // Append each reasoning step to the UI live
              setTrace((prev) => [...prev, newStep]);
            } catch (err) {
              console.error("Failed parsing stream token:", err);
            }
          }
        }
      }
    } catch (err) {
      console.error("Connection failed:", err);
      setTrace([
        {
          role: "System Error",
          content:
            "Could not reach the FastAPI backend. Check your terminal logs or CORS configuration.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-50 p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        <div className="border-b border-zinc-800 pb-4">
          <h1 className="text-3xl font-default font-bold tracking-tight">
            AgentDesk Workbench
          </h1>
          <p className="text-zinc-400 mt-1 font-default">
            Orchestrating multi-server MCP environments.
          </p>
        </div>

        <form
          onSubmit={handleExecute}
          className="flex gap-3 bg-zinc-900 p-4 rounded-xl border border-zinc-800"
        >
          <Input
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Ask a multi-step analytical question..."
            disabled={loading}
            className="bg-zinc-950 border-zinc-800 text-zinc-100 placeholder:text-zinc-500 h-12 font-default"
          />
          <Button
            type="submit"
            disabled={loading}
            className="bg-blue-600 hover:bg-blue-500 h-12 px-6 text-white font-medium font-default"
          >
            {loading ? "Running..." : "Execute"}
          </Button>
        </form>

        <div className="space-y-4">
          <h2 className="text-lg font-semibold tracking-wide text-zinc-300 font-default">
            Live Graph Traces
          </h2>

          {trace.length === 0 && !loading && (
            <div className="text-center text-zinc-600 py-12 border border-dashed border-zinc-800 rounded-xl font-default">
              Awaiting prompt execution loops...
            </div>
          )}

          {trace.map((step, idx) => (
            <Card
              key={idx}
              className="bg-zinc-900 border-zinc-800 text-zinc-100"
            >
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-mono text-zinc-400">
                  Step {idx + 1}: {step.role}
                </CardTitle>
                <div className="flex items-center gap-2">
                  {step.tool_calls && (
                    <Badge
                      variant="outline"
                      className="text-amber-400 border-amber-900 bg-amber-950/20"
                    >
                      🛠 Invoking: {step.tool_calls[0].name}
                    </Badge>
                  )}
                  {step.content && <CopyButton content={step.content} />}
                </div>
              </CardHeader>
              <CardContent>
                <div className="whitespace-pre-wrap text-sm text-zinc-300 font-sans leading-relaxed flex flex-col gap-3">
                  {/* CHRONOLOGICAL AI ROUTING CASES */}
                  {(() => {
                    const hasContent =
                      typeof step.content === "string" &&
                      step.content.trim().length > 0;
                    const hasToolCalls =
                      step.tool_calls && step.tool_calls.length > 0;

                    // # Case 1: AIMessage with empty `content` but populated data in `tool_calls` > Calling tool
                    if (!hasContent && hasToolCalls) {
                      return (
                        <div className="space-y-1 opacity-90">
                          <span className="text-xs font-mono text-zinc-500 block">
                            🔧 Tool Invocation Parameter Space:
                          </span>
                          <pre className="p-3 bg-zinc-950/60 rounded-lg border border-zinc-800 text-xs font-mono text-amber-400 overflow-x-auto max-h-60">
                            {JSON.stringify(
                              step.tool_calls?.[0]?.args,
                              null,
                              2,
                            )}
                          </pre>
                        </div>
                      );
                    }

                    // # Case 2: AIMessage with populated data in `content` and `tool_calls` > CoT execution
                    if (hasContent && hasToolCalls) {
                      return (
                        <div className="space-y-3">
                          <div>
                            <Markdown>{step.content as string}</Markdown>
                          </div>
                          <div className="space-y-1 opacity-90 pt-1">
                            <span className="text-xs font-mono text-zinc-500 block">
                              🔧 Parallel Execution Parameter Space:
                            </span>
                            <pre className="p-3 bg-zinc-950/60 rounded-lg border border-zinc-800 text-xs font-mono text-amber-400 overflow-x-auto max-h-60">
                              {JSON.stringify(
                                step.tool_calls?.[0]?.args,
                                null,
                                2,
                              )}
                            </pre>
                          </div>
                        </div>
                      );
                    }

                    // # Case 3: AIMessage with populated data in `content` but empty `tool_calls` > Direct response
                    if (hasContent && !hasToolCalls) {
                      return (
                        <div>
                          <Markdown>{step.content as string}</Markdown>
                        </div>
                      );
                    }

                    return null;
                  })()}

                  {/* CAPTURING TOOL DATA RETURNS (SQL Matrix Array Payloads / RAG contexts) */}
                  {step.content && typeof step.content !== "string" && (
                    <div className="space-y-1">
                      <span className="text-xs font-mono text-zinc-500 block">
                        📥 Data Payload Returned:
                      </span>
                      <pre className="p-3 bg-zinc-950 rounded-lg border border-zinc-800 text-xs font-mono text-emerald-400 overflow-x-auto max-h-96">
                        {JSON.stringify(step.content, null, 2)}
                      </pre>
                    </div>
                  )}

                  {/* SYSTEM RUNTIME FALLBACK */}
                  {!step.content &&
                    (!step.tool_calls || step.tool_calls.length === 0) && (
                      <span className="text-zinc-600 italic text-xs block">
                        Processing internal graph node...
                      </span>
                    )}
                </div>
              </CardContent>
            </Card>
          ))}

          <div ref={bottomRef} aria-hidden="true" />
        </div>
      </div>

      {loading && (
        <button
          type="button"
          onClick={scrollToLatest}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-lg border border-blue-500/40 bg-blue-600 px-4 py-2.5 text-sm font-medium text-white shadow-lg shadow-blue-950/50 hover:bg-blue-500 transition-colors font-default"
        >
          <span className="relative flex size-2">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-sky-300 opacity-75" />
            <span className="relative inline-flex size-2 rounded-full bg-sky-200" />
          </span>
          Agent running…
        </button>
      )}
    </main>
  );
}
