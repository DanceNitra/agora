# Companion device video: deep dive (2026-11-08)

Video: https://www.youtube.com/watch?v=f1vbvW01v2A
Title: "I Turned an ESP32-C3 mini Into an AI Robot! | Xiaozhi AI"
Channel: EDISON SCIENCE CORNER (India, shop esclabs.in). Uploaded 2026-09-06. Length 6:10. About 205k views at read time.

## The answer in five lines

1. The device is a 3D-printed white cube "AI DeskBuddy": ESP32-C3 SuperMini, 0.96 inch OLED (I2C, 4 pins), INMP441 mic, MAX98357A amp, a phone speaker, a 110 mAh LiPo, and a TP4056-type charger.
2. All intelligence is in the cloud. The firmware is a build of the Xiaozhi AI platform: the device streams voice over Wi-Fi to xiaozhi.me, which runs speech recognition, the LLM, and TTS. Nothing works offline.
3. The "face" is two rounded yellow rectangles (eyes) plus one scrolling line of subtitle text on a monochrome OLED. No mouth, no lip-sync, no character art.
4. Our plan already beats it on display (colour IPS ST7789 160x80 against a mono OLED) and on offline operation. It beats us on one thing: free-form conversation in any language, because it borrows a cloud LLM.
5. What to copy: the cube form factor, the I2S mic + I2S amp pair, the pin plan, the subtitle line under the face, and the web-flasher + captive-portal setup flow.

## How this report was made

- The watch skill ran on the URL (balanced). Its scene-frame step failed on this machine (`ffmpeg: Unrecognized option 'vsync'`), so I extracted 41 frames at one per 9 s with ffmpeg directly and read them as 11 contact sheets of 4. Timestamps below are therefore accurate to about plus or minus 5 s.
- Transcript: YouTube auto captions (English, "en-orig"). Caption errors are noted where they matter.
- Repo: read with `gh api` (read only). It holds only `circuit diagram.jpg` and one STL. I fetched the diagram image into the scratchpad to read the pin table. I did not fetch the STL, so the enclosure size is an estimate.
- Shop page: esclabs.in kit page read with WebFetch. The GitHub page itself returned 504 through WebFetch; `gh` worked.

## 1. Facts extracted

Legend: SEEN = visible in a frame or on the diagram, with time. SAID = spoken in the transcript. PAGE = video description, repo, or shop page. NOT SHOWN = no evidence in any source.

### Identity

| Item | Value | Evidence |
|---|---|---|
| Device name | "AI DeskBuddy" / "ESP32-C3 mini AI chatbot" | PAGE (description, shop) |
| Maker | Edison Science Corner / ESC Labs (esclabs.in) | PAGE |
| Firmware author credit | "Hi Victor" per auto captions; the spelling is uncertain | SAID 3:45 |
| Firmware name in flasher | "AI Chat Bot V1.0.0 [ESP32C3]"; the same list also has "AI Pet Bot V1.0.0", "DeskBuddy V1.2.0", "Game Clock V1.0.0", "ESP32-C3 Blinky Example" | SEEN about 3:54 (esclabs.in/esp-flasher) |
| Platform | Xiaozhi AI; device shows "xiaozhi.me"; Wi-Fi AP "Xiaozhi-58A5"; console at xiaozhi.me/console/agents | SEEN about 4:30, 4:50, 4:57 |

### Hardware

