import azure.cognitiveservices.speech as speechsdk
import logging
import time
import sounddevice as sd
import numpy as np
import scipy.signal as signal
from config import AZURE_KEY, AZURE_REGION
import threading
import queue
import warnings

# Suprime warnings
warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

# CONFIGURAÇÃO AUTOMÁTICA DE DISPOSITIVOS
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

# VARIÁVEIS DE CONTROLE ANTI-LOOP E VAD
estou_falando = False
estou_falando_lock = threading.Lock()
timestamp_ultima_sintese = 0
taxa_entrada_real = 44100
taxa_azure = 16000

# 🎤 VAD - Voice Activity Detection (economia de custos)
VAD_THRESHOLD = 0.01  # Limiar de energia para detectar voz (ajustável)
VAD_MIN_FRAMES = 3    # Frames consecutivos com voz para confirmar
vad_contador_voce = 0
vad_contador_gringo = 0

# Filas para processamento assíncrono
fila_sintese_gringo = queue.Queue()
fila_sintese_voce = queue.Queue()

# UTILITÁRIOS
def float32_to_int16(audio_float32):
    return np.clip(audio_float32 * 32768, -32768, 32767).astype(np.int16)

def normalizar_audio(audio):
    peak = np.max(np.abs(audio))
    if peak > 0:
        return 0.9 * audio / peak
    return audio

def calcular_duracao_audio(texto, taxa=16000, wpm=150):
    """Calcula duração estimada do áudio em segundos"""
    # WPM = palavras por minuto (150 é velocidade média de fala)
    palavras = len(texto.split())
    duracao_fala = (palavras / wpm) * 60
    # Adiciona margem de segurança de 30%
    return duracao_fala * 1.3 + 0.5  # +0.5s de buffer extra

# AZURE - CONFIGURAÇÃO OTIMIZADA

# ⏱️ AJUSTE SEU TIMING AQUI:
# - 400ms = Rápido (pausas curtas)
# - 600ms = Normal (RECOMENDADO) ✅
# - 800ms = Pausado (tempo para pensar)
TIMEOUT_SILENCIO = "600"  # Milissegundos

def criar_config_traducao(origem, destino):
    cfg = speechsdk.translation.SpeechTranslationConfig(subscription=AZURE_KEY, region=AZURE_REGION)
    cfg.speech_recognition_language = origem
    cfg.add_target_language(destino)

    # Timeout inicial (antes de começar a falar)
    cfg.set_property(speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "3000")

    # 🎯 TIMEOUT DE SILÊNCIO (quando você pausa)
    cfg.set_property(speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, TIMEOUT_SILENCIO)
    cfg.set_property(speechsdk.PropertyId.Speech_SegmentationSilenceTimeoutMs, TIMEOUT_SILENCIO)

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

# Isso evita que ele confunda "Visão" com "Prisão" ou erre seu nome.
def configurar_dicionario(recognizer, termos):
    phrase_list = speechsdk.PhraseListGrammar.from_recognizer(recognizer)
    for termo in termos:
        phrase_list.addPhrase(termo)
    logging.info(f"✅ Dicionário técnico aplicado!")

# Lista de termos críticos para sua área
meus_termos = [
    "Latonny Aguiar", "OCR", "RAG", "ChromaDB", "Pinecone", 
    "PGVector", "Machine Learning", "Inteligência Artificial", 
    "Visão Computacional", "Front-end", "Back-end", "Sistemas da Informação",
    "Python", "Azure", "JSON", "API", "Vector Database", "Fluxos conversacionais", "Otimização de prompt"
]

configurar_dicionario(rec_voce, meus_termos)
configurar_dicionario(rec_gringo, meus_termos)

