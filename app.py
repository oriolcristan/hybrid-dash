import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import date
import rutina as R
from datetime import datetime

st.set_page_config(page_title="Hybrid Dash", page_icon="🏋️", layout="wide")

SHEET_NAME = "hybrid-dash-data"
WORKSHEET = "bascula"

COLS = ["data", "pes", "bmi", "greix_pct", "greix_kg", "bmr", "muscul_pct",
        "muscul_kg", "aigua_pct", "proteina_pct", "os_kg", "visceral",
        "muscul_esq", "subcut_pct", "subcut_kg"]


# ---------- CONNEXIÓ AL SHEET ----------
@st.cache_resource
def connecta():
    scopes = ["https://www.googleapis.com/auth/spreadsheets",
              "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"], scopes=scopes)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).worksheet(WORKSHEET)


def llegeix_bascula():
    ws = connecta()
    valors = ws.get_all_values()
    if len(valors) < 2:
        return pd.DataFrame()
    df = pd.DataFrame(valors[1:], columns=valors[0])
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    for c in COLS[1:]:
        df[c] = pd.to_numeric(
            df[c].astype(str).str.replace(",", ".", regex=False),
            errors="coerce")
    return df.dropna(subset=["data"]).sort_values("data")


def guarda_bascula(fila):
    ws = connecta()
    ws.append_row(fila, value_input_option="RAW")

# ---------- WHOOP API ----------
import requests
import secrets as pysecrets
from urllib.parse import urlencode

WHOOP_AUTH = "https://api.prod.whoop.com/oauth/oauth2/auth"
WHOOP_TOKEN = "https://api.prod.whoop.com/oauth/oauth2/token"
WHOOP_BASE = "https://api.prod.whoop.com/developer/v2"
SCOPES = "offline read:recovery read:cycles read:sleep read:workout"


def ws_tokens():
    client = connecta().spreadsheet
    return client.worksheet("tokens")


def get_refresh_token():
    try:
        v = ws_tokens().acell("A2").value
        return v.strip() if v else None
    except Exception:
        return None


def set_refresh_token(token):
    ws_tokens().update_acell("A2", token)


def whoop_url_login():
    cfg = st.secrets["whoop"]
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": SCOPES,
        "state": pysecrets.token_urlsafe(8)[:8],
    }
    return f"{WHOOP_AUTH}?{urlencode(params)}"


def bescanvia_codi(code):
    cfg = st.secrets["whoop"]
    r = requests.post(WHOOP_TOKEN, data={
        "grant_type": "authorization_code",
        "code": code,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "redirect_uri": cfg["redirect_uri"],
    }, timeout=20)
    r.raise_for_status()
    d = r.json()
    set_refresh_token(d["refresh_token"])
    return d["access_token"]


def refresca_token():
    rt = get_refresh_token()
    if not rt:
        return None
    cfg = st.secrets["whoop"]
    r = requests.post(WHOOP_TOKEN, data={
        "grant_type": "refresh_token",
        "refresh_token": rt,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "scope": "offline",
    }, timeout=20)
    if r.status_code != 200:
        return None
    d = r.json()
    set_refresh_token(d["refresh_token"])   # el nou substitueix l'antic
    return d["access_token"]


