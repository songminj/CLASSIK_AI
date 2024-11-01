from transformers import BertTokenizer, TFBertModel

# KoBERT 모델 로드
kobert_tokenizer = BertTokenizer.from_pretrained('skt/kobert-base-v1')
kobert_model = TFBertModel.from_pretrained('skt/kobert-base-v1')

# 다국어 BERT 모델 로드
bert_tokenizer = BertTokenizer.from_pretrained('bert-base-multilingual-cased')
bert_model = TFBertModel.from_pretrained('bert-base-multilingual-cased')


def get_combined_embeddings(text):
    # KoBERT 임베딩 생성
    ko_inputs = kobert_tokenizer(text, return_tensors="tf", padding=True, truncation=True)
    ko_outputs = kobert_model(ko_inputs)
    ko_embeddings = ko_outputs.last_hidden_state[:, 0, :]  # [CLS] 토큰 임베딩

    # BERT 임베딩 생성
    bert_inputs = bert_tokenizer(text, return_tensors="tf", padding=True, truncation=True)
    bert_outputs = bert_model(bert_inputs)
    bert_embeddings = bert_outputs.last_hidden_state[:, 0, :]

    # 임베딩 결합
    combined_embeddings = (ko_embeddings + bert_embeddings) / 2  # 평균을 사용하여 결합
    return combined_embeddings

from sklearn.metrics.pairwise import cosine_similarity

def find_most_similar_word(input_text, answer_list):
    input_embedding = get_combined_embeddings(input_text)
    answer_embeddings = [get_combined_embeddings(answer) for answer in answer_list]

    # 코사인 유사도 계산
    similarities = cosine_similarity(input_embedding, answer_embeddings)
    most_similar_idx = similarities.argmax()
    return answer_list[most_similar_idx]