# SINTETIZADOR COM PROTEÇÃO ANTI-LOOP
def sintetizar_audio_worker(fila, device_id, voz, is_para_gringo=False):
    """Worker thread que processa a fila de síntese"""
    global estou_falando, timestamp_ultima_sintese
    
    while True:
        try:
            texto = fila.get()
            if texto is None:
                break
                
            if not texto:
                continue
            
            # 🔒 BLOQUEIA microfone do gringo ANTES de sintetizar
            if is_para_gringo:
                with estou_falando_lock:
                    estou_falando = True
                    timestamp_ultima_sintese = time.time()
            
            # Calcula duração estimada
            duracao_estimada = calcular_duracao_audio(texto)
            
            cfg = speechsdk.SpeechConfig(subscription=AZURE_KEY, region=AZURE_REGION)
            cfg.speech_synthesis_voice_name = voz
            cfg.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Raw16Khz16BitMonoPcm
            )
            
            synthesizer = speechsdk.SpeechSynthesizer(speech_config=cfg, audio_config=None)
            res = synthesizer.speak_text_async(texto).get()
            
            if res.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                audio = np.frombuffer(res.audio_data, dtype=np.int16).astype(np.float32) / 32768.0
                audio = normalizar_audio(audio)
                
                # Reproduz o áudio
                sd.play(float32_to_int16(audio), samplerate=taxa_azure, device=device_id)
                sd.wait()  # Espera terminar
                
                # 🔓 LIBERA microfone do gringo DEPOIS de reproduzir
                if is_para_gringo:
                    # Aguarda um tempo extra baseado na duração
                    time.sleep(duracao_estimada * 0.2)  # 20% extra de segurança
                    
                    with estou_falando_lock:
                        estou_falando = False
                        timestamp_ultima_sintese = time.time()
                        
            elif res.reason == speechsdk.ResultReason.Canceled:
                details = res.cancellation_details.error_details
                if "unauthorized" in details.lower() or "quota" in details.lower():
                    logging.error(f"❌ Erro crítico: {details}")
                    
                # Libera mesmo se der erro
                if is_para_gringo:
                    with estou_falando_lock:
                        estou_falando = False
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            if "key" in str(e).lower() or "quota" in str(e).lower():
                logging.error(f"❌ Erro: {e}")
            
            # Garante que libera mesmo com erro
            if is_para_gringo:
                with estou_falando_lock:
                    estou_falando = False
        finally:
            try:
                fila.task_done()
            except:
                pass

# INICIALIZA WORKERS DE SÍNTESE
worker_gringo = threading.Thread(
    target=sintetizar_audio_worker,
    args=(fila_sintese_gringo, ID_CABLE_IN_MEET, "en-US-AndrewMultilingualNeural", True),  # 🔥 is_para_gringo=True
    daemon=True
)
worker_gringo.start()

worker_voce = threading.Thread(
    target=sintetizar_audio_worker,
    args=(fila_sintese_voce, ID_FONES_USUARIO, "pt-BR-AntonioNeural", False),
    daemon=True
)
worker_voce.start()

# CALLBACKS COM TRANSCRIÇÃO AO VIVO
ultimo_texto_voce = ""
ultimo_texto_gringo = ""

def ao_reconhecer_voce(evt):
    """Callback quando VOCÊ termina de falar uma frase"""
    global ultimo_texto_voce, ultimo_texto_parcial_voce, ultimo_tempo_voce
    
    if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
        traducao = evt.result.translations.get("en")
        if traducao and traducao != ultimo_texto_voce:
            ultimo_texto_voce = traducao
            
            # Mostra atualização final se necessário
            if evt.result.text != ultimo_texto_parcial_voce:
                print(f"💬 VOCÊ: {evt.result.text}")
                print(f"   → EN: {traducao}")
            
            print("─" * 80)
            logging.info(f"✅ VOCÊ: {evt.result.text}")
            logging.info(f"   ➜  GRINGO OUVE: {traducao}")
            print("─" * 80)
            print()
            
            # Enfileira síntese (o worker gerencia o bloqueio)
            fila_sintese_gringo.put(traducao)
            
            # Reset do cache
            ultimo_texto_parcial_voce = ""
            ultimo_tempo_voce = 0

