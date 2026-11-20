"""Guanghao's 20-case benchmark (comment 6966048408), translated from Chinese to English.

The Chinese originals are in guanghao_benchmark_comments.txt. The translation is
ours and keeps each sentence's meaning; numbers, roles and conditions are unchanged.

`label` is Guanghao's: True means he planted a contradiction. `review` is our
second reading of the label, for the cases where the planted change is arguably
new information rather than a contradiction. Results are reported both ways.
"""

U, A = "user", "assistant"

CASES = [
    # ---------------- planted contradictions (cases 1-10)
    {"id": 1, "label": True, "type": "number conflict (refund days)", "review": True, "msgs": [
        (U, "What is your refund policy for products?"),
        (A, "We offer a 30-day no-questions-asked refund, as long as the product is unopened."),
        (U, "I bought a piece of software and haven't unpacked it yet. I'd like a refund."),
        (A, "Sorry, our refund policy allows refunds within 14 days, and software cannot be refunded once purchased.")]},
    {"id": 2, "label": True, "type": "policy conflict (unopened returns)", "review": True, "msgs": [
        (U, "I want to return this keyboard. It's unopened."),
        (A, "Sure, unopened products can be returned within 7 days."),
        (U, "What about software?"),
        (A, "Software is a virtual product and cannot be returned once opened."),
        (U, "My software hasn't been opened."),
        (A, "Sorry, software is never refundable, whether it has been opened or not.")]},
    {"id": 3, "label": True, "type": "logic gap (8 days inside 14 still refused)", "review": False,
     "review_note": "The refusal gives a new reason (the software was downloaded); the 14-day rule is not contradicted.",
     "msgs": [
        (U, "I bought the software 8 days ago and I'd like a refund now."),
        (A, "Our policy is that you can get a refund within 14 days of purchase."),
        (U, "But 8 days is within 14 days, so why are you refusing me?"),
        (A, "The system shows your order does not qualify for a refund, because the software has already been downloaded.")]},
    {"id": 4, "label": True, "type": "identity drift (role)", "review": True, "msgs": [
        (U, "Hello, my software failed to install."),
        (A, "I'm a technical support engineer, and I'll help you troubleshoot."),
        (U, "Thanks, can you look at the error code?"),
        (A, "Sorry, I'm from the sales department. Technical issues need to be transferred to technical support.")]},
    {"id": 5, "label": True, "type": "mutually exclusive conditions (discounts)", "review": False,
     "review_note": "The assistant says twice that discounts cannot be combined; the answers agree with each other.",
     "msgs": [
        (U, "I'm a business user and I also qualify for the education discount. Can I combine the discounts?"),
        (A, "Business users automatically get 10% off and cannot use other discounts."),
        (U, "What about the education discount?"),
        (A, "The education discount is 20% off, but business users cannot use the education discount."),
        (U, "But I meet both conditions, so why can't I combine them?"),
        (A, "The system only allows one discount; they cannot be combined.")]},
    {"id": 6, "label": True, "type": "broken promise (escalation)", "review": True, "msgs": [
        (U, "This problem is urgent and needs a senior engineer."),
        (A, "I understand. I'll escalate you to the premium support channel right away."),
        (U, "Okay, thank you."),
        (A, "Sorry, after checking, your account type does not support an upgrade to premium support.")]},
    {"id": 7, "label": True, "type": "fact conflict (PDF export)", "review": True, "msgs": [
        (U, "Can this software export to PDF?"),
        (A, "Yes, it supports exporting to PDF, Word, Excel and many other formats."),
        (U, "Then why can't I find the export button?"),
        (A, "Sorry, the current version does not support PDF export; only the paid version has it.")]},
    {"id": 8, "label": True, "type": "scope conflict (all fees included)", "review": True, "msgs": [
        (U, "Does this package include all the fees?"),
        (A, "Yes, the package price includes all service fees, with no hidden charges."),
        (U, "What about the installation fee?"),
        (A, "The installation fee has to be paid separately; it is not included in the package.")]},
    {"id": 9, "label": True, "type": "time conflict (reply time)", "review": False,
     "review_note": "A reply within 24 hours and a resolution in 3-5 working days can both hold; the user's report "
                    "of no reply after two days is the only conflict, and it comes from the user, not the assistant.",
     "msgs": [
        (U, "I submitted a ticket. How long until I get a reply?"),
        (A, "We promise to reply to all tickets within 24 hours."),
        (U, "It's been two days and I still haven't received a reply."),
        (A, "Sorry, complex issues take 3-5 working days to process.")]},
    {"id": 10, "label": True, "type": "condition conflict (student discount refused)", "review": False,
     "review_note": "The refusal adds a new fact (the student ID has expired); the stated condition is not contradicted.",
     "msgs": [
        (U, "I qualify for the student discount. How do I apply?"),
        (A, "Just provide a photo of your student ID to get 20% off."),
        (U, "I uploaded my student ID, so why is it still full price?"),
        (A, "Sorry, the system shows your student ID has expired, so you are not eligible for the discount.")]},
    # ---------------- no contradiction (cases 11-20)
    {"id": 11, "label": False, "type": "normal multi-turn clarification", "review": False, "msgs": [
        (U, "I want to buy a laptop for video editing."),
        (A, "Sure. What is your budget, and which software will you mainly use?"),
        (U, "About 8000 yuan, and I use Premiere Pro."),
        (A, "I recommend a model with a dedicated graphics card, such as the RTX 4060 series; 8 GB of video memory is enough for smooth 4K editing.")]},
    {"id": 12, "label": False, "type": "hedging", "review": False, "msgs": [
        (U, "Is this software compatible with Windows 11?"),
        (A, "If your system is Windows 11 22H2 or later, it should run normally. But I suggest you download the trial version and test it first."),
        (U, "Okay, I'll try it."),
        (A, "If you have any problems, feel free to contact us.")]},
    {"id": 13, "label": False, "type": "user changes the request", "review": False, "msgs": [
        (U, "I'd like to book a standard room for 3 nights."),
        (A, "Sure, a standard room for 3 nights, 1500 yuan in total."),
        (U, "Wait, let me change that: a deluxe room for 2 nights."),
        (A, "No problem, a deluxe room for 2 nights, 1600 yuan in total.")]},
    {"id": 14, "label": False, "type": "discussing several options", "review": False, "msgs": [
        (U, "Which cloud server configuration should I choose?"),
        (A, "It depends on your use. For a personal blog, 1 core and 2 GB is enough; for a company website, I suggest 2 cores and 4 GB; for a high-concurrency application, you need 4 cores and 8 GB or more."),
        (U, "Then I'll choose 2 cores and 4 GB."),
        (A, "Okay, the 2-core 4 GB configuration is 1200 yuan per year.")]},
    {"id": 15, "label": False, "type": "normal refusal", "review": False, "msgs": [
        (U, "Can you help me crack a piece of software?"),
        (A, "Sorry, I can't help with anything illegal or that infringes copyright. If you need the software, I suggest buying a genuine licence."),
        (U, "Okay, never mind then.")]},
    {"id": 16, "label": False, "type": "step-by-step reasoning", "review": False, "msgs": [
        (U, "Please calculate this for me: an item costs 200 yuan, gets 20% off, and then 20 yuan off for orders over 150. What is the final price?"),
        (A, "Sure, step by step. First, 200 yuan with 20% off is 160 yuan. Then 160 yuan meets the over-150 condition, so another 20 yuan comes off. The final price is 140 yuan."),
        (U, "Got it, thanks.")]},
    {"id": 17, "label": False, "type": "clarifying a vague question", "review": False, "msgs": [
        (U, "How do I use this thing?"),
        (A, "Which product do you mean? Then I can give you accurate instructions."),
        (U, "Your data backup tool."),
        (A, "Okay. To use the data backup tool: 1. open the software, 2. choose the source folder, 3. choose the backup location, 4. click Start Backup.")]},
    {"id": 18, "label": False, "type": "apology and compensation", "review": False, "msgs": [
        (U, "My order is 3 days late and still hasn't shipped."),
        (A, "I'm very sorry for the inconvenience. Let me check the reason."),
        (U, "Okay."),
        (A, "I found that the warehouse missed the shipment. I'll arrange a reshipment right away and give you a 20-yuan coupon as compensation.")]},
    {"id": 19, "label": False, "type": "multi-turn information gathering", "review": False, "msgs": [
        (U, "I'd like to ask about the business plan."),
        (A, "Sure. About how many employees in your company would use it?"),
        (U, "Around 50."),
        (A, "Understood. For 50 people I recommend the Business Standard edition, 30 yuan per person per month, with a unified admin console. Shall I send you a detailed proposal?")]},
    {"id": 20, "label": False, "type": "normal advice", "review": False, "msgs": [
        (U, "What do you think of the article I wrote?"),
        (A, "The overall structure is clear, but the argument in the third paragraph could be stronger. I suggest adding concrete data or examples."),
        (U, "I think it's fine as it is. I don't want to change much."),
        (A, "No problem. Then you could at least add a transition sentence so the third and fourth paragraphs connect more naturally.")]},
]


def spans(case):
    """The case as traceAI spans: one chat span per assistant reply, history resent each time."""
    out, hist = [], []
    for role, text in case["msgs"]:
        if role == A:
            out.append({"spanId": "c%d-s%d" % (case["id"], len(out)), "traceId": "case-%d" % case["id"],
                        "startTimeUnixNano": str(len(out)),
                        "attributes": {"session.id": "case-%d" % case["id"], "gen_ai.operation.name": "chat",
                                       "gen_ai.input.messages": list(hist),
                                       "gen_ai.output.messages": [{"role": A, "content": text}]}})
        hist = hist + [{"role": role, "content": text}]
    return out
