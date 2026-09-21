# Guia de Uso: RuFaS Brasil (Hemisfério Sul e Regionalização)

Este guia documenta as extensões e parâmetros introduzidos no **RuFaS Brasil (Passo 1)** para viabilizar a simulação fidedigna de sistemas de produção de leite no Brasil e em outras regiões do Hemisfério Sul.

---

## 1. Visão Geral

O modelo original do RuFaS foi desenvolvido sob premissas acopladas aos Estados Unidos e ao Hemisfério Norte. O **Passo 1** introduz duas generalizações fundamentais:

1. **Latitude com Sinal (`latitude`)**: Permite valores negativos para o Hemisfério Sul (ex: $-22{,}5^\circ$ para a Zona da Mata Mineira), garantindo que o fotoperíodo astronômico (horas de luz diárias) e a sazonalidade climática reflitam o verão em dezembro–fevereiro e o inverno em junho–agosto.
2. **Modularização de País e Região (`country` e `region_code`)**: Permite identificar o país via código ISO de 3 letras (`"BRA"`) e a localidade administrativa usando os códigos oficiais do IBGE (2 dígitos para UF ou 7 dígitos para municípios), mantendo 100% de compatibilidade retroativa com os códigos FIPS dos EUA (`"USA"`).

---

## 2. Configuração de Latitude no Hemisfério Sul

### 2.1 Esquema de Entrada

No arquivo de configuração de talhões/campos (bloco referenciado por `crop_configurations` nos metadados do cenário), utilize a chave `latitude` com o sinal negativo para o Hemisfério Sul:

```json
{
  "field_properties": {
    "name": "talhao_piquete_1",
    "field_size": 15.0,
    "latitude": -22.53,
    "longitude": -43.28,
    "minimum_daylength": 10.7,
    "seasonal_high_water_table": false,
    "watering_amount_in_liters": 0.0,
    "watering_interval": 0,
    "simulate_water_stress": true,
    "simulate_temp_stress": true,
    "simulate_nitrogen_stress": true,
    "simulate_phosphorus_stress": true
  }
}
```

### 2.2 Diferença entre `latitude` e `absolute_latitude`

| Parâmetro | Tipo | Unidade | Faixa | Descrição |
|---|---|---|---|---|
| `latitude` | `number` | graus ($^\circ$) | $-90{,}0$ a $+90{,}0$ | **Recomendado.** Latitude geográfica com sinal. Valores negativos indicam o Hemisfério Sul. |
| `absolute_latitude` | `number` | graus ($^\circ$) | $0{,}0$ a $90{,}0$ | **Legado.** Latitude positiva absoluta. Mantido para compatibilidade com cenários norte-americanos antigos. |

> [!NOTE]
> O RuFaS sincroniza os dois parâmetros automaticamente em runtime:
> - Se apenas `latitude` for fornecido (ex: `-22.5`), o motor calcula internamente `absolute_latitude = 22.5` para rotinas que requerem valor absoluto (como limiares de dormência de plantas).
> - Se apenas `absolute_latitude` for fornecido (cenários legados), `latitude` recebe o mesmo valor positivo.

### 2.3 Efeito no Fotoperíodo e Crescimento de Culturas

Ao definir latitude negativa, o cálculo de declinação solar astronômica ajusta automaticamente o comprimento do dia:
- **Solstício de Verão (Dezembro / Dia Juliano ~355)**: Dias mais longos (> 13,5 horas de luz).
- **Solstício de Inverno (Junho / Dia Juliano ~172)**: Dias mais curtos (< 11,0 horas de luz).

Isso impede a inversão sazonal que anteriormente provocava estresse fenológico e parada vegetativa em culturas tropicais no meio do verão brasileiro.

---

## 3. Identificação Regional e Administrativa (`country` e `region_code`)

### 3.1 Esquema de Entrada

No arquivo de configuração geral da simulação (`config_properties` no metadados do cenário), configure o país e o código regional:

