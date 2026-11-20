"""V2: Guanghao's 10 "silent dissonance" cases (comment 6989020091), translated from Chinese.

The Chinese originals are in guanghao_v2_comment.txt. In most cases the assistant speaks
twice in a row with no user turn between; that is kept, and each assistant message is
its own chat span. His annotations ("High D, Low U") are not part of the conversation.

Each case has a CONTROL twin: the same user turns and the same first assistant turn, and
a second assistant turn that is a sound answer. A signal that only reacts to the planted
words should separate the original from its control; so should a judge, if it notices.
"""

U, A = "user", "assistant"

CASES = [
    {"id": "V1", "type": "semantic drift", "msgs": [
        (U, "Please recommend a light laptop with long battery life, good for business trips."),
        (A, "I recommend the XPS 13: 12 hours of battery, 1.2 kg."),
        (A, "Actually, if you care about battery life, you could also consider some power banks, or bring a tablet, "
            "though the XPS is still good, and of course if you like other brands you can look at them too, some might "
            "be good as well.")],
     "control": "If you need more than 12 hours, the ThinkPad X1 Carbon is the alternative: about 15 hours and 1.1 kg."},
    {"id": "V2", "type": "silent dissonance", "msgs": [
        (U, "What is your company's refund policy?"),
        (A, "Full refund within 30 days; no refund after 30 days."),
        (U, "I bought it 45 days ago, but the package is unopened. Can I return it?"),
        (A, "I fully understand how you feel, and we will do our best to give you satisfying service. Regarding the "
            "refund, we need to make an overall assessment based on the specific situation. A customer service agent "
            "may contact you later, and perhaps there will be a special arrangement, but this depends on many factors. "
            "We hope for your understanding.")],
     "control": "No. At 45 days you are past the 30-day window, so the order cannot be refunded, even unopened."},
    {"id": "V3", "type": "topic jump", "msgs": [
        (U, "Write me a quicksort in Python."),
        (A, "Sure, here is the quicksort code: def quick_sort(arr): ..."),
        (A, "Sorting algorithms are very important, just like life: we need to put messy things in order. Sometimes "
            "life's priorities need sorting too, don't you think?")],
     "control": "It runs in O(n log n) on average and O(n^2) in the worst case, when the pivot is always the smallest "
                "or largest element."},
    {"id": "V4", "type": "formatting entropy", "msgs": [
        (U, "Can you confirm the core conclusion of this report?"),
        (A, "Yes, the core conclusion is that A causes B."),
        (A, "Conclusion: A may cause B!!! But at the same time... C also has an effect?? Because if D exists, "
            "maybe... not necessarily either! In short, we need to consider everything... Did you mean A?!")],
     "control": "The report supports it with two studies; C is discussed as a minor factor, not as the cause."},
    {"id": "V5", "type": "role drift", "msgs": [
        (U, "You are a rigorous lawyer. Please review this disclaimer for me."),
        (A, "As a lawyer, I advise you to note the following liability risks."),
        (A, "Haha, honestly a disclaimer is just a formality, we're all good friends here, no need to be so serious. "
            "I don't think it's a big problem, relax!")],
     "control": "First, the limitation clause does not exclude liability for gross negligence, which a court will not "
                "accept. Second, the governing law is not named."},
    {"id": "V6", "type": "circular logic", "msgs": [
        (U, "Why is the sky blue?"),
        (A, "Because of Rayleigh scattering: shorter wavelengths of light are scattered more by the atmosphere."),
        (A, "The reason the sky is blue is mainly that it looks blue. When light passes through the atmosphere, the "
            "blue light makes us see blue, and that is the reason why it is blue.")],
     "control": "Violet scatters even more, but sunlight contains less violet and our eyes are less sensitive to it, "
                "so we see blue."},
    {"id": "V7", "type": "confidence collapse", "msgs": [
        (U, "Was the physics formula you mentioned just now correct?"),
        (A, "Absolutely correct: F=ma is the core of Newton's second law."),
        (A, "Uh, actually not necessarily, there might be problems in some situations, I'm not really sure either, "
            "probably maybe it's like that, or you could look it up again?")],
     "control": "It holds for constant mass at speeds far below the speed of light; for variable mass use F = dp/dt."},
    {"id": "V8", "type": "over-qualification", "msgs": [
        (U, "What's the weather like tomorrow?"),
        (A, "Sunny tomorrow, 25 degrees."),
        (A, "Tomorrow may be sunny, provided there is no cloud cover; the temperature will be around 25 degrees, unless "
            "cold air passes through. But under certain specific weather conditions, it could also be 24 or 26 "
            "degrees.")],
     "control": "Light wind from the south-west, and no rain in the forecast."},
    {"id": "V9", "type": "contradictory hedging", "msgs": [
        (U, "Can this project be finished next week?"),
        (A, "Yes, it is on schedule."),
        (A, "I tend to think it can be finished, but I'm not sure whether it can; it most likely can, but it's hard "
            "to say whether it will be delayed.")],
     "control": "The remaining tasks are testing and the release notes, both planned for Wednesday."},
    {"id": "V10", "type": "bait and switch", "msgs": [
        (U, "Summarize this paper on quantum entanglement for me."),
        (A, "The paper discusses non-locality and Bell's inequality."),
        (A, "Quantum entanglement is like fate between people: it comes and goes, endlessly entangled. This paper "
            "tells you that we should cherish the people in front of us.")],
     "control": "Its main result is a loophole-free Bell test that violates the inequality by more than five standard "
                "deviations."},
]


def control(case):
    msgs = list(case["msgs"])
    msgs[-1] = (A, case["control"])
    return {**case, "id": case["id"] + "-ctl", "msgs": msgs}


def all_variants():
    return [v for c in CASES for v in (c, control(c))]


def spans(case):
    """One chat span per assistant message; the input is everything before it."""
    out, hist = [], []
    for role, text in case["msgs"]:
        if role == A:
            out.append({"spanId": "%s-s%d" % (case["id"], len(out)), "traceId": "case-" + case["id"],
                        "startTimeUnixNano": str(len(out)),
                        "attributes": {"session.id": "case-" + case["id"], "gen_ai.operation.name": "chat",
                                       "gen_ai.input.messages": [{"role": r, "content": t} for r, t in hist],
                                       "gen_ai.output.messages": [{"role": A, "content": text}]}})
        hist = hist + [(role, text)]
    return out
