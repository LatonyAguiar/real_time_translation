import azure.cognitiveservices.speech as speechsdk
import logging
import time
import sounddevice as sd
import numpy as np
import scipy.signal as signal
from config import AZURE_KEY, AZURE_REGION
import threading
import queue

# =============================
# LOGS
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

# Filas para processamento assíncrono
fila_sintese_gringo = queue.Queue()
fila_sintese_voce = queue.Queue()

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
# AZURE - CONFIGURAÇÃO OTIMIZADA
# =============================
def criar_config_traducao(origem, destino):
    cfg = speechsdk.translation.SpeechTranslationConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    cfg.speech_recognition_language = origem
    cfg.add_target_language(destino)
    
    # ⚡ TIMEOUTS ULTRA-OTIMIZADOS PARA BAIXA LATÊNCIA
    cfg.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "3000")  # Reduzido
    cfg.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "500")      # Mais agressivo
    cfg.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, "500")              # Mais agressivo
    
    # ⚡ ATIVA RESULTADOS PARCIAIS (baixa latência)
    cfg.set_property(speechsdk.PropertyId.SpeechServiceResponse_RequestWordLevelTimestamps, "true")
    cfg.set_property(speechsdk.PropertyId.SpeechServiceResponse_PostProcessingOption, "TrueText")
    
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
# SINTETIZADOR COM FILA ASSÍNCRONA
# =============================
def sintetizar_audio_worker(fila, device_id, voz):
    """Worker thread que processa a fila de síntese"""
    while True:
        try:
            texto = fila.get()
            if texto is None:  # Sinal de parada
                break
                
            if not texto:
                continue
            
            cfg = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
            cfg.speech_synthesis_voice_name = voz
            
            # ⚡ CONFIGURAÇÕES DE BAIXA LATÊNCIA
            cfg.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm
            )
            
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
            logging.error(f"❌ Erro no worker de síntese: {e}")
        finally:
            fila.task_done()

# =============================
# INICIALIZA WORKERS DE SÍNTESE
# =============================
# Worker para voz que o gringo ouve
worker_gringo = threading.Thread(
    target=sintetizar_audio_worker,
    args=(fila_sintese_gringo, ID_CABLE_IN_MEET, "en-US-AndrewMultilingualNeural"),
    daemon=True
)
worker_gringo.start()

# Worker para voz que você ouve
worker_voce = threading.Thread(
    target=sintetizar_audio_worker,
    args=(fila_sintese_voce, ID_FONES_USUARIO, "pt-BR-AntonioNeural"),
    daemon=True
)
worker_voce.start()

# =============================
# CALLBACKS OTIMIZADOS
# =============================
ultimo_texto_voce = ""
ultimo_texto_gringo = ""

def ao_reconhecer_voce(evt):
    """Callback otimizado - detecta fim de frase rapidamente"""
    global ultimo_texto_voce, estou_falando
    
    if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
        traducao = evt.result.translations.get("en")
        if traducao and traducao != ultimo_texto_voce:
            ultimo_texto_voce = traducao
            logging.info(f"VOCÊ: {evt.result.text}")
            logging.info(f"  ➜  GRINGO OUVE: {traducao}")
            
            estou_falando = True
            fila_sintese_gringo.put(traducao)  # ⚡ Adiciona na fila
            
            # Libera flag depois de um tempinho
            threading.Timer(0.5, lambda: setattr(globals(), 'estou_falando', False)).start()

def ao_reconhecer_gringo(evt):
    """Callback otimizado - processa traduções rapidamente"""
    global ultimo_texto_gringo
    
    if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
        traducao = evt.result.translations.get("pt-BR") or evt.result.translations.get("pt")
        if traducao and traducao != ultimo_texto_gringo:
            ultimo_texto_gringo = traducao
            logging.info(f"GRINGO: {evt.result.text}")
            logging.info(f"  ➜  VOCÊ OUVE: {traducao}")
            
            fila_sintese_voce.put(traducao)  # ⚡ Adiciona na fila

# ⚡ NOVO: Callbacks para resultados PARCIAIS (menor latência)
def ao_reconhecer_parcial_voce(evt):
    """Detecta fala em progresso para reduzir latência percebida"""
    if evt.result.text and len(evt.result.text) > 10:
        # Pode adicionar feedback visual aqui se quiser
        pass

def ao_reconhecer_parcial_gringo(evt):
    """Detecta fala em progresso para reduzir latência percebida"""
    if evt.result.text and len(evt.result.text) > 10:
        # Pode adicionar feedback visual aqui se quiser
        pass

# =============================
# PONTES DE ÁUDIO
# =============================
def ponte_audio(indata, frames, time, status, push_stream, is_gringo=False):
    if status: 
        logging.warning(f"Stream Status: {status}")
    
    if is_gringo and estou_falando:
        return
    
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

# ⚡ Adiciona callbacks de reconhecimento parcial (baixa latência)
rec_voce.recognizing.connect(ao_reconhecer_parcial_voce)
rec_gringo.recognizing.connect(ao_reconhecer_parcial_gringo)

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
    
    logging.info("🚀 Sistema ativo com BAIXA LATÊNCIA! PT ↔ EN")
    logging.info("⚡ Processamento assíncrono ativado")
    logging.info("💡 Fale naturalmente - o sistema processa em tempo real")
    
    while True:
        time.sleep(1)

except KeyboardInterrupt:
    logging.info("⏹️  Sistema encerrado pelo usuário")
except Exception as e:
    logging.error(f"❌ Erro crítico: {e}")
finally:
    rec_voce.stop_continuous_recognition()
    rec_gringo.stop_continuous_recognition()
    
    # Para os workers
    fila_sintese_gringo.put(None)
    fila_sintese_voce.put(None)