# Guida Dettagliata a Garmin Planner

Garmin Planner è un'applicazione versatile progettata per gestire, creare e pianificare allenamenti su Garmin Connect. Questa guida ti aiuterà a comprendere tutte le funzionalità dell'applicazione e come utilizzarle efficacemente.

## Indice
- [Introduzione](#introduzione)
- [Installazione](#installazione)
- [Interfaccia Principale](#interfaccia-principale)
- [Login a Garmin Connect](#login-a-garmin-connect)
- [Importazione Allenamenti](#importazione-allenamenti)
- [Esportazione Allenamenti](#esportazione-allenamenti)
- [Pianificazione](#pianificazione)
  - [Flusso Guidato di Pianificazione](#flusso-guidato-di-pianificazione)
  - [Creazione del Piano di Allenamento](#creazione-del-piano-di-allenamento)
  - [Conversione Excel a YAML](#conversione-excel-a-yaml)
  - [Pianificazione nel Calendario](#pianificazione-nel-calendario)
- [Editor di Allenamenti](#editor-di-allenamenti)
  - [Creare un Nuovo Allenamento](#creare-un-nuovo-allenamento)
  - [Tipi di Passi](#tipi-di-passi)
  - [Gestione delle Ripetizioni](#gestione-delle-ripetizioni)
  - [Configurazione delle Zone](#configurazione-delle-zone)
- [Funzionalità Avanzate](#funzionalità-avanzate)
  - [Modifica delle Date](#modifica-delle-date)
- [Risoluzione dei Problemi](#risoluzione-dei-problemi)

## Introduzione

Garmin Planner è un'applicazione che ti consente di:
- Importare ed esportare allenamenti da/verso Garmin Connect
- Creare piani di allenamento completi
- Pianificare gli allenamenti nel calendario di Garmin Connect
- Creare e modificare allenamenti con un editor visuale intuitivo
- Convertire piani di allenamento da Excel a YAML

L'applicazione è disponibile in diverse versioni:
- **Basic**: Funzionalità di importazione/esportazione
- **Pro**: Aggiunge funzionalità di pianificazione di base ed Excel
- **Premium**: Aggiunge funzionalità di conversione Excel a YAML e editor di allenamenti

## Installazione

L'applicazione Garmin Planner è disponibile come applicazione desktop. Per installarla:

1. Scarica l'installer appropriato per il tuo sistema operativo (Windows, macOS, Linux)
2. Esegui l'installer e segui le istruzioni a schermo
3. Al primo avvio, ti verrà richiesto di impostare la cartella per i token OAuth di Garmin Connect

Una volta installata, l'applicazione creerà automaticamente le cartelle necessarie per il funzionamento:
- `oauth`: Contiene i token di autenticazione per Garmin Connect
- `training_plans`: Contiene i piani di allenamento
- `cache`: Contiene la cache degli allenamenti di Garmin Connect
- `exported`: Directory predefinita per i file esportati
- `excel`: Directory predefinita per i file Excel

## Interfaccia Principale

Garmin Planner presenta un'interfaccia grafica con diverse schede (tab):

1. **Login**: Per accedere al tuo account Garmin Connect
2. **Importa**: Per importare allenamenti da file YAML
3. **Esporta**: Per esportare allenamenti da Garmin Connect
4. **Pianificazione**: Per creare e pianificare allenamenti 
5. **Editor Allenamenti**: Per creare e modificare allenamenti
6. **Log**: Visualizza i log delle operazioni
7. **Info**: Informazioni sull'applicazione e sulla licenza

## Login a Garmin Connect

Prima di utilizzare la maggior parte delle funzionalità, è necessario effettuare il login a Garmin Connect:

1. Vai alla scheda **Login**
2. Se non hai già effettuato l'accesso, clicca sul pulsante "Effettua login"
3. Inserisci le tue credenziali Garmin Connect (email e password)
4. Le credenziali verranno salvate in modo sicuro nella cartella OAuth specificata
5. Una volta effettuato l'accesso, vedrai uno stato "✅ Hai già effettuato l'accesso a Garmin Connect"

> **Nota**: Non è necessario effettuare nuovamente l'accesso ad ogni avvio dell'applicazione.

Per verificare la connessione in qualsiasi momento, puoi cliccare su "Verifica connessione".

## Importazione Allenamenti

La scheda **Importa** ti permette di importare allenamenti da file YAML a Garmin Connect:

1. Clicca su "Sfoglia" per selezionare un file YAML contenente definizioni di allenamenti
2. Opzionalmente, seleziona "Sostituisci allenamenti esistenti" se vuoi sovrascrivere allenamenti con lo stesso nome
3. Clicca su "Importa" per iniziare il processo di importazione

Nella parte inferiore della scheda, puoi visualizzare i piani di allenamento disponibili. Puoi:
- Cliccare su "Aggiorna lista" per ricaricare i piani
- Fare doppio clic su un piano per selezionarlo e visualizzarne i dettagli

### Struttura dei File YAML

I file YAML per Garmin Planner seguono una struttura specifica:

```yaml
config:
  name_prefix: "MYRUN_"
  paces:
    Z1: "6:30"
    Z2: "6:00"
    Z3: "5:30"
    Z4: "5:00"
    Z5: "4:30"
    race_pace: "5:10"
    threshold: "5:20-5:10"
  heart_rates:
    max_hr: 180
    Z1_HR: "62-76% max_hr"
    Z2_HR: "76-85% max_hr"
    Z3_HR: "85-91% max_hr"
    Z4_HR: "91-95% max_hr"
    Z5_HR: "95-100% max_hr"
  margins:
    faster: "0:03"
    slower: "0:03"
    hr_up: 5
    hr_down: 5

"W01S01 Easy Run": # Descrizione come commento
  - warmup: "10min @ Z1_HR"
  - interval: "30min @ Z2"
  - cooldown: "5min @ Z1_HR"

"W01S02 Interval Training":
  - warmup: "15min @ Z1_HR"
  - repeat: 5
    steps:
      - interval: "400m @ Z5"
      - recovery: "2min @ Z1_HR"
  - cooldown: "10min @ Z1_HR"
```

La sezione `config` contiene:
- `name_prefix`: Prefisso aggiunto ai nomi degli allenamenti
- `paces`: Definizione delle zone di ritmo
- `heart_rates`: Definizione delle zone di frequenza cardiaca
- `margins`: Margini di tolleranza per ritmi e frequenze cardiache

Ciascun allenamento è rappresentato da un nome (es. "W01S01 Easy Run") seguito da una lista di passi.

## Esportazione Allenamenti

La scheda **Esporta** ti permette di esportare allenamenti da Garmin Connect a file YAML o JSON:

1. Clicca su "Sfoglia" per selezionare la posizione e il nome del file di esportazione
2. Seleziona "Pulisci dati" per rimuovere informazioni non necessarie
3. Nella lista degli allenamenti, seleziona quelli che vuoi esportare
4. Clicca su "Esporta Selezionati" per salvare gli allenamenti selezionati

Puoi anche eliminare allenamenti selezionandoli dalla lista e cliccando su "Elimina Selezionati".

Per aggiornare la lista degli allenamenti disponibili su Garmin Connect, clicca su "Aggiorna lista".

## Pianificazione

### Flusso Guidato di Pianificazione

La scheda **Pianificazione** offre un flusso guidato a 4 step per la creazione e pianificazione di allenamenti:

#### Step 1: Pianificazione Allenamenti
- Inserisci i dati dell'atleta e la data della gara
- Seleziona i giorni preferiti per gli allenamenti
- Crea un template Excel del piano o carica un file YAML/Excel esistente

#### Step 2: Conversione Excel a YAML
- Converti il file Excel in un file YAML compatibile con Garmin Connect

#### Step 3: Informazioni Piano
- Visualizza le informazioni dettagliate sul piano creato
- Analizza il numero di settimane e allenamenti

#### Step 4: Pianificazione Calendario
- Simula la pianificazione per verificare come saranno distribuiti gli allenamenti
- Pianifica gli allenamenti nel calendario di Garmin Connect
- Rimuovi una pianificazione esistente se necessario

### Creazione del Piano di Allenamento

Per creare un nuovo piano di allenamento:

1. Nello Step 1, compila i seguenti campi:
   - Nome dell'atleta
   - Giorno della gara
   - Seleziona i giorni preferiti per gli allenamenti (es. Lunedì, Mercoledì, Venerdì)
2. Clicca su "Crea Template Piano" per generare un file Excel

Questo creerà un file Excel con la seguente struttura:
- Foglio **Config**: Contiene parametri generali come prefisso del nome e margini
- Foglio **Paces**: Definizione delle zone di ritmo
- Foglio **HeartRates**: Definizione delle zone di frequenza cardiaca
- Foglio **Workouts**: Gli allenamenti veri e propri
- Fogli **Examples** e **Advanced Examples**: Esempi di sintassi per la definizione degli allenamenti

#### Esempi Pratici di Compilazione del Foglio Excel

##### Foglio Config

Il foglio Config contiene i parametri generali del piano:

| Parameter   | Value     | Slower    | HR Up | HR Down |
|-------------|-----------|-----------|-------|---------|
| name_prefix | MYRUN_XYZ |           |       |         |
| margins     | 0:03      | 0:03      | 5     | 5       |
| race_day    | 2023-09-30|           |       |         |

- **name_prefix**: Definisce un prefisso che sarà aggiunto a tutti i nomi degli allenamenti
- **margins**: Definisce i margini di tolleranza per ritmi e frequenze cardiache
- **race_day**: La data della gara nel formato YYYY-MM-DD

##### Foglio Paces

Il foglio Paces definisce le zone di ritmo:

| Name        | Value     |
|-------------|-----------|
| Z1          | 6:30      |
| Z2          | 6:00      |
| Z3          | 5:30      |
| Z4          | 5:00      |
| Z5          | 4:30      |
| race_pace   | 5:10      |
| threshold   | 5:20-5:10 |
| marathon    | 5:30      |
| 10k         | 21:00     |

Le zone possono essere definite in diversi formati:
- Ritmo in min/km: `5:30`
- Intervallo di ritmi: `5:20-5:10`
- Tempo per una distanza: `10km in 45:00`
- Ritmo derivato: `110% marathon`

##### Foglio HeartRates

Il foglio HeartRates definisce le zone di frequenza cardiaca:

| Name        | Value        |
|-------------|--------------|
| max_hr      | 180          |
| Z1_HR       | 62-76% max_hr|
| Z2_HR       | 76-85% max_hr|
| Z3_HR       | 85-91% max_hr|
| Z4_HR       | 91-95% max_hr|
| Z5_HR       | 95-100% max_hr|
| recovery_HR | 120-130      |

Le zone possono essere definite in diversi formati:
- Valore fisso: `180`
- Intervallo diretto: `120-130`
- Percentuale di un'altra zona: `62-76% max_hr`

##### Foglio Workouts

Il foglio Workouts contiene gli allenamenti veri e propri:

| Week | Date       | Session | Description      | Steps                                                          |
|------|------------|---------|------------------|----------------------------------------------------------------|
| 1    | 2023-08-01 | 1       | Easy Run         | warmup: 10min @ Z1_HR\ninterval: 30min @ Z2\ncooldown: 5min @ Z1_HR |
| 1    | 2023-08-03 | 2       | Intervals        | warmup: 15min @ Z1_HR\nrepeat 5:\n  interval: 400m @ Z5\n  recovery: 2min @ Z1_HR\ncooldown: 10min @ Z1_HR |
| 1    | 2023-08-05 | 3       | Long Run         | warmup: 10min @ Z1_HR\ninterval: 60min @ Z2\ncooldown: 5min @ Z1_HR |
| 2    | 2023-08-08 | 1       | Recovery Run     | interval: 30min @ Z1_HR |
| 2    | 2023-08-10 | 2       | Tempo Run        | warmup: 15min @ Z1_HR\ninterval: 20min @ Z4\ncooldown: 10min @ Z1_HR |

Struttura della colonna Steps:
- Ogni passo è definito in una nuova riga usando la sintassi `tipo: durata @ zona`
- Per le ripetizioni, usa `repeat n:` seguito dai passi indentati con 2 spazi
- Puoi aggiungere descrizioni ai passi usando `-- descrizione`

**Esempio di syntax completo per la colonna Steps:**

```
warmup: 10min @ Z1_HR -- Riscaldamento iniziale
interval: 30min @ Z2 -- Mantieni ritmo costante
cooldown: 5min @ Z1_HR -- Rallenta gradualmente
```

**Esempio con ripetizioni:**

```
warmup: 15min @ Z1_HR
repeat 5:
  interval: 400m @ Z5 -- Veloce!
  recovery: 2min @ Z1_HR -- Recupero completo
cooldown: 10min @ Z1_HR
```

**Esempio con passi di vario tipo:**

```
warmup: 2km @ Z1_HR
interval: 5km @ Z3
rest: lap-button @ Z1_HR -- Premi lap quando sei pronto
repeat 3:
  interval: 1km @ threshold
  recovery: 3min @ Z1_HR
cooldown: 1km @ Z1_HR
```

### Conversione Excel a YAML

Una volta creato o modificato il piano in Excel, converti il file in formato YAML:

1. Nello Step 2, verifica che il file Excel sia correttamente selezionato
2. Se necessario, modifica il percorso del file YAML di output
3. Clicca su "Converti Excel → YAML"

La conversione trasformerà la struttura Excel in un file YAML compatibile con Garmin Connect e con la struttura necessaria per Garmin Planner.

### Pianificazione nel Calendario

Dopo aver convertito il piano in YAML, puoi pianificare gli allenamenti nel calendario di Garmin Connect:

1. Nello Step 4, puoi:
   - Cliccare su "Simula Pianificazione" per vedere come saranno distribuiti gli allenamenti senza apportare modifiche
   - Cliccare su "Pianifica Allenamenti" per inserire gli allenamenti nel calendario di Garmin Connect
   - Cliccare su "Rimuovi Pianificazione" per eliminare allenamenti precedentemente pianificati

La pianificazione distribuirà gli allenamenti nei giorni selezionati, tenendo conto della data della gara e assicurandosi che:
- Nessun allenamento coincida con il giorno della gara
- Nessun allenamento sia pianificato nel passato
- Nessun allenamento sia pianificato dopo la data della gara

## Editor di Allenamenti

La scheda **Editor Allenamenti** permette di creare e modificare allenamenti con un'interfaccia visuale intuitiva.

### Creare un Nuovo Allenamento

Per creare un nuovo allenamento:

1. Clicca su "Nuovo allenamento"
2. Inserisci un nome per l'allenamento (formato consigliato: "W01S01 Descrizione")
3. Aggiungi passi all'allenamento utilizzando i pulsanti "Aggiungi passo" e "Aggiungi ripetizione"
4. Configura ciascun passo con tipo, durata/distanza e zona di intensità
5. Al termine, clicca su "Salva"

L'editor mostra una visualizzazione grafica dell'allenamento nella parte superiore, che ti consente di vedere la struttura dell'allenamento e di trascinare i passi per riordinarli.

### Tipi di Passi

Garmin Planner supporta diversi tipi di passi:

- **warmup**: Riscaldamento
- **interval**: Intervallo di lavoro
- **recovery**: Recupero tra intervalli
- **cooldown**: Defaticamento
- **rest**: Pausa
- **repeat**: Sezione da ripetere multipla volta
- **other**: Altro tipo di passo

Per ciascun passo, puoi specificare:
- **Durata/Distanza**: Può essere in minuti (min), chilometri (km), metri (m) o tramite pulsante lap (lap-button)
- **Intensità**: Può essere basata su ritmo (pace) o frequenza cardiaca (hr)
- **Descrizione**: Una descrizione opzionale del passo

Esempio di definizione di un passo:
```
10min @ Z2 -- Corsa lenta a ritmo costante
```

Questo indica un passo di 10 minuti alla zona di ritmo Z2, con la descrizione "Corsa lenta a ritmo costante".

### Gestione delle Ripetizioni

Per creare una sezione di ripetizioni:

1. Clicca su "Aggiungi ripetizione"
2. Inserisci il numero di ripetizioni
3. Aggiungi i passi da ripetere (intervallo, recupero, ecc.)
4. Clicca su "OK" per confermare

Le ripetizioni sono visualizzate come blocchi circondati da una linea tratteggiata nell'anteprima grafica, con l'indicazione del numero di ripetizioni.

### Configurazione delle Zone

Puoi configurare zone di ritmo e frequenza cardiaca cliccando su "Modifica Configurazione":

#### Zone di Ritmo (Paces)

Puoi definire zone di ritmo in diversi formati:
- Direttamente come ritmo: `5:30` (minuti:secondi per km)
- Come intervallo di ritmi: `5:30-5:10`
- In base alla distanza e tempo: `10km in 45:00`
- Come percentuale di un altro ritmo: `80-85% marathon`

#### Zone di Frequenza Cardiaca (Heart Rates)

Puoi definire zone di frequenza cardiaca in diversi formati:
- Come valore fisso: `150`
- Come intervallo: `150-160`
- Come percentuale della frequenza massima: `70-76% max_hr`

#### Margini

I margini definiscono le tolleranze per ritmi e frequenze cardiache:
- `faster`: Margine per un ritmo più veloce (es. "0:03" = 3 secondi più veloce)
- `slower`: Margine per un ritmo più lento (es. "0:03" = 3 secondi più lento)
- `hr_up`: Margine per una frequenza cardiaca più alta (in %)
- `hr_down`: Margine per una frequenza cardiaca più bassa (in %)

## Funzionalità Avanzate

### Modifica delle Date

Puoi modificare le date di pianificazione in diversi modi:

1. **Direttamente nei file YAML**: Aggiungi un elemento `date` come primo passo di un allenamento
   ```yaml
   "W01S01 Easy Run":
     - date: "2023-06-01"
     - warmup: "10min @ Z1_HR"
     - interval: "30min @ Z2"
     - cooldown: "5min @ Z1_HR"
   ```

2. **Tramite il file Excel**: Modifica la colonna "Date" nel foglio Workouts

3. **Tramite l'interfaccia di pianificazione**: Modifica la data della gara e i giorni preferiti per ricalcolare la pianificazione



## Risoluzione dei Problemi

### Problemi di Login

Se hai problemi di accesso a Garmin Connect:

1. Assicurati di avere una connessione internet attiva
2. Verifica che le tue credenziali Garmin Connect siano corrette
3. Prova a cliccare su "Aggiorna credenziali" nella scheda Login
4. Controlla la cartella OAuth per verificare che i file di autenticazione siano presenti

### Problemi di Importazione/Esportazione

Se hai problemi con l'importazione o l'esportazione di allenamenti:

1. Controlla il log per messaggi di errore specifici
2. Verifica che il formato del file YAML sia corretto
3. Assicurati di avere effettuato l'accesso a Garmin Connect
4. Verifica che il file di input o la cartella di output esistano e siano accessibili

### Problemi di Pianificazione

Se hai problemi con la pianificazione degli allenamenti:

1. Verifica di aver selezionato il numero corretto di giorni per settimana (in base al piano di allenamento)
2. Controlla che la data della gara sia nel futuro
3. Assicurati che gli allenamenti siano stati importati correttamente
4. Verifica nel log eventuali messaggi di errore relativi alla pianificazione
