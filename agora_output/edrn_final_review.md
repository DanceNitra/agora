@luoxuejian000 @maratsultanov2 @qingkong66

Guanghao, Marat — thank you. I have read the 30 July LaTeX source. Marat's two corrections are both right and I agree with them.

Two things to settle before I can do the final read: one numerical inconsistency in the SOC section, and one statistical question about the parity result. On the second, part of what I have to report is a correction to my own reasoning.

---

## A. To settle before finalisation — the SOC text and the SOC table disagree

"Discovery 1" says the ratio $F_{\text{SOC}}(s)/F_{\text{Heis}}(s)$ is **not** constant, and that at the valley it exceeds unity for $N=6$ (**1.164**).

Table `tab:soc_main` is captioned "chain graph $N=6$ ... standard Pauli-matrix construction". Computing the ratio row by row from that table:

| $s$ | Heis ($D=0$) | SOC ($D=0.3$) | ratio |
|---|---|---|---|
| 0.00 | 0.1786 | 0.1711 | 0.95801 |
| **0.38 (valley)** | **0.1041** | **0.0997** | **0.95773** |
| 0.75 | 0.1514 | 0.1450 | 0.95773 |
| 1.12 | 0.1904 | 0.1823 | 0.95746 |
| 1.50 | 0.2192 | 0.2100 | 0.95803 |
| 1.88 | 0.2408 | 0.2306 | 0.95764 |
| 2.25 | 0.2574 | 0.2465 | 0.95765 |
| 2.62 | 0.2705 | 0.2591 | 0.95786 |
| 3.00 | 0.2810 | 0.2692 | 0.95801 |

The ratio is constant at **0.9578**, spread **0.00057 (0.06%)**; at the valley it is **0.9577**, a factor 1.215 from 1.164. To reach 1.164 the SOC valley entry would need to be 0.1212 rather than 0.0997, so this is not a rounding or normalisation effect. I also checked the obvious alternative definitions — ratios of valley depth, of prominence, of derivatives, self-normalised $F/F(0)$, and the ratio taken after dividing out the global factor — and they all return either 0.958 or 1.000, none returns 1.164.

The detail that I think identifies the cause: $1/\sqrt{1+D^2}$ at $D=0.3$ is **0.957826**, and the table's mean ratio is **0.95779**. The table matches the uniform SEA gauge factor to five digits. That is the same 0.9578 rescaling that came up on 27 July — and the paragraph directly below the table states that the earlier "nearly constant ratio ($\approx 0.958$)" was traced to an incorrect Hamiltonian and that "the corrected data shown here supersede that finding".

(One bookkeeping note so the two discussions are comparable: on 27 July I quoted the relative depth as 0.3691 vs 0.3692, measured against the shoulders; the 0.6295 vs 0.6296 above is (max−min)/max over this table. Different normalisation, same conclusion — the depth is unchanged to four decimals either way.)

At least three things could explain this, and only you can say which:

1. `tab:soc_main` still holds the pre-correction data, left in place when the text was revised — then the table needs replacing with the re-run isotropic Heisenberg output;
2. the 1.164 / 0.950 / 1.042 figures come from a scan that is not in the manuscript — then that scan should be added as a table for $N=6,8,10$;
3. those figures refer to a **different quantity** than $F_{\text{SOC}}/F_{\text{Heis}}$ — a ratio of relative depths, say, or a different $D$ — in which case the fix is only to define it explicitly in the text.

Related: $N=8$ and $N=10$ do not appear anywhere in the source except the parity discussion, and Sec. VI E limitation (1) states that all cross-graph scans were completed at $N=6$. So two of the three figures in that triple have no tabulated support that I could find. If there is another table or appendix I missed, please point me to it — this is the only SOC dataset I located in the 30 July source, not necessarily the only one that exists.

As written, Discovery 1 — and the Fourth Law insofar as it cites Discovery 1 — rests on a number the tabulated data does not reproduce. A referee is likely to check this ratio. Most likely the table and the text simply come from different revisions.

**Concretely, so this is easy to close:** which script produced `tab:soc_main`, and where do the $N=8$ / $N=10$ SOC scans live? I still have my 27 July audit script — send me the corrected run's CSV (or just the Hamiltonian construction) and I will regenerate the table and add the ratio column myself.

---

## B. The parity result — and a correction to what I first wrote

I drafted a claim here and then found it was wrong in a way worth stating plainly, because the same error would have gone into the paper.

**I first argued:** with ~10 odd chains tested, $N=9$ at $p=0.030$ is unremarkable; Bonferroni over 10 gives 0.005; neither $N=9$ nor the $N=19$ migration survives; therefore the clean law "no odd chain resonates" is *preserved*, and is better than narrowing it to "prime odd chains" or "odd chains above $N=9$".

