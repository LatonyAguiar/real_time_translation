import whisper
import torch
import logging




# Carrega modelo uma vez no início (warmup)
device = "cuda" if torch.cuda.is_available() else "cpu"
model = whisper.load_model("small", device=device)  # ou "base" para ser mais rápido
logging.info(f"✅ Whisper carregado no device: {device}")

def transcribe_whisper_local(audio_path: str) -> str:
    """
    Transcreve áudio usando Whisper local na GPU.
    
    Args:
        audio_path: Caminho do arquivo de áudio
    
    Returns:
        Texto transcrito
    """
    result = model.transcribe(
        audio_path,
        language="pt",           # Força português
        fp16=True,               # Usa half-precision (2x mais rápido na GPU)
        beam_size=1,             # Reduz qualidade levemente, mas ganha velocidade
        best_of=1,               # Não faz múltiplas tentativas
        temperature=0.0,         # Determinístico (sem variação)
        condition_on_previous_text=False  # Não usa contexto anterior (mais rápido)
    )
    return result["text"].strip()