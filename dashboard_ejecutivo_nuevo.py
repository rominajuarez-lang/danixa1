
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go


# =========================================================
# DASHBOARD EJECUTIVO - VISTA GENERAL
# Archivo independiente para integrar con app.py
# =========================================================


def _fmt_money(x):
    try:
        x = float(x)
    except Exception:
        x = 0.0
    return f"S/ {x:,.0f}"


def _fmt_num(x):
    try:
        x = float(x)
    except Exception:
        x = 0.0
    return f"{x:,.0f}"


def _fmt_pct(x):
    try:
        x = float(x)
    except Exception:
        x = 0.0
    return f"{x:.2%}"


def _safe_df(df):
    if df is None:
        return pd.DataFrame()
    return df.copy()


def _normalizar_fecha(df, col="date"):
    df = df.copy()
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")
        df = df.dropna(subset=[col])
        df[col] = df[col].dt.to_period("M").dt.to_timestamp()
    return df


def _inject_css():
    st.markdown(
        """
        <style>
        .main .block-container {
            padding-top: 1.5rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }

        .dashboard-title {
            font-size: 2.2rem;
            font-weight: 800;
            color: #172033;
            margin-bottom: 0rem;
            line-height: 1.15;
        }

        .dashboard-subtitle {
            color: #6b7280;
            font-size: 0.98rem;
            margin-top: 0.2rem;
            margin-bottom: 1.0rem;
        }

        .card {
            background: #ffffff;
            border: 1px solid #e8edf5;
            border-radius: 16px;
            padding: 18px 18px;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
            min-height: 105px;
        }

        .metric-icon {
            width: 42px;
            height: 42px;
            border-radius: 14px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.35rem;
            margin-bottom: 8px;
        }

        .metric-label {
            font-size: 0.78rem;
            color: #4b5563;
            font-weight: 600;
            margin-bottom: 4px;
        }

        .metric-value {
            font-size: 1.45rem;
            color: #111827;
            font-weight: 800;
            line-height: 1.15;
        }

        .metric-note-green {
            color: #138a3d;
            font-size: 0.78rem;
            font-weight: 600;
            margin-top: 6px;
        }

        .metric-note-red {
            color: #dc2626;
            font-size: 0.78rem;
            font-weight: 600;
            margin-top: 6px;
        }

        .section-card {
            background: #ffffff;
            border: 1px solid #e8edf5;
            border-radius: 16px;
            padding: 16px 16px 8px 16px;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
            margin-bottom: 1rem;
        }

        .section-title {
            font-size: 1.0rem;
            font-weight: 800;
            color: #172033;
            margin-bottom: 0.6rem;
        }

        .insight-box {
            border-radius: 14px;
            padding: 14px 16px;
            background: #f8fafc;
            border: 1px solid #e5e7eb;
            margin-bottom: 10px;
            font-size: 0.86rem;
        }

        .blue-band {
            background: #eaf3ff;
            border-radius: 12px;
            padding: 12px 16px;
            color: #075aa6;
            font-weight: 700;
            margin: 8px 0 12px 0;
        }

        div[data-testid="stMetric"] {
            background: #ffffff;
            border: 1px solid #e8edf5;
            border-radius: 16px;
            padding: 16px;
            box-shadow: 0 6px 18px rgba(15, 23, 42, 0.05);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _metric_card(icon, label, value, note="", note_type="green", bg="#eef4ff"):
    note_class = "metric-note-green" if note_type == "green" else "metric-note-red"
    st.markdown(
        f"""
        <div class="card">
            <div class="metric-icon" style="background:{bg};">{icon}</div>
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="{note_class}">{note}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _calcular_resumen_metodos(df_comparacion):
    df = _safe_df(df_comparacion)
    if df.empty or "Método" not in df.columns:
        return pd.DataFrame(columns=["Método", "Cantidad", "% del Portafolio"])

    if "Es mejor" in df.columns:
        mejores = df[df["Es mejor"] == True].copy()
    else:
        mejores = df.copy()

    if mejores.empty:
        return pd.DataFrame(columns=["Método", "Cantidad", "% del Portafolio"])

    conteo = mejores["Método"].value_counts().reset_index()
    conteo.columns = ["Método", "Cantidad"]
    total = max(1, conteo["Cantidad"].sum())
    conteo["% del Portafolio"] = conteo["Cantidad"] / total
    return conteo


def _calcular_kpis_forecast(df_forecast_auto, df_comparacion):
    fc = _normalizar_fecha(_safe_df(df_forecast_auto))
    comp = _safe_df(df_comparacion)

    out = {
        "productos": 0,
        "wmape": 0.0,
        "bias": 0.0,
        "rmse": 0.0,
        "metodo_mas_usado": "Sin datos",
        "demanda_total_2025": 0.0,
        "pronostico_futuro_total": 0.0,
    }

    if not fc.empty:
        out["productos"] = int(fc["product_id"].nunique()) if "product_id" in fc.columns else 0

        if "tipo_periodo" in fc.columns:
            hist = fc[fc["tipo_periodo"] == "Histórico"].copy()
            fut = fc[fc["tipo_periodo"] == "Pronóstico futuro"].copy()
        else:
            hist = fc.copy()
            fut = pd.DataFrame()

        if not hist.empty and "date" in hist.columns and "demand_real" in hist.columns:
            out["demanda_total_2025"] = float(
                pd.to_numeric(hist[pd.to_datetime(hist["date"]).dt.year == 2025]["demand_real"], errors="coerce").fillna(0).sum()
            )

        if not fut.empty and "demand_forecast" in fut.columns:
            out["pronostico_futuro_total"] = float(pd.to_numeric(fut["demand_forecast"], errors="coerce").fillna(0).sum())

    if not comp.empty:
        if "Es mejor" in comp.columns:
            mejores = comp[comp["Es mejor"] == True].copy()
        else:
            mejores = comp.copy()

        if not mejores.empty:
            if "wMAPE" in mejores.columns:
                out["wmape"] = float(pd.to_numeric(mejores["wMAPE"], errors="coerce").dropna().mean() or 0)
            if "Bias" in mejores.columns:
                out["bias"] = float(pd.to_numeric(mejores["Bias"], errors="coerce").dropna().mean() or 0)
            if "RMSE" in mejores.columns:
                out["rmse"] = float(pd.to_numeric(mejores["RMSE"], errors="coerce").dropna().mean() or 0)
            elif "MAE" in mejores.columns:
                out["rmse"] = float(pd.to_numeric(mejores["MAE"], errors="coerce").dropna().mean() or 0)
            if "Método" in mejores.columns and not mejores["Método"].mode().empty:
                out["metodo_mas_usado"] = str(mejores["Método"].mode().iloc[0])

    return out


def _grafico_demanda_general(df_forecast_auto):
    df = _normalizar_fecha(_safe_df(df_forecast_auto))
    fig = go.Figure()

    if df.empty or "date" not in df.columns:
        fig.update_layout(title="Demanda histórica vs pronóstico general")
        return fig

    if "tipo_periodo" in df.columns:
        hist = df[df["tipo_periodo"] == "Histórico"].copy()
        fut = df[df["tipo_periodo"] == "Pronóstico futuro"].copy()
    else:
        hist = df.copy()
        fut = pd.DataFrame()

    if not hist.empty:
        agg_hist = (
            hist.groupby("date", as_index=False)
            .agg(
                demand_real=("demand_real", "sum"),
                demand_forecast=("demand_forecast", "sum"),
            )
            .sort_values("date")
        )

        fig.add_trace(
            go.Scatter(
                x=agg_hist["date"],
                y=agg_hist["demand_real"],
                mode="lines+markers",
                name="Demanda real",
                line=dict(width=2),
            )
        )

        fig.add_trace(
            go.Scatter(
                x=agg_hist["date"],
                y=agg_hist["demand_forecast"],
                mode="lines+markers",
                name="Ajuste del modelo",
                line=dict(width=2, dash="dot"),
            )
        )

    if not fut.empty:
        agg_fut = (
            fut.groupby("date", as_index=False)
            .agg(demand_forecast=("demand_forecast", "sum"))
            .sort_values("date")
        )

        fig.add_trace(
            go.Scatter(
                x=agg_fut["date"],
                y=agg_fut["demand_forecast"],
                mode="lines+markers",
                name="Pronóstico futuro",
                line=dict(width=3, dash="dash"),
            )
        )

    fig.update_layout(
        title="Demanda histórica vs pronóstico total del portafolio",
        template="plotly_white",
        xaxis_title="Mes",
        yaxis_title="Unidades",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.2, x=0.5, xanchor="center"),
        margin=dict(l=20, r=20, t=60, b=40),
        height=390,
    )
    return fig


