# Action plan - from "gig prepped" to first paying client

Everything on the build side is done: a working support agent that won't hallucinate
(`services/support_agent/`), a real Reliability Receipt from a live deployment
(`services/support_agent/reliability_receipt_2026-06-16.md`), and a paste-ready gig
(`services/gig_support_agent_with_receipt.md`). What's left is the part only YOU can do:
put it in front of real buyers. This is that list, in order.

**The one number that matters:** ~40 conversations / ~20 proposals -> first paid gig in ~2 weeks
(realistic). So the whole game is volume of real touches. Everything below serves that.

---

## Phase 0 - Decide (15 min, do today)
- [ ] **Name/handle** you'll trade under (e.g. your name, or a simple brand). Used on Fiverr + Upwork.
- [ ] **Payout method.** In Slovakia: a bank account works on Upwork; Fiverr pays via Payoneer (free) or bank. Set this up first - you can't get paid without it.
- [ ] **Starting prices:** keep them LOW for the first ~3 sales to win reviews (Basic ~EUR45). Raise after 3-5 reviews. The money is the EUR90/mo care plan, not the one-off.
- [ ] **First channel** (pick one to start, recommended order below). Don't try all three at once.

## Phase 1 - Set up the two accounts (1-2 hrs)
- [ ] **Fiverr seller account:** verify ID, connect payout, add a photo, paste the profile bio from `services/GIGS.md` ("Profile blurb"). 
- [ ] **Upwork freelancer account:** fill the profile, add AI/automation skills, aim "Rising Talent". Connect payout.
- [ ] Add **portfolio items**: the support-agent demo + the Reliability Receipt + a screenshot of Agora.

## Phase 2 - Make the 3 proof assets (2-3 hrs) - THIS is what gates launch
1. [ ] **60-sec demo video** (screen recording). Script:
   - Ask the agent: *"What time do you open on Sunday and do you have oat milk?"* -> it answers correctly from the content.
   - Ask: *"Can you ship coffee beans to Prague?"* -> it says it's not sure and offers a human. **Say on camera: "It did NOT invent a policy - that's the point."**
   - (Run `python services/support_agent/support_agent.py` for these.)
2. [ ] **Screenshot the Reliability Receipt** (`reliability_receipt_2026-06-16.md`) - this is your differentiator. Caption: "Every client gets this monthly."
3. [ ] **Screenshot Agora running** (the 3D dungeon at http://localhost:5174 or a brain dashboard) - proof you build real agent systems.

## Phase 3 - Post the gig (1 hr)
- [ ] On Fiverr, create **Gig 1** by pasting title / description / 3 tiers / FAQ / image text straight from `services/gig_support_agent_with_receipt.md`. Publish.
- [ ] Add the 3 assets from Phase 2 as the gig images/video.
- [ ] (Later, once Gig 1 is live: post Gigs 2 and 3 from `GIGS.md`.)

## Phase 4 - Get leads (daily, this is the real work)
Pick the channel(s). Recommended for the FIRST client, in order of conversion:
- [ ] **A. Direct local outreach (warmest - do this first).** Email/DM 5-10 small Bratislava businesses with a website (cafes, clinics, gyms, shops, law/real-estate offices). Offer a **free demo built on their own content**. This converts fastest for a first client because it's personal and they see it work on THEIR stuff. (Tell me a business + their site and I'll build the demo same-day.)
- [ ] **B. Upwork (steady pipeline).** Apply to **5 AI-agent / chatbot / customer-support jobs per day** using the proposal template in the gig file. Paste me each job post -> I write the tailored proposal in 2 min.
- [ ] **C. Fiverr (passive once posted).** Share your gig where buyers look: r/forhire, indie-hacker / small-biz communities, LinkedIn. First impressions are slow; treat it as background.

## Phase 5 - Land + deliver the first client
- [ ] When someone bites: get their **content** (FAQ, site URL, docs) -> send it to me.
- [ ] I build the grounded agent on their content + wire the receipt; you review and ship it to them.
- [ ] **On delivery, pitch the care plan:** *"Your agent is live. For EUR90/mo I keep it accurate as your info changes and email you a monthly reliability report so you know it's working."* -> recurring income.
- [ ] Ask for a review. Repeat. After 3-5 reviews, raise prices.

---

## Division of labor
**You (only you can):** create accounts + verify ID, set up payout, record the demo video, post the gig, hit "send" on outreach/proposals, talk to the client, get paid.
**Me (say the word, any time):** tailor each Upwork proposal to a specific job, write the local-business outreach emails, build the agent on a real client's content, generate their receipt, adjust pricing/copy.

## This week (minimum viable launch)
1. Phase 0 + Phase 1 (accounts + payout). 2. Phase 2 (3 assets). 3. Post Fiverr gig.
4. Send 5 local-business outreach emails (I'll write them) **and** 5 Upwork proposals/day (I'll tailor them).
That's the whole path. The build is done; this is execution and volume.
