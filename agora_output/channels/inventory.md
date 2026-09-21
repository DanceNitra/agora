# Channel inventory, measured 2026-09-21

Access: "Chrome" means the Claude in Chrome extension reaches the site logged in as the owner
and can post. "API" means read-only through an app credential. "blocked" means the harness
refuses the domain in both browsers.

| channel | handle | reach | audience | content today | access |
|---|---|---|---|---|---|
| LinkedIn | Rastislav Drahos | Agora, inspeximus, podcast | (profile) | posts, comments, DMs; ledger since 09-18 | Chrome, posts by me after "ok" |
| Reddit | u/Danculus | Agora, inspeximus | karma 27 link / 9 comment | 24 posts (17 r/Rag), 95 comments | API read; blocked in browsers; owner pastes |
| X | @Dance_NR | DANCHI | 8 followers, 42 following | 117 posts, last 09-18 (music) | Chrome |
| Bluesky | @danchinitra.bsky.social | DANCHI | 0 followers, 1 following | 6 posts, all music, last 09-19 | Chrome |
| Instagram | danchinitra | DANCHI | 86 followers, 103 following | 60 posts | Chrome (posting needs image; test) |
| Facebook | rastislav.drahos (Danchi) | personal + DANCHI | 178 followers, 158 following | personal page, 1 unread notification | Chrome |
| YouTube | @Danchinitra | DANCHI | 180 subscribers | 20 videos | Chrome (comments; uploads via Studio, test) |
| TikTok | @danchinitra | DANCHI | 126 followers, 200 likes, 799 following | (videos, count not read) | Chrome (video upload, test) |
| Spotify | Echoes of Tomorrow show, DANCHI artist | podcast, music | (not read) | episodes, tracks | links only |

Sites (all HTTP 200 on 2026-09-21): dancenitra.github.io (root, robots, sitemaps), /agora, /inspeximus, /ramr, /danchi.

Observations:
- Two audiences, one person: Agora/inspeximus (LinkedIn, Reddit) and DANCHI (X, Bluesky, IG, FB, YT, TikTok).
  X and Bluesky carry only music today; the Agora work has no presence there.
- X 8 followers and Bluesky 0 followers: these are new or dormant; a post there reaches nobody yet.
- Reddit is the only channel where I cannot act in the browser.
- Ledger: agora_output/linkedin/ledger.jsonl already carries a channel field (linkedin 14, reddit 3).
