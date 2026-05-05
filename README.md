# Supervisório Atuador Pneumático

Interface de supervisão e controle em tempo real para um atuador pneumático linear, com comunicação serial com Arduino via protocolo serial customizado e controle PID ajustável em tempo real.

---

## Visão Geral

O sistema é dividido em dois componentes principais:

- **`supervisory.py`** - Interface desktop em Python (PySide6) que envia parâmetros de controle ao Arduino e recebe a posição do sensor em tempo real, plotando os dados e permitindo exportação.
- **`arduinoCode.ino`** - Firmware do Arduino responsável por receber os parâmetros via serial, executar a rotina de controle PID e retornar a posição do sensor.

---

## Funcionalidades

### Interface (Python)
- Conexão com porta COM configurável pela interface - sem necessidade de editar código
- Envio de **setpoint** e **ganhos PID** (Kp, Ki, Kd) ao Arduino em tempo real
- Visualizador linear de posição atual vs. setpoint
- Gráfico histórico com **janela deslizante** de 10 segundos (ativável/desativável)
- Leitura contínua a 20 Hz com buffer serial drenado a cada ciclo
- Exportação dos dados da sessão em **CSV** (`time_s`, `position_cm`, `setpoint_cm`, `error_cm`)
- Indicador de status de conexão na sidebar

### Firmware (Arduino)
- Comunicação serial a **9600 baud**
- Recebe pacotes no formato: `SP:<valor>;P:<kp>;I:<ki>;D:<kd>`
- Envia posição atual via `Serial.println()` a cada ciclo do loop
- LED embutido (pino 13) pisca 3× ao receber um pacote válido (debug)

---

## Protocolo Serial

| Direção | Formato | Exemplo |
|---|---|---|
| PC → Arduino | `SP:<float>;P:<float>;I:<float>;D:<float>\n` | `SP:12.5;P:12.5;I:0.85;D:2.1` |
| Arduino → PC | `<float>\n` | `12.501` |

---

## Instalação

### Pré-requisitos
- Python 3.9+
- Arduino IDE (para upload do firmware)

### 1. Clonar o repositório

```bash
git clone <url-do-repositorio>
cd <nome-do-repositorio>
```

### 2. Instalar dependências Python

```bash
pip install -r requirements.txt
```

### 3. Upload do firmware

Abra `arduinoCode/arduinoCode.ino` na Arduino IDE, selecione a placa e porta corretas, e faça o upload.

### 4. Executar a interface

```bash
python supervisory.py
```

---

## Uso

1. Abra a aba **Configurações**
2. Clique em **Atualizar Lista** para escanear as portas COM disponíveis
3. Selecione a porta do Arduino e clique em **Conectar**
4. Volte à aba **Supervisório** e clique em **INICIAR LEITURA**
5. Ajuste o **Setpoint** e os **Ganhos PID** conforme necessário
6. Ao finalizar, clique em **PARAR LEITURA** e depois em **Exportar Run (.CSV)** para salvar os dados

---

## Estrutura do Projeto

```
.
├── arduinoCode/
│   └── arduinoCode.ino   # Firmware do Arduino
├── supervisory.py        # Interface de supervisão (PySide6)
├── requirements.txt      # Dependências Python
├── data_test.csv         # Exemplo de exportação CSV
└── README.md
```

---

## Dependências

Veja `requirements.txt` para a lista completa. Principais bibliotecas:

| Biblioteca | Uso |
|---|---|
| `PySide6` | Interface gráfica (Qt6) |
| `pyqtgraph` | Gráficos em tempo real |
| `pyserial` | Comunicação serial com o Arduino |
| `numpy` | Operações numéricas auxiliares |

---

## Observações

- O firmware contém a linha `sensorPosition += 0.001;` no `loop()` apenas para fins de teste. **Substitua pelo código real de leitura do sensor antes de usar em produção.**
- A interface aguarda até 5 segundos pela mensagem `"System ready."` do Arduino ao conectar. Se o timeout for atingido, a conexão é assumida como bem-sucedida mesmo assim.
- O buffer serial é drenado a cada ciclo de leitura para evitar acúmulo de pacotes antigos.