def _grafico_metodos(df_comparacion):
    conteo = _calcular_resumen_metodos(df_comparacion)
    if conteo.empty:
        return go.Figure()

    fig = px.pie(
        conteo,
        names="Método",
        values="Cantidad",
        hole=0.52,
        title="Distribución de mejores métodos por producto",
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=55, b=10), height=315)
    return fig


def _grafico_tvu_barras(resumen_vencimientos):
    df = _safe_df(resumen_vencimientos)
    if df.empty:
        return go.Figure()

    col_y = "cantidad_lotes" if "cantidad_lotes" in df.columns else "cantidad_sku"
    fig = px.bar(
        df,
        x="riesgo_tvu",
        y=col_y,
        text=col_y,
        title="Cantidad de lotes por nivel de riesgo",
        labels={"riesgo_tvu": "Riesgo", col_y: "Cantidad"},
    )
    fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=55, b=10), height=300)
    return fig


def _grafico_tvu_valor(resumen_vencimientos):
    df = _safe_df(resumen_vencimientos)
    if df.empty or "valor_en_riesgo" not in df.columns:
        return go.Figure()

    df = df[df["valor_en_riesgo"] > 0].copy()
    if df.empty:
        return go.Figure()

    fig = px.pie(
        df,
        names="riesgo_tvu",
        values="valor_en_riesgo",
        hole=0.52,
        title="Valor económico por riesgo",
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(template="plotly_white", margin=dict(l=10, r=10, t=55, b=10), height=300)
    return fig


def _grafico_ahorro(df_ahorro):
    df = _safe_df(df_ahorro)
    if df.empty or "Ahorro potencial S/" not in df.columns:
        return go.Figure()

    top = df.sort_values("Ahorro potencial S/", ascending=False).head(5).copy()
    fig = px.bar(
        top,
        x="Ahorro potencial S/",
        y="Producto",
        orientation="h",
        title="Top productos con mayor ahorro potencial",
        labels={"Ahorro potencial S/": "Ahorro estimado", "Producto": "Producto"},
    )
    fig.update_layout(
        template="plotly_white",
        yaxis={"categoryorder": "total ascending"},
        margin=dict(l=10, r=10, t=55, b=10),
        height=300,
    )
    return fig


def _grafico_kpis_tendencia(df_forecast_auto):
    df = _normalizar_fecha(_safe_df(df_forecast_auto))
    if df.empty or "date" not in df.columns:
        return go.Figure()

    if "tipo_periodo" in df.columns:
        df = df[df["tipo_periodo"] == "Histórico"].copy()

    if df.empty:
        return go.Figure()

    for c in ["demand_real", "demand_forecast"]:
        if c not in df.columns:
            df[c] = 0
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

    agg = df.groupby(df["date"].dt.year, as_index=False).agg(
        real=("demand_real", "sum"),
        forecast=("demand_forecast", "sum"),
    )
    agg["wMAPE"] = np.where(agg["real"] > 0, abs(agg["forecast"] - agg["real"]) / agg["real"], 0)
    agg["Bias"] = np.where(agg["real"] > 0, (agg["forecast"] - agg["real"]) / agg["real"], 0)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=agg["date"], y=agg["wMAPE"] * 100, mode="lines+markers", name="wMAPE"))
    fig.add_trace(go.Scatter(x=agg["date"], y=agg["Bias"] * 100, mode="lines+markers", name="Bias"))
    fig.update_layout(
        title="Evolución anual de indicadores de forecast",
        template="plotly_white",
        yaxis_title="Porcentaje",
        xaxis_title="Año",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center"),
        margin=dict(l=10, r=10, t=55, b=25),
        height=300,
    )
    return fig


