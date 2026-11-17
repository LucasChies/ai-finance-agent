# Decisões de projeto

## Regras determinísticas, LLM só para explicar
Cálculos de anomalia ficam em código Python testável. O modelo do Azure AI Foundry chama a ferramenta `run_anomaly_rules` e explica o resultado. Motivo: LLMs erram aritmética e não dão resultados reproduzíveis. Assim, os alertas são os mesmos a cada execução, e o modelo só adiciona linguagem.

## Z-score robusto por estabelecimento
Usa mediana e MAD em vez de média e desvio padrão. Motivo: valores extremos distorcem a média e o desvio, o que esconde outros outliers. A comparação é feita por estabelecimento, porque um gasto alto em posto de gasolina não é anômalo para uma loja online.

## Janela centrada para rajadas
A regra de velocidade conta, para cada transação, quantas da mesma conta caem em uma janela de 10 minutos centrada nela. Motivo: uma contagem acumulada só marcaria as transações depois de atingir o limite, e deixaria passar as primeiras da rajada. O teste `test_planted_anomalies_are_detected` cobre esse caso.

## Duplicidade no mesmo dia
Marca apenas a segunda ocorrência em diante. Motivo: a original é a transação legítima; marcar as duas geraria ruído na revisão.

## Dados sintéticos
O projeto usa apenas dados gerados em `data/generate_sample.py`, com anomalias plantadas. Nenhum dado real de cliente ou banco entra no repositório.

## Limitações
- As regras são heurísticas. Não substituem modelos treinados com dados rotulados de fraude.
- Os limites (6 de z-score, 5 transações em 10 minutos) são escolhidos para o exemplo e precisam de calibração com dados reais.
- A integração com o Azure AI Foundry usa o cliente `AzureOpenAI` e não foi testada contra uma implantação real neste repositório. Confira a versão da API e o nome da implantação.
