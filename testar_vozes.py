import azure.cognitiveservices.speech as speechsdk
import sounddevice as sd
import numpy as np
import time
from config import AZURE_KEY, AZURE_REGION

# CONFIGURAÇÃO
def float32_to_int16(audio_float32):
    return np.clip(audio_float32 * 32768, -32768, 32767).astype(np.int16)

def normalizar_audio(audio):
    peak = np.max(np.abs(audio))
    if peak > 0:
        return 0.9 * audio / peak
    return audio

def testar_voz(voz, texto, device_id=None):
    """Testa uma voz específica"""
    try:
        print(f"\n🎤 Testando: {voz}")
        print(f"   Texto: '{texto}'")
        
        cfg = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        cfg.speech_synthesis_voice_name = voz
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
        
        res = synthesizer.speak_text_async(texto).get()
        
        if res.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio = np.frombuffer(res.audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            audio = normalizar_audio(audio)
            sd.play(float32_to_int16(audio), samplerate=16000, device=device_id)
            sd.wait()
            print(f"   ✅ Reproduzido!")
        else:
            print(f"   ❌ Erro: {res.reason}")
            
    except Exception as e:
        print(f"   ❌ Erro: {e}")
    
    time.sleep(0.5)

# VOZES PARA TESTAR
vozes_ingles = {
    "🌟 TOP 1 - AndrewMultilingual": "en-US-AndrewMultilingualNeural",
    "🌟 TOP 2 - BrianMultilingual": "en-US-BrianMultilingualNeural",
    "🌟 TOP 3 - Davis": "en-US-DavisNeural",
    "⭐ Guy (atual)": "en-US-GuyNeural",
    "⭐ Roger": "en-US-RogerNeural",
    "⭐ Tony": "en-US-TonyNeural",
    "⭐ Jason": "en-US-JasonNeural",
    "⭐ Steffan": "en-US-SteffanNeural",
}

vozes_portugues = {
    "🌟 TOP 1 - Antonio": "pt-BR-AntonioNeural",
    "🌟 TOP 2 - Fabio": "pt-BR-FabioNeural",
    "⭐ Julio": "pt-BR-JulioNeural",
    "⭐ Nicolau": "pt-BR-NicolauNeural",
    "⭐ Valério": "pt-BR-ValerioNeural",
    "⭐ Humberto": "pt-BR-HumbertoNeural",
}

# Textos de teste
texto_ingles = "Hello, my name is John. I have over five years of experience in software development, specializing in Python and cloud technologies. I'm excited about this opportunity."

texto_portugues = "Olá, meu nome é João. Tenho mais de cinco anos de experiência em desenvolvimento de software, com especialização em Python e tecnologias em nuvem. Estou muito animado com esta oportunidade."

# EXECUÇÃO
print("=" * 80)
print("🎙️  TESTE DE VOZES - TRADUTOR BIDIRECIONAL")
print("=" * 80)
print("\nVocê vai ouvir várias vozes masculinas.")
print("Anote qual você acha mais natural para usar nas entrevistas!\n")

input("Pressione ENTER para começar os testes de INGLÊS (o gringo vai ouvir)...")

print("\n" + "=" * 80)
print("🇺🇸 TESTANDO VOZES EM INGLÊS (para o gringo ouvir)")
print("=" * 80)

for nome, voz in vozes_ingles.items():
    testar_voz(voz, texto_ingles)
    time.sleep(1)

print("\n\n")
input("Pressione ENTER para começar os testes de PORTUGUÊS (você vai ouvir)...")

print("\n" + "=" * 80)
print("🇧🇷 TESTANDO VOZES EM PORTUGUÊS (você vai ouvir)")
print("=" * 80)

for nome, voz in vozes_portugues.items():
    testar_voz(voz, texto_portugues)
    time.sleep(1)

print("\n" + "=" * 80)
print("✅ TESTE CONCLUÍDO!")
print("=" * 80)
print("\n📝 VOZES MAIS NATURAIS RECOMENDADAS:")
print("\n   🇺🇸 INGLÊS (para o gringo):")
print("      1. en-US-AndrewMultilingualNeural")
print("      2. en-US-BrianMultilingualNeural")
print("      3. en-US-DavisNeural")
print("\n   🇧🇷 PORTUGUÊS (para você):")
print("      1. pt-BR-AntonioNeural")
print("      2. pt-BR-FabioNeural")
print("\n💡 Para alterar, edite as vozes no main.py nas funções:")
print("   - ao_reconhecer_voce() → voz do gringo")
print("   - ao_reconhecer_gringo() → sua voz")
print("\n🚀 Boa sorte nas entrevistas!\n")