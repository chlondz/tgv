import streamlit as st
import requests
from datetime import datetime, timedelta
from collections import defaultdict

st.set_page_config(page_title="TGVmax Week-ends", layout="wide")

# -------------------- CSS girly + distinct week-ends --------------------
st.markdown("""
<style>
.block-container { max-width: 680px; padding-top: 1rem; padding-bottom: 2rem; }

/* Carte week-end avec ombre + bord pastel */
.weekend-card {
    border-left: 6px solid #FFB6C1;  /* couleur pastel rose pour le week-end */
    border-radius: 12px;
    padding: 16px;
    margin-bottom: 24px;
    background: #FFFFFF;
    box-shadow: 0 4px 8px rgba(0,0,0,0.05);
}

/* Titre du week-end */
.weekend-title {
    font-size: 1rem;
    font-weight: bold;
    margin-bottom: 12px;
    color: #9B1452;  /* rose girly */
}

/* Colonnes */
.weekend-columns {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
}

/* Sections aller / retour */
.section {
    flex: 1;
    min-width: 120px;
}

/* Section titre */
.section-title { font-size: 0.8rem; color: #6B7280; margin-bottom: 6px; }

/* Horaires collés */
.time-line {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 6px;
    font-size: 0.85rem;
}

/* Chips horaires pastel */
.time-chip {
    padding: 4px 8px;
    border-radius: 999px;
    font-weight: 500;
}

/* Couleurs girly */
.aller { background: #FFD6E8; color: #9B1452; }
.retour { background: #E8D6FF; color: #5C2A9D; }

/* Date */
.date-line { font-size: 0.85rem; color: #374151; margin-bottom: 4px; }
</style>
""", unsafe_allow_html=True)

# -------------------- Fonctions --------------------
def parse_time(t):
    return datetime.strptime(t, "%H:%M").time()

jours_fr = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]
mois_fr = ["janvier","février","mars","avril","mai","juin",
           "juillet","août","septembre","octobre","novembre","décembre"]

def format_date_fr(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    jour = jours_fr[date_obj.weekday()]
    mois = mois_fr[date_obj.month-1]
    return f"{jour} {date_obj.day:02d} {mois}"

def week_end_ref(date_obj, is_return=False):
    weekday = date_obj.weekday()
    if not is_return:
        if weekday in [3,4]: return date_obj + timedelta(days=(5-weekday))
        elif weekday == 5: return date_obj
    else:
        if weekday == 6: return date_obj - timedelta(days=1)
        elif weekday == 0: return date_obj - timedelta(days=2)
        elif weekday == 1: return date_obj - timedelta(days=3)
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
        if len(trains) < 100: break
        index += 100
    return all_results

# -------------------- UI --------------------
st.title("🚄 TGVmax – Week-ends")

aujd = datetime.today()
date_plus_30 = aujd + timedelta(days=30)
st.markdown(
    f"Nous sommes le **{format_date_fr(aujd.strftime('%Y-%m-%d'))}**, "
    f"les trains pour le **{format_date_fr(date_plus_30.strftime('%Y-%m-%d'))}** seront disponibles."
)

with st.expander("Règles TGVmax - Aller"):
    st.markdown("- Jeudi après 17h30\n- Vendredi avant 8h et après 17h30\n- Samedi toute la journée")
with st.expander("Règles TGVmax - Retour"):
    st.markdown("- Dimanche toute la journée\n- Lundi avant 8h et après 17h30\n- Mardi avant 8h")

trajet = st.selectbox(
    "Choisis un trajet",
    ["Lyon → Paris","Paris → Lyon","Lyon → Picardie","Lyon → Lille","Lyon → Rouen"]
)
trajets_codes = {
    "Lyon → Paris": ("FRLPD","FRPLY"),
    "Paris → Lyon": ("FRPLY","FRLPD"),
    "Lyon → Picardie": ("FRLPD","FRTHP"),
    "Lyon → Lille": ("FRLPD","FRLLE"),
    "Lyon → Rouen": ("FRLPD","FRURD"),
}
origine_code, destination_code = trajets_codes[trajet]
st.markdown(f"**{trajet}**")

with st.spinner("Récupération des trains..."):
    trains_aller = fetch_trains(origine_code, destination_code)
    trains_retour = fetch_trains(destination_code, origine_code)

    filtered_trains = []

    for t in trains_aller:
        date_obj = datetime.strptime(t["date"], "%Y-%m-%d")
        heure = parse_time(t["heure_depart"])
        weekday = date_obj.weekday()
        if (weekday==3 and heure>=parse_time("17:30")) or (weekday==4 and (heure<=parse_time("08:00") or heure>=parse_time("17:30"))) or (weekday==5):
            filtered_trains.append({**t, "type":"aller"})
    for t in trains_retour:
        date_obj = datetime.strptime(t["date"], "%Y-%m-%d")
        heure = parse_time(t["heure_depart"])
        weekday = date_obj.weekday()
        if weekday==6 or (weekday==0 and (heure<=parse_time("08:00") or heure>=parse_time("17:30"))) or (weekday==1 and heure<=parse_time("08:00")):
            filtered_trains.append({**t, "type":"retour"})

    weekends = defaultdict(lambda: {"aller": [], "retour": []})
    for t in filtered_trains:
        date_obj = datetime.strptime(t["date"], "%Y-%m-%d")
        ref = week_end_ref(date_obj, t["type"]=="retour")
        weekends[ref][t["type"]].append(t)

# -------------------- Affichage week-end distinct --------------------
# -------------------- Affichage week-end 100% dans la carte --------------------
for weekend, trips in sorted(weekends.items()):
    # Carte complète pour le week-end
    card_html = f"<div class='weekend-card'>"
    card_html += f"<div class='weekend-title'>Week-end du {format_date_fr(weekend.strftime('%Y-%m-%d'))}</div>"
    card_html += "<div class='weekend-columns'>"

    # --- ALLER ---
    card_html += "<div class='section'><div class='section-title'>ALLER</div>"
    if trips["aller"]:
        by_date = defaultdict(list)
        for t in trips["aller"]:
            by_date[t["date"]].append(t)
        for date_str, trains in sorted(by_date.items()):
            card_html += f"<div class='date-line'>{format_date_fr(date_str)}</div>"
            card_html += "<div class='time-line'>" + "".join([
                f"<span class='time-chip aller'>{t['heure_depart']}</span>"
                for t in sorted(trains, key=lambda x:x['heure_depart'])
            ]) + "</div>"
    else:
        card_html += "<span class='date-line'>Aucun aller</span>"
    card_html += "</div>"

    # --- RETOUR ---
    card_html += "<div class='section'><div class='section-title'>RETOUR</div>"
    if trips["retour"]:
        by_date = defaultdict(list)
        for t in trips["retour"]:
            by_date[t["date"]].append(t)
        for date_str, trains in sorted(by_date.items()):
            card_html += f"<div class='date-line'>{format_date_fr(date_str)}</div>"
            card_html += "<div class='time-line'>" + "".join([
                f"<span class='time-chip retour'>{t['heure_depart']}</span>"
                for t in sorted(trains, key=lambda x:x['heure_depart'])
            ]) + "</div>"
    else:
        card_html += "<span class='date-line'>Aucun retour</span>"
    card_html += "</div>"

    card_html += "</div></div>"  # fermeture columns + carte
    st.markdown(card_html, unsafe_allow_html=True)
