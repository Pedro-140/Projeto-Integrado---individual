"""Indicador 4 - Mulheres (Censo 2022, população residente por sexo).

Unidade de análise: município. Variável: % de mulheres na população.
Fonte: SIDRA, tabela 9514 (Censo 2022). CONFIRA os códigos em
https://sidra.ibge.gov.br/tabela/9514 -> botão "API" e ajuste CAMINHO se preciso.
"""
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

import ibge_utils as u

# v/93 = população residente | c2/4,5 = homens, mulheres
# c287 / c286 = totais de idade e de forma de declaração (confirme na tela da API)
CAMINHO = "/t/9514/n6/all/v/93/p/2022/c2/4,5/c287/100362/c286/113635"


@st.cache_data(show_spinner=False)
def _demo() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    ufs = list(u.UF_REGIAO)
    linhas = []
    for i in range(600):
        uf = ufs[i % len(ufs)]
        total = int(rng.lognormal(9.5, 1.2))
        pct = np.clip(rng.normal(50.8, 1.2), 44, 57)
        m = int(total * pct / 100)
        linhas.append((f"Município {i} - {uf}", uf, total - m, m))
    d = pd.DataFrame(linhas, columns=["municipio", "uf", "homens", "mulheres"])
    return d


@st.cache_data(show_spinner=False)
def _carrega_sidra() -> pd.DataFrame:
    df = u.sidra(CAMINHO)
    col_mun = next(c for c in df.columns if c.startswith("Município") and "Código" not in c)
    p = df.pivot_table(index=col_mun, columns="Sexo", values="Valor", aggfunc="sum").reset_index()
    p = p.rename(columns={col_mun: "municipio", "Homens": "homens", "Mulheres": "mulheres"})
    p["uf"] = u.extrai_uf(p["municipio"])
    return p.dropna(subset=["uf"])


def _prepara(d: pd.DataFrame) -> pd.DataFrame:
    d = d.copy()
    d["total"] = d["homens"] + d["mulheres"]
    d["pct_mulheres"] = 100 * d["mulheres"] / d["total"]
    d["razao_sexos"] = 100 * d["homens"] / d["mulheres"]  # homens por 100 mulheres
    d["regiao"] = d["uf"].map(u.UF_REGIAO)
    return d


def render():
    st.header("👩 Mulheres")
    st.caption("Proporção de mulheres na população residente — Censo 2022 (IBGE/SIDRA)")

    fonte = st.radio("Fonte dos dados", ["API do SIDRA", "Arquivo CSV/XLSX", "Demonstração (sintético)"],
                     horizontal=True, key="mul_fonte")
    try:
        if fonte == "API do SIDRA":
            d = _carrega_sidra()
        elif fonte == "Arquivo CSV/XLSX":
            up = st.file_uploader("Colunas esperadas: municipio, homens, mulheres (UF no nome: 'Cidade - MG')",
                                  type=["csv", "xlsx"], key="mul_up")
            if up is None:
                st.stop()
            d = pd.read_csv(up) if up.name.endswith("csv") else pd.read_excel(up)
            d["uf"] = u.extrai_uf(d["municipio"])
        else:
            d = _demo()
            st.warning("Dados SINTÉTICOS, apenas para testar a tela. Não use na apresentação.")
    except Exception as e:
        st.error(f"Falha ao carregar os dados: {e}\n\nConfira CAMINHO em mulheres.py ou use outra fonte.")
        st.stop()

    d = _prepara(d)

    regs = st.multiselect("Regiões", list(u.REGIOES), default=list(u.REGIOES), key="mul_reg")
    d = d[d["regiao"].isin(regs)]
    if d.empty:
        st.info("Selecione ao menos uma região.")
        st.stop()

    s = d["pct_mulheres"]
    r = u.resumo(s, 2)
    pct_pop = 100 * d["mulheres"].sum() / d["total"].sum()

    c = st.columns(5)
    c[0].metric("Mulheres (total)", f"{int(d['mulheres'].sum()):,}".replace(",", "."))
    c[1].metric("% na população", f"{pct_pop:.2f}%".replace(".", ","))
    c[2].metric("Mediana % municipal", f"{r['mediana']:.2f}%".replace(".", ","))
    c[3].metric("Desvio padrão", f"{r['desvio padrão']:.2f} p.p.".replace(".", ","))
    c[4].metric("Outliers (municípios)", r["nº outliers"])

    g1, g2 = st.columns(2)
    with g1:
        fig = px.histogram(d, x="pct_mulheres", nbins=40, title="Distribuição do % de mulheres por município",
                           labels={"pct_mulheres": "% de mulheres"})
        fig.add_vline(x=r["média"], line_dash="dash", annotation_text="média")
        fig.add_vline(x=r["mediana"], line_dash="dot", annotation_text="mediana", annotation_position="bottom")
        st.plotly_chart(fig, use_container_width=True)
    with g2:
        fig = px.box(d, x="regiao", y="pct_mulheres", points="outliers", title="Boxplot por região",
                     labels={"pct_mulheres": "% de mulheres", "regiao": ""})
        st.plotly_chart(fig, use_container_width=True)

    por_uf = d.groupby("uf")[["mulheres", "total"]].sum()
    por_uf["pct"] = 100 * por_uf["mulheres"] / por_uf["total"]
    por_uf = por_uf.sort_values("pct", ascending=False).reset_index()
    fig = px.bar(por_uf, x="uf", y="pct", title="% de mulheres por UF",
                 labels={"pct": "% de mulheres", "uf": "UF"})
    fig.update_yaxes(range=[por_uf["pct"].min() - 1, por_uf["pct"].max() + 0.5])
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("Medidas estatísticas (por município)"):
        st.dataframe(u.tabela_resumo(s, 2), hide_index=True)
        out, lo, hi = u.outliers(s)
        st.write(f"Outliers: valores fora de [{lo:.2f}% ; {hi:.2f}%] — "
                 f"{len(out)} de {len(s)} municípios.")
        st.dataframe(d.loc[out.index, ["municipio", "pct_mulheres", "total"]]
                     .sort_values("pct_mulheres"), hide_index=True)

    st.subheader("Interpretação")
    dif = r["média"] - r["mediana"]
    st.markdown(
        f"- Em média, **{r['média']:.2f}%** dos moradores dos municípios selecionados são mulheres "
        f"(mediana {r['mediana']:.2f}%; diferença de {abs(dif):.2f} p.p., ou seja, poucos outliers afetam a média).\n"
        f"- A dispersão é **baixa** (desvio padrão {r['desvio padrão']:.2f} p.p., IQR {r['IQR']:.2f} p.p., "
        f"amplitude {r['amplitude']:.2f} p.p.): a composição por sexo é parecida entre os municípios.\n"
        f"- Outliers costumam ser municípios pequenos ou com características específicas "
        f"(presídios, garimpos, obras, bases militares, forte migração masculina), onde a proporção foge do padrão.\n"
        f"- Razão de sexos mediana: **{d['razao_sexos'].median():.1f}** homens por 100 mulheres."
    )

    u.mostra_noticias("mulheres Censo 2022 IBGE população feminina")


if __name__ == "__main__":
    st.set_page_config(page_title="Mulheres", layout="wide")
    render()
