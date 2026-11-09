Dashboard IBGE - Mulheres e Rendimento dos Responsáveis
pip install -r requirements.txt
streamlit run app.py
ibge_utils.py: SIDRA, estatísticas (média, mediana, moda, quartis, IQR, amplitude, desvio, outliers), notícias.
mulheres.py / rendimento.py: cada um expõe render() para integrar no painel do grupo.
Rodar um módulo sozinho: streamlit run mulheres.py