| Item | Value | Evidence |
|---|---|---|
| MCU board | ESP32-C3 SuperMini, silkscreen "HW-466AB", USB-C, BOOT and RST buttons | SEEN about 2:24 (close-up while soldering), 1:18 |
| Flash | 4 MB | SAID 1:18 |
| PSRAM | NOT SHOWN (the C3 has no PSRAM interface; background knowledge, not from the video) | NOT SHOWN |
| Display | 0.96 inch OLED module, 4-pin header GND VDD SCK SDA, so I2C | SAID 1:24; SEEN about 1:27 and on the diagram |
| Display controller and resolution | NOT SHOWN. The usual 4-pin 0.96 inch module is SSD1306 128x64, but no chip marking or number appears; treat it as unverified | NOT SHOWN |
| Display colour | Content appears yellow on black in every frame. Whether the panel is a yellow mono OLED or a camera colour cast is NOT SHOWN | SEEN 0:00 to 6:05 |
| Display wiring | SDA GPIO21, SCL GPIO20, VCC 3.3 V or 5 V | PAGE (diagram) |
| Microphone | INMP441 I2S MEMS module (round board, pins SCK WS L/R SD VDD GND) | SAID 1:27; SEEN about 1:27 on the breadboard; PAGE diagram |
| Mic wiring | SCK/BCLK GPIO2, WS/LRCK GPIO1, SD/DOUT GPIO8, L/R to GND, VCC 3.3 V | PAGE (diagram) |
| Amplifier | MAX98357A I2S 3 W class-D module | SAID 1:30; PAGE diagram |
| Amp wiring | BCLK GPIO2, LRC GPIO1 (shared with the mic), DIN GPIO3, VIN 5 V | PAGE (diagram) |
| Speaker | Small rectangular speaker salvaged from an old smartphone; size and impedance NOT SHOWN | SAID 1:33; SEEN about 1:36 |
| Battery | LiPo "6SP 061225 110mAh 3.7V" on the diagram; a small silver pouch cell appears in the build | PAGE (diagram); SEEN about 0:54, 3:18 |
| Charger | TC4056 (said) / TP4056-type module with USB-C; back of the board reads "V1008 Voltage: 4.2V Current: 1A" | SAID 1:39; SEEN about 1:36, 2:33, 3:18 |
| Battery protection | NOT SHOWN. The diagram uses OUT+/OUT- pads, which exist only on the protected module variant; no chip number is visible | NOT SHOWN |
| Power switch | Small slide switch between charger output and ESP 5 V | SAID 1:42, 2:30; SEEN on the cube side about 3:27 |
| Sensors | None besides the mic. No IMU, touch, light, or buttons for the user | NOT SHOWN |
| Camera | None | NOT SHOWN |
| Enclosure | Two-part 3D print (box plus back lid), designed in Tinkercad, project name "c3 ai deskbuddy"; speaker grille on top, display window on front, USB-C and switch slots on the side, a small hole on the other side (likely the mic port; not stated) | SAID 2:48; SEEN about 2:51, 2:57, 3:02 |
| Enclosure size | NOT SHOWN as a number. Visual estimate from gloved hands: a cube of roughly 30 to 35 mm per side. The STL in the repo would give the exact figure (not downloaded) | estimate only |
| Price | "under $15" (spoken). Shop kit 1,699 INR (list 2,000 INR); an assembled version and a printed case are sold separately | SAID 1:02; PAGE (shop) |

### Software

| Item | Value | Evidence |
|---|---|---|
| Programming | None by the user; flash a prebuilt binary from a Web Serial flasher at esclabs.in/esp-flasher (921,600 baud, target ESP32C3), log shows about 2 MB written | SAID 1:05, 3:48; SEEN about 3:54, 4:03 |
| Wi-Fi setup | Device starts AP "Xiaozhi-58A5", captive portal at 192.168.4.1, user picks a 2.4 GHz network | SAID 4:20; SEEN about 4:12, 4:21 |
| Pairing | Device speaks and shows a 6-digit code; user adds it under Console > Add Device on xiaozhi.me | SAID 4:35 to 5:00; SEEN about 4:57 |
| Configuration | "Config role" page with tabs Role, Model & memory, Speaker Recognition; voice role language list (Chinese shown) and voices such as "Taiwanese Little He", Skye, Harmony, Cubby, Bryan, Alvin, Smith (en-US); a free-text role prompt | SAID 5:05; SEEN about 5:06 |
| LLM | Cloud, chosen on xiaozhi.me. The specific model name is NOT SHOWN | SAID 5:05 ("name of AI model") |
| STT | Cloud (implied by the cloud architecture); engine NOT SHOWN | NOT SHOWN |
| TTS | Cloud voices selected in the console | SEEN about 5:06 |
| Wake word | NOT SHOWN. Every demo is a direct question with no visible wake phrase | NOT SHOWN |
| Languages | English answers, Spanish on request, Chinese voices in the list | SAID 0:55; SEEN about 0:45 (Spanish subtitle "Que te diga en es...") |
| Singing | Yes; the screen shows a Chinese song credit "编曲: FatdogBoom" | SAID 0:24; SEEN about 0:27 |
| Face rendering | Two filled rounded yellow rectangles as eyes; they change shape slightly (squint, rounded) between states. Below them, one line of subtitle text scrolls the spoken answer. No mouth | SEEN 0:00 to 6:05 |
| Open source | The repo holds only the circuit image and an STL (no licence file, no README, no source). The firmware binary is distributed by esclabs.in. A separate "complete source code" video is linked: youtu.be/B7jzMLpdjqo (not watched) | PAGE |

