# -*- coding: utf-8 -*-
"""
Sistema de internacionalização (i18n) do RDDownloader.

Como adicionar um novo idioma:
  1. Copie o bloco "en" abaixo para uma nova chave (ex.: "fr").
  2. Traduza cada valor. NÃO mude as chaves nem os campos entre chaves {}.
  3. Adicione o nome do idioma em LANGUAGE_NAMES.
Pronto — ele aparecerá automaticamente no seletor de idiomas do programa.
"""

# Idioma atual (alterado em tempo de execução por set_language)
_current = "pt"

# Nomes exibidos no seletor de idioma (sempre no próprio idioma)
LANGUAGE_NAMES = {
    "pt": "Português",
    "en": "English",
    "es": "Español",
}

TRANSLATIONS = {
    # ------------------------------------------------------------------ PT
    "pt": {
        "app_title": "RDDownloader — Real-Debrid",
        "group_config": "Configuração",
        "lbl_api_key": "Chave API Real-Debrid:",
        "ph_api_key": "Cole sua chave de real-debrid.com/apitoken",
        "btn_show": "Mostrar",
        "btn_hide": "Ocultar",
        "btn_verify": "Verificar conta",
        "lbl_folder": "Pasta de download:",
        "btn_choose": "Escolher...",
        "lbl_language": "Idioma:",
        "lbl_concurrent": "Downloads simultâneos:",
        "account_not_verified": "Conta: não verificada",
        "account_error": "Conta: erro",
        "account_info": "Conta: {user} ({type}) até {exp}",
        "group_add": "Adicionar download",
        "ph_magnet": "Cole aqui um link magnet, ou arraste um .torrent para a janela",
        "btn_add_magnet": "Adicionar magnet",
        "btn_open_torrent": "Abrir .torrent...",
        "col_name": "Nome",
        "col_size": "Tamanho",
        "col_progress": "Progresso",
        "col_speed": "Velocidade",
        "col_status": "Status",
        "btn_cancel_remove": "Cancelar/Remover selecionado",
        "btn_open_folder": "Abrir pasta",
        "st_queued": "Na fila...",
        "st_sending": "Enviando para o Real-Debrid...",
        "st_selecting": "Selecionando arquivos...",
        "st_rd_downloading": "Real-Debrid baixando... {pct}%",
        "st_rd_generic": "RD: {status}",
        "st_getting_links": "Obtendo links diretos...",
        "st_downloading_file": "Baixando: {name}",
        "st_done": "Concluído ({size} em {secs}s)",
        "st_canceled": "Cancelado.",
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
    },
    # ------------------------------------------------------------------ EN
    "en": {
        "app_title": "RDDownloader — Real-Debrid",
        "group_config": "Settings",
        "lbl_api_key": "Real-Debrid API key:",
        "ph_api_key": "Paste your key from real-debrid.com/apitoken",
        "btn_show": "Show",
        "btn_hide": "Hide",
        "btn_verify": "Verify account",
        "lbl_folder": "Download folder:",
        "btn_choose": "Choose...",
        "lbl_language": "Language:",
        "lbl_concurrent": "Simultaneous downloads:",
        "account_not_verified": "Account: not verified",
        "account_error": "Account: error",
        "account_info": "Account: {user} ({type}) until {exp}",
        "group_add": "Add download",
        "ph_magnet": "Paste a magnet link here, or drag a .torrent onto the window",
        "btn_add_magnet": "Add magnet",
        "btn_open_torrent": "Open .torrent...",
        "col_name": "Name",
        "col_size": "Size",
        "col_progress": "Progress",
        "col_speed": "Speed",
        "col_status": "Status",
        "btn_cancel_remove": "Cancel/Remove selected",
        "btn_open_folder": "Open folder",
        "st_queued": "Queued...",
        "st_sending": "Sending to Real-Debrid...",
        "st_selecting": "Selecting files...",
        "st_rd_downloading": "Real-Debrid downloading... {pct}%",
        "st_rd_generic": "RD: {status}",
        "st_getting_links": "Getting direct links...",
        "st_downloading_file": "Downloading: {name}",
        "st_done": "Done ({size} in {secs}s)",
        "st_canceled": "Canceled.",
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
    },
    # ------------------------------------------------------------------ ES
    "es": {
        "app_title": "RDDownloader — Real-Debrid",
        "group_config": "Configuración",
        "lbl_api_key": "Clave API de Real-Debrid:",
        "ph_api_key": "Pega tu clave de real-debrid.com/apitoken",
        "btn_show": "Mostrar",
        "btn_hide": "Ocultar",
        "btn_verify": "Verificar cuenta",
        "lbl_folder": "Carpeta de descarga:",
        "btn_choose": "Elegir...",
        "lbl_language": "Idioma:",
        "lbl_concurrent": "Descargas simultáneas:",
        "account_not_verified": "Cuenta: no verificada",
        "account_error": "Cuenta: error",
        "account_info": "Cuenta: {user} ({type}) hasta {exp}",
        "group_add": "Agregar descarga",
        "ph_magnet": "Pega aquí un enlace magnet, o arrastra un .torrent a la ventana",
        "btn_add_magnet": "Agregar magnet",
        "btn_open_torrent": "Abrir .torrent...",
        "col_name": "Nombre",
        "col_size": "Tamaño",
        "col_progress": "Progreso",
        "col_speed": "Velocidad",
        "col_status": "Estado",
        "btn_cancel_remove": "Cancelar/Quitar seleccionado",
        "btn_open_folder": "Abrir carpeta",
        "st_queued": "En cola...",
        "st_sending": "Enviando a Real-Debrid...",
        "st_selecting": "Seleccionando archivos...",
        "st_rd_downloading": "Real-Debrid descargando... {pct}%",
        "st_rd_generic": "RD: {status}",
        "st_getting_links": "Obteniendo enlaces directos...",
        "st_downloading_file": "Descargando: {name}",
        "st_done": "Completado ({size} en {secs}s)",
        "st_canceled": "Cancelado.",
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
    },
}


def available_languages():
    """Lista de (codigo, nome) para os idiomas disponíveis."""
    return [(code, LANGUAGE_NAMES.get(code, code)) for code in TRANSLATIONS]


def set_language(lang):
    global _current
    if lang in TRANSLATIONS:
        _current = lang


def current_language():
    return _current


def detect_default(system_locale):
    """Escolhe um idioma a partir do locale do sistema (ex.: 'pt_BR')."""
    if not system_locale:
        return "en"
    prefix = system_locale.split("_")[0].lower()
    return prefix if prefix in TRANSLATIONS else "en"


def tr(key, **kwargs):
    """Traduz uma chave para o idioma atual, com fallback para inglês."""
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
