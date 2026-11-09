"""Indicador 5 - Rendimento dos Responsáveis pelos domicílios (Censo 2022).

Fontes aceitas:
  1) API do SIDRA: cole o caminho gerado em sidra.ibge.gov.br (tabela -> botão "API").
  2) Arquivo CSV/XLSX baixado do IBGE (ex.: Agregados por Setores Censitários,
     coluna de rendimento médio do responsável) ou exportado do SIDRA.
  3) Demonstração (dados sintéticos) só para testar a tela.

Você escolhe, na própria tela, qual coluna é o território (UF/município) e qual é o valor.
"""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

import ibge_utils as u

SALARIO_MINIMO_2022 = 1212.0  # valor vigente na data de referência do Censo 2022


@st.cache_data(show_spinner=False)
def _demo() -> pd.DataFrame:
    rng = np.random.default_rng(7)
    ufs = list(u.UF_REGIAO)
    base = {"Norte": 7.35, "Nordeste": 7.25, "Sudeste": 7.75, "Sul": 7.7, "Centro-Oeste": 7.7}
    linhas = []
    for i in range(1500):
        uf = ufs[i % len(ufs)]
        linhas.append((f"Local {i} - {uf}", uf, float(rng.lognormal(base[u.UF_REGIAO[uf]], 0.55))))
    return pd.DataFrame(linhas, columns=["territorio", "uf", "rendimento"])


def _le_arquivo(up) -> pd.DataFrame:
    if up.name.lower().endswith("csv"):
        try:
            return pd.read_csv(up, sep=None, engine="python", decimal=",")
        except Exception:
            up.seek(0)
            return pd.read_csv(up)
    return pd.read_excel(up)


def _escolhe_colunas(bruto: pd.DataFrame) -> pd.DataFrame:
    cols = list(bruto.columns)
    c1, c2 = st.columns(2)
    col_terr = c1.selectbox("Coluna do território (UF ou 'Município - UF')", cols, key="ren_terr")
    num = [c for c in cols if c != col_terr]
    col_val = c2.selectbox("Coluna do rendimento (R$)", num, key="ren_val")
    d = pd.DataFrame({
        "territorio": bruto[col_terr].astype(str),
        "rendimento": pd.to_numeric(bruto[col_val].astype(str).str.replace(",", ".", regex=False),
                                    errors="coerce"),
    })
    ufs = set(u.UF_REGIAO)
    d["uf"] = np.where(d["territorio"].str.upper().isin(ufs), d["territorio"].str.upper(),
                       u.extrai_uf(d["territorio"]))
    return d