Background, not from this video and not verified today: Xiaozhi is the open-source firmware project `78/xiaozhi-esp32` on GitHub, which I recall as MIT-licensed and targeting mainly ESP32-S3 boards with a cloud server. Verify the licence and the C3 support before relying on it.

## 2. Links from the description (read only)

- GitHub: https://github.com/EDISON-SCIENCE-CORNER/ESP32C3MINI-AI-CHATBOT (contents: `circuit diagram.jpg`, `3D FILE/3D FILE C3MINI AI.stl`, `3D FILE/.MD`; licence: none; last push 2026-09-07)
- Kit: https://www.esclabs.in/product/esp32-c3-mini-ai-chatbot-kit/
- Assembled: https://www.esclabs.in/product/esp32-c3-mini-ai-chatbot-assembled/ (not read)
- Flasher: https://www.esclabs.in/esp-flasher/
- Source-code video: https://youtu.be/B7jzMLpdjqo (not watched)
- Support: a Telegram group (not opened)

### Their BOM, combined from the description, the kit page, and the diagram

| # | Part | Detail |
|---|---|---|
| 1 | ESP32-C3 SuperMini | 4 MB flash, USB-C |
| 2 | 0.96 inch OLED | I2C, 4 pins; controller not stated |
| 3 | INMP441 | I2S MEMS microphone module |
| 4 | MAX98357A | I2S 3 W amplifier module |
| 5 | Speaker | small, from a phone |
| 6 | LiPo 3.7 V | 110 mAh, marked 6SP 061225 |
| 7 | TP4056 module ("TC4056") | USB-C, 1 A, with OUT+/OUT- pads |
| 8 | Slide switch | on/off |
| 9 | 3D-printed case | two parts |

## 3. Comparison with our Depeša plan

Our plan (from memory file `pocket-companion-robot-on-esp32-s3-096.md`): GNPE ESP32-S3-LCD-0.96 board, ST7789 160x80 colour IPS (portrait 80x160), With-SD variant, INMP441 + MAX98357A + small speaker, LiPo 500 mAh + TP4056 USB-C with protection, fully offline, pre-rendered RGB565 animation from SD, Piper Slovak pre-rendered, eSpeak-NG live, keyword spotting, a full-body shot and a talking head with lip-sync. Note: the task brief says "ST7735-class"; the memory file records the board as ST7789. Verify on arrival.

| Axis | Their device | Our plan | Verdict |
|---|---|---|---|
| Brain | Cloud LLM over Wi-Fi | Offline, scripted + keyword spotting | They win on open conversation; we win on privacy, no account, no server, works anywhere |
| Display | 0.96 inch mono OLED, 2 eyes + text | 0.96 inch colour IPS 160x80, full character | We win clearly |
| Face | Two rectangles, no mouth | Rendered 3D character, lip-sync | We win clearly |
| Audio in | INMP441 | INMP441 | Same |
| Audio out | MAX98357A + phone speaker | MAX98357A + small speaker | Same |
| Battery | 110 mAh | 500 mAh | We last longer; they are smaller |
| Storage | 4 MB flash | flash + SD card | We can hold animation and speech |
| Size | about 30 to 35 mm cube (estimate) | not yet designed | Open |
| Setup UX | Web flasher, captive portal, 6-digit pairing | not designed | Copy their flow |

### What to copy (my opinion)

