#!/usr/bin/env bash
# sh_32k (2310 facts). (B) mnemo-mechanism test FIRST (fast, the money test), then (A) faithful length-scaling.
cd /c/Users/Danculus/agora
P="python -u mnemo/probes/mab_official/run_mnemo_official.py --n 100 --sample sh_32k"

echo "######## (B) MNEMO-MECHANISM · atomic keyed ingest / retrieve k=10 · deepseek (free) ########"
echo "######## supersession (2310 facts -> consolidated latest-only) should BEAT naive (k=10 over 2310 misses fresh) ########"
for cond in mnemo naive; do
  echo "===RUN=== B $cond deepseek atomic k10"
  $P --condition $cond --ingest atomic --retrieve-num 10 --llm deepseek
done

echo "######## (A) FAITHFUL length-scaling · chunk 4096 / retrieve 100 · deepseek (free) ########"
for cond in longcontext mnemo naive mem0; do
  echo "===RUN=== A $cond deepseek chunk4096 k100"
  $P --condition $cond --ingest chunk --chunk-size 4096 --retrieve-num 100 --llm deepseek
done

echo "######## (A') faithful mem0 on gpt-4o-mini (confirm published ~22% @32k) ########"
echo "===RUN=== A mem0 openai chunk4096 k100"
$P --condition mem0 --ingest chunk --chunk-size 4096 --retrieve-num 100 --llm openai

echo "######## MATRIX2 DONE ########"