**That reasoning is unsound, and I withdraw it.** "No odd chain resonates" is a null hypothesis. A multiple-comparison correction only raises the bar for *rejecting* a null; it can never provide evidence *for* one. So "apply Bonferroni and the law survives" is circular — the procedure cannot fail to produce that answer. I had also drawn the family around the odd chains only, which is precisely the subset containing the datum that contradicted the law. Applying a correction to the half I wanted removed, while leaving the half I wanted kept uncorrected, is not a defensible procedure and a referee would say so.

What I should have asked first, and am asking now:

**(0) What ensemble are these $p$-values tails of?** These are exact-diagonalization results, so there is no sampling noise. A $p$-value needs a reference distribution — a randomization null over triad/level assignment would be one, and a legitimate one; a fit residual on deterministic data would not be. Until that is named, both the paper's $p$-values and any correction of mine are decorative. This question comes before the rest.

If there is a randomization null, then three requests:

**(1) Per-chain $p$-values for all 19 chains, plus $k$ = how many triads were examined per chain.** Format: chain $N$, triad label, $p$, number of tests. This matters concretely: the $N=19$ value of 0.02 is a *minimum over $k$ triads*, so its reference distribution is the minimum order statistic, not $U(0,1)$ — at $k=2$ a nominal 0.02 corresponds to an effective 0.0396. I would describe that as selective inference rather than "migration", and note that "migration to a different triad" quietly drops the quantifier from the law: over which triad is the law universally stated?

**(2) One stated correction over the full $19 \times k$ family, not over a subset.** The verdict is currently a free parameter: Bonferroni at $m=19$ gives 0.0026 and kills $N=9$, $N=19$ *and* the even chains at 0.026; Benjamini–Hochberg at $m=19$ keeps $N=19$ and drops $N=9$ by 0.001. I would propose a Westfall–Young max-statistic permutation over the grid, which inherits the chains' shared-construction dependence instead of assuming independence.

**(3) Power for the odd chains.** Since the law is a negative, the informative statistic is not a corrected $\alpha$ but whether the odd-chain tests were powered to detect an effect of the size the even chains show (agreement > 0.97). If they were not, the ten quiet chains, $N=9$ and $N=19$ are all equally uninformative. An equivalence test against the even-chain effect size would settle it.

On my earlier worry that the even chains might not survive correction: **that was overstated.** Nine chains at $p \leq 0.026$ combine to a Fisher $p$ of $2.4\times10^{-7}$ if independent. Under strong dependence it collapses toward 0.026, so the quantity that actually matters is the effective number of independent chains — which is again answered by (1) and (2).

Marat, on your two corrections: I agree with both as written. On the second, I would suggest that rather than narrowing the statement to "prime odd chains" or "above $N=9$", we first settle (0)–(3) and then state whatever the corrected analysis supports. A boundary fitted to one data point is the version a referee will press hardest.

---

## On finalisation and Zenodo

Guanghao, you gave me final sign-off and asked me to handle the Zenodo deposit. I would rather settle A first, and I want to be accurate about why.

Zenodo does support versioning — we could post v1 now and supersede it — so "a DOI is permanent" is not by itself a sufficient reason to wait. The real reason is narrower: a v1 remains permanently retrievable and citable, and I would prefer not to have a v1 whose headline SOC statement is not reproduced by its own table. This is a matter of days, not weeks. Once A is settled I can do the final read and the deposit on the same day.

Proposed sequence:

1. You resolve A — replace the table, add the missing scan, or define the quantity precisely, whichever is the case.
2. You or Marat answer (0) and supply (1); **if it is easier, send me the raw triad outputs and I will do the correction and write the statistics paragraph myself.** I would rather do that work than hand it back.
3. Marat's two corrections go in as he wrote them.
4. I do the final read, then handle Zenodo and the version record.

On the route after that: our settled path is **SciPost Physics Core by direct submission** — no arXiv, no endorser, no fee, open to unaffiliated authors, with SciPost self-hosting the preprint and minting a DOI. arXiv (cond-mat.str-el) stays closed to us because none of the three of us holds an endorsement, so it is not a step in this plan.

Thank you both for the care in the manuscript, and Guanghao, thank you for the attribution — it is more generous than I would have written for myself. The corrections above are offered in the same spirit as the earlier rounds: the data decides, including when it decides against my own reasoning, as it did in section B.

Rastislav

---
---

@luoxuejian000 @maratsultanov2 @qingkong66

广好、Marat，

感谢你们。我已读完 7 月 30 日版本的 LaTeX 源文件。Marat 的两条修改都正确，我同意。

在做终审通读之前，有两件事需要先确认：SOC 一节中的一处数值不一致，以及宇称结果的一个统计问题。关于第二点，我要报告的内容里有一部分是对我自己推理的更正。

