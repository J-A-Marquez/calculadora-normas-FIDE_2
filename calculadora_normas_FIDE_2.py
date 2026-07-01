import re
import math
import streamlit as st
import pandas as pd

# =========================================================
# CONFIGURACIÓN DE LA ESTRUCTURA INTERNA
# =========================================================
class Match:
    def __init__(self, raw_token, result="", color="", opponent=0, special="", is_valid=False):
        self.raw_token = raw_token
        self.result = result
        self.color = color
        self.opponent = opponent
        self.special = special
        self.is_valid = is_valid

class Player:
    def __init__(self, id, name, elo, title, federation):
        self.id = id
        self.name = name
        self.elo = elo
        self.title = title
        self.federation = federation
        self.matches = []

def get_title_rank(title):
    ranks = {"GM": 6, "IM": 5, "WGM": 4, "WIM": 3, "FM": 2, "WFM": 1}
    return ranks.get(title, 0)

def parse_match_token(t):
    m = Match(raw_token=t)
    match = re.match(r"^([+=-]?)([WBF])(\d+)$|^([+=-]?)(HPB|FPB)$|^(--)$", t)
    
    if match:
        m.is_valid = True
        if match.group(6):
            m.special = "--"
        elif match.group(5):
            m.result = match.group(4) if match.group(4) else ""
            m.special = match.group(5)
        elif match.group(3):
            m.result = match.group(1) if match.group(1) else ""
            m.color = match.group(2)
            m.opponent = int(match.group(3))
            
    return m

def get_player(player_id, players):
    for p in players:
        if p.id == player_id:
            return p
    return None

# Tabla p-dp integrada (Conversión oficial FIDE)
dp_table = {
    100: 800, 99: 677, 98: 589, 97: 538, 96: 501, 95: 470, 94: 444, 93: 422, 92: 401, 91: 383,
    90: 366, 89: 351, 88: 336, 87: 322, 86: 309, 85: 296, 84: 284, 83: 273, 82: 262, 81: 251,
    80: 240, 79: 230, 78: 220, 77: 211, 76: 202, 75: 193, 74: 184, 73: 175, 72: 166, 71: 158,
    70: 149, 69: 141, 68: 133, 67: 125, 66: 117, 65: 110, 64: 102, 63: 95, 62: 87, 61: 80,
    60: 72,  59: 65,  58: 57,  57: 50,  56: 43,  55: 36,  54: 29,  53: 21,  52: 14,  51: 7,
    50: 0,
    49: -7,  48: -14, 47: -21, 46: -29, 45: -36, 44: -43, 43: -50, 42: -57, 41: -65, 40: -72,
    39: -80, 38: -87, 37: -95, 36: -102,35: -110,34: -117,33: -125,32: -133,31: -141,30: -149,
    29: -158,28: -166,27: -175,26: -184,25: -193,24: -202,23: -211,22: -220,21: -230,20: -240,
    19: -251,18: -262,17: -273,16: -284,15: -296,14: -309,13: -322,12: -336,11: -351,10: -366,
    9: -383,  8: -401,  7: -422,  6: -444,  5: -470,  4: -501,  3: -538,  2: -589,  1: -677,  0: -800
}

