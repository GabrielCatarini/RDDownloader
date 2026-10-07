# -*- coding: utf-8 -*-
"""
RDDownloader translations (i18n).

To add a language:
  1. Copy the "en" block below under a new ISO 639-1 code (e.g. "fr").
  2. Translate the values only. Do NOT change the keys or the {fields}.
  3. Add the language name to LANGUAGE_NAMES.
It then shows up automatically in the app's language selector.
"""

# Current language (changed at runtime by set_language)
_current = "pt"

# Names shown in the language selector (each in its own language)
LANGUAGE_NAMES = {
    "pt": "Português",
    "en": "English",
    "es": "Español",
}

TRANSLATIONS = {
    # ------------------------------------------------------------------ PT
    "pt": {
        "err_download_range": "Resposta inválida ao retomar o download.",
        "err_download_incomplete": "O arquivo recebido está incompleto.",
        "app_title": "RDDownloader — Real-Debrid",
        "group_config": "Configurações",
        "lbl_api_key": "Chave API",
        "ph_api_key": "Cole sua chave de real-debrid.com/apitoken",
        "btn_show": "Mostrar",
        "btn_hide": "Ocultar",
        "btn_verify": "Salvar e verificar",
        "lbl_folder": "Pasta de download",
        "btn_choose": "Escolher…",
        "lbl_language": "Idioma",
        "lbl_concurrent": "Downloads simultâneos",
        "account_not_verified": "Conta não verificada",
        "account_error": "Chave inválida ou sem conexão",
        "account_info": "{user} · {type} · {exp}",
        "group_add": "Novo download",
        "ph_magnet": "Cole aqui um link magnet (magnet:?xt=…)",
        "btn_add_magnet": "Baixar",
        "btn_open_torrent": "Abrir .torrent",
        "col_name": "Nome",
        "col_size": "Tamanho",
        "col_progress": "Progresso",
        "col_speed": "Velocidade",
        "col_status": "Status",
        "btn_open_folder": "Abrir pasta",
        "btn_pause": "Pausar",
        "btn_resume": "Retomar",
        "menu_copy_download_url": "Copiar URL direta do Real-Debrid",
        "menu_url_unavailable": "URL disponível quando o download do arquivo iniciar",
        "st_queued": "Na fila...",
        "st_sending": "Enviando para o Real-Debrid...",
        "st_selecting": "Selecionando arquivos...",
        "st_rd_downloading": "Real-Debrid baixando... {pct}%",
        "st_rd_generic": "RD: {status}",
        "st_getting_links": "Obtendo links diretos...",
        "st_downloading_file": "Baixando: {name}",
        "st_done": "Concluído · {size} em {elapsed}",
        "st_canceled": "Cancelado.",
        "st_paused": "Pausado.",
        "st_retry": "Erro de rede — nova tentativa em {secs}s ({n}/{max})",
        "err_prefix": "ERRO: ",
        "title_warning": "Atenção",
        "title_error": "Falha",
        "title_notice": "Aviso",
        "msg_need_key": "Cole sua chave API primeiro.",
        "msg_need_folder": "Escolha a pasta de download.",
        "msg_bad_magnet": "Isso não parece um link magnet válido.",
        "msg_not_premium": "Sua conta não está como 'premium'. O download pode falhar.",
        "dlg_choose_folder": "Escolher pasta de download",
        "dlg_choose_torrent": "Escolher arquivo .torrent",
        "dlg_torrent_filter": "Arquivos torrent (*.torrent)",
        "err_invalid_key": "Chave API inválida ou expirada (401).",
        "err_forbidden": "Acesso negado (403). Conta sem premium?",
        "err_status": "Erro {code}: {msg}",
        "err_network": "Erro de rede: {err}",
        "err_generic": "Erro: {err}",
        "err_rd_status": "Real-Debrid retornou o status '{status}'.",
        "err_no_links": "Nenhum link disponível neste torrent.",
        "notify_done_title": "Download concluído",
        "notify_done_body": "{name} terminou.",
        "app_subtitle": "Baixe torrents e magnets via Real-Debrid",
        "btn_settings": "⚙  Configurações",
        "key_help": "Não tem a chave? Faça login no Real-Debrid e copie em {link}",
        "account_checking": "Verificando conta…",
        "account_no_key": "Configure sua chave API",
        "hint_drop": "Dica: arraste arquivos .torrent ou links magnet para qualquer lugar da janela.",
        "hint_drop_now": "Solte para adicionar à fila ⬇",
        "group_downloads": "Downloads",
        "counter": "{total} · {active} em andamento",
        "empty_title": "Nenhum download por aqui",
        "empty_body": "Cole um link magnet acima ou arraste um arquivo .torrent para esta janela.",
        "btn_remove": "Remover",
        "btn_clear_done": "Limpar finalizados",
        "menu_retry": "Tentar novamente",
        "hint_retry": "Clique duas vezes para tentar novamente.",
        "st_rd_converting": "Convertendo magnet no Real-Debrid…",
        "st_rd_queued": "Na fila do Real-Debrid…",
        "st_rd_processing": "Real-Debrid processando… {pct}%",
        "title_quit": "Sair do RDDownloader?",
        "msg_quit_active": "Há {n} download(s) em andamento. Se sair agora, eles serão cancelados.",
    },
    # ------------------------------------------------------------------ EN
    "en": {
        "err_download_range": "Invalid response when resuming the download.",
        "err_download_incomplete": "The downloaded file is incomplete.",
        "app_title": "RDDownloader — Real-Debrid",
        "group_config": "Settings",
        "lbl_api_key": "API key",
        "ph_api_key": "Paste your key from real-debrid.com/apitoken",
        "btn_show": "Show",
        "btn_hide": "Hide",
        "btn_verify": "Save & verify",
        "lbl_folder": "Download folder",
        "btn_choose": "Choose…",
        "lbl_language": "Language",
        "lbl_concurrent": "Simultaneous downloads",
        "account_not_verified": "Account not verified",
        "account_error": "Invalid key or no connection",
        "account_info": "{user} · {type} · {exp}",
        "group_add": "New download",
        "ph_magnet": "Paste a magnet link here (magnet:?xt=…)",
        "btn_add_magnet": "Download",
        "btn_open_torrent": "Open .torrent",
        "col_name": "Name",
        "col_size": "Size",
        "col_progress": "Progress",
        "col_speed": "Speed",
        "col_status": "Status",
        "btn_open_folder": "Open folder",
        "btn_pause": "Pause",
        "btn_resume": "Resume",
        "menu_copy_download_url": "Copy Real-Debrid direct URL",
        "menu_url_unavailable": "URL available when the file download starts",
        "st_queued": "Queued...",
        "st_sending": "Sending to Real-Debrid...",
        "st_selecting": "Selecting files...",
        "st_rd_downloading": "Real-Debrid downloading... {pct}%",
        "st_rd_generic": "RD: {status}",
        "st_getting_links": "Getting direct links...",
        "st_downloading_file": "Downloading: {name}",
        "st_done": "Done · {size} in {elapsed}",
        "st_canceled": "Canceled.",
        "st_paused": "Paused.",
        "st_retry": "Network error — retry in {secs}s ({n}/{max})",
        "err_prefix": "ERROR: ",
        "title_warning": "Warning",
        "title_error": "Failed",
        "title_notice": "Notice",
        "msg_need_key": "Paste your API key first.",
        "msg_need_folder": "Choose the download folder.",
        "msg_bad_magnet": "That does not look like a valid magnet link.",
        "msg_not_premium": "Your account is not 'premium'. Downloads may fail.",
        "dlg_choose_folder": "Choose download folder",
        "dlg_choose_torrent": "Choose .torrent file",
        "dlg_torrent_filter": "Torrent files (*.torrent)",
        "err_invalid_key": "Invalid or expired API key (401).",
        "err_forbidden": "Access denied (403). Non-premium account?",
        "err_status": "Error {code}: {msg}",
        "err_network": "Network error: {err}",
        "err_generic": "Error: {err}",
        "err_rd_status": "Real-Debrid returned status '{status}'.",
        "err_no_links": "No links available in this torrent.",
        "notify_done_title": "Download complete",
        "notify_done_body": "{name} finished.",
        "app_subtitle": "Download torrents & magnets via Real-Debrid",
        "btn_settings": "⚙  Settings",
        "key_help": "No key yet? Log in to Real-Debrid and copy it from {link}",
        "account_checking": "Checking account…",
        "account_no_key": "Set up your API key",
        "hint_drop": "Tip: drag .torrent files or magnet links anywhere onto the window.",
        "hint_drop_now": "Drop to add to the queue ⬇",
        "group_downloads": "Downloads",
        "counter": "{total} · {active} in progress",
        "empty_title": "No downloads yet",
        "empty_body": "Paste a magnet link above or drag a .torrent file onto this window.",
        "btn_remove": "Remove",
        "btn_clear_done": "Clear finished",
        "menu_retry": "Try again",
        "hint_retry": "Double-click to try again.",
        "st_rd_converting": "Converting magnet on Real-Debrid…",
        "st_rd_queued": "Queued on Real-Debrid…",
        "st_rd_processing": "Real-Debrid processing… {pct}%",
        "title_quit": "Quit RDDownloader?",
        "msg_quit_active": "{n} download(s) still in progress. Quitting now will cancel them.",
    },
    # ------------------------------------------------------------------ ES
    "es": {
        "err_download_range": "Respuesta inválida al reanudar la descarga.",
        "err_download_incomplete": "El archivo descargado está incompleto.",
        "app_title": "RDDownloader — Real-Debrid",
        "group_config": "Configuración",
        "lbl_api_key": "Clave API",
        "ph_api_key": "Pega tu clave de real-debrid.com/apitoken",
        "btn_show": "Mostrar",
        "btn_hide": "Ocultar",
        "btn_verify": "Guardar y verificar",
        "lbl_folder": "Carpeta de descarga",
        "btn_choose": "Elegir…",
        "lbl_language": "Idioma",
        "lbl_concurrent": "Descargas simultáneas",
        "account_not_verified": "Cuenta no verificada",
        "account_error": "Clave inválida o sin conexión",
        "account_info": "{user} · {type} · {exp}",
        "group_add": "Nueva descarga",
        "ph_magnet": "Pega aquí un enlace magnet (magnet:?xt=…)",
        "btn_add_magnet": "Descargar",
        "btn_open_torrent": "Abrir .torrent",
        "col_name": "Nombre",
        "col_size": "Tamaño",
        "col_progress": "Progreso",
        "col_speed": "Velocidad",
        "col_status": "Estado",
        "btn_open_folder": "Abrir carpeta",
        "btn_pause": "Pausar",
        "btn_resume": "Reanudar",
        "menu_copy_download_url": "Copiar URL directa de Real-Debrid",
        "menu_url_unavailable": "URL disponible cuando comience la descarga del archivo",
        "st_queued": "En cola...",
        "st_sending": "Enviando a Real-Debrid...",
        "st_selecting": "Seleccionando archivos...",
        "st_rd_downloading": "Real-Debrid descargando... {pct}%",
        "st_rd_generic": "RD: {status}",
        "st_getting_links": "Obteniendo enlaces directos...",
        "st_downloading_file": "Descargando: {name}",
        "st_done": "Completado · {size} en {elapsed}",
        "st_canceled": "Cancelado.",
        "st_paused": "Pausado.",
        "st_retry": "Error de red — reintento en {secs}s ({n}/{max})",
        "err_prefix": "ERROR: ",
        "title_warning": "Atención",
        "title_error": "Error",
        "title_notice": "Aviso",
        "msg_need_key": "Pega primero tu clave API.",
        "msg_need_folder": "Elige la carpeta de descarga.",
        "msg_bad_magnet": "Eso no parece un enlace magnet válido.",
        "msg_not_premium": "Tu cuenta no es 'premium'. Las descargas pueden fallar.",
        "dlg_choose_folder": "Elegir carpeta de descarga",
        "dlg_choose_torrent": "Elegir archivo .torrent",
        "dlg_torrent_filter": "Archivos torrent (*.torrent)",
        "err_invalid_key": "Clave API inválida o expirada (401).",
        "err_forbidden": "Acceso denegado (403). ¿Cuenta sin premium?",
        "err_status": "Error {code}: {msg}",
        "err_network": "Error de red: {err}",
        "err_generic": "Error: {err}",
        "err_rd_status": "Real-Debrid devolvió el estado '{status}'.",
        "err_no_links": "No hay enlaces disponibles en este torrent.",
        "notify_done_title": "Descarga completada",
        "notify_done_body": "{name} ha terminado.",
        "app_subtitle": "Descarga torrents y magnets vía Real-Debrid",
        "btn_settings": "⚙  Configuración",
        "key_help": "¿No tienes la clave? Inicia sesión en Real-Debrid y cópiala en {link}",
        "account_checking": "Verificando cuenta…",
        "account_no_key": "Configura tu clave API",
        "hint_drop": "Consejo: arrastra archivos .torrent o enlaces magnet a cualquier parte de la ventana.",
        "hint_drop_now": "Suelta para añadir a la cola ⬇",
        "group_downloads": "Descargas",
        "counter": "{total} · {active} en curso",
        "empty_title": "Aún no hay descargas",
        "empty_body": "Pega un enlace magnet arriba o arrastra un archivo .torrent a esta ventana.",
        "btn_remove": "Quitar",
        "btn_clear_done": "Limpiar finalizadas",
        "menu_retry": "Reintentar",
        "hint_retry": "Haz doble clic para reintentar.",
        "st_rd_converting": "Convirtiendo magnet en Real-Debrid…",
        "st_rd_queued": "En cola de Real-Debrid…",
        "st_rd_processing": "Real-Debrid procesando… {pct}%",
        "title_quit": "¿Salir de RDDownloader?",
        "msg_quit_active": "Hay {n} descarga(s) en curso. Si sales ahora, se cancelarán.",
    },
}


def available_languages():
    """List of (code, name) for the available languages."""
    return [(code, LANGUAGE_NAMES.get(code, code)) for code in TRANSLATIONS]


def set_language(lang):
    global _current
    if lang in TRANSLATIONS:
        _current = lang


def current_language():
    return _current


def detect_default(system_locale):
    """Pick a language from the system locale (e.g. 'pt_BR')."""
    if not system_locale:
        return "en"
    prefix = system_locale.split("_")[0].lower()
    return prefix if prefix in TRANSLATIONS else "en"


def tr(key, **kwargs):
    """Translate a key into the current language, falling back to English."""
    table = TRANSLATIONS.get(_current, {})
    text = table.get(key)
    if text is None:
        text = TRANSLATIONS["en"].get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text
