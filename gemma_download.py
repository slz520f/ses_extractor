# gemma_download.py
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "google/gemma-2b-it"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    torch_dtype="auto"
)

# モデル保存（ローカルキャッシュにも保存されます）
model.save_pretrained("models/gemma-2b-transformers")
tokenizer.save_pretrained("models/gemma-2b-transformers")