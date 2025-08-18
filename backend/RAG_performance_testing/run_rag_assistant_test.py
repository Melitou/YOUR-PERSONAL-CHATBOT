#!/usr/bin/env python3
"""
Direct Assistant RAG Test (uses ask_openai_assistant)
- Initializes RAG config (no websockets)
- Runs 8 Alice-in-Wonderland questions
- Generates final answers via ask_openai_assistant with/without keyword enhancement
- Evaluates answers and saves a JSON report
"""

import os
import sys
import json
import time
from datetime import datetime
from typing import Dict, List

# Make repository root importable
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from LLM.rag_llm_call import initialize_rag_config, ask_openai_assistant
from RAG_performance_testing.RAG_repsonse_evaluation import evaluate_response
from db_service import initialize_db

# --------------------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------------------
# Namespace(s) to search in (can be a single namespace). Default to your Alice chatbot namespace.
NAMESPACES = [
	os.getenv("ALICE_NAMESPACE", "AliceInWonderlandChatbotNew_68a2e1119aad87a707897662")
]

# Embedding model used for that namespace (must match actual ingestion model)
EMBEDDING_MODEL = os.getenv("ALICE_EMBEDDING_MODEL", "text-embedding-3-small")

# Assistant model to use (the same model your system uses for generation)
CHATBOT_MODEL = os.getenv("ALICE_LLM_MODEL", "gpt-4.1")

# An arbitrary user id string to satisfy config (not used against DB in this script)
USER_ID = os.getenv("ALICE_TEST_USER_ID", "test_user")

# Questions to test
TEST_QUESTIONS: Dict[int, str] = {
	1: "What unusual thing did Alice notice about the White Rabbit before following it?",
	2: "What was written on the bottle Alice found on the glass table?",
	3: "What happened to Alice after she drank from the bottle?",
	4: "How did Alice end up in the pool of tears?",
	5: "Who suggested the Caucus-race to get everyone dry?",
	6: "What did the animals and birds receive as prizes after the race?",
	7: "Who mistook Alice for his housemaid, Mary Ann?",
	8: "What animal did Alice encounter sitting on top of a mushroom smoking a hookah?",
}

# --------------------------------------------------------------------------------------
# Test Runner
# --------------------------------------------------------------------------------------

def run_single(question_id: int, question: str, enable_keywords: bool) -> Dict:
	mode = "with_keywords" if enable_keywords else "without_keywords"
	print(f"\n🧪 Q{question_id} {mode}: {question}")

	# Empty short history for now (you can extend with prior turns if desired)
	history: List[Dict] = []

	answer = ask_openai_assistant(
		history=history,
		query=question,
		model=CHATBOT_MODEL,
		keyword_enhancement=enable_keywords,
		keyword_boost_factor=0.3,
	)
	print(f"\n\n\033[34mANSWER LENGTH: {len(answer)}\033[0m\n\n")
	metrics = evaluate_response(question_id, answer or "")
	print(f"   F1={metrics['f1']} | Recall={metrics['recall']} | Precision={metrics['precision']} | Similarity={metrics['similarity']}")

	return {
		"question_id": question_id,
		"question": question,
		"use_keywords": enable_keywords,
		"final_answer": answer or "",
		"evaluation": metrics,
		"timestamp": datetime.now().isoformat(),
	}


def summarize(results: List[Dict]) -> Dict:
	with_kw = [r for r in results if r.get("use_keywords") and r.get("evaluation")]
	without_kw = [r for r in results if (not r.get("use_keywords")) and r.get("evaluation")]

	def avg(metric: str, arr: List[Dict]) -> float:
		if not arr:
			return 0.0
		return round(sum(r["evaluation"][metric] for r in arr) / len(arr), 3)

	summary = {
		"with_keywords": {m: avg(m, with_kw) for m in ("f1", "recall", "precision", "similarity")},
		"without_keywords": {m: avg(m, without_kw) for m in ("f1", "recall", "precision", "similarity")},
	}
	summary["improvements"] = {
		f"{m}_improvement": round(summary["with_keywords"][m] - summary["without_keywords"][m], 3)
		for m in ("f1", "recall", "precision", "similarity")
	}
	return summary


def save_report(all_results: List[Dict], out_dir: str = "RAG_performance_testing") -> str:
	os.makedirs(out_dir, exist_ok=True)
	ts = datetime.now().strftime("%Y%m%d_%H%M%S")
	path = os.path.join(out_dir, f"RAG_assistant_results_{ts}.json")
	report = {
		"test_config": {
			"namespaces": NAMESPACES,
			"embedding_model": EMBEDDING_MODEL,
			"chatbot_model": CHATBOT_MODEL,
			"user_id": USER_ID,
			"date": datetime.now().isoformat(),
			"total_questions": len(TEST_QUESTIONS),
		},
		"individual_results": all_results,
		"summary": summarize(all_results),
	}
	with open(path, "w", encoding="utf-8") as f:
		json.dump(report, f, indent=2)
	print(f"\n💾 Saved report: {path}")
	return path


def main():
	print("🔬 Direct Assistant RAG Test (ask_openai_assistant)")
	print(f"📚 Namespaces: {NAMESPACES}")
	print(f"🤖 Embedding Model: {EMBEDDING_MODEL}")
	print(f"🧠 Chatbot Model: {CHATBOT_MODEL}")

	# Initialize MongoDB connection
	initialize_db()

	# Initialize the RAG config so the assistant will use the right namespaces and embedding model
	initialize_rag_config(
		user_id=USER_ID,
		namespaces=NAMESPACES,
		embedding_model=EMBEDDING_MODEL,
		chatbot_model=CHATBOT_MODEL,
	)

	results: List[Dict] = []
	for qid, question in TEST_QUESTIONS.items():
		# Without keywords
		res_off = run_single(qid, question, enable_keywords=False)
		results.append(res_off)
		time.sleep(0.5)

		# With keywords
		res_on = run_single(qid, question, enable_keywords=True)
		results.append(res_on)
		time.sleep(0.5)

	# Summary
	sumry = summarize(results)
	print("\n📊 Averages (without → with → improvement):")
	for metric in ("f1", "recall", "precision", "similarity"):
		w = sumry["without_keywords"][metric]
		k = sumry["with_keywords"][metric]
		d = sumry["improvements"][f"{metric}_improvement"]
		print(f" - {metric.upper():<10} {w:.3f} → {k:.3f}  (Δ {d:+.3f})")

	# Save
	save_report(results)


if __name__ == "__main__":
	main()