def ao_reconhecer_gringo(evt):
    """Callback quando o GRINGO termina de falar uma frase"""
    global ultimo_texto_gringo, ultimo_texto_parcial_gringo, ultimo_tempo_gringo, timestamp_ultima_sintese
    
    if evt.result.reason == speechsdk.ResultReason.TranslatedSpeech:
        # 🛡️ PROTEÇÃO ANTI-LOOP: Ignora se acabou de sintetizar (provável eco)
        tempo_desde_sintese = time.time() - timestamp_ultima_sintese
        if tempo_desde_sintese < 2.0:  # Menos de 2s desde última síntese = provável eco
            logging.debug(f"⚠️ Ignorando provável eco (tempo: {tempo_desde_sintese:.2f}s)")
            return
        
        traducao = evt.result.translations.get("pt-BR") or evt.result.translations.get("pt")
        if traducao and traducao != ultimo_texto_gringo:
            ultimo_texto_gringo = traducao
            
            # Mostra atualização final se necessário
            if evt.result.text != ultimo_texto_parcial_gringo:
                print(f"🌐 GRINGO: {evt.result.text}")
                print(f"   → PT: {traducao}")
            
            print("─" * 80)
            logging.info(f"✅ GRINGO: {evt.result.text}")
            logging.info(f"   ➜  VOCÊ OUVE: {traducao}")
            print("─" * 80)
            print()
            
            fila_sintese_voce.put(traducao)
            
            # Reset do cache
            ultimo_texto_parcial_gringo = ""
            ultimo_tempo_gringo = 0

# ⚡ TRANSCRIÇÃO AO VIVO
ultimo_texto_parcial_voce = ""
ultimo_texto_parcial_gringo = ""
ultimo_tempo_voce = 0
ultimo_tempo_gringo = 0

def ao_reconhecer_parcial_voce(evt):
    """Mostra o que VOCÊ está falando em tempo real"""
    global ultimo_texto_parcial_voce, ultimo_tempo_voce
    
    if evt.result.reason == speechsdk.ResultReason.TranslatingSpeech:
        texto = evt.result.text
        traducao = evt.result.translations.get("en", "")
        
        palavras_anteriores = len(ultimo_texto_parcial_voce.split())
        palavras_atuais = len(texto.split())
        palavras_novas = palavras_atuais - palavras_anteriores
        
        tempo_atual = time.time()
        tempo_decorrido = tempo_atual - ultimo_tempo_voce
        
        if texto and (palavras_novas >= 5 or tempo_decorrido >= 2.0):
            ultimo_texto_parcial_voce = texto
            ultimo_tempo_voce = tempo_atual
            
            if traducao:
                print(f"💬 VOCÊ: {texto}")
                print(f"   → EN: {traducao}")
            else:
                print(f"💬 VOCÊ: {texto}")

def ao_reconhecer_parcial_gringo(evt):
    """Mostra o que o GRINGO está falando em tempo real"""
    global ultimo_texto_parcial_gringo, ultimo_tempo_gringo, timestamp_ultima_sintese
    
    if evt.result.reason == speechsdk.ResultReason.TranslatingSpeech:
        # 🛡️ Ignora parciais se acabou de sintetizar
        tempo_desde_sintese = time.time() - timestamp_ultima_sintese
        if tempo_desde_sintese < 2.0:
            return
        
        texto = evt.result.text
        traducao = evt.result.translations.get("pt-BR") or evt.result.translations.get("pt", "")
        
        palavras_anteriores = len(ultimo_texto_parcial_gringo.split())
        palavras_atuais = len(texto.split())
        palavras_novas = palavras_atuais - palavras_anteriores
        
        tempo_atual = time.time()
        tempo_decorrido = tempo_atual - ultimo_tempo_gringo
        
        if texto and (palavras_novas >= 5 or tempo_decorrido >= 2.0):
            ultimo_texto_parcial_gringo = texto
            ultimo_tempo_gringo = tempo_atual
            
            if traducao:
                print(f"🌐 GRINGO: {texto}")
                print(f"   → PT: {traducao}")
            else:
                print(f"🌐 GRINGO: {texto}")