def whoop_get(path, token, params=None):
    """Recorre totes les pàgines d'un endpoint."""
    out, next_token = [], None
    for _ in range(50):
        p = dict(params or {})
        p["limit"] = 25
        if next_token:
            p["nextToken"] = next_token
        r = requests.get(f"{WHOOP_BASE}{path}", params=p, timeout=20,
                         headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        d = r.json()
        out.extend(d.get("records", []))
        next_token = d.get("next_token")
        if not next_token:
            break
    return out


@st.cache_data(ttl=1800)
def baixa_whoop(_token, dies=180):
    inici = (pd.Timestamp.utcnow() - pd.Timedelta(days=dies)).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    par = {"start": inici}

    cycles = whoop_get("/cycle", _token, par)
    recov = whoop_get("/recovery", _token, par)
    sleeps = whoop_get("/activity/sleep", _token, par)

    # --- Cicles: strain i kcal ---
    c = pd.DataFrame([{
        "cycle_id": x["id"],
        "data": pd.to_datetime(x["start"]).date(),
        "strain": (x.get("score") or {}).get("strain"),
        "kcal": ((x.get("score") or {}).get("kilojoule") or 0) / 4.184,
    } for x in cycles])

    # --- Recovery: recovery %, HRV, RHR ---
    r = pd.DataFrame([{
        "cycle_id": x["cycle_id"],
        "recovery": (x.get("score") or {}).get("recovery_score"),
        "hrv": (x.get("score") or {}).get("hrv_rmssd_milli"),
        "rhr": (x.get("score") or {}).get("resting_heart_rate"),
    } for x in recov])

    # --- Son: minuts dormits ---
    s = pd.DataFrame([{
        "data": pd.to_datetime(x["start"]).date(),
        "son_min": (((x.get("score") or {}).get("stage_summary") or {})
                    .get("total_in_bed_time_milli", 0)
                    - ((x.get("score") or {}).get("stage_summary") or {})
                    .get("total_awake_time_milli", 0)) / 60000,
    } for x in sleeps if not x.get("nap")])

    if c.empty:
        return pd.DataFrame()

    df = c.merge(r, on="cycle_id", how="left")
    if not s.empty:
        df = df.merge(s.groupby("data", as_index=False).sum(), on="data", how="left")
    else:
        df["son_min"] = None

    return df.sort_values("data").reset_index(drop=True)

# ---------- MOTOR DE FATIGA ----------
def calcula_fatiga(df):
    d = df.copy()
    d["strain"] = pd.to_numeric(d["strain"], errors="coerce")
    d["hrv"] = pd.to_numeric(d["hrv"], errors="coerce")
    d["rec"] = pd.to_numeric(d["recovery"], errors="coerce")
    d["son"] = pd.to_numeric(d["son_min"], errors="coerce")

    # ACWR: mitjana exponencial 7d / 28d
    agut = d["strain"].ewm(span=7, min_periods=3).mean()
    cronic = d["strain"].ewm(span=28, min_periods=7).mean()
    d["acwr"] = agut / cronic

    # HRV z-score sobre baseline rodant de 30 dies
    mu = d["hrv"].rolling(30, min_periods=10).mean()
    sd = d["hrv"].rolling(30, min_periods=10).std()
    d["hrv_z"] = (d["hrv"] - mu) / sd

    # Normalitzacions a 0-100
    n_rec = d["rec"].clip(0, 100)
    n_hrv = ((d["hrv_z"] + 2) / 4 * 100).clip(0, 100)
    n_son = (d["son"] / 480 * 100).clip(0, 100)
    pen = (1 - (d["acwr"] - 1.3).clip(0, 0.7) / 0.7) * 100

    d["readiness"] = (0.4 * n_rec + 0.3 * n_hrv + 0.2 * n_son + 0.1 * pen)
    return d


def prescriu(readiness, acwr):
    if pd.isna(readiness):
        return "⚪", "Dades insuficients", "Cal més històric per calcular."
    if readiness > 80:
        return "🟢", "VERD — Empeny", "Sèrie extra al bàsic. Intenta PR (RPE 8-9). Cardio intens OK."
    if readiness >= 60:
        return "🔵", "BLAU — Pla normal", "Executa la sessió tal com està programada. RPE 7-8."
    if readiness >= 40:
        return "🟡", "GROC — Retalla", "−1 sèrie per exercici. RPE màxim 7. Cardio només Z2."
    return "🔴", "VERMELL — Deload", "50% del volum, només tècnica. O descans + mobilitat."

# ---------- CAPÇALERA ----------
st.title("🏋️ Hybrid Dash — Uri")
st.caption("57 → 65 kg · Seguiment Whoop + bàscula")

tab0, tab1, tab2, tab3, tab4 = st.tabs(
    ["🗓️ Avui toca", "📊 Whoop", "⚖️ Bàscula", "🎯 Readiness", "📈 Progrés"])

# ---------- COMPOSICIÓ CORPORAL ----------
KCAL_BASE = 2500
OBJECTIU_KG = 65.0

def setmanals(hist):
    h = hist.set_index("data").sort_index()
    w = h[["pes", "muscul_esq", "greix_kg", "greix_pct"]].resample("W").mean()
    return w.dropna(subset=["pes"])


def ritme(w, setmanes=3):
    """kg/setmana segons regressió sobre les últimes N setmanes."""
    x = w.tail(setmanes)
    if len(x) < 2:
        return None
    dies = (x.index[-1] - x.index[0]).days
    if dies == 0:
        return None
    return (x["pes"].iloc[-1] - x["pes"].iloc[0]) / dies * 7


def ajust_kcal(r):
    if r is None:
        return "⚪", "Encara no hi ha prou dades", 0, "Calen 3 setmanes de mesures."
    if r < 0.15:
        return "🔵", f"{r:+.2f} kg/set — Massa lent", +200, \
               "Puja 200 kcal de carbohidrats: +50 g d'arròs/pasta al dinar."
    if r <= 0.40:
        return "🟢", f"{r:+.2f} kg/set — Correcte", 0, \
               "No toquis res. Aquest és el ritme objectiu."
    if r <= 0.60:
        return "🟡", f"{r:+.2f} kg/set — Vigila", 0, \
               "Al límit. Revisa la cintura: si creix, retalla. Si no, aguanta."
    return "🔴", f"{r:+.2f} kg/set — Massa ràpid", -150, \
           "Retalla 150 kcal. Probablement estàs acumulant greix."


def qualitat(w):
    """% del guany de pes que és múscul esquelètic."""
    if len(w) < 2:
        return None
    d_pes = w["pes"].iloc[-1] - w["pes"].iloc[0]
    d_mus = w["muscul_esq"].iloc[-1] - w["muscul_esq"].iloc[0]
    if abs(d_pes) < 0.1:
        return None
    return d_mus / d_pes * 100

# ================= TAB 1: WHOOP =================
with tab1:
    df = None

    # Si tornem del login de Whoop, hi ha un ?code= a la URL
    code = st.query_params.get("code")
    if code and not get_refresh_token():
        try:
            bescanvia_codi(code)
            st.query_params.clear()
            st.success("Connectat a Whoop!")
        except Exception as e:
            st.error(f"Error autoritzant: {e}")

    token = refresca_token()

    if token is None:
        st.warning("Encara no estàs connectat a Whoop.")
        st.link_button("🔗 Connectar amb Whoop", whoop_url_login(),
                       use_container_width=True)
        st.caption("Un cop autoritzis, tornaràs aquí automàticament.")
        st.divider()
        st.caption("Alternativa: puja el CSV manualment.")
        fitxer = st.file_uploader("physiological_cycles.csv", type="csv")
        if fitxer is not None:
            df = pd.read_csv(fitxer)
            df = df.rename(columns={
                "Esfuerzo del día": "strain",
                "Energía quemada (cal)": "kcal",
                "Puntuación de recuperación (%)": "recovery",
                "Variabilidad de la frecuencia cardíaca (ms)": "hrv",
                "Duración del sueño (min)": "son_min",
            })
            df["data"] = pd.to_datetime(df["Hora de inicio del ciclo"]).dt.date
            df = df.sort_values("data")
    else:
        c1, c2 = st.columns([3, 1])
        c1.success("✅ Connectat a Whoop")
        if c2.button("🔄 Actualitzar dades", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        with st.spinner("Baixant dades..."):
            df = baixa_whoop(token)

    if df is None or df.empty:
        st.info("Sense dades encara.")
    else:
        st.caption(f"{len(df)} dies · de {df['data'].min()} a {df['data'].max()}")

        tall = pd.Timestamp.today().date() - pd.Timedelta(days=28)
        rec = df[df["data"] >= tall]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("TDEE mitjà (4 set.)", f"{rec['kcal'].mean():.0f} kcal")
        c2.metric("Recovery mitjà", f"{rec['recovery'].mean():.0f} %")
        c3.metric("Strain mitjà", f"{rec['strain'].mean():.1f}")
        c4.metric("HRV mitjà", f"{rec['hrv'].mean():.0f} ms")

        st.divider()
        st.plotly_chart(px.line(df, x="data", y="recovery", title="Recovery (%)"),
                        use_container_width=True)
        st.plotly_chart(px.bar(df, x="data", y="kcal", title="Energia cremada (kcal)"),
                        use_container_width=True)
        st.plotly_chart(px.line(df, x="data", y="hrv", title="HRV (ms)"),
                        use_container_width=True)

# ================= TAB 2: BÀSCULA =================
with tab2:
    st.subheader("Nova mesura")

    with st.form("form_bascula", clear_on_submit=True):
        d = st.date_input("Data", value=date.today())

        c1, c2, c3 = st.columns(3)
        with c1:
            pes = st.number_input("Pes (kg)", 40.0, 120.0, 57.15, 0.01, format="%.2f")
            bmi = st.number_input("BMI", 10.0, 40.0, 18.8, 0.1)
            greix_pct = st.number_input("Taxa de greix (%)", 3.0, 50.0, 12.0, 0.1)
            greix_kg = st.number_input("Massa greix (kg)", 1.0, 50.0, 6.8, 0.1)
            bmr = st.number_input("BMR (kcal)", 800, 3000, 1370, 5)
        with c2:
            muscul_pct = st.number_input("Taxa muscular (%)", 30.0, 95.0, 83.4, 0.1)
            muscul_kg = st.number_input("Massa muscular (kg)", 20.0, 90.0, 47.7, 0.1)
            aigua_pct = st.number_input("Taxa humitat (%)", 30.0, 80.0, 60.3, 0.1)
            proteina_pct = st.number_input("Taxa proteïna (%)", 5.0, 30.0, 18.3, 0.1)
            os_kg = st.number_input("Massa òssia (kg)", 1.0, 6.0, 2.6, 0.05)
        with c3:
            visceral = st.number_input("Greix visceral", 1, 30, 2, 1)
            muscul_esq = st.number_input("Múscul esquelètic (kg)", 10.0, 60.0, 25.8, 0.1)
            subcut_pct = st.number_input("Greix subcutani (%)", 2.0, 45.0, 11.2, 0.1)
            subcut_kg = st.number_input("Massa greix subcutani (kg)", 1.0, 45.0, 6.4, 0.1)

        enviat = st.form_submit_button("💾 Guardar", use_container_width=True)

    if enviat:
        fila = [str(d), pes, bmi, greix_pct, greix_kg, bmr, muscul_pct,
                muscul_kg, aigua_pct, proteina_pct, os_kg, visceral,
                muscul_esq, subcut_pct, subcut_kg]
        try:
            guarda_bascula(fila)
            st.success(f"Mesura del {d} guardada!")
        except Exception as e:
            st.error(f"Error en guardar: {e}")

    st.divider()
    c_tit, c_btn = st.columns([4, 1])
    c_tit.subheader("Historial")
    if c_btn.button("🔄 Refrescar", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()

    try:
        hist = llegeix_bascula()
    except Exception as e:
        st.error(f"No puc llegir el Sheet: {e}")
        hist = pd.DataFrame()

    if hist.empty:
        st.info("Encara no hi ha mesures. Guarda'n una a dalt.")
    else:
        ultima = hist.iloc[-1]
        objectiu = 65.0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Pes actual", f"{ultima['pes']:.2f} kg")
        c2.metric("Falten", f"{objectiu - ultima['pes']:.2f} kg")
        c3.metric("Greix", f"{ultima['greix_pct']:.1f} %")
        c4.metric("Múscul esquelètic", f"{ultima['muscul_esq']:.1f} kg")

        if len(hist) > 1:
            prev = hist.iloc[-2]
            dies = (ultima["data"] - prev["data"]).days
            c1, c2, c3 = st.columns(3)
            c1.metric("Δ Pes", f"{ultima['pes'] - prev['pes']:+.2f} kg", f"{dies} dies")
            c2.metric("Δ Múscul esq.", f"{ultima['muscul_esq'] - prev['muscul_esq']:+.2f} kg")
            c3.metric("Δ Greix", f"{ultima['greix_kg'] - prev['greix_kg']:+.2f} kg")

        st.plotly_chart(
            px.line(hist, x="data", y="pes", markers=True, title="Pes (kg)")
              .add_hline(y=objectiu, line_dash="dash", line_color="green",
                         annotation_text="Objectiu 65 kg"),
            use_container_width=True)

        st.plotly_chart(
            px.line(hist, x="data", y=["muscul_esq", "greix_kg"], markers=True,
                    title="Múscul esquelètic vs Massa greix (kg)"),
            use_container_width=True)
            
        with st.expander("Veure totes les dades"):
            st.dataframe(hist, use_container_width=True)

# ================= TAB 0: AVUI TOCA =================
with tab0:
    avui_idx = datetime.today().weekday()

    c1, c2 = st.columns([2, 1])
    dia_sel = c1.selectbox(
        "Dia", options=list(R.DIES.keys()),
        format_func=lambda i: R.DIES[i]["nom"] + (" (avui)" if i == avui_idx else ""),
        index=avui_idx)
    lloc = c2.radio("Ubicació", ["🏠 Casa", "🏢 Apartament"], horizontal=True)
    key_lloc = "casa" if "Casa" in lloc else "apart"

    d = R.DIES[dia_sel]
    st.markdown(f"## {d['titol']}")
    st.caption(d["sub"])

    # ---------- DIES DE FORÇA ----------
    if d["tipus"] == "forca":
        st.info(d["extra"])

        with st.expander("🔥 ESCALFAMENT (10 min) — obligatori", expanded=False):
            st.markdown("### 1. Foam roller")
            st.error("⚠️ MAI passis el roller per la banda IT directament. "
                     "És teixit connectiu: no es 'desenganxa' i només l'inflames.")
            for e in R.FOAM:
                with st.expander(f"**{e['zona']}** — {e['dosi']}"):
                    st.markdown(f"**On:** {e['on']}")
                    st.markdown(f"**Com:** {e['com']}")
                    st.markdown(f"**Per què:** {e['per']}")
                    st.link_button("📹 YouTube",
                        f"https://www.youtube.com/results?search_query={e['yt'].replace(' ', '+')}")

            st.markdown("### 2. Mobilitat dinàmica")
            for e in R.DINAMIC:
                with st.expander(f"**{e['exercici']}** — {e['dosi']}"):
                    st.markdown(f"**Què és:** {e['què']}")
                    st.markdown(f"**Com:** {e['com']}")
                    st.markdown(f"**Per què:** {e['per']}")
                    st.link_button("📹 YouTube",
                        f"https://www.youtube.com/results?search_query={e['yt'].replace(' ', '+')}")

            st.markdown("### 3. Activació minibands (prevenció BIT)")
            for e in R.MINIBANDS:
                with st.expander(f"**{e['exercici']}** — {e['dosi']}"):
                    st.markdown(f"**Què és:** {e['què']}")
                    st.markdown(f"**Com:** {e['com']}")
                    st.markdown(f"**Per què:** {e['per']}")
                    st.link_button("📹 YouTube",
                        f"https://www.youtube.com/results?search_query={e['yt'].replace(' ', '+')}")

        st.subheader("Sessió")
        for i, e in enumerate(d["exercicis"], 1):
            with st.expander(f"**{i}. {e[key_lloc]}** — {e['sr']}", expanded=False):
                c1, c2, c3 = st.columns(3)
                c1.metric("Patró", e["patró"])
                c2.metric("Sèries x Reps", e["sr"])
                c3.metric("Tempo", e["tempo"])

                st.markdown(f"**Què és:** {e['què']}")
                st.markdown(f"**Per a què serveix:** {e['per']}")
                st.markdown(f"**Com es fa:** {e['com']}")

                q = e["yt"].replace(" ", "+")
                st.link_button("📹 Veure vídeos de tècnica a YouTube",
                               f"https://www.youtube.com/results?search_query={q}",
                               use_container_width=True)

        with st.expander("📋 Veure sessió en format taula (resum ràpid)"):
            st.dataframe(pd.DataFrame([{
                "Patró": e["patró"],
                "Exercici": e[key_lloc],
                "Sèries x Reps": e["sr"],
                "Tempo": e["tempo"],
            } for e in d["exercicis"]]), hide_index=True, use_container_width=True)

        with st.expander("⏱️ Descansos i regles"):
            st.dataframe(pd.DataFrame(R.DESCANSOS), hide_index=True, use_container_width=True)
            st.markdown("""
**Doble progressió:** només puges càrrega quan fas el límit **superior** de reps
a **totes** les sèries. Ni abans.

**RPE:** setmana 1 → RPE 6-7 · setmana 2 → RPE 7-8 · setmana 3+ → RPE 8.

**No alteris l'ordre.** Els bàsics primer (sistema nerviós fresc), el core al final.

**Dominades:** progressió només per reps fins a 4x10 net. Després, llast.
           """)

        with st.expander("🧊 TORNADA A LA CALMA (5 min) — al acabar", expanded=False):
            st.info("El teixit està calent: és la millor finestra del dia per guanyar ROM. "
                    "Ara sí que toca estàtic — abans d'entrenar t'hauria baixat la força.")
            for e in R.TORNADA_CALMA:
                with st.expander(f"**{e['posició']}** — {e['temps']}"):
                    st.markdown(f"**Com:** {e['com']}")
                    st.markdown(f"**Clau:** {e['clau']}")
                    st.link_button("📹 YouTube",
                        f"https://www.youtube.com/results?search_query={e['yt'].replace(' ', '+')}")

        st.divider()
        st.subheader("🦵 Semàfor del genoll")
        st.dataframe(pd.DataFrame([
            {"Senyal": "Molèstia lateral DURANT l'exercici", "Acció": "Para aquell exercici. Revisa tècnica."},
            {"Senyal": "Molèstia L'ENDEMÀ", "Acció": "−30% volum de tren inferior la propera sessió"},
            {"Senyal": "Dolor punxant al genoll extern", "Acció": "PARA i consulta"},
            {"Senyal": "Res", "Acció": "Endavant"},
        ]), hide_index=True, use_container_width=True)

        st.divider()
        st.text_area("📝 Registre de la sessió (copia-ho a les notes del mòbil)",
                     value=f"{d['nom']} {datetime.today().strftime('%d/%m')} — {d['titol']}\n"
                           + "\n".join(f"{e['patró']}: " for e in d["exercicis"])
                           + "\nGenoll: ",
                     height=200)

    # ---------- MOBILITAT PASSIVA ----------
    elif d["tipus"] == "passiva":
        st.info(d["extra"])

        st.subheader("Bloc 1 — Alliberament (4 min)")
        st.dataframe(pd.DataFrame([
            {"zona": "TFL (pressió sostinguda + flexió/extensió genoll)", "dosi": "90 s/costat"},
            {"zona": "Gluti mitjà (roller o pilota)", "dosi": "60 s/costat"},
            {"zona": "Vast lateral", "dosi": "60 s/costat"},
        ]), hide_index=True, use_container_width=True)
        st.error("⚠️ Banda IT: MAI directament.")

        st.subheader("Bloc 2 — Estirament profund (12 min)")
        for e in R.PASSIVA:
            with st.expander(f"**{e['posició']}** — {e['temps']}"):
                st.markdown(f"**Com:** {e['com']}")
                st.markdown(f"**Clau:** {e['clau']}")
                st.link_button("📹 YouTube",
                    f"https://www.youtube.com/results?search_query={e['yt'].replace(' ', '+')}")
        st.success("Si una setmana només pots fer una cosa: **couch stretch, 2 min per costat, cada dia.** "
                   "És el 80% del resultat per al teu perfil (bici + cadira + BIT).")

    # ---------- MICRO-DOSI ----------
    else:
        st.info(d["extra"])
        st.subheader("Micro-dosi diària")
        for e in R.MICRO:
            with st.expander(f"**{e['quan']}**"):
                st.markdown(f"**Què:** {e['què']}")
                st.markdown(f"**Per què:** {e['per']}")
        st.caption("Freqüència > durada. Això és el multiplicador.")


# ================= TAB 3: AVUI =================
with tab3:
    st.subheader("Prescripció d'avui")

    if df is None or df.empty:
        st.warning("Puja el CSV del Whoop a la pestanya 📊 per calcular la prescripció.")
        st.stop()

    f = calcula_fatiga(df)
    avui = f.iloc[-1]
    icona, titol, accio = prescriu(avui["readiness"], avui["acwr"])

    st.markdown(f"## {icona} {titol}")
    st.info(accio)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Readiness", f"{avui['readiness']:.0f}" if pd.notna(avui["readiness"]) else "—")
    c2.metric("Recovery", f"{avui['rec']:.0f} %")
    c3.metric("ACWR", f"{avui['acwr']:.2f}" if pd.notna(avui["acwr"]) else "—")
    c4.metric("HRV z-score", f"{avui['hrv_z']:+.2f}" if pd.notna(avui["hrv_z"]) else "—")

    # Alerta BIT
    if pd.notna(avui["acwr"]) and avui["acwr"] > 1.4:
        st.error("⚠️ **ACWR > 1.4** — Càrrega acumulada alta. Retalla volum de tren inferior "
                 "aquesta setmana (protecció BIT: la fatiga degrada la mecànica del gluti mitjà).")

    st.divider()

    st.subheader("Readiness (60 dies)")
    ult = f.tail(60)
    fig = px.line(ult, x="data", y="readiness", markers=True)
    fig.add_hrect(y0=80, y1=100, fillcolor="green", opacity=0.08, line_width=0)
    fig.add_hrect(y0=60, y1=80, fillcolor="blue", opacity=0.08, line_width=0)
    fig.add_hrect(y0=40, y1=60, fillcolor="orange", opacity=0.08, line_width=0)
    fig.add_hrect(y0=0, y1=40, fillcolor="red", opacity=0.08, line_width=0)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("ACWR — càrrega aguda / crònica")
    fig2 = px.line(ult, x="data", y="acwr", markers=True)
    fig2.add_hrect(y0=0.8, y1=1.3, fillcolor="green", opacity=0.1, line_width=0,
                   annotation_text="Sweet spot")
    fig2.add_hline(y=1.5, line_dash="dash", line_color="red",
                   annotation_text="Risc de lesió")
    st.plotly_chart(fig2, use_container_width=True)

# ================= TAB 4: PROGRÉS =================
with tab4:
    st.subheader("Validació del guany")

    try:
        h = llegeix_bascula()
    except Exception:
        h = pd.DataFrame()

    if h.empty or len(h) < 2:
        st.info("Calen almenys 2 mesures. Segueix pesant-te cada dia — "
                "el sistema farà servir les mitjanes setmanals.")
        st.stop()

    w = setmanals(h)
    r = ritme(w)
    icona, titol, delta, accio = ajust_kcal(r)

    st.markdown(f"## {icona} {titol}")
    st.info(accio)

    c1, c2, c3 = st.columns(3)
    c1.metric("Kcal objectiu", f"{KCAL_BASE + delta}",
              f"{delta:+d}" if delta else "sense canvis")
    c2.metric("Pes (mitjana setmana)", f"{w['pes'].iloc[-1]:.2f} kg")
    c3.metric("Falten", f"{OBJECTIU_KG - w['pes'].iloc[-1]:.2f} kg")

    q = qualitat(w)
    if q is not None:
        st.divider()
        st.subheader("Qualitat del guany")
        c1, c2 = st.columns([1, 3])
        c1.metric("Múscul del total guanyat", f"{q:.0f} %")
        if q > 60:
            c2.success("✅ Guany net. El superàvit està ben calibrat.")
        elif q > 30:
            c2.warning("🟡 Normal en volum. Vigila la cintura cada 2 setmanes.")
        else:
            c2.error("🔴 Massa greix proporcionalment. Retalla 150-200 kcal.")
        st.caption("⚠️ La bioimpedància és imprecisa en persones magres. "
                   "Fes cas a la tendència de 4+ setmanes, no a la xifra d'avui.")

    st.divider()
    st.subheader("Pes — mitjanes setmanals")
    fig = px.line(w.reset_index(), x="data", y="pes", markers=True)
    fig.add_hline(y=OBJECTIU_KG, line_dash="dash", line_color="green",
                  annotation_text="Objectiu 65 kg")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Múscul esquelètic vs Greix")
    fig2 = px.line(w.reset_index(), x="data", y=["muscul_esq", "greix_kg"], markers=True)
    st.plotly_chart(fig2, use_container_width=True)

    with st.expander("Veure mitjanes setmanals"):
        st.dataframe(w, use_container_width=True)

