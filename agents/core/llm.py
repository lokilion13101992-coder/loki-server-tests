from llama_cpp import Llama

MODEL_PATH = "/root/nexus-core/models/mistral.gguf"

llm = Llama(
    model_path=MODEL_PATH,
    n_ctx=4096,
    n_threads=8,
    verbose=False
)

def ask_llm(prompt: str):
    output = llm(
        prompt,
        max_tokens=300,
        temperature=0.7,
        stop=["</s>"]
    )
    return output["choices"][0]["text"]
