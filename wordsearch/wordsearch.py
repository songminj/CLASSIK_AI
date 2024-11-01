from transformers import BertTokenizer, TFBertModel

tokenizer = BertTokenizer.from_pretrained('bert-base-multilingual-cased')
model = TFBertModel.from_pretrained('bert-base-multilingual-cased')

def encode_query(query):
    inputs = tokenizer(query, return_tensors="tf", padding=True, truncation=True)
    outputs = model(inputs)
    return outputs.last_hidden_state