```json
{
  "config_properties": {
    "simulation_type": "full_farm",
    "nutrient_standard": "NASEM",
    "start_date": "2024:1",
    "end_date": "2024:365",
    "country": "BRA",
    "region_code": 3120508
  }
}
```

### 3.2 Tabela de Parâmetros

| Parâmetro | Tipo | Padrão | Exemplo | Descrição |
|---|---|---|---|---|
| `country` | `string` | `"USA"` | `"BRA"` | Código ISO 3166-1 alpha-3 de 3 letras maiúsculas. |
| `region_code` | `number` | `None` | `31` ou `3120508` | Código regional administrativo. Para o Brasil, use os códigos do IBGE. Para os EUA, use o FIPS de 5 dígitos. |
| `FIPS_county_code` | `number` | `None` | `55025` | **Legado.** Código FIPS de condado americano. Se `region_code` não for informado, o RuFaS usará este valor como fallback. |

### 3.3 Códigos IBGE Suportados para o Brasil

O RuFaS Brasil aceita:
1. **Códigos de Município do IBGE (7 dígitos)**: Exemplo: `3120508` (Coronel Pacheco / MG - sede da Embrapa Gado de Leite). O modelo extrai automaticamente os 2 primeiros dígitos (`31`) para identificar o estado.
2. **Códigos de Unidade Federativa do IBGE (2 dígitos)**:
   - `31`: Minas Gerais
   - `35`: São Paulo
   - `41`: Paraná
   - `42`: Santa Catarina
   - `43`: Rio Grande do Sul
   - `52`: Goiás / DF

---

## 4. Integração com os Módulos do RuFaS

### 4.1 Curva de Lactação de Wood ([`lactation_curve.py`](../RUFAS/biophysical/animal/milk/lactation_curve.py))
- Quando `country == "BRA"`, o RuFaS mapeia o código do estado (IBGE) para a macrorregião correspondente do arquivo de lactação.
- Se a região específica não estiver mapeada ou não houver dados regionais customizados, o modelo aplica com segurança os **ajustes aditivos neutros**:
  $$\Delta l = 0{,}0, \quad \Delta m = 0{,}0, \quad \Delta n = 0{,}0$$
  Isso preserva rigorosamente a forma canônica da curva de lactação configurada para o rebanho, sem distorções acidentais.

### 4.2 Emissões de Alimentos Comprados ([`emissions.py`](../RUFAS/EEE/emissions.py))
- O módulo de economia e ciclo de vida (EEE) busca os fatores de emissão de alimentos comerciais na tabela de emissões indexada por `region_code` (ou `county_code` para bases legadas).
- Se `region_code` não for explicitamente configurado, o RuFaS realiza fallback automático para o código legado `FIPS_county_code`.
- A detecção da coluna identificadora (`region_code` ou `county_code`) na tabela de fatores é dinâmica, garantindo total interoperabilidade entre novos conjuntos de dados nacionais e tabelas legadas.
- Alimentos sem fatores regionais identificados emitem avisos informativos (`warnings`) via `OutputManager` e são omitidos com segurança das estimativas, sem provocar interrupção precoce da simulação.

---

## 5. Exemplo de Execução

1. **Ativar o Ambiente Virtual:**
   ```bash
   cd /caminho/para/o/RuFaS
   source venv/bin/activate
   ```

2. **Habilitar a Exportação de Variáveis:**
   Verifique se o filtro de variáveis está ativo em `output/output_filters/`:
   ```bash
   # Certifique-se de que o arquivo csv_all_variables.txt não possui o sublinhado inicial:
   ls output/output_filters/csv_all_variables.txt
   ```

3. **Executar a Simulação:**
   ```bash
   # Execute apontando para o arquivo de metadados do seu cenário:
   python main.py --path-to-metadata input/metadata/cenario_brasil_metadata.json
   ```