# =========================================================
# LÓGICA DE CÁLCULO FIDE
# =========================================================
def evaluate_norm(norm_p, norm_type, players, last_opp=None):
    """Evalúa las condiciones matemáticas de una norma para un jugador dado."""
    
    if norm_type == "GM":
        target_rank, elo_threshold, elo_target, target_performance = 6, 2200, 2380, 2599.5
    elif norm_type == "IM":
        target_rank, elo_threshold, elo_target, target_performance = 5, 2050, 2230, 2449.5
    elif norm_type == "WGM":
        target_rank, elo_threshold, elo_target, target_performance = 4, 2000, 2180, 2399.5
    elif norm_type == "WIM":
        target_rank, elo_threshold, elo_target, target_performance = 3, 1850, 2030, 2249.5
    else:
        return None

    opponent_elos = []
    valid_titles_total = 0
    category_titles = 0
    federation_counts = {}
    same_fed_as_player = 0
    actual_score = 0.0
    opponent_details = []

    # Partidas reales
    for m in norm_p.matches:
        if m.opponent > 0 and m.color != "F" and not m.special:
            opp = get_player(m.opponent, players)
            if opp:
                opponent_elos.append(opp.elo)
                
                rank = get_title_rank(opp.title)
                if rank > 0:
                    valid_titles_total += 1
                    if rank >= target_rank:
                        category_titles += 1
                        
                federation_counts[opp.federation] = federation_counts.get(opp.federation, 0) + 1
                if opp.federation == norm_p.federation:
                    same_fed_as_player += 1
                
                res_str = "0"
                if m.result == "+":
                    actual_score += 1.0
                    res_str = "1"
                elif m.result == "=":
                    actual_score += 0.5
                    res_str = "0.5"
                    
                opponent_details.append({
                    "ID": opp.id, "Nombre": opp.name, "ELO": opp.elo, 
                    "Título": opp.title if opp.title else "-", "Fed": opp.federation, "Resultado": res_str
                })

    # Rival hipotético añadido
    if last_opp:
        opponent_elos.append(last_opp.elo)
        
        rank = get_title_rank(last_opp.title)
        if rank > 0:
            valid_titles_total += 1
            if rank >= target_rank:
                category_titles += 1
                
        federation_counts[last_opp.federation] = federation_counts.get(last_opp.federation, 0) + 1
        if last_opp.federation == norm_p.federation:
            same_fed_as_player += 1

        opponent_details.append({
            "ID": last_opp.id, "Nombre": last_opp.name, "ELO": last_opp.elo, 
            "Título": last_opp.title if last_opp.title else "-", "Fed": last_opp.federation, "Resultado": "?"
        })

    n = len(opponent_elos)
    if n == 0:
        return None

    # Umbral FIDE (Floor limit)
    elo_adjusted = False
    original_min_elo = 0
    min_elo = min(opponent_elos)
    
    if min_elo < elo_threshold:
        min_idx = opponent_elos.index(min_elo)
        original_min_elo = min_elo
        opponent_elos[min_idx] = elo_threshold
        elo_adjusted = True

    # ELO Medio
    avg_elo = sum(opponent_elos) / n
    max_freq = max(federation_counts.values()) if federation_counts else 0

    # Cálculo de la performance
    actual_p = actual_score / n if n > 0 else 0
    actual_p_idx = max(0, min(100, int(round(actual_p * 100.0))))
    actual_dp = dp_table.get(actual_p_idx, 0)
    actual_performance = round(avg_elo + actual_dp + 1e-9)

    # Cálculo de la puntuación mínima requerida
    min_required_score = -1.0
    s = 0.0
    while s <= n:
        p = s / n
        p_idx = max(0, min(100, int(round(p * 100.0))))
        dp = dp_table.get(p_idx, 0)
        if avg_elo + dp >= target_performance:
            min_required_score = s
            break
        s += 0.5

    # Evaluación de condiciones
    req_cat_min = max(3, math.ceil(n / 3.0))
    req_tot_min = math.ceil(n / 2.0)
    req_fed_player_max = math.floor(n * 3.0 / 5.0)
    req_fed_any_max = math.floor(n * 2.0 / 3.0)
    req_fed_diff_min = 3

    cond_elo = avg_elo >= elo_target
    cond_cat_titles = category_titles >= req_cat_min
    cond_tot_titles = valid_titles_total >= req_tot_min
    cond_fed_player = same_fed_as_player <= req_fed_player_max
    cond_fed_any = max_freq <= req_fed_any_max
    cond_fed_diff = len(federation_counts) >= req_fed_diff_min
    cond_score = (min_required_score >= 0.0 and actual_score >= min_required_score)

    norm_achieved = cond_score and cond_elo and cond_cat_titles and cond_tot_titles and cond_fed_player and cond_fed_any and cond_fed_diff

    return {
        "norm_achieved": norm_achieved, "n_games": n, "opponent_details": opponent_details,
        "avg_elo": avg_elo, "actual_score": actual_score, "actual_performance": actual_performance,
        "min_required_score": min_required_score, "target_performance": target_performance, "elo_target": elo_target,
        "category_titles": category_titles, "req_cat_min": req_cat_min, "cond_cat_titles": cond_cat_titles,
        "valid_titles_total": valid_titles_total, "req_tot_min": req_tot_min, "cond_tot_titles": cond_tot_titles,
        "same_fed_as_player": same_fed_as_player, "req_fed_player_max": req_fed_player_max, "cond_fed_player": cond_fed_player,
        "max_freq": max_freq, "req_fed_any_max": req_fed_any_max, "cond_fed_any": cond_fed_any,
        "num_feds": len(federation_counts), "req_fed_diff_min": req_fed_diff_min, "cond_fed_diff": cond_fed_diff,
        "cond_elo": cond_elo, "cond_score": cond_score, "elo_adjusted": elo_adjusted,
        "original_min_elo": original_min_elo, "elo_threshold": elo_threshold
    }

