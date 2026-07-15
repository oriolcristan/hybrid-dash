import streamlit as st
import pandas as pd
import plotly.express as px
import gspread
from google.oauth2.service_account import Credentials
from datetime import date

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

# ---------- MOTOR DE FATIGA ----------
def calcula_fatiga(df):
    d = df.copy()
    d["strain"] = pd.to_numeric(d["Esfuerzo del día"], errors="coerce")
    d["hrv"] = pd.to_numeric(d["Variabilidad de la frecuencia cardíaca (ms)"], errors="coerce")
    d["rec"] = pd.to_numeric(d["Puntuación de recuperación (%)"], errors="coerce")
    d["son"] = pd.to_numeric(d["Duración del sueño (min)"], errors="coerce")

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

tab1, tab2, tab3 = st.tabs(["📊 Whoop", "⚖️ Bàscula", "🎯 Avui"])


# ================= TAB 1: WHOOP =================
with tab1:
    fitxer = st.file_uploader("Puja physiological_cycles.csv", type="csv")

    if fitxer is not None:
        df = pd.read_csv(fitxer)
        df["data"] = pd.to_datetime(df["Hora de inicio del ciclo"]).dt.date
        df = df.sort_values("data")

        st.success(f"Carregades {len(df)} files.")

        tall = pd.Timestamp.today().date() - pd.Timedelta(days=28)
        recent = df[df["data"] >= tall]

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("TDEE mitjà (4 set.)", f"{recent['Energía quemada (cal)'].mean():.0f} kcal")
        c2.metric("Recovery mitjà", f"{recent['Puntuación de recuperación (%)'].mean():.0f} %")
        c3.metric("Strain mitjà", f"{recent['Esfuerzo del día'].mean():.1f}")
        c4.metric("HRV mitjà", f"{recent['Variabilidad de la frecuencia cardíaca (ms)'].mean():.0f} ms")

        st.divider()
        st.subheader("Recovery")
        st.plotly_chart(px.line(df, x="data", y="Puntuación de recuperación (%)"), use_container_width=True)

        st.subheader("Energia cremada (kcal)")
        st.plotly_chart(px.bar(df, x="data", y="Energía quemada (cal)"), use_container_width=True)

        st.subheader("HRV (ms)")
        st.plotly_chart(px.line(df, x="data", y="Variabilidad de la frecuencia cardíaca (ms)"), use_container_width=True)
    else:
        st.info("Puja el fitxer del Whoop per veure les gràfiques.")


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

# ================= TAB 3: AVUI =================
with tab3:
    st.subheader("Prescripció d'avui")

    if fitxer is None:
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