def _top_tvu(df_tvu, n=5):
    df = _safe_df(df_tvu)
    if df.empty:
        return pd.DataFrame(columns=["Lote", "Producto", "TVU", "Stock", "Valor en Riesgo", "Riesgo"])

    cols = {
        "lote": "Lote",
        "producto": "Producto",
        "tvu": "TVU",
        "stock": "Stock",
        "valor_en_riesgo": "Valor en Riesgo",
        "riesgo_tvu": "Riesgo",
    }
    for c in cols:
        if c not in df.columns:
            df[c] = np.nan

    out = df.sort_values(["orden_riesgo", "tvu", "valor_en_riesgo"], ascending=[True, True, False], na_position="last").head(n)
    out = out[list(cols.keys())].rename(columns=cols)
    return out


def _top_ahorro(df_ahorro, n=5):
    df = _safe_df(df_ahorro)
    if df.empty:
        return pd.DataFrame(columns=["Producto", "Ahorro Estimado", "Método"])

    if "Ahorro potencial S/" not in df.columns:
        df["Ahorro potencial S/"] = 0
    if "Mejor método" not in df.columns:
        df["Mejor método"] = "Sin datos"

    out = df.sort_values("Ahorro potencial S/", ascending=False).head(n).copy()
    out = out.rename(columns={"Ahorro potencial S/": "Ahorro Estimado", "Mejor método": "Método"})
    cols = [c for c in ["Producto", "Ahorro Estimado", "Método"] if c in out.columns]
    return out[cols]


