"use client";

import { useState, useEffect, useRef } from "react";
import { ragChat, getSuggestedQuestions, clearChatHistory, RAGChatResponse } from "../../lib/api";
import {
  Send,
  Sparkles,
  Loader2,
  Zap,
  Database,
  BookOpen,
  RotateCcw,
  Code2,
  Check,
  Copy,
  Layers,
  Bot,
  User,
} from "lucide-react";
import { ProtectedRoute } from "../../components/ProtectedRoute";
import { AppShell } from "../../components/AppShell";

interface Message {
  role: "user" | "assistant";
  content: string;
  sql?: string;
  rowCount?: number;
  fromCache?: boolean;
  retrievalStats?: RAGChatResponse["rag_retrieval_stats"];
  timestamp?: string;
}

const SESSION_ID =
  typeof window !== "undefined"
    ? sessionStorage.getItem("chat_session_id") ??
      (() => {
        const id = Math.random().toString(36).slice(2);
        sessionStorage.setItem("chat_session_id", id);
        return id;
      })()
    : "default";

export default function ChatPage() {
  return (
    <ProtectedRoute allowedRoles={["admin", "analyst"]} redirectOnRoleDenied="/dashboard">
      <AppShell>
        <ChatContent />
      </AppShell>
    </ProtectedRoute>
  );
}

