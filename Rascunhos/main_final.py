import azure.cognitiveservices.speech as speechsdk
import logging
import time
import sounddevice as sd
import numpy as np
import scipy.signal as signal
from config import AZURE_KEY, AZURE_REGION

# =============================
# LOGS - Apenas INFO e acima
# =============================
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# =============================
# CONFIGURAÇÃO AUTOMÁTICA DE DISPOSITIVOS
# =============================
def detectar_dispositivo(nome_busca, tipo='input'):
    """Retorna o device ID baseado no nome parcial"""
    devices = sd.query_devices()
    for idx, dev in enumerate(devices):
        if nome_busca.lower() in dev['name'].lower():
            if tipo == 'input' and dev['max_input_channels'] > 0:
                return idx
            elif tipo == 'output' and dev['max_output_channels'] > 0:
                return idx
    logging.warning(f"Não encontrei dispositivo {tipo} com '{nome_busca}', use ID manual.")
    return None

# IDs automáticos
ID_MIC_VOCE = detectar_dispositivo("ME6S", 'input') or 1
ID_CABLE_OUT_GRINGO = detectar_dispositivo("CABLE Output", 'input') or 14
ID_FONES_USUARIO = detectar_dispositivo("Fone", 'output') or 17
ID_CABLE_IN_MEET = detectar_dispositivo("CABLE Input", 'output') or 9

logging.info(f"Dispositivos: MIC={ID_MIC_VOCE} | CABLE_OUT={ID_CABLE_OUT_GRINGO} | FONE={ID_FONES_USUARIO} | CABLE_IN={ID_CABLE_IN_MEET}")

# =============================
# VARIÁVEIS
# =============================
estou_falando = False
taxa_entrada_real = 44100
taxa_azure = 16000

# =============================
# UTILITÁRIOS
# =============================
def float32_to_int16(audio_float32):
    return np.clip(audio_float32 * 32768, -32768, 32767).astype(np.int16)

def normalizar_audio(audio):
    peak = np.max(np.abs(audio))
    if peak > 0:
        return 0.9 * audio / peak
    return audio

# =============================
# AZURE
# =============================
def criar_config_traducao(origem, destino):
    cfg = speechsdk.translation.SpeechTranslationConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    cfg.speech_recognition_language = origem
    cfg.add_target_language(destino)
    cfg.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "5000")
    cfg.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "800")
    cfg.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "800")
    return cfg

formato_audio = speechsdk.audio.AudioStreamFormat(samples_per_second=taxa_azure, bits_per_sample=16, channels=1)
push_voce = speechsdk.audio.PushAudioInputStream(stream_format=formato_audio)
push_gringo = speechsdk.audio.PushAudioInputStream(stream_format=formato_audio)

rec_voce = speechsdk.translation.TranslationRecognizer(
    translation_config=criar_config_traducao("pt-BR", "en"),
    audio_config=speechsdk.audio.AudioConfig(stream=push_voce)
)

rec_gringo = speechsdk.translation.TranslationRecognizer(
    translation_config=criar_config_traducao("en-US", "pt-BR"),
    audio_config=speechsdk.audio.AudioConfig(stream=push_gringo)
)

# =============================
# SINTETIZADOR
# =============================
def sintetizar_audio(texto, voz, device_id):
    if not texto: return
    
    try:
        cfg = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
        cfg.speech_synthesis_voice_name = voz
        synthesizer = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
        res = synthesizer.speak_text_async(texto).get()
        
        if res.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            audio = np.frombuffer(res.audio_data, dtype=np.int16).astype(np.float32) / 32768.0
            audio = normalizar_audio(audio)
            sd.play(float32_to_int16(audio), samplerate=taxa_azure, device=device_id)
            sd.wait()
        elif res.reason == speechsdk.ResultReason.Canceled:
            logging.error(f"❌ Erro na síntese: {res.cancellation_details.error_details}")
            
    except Exception as e:
        logging.error(f"❌ Erro ao sintetizar: {e}")

# =============================
# CALLBACKS
# =============================
def ao_reconhecer_voce(evt):
    if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
        traducao = evt.result.translations.get("en")
        if traducao:
            logging.info(f"VOCÊ: {evt.result.text}")
            logging.info(f"  ➜  GRINGO OUVE: {traducao}")
            global estou_falando
            estou_falando = True
            # sintetizar_audio(traducao, "en-US-AndrewMultilingualNeural", ID_CABLE_IN_MEET)
            sintetizar_audio(traducao, "en-US-BrianMultilingualNeural", ID_CABLE_IN_MEET)
            # sintetizar_audio(traducao, "en-US-GuyNeural", ID_CABLE_IN_MEET)
            # sintetizar_audio(traducao, "en-US-RogerNeural", ID_CABLE_IN_MEET)
            estou_falando = False

def ao_reconhecer_gringo(evt):
    if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
        traducao = evt.result.translations.get("pt-BR") or evt.result.translations.get("pt")
        if traducao:
            logging.info(f"GRINGO: {evt.result.text}")
            logging.info(f"  ➜  VOCÊ OUVE: {traducao}")
            # sintetizar_audio(traducao, "pt-BR-AntonioNeural", ID_FONES_USUARIO)
            sintetizar_audio(traducao, "pt-BR-JulioNeural", ID_FONES_USUARIO)

# =============================
# PONTES DE ÁUDIO
# =============================
def ponte_audio(indata, frames, time, status, push_stream, is_gringo=False):
    if status: logging.warning(f"Stream Status: {status}")
    if is_gringo and estou_falando: return
    
    audio = indata.flatten().astype(np.float32)
    audio = normalizar_audio(audio)
    if np.linalg.norm(audio)/np.sqrt(len(audio)) < 0.01:
        audio = np.zeros_like(audio)
    num_samples = int(len(audio) * taxa_azure / taxa_entrada_real)
    resampled = signal.resample(audio, num_samples)
    push_stream.write(float32_to_int16(resampled).tobytes())

# =============================
# CONEXÃO AZURE
# =============================
rec_voce.recognized.connect(ao_reconhecer_voce)
rec_gringo.recognized.connect(ao_reconhecer_gringo)

# =============================
# EXECUÇÃO
# =============================
try:
    stream_voce = sd.InputStream(device=ID_MIC_VOCE, channels=1, samplerate=taxa_entrada_real,
                                 dtype='int16', callback=lambda i,f,t,s: ponte_audio(i,f,t,s,push_voce))
    stream_gringo = sd.InputStream(device=ID_CABLE_OUT_GRINGO, channels=1, samplerate=taxa_entrada_real,
                                   dtype='int16', callback=lambda i,f,t,s: ponte_audio(i,f,t,s,push_gringo, True))
    
    stream_voce.start()
    stream_gringo.start()
    
    rec_voce.start_continuous_recognition()
    rec_gringo.start_continuous_recognition()
    
    logging.info("🚀 Sistema ativo! Traduções em tempo real PT ↔ EN")
    
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    logging.info("⏹️  Sistema encerrado pelo usuário")
except Exception as e:
    logging.error(f"❌ Erro crítico: {e}")
finally:
    rec_voce.stop_continuous_recognition()
    rec_gringo.stop_continuous_recognition()