---

## A. 定稿前需解决 —— SOC 正文与表格数据不一致

"Discovery 1" 写道：比值 $F_{\text{SOC}}(s)/F_{\text{Heis}}(s)$ **不是**常数，且在谷底处 $N=6$ 时超过 1（**1.164**）。

而表 `tab:soc_main` 的标题为"链图 $N=6$ …… 标准泡利矩阵构造"。逐行计算该表的比值：

| $s$ | Heis ($D=0$) | SOC ($D=0.3$) | 比值 |
|---|---|---|---|
| 0.00 | 0.1786 | 0.1711 | 0.95801 |
| **0.38（谷底）** | **0.1041** | **0.0997** | **0.95773** |
| 0.75 | 0.1514 | 0.1450 | 0.95773 |
| 1.12 | 0.1904 | 0.1823 | 0.95746 |
| 1.50 | 0.2192 | 0.2100 | 0.95803 |
| 1.88 | 0.2408 | 0.2306 | 0.95764 |
| 2.25 | 0.2574 | 0.2465 | 0.95765 |
| 2.62 | 0.2705 | 0.2591 | 0.95786 |
| 3.00 | 0.2810 | 0.2692 | 0.95801 |

比值恒为 **0.9578**，全程波动 **0.00057（0.06%）**；谷底处为 **0.9577**，与 1.164 相差 1.215 倍。若要得到 1.164，SOC 谷底数值需为 0.1212 而非 0.0997，因此这不是舍入或归一化造成的差异。我也核算了其他可能的定义 —— 谷深之比、突出度之比、导数之比、自归一化 $F/F(0)$，以及除去全局因子后再取比值 —— 结果都落在 0.958 或 1.000，没有一种得到 1.164。

我认为能指认原因的细节是：$D=0.3$ 时 $1/\sqrt{1+D^2} = $ **0.957826**，而该表比值的平均为 **0.95779**，与均匀 SEA 规范因子吻合到五位数字。这正是 7 月 27 日讨论过的那个 0.9578 等比缩放 —— 而表格下方那一段写着，早先"近似常数的比值（$\approx 0.958$）"被追溯到哈密顿量构造错误，"此处展示的修正数据取代了该结论"。

（一处记账说明，便于两次讨论对照：7 月 27 日我给出的相对谷深是 0.3691 对 0.3692，以肩部为基准；上文的 0.6295 对 0.6296 则是本表的 (max−min)/max。归一化方式不同，结论相同 —— 两种算法下谷深都在小数点后四位保持不变。）

至少有三种可能，只有你能确认是哪一种：

1. `tab:soc_main` 中仍是修正前的数据，正文改写时未一并替换 —— 那么需用重跑的各向同性 Heisenberg 结果替换该表；
2. 1.164 / 0.950 / 1.042 来自稿件中未收录的另一次扫描 —— 那么应将其作为 $N=6,8,10$ 的表格补入；
3. 这些数字指的并非 $F_{\text{SOC}}/F_{\text{Heis}}$，而是另一个量（例如相对谷深之比，或不同的 $D$）—— 若如此，只需在正文中明确定义即可。

相关一点：$N=8$ 与 $N=10$ 在源文件中除宇称讨论外未再出现，且第 VI E 节限制条款 (1) 说明所有 cross-graph 扫描均在 $N=6$ 完成。因此那组三个数字中有两个，我没有找到对应的表格支持。若另有表格或附录是我遗漏的，请告知 —— 这是我在 7 月 30 日源文件中找到的唯一 SOC 数据集，未必是全部。

按现在的写法，Discovery 1 —— 以及第四定律中援引 Discovery 1 的部分 —— 建立在一个表格数据未能重现的数值上。审稿人很可能会自行核算这一比值。很可能表格与正文来自不同的修订版本。

**为便于处理，具体请求是：** `tab:soc_main` 由哪个脚本生成，以及 $N=8$ / $N=10$ 的 SOC 扫描数据在哪里？我仍保留 7 月 27 日的核算脚本 —— 把修正后那次运行的 CSV（或仅哈密顿量构造）发给我，表格和比值列我可以自己重新生成。

---

## B. 宇称结果 —— 以及对我最初写法的更正

我先起草了一段论证，随后发现它是错的，而且值得明说，因为同样的错误本会进入论文。

**我最初的论证是：** 测试了约 10 条奇数链，$N=9$ 的 $p=0.030$ 并不特别；对 10 条做 Bonferroni 得阈值 0.005；$N=9$ 与 $N=19$ 迁移都通不过；因此"无奇数链共振"这一干净表述得以*保留*，优于收窄为"素数奇数链"或"$N>9$ 的奇数链"。

