import streamlit as st
import requests
from datetime import datetime, timedelta
from collections import defaultdict

# -------------------- Streamlit config (DOIT ÊTRE EN PREMIER) --------------------
st.set_page_config(page_title="TGVmax Week-ends", layout="wide")

# -------------------- Fonctions utilitaires --------------------
def parse_time(t):
    return datetime.strptime(t, "%H:%M").time()

jours_fr = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
mois_fr = ["janvier", "février", "mars", "avril", "mai", "juin",
           "juillet", "août", "septembre", "octobre", "novembre", "décembre"]

def format_date_fr(date_str):
    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
    jour = jours_fr[date_obj.weekday()]
    mois = mois_fr[date_obj.month - 1]
    return f"{jour} {date_obj.day:02d} {mois}"

def week_end_ref(date_obj, is_return=False):
    weekday = date_obj.weekday()
    if not is_return:
        # Allers
        if weekday in [3, 4]:  # jeudi, vendredi
            return date_obj + timedelta(days=(5 - weekday))
        elif weekday == 5:  # samedi
            return date_obj
    else:
        # Retours
        if weekday == 6:  # dimanche
            return date_obj - timedelta(days=1)  # rattaché au samedi ?
        elif weekday == 0:  # lundi
            return date_obj - timedelta(days=2)
        elif weekday == 1:  # mardi
            return date_obj - timedelta(days=3)  # rattaché au dimanche précédent
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
    color = "#1f77b4" if train["type"] == "aller" else "#ff7f0e"
    return f"<span style='color:{color}; font-weight:bold'>{train['heure_depart']}</span>"

# -------------------- UI --------------------
st.title("🚄 TGVmax – Week-ends")

# Dates info
aujd = datetime.today()
date_plus_30 = aujd + timedelta(days=30)
st.markdown(
    f"Nous sommes le **{format_date_fr(aujd.strftime('%Y-%m-%d'))}**, "
    f"demain les trains pour le **{format_date_fr(date_plus_30.strftime('%Y-%m-%d'))}** sortiront."
)

# ----- Règles dans deux boîtes -----
st.markdown("### Règles TGVmax")

col1, col2 = st.columns(2)

with col1:
    st.markdown(
        """
<div style="background:#e6f2ff; padding:12px; border-radius:8px">
<b>Aller</b><br>
Jeudi après 17h30<br>
Vendredi avant 8h et après 17h30<br>
Samedi toute la journée
</div>
""",
        unsafe_allow_html=True
    )

with col2:
    st.markdown(
        """
<div style="background:#fff0e6; padding:12px; border-radius:8px">
<b>Retour</b><br>
Dimanche toute la journée<br>
Lundi avant 8h et après 17h30<br>
Mardi avant 8h
</div>
""",
        unsafe_allow_html=True
    )


# -------------------- Sélection du trajet --------------------
st.markdown("### Trajet")

trajet = st.radio(
    "Choisis un trajet",
    [
        "Lyon → Paris",
        "Paris → Lyon",
        "Lyon → Picardie",
        "Lyon → Lille",
        "Lyon → Rouen"
    ],
    index=0
)

trajets_codes = {
    "Lyon → Paris": ("FRLPD", "FRPLY"),
    "Paris → Lyon": ("FRPLY", "FRLPD"),
    "Lyon → Picardie": ("FRLPD", "FRTHP"),
    "Lyon → Lille": ("FRLPD", "FRLLE"),
    "Lyon → Rouen": ("FRLPD", "FRURD"),
}

origine_code, destination_code = trajets_codes[trajet]
st.markdown(f"**{trajet}**")

# -------------------- Récupération --------------------
with st.spinner("Récupération des trains..."):
    trains_aller = fetch_trains(origine_code, destination_code)
    trains_retour = fetch_trains(destination_code, origine_code)

    filtered_trains = []

    # -------- Allers --------
    for t in trains_aller:
        date_obj = datetime.strptime(t["date"], "%Y-%m-%d")
        heure = parse_time(t["heure_depart"])
        weekday = date_obj.weekday()

        if (
            (weekday == 3 and heure >= parse_time("17:30")) or
            (weekday == 4 and (heure <= parse_time("08:00") or heure >= parse_time("17:30"))) or
            (weekday == 5)
        ):
            filtered_trains.append({**t, "type": "aller"})

    # -------- Retours --------
    for t in trains_retour:
        date_obj = datetime.strptime(t["date"], "%Y-%m-%d")
        heure = parse_time(t["heure_depart"])
        weekday = date_obj.weekday()

        if (
            weekday == 6 or
            (weekday == 0 and (heure <= parse_time("08:00") or heure >= parse_time("17:30"))) or
            (weekday == 1 and heure <= parse_time("08:00"))
        ):
            filtered_trains.append({**t, "type": "retour"})

    weekends = defaultdict(lambda: {"aller": [], "retour": []})
    for t in filtered_trains:
        date_obj = datetime.strptime(t["date"], "%Y-%m-%d")
        ref = week_end_ref(date_obj, t["type"] == "retour")
        weekends[ref][t["type"]].append(t)

# -------------------- Affichage --------------------
for weekend, trips in sorted(weekends.items()):
    st.markdown(f"### Week-end du {weekend.day:02d} {mois_fr[weekend.month - 1]}")
    col1, col2 = st.columns(2)

    # Allers
    with col1:
        st.markdown("**Allers possibles**")
        if trips["aller"]:
            by_date = defaultdict(list)
            for t in trips["aller"]:
                by_date[t["date"]].append(t)

            for date_str, trains in sorted(by_date.items()):
                horaires = {t["heure_depart"]: t for t in trains}.values()
                st.markdown(
                    "<div style='background:#e6f2ff; padding:10px; margin-bottom:6px; border-radius:6px'>"
                    f"<b>{format_date_fr(date_str)} :</b> "
                    + ", ".join(format_train_line(t) for t in sorted(horaires, key=lambda x: x["heure_depart"]))
                    + "</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown("❌ Aucun aller disponible")

    # Retours
    with col2:
        st.markdown("**Retours possibles**")
        if trips["retour"]:
            by_date = defaultdict(list)
            for t in trips["retour"]:
                by_date[t["date"]].append(t)

            for date_str, trains in sorted(by_date.items()):
                horaires = {t["heure_depart"]: t for t in trains}.values()
                st.markdown(
                    "<div style='background:#fff0e6; padding:10px; margin-bottom:6px; border-radius:6px'>"
                    f"<b>{format_date_fr(date_str)} :</b> "
                    + ", ".join(format_train_line(t) for t in sorted(horaires, key=lambda x: x["heure_depart"]))
                    + "</div>",
                    unsafe_allow_html=True
                )
        else:
            st.markdown("❌ Aucun retour disponible")