def scan_all_players_for_norms(players_list, include_womens_titles=True):
    """Escanea a todos los jugadores y devuelve una lista con las normas conseguidas."""
    successful_candidates = []
    title_hierarchy = {"GM": 4, "IM": 3, "WGM": 2, "WIM": 1, "": 0, "FM": 0, "WFM": 0, "CM": 0, "WCM": 0}
    
    for p in players_list:
        valid_matches = [m for m in p.matches if m.opponent > 0 and m.color != "F" and not m.special]
        
        # Filtro básico (mínimo 7 rondas)
        if len(valid_matches) < 7: 
            continue
            
        player_title_level = title_hierarchy.get(p.title, 0)
        norms_to_test = []
        
        if player_title_level < 4: norms_to_test.append("GM")
        if player_title_level < 3: norms_to_test.append("IM")
        
        if include_womens_titles:
            # Ahora sólo evalúa WGM/WIM si el nivel del título del jugador es inferior
            if player_title_level < 2: norms_to_test.append("WGM")
            if player_title_level < 1: norms_to_test.append("WIM")
        
        for norm_type in norms_to_test:
            res = evaluate_norm(p, norm_type, players_list)
            if res and res["norm_achieved"]:
                successful_candidates.append({
                    "ID": p.id,
                    "Jugador": p.name,
                    "Fed": p.federation,
                    "Norma": norm_type,
                    "Puntos": res["actual_score"],
                    "TPR": res["actual_performance"],
                    "Rc": round(res["avg_elo"], 1)
                })
                
    return successful_candidates

# =========================================================
# INTERFAZ WEB (STREAMLIT)
# =========================================================
st.set_page_config(page_title="Calculadora de Normas FIDE", page_icon="♟️", layout="centered")

st.title("♟️ Calculadora de Normas FIDE")
st.subheader("Creado por el Árbitro FIDE Juan Antonio Márquez León (22237364)")
st.write("Esta herramienta analiza el cuadro cruzado de un torneo suizo para verificar si un jugador cumple las condiciones para obtener una norma.")

uploaded_file = st.file_uploader("Sube aquí el archivo 'crosstable.txt' generado por el programa de emparejamientos (Vega):", type=["txt"])

