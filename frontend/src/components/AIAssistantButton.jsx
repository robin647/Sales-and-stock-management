import { useState } from "react";
import { assistantApi } from "../api/endpoints";

const suggestions = [
  "32 number lot er swing operator ke?",
  "2026-11-23 tarike Mahadi Zone-1 showroom e koto sale?",
  "Employee Robin er salary koto?",
];

export default function AIAssistantButton() {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([
    { role: "assistant", text: "Assalamu alaikum! Business data niye Bangla, English, ba Banglish-e jiggesh korun." },
  ]);
  const [sending, setSending] = useState(false);

  async function sendQuestion(value = question) {
    const text = value.trim();
    if (!text || sending) return;
    setQuestion("");
    setSending(true);
    setMessages((current) => [...current, { role: "user", text }]);
    try {
      const { data } = await assistantApi.chat(text);
      setMessages((current) => [...current, { role: "assistant", text: data.answer }]);
    } catch (error) {
      const detail = error.response?.data?.detail;
      const fallback = error.response?.status === 503
        ? "AI assistant setup kora hoyni. Backend-e GROQ_API_KEY configure korte hobe."
        : "Request-ti complete kora jayni. Ektu pore abar try korun.";
      setMessages((current) => [...current, { role: "assistant", text: typeof detail === "string" ? detail : fallback }]);
    } finally {
      setSending(false);
    }
  }

  return (
    <>
      {open && (
        <section
          aria-label="AI business assistant"
          className="fixed bottom-[142px] right-3 z-50 flex h-[min(570px,calc(100dvh-170px))] w-[min(390px,calc(100vw-24px))] flex-col overflow-hidden rounded-2xl border border-emerald-900/10 bg-white shadow-2xl sm:right-5"
        >
          <header className="flex items-center justify-between bg-emerald-900 px-4 py-3 text-white">
            <div className="flex items-center gap-3">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-white/15" aria-hidden="true">
                <svg viewBox="0 0 24 24" fill="none" className="h-5 w-5" stroke="currentColor" strokeWidth="1.7">
                  <path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z" />
                  <path d="m19 15 .9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15Z" />
                </svg>
              </span>
              <div><h2 className="text-sm font-semibold text-white">AI Assistance</h2><p className="text-xs text-emerald-100">Business data helper</p></div>
            </div>
            <button type="button" onClick={() => setOpen(false)} aria-label="Close AI assistant" className="flex h-8 w-8 items-center justify-center rounded-full text-xl text-white/80 hover:bg-white/10 hover:text-white">×</button>
          </header>

          <div className="flex-1 space-y-3 overflow-y-auto bg-[#f7f8f4] p-3" aria-live="polite">
            {messages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}>
                <p className={`max-w-[88%] whitespace-pre-wrap rounded-2xl px-3 py-2 text-sm leading-6 ${message.role === "user" ? "rounded-br-sm bg-emerald-800 text-white" : "rounded-bl-sm border border-gray-200 bg-white text-gray-800 shadow-sm"}`}>
                  {message.text}
                </p>
              </div>
            ))}
            {sending && <div className="flex justify-start"><p className="rounded-2xl rounded-bl-sm border border-gray-200 bg-white px-3 py-2 text-sm text-gray-500">Checking business records…</p></div>}
          </div>

          {messages.length === 1 && (
            <div className="flex gap-2 overflow-x-auto border-t border-gray-100 bg-white px-3 py-2">
              {suggestions.map((suggestion) => (
                <button key={suggestion} type="button" onClick={() => sendQuestion(suggestion)} disabled={sending} className="shrink-0 rounded-full border border-emerald-200 px-3 py-1.5 text-left text-xs text-emerald-900 hover:bg-emerald-50 disabled:opacity-50">
                  {suggestion}
                </button>
              ))}
            </div>
          )}

          <p className="bg-white px-3 pt-2 text-center text-[11px] text-gray-500">Relevant business records are sent to Groq to answer your question.</p>
          <form onSubmit={(event) => { event.preventDefault(); sendQuestion(); }} className="flex items-end gap-2 border-t border-gray-200 bg-white p-3">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  sendQuestion();
                }
              }}
              rows={1}
              maxLength={1000}
              placeholder="Ask about your business…"
              aria-label="Ask the AI assistant"
              className="max-h-24 min-h-10 flex-1 resize-y rounded-xl border border-gray-300 px-3 py-2 text-sm text-gray-900 outline-none focus:border-emerald-700 focus:ring-2 focus:ring-emerald-100"
            />
            <button type="submit" disabled={sending || !question.trim()} aria-label="Send question" title="Send question" className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-emerald-800 text-white hover:bg-emerald-900 disabled:opacity-40">
              <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="h-5 w-5" stroke="currentColor" strokeWidth="1.8"><path d="m5 12 14-7-4.5 14-2.4-5.8L5 12Z" /><path d="m12.1 13.2 6.9-8.2" /></svg>
            </button>
          </form>
        </section>
      )}

      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-label={open ? "Close AI assistant" : "Open AI assistant"}
        aria-expanded={open}
        title="AI Assistance"
        className="fixed bottom-[82px] right-5 z-50 flex h-12 w-12 items-center justify-center rounded-full border-2 border-white bg-emerald-800 text-white shadow-lg transition-transform hover:scale-105 focus-visible:outline-none focus-visible:ring-4 focus-visible:ring-emerald-300"
      >
        <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className="h-6 w-6" stroke="currentColor" strokeWidth="1.7">
          <path d="m12 2 1.8 6.2L20 10l-6.2 1.8L12 18l-1.8-6.2L4 10l6.2-1.8L12 2Z" />
          <path d="m19 15 .9 2.1L22 18l-2.1.9L19 21l-.9-2.1L16 18l2.1-.9L19 15Z" />
        </svg>
      </button>
    </>
  );
}