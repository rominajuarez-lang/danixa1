import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# =========================================================
# DASHBOARD EJECUTIVO - VISTA GENERAL
# Archivo independiente para no modificar la lógica principal.
# =========================================================


def _num(x, default=0.0):
    try:
        if pd.isna(x):
            return default
        return float(x)
    except Exception:
        return default


def _fmt_soles(x):
    return f"S/ {_num(x):,.0f}"


def _fmt_num(x):
    return f"{_num(x):,.0f}"


def _safe_df(df):
    return df if isinstance(df, pd.DataFrame) else pd.DataFrame()


def _inyectar_css_dashboard():
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.3rem;
            padding-bottom: 2rem;
        }
        .dash-hero {
            padding: 1.25rem 1.4rem;
            border-radius: 22px;
            background: linear-gradient(135deg, #0f172a 0%, #1e293b 45%, #334155 100%);
            color: white;
            margin-bottom: 1rem;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.18);
        }
        .dash-hero h1 {
            margin: 0;
            font-size: 2.1rem;
            line-height: 1.15;
        }
        .dash-hero p {
            margin: 0.35rem 0 0 0;
            opacity: 0.86;
            font-size: 1rem;
        }
        .dash-card {
            border: 1px solid rgba(148, 163, 184, 0.25);
            border-radius: 18px;
            padding: 1rem 1.05rem;
            background: rgba(255,255,255,0.72);
            box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
            min-height: 116px;
        }
        .dash-kpi-label {
            color: #64748b;
            font-size: 0.83rem;
            font-weight: 650;
            margin-bottom: 0.25rem;
        }
        .dash-kpi-value {
            color: #0f172a;
            font-size: 1.45rem;
            font-weight: 800;
            margin-bottom: 0.15rem;
        }
        .dash-kpi-help {
            color: #64748b;
            font-size: 0.78rem;
        }
        .dash-section-title {
            font-size: 1.2rem;
            font-weight: 800;
            color: #0f172a;
            margin-top: 0.8rem;
            margin-bottom: 0.35rem;
        }
        .dash-alert {
            border-left: 5px solid #f59e0b;
            background: #fffbeb;
            padding: 0.85rem 1rem;
            border-radius: 14px;
            margin-bottom: 0.6rem;
            color: #78350f;
        }
        .dash-ok {
            border-left: 5px solid #10b981;
            background: #ecfdf5;
            padding: 0.85rem 1rem;
            border-radius: 14px;
            margin-bottom: 0.6rem;
            color: #064e3b;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _card(label, value, help_text=""):
    st.markdown(
        f"""
        <div class="dash-card">
            <div class="dash-kpi-label">{label}</div>
            <div class="dash-kpi-value">{value}</div>
            <div class="dash-kpi-help">{help_text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _preparar_forecast_general(df_forecast_auto: pd.DataFrame) -> pd.DataFrame:
    df = _safe_df(df_forecast_auto).copy()
    columnas = {"date", "demand_forecast"}
    if df.empty or not columnas.issubset(set(df.columns)):
        return pd.DataFrame(columns=["date", "Serie", "Unidades"])

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df = df.dropna(subset=["date"])
    df["demand_forecast"] = pd.to_numeric(df["demand_forecast"], errors="coerce").fillna(0)

    if "demand_real" not in df.columns:
        df["demand_real"] = 0
    df["demand_real"] = pd.to_numeric(df["demand_real"], errors="coerce").fillna(0)

    if "tipo_periodo" not in df.columns:
        df["tipo_periodo"] = "Histórico"

    hist = df[df["tipo_periodo"].astype(str).str.lower().eq("histórico") | df["tipo_periodo"].astype(str).str.lower().eq("historico")].copy()
    futuro = df[df["tipo_periodo"].astype(str).str.lower().str.contains("pron", na=False)].copy()

    partes = []
    if not hist.empty:
        real = hist.groupby("date", as_index=False)["demand_real"].sum()
        real["Serie"] = "Demanda real total"
        real = real.rename(columns={"demand_real": "Unidades"})
        partes.append(real[["date", "Serie", "Unidades"]])

        ajuste = hist.groupby("date", as_index=False)["demand_forecast"].sum()
        ajuste["Serie"] = "Forecast ajustado total"
        ajuste = ajuste.rename(columns={"demand_forecast": "Unidades"})
        partes.append(ajuste[["date", "Serie", "Unidades"]])

    if not futuro.empty:
        fut = futuro.groupby("date", as_index=False)["demand_forecast"].sum()
        fut["Serie"] = "Pronóstico futuro total"
        fut = fut.rename(columns={"demand_forecast": "Unidades"})
        partes.append(fut[["date", "Serie", "Unidades"]])

    if not partes:
        return pd.DataFrame(columns=["date", "Serie", "Unidades"])

    out = pd.concat(partes, ignore_index=True)
    out = out.sort_values(["date", "Serie"])
    return out


def grafico_forecast_general(df_forecast_auto: pd.DataFrame):
    df_plot = _preparar_forecast_general(df_forecast_auto)
    fig = px.line(
        df_plot,
        x="date",
        y="Unidades",
        color="Serie",
        markers=True,
        title="Demanda total vs forecast total del portafolio",
        labels={"date": "Mes", "Unidades": "Unidades"},
    )
    fig.update_layout(
        template="plotly_white",
        hovermode="x unified",
        legend=dict(orientation="h", y=-0.22, x=0.5, xanchor="center"),
        margin=dict(l=20, r=20, t=60, b=25),
    )
    return fig


def grafico_modelos_ganadores_dashboard(df_comparacion: pd.DataFrame):
    df = _safe_df(df_comparacion).copy()
    if df.empty or "Es mejor" not in df.columns or "Método" not in df.columns:
        return go.Figure()
    mejores = df[df["Es mejor"] == True].copy()
    conteo = mejores["Método"].value_counts().reset_index()
    conteo.columns = ["Método", "Cantidad de SKUs"]
    fig = px.pie(
        conteo,
        names="Método",
        values="Cantidad de SKUs",
        hole=0.52,
        title="Distribución de modelos ganadores",
    )
    fig.update_traces(textposition="inside", textinfo="percent+label")
    fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=60, b=20))
    return fig


def grafico_tvu_dashboard(resumen_vencimientos: pd.DataFrame):
    df = _safe_df(resumen_vencimientos).copy()
    if df.empty or "riesgo_tvu" not in df.columns:
        return go.Figure()
    y_col = "valor_en_riesgo" if "valor_en_riesgo" in df.columns else "stock"
    fig = px.bar(
        df,
        x="riesgo_tvu",
        y=y_col,
        text=y_col,
        title="TVU: valor económico por nivel de riesgo",
        labels={"riesgo_tvu": "Riesgo", y_col: "Valor / stock"},
    )
    fig.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    fig.update_layout(template="plotly_white", margin=dict(l=20, r=20, t=60, b=20))
    return fig


def grafico_ahorro_dashboard(df_ahorro: pd.DataFrame, top_n: int = 10):
    df = _safe_df(df_ahorro).copy()
    if df.empty or "Ahorro potencial S/" not in df.columns or "Producto" not in df.columns:
        return go.Figure()
    df = df.sort_values("Ahorro potencial S/", ascending=False).head(top_n)
    fig = px.bar(
        df,
        x="Ahorro potencial S/",
        y="Producto",
        orientation="h",
        title=f"Top {top_n} SKUs con mayor ahorro potencial",
        labels={"Ahorro potencial S/": "Ahorro potencial (S/)", "Producto": "SKU"},
    )
    fig.update_layout(
        template="plotly_white",
        yaxis={"categoryorder": "total ascending"},
        margin=dict(l=20, r=20, t=60, b=20),
    )
    return fig


def _calcular_kpis_modelo(df_comparacion: pd.DataFrame):
    df = _safe_df(df_comparacion).copy()
    if df.empty:
        return {"wmape": 0, "bias": 0, "rmse": 0, "modelo_mas_usado": "Sin datos", "modelos": 0}
    mejores = df[df["Es mejor"] == True].copy() if "Es mejor" in df.columns else df.copy()
    modelo = "Sin datos"
    if not mejores.empty and "Método" in mejores.columns:
        moda = mejores["Método"].mode()
        modelo = moda.iloc[0] if not moda.empty else "Sin datos"
    return {
        "wmape": _num(mejores["wMAPE"].mean() if "wMAPE" in mejores.columns else 0),
        "bias": _num(mejores["Bias"].mean() if "Bias" in mejores.columns else 0),
        "rmse": _num(mejores["RMSE"].mean() if "RMSE" in mejores.columns else 0),
        "modelo_mas_usado": modelo,
        "modelos": int(df["Método"].nunique()) if "Método" in df.columns else 0,
    }


def _estado_general(wmape, ahorro_total, valor_tvu, lotes_alto):
    puntos = 0
    if wmape <= 0.20:
        puntos += 1
    if ahorro_total > 0:
        puntos += 1
    if valor_tvu <= 0 or lotes_alto == 0:
        puntos += 1
    if puntos >= 3:
        return "🟢 Controlado", "El portafolio muestra buena precisión, impacto económico positivo y bajo riesgo TVU."
    if puntos == 2:
        return "🟡 En observación", "Hay beneficios relevantes, pero todavía existen puntos de control por revisar."
    return "🔴 Crítico", "Se recomienda priorizar correcciones de forecast, inventario o vencimiento."


def _generar_alertas(kpis_modelo, kpis_forecast, kpis_tvu, df_tvu, df_ahorro):
    alertas = []
    wmape = kpis_modelo.get("wmape", 0)
    if wmape > 0.30:
        alertas.append(f"El wMAPE promedio de los mejores modelos es alto: {wmape:.1%}.")
    elif wmape > 0:
        alertas.append(f"El wMAPE promedio de los mejores modelos es {wmape:.1%}.")

    ahorro = _num(kpis_forecast.get("ahorro_total", 0)) if isinstance(kpis_forecast, dict) else 0
    if ahorro > 0:
        alertas.append(f"El forecast propuesto identifica un ahorro potencial de {_fmt_soles(ahorro)}.")
    elif not _safe_df(df_ahorro).empty:
        alertas.append("El ahorro total no es positivo; revisar SKUs donde el forecast propuesto no mejora al comercial.")

    lotes_alto = int(_num(kpis_tvu.get("lotes_alto", 0))) if isinstance(kpis_tvu, dict) else 0
    valor_tvu = _num(kpis_tvu.get("valor_riesgo", 0)) if isinstance(kpis_tvu, dict) else 0
    if lotes_alto > 0:
        alertas.append(f"Existen {lotes_alto:,} lotes en riesgo alto por TVU.")
    if valor_tvu > 0:
        alertas.append(f"El valor económico comprometido por TVU alto/medio es {_fmt_soles(valor_tvu)}.")

    if _safe_df(df_tvu).empty:
        alertas.append("No se encontró información TVU; validar que el Excel tenga la hoja TVU.")

    if not alertas:
        alertas.append("No se detectaron alertas críticas con la información cargada.")
    return alertas[:6]


def mostrar_dashboard(
    df_real=None,
    df_forecast_auto=None,
    df_comparacion=None,
    df_tvu=None,
    resumen_vencimientos=None,
    kpis_tvu=None,
    df_ahorro_forecast=None,
    kpis_forecast=None,
    resumen_productos_tvu=None,
):
    """
    Renderiza una Vista General Ejecutiva reutilizando los DataFrames ya calculados.
    No modifica ni recalcula la lógica de pronóstico, inventario ni TVU.
    """
    _inyectar_css_dashboard()

    df_real = _safe_df(df_real)
    df_forecast_auto = _safe_df(df_forecast_auto)
    df_comparacion = _safe_df(df_comparacion)
    df_tvu = _safe_df(df_tvu)
    resumen_vencimientos = _safe_df(resumen_vencimientos)
    df_ahorro_forecast = _safe_df(df_ahorro_forecast)
    resumen_productos_tvu = _safe_df(resumen_productos_tvu)
    kpis_tvu = kpis_tvu or {}
    kpis_forecast = kpis_forecast or {}

    kpis_modelo = _calcular_kpis_modelo(df_comparacion)

    total_skus_forecast = int(df_real["product_id"].nunique()) if not df_real.empty and "product_id" in df_real.columns else 0
    total_skus_tvu = int(df_tvu["producto"].nunique()) if not df_tvu.empty and "producto" in df_tvu.columns else 0
    total_skus = max(total_skus_forecast, total_skus_tvu)

    ahorro_total = _num(kpis_forecast.get("ahorro_total", 0))
    error_empresa = _num(kpis_forecast.get("error_empresa", 0))
    error_propuesta = _num(kpis_forecast.get("error_propuesta", 0))
    valor_tvu = _num(kpis_tvu.get("valor_riesgo", 0))
    lotes_alto = int(_num(kpis_tvu.get("lotes_alto", 0)))
    lotes_medio = int(_num(kpis_tvu.get("lotes_medio", 0)))
    stock_riesgo = _num(kpis_tvu.get("stock_riesgo", 0))
    impacto_total = ahorro_total + valor_tvu

    estado, descripcion_estado = _estado_general(kpis_modelo["wmape"], ahorro_total, valor_tvu, lotes_alto)

    st.markdown(
        f"""
        <div class="dash-hero">
            <h1>📊 Dashboard Ejecutivo de Inventarios</h1>
            <p>Vista general de pronóstico, ahorro económico, modelos ganadores y riesgo de vencimiento por lote.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_estado, col_desc = st.columns([1.2, 2.8])
    with col_estado:
        _card("Estado general", estado, "Lectura rápida del sistema")
    with col_desc:
        st.markdown(
            f"""
            <div class="dash-card">
                <div class="dash-kpi-label">Interpretación ejecutiva</div>
                <div style="font-size:1.05rem; color:#0f172a; font-weight:650;">{descripcion_estado}</div>
                <div class="dash-kpi-help" style="margin-top:.35rem;">Este estado combina precisión del forecast, ahorro potencial y riesgo TVU.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="dash-section-title">Indicadores principales</div>', unsafe_allow_html=True)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        _card("SKU evaluados", f"{total_skus:,}", "Portafolio analizado")
    with k2:
        _card("Ahorro potencial", _fmt_soles(ahorro_total), "Forecast propuesto vs empresa")
    with k3:
        _card("Valor TVU en riesgo", _fmt_soles(valor_tvu), "Riesgo alto + medio")
    with k4:
        _card("Impacto identificado", _fmt_soles(impacto_total), "Ahorro + riesgo económico")
    with k5:
        _card("Modelo dominante", str(kpis_modelo["modelo_mas_usado"]), f"{kpis_modelo['modelos']} métodos evaluados")

    st.markdown('<div class="dash-section-title">Forecast general del portafolio</div>', unsafe_allow_html=True)
    df_forecast_general = _preparar_forecast_general(df_forecast_auto)
    if df_forecast_general.empty:
        st.info("Todavía no hay información suficiente para graficar la demanda y el pronóstico general.")
    else:
        st.plotly_chart(grafico_forecast_general(df_forecast_auto), use_container_width=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _card("wMAPE promedio", f"{kpis_modelo['wmape']:.1%}", "Promedio de mejores modelos")
    with c2:
        _card("Bias promedio", f"{kpis_modelo['bias']:.1%}", "Sesgo del forecast")
    with c3:
        _card("RMSE promedio", _fmt_num(kpis_modelo["rmse"]), "Error promedio")
    with c4:
        _card("SKUs comparados", f"{int(_num(kpis_forecast.get('skus_comparados', 0))):,}", "Con forecast comercial")

    st.markdown('<div class="dash-section-title">Análisis comparativo</div>', unsafe_allow_html=True)
    g1, g2 = st.columns([1.15, 1])
    with g1:
        if df_ahorro_forecast.empty:
            st.info("No hay ahorro económico calculado. Debe existir Forecast_Comercial y costos unitarios en Datos.")
        else:
            top_n = st.slider("Top SKUs por ahorro", 5, 30, 10, 5)
            st.plotly_chart(grafico_ahorro_dashboard(df_ahorro_forecast, top_n=top_n), use_container_width=True)
    with g2:
        if df_comparacion.empty:
            st.info("No hay comparación de métodos disponible.")
        else:
            st.plotly_chart(grafico_modelos_ganadores_dashboard(df_comparacion), use_container_width=True)

    st.markdown('<div class="dash-section-title">Riesgo TVU por lote</div>', unsafe_allow_html=True)
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        _card("Lotes alto", f"{lotes_alto:,}", "TVU menor a 5")
    with t2:
        _card("Lotes medio", f"{lotes_medio:,}", "TVU entre 5 y 10")
    with t3:
        _card("Stock en riesgo", _fmt_num(stock_riesgo), "Unidades alto + medio")
    with t4:
        _card("Lote crítico", str(kpis_tvu.get("lote_critico", "Sin datos")), "Menor TVU / mayor valor")

    tvu_col1, tvu_col2 = st.columns([1.1, 1])
    with tvu_col1:
        if resumen_vencimientos.empty:
            st.info("No hay resumen TVU disponible.")
        else:
            st.plotly_chart(grafico_tvu_dashboard(resumen_vencimientos), use_container_width=True)
    with tvu_col2:
        st.markdown("#### 🚨 Alertas automáticas")
        for alerta in _generar_alertas(kpis_modelo, kpis_forecast, kpis_tvu, df_tvu, df_ahorro_forecast):
            clase = "dash-alert" if "alto" in alerta.lower() or "riesgo" in alerta.lower() or "no se" in alerta.lower() else "dash-ok"
            st.markdown(f'<div class="{clase}">{alerta}</div>', unsafe_allow_html=True)

    st.markdown('<div class="dash-section-title">Rankings ejecutivos</div>', unsafe_allow_html=True)
    r1, r2 = st.columns(2)
    with r1:
        st.markdown("#### 💰 Top ahorro por SKU")
        if df_ahorro_forecast.empty:
            st.info("Sin datos de ahorro.")
        else:
            cols = [c for c in ["Producto", "Mejor método", "Ahorro potencial S/", "wMAPE empresa", "wMAPE propuesta"] if c in df_ahorro_forecast.columns]
            top_ahorro = df_ahorro_forecast.sort_values("Ahorro potencial S/", ascending=False).head(10)[cols]
            st.dataframe(
                top_ahorro.style.format({
                    "Ahorro potencial S/": "S/ {:,.2f}",
                    "wMAPE empresa": "{:.1%}",
                    "wMAPE propuesta": "{:.1%}",
                }),
                use_container_width=True,
                hide_index=True,
            )
    with r2:
        st.markdown("#### ⚠️ Top riesgo TVU")
        if df_tvu.empty:
            st.info("Sin datos TVU.")
        else:
            df_top = df_tvu.copy().head(10)
            rename = {
                "lote": "Lote",
                "producto": "Producto",
                "warehouse": "Warehouse",
                "tvu": "TVU",
                "stock": "Stock",
                "valor_en_riesgo": "Valor en riesgo",
                "riesgo_tvu": "Riesgo",
            }
            cols = [c for c in ["lote", "producto", "warehouse", "tvu", "stock", "valor_en_riesgo", "riesgo_tvu"] if c in df_top.columns]
            df_top = df_top[cols].rename(columns=rename)
            st.dataframe(
                df_top.style.format({
                    "TVU": "{:,.2f}",
                    "Stock": "{:,.0f}",
                    "Valor en riesgo": "S/ {:,.2f}",
                }),
                use_container_width=True,
                hide_index=True,
            )

    st.markdown('<div class="dash-section-title">Resumen económico</div>', unsafe_allow_html=True)
    e1, e2, e3 = st.columns(3)
    with e1:
        _card("Error forecast empresa", _fmt_soles(error_empresa), "Costo de error 2025")
    with e2:
        _card("Error forecast propuesto", _fmt_soles(error_propuesta), "Costo de error 2025")
    with e3:
        mejora = (ahorro_total / error_empresa) if error_empresa > 0 else 0
        _card("Mejora relativa", f"{mejora:.1%}", "Ahorro / error empresa")

    with st.expander("📋 Ver resumen TVU por producto"):
        if resumen_productos_tvu.empty:
            st.info("No hay resumen por producto disponible.")
        else:
            st.dataframe(resumen_productos_tvu, use_container_width=True, hide_index=True)