def _tabla_alertas(kpis_forecast_calc, kpis_tvu, df_ahorro):
    ahorro = 0
    if isinstance(df_ahorro, pd.DataFrame) and not df_ahorro.empty and "Ahorro potencial S/" in df_ahorro.columns:
        ahorro = float(pd.to_numeric(df_ahorro["Ahorro potencial S/"], errors="coerce").fillna(0).sum())

    lotes_alto = int(kpis_tvu.get("lotes_alto", kpis_tvu.get("sku_alto", 0))) if isinstance(kpis_tvu, dict) else 0
    valor_riesgo = float(kpis_tvu.get("valor_riesgo", 0)) if isinstance(kpis_tvu, dict) else 0
    wmape = kpis_forecast_calc.get("wmape", 0)

    filas = []
    if lotes_alto > 0:
        filas.append(["⚠️ Riesgo TVU", f"{lotes_alto:,} lotes con riesgo alto de vencimiento", "Alta"])
    if valor_riesgo > 0:
        filas.append(["💰 Valor en riesgo", f"{_fmt_money(valor_riesgo)} comprometidos por TVU alto/medio", "Alta"])
    if wmape >= 0.30:
        filas.append(["📈 Pronóstico", f"wMAPE promedio de {_fmt_pct(wmape)}; requiere revisión", "Media"])
    elif wmape > 0:
        filas.append(["📈 Pronóstico", f"wMAPE promedio de {_fmt_pct(wmape)}; desempeño moderado", "Media"])
    if ahorro > 0:
        filas.append(["✅ Ahorro", f"Oportunidad de ahorro estimada de {_fmt_money(ahorro)}", "Media"])
    if not filas:
        filas.append(["✅ Estado general", "No se detectaron alertas críticas con la información disponible", "Baja"])

    return pd.DataFrame(filas, columns=["Tipo", "Mensaje", "Prioridad"])


