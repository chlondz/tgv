import streamlit as st
import requests
from datetime import datetime, timedelta
from collections import defaultdict

# -------------------- Fonctions utilitaires --------------------
def parse_time(t):
    return datetime.strptime(t, "%H:%M").time()

# Jours et mois en français
jours_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
mois_fr = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

def format_date_fr(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    jour = jours_fr[date_obj.weekday()]
    jour_mois = f"{date_obj.day:02d}"
    mois = mois_fr[date_obj.month - 1]
    return f"{jour} {jour_mois} {mois}"

def week_end_ref(date_obj, is_return=False):
    weekday = date_obj.weekday()
    if not is_return:
        if weekday in [3, 4]:
            return date_obj + timedelta(days=(5 - weekday))
        elif weekday == 5:
            return date_obj
    else:
        if weekday == 6:
            return date_obj - timedelta(days=1)
        elif weekday == 0:
            return date_obj - timedelta(days=2)
    return date_obj

def fetch_trains(origine, destination):
    all_results = []
    index = 0
    while True:
        url = "https://ressources.data.sncf.com/api/explore/v2.1/catalog/datasets/tgvmax/records"
        params = {
            "refine": [
                "od_happy_card:OUI",
                f"origine_iata:{origine}",
                f"destination_iata:{destination}"
            ],
            "limit": 100,
            "offset": index
        }
        response = requests.get(url, params=params)
        data = response.json()
        trains = data.get("results", [])
        all_results.extend(trains)
        if len(trains) < 100:
            break
        index += 100
    return all_results

def format_train_line(train):
    heure = train['heure_depart']
    t_type = train['type']
    color = "#1f77b4" if t_type == "aller" else "#ff7f0e"
    return f"<span style='color:{color}; font-weight:bold'>{heure}</span>"

# -------------------- Streamlit UI --------------------
st.set_page_config(page_title="TGVmax Lyon ↔ Paris", layout="wide")
st.title("🚄 TGVmax - Week-ends Lyon ↔ Paris")

# --- Nouvelle section : date du jour et date +31 ---
aujd = datetime.today()
date_plus_30 = aujd + timedelta(days=30)
st.markdown(f"Nous sommes le **{format_date_fr(aujd.strftime('%Y-%m-%d'))}**, demain les trains pour le **{format_date_fr(date_plus_30.strftime('%Y-%m-%d'))}** sortiront.")

if "origine" not in st.session_state:
    st.session_state.origine = "LYON"
if "destination" not in st.session_state:
    st.session_state.destination = "PARIS"

# Bouton inverser
if st.button("↔ Inverser"):
    st.session_state.origine, st.session_state.destination = st.session_state.destination, st.session_state.origine

st.markdown(f"**{st.session_state.origine} → {st.session_state.destination}**")

# -------------------- Récupération --------------------
with st.spinner("Récupération des trains..."):
    if st.session_state.origine == "LYON":
        trains_aller = fetch_trains("FRLPD", "FRPLY")
        trains_retour = fetch_trains("FRPLY", "FRLPD")
    else:
        trains_aller = fetch_trains("FRPLY", "FRLPD")
        trains_retour = fetch_trains("FRLPD", "FRPLY")

    filtered_trains = []
    for t in trains_aller:
        date_obj = datetime.strptime(t["date"], "%Y-%m-%d")
        weekday = date_obj.weekday()
        heure = parse_time(t["heure_depart"])
        if (weekday in [3, 4] and heure >= parse_time("17:00")) or (weekday == 5):
            filtered_trains.append({**t, "type": "aller"})
    for t in trains_retour:
        date_obj = datetime.strptime(t["date"], "%Y-%m-%d")
        weekday = date_obj.weekday()
        heure = parse_time(t["heure_depart"])
        if (weekday == 6) or (weekday == 0 and heure >= parse_time("17:00")):
            filtered_trains.append({**t, "type": "retour"})

    weekends = defaultdict(lambda: {"aller": [], "retour": []})
    for t in filtered_trains:
        date_obj = datetime.strptime(t["date"], "%Y-%m-%d")
        is_return = t["type"] == "retour"
        ref = week_end_ref(date_obj, is_return)
        if is_return:
            weekends[ref]["retour"].append(t)
        else:
            weekends[ref]["aller"].append(t)

# -------------------- Affichage amélioré --------------------
for weekend, trips in sorted(weekends.items()):
    joli_print = f"{weekend.day:02d} {mois_fr[weekend.month - 1]}"
    st.markdown(f"### Week-end du {joli_print}")
    col1, col2 = st.columns(2)

    # Allers
    with col1:
        st.markdown("**Allers possibles**")
        if trips["aller"]:
            aller_by_date = defaultdict(list)
            for a in trips["aller"]:
                aller_by_date[a["date"]].append(a)
            for date_str, trains in sorted(aller_by_date.items()):
                horaires_uniques = {t['heure_depart']: t for t in trains}.values()
                st.markdown(
                    f"<div style='background-color:#e6f2ff; padding:10px; margin-bottom:5px; border-radius:5px'>"
                    f"<b>{format_date_fr(date_str)} :</b> " +
                    ", ".join([format_train_line(t) for t in sorted(horaires_uniques, key=lambda x: x["heure_depart"])]) +
                    "</div>", unsafe_allow_html=True
                )
        else:
            st.markdown("<span style='color:#d62728'>Aucun aller disponible</span>", unsafe_allow_html=True)

    # Retours
    with col2:
        st.markdown("**Retours possibles**")
        if trips["retour"]:
            retour_by_date = defaultdict(list)
            for r in trips["retour"]:
                retour_by_date[r["date"]].append(r)
            for date_str, trains in sorted(retour_by_date.items()):
                horaires_uniques = {t['heure_depart']: t for t in trains}.values()
                st.markdown(
                    f"<div style='background-color:#fff0e6; padding:10px; margin-bottom:5px; border-radius:5px'>"
                    f"<b>{format_date_fr(date_str)} :</b> " +
                    ", ".join([format_train_line(t) for t in sorted(horaires_uniques, key=lambda x: x["heure_depart"])]) +
                    "</div>", unsafe_allow_html=True
                )
        else:
            st.markdown("<span style='color:#d62728'>Aucun retour disponible</span>", unsafe_allow_html=True)
