#!/usr/bin/env bash
# Full competitive matrix, MAB REAL protocol (512-token chunked ingest), sh_6k, n=100.
# Sequential so cloud-LLM answerers never contend. mem0 deepseek-chunk already ran separately.
cd /c/Users/Danculus/agora
R="python -u mnemo/probes/mab_official/run_mnemo_official.py --n 100 --ingest chunk"

echo "######## DEEPSEEK backend (Ollama Cloud, free) ########"
for cond in mnemo naive; do
  echo "===RUN=== $cond deepseek chunk"
  $R --condition $cond --llm deepseek
done

echo "######## OPENAI backend (gpt-4o-mini = faithful published config) ########"
for cond in longcontext mem0 mnemo naive; do
  echo "===RUN=== $cond openai chunk"
  $R --condition $cond --llm openai
done

echo "######## MATRIX DONE ########"
