import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Hybrid Dash", page_icon="🏋️", layout="wide")

st.title("🏋️ Hybrid Dash — Uri")
st.caption("57 → 65 kg · Seguiment Whoop + bàscula")

st.divider()

st.header("Puja el CSV del Whoop")
fitxer = st.file_uploader("physiological_cycles.csv", type="csv")

if fitxer is None:
    st.info("Puja el fitxer physiological_cycles.csv per començar.")
    st.stop()

df = pd.read_csv(fitxer)
df["data"] = pd.to_datetime(df["Hora de inicio del ciclo"]).dt.date
df = df.sort_values("data")

st.success(f"Carregades {len(df)} files.")

# --- Mètriques últimes 4 setmanes ---
tall = pd.Timestamp.today().date() - pd.Timedelta(days=28)
recent = df[df["data"] >= tall]

c1, c2, c3, c4 = st.columns(4)
c1.metric("TDEE mitjà (4 set.)", f"{recent['Energía quemada (cal)'].mean():.0f} kcal")
c2.metric("Recovery mitjà", f"{recent['Puntuación de recuperación (%)'].mean():.0f} %")
c3.metric("Strain mitjà", f"{recent['Esfuerzo del día'].mean():.1f}")
c4.metric("HRV mitjà", f"{recent['Variabilidad de la frecuencia cardíaca (ms)'].mean():.0f} ms")

st.divider()

# --- Gràfiques ---
st.subheader("Recovery")
st.plotly_chart(px.line(df, x="data", y="Puntuación de recuperación (%)", markers=False), use_container_width=True)

st.subheader("Energia cremada (kcal)")
st.plotly_chart(px.bar(df, x="data", y="Energía quemada (cal)"), use_container_width=True)

st.subheader("HRV (ms)")
st.plotly_chart(px.line(df, x="data", y="Variabilidad de la frecuencia cardíaca (ms)", markers=False), use_container_width=True)

st.divider()
with st.expander("Veure dades en brut"):
    st.dataframe(df)