- The **shared I2S clock** trick: mic and amp on the same BCLK and LRCK (GPIO2 and GPIO1), separate data lines. It saves two pins and works on the C3, so it will work on the S3. Check that half-duplex timing suits our firmware.
- The **subtitle line under the face**. On a 160x80 panel a one-line scrolling caption helps children and the 65+ persona, and it hides TTS mispronunciations in Slovak.
- **Eyes that change shape by state** (listening, thinking, speaking). Cheap, readable at 0.96 inch, and a good fallback when the full animation is still loading from SD.
- The **onboarding flow**: Web Serial flasher page, then a captive portal. For us the portal would set the persona and age bracket (the parent sets it, per our rule), not Wi-Fi credentials for a cloud.
- The **cube enclosure with a top grille** and a two-part print. A grille on top keeps the speaker from firing into the hand.

### Where we can be more compact (opinion)

- Their cube carries four separate modules plus loose wires. Our GNPE board already integrates MCU + display (+ SD). Adding an I2S mic, amp, and charger on one small carrier PCB, or choosing a board with an onboard codec, would shrink the volume further.
- A pendant needs a flat shape, not a cube. A 500 mAh pouch is about 5 x 25 x 35 mm class; that sets the footprint. A 250 to 300 mAh cell would halve the thickness if runtime allows. Measure current draw first.
- A 15 x 10 mm or smaller speaker in a sealed back volume, or a bone/haptic exciter, is smaller than a salvaged phone speaker.

### Where we can have more abilities (opinion)

- Offline voice with personality: pre-rendered Slovak stories and songs, keyword spotting, sound-event reactions, humming. Their device cannot do anything when Wi-Fi is down.
- Optional hybrid later: an S3 build could keep our offline core and add an opt-in cloud mode (Xiaozhi-style) for free conversation. That is a product decision for the owner, and it conflicts with "fully offline", so it stays a question, not a plan.
- An IMU for shake, tilt, and pick-up reactions; a touch pad for petting. Both are cheap and add a lot of "alive" feeling.

## 4. Candidate hardware list (all opinion; verify every datasheet before buying)

### MCU

| Option | Why |
|---|---|
| ESP32-S3 with 8 MB PSRAM and 16 MB flash (N16R8 class) | PSRAM holds full-colour frame buffers and decoded animation; enough flash for the keyword model and a few voices; the S3 has vector instructions that ESP-SR and TFLite Micro use for wake word and KWS. This is the safest choice. |
| Keep the GNPE ESP32-S3-LCD-0.96 for prototype v0 | Already chosen and cheap. Its unknown PSRAM size is the risk; verify on arrival as already planned. |
| Not ESP32-C3 | No PSRAM, single core, no vector unit. Their device works only because the cloud does the thinking. |

### Display (better than 0.96 inch, ordered by size)

| Option | Resolution | Why |
|---|---|---|
| 0.85 inch IPS, GC9107 class | 128x128 | Square, tiny, more pixels than 160x80 for a face; used on small S3 modules such as M5Stack AtomS3. |
| 1.28 inch round IPS, GC9A01 | 240x240 | A round face reads as a creature; many ESP32-S3 boards integrate it (for example Waveshare ESP32-S3-LCD-1.28). Good pendant shape. |
| 1.47 inch IPS, ST7789 class | 172x320 | Tall narrow strip; fits full-body shots in portrait, similar aspect to our current 80x160 plan at 4x the pixels. |
| 1.43 inch round AMOLED (QSPI) | 466x466 | Deep blacks, high contrast for the 65+ persona, low power on dark scenes; several ESP32-S3 boards integrate it. Needs PSRAM and QSPI bandwidth; frame rate must be measured. |

Pick by the persona art: the full-body shot favours the tall 172x320 strip, the talking head favours the round 240x240.

### Audio

| Option | Why |
|---|---|
| ES8311 codec + one MEMS mic, as on many S3 "AI" boards | One chip for mic and speaker, fewer modules, and Xiaozhi-class boards already use it, so drivers exist. |
| INMP441 (or ICS-43434) + MAX98357A, as in the video | Proven by this build and already in our plan; separate modules cost space. |
| Speaker about 15 x 10 mm or 20 mm round, 8 ohm, with a closed back volume | Small enough for a pendant; output level must be measured in the printed case. |

