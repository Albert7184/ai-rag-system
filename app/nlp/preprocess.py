import re
import underthesea

def clean_text(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-zA-ZÀ-ỹ\s]", "", text)
    tokens = underthesea.word_tokenize(text)
    return " ".join(tokens)
def preprocess_texts(texts: list[str]) -> list[str]:
    return [clean_text(text) for text in texts]