**这个推理不成立，我撤回它。** "无奇数链共振"是一个零假设。多重比较校正只会提高*拒绝*零假设的门槛，它永远无法为零假设*提供*证据。所以"做了 Bonferroni，定律依然成立"是循环论证 —— 该程序不可能得出别的结论。而且我把检验族划定为仅奇数链，恰恰是包含那个与定律矛盾的数据点的子集。对想剔除的一半施加校正、对想保留的一半不施加，这不是站得住脚的程序，审稿人会直接指出。

我本应先问、现在提出的问题是：

**(0) 这些 $p$ 值是哪个 ensemble 的尾部？** 这些是精确对角化结果，没有抽样噪声。$p$ 值需要一个参考分布 —— 对三元组/能级指派做随机化零分布是一种，而且是合理的一种；对确定性数据做拟合残差则不是。在这一点明确之前，论文的 $p$ 值和我提出的任何校正都只是装饰。这个问题排在其余之前。

若确有随机化零分布，则有三项请求：

**(1) 全部 19 条链的逐链 $p$ 值，以及每条链检验了多少个三元组 $k$。** 格式：链 $N$、三元组标签、$p$、检验次数。这一点很具体：$N=19$ 的 0.02 是*在 $k$ 个三元组上取的最小值*，其参考分布是最小值次序统计量而非 $U(0,1)$ —— 当 $k=2$ 时，名义 0.02 对应的有效值为 0.0396。我会把这称为选择性推断（selective inference），而非"迁移"；并且"迁移到另一个三元组"实际上悄悄取消了定律中的量词：这条定律是对哪一个三元组普遍成立的？

**(2) 对完整的 $19 \times k$ 族施加一种明确声明的校正，而非对子集。** 目前的结论是一个自由参数：$m=19$ 的 Bonferroni 阈值为 0.0026，会同时否决 $N=9$、$N=19$ *以及* 0.026 处的偶数链；$m=19$ 的 Benjamini–Hochberg 则保留 $N=19$，而 $N=9$ 以 0.001 之差落选。我建议采用 Westfall–Young max 统计量置换检验，它继承各链共享构造带来的真实相关性，而不是假定独立。

**(3) 奇数链的检验功效。** 既然该定律是一个否定命题，有信息量的统计量就不是校正后的 $\alpha$，而是奇数链的检验是否有足够功效去探测偶数链所显示的效应量（agreement > 0.97）。若功效不足，那么十条"沉默"的链、$N=9$ 和 $N=19$ 同样都不提供信息。用等价性检验对照偶数链的效应量即可判定。

关于我先前担心偶数链可能通不过校正：**那个担心被高估了。** 九条链的 $p \leq 0.026$，若相互独立，合并的 Fisher $p$ 为 $2.4\times10^{-7}$。在强相关下则会收敛到 0.026，所以真正关键的量是有效独立链数 —— 这同样由 (1) 和 (2) 回答。

Marat，关于你的两条修改：按你所写，我都同意。第二条我的建议是：与其把表述收窄为"素数奇数链"或"$N>9$"，不如先解决 (0)–(3)，再按校正后的分析结果如实陈述。为单个数据点设定的边界，正是审稿人会追问最紧的版本。

---

## 关于定稿与 Zenodo

广好，你把终审定稿权和 Zenodo 上传交给了我。我希望先解决 A，也想把理由说准确。

Zenodo 是支持版本化的 —— 我们可以先发 v1，之后再更新 —— 所以"DOI 是永久的"本身并不构成充分理由。真正的理由更窄：v1 会永久可检索、可被引用，而我不希望存在一个头号 SOC 结论未被自己表格重现的 v1。这是几天的事，不是几周。A 一旦解决，我可以在当天完成通读与上传。

建议顺序：

1. 你解决 A —— 替换表格、补入缺失的扫描，或明确定义该量，视实际情况而定。
2. 你或 Marat 回答 (0) 并提供 (1)；**若更方便，把三元组的原始输出发给我，校正和统计段落由我来写。** 我更愿意承担这部分工作，而不是把问题推回去。
3. Marat 的两条修改按他写的原文加入。
4. 我做最终通读，然后处理 Zenodo 与版本记录。

关于之后的投稿路径：我们已确定的方案是 **SciPost Physics Core 直接投稿** —— 不需要 arXiv、不需要 endorser、不收费用，接受无机构署名作者，SciPost 自行托管预印本并分配 DOI。arXiv（cond-mat.str-el）对我们仍然关闭，因为我们三人都没有 endorsement，所以它不在此计划内。

感谢你们二位对稿件的用心。广好，也谢谢你的署名描述 —— 比我自己会写的更慷慨。以上修改与此前每一轮秉持同样的精神：由数据裁决，包括当它裁决的是我自己的推理时 —— 正如 B 节所示。

Rastislav
