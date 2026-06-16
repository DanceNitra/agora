# AI Customer-Support Agent (demo)

A support agent that answers customers using **only the business's own content** — and when the answer
isn't there, it **says so and offers a human instead of making things up.** That "won't hallucinate
your prices/hours/policies" guarantee is the thing that makes a bot safe to actually put on a website.

## Demo (runs locally, free, on Ollama)
```
$ python support_agent.py "What time do you open on Sunday and do you have oat milk?"
On Sundays we open at 9:00. Yes — we have oat milk at no extra charge.

$ python support_agent.py "Do you ship coffee beans to Prague?"
I'm not sure about shipping to Prague — we focus on Bratislava. I can connect you with the team
at hello@brewandbloom.sk. (It did NOT invent a shipping policy.)
```
Point it at any business's content: `python support_agent.py --content my_business.txt "question"`,
or run `python support_agent.py` for interactive mode.

## How it works
1. Loads the business content, splits into chunks.
2. Retrieves the most relevant chunks for the question (lexical — fast, zero-dep).
3. The LLM answers using ONLY those chunks, with a strict "don't invent, offer a human if unknown" rule.

## For a client
- Swap the local model for OpenAI/Anthropic (one function, `ask_llm`) for production quality.
- Feed real content: scrape their site/FAQ/docs.
- Wrap in a chat widget (web), or wire to WhatsApp / email / their CRM.
- The grounded + refusal behavior is the selling point — demo both in the sales call.

Built as a portfolio piece for AI-agent service work. Tool-agnostic; the value is a reliable agent, not the framework.
