import pandas as pd
import pickle
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from app.nlp.preprocess import clean_text

# Đường dẫn file
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, "nlp", "intents.csv")

# 1. Tạo dữ liệu mẫu để huấn luyện (Vì file CSV của bạn đang bị lẫn câu trả lời)
data = {
    'text': [
        'hi', 'hello', 'chào bạn', 'xin chào', 'alo',
        'tạm biệt', 'bye', 'hẹn gặp lại',
        'hoàn tiền', 'đổi trả', 'chính sách hoàn hàng',
        'bao lâu nhận được hàng', 'thời gian giao hàng', 'giao hàng mất bao lâu',
        'khiếu nại', 'không hài lòng', 'phản ánh dịch vụ'
    ],
    'intent': [
        'greeting', 'greeting', 'greeting', 'greeting', 'greeting',
        'goodbye', 'goodbye', 'goodbye',
        'refund_policy', 'refund_policy', 'refund_policy',
        'delivery_time', 'delivery_time', 'delivery_time',
        'complaint', 'complaint', 'complaint'
    ]
}
df = pd.DataFrame(data)

# 2. Tiền xử lý và Huấn luyện
df['cleaned_text'] = df['text'].apply(clean_text)
vectorizer = TfidfVectorizer()
X = vectorizer.fit_transform(df['cleaned_text'])
y = df['intent']

model = MultinomialNB()
model.fit(X, y)

# 3. Lưu model
with open(os.path.join(BASE_DIR, "nlp", "model.pkl"), "wb") as f:
    pickle.dump(model, f)
with open(os.path.join(BASE_DIR, "nlp", "vectorizer.pkl"), "wb") as f:
    pickle.dump(vectorizer, f)

print("✅ Đã huấn luyện lại Model thành công!")