if uploaded_file is not None:
    players = []
    
    try:
        content = uploaded_file.read().decode("utf-8")
    except UnicodeDecodeError:
        content = uploaded_file.read().decode("ISO-8859-1")
        
    lines = content.splitlines()
    player_re = re.compile(r"^\s*(\d+)\s+(.+?)\s+(\d+)\s+(?:([A-Z]{2,3})\s+)?([A-Z]{3})\s+[0-9.]+\s*\|")
    
    for line in lines:
        match = player_re.search(line)
        if match:
            p_id = int(match.group(1))
            name = match.group(2).strip()
            elo = int(match.group(3))
            title = match.group(4).strip() if match.group(4) else ""
            federation = match.group(5).strip()
            p = Player(p_id, name, elo, title, federation)
            players.append(p)
        
        tokens = line.split()
        for token in tokens:
            m = parse_match_token(token)
            if m.is_valid and players:
                players[-1].matches.append(m)

    st.success("¡Archivo cargado correctamente!")
    
    tab_individual, tab_escaner = st.tabs(["🔍 Búsqueda Individual", "🚀 Escáner del Torneo"])

    # -----------------------------------------------------
    # PESTAÑA 1: MODO INDIVIDUAL
    # -----------------------------------------------------
    with tab_individual:
        player_options = {p.id: f"{p.id} - {p.name} (ELO: {p.elo})" for p in players}
        
        norm_player_id = st.selectbox("Selecciona el jugador que busca la norma:", options=list(player_options.keys()), format_func=lambda x: player_options[x])
        norm_p = get_player(norm_player_id, players)

        norm_type = st.radio("¿Qué tipo de norma deseas evaluar?", ["GM", "IM", "WGM", "WIM"], horizontal=True)

        add_opp = st.checkbox("¿Deseas añadir un rival extra manualmente para cálculos hipotéticos?")
        last_opp = None
        if add_opp:
            last_opponent_id = st.selectbox("Selecciona el rival adicional:", options=list(player_options.keys()), format_func=lambda x: player_options[x], key="last_rival")
            last_opp = get_player(last_opponent_id, players)

        if norm_p:
            res = evaluate_norm(norm_p, norm_type, players, last_opp)
            
            if res is None:
                st.error("El jugador seleccionado no posee partidas válidas computables.")
            else:
                def st_status(met):
                    return "✅ CUMPLIDO" if met else "❌ NO CUMPLIDO"

                st.markdown("---")
                st.header(f"Informe de requisitos: Norma de {norm_type}")
                st.subheader(f"Jugador: {norm_p.name} ({norm_p.federation})")
                
                st.write("### 📋 Listado de rivales")
                st.table(res["opponent_details"])
                
                if res["elo_adjusted"]:
                    st.warning(f"⚠️ **Umbral FIDE aplicado:** El rival con menor ELO ({res['original_min_elo']}) ha sido ajustado a {res['elo_threshold']} para el cálculo del ELO medio.")

                st.write("### 📊 Verificación de condiciones FIDE")
                st.write(f"**1. ELO medio de los rivales** (Mínimo: {res['elo_target']})  \n*Actual:* **{res['avg_elo']:.2f}** ➔ {st_status(res['cond_elo'])}")
                st.write(f"**2. Rivales titulados categoría {norm_type}+** (Mínimo: {res['req_cat_min']})  \n*Actual:* **{res['category_titles']}** ➔ {st_status(res['cond_cat_titles'])}")
                st.write(f"**3. Rivales titulados totales** (Mínimo: {res['req_tot_min']})  \n*Actual:* **{res['valid_titles_total']}** ➔ {st_status(res['cond_tot_titles'])}")
                st.write(f"**4. Rivales de la misma federación ({norm_p.federation})** (Máximo: {res['req_fed_player_max']})  \n*Actual:* **{res['same_fed_as_player']}** ➔ {st_status(res['cond_fed_player'])}")
                st.write(f"**5. Rivales de la federación más común** (Máximo: {res['req_fed_any_max']})  \n*Actual:* **{res['max_freq']}** ➔ {st_status(res['cond_fed_any'])}")
                st.write(f"**6. Federaciones diferentes** (Mínimo: {res['req_fed_diff_min']})  \n*Actual:* **{res['num_feds']}** ➔ {st_status(res['cond_fed_diff'])}")
                
                if res["min_required_score"] < 0.0:
                    st.error(f"**7. Puntuación mínima** (Para TPR {res['target_performance']}) ➔ **❌ IMPOSIBLE** (La media de ELO es demasiado baja)")
                else:
                    st.write(f"**7. Puntuación mínima necesaria** (Para TPR {res['target_performance']}) (Requiere: {res['min_required_score']} ptos)  \n*Performance actual:* **{res['actual_performance']}** \n*Puntuación actual:* **{res['actual_score']} ptos** ➔ {st_status(res['cond_score'])}")
                    
                    if res["norm_achieved"]:
                        st.balloons()
                        st.success(f"🎉 ¡El jugador cumple TODOS los requisitos para optar a la norma de {norm_type}!")
                    else:
                        st.info("💡 Revisa las condiciones marcadas con '❌' para ver qué falla en la norma.")

    # -----------------------------------------------------
    # PESTAÑA 2: ESCÁNER DEL TORNEO
    # -----------------------------------------------------
    with tab_escaner:
        st.write("### 🤖 Búsqueda automática de normas")
        st.write("Analiza el torneo completo y encuentra a los jugadores que han logrado normas.")
        
        modo_escaner = st.radio(
            "Selecciona el tipo de análisis:",
            ["Análisis Completo (GM, IM, WGM, WIM)", "Solo Títulos Absolutos (GM, IM)"],
            horizontal=True
        )
        
        incluir_femeninos = (modo_escaner == "Análisis Completo (GM, IM, WGM, WIM)")
        
        if st.button("Escanear torneo", type="primary"):
            with st.spinner('Analizando cuadro cruzado...'):
                candidates = scan_all_players_for_norms(players, include_womens_titles=incluir_femeninos)
                
            if len(candidates) > 0:
                st.success(f"¡Se han detectado {len(candidates)} posibles normas!")
                df = pd.DataFrame(candidates)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.info("ℹ️ Vuelve a la pestaña 'Búsqueda Individual' si quieres ver el desglose detallado de alguno de estos jugadores.")
            else:
                st.warning("No se ha detectado ninguna norma en este torneo (considerando jugadores con al menos 7 rondas válidas).")