4. **Verificar os Resultados:**
   - Variáveis diárias exportadas: `output/csv_variables_pool.csv` (ou arquivos particionados por módulo).
   - Diagnósticos e logs: `output/logs/logs.txt` e `output/logs/errors.txt`.

---

## 6. Produção Própria de Forragem e Rotação de Culturas (Minas Gerais)

### 6.1 Realidade da Pecuária Leiteira Tropical
Em fazendas leiteiras tecnificadas no Brasil (e especialmente em bacias como o Alto Paranaíba e Triângulo Mineiro), a produção própria de volumoso é um pilar econômico e operacional indispensável. A silagem de milho constitui a principal fonte de energia forrageira da dieta, sendo produzida nas áreas de lavoura da própria propriedade e armazenada em silos trincheira (bunker).

### 6.2 Calendário Agrícola e Sazonalidade do Cerrado
O calendário de cultivo ([`crop_schedule_minas_gerais.json`](../input/data/crop/crop_schedule_minas_gerais.json)) é projetado para explorar o período chuvoso do Cerrado (outubro a abril, precipitação acumulada > 1.200 mm):

| Safra / Ciclo | Janela de Plantio | Janela de Colheita | Duração | Ponto de Corte e Operação |
|---|---|---|---|---|
| **Safra de Verão** | 1º de Novembro (Dia 305) | 24 de Fevereiro (Dia 55) | ~115 dias | Grão farináceo-duro (32–35% MS), `harvest_kill` |
| **Ciclo 1 / Janela Inicial** | 15 de Janeiro (Dia 15) | 25 de Abril (Dia 115) | ~100 dias | Ponto de silagem (35% MS), `harvest_kill` |

- **Produtividade Observada**: Entre 11,4 e 15,0 t MS/ha (33 a 43 t MV/ha), coerente com híbridos de milho adaptados para silagem em Latossolo Vermelho sob boa adubação.
- **Repetição Multianual**: O padrão utiliza `"pattern_repeat": 1` com `"planting_skip": 0`, assegurando que o milho seja semeado e colhido anualmente de forma contínua em simulações plurianuais.

### 6.3 Armazenamento em Silo Bunker e Dieta do Rebanho
- **Identificador no RuFaS**: A silagem de milho produzida internamente no campo `field_1` é recebida no silo trincheira `corn_silage_storage_1` sob o **Feed ID 51** (`"Corn silage, mid maturity"`).
- **Alocação na Dieta ([`feed_minas_gerais.json`](../input/data/feed/feed_minas_gerais.json))**: As rações para novilhas, vacas secas e vacas em lactação utilizam `feed_type: 51`. O [`FeedManager`](../RUFAS/biophysical/feed_storage/feed_manager.py) atende a demanda diária (~715 kg MS/dia) priorizando o estoque do silo da fazenda, recorrendo a compras comerciais apenas como reserva de contingência.
- **Conservação e Perdas**: O modelo simula perdas de fermentação e gases (~2,3% da MS), mantendo a qualidade de amido (33%), proteína bruta (7,7%) e FDN (41%).

### 6.4 Sincronização da Aplicação de Dejetos ([`manure_schedule_minas_gerais.json`](../input/data/manure_schedule/manure_schedule_minas_gerais.json))
A fertirrigação / distribuição de esterco líquido é posicionada estrategicamente nas janelas pré-plantio (dias 10 e 300), garantindo:
1. **Aproveitamento Agronômico de Nutrientes**: O nitrogênio, fósforo e potássio orgânicos e amoniacais são disponibilizados no momento de maior exigência inicial da cultura.
2. **Eliminação de Deficiências**: O parâmetro `"supplement_manure_nutrient_deficiencies": "synthetic fertilizer and manure"` complementa automaticamente qualquer déficit com adubo mineral, evitando alertas de carência nutricional.
3. **Mitigação Ambiental**: Evita a aplicação de dejetos em solo descoberto durante a entressafra seca, mitigando perdas por lixiviação de nitratos e emissões desnecessárias de $\text{N}_2\text{O}$.