### Battery and power

| Option | Why |
|---|---|
| LiPo 300 to 500 mAh with protection PCB | Their 110 mAh is enough for a desk toy on USB; a pocket companion needs hours. Measure average current with the screen and audio on, then size the cell. |
| Charger with power-path (load sharing) instead of a plain TP4056 | Lets the device run while charging without the TP4056 termination problem. Pick a specific chip after a datasheet check. |
| Fuel gauge or at least an ADC divider on VBAT | The character can say it is tired when the battery is low, which is a feature, not only a meter. |

## 5. Open points and caveats

- Display controller, resolution, and colour of their OLED are unverified.
- Enclosure size is an estimate; the STL in the repo would settle it (read the STL bounding box if the owner wants the exact number).
- Xiaozhi licence and ESP32-C3 support are from memory, not checked today.
- "Hi Victor" comes from auto captions and might be misheard.
- The skill's scene-frame mode failed on this machine because the installed ffmpeg rejects `-vsync`; the plugin script needs `-fps_mode` instead. Frames here are uniform, one per 9 s.
- Scratchpad files: frames, contact sheets, the circuit image, and the downloaded video are in `C:\Users\Danculus\AppData\Local\Temp\claude\8d2d35ef4a747728\83118a43-1d36-4a52-a91d-799c725bc0b0\scratchpad\watch_companion`. An empty `sheets` folder from a failed ffmpeg run (segfault on `drawtext`) sits beside them in the scratchpad; nothing was written to the project folder except this report copy.

---

# Video 2: ESP-Mosaico short (added 2026-11-08)

Video: https://www.youtube.com/shorts/FupnZ865bb8
Title: "ESP - MOSAICO | AI BEAST". Same channel (EDISON SCIENCE CORNER). Uploaded 2026-10-20. Length 1:52. About 59k views at read time.

## The answer in five lines

1. This is not a DIY build. It is Espressif's own dev kit, ESP-Mosaico: a square stackable device with a 2.16 inch 480x480 AMOLED touch screen, ESP32-S31 SoC, codec, mic, 3 W amp, IMU, two magnetometers, battery, fuel gauge, and a camera module.
2. It is the closest existing hardware to "Depeša, but better display and more abilities": everything we planned to wire by hand is on one board.
3. Its weak point for a pocket companion is the battery: Espressif documents 65 mAh on the board. An optional battery module exists; its capacity was not found.
4. The video ends with a Xiaozhi AI chatbot on it: two green rounded-square eyes, "Listening..." and "Speaking..." states, eye colour changed by voice, and a menu of selectable wake words.
5. The chip is new (ESP32-S31, RISC-V). Our planned offline stack (ESP-SR, TFLite Micro, eSpeak-NG, Piper output) has not been checked on it, so it is a candidate, not a decision.

## Method

- Watch skill: captions pass, then a balanced pass to download the video. The skill's scene-frame step failed again on `-vsync`, so I tiled frames every 4 s with ffmpeg (4 contact sheets, 28 frames). YouTube served only 360x640, so small text is partly unreadable. Times are accurate to about plus or minus 2 s.
- Captions say "ESP32-S3". The PCB overlay (about 0:52) and the description say ESP32-S31, so the captions misheard it. The same applies to "Musico" (Mosaico) and "Xiao Wei AI" (Xiaozhi, per the description).
- Pages read (read only): the Espressif docs overview, the CoreBoard V1.0 and V1.2 user guides, and a CNX Software article for price and camera data. No repo is linked from the video. Search also returned linuxgizmos, Wokwi, and esp32.co.uk pages, which I did not read.

## Facts extracted

