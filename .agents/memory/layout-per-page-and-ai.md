---
name: Layout-per-page mounting & AI accountant wiring
description: Why the sidebar remounts on every route, what state must persist, and how the AI accountant connects to OpenAI via Replit AI Integrations.
---

# Sidebar is mounted per-page, not via a shared layout route

Every page component imports and renders its own `<Layout>` wrapper (there is no
single parent layout route in the router). Consequences:

- **A new page that forgets to wrap its content in `<Layout>` loses the sidebar
  entirely.** This is exactly what made `/robots` and `/integrations/status`
  render with no sidebar — they returned bare `<div>`s. Fix: wrap every return
  (including loading/early returns) in `<Layout>`.
- **The sidebar `<nav>` remounts on every navigation**, so any in-memory sidebar
  state resets. Anything that must survive navigation has to be persisted:
  - expanded accordion sections → `localStorage` (`expandedSections`)
  - nav scroll position → `sessionStorage` (`sidebarScroll`), saved via `onScroll`
    on the nav and restored on mount with `requestAnimationFrame`.

**Why:** Without scroll persistence the menu jumps back to the top after every
sub-item click and the user loses their place. Don't "fix" this by hoisting Layout
into a route wrapper without checking every page — many pages assume they own Layout.

# AI accountant (/ai/chat) uses Replit AI Integrations (OpenAI)

`backend/services/ai/llm_service.py` `LLMService` is the single AI entry point
(chat_routes.py `get_llm_service` → `process_chat_query`; agents.py uses the same).
It was previously bound to `emergentintegrations` (not installed) + `EMERGENT_LLM_KEY`
(missing) → always fell back to a mock.

Now it uses the **python_openai_ai_integrations** blueprint (Replit AI Integrations,
OpenAI-compatible, no own API key, billed to credits). Credentials are the
auto-set env vars `AI_INTEGRATIONS_OPENAI_API_KEY` + `AI_INTEGRATIONS_OPENAI_BASE_URL`
— never ask the user for them, never hardcode.

**How to apply:** All `LLMService` methods funnel through `_get_chat_instance()`,
which returns a `_ChatAdapter` whose `send_message()` calls `AsyncOpenAI`
`chat.completions` (model `gpt-5`, `max_completion_tokens`, no `temperature`). The
OpenAI import + client build is lazy in `_get_openai_client()` and returns `None`
when the integration isn't configured, so the backend never crashes on import —
it just surfaces the methods' Arabic error fallback until the integration is bound.
