"""Funções compartilhadas pelos módulos Mulheres e Rendimento dos Responsáveis."""
import xml.etree.ElementTree as ET
from urllib.parse import quote

import numpy as np
import pandas as pd
import requests
import streamlit as st

SIDRA_URL = "https://apisidra.ibge.gov.br/values"

REGIOES = {
    "Norte": ["AC", "AP", "AM", "PA", "RO", "RR", "TO"],
    "Nordeste": ["AL", "BA", "CE", "MA", "PB", "PE", "PI", "RN", "SE"],
    "Sudeste": ["ES", "MG", "RJ", "SP"],
    "Sul": ["PR", "RS", "SC"],
    "Centro-Oeste": ["DF", "GO", "MT", "MS"],
}
UF_REGIAO = {uf: r for r, ufs in REGIOES.items() for uf in ufs}


# ----------------------------------------------------------------- coleta
@st.cache_data(ttl=3600, show_spinner="Consultando a API do SIDRA...")
def sidra(caminho: str) -> pd.DataFrame:
    """Consulta a API do SIDRA. `caminho` é tudo que vem depois de /values,
    ex.: '/t/9514/n6/all/v/93/p/2022/c2/4,5'.
    A 1ª linha do JSON é o cabeçalho; ela vira o nome das colunas."""
    r = requests.get(SIDRA_URL + caminho, timeout=90)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)
    df["Valor"] = pd.to_numeric(df["Valor"], errors="coerce")  # '-', '...', 'X' viram NaN
    return df


def extrai_uf(nome_local: pd.Series) -> pd.Series:
    """'Belo Horizonte - MG' -> 'MG'."""
    return nome_local.str.extract(r"-\s*([A-Z]{2})\s*$")[0]


# ------------------------------------------------------------ estatísticas
def outliers(s: pd.Series):
    """Regra de Tukey: fora de [Q1 - 1,5·IQR ; Q3 + 1,5·IQR]."""
    s = s.dropna()
    q1, q3 = s.quantile([0.25, 0.75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return s[(s < lo) | (s > hi)], lo, hi


def resumo(s: pd.Series, casas: int = 1) -> dict:
    """Medidas de tendência central e de dispersão.
    A moda de variável contínua é calculada após arredondar para `casas`."""
    s = pd.Series(s).dropna().astype(float)
    q1, med, q3 = s.quantile([0.25, 0.5, 0.75])
    out, lo, hi = outliers(s)
    moda = s.round(casas).mode()
    return {
        "n": int(len(s)),
        "média": s.mean(),
        "mediana": med,
        "moda": moda.iloc[0] if len(moda) else np.nan,
        "mínimo": s.min(),
        "Q1": q1,
        "Q3": q3,
        "máximo": s.max(),
        "IQR": q3 - q1,
        "amplitude": s.max() - s.min(),
        "desvio padrão": s.std(),
        "coef. variação (%)": 100 * s.std() / s.mean() if s.mean() else np.nan,
        "limite inferior": lo,
        "limite superior": hi,
        "nº outliers": int(len(out)),
    }


def tabela_resumo(s: pd.Series, casas: int = 1) -> pd.DataFrame:
    r = resumo(s, casas)
    return pd.DataFrame({"medida": r.keys(), "valor": r.values()})


# ---------------------------------------------------------------- notícias
@st.cache_data(ttl=1800, show_spinner=False)
def noticias(consulta: str, n: int = 6):
    """Notícias do tema via RSS do Google Notícias (sem chave de API)."""
    url = f"https://news.google.com/rss/search?q={quote(consulta)}&hl=pt-BR&gl=BR&ceid=BR:pt-419"
    try:
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        itens = ET.fromstring(r.content).findall("./channel/item")[:n]
        return [
            {
                "titulo": i.findtext("title"),
                "link": i.findtext("link"),
                "data": i.findtext("pubDate"),
                "fonte": i.findtext("source") or "",
            }
            for i in itens
        ]
    except Exception:
        return []


def mostra_noticias(consulta: str, n: int = 6):
    st.subheader("Notícias do tema")
    itens = noticias(consulta, n)
    if not itens:
        st.info("Não foi possível carregar as notícias agora.")
        return
    for i in itens:
        st.markdown(f"- [{i['titulo']}]({i['link']})  \n  <small>{i['fonte']} · {i['data']}</small>",
                    unsafe_allow_html=True)
