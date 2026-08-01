@maratsultanov2 @luoxuejian000

A follow-up to my review above, because Marat had already answered part of it before I posted it — my comment went up this morning, his results arrived last night, and I should correct the record rather than leave a request standing for work that is already done.

**Point (0) in my review — "what ensemble are these $p$-values tails of?" — is answered.** Marat ran a per-$N$ randomisation null: permutations within each chain, $T=1$ fixed. That is exactly the right construction, and it is the one I had asked for. Quoting his numbers (his run, not an independent re-run by me):

| | per-$N$ null, $T=1$ |
|---|---|
| all even $N$ (4–20) | $p \leq 0.015$ |
| all odd $N$ (3–21) | $p \geq 0.03$, most $> 0.3$ |

Two consequences for the manuscript.

**First, this is a cleaner result than the one currently in the paper, and the paper should cite this test rather than the earlier one.** The manuscript reports $p \leq 0.026$ for the even chains. Under the per-$N$ null the even chains come in at $\leq 0.015$ and the odd chains at $\geq 0.03$ — a gap with no overlap, from a null that scales with each chain's own error. That is a stronger statement than the one being made, and it is the version that answers a referee's first question.

**Second, and this is the part I owe Marat and you directly.** In our exchange I raised a confound: across the odd chains, $p$ tracked the error scale inversely — Spearman$(\text{norm\_error}, p) = -0.49$ within the odd arm and $-0.83$ across all chains — so "parity" and "error scale" risked being one variable with two names. I said that if the split survived a per-$N$ null built to scale with each chain's own error, I would have nothing left and would say so here.

**It survived, and I have nothing left. The anticorrelation is gone under the per-$N$ null; $p$ is now determined by parity and not by error scale.** That objection is withdrawn, and the parity separation stands on the strongest test we have put to it.

**One thing that does need narrowing.** Marat also went back to the CSV and corrected several of his own earlier statements against himself, unprompted — including this one, which cuts against the clean story: in the angular scan, $N = 3, 9, 15, 21$ give the lowest $p$ of the odd chains, and every one of them is a multiple of three, while the primes $N=17$ and $N=19$ sit at 0.75 and 0.61. His words: *"this is important, and I should not have hidden it behind a generalisation."*

The manuscript currently says divisibility by three is "decisively ruled out". On the raw per-chain $p$-values that is correct, and the even-chain argument ($N = 4, 8, 10, 14, 16, 20$ all resonate and none is divisible by three) holds. But it is not correct for the angular scan, where the multiples of three come back. So I would narrow the claim to what the data supports:

> Parity is the primary variable: under a per-$N$ randomisation null the even chains separate cleanly from the odd ($p \leq 0.015$ vs $p \geq 0.03$), and divisibility by three does not account for it. Within the odd chains a residual structure remains that does track divisibility by three, visible in the angular scan ($N = 3, 9, 15, 21$ give the lowest angular $p$; the primes 17 and 19 do not). This is a refinement of the parity result, not a competitor to it.

That sentence is defensible as written and does not need an exception fitted to $N=9$.

On $N=9$ specifically, Marat: under the per-$N$ null it sits at the bottom edge of the odd group ($\geq 0.03$) rather than inside the even group ($\leq 0.015$), so I think your correction to the manuscript is still right — the literal "no odd chain passes" needs qualifying — but the qualification is now about where the boundary is drawn, not about a chain crossing it.

My section-A point about the SOC table is unchanged and still needs settling. Section B is largely superseded by the above: the ensemble question is answered, and what remains is the smaller request to put the per-chain numbers and the $k$ (triads examined per chain) into the manuscript so the correction is stated rather than implied.

Marat — thank you for running it, and for going back and correcting your own numbers before anyone asked you to. That is the harder half of the job.

Rastislav

---

@maratsultanov2 @luoxuejian000

对上文评审的补充说明。Marat 在我发帖之前就已经回答了其中一部分 —— 我的评审是今早发出的，而他的结果昨晚就到了，所以我应当更正记录，而不是让一项已完成的工作继续挂在请求清单上。