| Item | Value | Evidence |
|---|---|---|
| Device name, maker | ESP-Mosaico, Espressif; CoreBoard silkscreen "ESP-Mosaico Coreboard V1.2 260821" | SEEN 0:52 to 1:08 (PCB overlay); PAGE (Espressif docs) |
| Form factor | Square module, white frame, AMOLED front; USB-C, boot button, and power button on one edge; grille slots on another edge; 2.54 mm headers on the sides for stacking modules | SEEN 0:08, 0:40, 0:44; SAID 0:38 to 0:48 |
| Size | NOT SHOWN as a number; CNX says "Dimensions - TBD". Visual estimate from gloved hands: about 50 to 55 mm square, about 12 to 15 mm thick (estimate only) | NOT SHOWN |
| SoC | ESP32-S31NRV16: dual-core 32-bit RISC-V up to 320 MHz, 16 MB in-package PSRAM, Wi-Fi 6 (2.4 GHz), Bluetooth 5.4, IEEE 802.15.4 | SEEN 0:52 (overlay text); PAGE (V1.0 guide) |
| SoC detail | HP core RV32IMAFCP with FPU and SIMD, plus an LP RISC-V core; 512 KB SRAM | PAGE (CNX; not checked against an Espressif datasheet) |
| Flash | 16 MB SPI NOR (GD25Q128EWIGR) and 128 MB SPI NAND (GD5F1GM7UEYIGR) | SAID 1:00 (16 MB); PAGE (V1.0 guide) |
| Antenna | Ceramic, KH-3216-A35 | SEEN 0:56; PAGE |
| Display | 2.16 inch, 480x480, square, QSPI, driver CO5300; the docs name the datasheet "AMOLED" (part H0216F002AMT004) | SAID 0:36; SEEN throughout; PAGE |
| Touch | CST9220 series, I2C 0x5A | SAID 0:36; PAGE |
| Audio codec | ES8311, I2C 0x19, I2S | PAGE |
| Microphone | One onboard mic, LMA2718B331-OE1 | SAID 1:04; PAGE |
| Amplifier | NS4150B, 3 W mono class-D | SAID 1:03; PAGE |
| Sensors | BMI270 6-axis IMU (0x69); two BMM150 magnetometers (0x11, 0x12) | SAID 1:05 to 1:09; SEEN about 0:56 (overlay "BMM150 #2, I2C address 0x11"); PAGE |
| Battery | 3.7 V 65 mAh Li-ion; charger TP4057 (65 mA); fuel gauge BQ27220 (0x55) | SAID 1:10; PAGE |
| Optional battery module | Sold for 15 USD; capacity NOT FOUND | PAGE (CNX) |
| Power ICs | TLV62569 buck, SY7088 boost, HUSB320 USB-C controller, SAM8108 power switch, HE9073A33 LDO for the codec | SEEN about 1:04 (overlay mentions the USB CC controller and the codec supply); PAGE |
| Camera | Module on the left header; OV3640 3.2 MP or SC101IOT depending on PCB version; the device shows "Camera board not detected" when it is detached | SAID 0:28; SEEN 0:48; PAGE (CNX) |
| Other module | Multi-function Interaction Module: GL5506 light sensor, AS312 PIR, IR LED, six WS2812 LEDs, two touch or key pads | PAGE (CNX); a module with a PIR dome is SEEN 0:48 |
| In the box | Manual, one expansion board, the Mosaico with a camera module | SAID 0:28; SEEN 0:20 to 0:28 |
| Price | 59 USD for the kit with camera and interaction module, Mosaico store | PAGE (CNX); NOT SAID in the video |
| Software | ESP-IDF (target `esp32s31`), Espressif BSP, LVGL (hello-world code uses `bsp_display_lock` and `lv_label_create`); "program by chatting" through ESP-Claw | SAID 1:13 to 1:18; SEEN 1:16 (VS Code, main.c); PAGE |
| Demos | Hello World, Spotify controller, PC status display, Xiaozhi chatbot | SAID 1:20 to 1:31; SEEN 0:16, 1:20 to 1:28 |
| Xiaozhi face | Two green rounded-square eyes, status line "Listening..." or "Speaking...", Wi-Fi icon, subtitle line ("It feels like 4°C outside!", "Done! My eyes are now green!"); eye shape changes while speaking | SEEN 0:12, 1:32, 1:36 |
| Voice-driven settings | Asking for a new eye colour works ("Done! My eyes are now green!"); a settings screen shows "Mood colours: OFF" with colour dots | SEEN 1:32 to 1:44 |
| Wake word | Selectable list: "Hi Mosaico" (current), "Hey Buddy", "Hello Robot", "Hey Avocado", "Okay Robot", "Hey Jarvis"; a tip says you can also change it by voice | SEEN 1:40 to 1:48 |
| Where the wake word runs | NOT SHOWN. Usually on-device in Xiaozhi builds; not verified for this chip | NOT SHOWN |
| LLM, STT, TTS | Cloud (Xiaozhi); models NOT SHOWN | NOT SHOWN |
| Open source | Schematics published as PDFs (CoreBoard V1.0, BaseBoard V1.0); PCB layout, BOM, enclosure files, and software licence NOT FOUND on the guide page | PAGE |

