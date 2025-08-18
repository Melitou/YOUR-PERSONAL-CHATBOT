import re
from difflib import SequenceMatcher

# Gold answers (ground truth)
gold_answers = {
    1: "The White Rabbit took a watch out of its waistcoat-pocket, looked at it, and hurried on, which surprised Alice because she had never seen a rabbit with a waistcoat-pocket or a watch.",
    2: "The bottle had a label that said 'DRINK ME' in large letters.",
    3: "She shrank until she was only about ten inches high, the right size to fit through the little door into the garden.",
    4: "She grew to more than nine feet tall, became upset, and cried until her tears formed a large pool. Later she shrank again and fell into it.",
    5: "The Dodo suggested the Caucus-race.",
    6: "Alice gave them comfits (sweets), one each, and the Dodo presented Alice with a thimble as her prize.",
    7: "The White Rabbit mistook Alice for his housemaid.",
    8: "A caterpillar."
}

def normalize(text):
    text = text.lower()
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return text.split()


def evaluate_response(question_id, response):
    gold = gold_answers[question_id]

    # Normalize
    gold_tokens = set(normalize(gold))
    resp_tokens = set(normalize(response))

    # Keyword overlap
    overlap = gold_tokens & resp_tokens
    recall = len(overlap) / len(gold_tokens) if gold_tokens else 0
    precision = len(overlap) / len(resp_tokens) if resp_tokens else 0

    # F1 score (harmonic mean)
    if recall + precision > 0:
        f1 = 2 * (recall * precision) / (recall + precision)
    else:
        f1 = 0

    # Similarity ratio (string-level)
    similarity = SequenceMatcher(None, gold.lower(), response.lower()).ratio()

    return {
        "gold_answer": gold,
        "response": response,
        "overlap": list(overlap),
        "recall": round(recall, 2),
        "precision": round(precision, 2),
        "f1": round(f1, 2),
        "similarity": round(similarity, 2)
    }


# Example usage
if __name__ == "__main__":
    resp = "The rabbit had a watch in its pocket and Alice was curious because she never saw that before."
    result = evaluate_response(1, resp)
    print(result)