# PONTES DE ÁUDIO COM PROTEÇÃO ROBUSTA E VAD
def ponte_audio(indata, frames, time_info, status, push_stream, is_gringo=False):
    global vad_contador_voce, vad_contador_gringo
    
    if status:
        logging.warning(f"Stream Status: {status}")
    
    # 🛡️ PROTEÇÃO ANTI-LOOP: Bloqueia áudio do gringo se estiver sintetizando
    if is_gringo:
        with estou_falando_lock:
            if estou_falando:
                # Envia silêncio em vez do áudio
                silence = np.zeros(len(indata), dtype=np.int16)
                resampled_silence = signal.resample(silence, int(len(silence) * taxa_azure / taxa_entrada_real))
                push_stream.write(resampled_silence.astype(np.int16).tobytes())
                return
    
    audio = indata.flatten().astype(np.float32)
    audio = normalizar_audio(audio)
    
    # 🎤 VAD - Voice Activity Detection (economia de $$)
    energia = np.linalg.norm(audio) / np.sqrt(len(audio))
    tem_voz = energia > VAD_THRESHOLD
    
    if is_gringo:
        # Conta frames consecutivos com voz
        if tem_voz:
            vad_contador_gringo += 1
        else:
            vad_contador_gringo = max(0, vad_contador_gringo - 1)
        
        # Só envia se detectou voz consistente
        if vad_contador_gringo < VAD_MIN_FRAMES:
            # 💰 ECONOMIA: Não envia silêncio pro Azure
            return
    else:  # Você falando
        if tem_voz:
            vad_contador_voce += 1
        else:
            vad_contador_voce = max(0, vad_contador_voce - 1)
        
        if vad_contador_voce < VAD_MIN_FRAMES:
            # 💰 ECONOMIA: Não envia silêncio pro Azure
            return
    
    # Se chegou aqui, tem voz de verdade - processa e envia
    if energia < 0.01:
        audio = np.zeros_like(audio)
    
    num_samples = int(len(audio) * taxa_azure / taxa_entrada_real)
    resampled = signal.resample(audio, num_samples)
    push_stream.write(float32_to_int16(resampled).tobytes())

# CONEXÃO AZURE
rec_voce.recognized.connect(ao_reconhecer_voce)
rec_gringo.recognized.connect(ao_reconhecer_gringo)
rec_voce.recognizing.connect(ao_reconhecer_parcial_voce)
rec_gringo.recognizing.connect(ao_reconhecer_parcial_gringo)

# EXECUÇÃO COM TRATAMENTO ROBUSTO
try:
    stream_voce = sd.InputStream(device=ID_MIC_VOCE, channels=1, samplerate=taxa_entrada_real,
                                 dtype='int16', callback=lambda i,f,t,s: ponte_audio(i,f,t,s,push_voce))
    stream_gringo = sd.InputStream(device=ID_CABLE_OUT_GRINGO, channels=1, samplerate=taxa_entrada_real,
                                   dtype='int16', callback=lambda i,f,t,s: ponte_audio(i,f,t,s,push_gringo, True))
    
    stream_voce.start()
    stream_gringo.start()
    
    rec_voce.start_continuous_recognition()
    rec_gringo.start_continuous_recognition()
    
    logging.info("=" * 80)
    logging.info("🚀 TRADUTOR BIDIRECIONAL ATIVO - PROTEÇÃO ANTI-LOOP ATIVADA!")
    logging.info("=" * 80)
    logging.info("💬 Você verá a transcrição em TEMPO REAL enquanto fala")
    logging.info("🎤 O áudio completo é sintetizado apenas quando terminar a frase")
    logging.info("🛡️  Proteção anti-loop: microfone do gringo bloqueado durante síntese")
    logging.info("💰 VAD ativado: só envia áudio quando detecta voz (economia de custos)")
    logging.info("⚡ Latência otimizada: ~1 segundo após terminar de falar")
    logging.info("=" * 80)
    print()
    
    while True:
        try:
            time.sleep(0.1)
        except Exception as e:
            logging.error(f"Erro no loop: {e}")
            continue

except KeyboardInterrupt:
    print("\n")
    logging.info("⏹️  Sistema encerrado pelo usuário")
except Exception as e:
    logging.error(f"❌ Erro crítico: {e}")
    import traceback
    traceback.print_exc()
finally:
    try:
        rec_voce.stop_continuous_recognition()
        rec_gringo.stop_continuous_recognition()
        fila_sintese_gringo.put(None)
        fila_sintese_voce.put(None)
    except:
        pass