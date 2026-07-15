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
    df = pd.DataFrame(ws.get_all_records())
    if df.empty:
        return df
    df["data"] = pd.to_datetime(df["data"])
    for c in COLS[1:]:
        df[c] = pd.to_numeric(
            df[c].astype(str).str.replace(",", ".", regex=False),
            errors="coerce")
    return df.sort_values("data")


def guarda_bascula(fila):
    ws = connecta()
    ws.append_row(fila, value_input_option="USER_ENTERED")


# ---------- CAPÇALERA ----------
st.title("🏋️ Hybrid Dash — Uri")
st.caption("57 → 65 kg · Seguiment Whoop + bàscula")

tab1, tab2 = st.tabs(["📊 Whoop", "⚖️ Bàscula"])


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
            pes = st.number_input("Pes (kg)", 40.0, 120.0, 57.0, 0.05)
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
    st.subheader("Historial")

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