def mostrar_dashboard(
    df_real=None,
    df_forecast_auto=None,
    df_comparacion=None,
    df_tvu=None,
    resumen_vencimientos=None,
    kpis_tvu=None,
    df_ahorro=None,
    kpis_ahorro=None,
    **kwargs,
):
    """
    Vista general ejecutiva para Streamlit.

    Parámetros esperados desde app.py:
    - df_real
    - df_forecast_auto
    - df_comparacion
    - df_tvu
    - resumen_vencimientos
    - kpis_tvu
    - df_ahorro o df_ahorro_forecast
    - kpis_ahorro o kpis_forecast
    """

    _inject_css()

    df_real = _safe_df(df_real)
    df_forecast_auto = _safe_df(df_forecast_auto)
    df_comparacion = _safe_df(df_comparacion)
    df_tvu = _safe_df(df_tvu)
    resumen_vencimientos = _safe_df(resumen_vencimientos)
    df_ahorro = _safe_df(df_ahorro)
    kpis_tvu = kpis_tvu or {}
    kpis_ahorro = kpis_ahorro or {}

    kpis_forecast_calc = _calcular_kpis_forecast(df_forecast_auto, df_comparacion)
    resumen_metodos = _calcular_resumen_metodos(df_comparacion)

    ahorro_total = float(kpis_ahorro.get("ahorro_total", 0))
    if ahorro_total == 0 and not df_ahorro.empty and "Ahorro potencial S/" in df_ahorro.columns:
        ahorro_total = float(pd.to_numeric(df_ahorro["Ahorro potencial S/"], errors="coerce").fillna(0).sum())

    valor_tvu = float(kpis_tvu.get("valor_riesgo", 0)) if isinstance(kpis_tvu, dict) else 0
    stock_tvu = float(kpis_tvu.get("stock_riesgo", 0)) if isinstance(kpis_tvu, dict) else 0
    lotes_alto = int(kpis_tvu.get("lotes_alto", kpis_tvu.get("sku_alto", 0))) if isinstance(kpis_tvu, dict) else 0
    lotes_medio = int(kpis_tvu.get("lotes_medio", kpis_tvu.get("sku_medio", 0))) if isinstance(kpis_tvu, dict) else 0
    lote_critico = str(kpis_tvu.get("lote_critico", kpis_tvu.get("sku_critico", "Sin datos"))) if isinstance(kpis_tvu, dict) else "Sin datos"

    productos = kpis_forecast_calc["productos"]
    impacto = ahorro_total + valor_tvu

    if not df_forecast_auto.empty and "date" in df_forecast_auto.columns:
        fechas = pd.to_datetime(df_forecast_auto["date"], errors="coerce").dropna()
        periodo = f"{fechas.dt.year.min()} - {fechas.dt.year.max()}" if not fechas.empty else "Sin datos"
    else:
        periodo = "Sin datos"

    st.markdown('<div class="dashboard-title">📊 Vista General</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="dashboard-subtitle">Resumen ejecutivo del desempeño del portafolio: demanda, pronóstico, ahorro y riesgo TVU.</div>',
        unsafe_allow_html=True,
    )

    top_left, top_right = st.columns([5, 1])
    with top_right:
        st.caption("Periodo de análisis")
        st.info(periodo)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        _metric_card("📈", "Demanda Total 2025", _fmt_num(kpis_forecast_calc["demanda_total_2025"]), "Real consolidado", "green", "#eef4ff")
    with c2:
        _metric_card("🎯", "wMAPE Promedio", _fmt_pct(kpis_forecast_calc["wmape"]), "Mejores modelos", "green", "#ecfdf3")
    with c3:
        _metric_card("📦", "Productos Analizados", _fmt_num(productos), "Portafolio evaluado", "green", "#fff7ed")
    with c4:
        _metric_card("⚠️", "Valor en Riesgo TVU", _fmt_money(valor_tvu), f"{lotes_alto:,} lotes alto", "red", "#fef2f2")
    with c5:
        _metric_card("💰", "Ahorro Potencial", _fmt_money(ahorro_total), "Forecast propuesto", "green", "#faf5ff")

    st.write("")

    col1, col2 = st.columns([1.25, 1])
    with col1:
        with st.container():
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">📈 Demanda histórica vs pronóstico general</div>', unsafe_allow_html=True)
            st.plotly_chart(_grafico_demanda_general(df_forecast_auto), use_container_width=True, key="dash_demanda_general")
            st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        with st.container():
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">📦 Marco de Optimización de Inventarios</div>', unsafe_allow_html=True)

            m1, m2, m3 = st.columns(3)
            m1.metric("Método más usado", kpis_forecast_calc["metodo_mas_usado"])
            m2.metric("wMAPE", _fmt_pct(kpis_forecast_calc["wmape"]))
            m3.metric("Bias", _fmt_pct(kpis_forecast_calc["bias"]))

            m4, m5, m6 = st.columns(3)
            m4.metric("RMSE/MAE prom.", _fmt_num(kpis_forecast_calc["rmse"]))
            m5.metric("SKUs comparados", _fmt_num(kpis_ahorro.get("skus_comparados", 0)))
            m6.metric("Impacto identificado", _fmt_money(impacto))

            g1, g2 = st.columns([1, 1])
            with g1:
                st.plotly_chart(_grafico_metodos(df_comparacion), use_container_width=True, key="dash_metodos")
            with g2:
                if resumen_metodos.empty:
                    st.info("No hay métodos ganadores disponibles.")
                else:
                    tabla_metodos = resumen_metodos.head(7).copy()
                    tabla_metodos["% del Portafolio"] = tabla_metodos["% del Portafolio"] * 100
                    st.dataframe(
                        tabla_metodos,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "Cantidad": st.column_config.ProgressColumn(
                                "Cantidad",
                                format="%d",
                                min_value=0,
                                max_value=int(tabla_metodos["Cantidad"].max()) if not tabla_metodos.empty else 1,
                            ),
                            "% del Portafolio": st.column_config.NumberColumn("% Portafolio", format="%.1f %%"),
                        },
                    )
            st.markdown("</div>", unsafe_allow_html=True)

    col3, col4 = st.columns([1, 1])
    with col3:
        with st.container():
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">⚠️ TVU: Productos próximos a vencer</div>', unsafe_allow_html=True)

            t1, t2, t3, t4 = st.columns(4)
            t1.metric("Lotes alto", f"{lotes_alto:,}")
            t2.metric("Lotes medio", f"{lotes_medio:,}")
            t3.metric("Stock en riesgo", _fmt_num(stock_tvu))
            t4.metric("Valor en riesgo", _fmt_money(valor_tvu))
            st.markdown(f'<div class="blue-band">Lote más crítico: {lote_critico}</div>', unsafe_allow_html=True)

            tvu1, tvu2 = st.columns(2)
            with tvu1:
                st.plotly_chart(_grafico_tvu_barras(resumen_vencimientos), use_container_width=True, key="dash_tvu_barras")
            with tvu2:
                st.plotly_chart(_grafico_tvu_valor(resumen_vencimientos), use_container_width=True, key="dash_tvu_valor")
            st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        with st.container():
            st.markdown('<div class="section-card">', unsafe_allow_html=True)
            st.markdown('<div class="section-title">📊 Indicadores clave de desempeño</div>', unsafe_allow_html=True)

            k1, k2, k3, k4, k5 = st.columns(5)
            k1.metric("wMAPE", _fmt_pct(kpis_forecast_calc["wmape"]))
            k2.metric("RMSE/MAE", _fmt_num(kpis_forecast_calc["rmse"]))
            k3.metric("Bias", _fmt_pct(kpis_forecast_calc["bias"]))
            k4.metric("TVU alto", f"{lotes_alto:,}")
            k5.metric("Ahorro", _fmt_money(ahorro_total))

            sub1, sub2 = st.columns([1.4, 0.8])
            with sub1:
                st.plotly_chart(_grafico_kpis_tendencia(df_forecast_auto), use_container_width=True, key="dash_kpis_tendencia")
            with sub2:
                st.markdown("**Insights generales**")
                wmape = kpis_forecast_calc["wmape"]
                if wmape < 0.20 and wmape > 0:
                    st.success("El forecast presenta buen nivel de precisión.")
                elif wmape > 0:
                    st.warning("El forecast tiene precisión moderada; conviene revisión manual.")
                else:
                    st.info("No se cuenta con wMAPE suficiente para evaluar precisión.")

                if lotes_alto > 0:
                    st.warning(f"Existen {lotes_alto:,} lotes en alto riesgo TVU.")
                else:
                    st.success("No se detectan lotes de alto riesgo TVU.")

                if ahorro_total > 0:
                    st.info(f"Oportunidad de ahorro estimada de {_fmt_money(ahorro_total)}.")
                else:
                    st.info("No se calculó ahorro económico por falta de forecast comercial.")
            st.markdown("</div>", unsafe_allow_html=True)

    col5, col6, col7 = st.columns([1, 1, 1])
    with col5:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Top 5 productos con mayor riesgo TVU</div>', unsafe_allow_html=True)
        top_tvu = _top_tvu(df_tvu, 5)
        if top_tvu.empty:
            st.info("Sin datos TVU.")
        else:
            st.dataframe(
                top_tvu.style.format({
                    "TVU": "{:,.2f}",
                    "Stock": "{:,.0f}",
                    "Valor en Riesgo": "S/ {:,.2f}",
                }, na_rep="-"),
                use_container_width=True,
                hide_index=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with col6:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Top 5 productos con mayor ahorro potencial</div>', unsafe_allow_html=True)
        top_ahorro = _top_ahorro(df_ahorro, 5)
        if top_ahorro.empty:
            st.info("Sin datos de ahorro.")
        else:
            st.dataframe(
                top_ahorro.style.format({"Ahorro Estimado": "S/ {:,.2f}"}, na_rep="-"),
                use_container_width=True,
                hide_index=True,
            )
        st.markdown("</div>", unsafe_allow_html=True)

    with col7:
        st.markdown('<div class="section-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Alertas y recomendaciones</div>', unsafe_allow_html=True)
        alertas = _tabla_alertas(kpis_forecast_calc, kpis_tvu, df_ahorro)
        st.dataframe(alertas, use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("📌 Ver gráfico de ahorro potencial"):
        if df_ahorro.empty:
            st.info("No se calculó ahorro potencial porque falta Forecast_Comercial o costos unitarios.")
        else:
            st.plotly_chart(_grafico_ahorro(df_ahorro), use_container_width=True, key="dash_ahorro")