function ChatContent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [copiedIndex, setCopiedIndex] = useState<number | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    getSuggestedQuestions()
      .then((res) => setSuggestions(res.suggestions))
      .catch(() => {
        setSuggestions([
          "Which state spent the most on opioids in 2024?",
          "Top 5 most expensive drugs by total claim volume",
          "Compare generic vs brand spend and claim rates",
          "Which prescribers have the highest cost in Texas?",
          "What is the average cost per beneficiary across states?",
        ]);
      });
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendQuestion = async (question: string) => {
    if (!question.trim() || loading) return;

    const timeStr = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
    setMessages((prev) => [...prev, { role: "user", content: question, timestamp: timeStr }]);
    setInput("");
    setLoading(true);

    try {
      const res = await ragChat(question, SESSION_ID);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: res.summary,
          sql: res.generated_sql,
          rowCount: res.row_count,
          fromCache: res.from_cache,
          retrievalStats: res.rag_retrieval_stats,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } catch (err: any) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `⚠️ ${err?.response?.data?.detail || "Something went wrong. Please check your query."}`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleNewChat = async () => {
    await clearChatHistory(SESSION_ID).catch(() => {});
    setMessages([]);
  };

  const handleCopySQL = (sql: string, idx: number) => {
    navigator.clipboard.writeText(sql);
    setCopiedIndex(idx);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8.5rem)] glass-panel rounded-2xl border border-slate-800 overflow-hidden shadow-2xl">
      {/* Copilot Header */}
      <div className="bg-slate-900/90 border-b border-slate-800 px-6 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-sky-500/20 border border-sky-500/30 flex items-center justify-center text-sky-400">
            <Bot size={18} />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-wide">RAG Healthcare Intelligence Copilot</h1>
            <p className="text-[11px] text-slate-400">Schema-aware · Safe Harbor PHI Redaction Guard · Conversational Memory</p>
          </div>
        </div>

        <button
          onClick={handleNewChat}
          className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-white bg-slate-950 hover:bg-slate-800 border border-slate-800 rounded-lg px-3 py-1.5 transition-colors"
        >
          <RotateCcw size={12} /> Reset Memory
        </button>
      </div>

      {/* Messages Feed */}
      <div className="flex-1 overflow-y-auto p-6 space-y-4">
        {messages.length === 0 && (
          <div className="max-w-2xl mx-auto my-auto text-center py-10 space-y-6">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-sky-500 to-indigo-600 flex items-center justify-center text-slate-950 font-black text-2xl mx-auto shadow-xl glow-sky">
              🤖
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">How can I assist your clinical data analysis?</h2>
              <p className="text-xs text-slate-400 max-w-md mx-auto mt-1">
                Ask analytical questions in plain English. Queries are verified for SQL safety, executed on Snowflake/Gold, and narrated with clinical domain context.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left pt-2">
              {suggestions.map((q, i) => (
                <button
                  key={i}
                  onClick={() => sendQuestion(q)}
                  className="bg-slate-900/80 hover:bg-slate-800/80 border border-slate-800/80 rounded-xl p-3.5 text-xs text-slate-300 hover:text-white transition-all text-left flex items-start gap-2.5 group"
                >
                  <Sparkles size={14} className="text-sky-400 mt-0.5 shrink-0 group-hover:scale-110 transition-transform" />
                  <span>{q}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div key={i} className={`flex gap-3 ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            {m.role === "assistant" && (
              <div className="w-7 h-7 rounded-lg bg-sky-500/20 border border-sky-500/30 flex items-center justify-center text-sky-400 shrink-0 mt-1">
                <Bot size={14} />
              </div>
            )}

            <div
              className={`max-w-[85%] rounded-2xl p-4 text-xs leading-relaxed ${
                m.role === "user"
                  ? "bg-sky-600 text-white rounded-br-none shadow-lg shadow-sky-600/10"
                  : "bg-slate-900/90 border border-slate-800 rounded-bl-none text-slate-200"
              }`}
            >
              <p className="whitespace-pre-wrap">{m.content}</p>

              {/* Badges for Assistant */}
              {m.role === "assistant" && (
                <div className="mt-3 pt-3 border-t border-slate-800/80 flex flex-wrap items-center gap-2">
                  {m.fromCache && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-md px-2 py-0.5">
                      <Zap size={10} /> Semantic Cache Hit
                    </span>
                  )}
                  {m.retrievalStats && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-sky-400 bg-sky-500/10 border border-sky-500/20 rounded-md px-2 py-0.5">
                      <BookOpen size={10} />
                      {m.retrievalStats.knowledge_chunks + m.retrievalStats.schema_chunks} RAG Chunks
                    </span>
                  )}
                  {m.rowCount !== undefined && m.rowCount > 0 && (
                    <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-slate-400 bg-slate-800 rounded-md px-2 py-0.5">
                      <Database size={10} /> {m.rowCount} Records Retrieved
                    </span>
                  )}
                </div>
              )}

              {/* SQL Inspection Drawer */}
              {m.sql && (
                <div className="mt-3 bg-slate-950 rounded-xl p-3 border border-slate-800/80">
                  <div className="flex items-center justify-between mb-1.5 text-[10px] text-slate-400">
                    <span className="flex items-center gap-1 font-semibold text-sky-400">
                      <Code2 size={11} /> Executed Snowflake SQL
                    </span>
                    <button
                      onClick={() => handleCopySQL(m.sql!, i)}
                      className="hover:text-white flex items-center gap-1"
                    >
                      {copiedIndex === i ? <Check size={10} className="text-emerald-400" /> : <Copy size={10} />}
                      {copiedIndex === i ? "Copied" : "Copy"}
                    </button>
                  </div>
                  <pre className="text-[11px] font-mono text-cyan-300 overflow-x-auto p-1.5">{m.sql}</pre>
                </div>
              )}
            </div>

            {m.role === "user" && (
              <div className="w-7 h-7 rounded-lg bg-slate-800 border border-slate-700 flex items-center justify-center text-slate-300 shrink-0 mt-1">
                <User size={14} />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex items-center gap-3 text-xs text-sky-400 bg-sky-950/30 border border-sky-500/20 p-3.5 rounded-xl max-w-md">
            <Loader2 className="animate-spin shrink-0" size={16} />
            <span>Redacting PHI, retrieving schema & generating SQL...</span>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input Form Bar */}
      <div className="bg-slate-900/90 border-t border-slate-800 p-4">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            sendQuestion(input);
          }}
          className="flex gap-2"
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question (e.g. Which state spent the most on opioids in 2024?)"
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-2.5 text-xs text-white placeholder-slate-500 outline-none focus:border-sky-500 transition-colors"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="bg-sky-600 hover:bg-sky-500 disabled:opacity-40 text-white rounded-xl px-5 py-2.5 transition-colors flex items-center justify-center shadow-lg shadow-sky-600/20"
          >
            <Send size={15} />
          </button>
        </form>
      </div>
    </div>
  );
}
