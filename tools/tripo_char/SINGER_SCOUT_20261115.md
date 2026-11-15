# Singer scout for the acting database (2026-11-15)

Owner, 2026-11-15: "najdi mi ty zoznam ty 10 najlepsich sprav si deepdajv a hladaj prave starsie veci pretoze tam
ludia prezivali emotivne veci najlepsie".

Method: 56 YouTube uploads from 36 searches for older live performances, each fetched at 360p and measured with
`perf_clip_pick.py` (face found, |yaw| and |pitch| under 25 degrees, inner eye distance at least 3 % of the width, no
shot cut). "Run" is the longest continuous usable stretch. Measurements and contact sheets:
`reports/yuki_lipsync/scout/` (`scout_summary.json`, `sheet_round1.jpg`, `sheet_round2.jpg`). Private tests only;
never published.

## The 10

| # | singer, song, year | intent | run (s) | starts at | link | notes |
|---|---|---|---|---|---|---|
| 1 | Jacques Brel, Ne me quitte pas, TV 1966 | prosi, zufalo | 125.5 | 0.6 | https://www.youtube.com/watch?v=n0ehZeWGXW0 | extreme close-up, sweat on the face, eyes closed; 360p at most |
| 2 | Billie Holiday, Strange Fruit, 1959 | svedci, potlaca hrozu | 55.7 | 125.3 | https://www.youtube.com/watch?v=-DGY9HvChXk | close-up, frontal |
| 3 | Yamaguchi Momoe, Sayonara no mukougawa, farewell 1980 | lucí sa, zadrziava plac | 104.9 | 15.8 | https://www.youtube.com/watch?v=6O6RwXldILI | cries on stage; burned-in subtitles; 480p. Clean alternative without subtitles: w_mYonnLBKE (85 s) |
| 4 | Misora Hibari, Kanashii Sake, TV 1985 | smuti, plac | 17.0 | 87.4 | https://www.youtube.com/watch?v=XnVC7-Lrde4 | real tears on screen; enka, microphone under the chin |
| 5 | Louis Armstrong, What a Wonderful World, BBC | teší sa, daruje | 25.0 | 109.2 | https://www.youtube.com/watch?v=CaCSuzR4DwM | laughter, wide eyes |
| 6 | Barbra Streisand, People, 1965 | odhaluje sa, dufa | 29.1 | 117.1 | https://www.youtube.com/watch?v=7i8jfm3BUJQ | frontal close-up; live or playback not verified |
| 7 | Nina Simone, Ne me quitte pas, 1967 | prosi potichu | 21.1 | 30.5 | https://www.youtube.com/watch?v=t-9w8GLGnQE | same song as #1: two singers, one song, for the persona profile |
| 8 | Charles Aznavour, Comme ils disent, INA | obhajuje sa, tichá bolest | 27.2 | 104.0 | https://www.youtube.com/watch?v=WWapuMHMKRw | close-up |
| 9 | Edith Piaf, Non, je ne regrette rien, INA | vzdoruje | 24.1 | 88.0 | https://www.youtube.com/watch?v=muXYs_5RarI | small face (3.9 %), dark |
| 10 | Janis Joplin, Summertime, Frankfurt 1969 | vybuch, bolest | 16.3 | 180.3 | https://www.youtube.com/watch?v=reAZI4cjo3w | the only measurable explosion; 356p |

Alternates: Dalida, Je suis malade, 1978 (AHv28NenQdQ, 23 s, small face); Nina Simone, Mississippi Goddam (anger,
ghhaREDM3X8, 16.6 s, small face at the piano); Momoe w_mYonnLBKE (85 s).

## Rejected by measurement

Under 15 s of continuous usable face: Janis Joplin Ball and Chain and Cry Baby, Otis Redding (both songs), Joe Cocker
(both), Aretha Franklin (both), Elvis If I Can Dream, Judy Garland, Mahalia Jackson, Roy Orbison, Marta Kubisova,
Chiaki Naomi, Amalia Rodrigues, Brel Amsterdam. Old rock footage cuts every few seconds and the singers move out of
frontal view.

Not a performance: two Misora Hibari uploads (47K0NLyE5sk, 7Cj8mtSqbYc) are still photos with audio (blendshape
spread 0.002). Linda Ronstadt and Aretha Franklin sing with the microphone at the lips. Hana Hegerova, Lasko
prokleta (1968) is a staged film clip, very likely playback.

## Defect found and fixed on the way

`perf_clip_pick.py` sized its window in samples as if it sampled at 10 Hz. It samples every round(fps / 10) frames,
so a 25 fps source runs at 12.5 Hz and a 24 fps source at 12 Hz: a "60 s" window was 48 to 50 s long. The window now
uses the real sample rate. The Sinead minute started at the right second, so its result stands.