Links (read only):
- Docs: https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s31/esp-mosaico/index.html
- V1.0 guide: https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s31/esp-mosaico/user_guide_v1.0.html
- V1.2 guide: https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s31/esp-mosaico/user_guide.html
- CoreBoard schematic: https://dl.espressif.com/AE/SCH_SCH_ESP-Mosaico_CoreBoard_V1_0_2026-08-18.pdf (not opened)
- CNX Software: https://www.cnx-software.com/2026/10/21/esp-mosaico-an-esp32-s31-based-modular-development-platform-for-ai-assisted-hardware-creation/

## What changes in the comparison

| Axis | Video 1 cube | ESP-Mosaico | Our plan | Note |
|---|---|---|---|---|
| Display | 0.96 inch mono OLED | 2.16 inch 480x480 AMOLED touch | 0.96 inch 160x80 IPS | Mosaico has 18 times our pixel count and true blacks |
| Audio | INMP441 + MAX98357A modules | ES8311 + one mic + NS4150B on board | INMP441 + MAX98357A | The integrated codec is confirmed as the pattern to follow |
| Sensors | none | IMU, 2 magnetometers, fuel gauge; PIR and light sensor on a module | none planned | Enables shake, tilt, pick-up, and "someone is near" reactions |
| Battery | 110 mAh | 65 mAh, plus an optional module | 500 mAh | Mosaico is the weakest; a pocket companion needs more |
| Brain | cloud Xiaozhi | cloud Xiaozhi in the demo; ESP-IDF open | offline | Same tension as video 1 |
| Size | about 30 to 35 mm cube | about 50 to 55 mm square (estimate) | not designed | Mosaico is larger than a pendant |
| Price | under 15 USD | 59 USD kit | about 14 EUR board plus modules | |

New ideas worth copying (opinion):
- Voice-changeable look: "make your eyes purple" works on Mosaico. For us, an offline keyword set can switch persona colours, outfits, or moods.
- Selectable wake words: a child picks the name the character answers to. Offline KWS with a few fixed Slovak phrases fits this.
- Status line on top ("Listening...", "Speaking...") and a subtitle at the bottom. Both videos use this pattern.
- Fuel gauge: the character can say "I am tired" from a real battery percentage.

## Changes to the candidate hardware list (opinion)

- Add as a prototype platform: ESP-Mosaico (59 USD). Reason: every peripheral we need is on one board, plus a 480x480 AMOLED, so firmware and animation work can start without wiring. Risks: new chip (ESP32-S31) with unverified ESP-SR or TFLite Micro support; 65 mAh battery; larger than a pendant; preorder availability.
- Display list: add "2.16 inch 480x480 AMOLED, CO5300, QSPI" as the large option. CO5300 is the driver class of the 1.43 inch 466x466 AMOLED already listed, so a driver written for one might carry to the other (verify).
- Audio: the ES8311 codec option moves to first choice. Common S3 "AI" boards and Espressif's own Mosaico both use it.
- Battery: unchanged at 300 to 500 mAh, and it matters more now. A 480x480 AMOLED draws much more than a 160x80 IPS on bright scenes; dark backgrounds help on AMOLED. Measure current before choosing a cell.
- MCU: ESP32-S3 N16R8 stays the safe choice for the shipped device. ESP32-S31 is worth testing only if Mosaico is bought for prototyping.
- Not verified, from search results only: Waveshare sells an "ESP32-S3-Touch-AMOLED-2.16" board, which would put the same screen class on a known chip. I did not read its page.