**我评审中的第 (0) 点 ——"这些 $p$ 值是哪个 ensemble 的尾部？"—— 已有答案。** Marat 做了逐 $N$ 的随机化零分布：在每条链内部做置换，固定 $T=1$。这正是恰当的构造，也正是我所请求的。引用他的数据（他的运行结果，我尚未独立复算）：

| | 逐 $N$ 零分布，$T=1$ |
|---|---|
| 全部偶数 $N$（4–20） | $p \leq 0.015$ |
| 全部奇数 $N$（3–21） | $p \geq 0.03$，多数 $> 0.3$ |

这对稿件有两点影响。

**第一，这个结果比论文现有的更干净，论文应当引用这个检验，而非早先那个。** 稿件报告偶数链 $p \leq 0.026$。在逐 $N$ 零分布下，偶数链为 $\leq 0.015$，奇数链为 $\geq 0.03$ —— 两者无重叠，且该零分布随每条链自身的误差尺度而缩放。这比目前的表述更强，也正是能回答审稿人第一个问题的版本。

**第二，这一点是我直接欠 Marat 和你的。** 在我们的通信中我提出过一个混淆因素：在奇数链上，$p$ 与误差尺度呈反向关系 —— 奇数臂内 Spearman$(\text{norm\_error}, p) = -0.49$，全体链为 $-0.83$ —— 因此"宇称"与"误差尺度"有可能是同一个变量的两个名字。我当时说过：若该分离能在一个随每条链自身误差缩放的逐 $N$ 零分布下存活，我就无话可说，并会在此明说。

**它存活了，我无话可说。在逐 $N$ 零分布下反相关消失了；$p$ 现在由宇称决定，而非由误差尺度决定。** 该异议撤回，宇称分离经受住了我们对它施加的最强检验。

**但有一处确实需要收窄。** Marat 也回到 CSV，在无人要求的情况下更正了自己此前的若干表述 —— 包括这一条，它与那个干净的故事相悖：在角度扫描中，$N = 3, 9, 15, 21$ 给出奇数链中最低的 $p$，而它们无一例外都是三的倍数；素数 $N=17$ 与 $N=19$ 则位于 0.75 和 0.61。他的原话是：*"这一点很重要，我不该把它藏在一个笼统的说法后面。"*

稿件目前写道，三的整除性已被"决定性排除"。就逐链的原始 $p$ 值而言这是对的，偶数链的论证（$N = 4, 8, 10, 14, 16, 20$ 全部共振且都不被 3 整除）也成立。但对角度扫描而言并不成立 —— 在那里三的倍数又回来了。因此我建议把该论断收窄到数据所支持的范围：

> 宇称是主变量：在逐 $N$ 随机化零分布下，偶数链与奇数链干净分离（$p \leq 0.015$ 对 $p \geq 0.03$），且三的整除性无法解释这一分离。但在奇数链内部仍残留一层确实与三的整除性相关的结构，可见于角度扫描（$N = 3, 9, 15, 21$ 给出最低的角度 $p$；素数 17 与 19 则不然）。这是对宇称结果的细化，而非与之竞争的解释。

这句话按原样即可辩护，也无需为 $N=9$ 单设例外。

关于 $N=9$，Marat：在逐 $N$ 零分布下它位于奇数组的下边缘（$\geq 0.03$），而不在偶数组之内（$\leq 0.015$）。所以我认为你对稿件的修改仍然正确 —— 字面意义上的"无奇数链通过"需要限定 —— 只是这个限定现在关乎边界画在哪里，而不是某条链越过了边界。

我关于 SOC 表格的 A 节意见维持不变，仍需解决。B 节则大部分已被上述内容取代：ensemble 的问题已有答案，剩下的只是一个较小的请求 —— 把逐链数值以及每条链检验的三元组数 $k$ 写入稿件，使校正是被明确陈述的，而不是被默认的。

Marat —— 感谢你运行了这个检验，也感谢你在无人要求之前就回头更正了自己的数字。那是这份工作中更难的一半。

Rastislav