def render():
    st.header("💰 Rendimento dos Responsáveis")
    st.caption("Rendimento nominal mensal da pessoa responsável pelo domicílio — Censo 2022 (IBGE)")

    fonte = st.radio("Fonte dos dados", ["API do SIDRA", "Arquivo CSV/XLSX", "Demonstração (sintético)"],
                     horizontal=True, key="ren_fonte")
    try:
        if fonte == "API do SIDRA":
            caminho = st.text_input("Caminho da API (tudo depois de /values)",
                                    placeholder="/t/XXXX/n3/all/v/XXX/p/2022", key="ren_path")
            if not caminho:
                st.info("Gere o caminho em sidra.ibge.gov.br: abra a tabela de rendimento do responsável "
                        "(Censo 2022), selecione UF ou município e use o botão **API**.")
                st.stop()
            bruto = u.sidra(caminho)
            bruto = bruto.drop(columns=[c for c in bruto.columns if "Código" in str(c)], errors="ignore")
            d = _escolhe_colunas(bruto)
        elif fonte == "Arquivo CSV/XLSX":
            up = st.file_uploader("Envie o arquivo", type=["csv", "xlsx"], key="ren_up")
            if up is None:
                st.stop()
            d = _escolhe_colunas(_le_arquivo(up))
        else:
            d = _demo()
            st.warning("Dados SINTÉTICOS, apenas para testar a tela. Não use na apresentação.")
    except Exception as e:
        st.error(f"Falha ao carregar os dados: {e}")
        st.stop()

    d = d.dropna(subset=["rendimento"])
    d = d[d["rendimento"] > 0].copy()
    d["regiao"] = d["uf"].map(u.UF_REGIAO)

    if d["uf"].notna().any():
        regs = st.multiselect("Regiões", list(u.REGIOES), default=list(u.REGIOES), key="ren_reg")
        d = d[d["regiao"].isin(regs) | d["regiao"].isna()]
    if d.empty:
        st.info("Nenhum dado para os filtros escolhidos.")
        st.stop()

    s = d["rendimento"]
    r = u.resumo(s, 0)
    brl = lambda v: "R$ " + f"{v:,.0f}".replace(",", ".")

    c = st.columns(6)
    c[0].metric("Média", brl(r["média"]))
    c[1].metric("Mediana", brl(r["mediana"]))
    c[2].metric("Moda (R$ arred.)", brl(r["moda"]))
    c[3].metric("Desvio padrão", brl(r["desvio padrão"]))
    c[4].metric("IQR", brl(r["IQR"]))
    c[5].metric("Outliers", r["nº outliers"])

    gap = 100 * (r["média"] - r["mediana"]) / r["mediana"]
    st.metric("Média acima da mediana", f"{gap:.1f}%".replace(".", ","),
              help="Quanto maior, mais os valores altos puxam a média (assimetria à direita).")

    g1, g2 = st.columns(2)
    with g1:
        lim = r["limite superior"]
        ver_todos = st.checkbox("Mostrar também os outliers no histograma", value=False, key="ren_out")
        dh = d if ver_todos else d[d["rendimento"] <= lim]
        fig = px.histogram(dh, x="rendimento", nbins=50, title="Distribuição do rendimento",
                           labels={"rendimento": "Rendimento (R$)"})
        fig.add_vline(x=r["média"], line_dash="dash", annotation_text="média")
        fig.add_vline(x=r["mediana"], line_dash="dot", annotation_text="mediana", annotation_position="bottom")
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        if d["regiao"].notna().any():
            fig = px.box(d, x="regiao", y="rendimento", points="outliers", title="Boxplot por região",
                         labels={"rendimento": "Rendimento (R$)", "regiao": ""})
        else:
            fig = px.box(d, y="rendimento", points="outliers", title="Boxplot")
        st.plotly_chart(fig, use_container_width=True)

    if d["uf"].notna().any():
        por_uf = d.groupby("uf")["rendimento"].agg(mediana="median", média="mean").reset_index()
        por_uf = por_uf.sort_values("mediana", ascending=False)
        fig = px.bar(por_uf, x="uf", y=["mediana", "média"], barmode="group",
                     title="Mediana e média do rendimento por UF",
                     labels={"value": "R$", "uf": "UF", "variable": ""})
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Medidas estatísticas completas"):
        st.dataframe(u.tabela_resumo(s, 0), hide_index=True)
        out, lo, hi = u.outliers(s)
        st.write(f"Outliers: acima de {brl(hi)} (limite inferior: {brl(max(lo, 0))}) — "
                 f"{len(out)} de {len(s)} observações ({100 * len(out) / len(s):.1f}%).")
        st.write("**Efeito dos outliers:** média sem outliers = "
                 f"{brl(s.drop(out.index).mean())} (com outliers: {brl(r['média'])}); "
                 f"mediana sem outliers = {brl(s.drop(out.index).median())} "
                 f"(com outliers: {brl(r['mediana'])}).")

    st.subheader("Interpretação")
    sm = r["mediana"] / SALARIO_MINIMO_2022
    st.markdown(
        f"- A **média ({brl(r['média'])})** fica {gap:.1f}% acima da **mediana ({brl(r['mediana'])})**: "
        f"poucos rendimentos muito altos puxam a média. Por isso a mediana representa melhor o responsável típico "
        f"(≈ {sm:.1f} salário(s) mínimo(s) de 2022).\n"
        f"- Metade central dos dados está entre {brl(r['Q1'])} e {brl(r['Q3'])} (IQR = {brl(r['IQR'])}); "
        f"o coeficiente de variação é {r['coef. variação (%)']:.0f}%, indicando **alta dispersão**.\n"
        f"- Há {r['nº outliers']} outliers acima de {brl(r['limite superior'])}, que concentram a cauda superior da renda.\n"
        f"- Comparando regiões/UF no boxplot e nas barras, é possível discutir a **desigualdade regional** "
        f"de renda (relacionar com EM13CHS402)."
    )
    st.caption("Atenção: estatísticas calculadas sobre os territórios/setores (cada linha pesa igual, sem ponderar "
               "pelo nº de domicílios). A média de médias não é a média nacional dos responsáveis.")

    u.mostra_noticias("rendimento responsáveis domicílios Censo 2022 IBGE renda")


if __name__ == "__main__":
    st.set_page_config(page_title="Rendimento dos Responsáveis", layout="wide")
    render()
