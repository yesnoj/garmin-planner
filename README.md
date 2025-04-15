# Guida completa a Garmin Planner

Garmin Planner è un'applicazione potente per la gestione e pianificazione degli allenamenti su Garmin Connect. Questo strumento consente di importare, esportare e pianificare allenamenti in modo semplice ed efficace, automatizzando molte delle operazioni ripetitive che normalmente dovresti fare manualmente nell'interfaccia di Garmin Connect.

## Indice
1. [Introduzione e panoramica](#introduzione-e-panoramica)
2. [Installazione e primo avvio](#installazione-e-primo-avvio)
3. [Interfaccia grafica (GUI)](#interfaccia-grafica-gui)
4. [Pianificazione degli allenamenti](#pianificazione-degli-allenamenti)
5. [Conversione Excel a YAML](#conversione-excel-a-yaml)
6. [Struttura e formato degli allenamenti](#struttura-e-formato-degli-allenamenti)
7. [Editor di allenamenti](#editor-di-allenamenti)
8. [Esempi pratici](#esempi-pratici)
9. [Risoluzione dei problemi](#risoluzione-dei-problemi)
10. [FAQ](#faq)

## Introduzione e panoramica

Garmin Planner è nato per risolvere un problema comune tra gli atleti che utilizzano Garmin Connect: la difficoltà di creare e pianificare allenamenti complessi. Con questa applicazione, puoi:

- Importare e esportare allenamenti in formato YAML
- Creare piani di allenamento completi in Excel e convertirli in YAML
- Pianificare automaticamente gli allenamenti nel calendario di Garmin Connect
- Modificare facilmente gli allenamenti con un editor visuale intuitivo
- Gestire i tuoi allenamenti tramite un'interfaccia grafica semplice da usare

## Installazione e primo avvio

### Installazione
1. Scarica l'ultima versione di Garmin Planner dal sito ufficiale
2. Fai doppio clic sul file di installazione e segui le istruzioni a schermo
3. Una volta completata l'installazione, avvia Garmin Planner dal menu Start o dall'icona sul desktop

### Primo avvio
1. Al primo avvio, ti verrà richiesto di effettuare il login a Garmin Connect
2. Inserisci le tue credenziali di Garmin Connect (email e password)
3. L'applicazione salverà in modo sicuro i token di autenticazione per le sessioni future

## Interfaccia grafica (GUI)

L'interfaccia grafica di Garmin Planner è divisa in diverse schede, ognuna dedicata a una funzionalità specifica:

### Scheda Login
Qui puoi effettuare il login a Garmin Connect. La scheda mostra lo stato corrente della connessione e ti permette di:
- Effettuare il login con le tue credenziali Garmin
- Verificare lo stato della connessione
- Eseguire il logout

**Come effettuare il login:**
1. Fai clic su "Effettua login"
2. Inserisci la tua email e password di Garmin Connect
3. Attendi la conferma di avvenuto login

### Scheda Importa
Qui puoi importare allenamenti da file YAML a Garmin Connect:
- Seleziona un file YAML contenente gli allenamenti
- Opzionalmente sostituisci allenamenti esistenti con lo stesso nome
- Importa tutti gli allenamenti o solo quelli selezionati

### Scheda Esporta
Consente di esportare allenamenti da Garmin Connect:
- Visualizza la lista degli allenamenti disponibili
- Seleziona gli allenamenti da esportare
- Scegli tra formato YAML o JSON
- Opzionalmente pulisci i dati non necessari

### Scheda Pianificazione
Permette di pianificare gli allenamenti in modo visuale e strutturato:
1. Inserisci i dati dell'atleta e la data della gara
2. Seleziona i giorni preferiti per gli allenamenti
3. Converti il piano Excel in YAML
4. Pianifica gli allenamenti sul calendario Garmin

### Scheda Editor Allenamenti
Un editor visuale completo per creare e modificare allenamenti:
- Crea nuovi allenamenti da zero
- Modifica allenamenti esistenti
- Visualizza graficamente la struttura dell'allenamento
- Salva e carica allenamenti da file YAML

## Pianificazione degli allenamenti

La pianificazione degli allenamenti è una delle funzionalità più potenti di Garmin Planner. Permette di organizzare automaticamente i tuoi allenamenti nel calendario di Garmin Connect.

### Procedura guidata in 4 step

1. **Step 1: Pianificazione Allenamenti**
   - Inserisci il nome dell'atleta
   - Seleziona la data della gara
   - Scegli i giorni preferiti per gli allenamenti
   - Crea un template Excel o seleziona un file esistente

2. **Step 2: Conversione Excel → YAML**
   - Converti il file Excel in formato YAML
   - Questo YAML contiene tutti i dettagli degli allenamenti

3. **Step 3: Informazioni Piano**
   - Visualizza le informazioni sul piano creato
   - Verifica il numero di allenamenti e settimane
   - Controlla le date pianificate

4. **Step 4: Pianificazione Calendar**
   - Simula la pianificazione per verificare
   - Pianifica effettivamente gli allenamenti su Garmin Connect
   - Visualizza e gestisci gli allenamenti pianificati

### Esempio di pianificazione

Supponiamo di voler pianificare un piano di 12 settimane per una mezza maratona:

1. Inserisci "Mario Rossi" come nome atleta
2. Seleziona la data della gara (es. 15 Ottobre 2023)
3. Seleziona martedì, giovedì e domenica come giorni preferiti
4. Crea il template Excel con "Crea Template Piano"
5. Completa il piano nel file Excel generato
6. Torna nell'app e converti il file in YAML
7. Verifica le informazioni del piano
8. Simula la pianificazione per controllare le date
9. Pianifica gli allenamenti sul calendario

## Conversione Excel a YAML

La conversione da Excel a YAML è perfetta per chi preferisce creare i propri piani di allenamento in Excel.

### Struttura del file Excel

Il file Excel deve contenere quattro fogli:
1. **Config**: Impostazioni generali del piano
2. **Paces**: Definizione dei ritmi di corsa
3. **HeartRates**: Definizione delle zone di frequenza cardiaca
4. **Workouts**: Gli allenamenti veri e propri

### Foglio Workouts

Il foglio Workouts deve avere questa struttura:
- Riga 1: Nome dell'atleta (Atleta: Mario Rossi)
- Riga 2: Intestazioni (Week, Date, Session, Description, Steps)
- Righe successive: Allenamenti

Esempio:
```
| Week | Date       | Session | Description  | Steps                                         |
|------|------------|---------|--------------|-----------------------------------------------|
| 1    | 2023-09-01 | 1       | Easy run     | warmup: 10min @ Z1                           |
|      |            |         |              | interval: 30min @ Z2                          |
|      |            |         |              | cooldown: 5min @ Z1                           |
| 1    | 2023-09-03 | 2       | Intervals    | warmup: 15min @ Z1                           |
|      |            |         |              | repeat 5:                                     |
|      |            |         |              |   interval: 400m @ Z5                         |
|      |            |         |              |   recovery: 2min @ Z1                         |
|      |            |         |              | cooldown: 10min @ Z1                          |
```

### Esecuzione della conversione

1. Nella scheda "Pianificazione", seleziona il file Excel
2. Fai click su "Converti Excel → YAML"
3. Seleziona dove salvare il file YAML risultante
4. Il file YAML è ora pronto per essere importato in Garmin Connect

## Struttura e formato degli allenamenti

La corretta struttura degli allenamenti è fondamentale per il funzionamento di Garmin Planner e per la pianificazione automatica.

### Convenzione di denominazione degli allenamenti

Per permettere la pianificazione automatica, gli allenamenti devono seguire una specifica convenzione di denominazione:

```
[PREFISSO] WxxSyy Descrizione
```

Dove:
- **[PREFISSO]**: Un prefisso opzionale definito nella configurazione (es. "HM_" per mezza maratona)
- **Wxx**: Indica la settimana (es. W01 = prima settimana, W12 = dodicesima settimana)
- **Syy**: Indica la sessione all'interno della settimana (es. S01 = prima sessione, S03 = terza sessione)
- **Descrizione**: Breve descrizione dell'allenamento (es. "Easy Run", "Intervals", "Long Run")

Esempi di nomi corretti:
- `W01S01 Easy Run`
- `HM_W04S02 Hill Intervals`
- `MYRUN_123 W12S03 Race Pace`

### Perché questa struttura è importante

Questa convenzione permette a Garmin Planner di:
1. **Raggruppare gli allenamenti** per piano (tramite il prefisso)
2. **Ordinare correttamente** le settimane e le sessioni
3. **Pianificare automaticamente** in base alla data della gara e ai giorni selezionati
4. **Tracciare la progressione** all'interno del piano

Senza questa struttura, la pianificazione automatica non funzionerà correttamente.

### Tipi di passi (step) supportati

Gli step dell'allenamento possono essere di vari tipi:
- **warmup**: Riscaldamento
- **interval**: Intervallo di lavoro
- **recovery**: Recupero
- **cooldown**: Defaticamento
- **rest**: Riposo
- **repeat**: Ripetizioni di una sequenza di passi

La sintassi per ogni step è:
```
tipo: durata/distanza @ zona [-- descrizione]
```

Esempi:
- `warmup: 10min @ Z1`
- `interval: 5km @ Z3 -- Corsa a ritmo medio`
- `recovery: 2min @ Z1`
- `interval: 400m @ Z5 -- Sprint`

Per le ripetizioni:
```
repeat 5:
  interval: 400m @ Z5
  recovery: 2min @ Z1
```

### Unità di misura supportate

- **Tempo**: min (minuti), h (ore), s (secondi)
- **Distanza**: m (metri), km (chilometri)
- **Altro**: lap-button (pulsante lap)

### Zone di ritmo e frequenza cardiaca

Le zone possono essere definite nel foglio configurazione o nell'editor:

#### Zone di ritmo (Paces)
- Possono essere definite come intervalli (es. "5:30-5:10")
- Possono essere calcolate da una prestazione (es. "10km in 45:00")
- Possono essere relative ad altre zone (es. "80-85% marathon")

#### Zone di frequenza cardiaca (Heart Rates)
- Possono essere definite come intervalli (es. "150-160")
- Possono essere relative a una frequenza massima (es. "70-76% max_hr")
- Possono essere specificate come zone standardizzate (es. "Z1", "Z2")

## Editor di allenamenti

L'editor di allenamenti è uno strumento visuale per creare e modificare facilmente gli allenamenti senza dover conoscere la sintassi YAML.

### Interfaccia principale

L'interfaccia dell'editor è divisa in:
- **Lista degli allenamenti**: Visualizza tutti gli allenamenti disponibili
- **Pulsanti di gestione**: Per creare, modificare ed eliminare allenamenti
- **Pulsanti di file**: Per caricare e salvare allenamenti da/su file

### Editor di un singolo allenamento

Quando crei o modifichi un allenamento, vedrai:
- **Nome dell'allenamento**: Campo per inserire il nome (formato consigliato: W01S01 Descrizione)
- **Anteprima grafica**: Rappresentazione visuale dell'allenamento
- **Lista dei passi**: Dettagli di tutti i passi dell'allenamento
- **Pulsanti di gestione**: Per aggiungere, modificare, rimuovere e riordinare i passi

### Creazione di un allenamento

Esempio di creazione di un allenamento:

1. Fai click su "Nuovo allenamento"
2. Inserisci nome "W01S01 Easy Run"
3. Aggiungi un passo di riscaldamento:
   - Fai click su "Aggiungi passo"
   - Seleziona tipo "warmup"
   - Inserisci durata "10" e unità "min"
   - Seleziona zona di ritmo "Z1"
   - Fai click su "OK"
4. Aggiungi un intervallo principale:
   - Fai click su "Aggiungi passo"
   - Seleziona tipo "interval"
   - Inserisci durata "30" e unità "min"
   - Seleziona zona di ritmo "Z2"
   - Inserisci descrizione "Corsa facile"
   - Fai click su "OK"
5. Aggiungi un defaticamento:
   - Fai click su "Aggiungi passo"
   - Seleziona tipo "cooldown"
   - Inserisci durata "5" e unità "min"
   - Seleziona zona di ritmo "Z1"
   - Fai click su "OK"
6. Fai click su "Salva" per completare l'allenamento

### Creazione di ripetizioni

Per aggiungere ripetizioni:

1. Fai click su "Aggiungi ripetizione"
2. Inserisci il numero di ripetizioni (es. 5)
3. Aggiungi passi alla ripetizione:
   - Fai click su "Aggiungi passo"
   - Inserisci i dettagli del passo
   - Ripeti per tutti i passi necessari
4. Fai click su "OK" per salvare la ripetizione

### Configurazione dei ritmi e frequenze cardiache

Per personalizzare ritmi e frequenze cardiache:

1. Fai click su "Modifica Configurazione"
2. Vai alla scheda "Ritmi" per configurare i ritmi
3. Vai alla scheda "Frequenze Cardiache" per configurare le zone FC
4. Imposta i margini di tolleranza nella scheda "Margini"
5. Fai click su "OK" per salvare la configurazione

## Esempi pratici

### Esempio 1: Piano completo per una mezza maratona

In questo esempio, creeremo un piano completo di 12 settimane per una mezza maratona:

1. **Creazione del file Excel:**
   - Avvia l'applicazione e vai alla scheda "Pianificazione"
   - Compila i dati dell'atleta e seleziona la data della gara
   - Seleziona i giorni martedì, giovedì e domenica
   - Fai click su "Crea Template Piano"
   - Si aprirà un file Excel con una struttura predefinita
   - Completa il file Excel con i dettagli degli allenamenti, assicurandoti di seguire il formato corretto

2. **Esempio di come compilare il file Excel:**
   
   **Foglio Config:**
   ```
   Parameter | Value    | Slower  | HR Up | HR Down
   ----------|----------|---------|-------|--------
   name_prefix | HM_PLAN_ |         |       |
   margins   | 0:03     | 0:03    | 5     | 5
   race_day  | 2023-10-15|         |       |
   ```

   **Foglio Paces:**
   ```
   Name      | Value
   ----------|-------
   Z1        | 6:30
   Z2        | 6:00
   Z3        | 5:30
   Z4        | 5:00
   Z5        | 4:30
   race_pace | 5:10
   ```

   **Foglio HeartRates:**
   ```
   Name      | Value
   ----------|-------
   max_hr    | 180
   Z1        | 62-76% max_hr
   Z2        | 76-85% max_hr
   Z3        | 85-91% max_hr
   Z4        | 91-95% max_hr
   Z5        | 95-100% max_hr
   ```

   **Foglio Workouts:**
   ```
   Week | Date       | Session | Description     | Steps
   -----|------------|---------|-----------------|------
   1    |            | 1       | Easy Run        | warmup: 10min @ Z1
        |            |         |                 | interval: 30min @ Z2
        |            |         |                 | cooldown: 5min @ Z1
   1    |            | 2       | Intervals       | warmup: 15min @ Z1
        |            |         |                 | repeat 5:
        |            |         |                 |   interval: 400m @ Z5
        |            |         |                 |   recovery: 2min @ Z1
        |            |         |                 | cooldown: 10min @ Z1
   1    |            | 3       | Long Run        | warmup: 10min @ Z1
        |            |         |                 | interval: 60min @ Z2
        |            |         |                 | cooldown: 5min @ Z1
   ```

3. **Conversione in YAML:**
   - Ritorna all'applicazione
   - Vai al secondo step e fai click su "Converti Excel → YAML"
   - Verifica le informazioni del piano nel terzo step

4. **Importazione in Garmin Connect:**
   - Vai alla scheda "Importa"
   - Seleziona il file YAML appena creato
   - Fai click su "Importa"

5. **Pianificazione nel calendario:**
   - Torna alla scheda "Pianificazione" e vai al quarto step
   - Fai click su "Simula Pianificazione" per verificare
   - Fai click su "Pianifica Allenamenti" per confermare

### Esempio 2: Creazione di un allenamento a intervalli avanzato

Creiamo un allenamento a intervalli avanzato con l'editor:

1. **Avvio dell'editor:**
   - Vai alla scheda "Editor Allenamenti"
   - Fai click su "Nuovo allenamento"
   - Inserisci nome "W05S02 Interval Training"

2. **Creazione della struttura:**
   - Aggiungi un riscaldamento di 15min @ Z1
   - Aggiungi una ripetizione di 6 volte:
     - Intervallo di 400m @ Z5
     - Recupero di 90sec @ Z1
   - Aggiungi un intervallo di 5min @ Z2
   - Aggiungi una ripetizione di 4 volte:
     - Intervallo di 200m @ Z5
     - Recupero di 60sec @ Z1
   - Aggiungi un defaticamento di 10min @ Z1

3. **Salvataggio e esportazione:**
   - Fai click su "Salva" per completare l'allenamento
   - Torna alla lista degli allenamenti
   - Fai click su "Salva su file" per esportare in YAML

### Esempio 3: Allenamento con ripetute e descrizioni personalizzate

Ecco un esempio di come impostare un allenamento con ripetute e descrizioni dettagliate:

```
Nome: W08S02 Hill Intervals

Passi:
- warmup: 15min @ Z1 -- Riscaldamento progressivo
- interval: 5min @ Z2 -- Avvicinamento alla collina
- repeat 6:
  - interval: 1min @ Z5 -- Salita a massima potenza
  - recovery: 90sec @ Z1 -- Recupero in discesa
- interval: 10min @ Z2 -- Transizione verso casa
- cooldown: 10min @ Z1 -- Defaticamento
```

Questo allenamento include:
- Un riscaldamento specifico con descrizione
- Un intervallo di avvicinamento
- 6 ripetute su salita con recupero in discesa
- Un intervallo di transizione
- Un defaticamento finale

## Risoluzione dei problemi

### Problemi di login

**Problema**: Non riesco ad accedere a Garmin Connect.
**Soluzione**: 
1. Verifica le credenziali (email e password)
2. Assicurati di avere una connessione a Internet attiva
3. Prova a effettuare nuovamente il login
4. Riavvia l'applicazione se il problema persiste

### Errori di importazione

**Problema**: Errore durante l'importazione degli allenamenti.
**Soluzione**:
1. Verifica che il file YAML sia formattato correttamente
2. Controlla la sintassi degli allenamenti
3. Assicurati di essere connesso a Garmin Connect
4. Prova a importare un singolo allenamento alla volta

### Errori di pianificazione

**Problema**: Gli allenamenti non vengono pianificati correttamente.
**Soluzione**:
1. Verifica che gli allenamenti siano stati importati correttamente
2. Controlla che i nomi degli allenamenti seguano il formato corretto (es. W01S01)
3. Assicurati che la data della gara sia nel futuro
4. Prova prima la modalità "Simula Pianificazione" per verificare

### Problemi con l'editor

**Problema**: L'editor non visualizza correttamente gli allenamenti.
**Soluzione**:
1. Verifica che il file YAML caricato abbia la struttura corretta
2. Prova a creare un nuovo allenamento da zero
3. Riavvia l'applicazione se persiste il problema

### Errori nel file Excel

**Problema**: La conversione Excel a YAML fallisce.
**Soluzione**:
1. Verifica che la struttura del file Excel sia corretta
2. Controlla che tutti i fogli necessari siano presenti
3. Assicurati che i nomi degli allenamenti seguano il formato corretto
4. Verifica che i passi degli allenamenti usino la sintassi corretta
5. Prova a utilizzare il template generato dall'applicazione

## FAQ

### Domande generali

**D: Posso usare Garmin Planner senza un account Garmin Connect?**
R: No, Garmin Planner richiede un account Garmin Connect valido per funzionare, in quanto interagisce direttamente con il servizio di Garmin.

**D: I miei dati sono al sicuro?**
R: Garmin Planner salva localmente solo i token di autenticazione necessari per comunicare con Garmin Connect. Le credenziali complete non vengono mai memorizzate.

**D: Quali tipi di allenamento posso creare?**
R: Puoi creare allenamenti per corsa, ciclismo, nuoto e altri sport supportati da Garmin Connect, con vari tipi di passi come riscaldamento, intervalli, recupero, etc.

### Domande sulla pianificazione

**D: Quanti allenamenti posso pianificare alla volta?**
R: Non c'è un limite specifico, ma si consiglia di pianificare un piano di allenamento alla volta per evitare sovrapposizioni.

**D: Posso pianificare allenamenti ripetitivi (es. ogni lunedì)?**
R: Sì, puoi selezionare i giorni della settimana preferiti e Garmin Planner pianificherà gli allenamenti in quei giorni.

**D: Cosa succede se ho già allenamenti pianificati in quelle date?**
R: Garmin Planner non sovrascrive automaticamente gli allenamenti esistenti, ma puoi utilizzare l'opzione "Rimuovi Pianificazione" per rimuoverli prima di pianificare.

**D: Perché è importante che i nomi degli allenamenti seguano il formato WxxSyy?**
R: Questo formato permette a Garmin Planner di organizzare gli allenamenti in settimane e sessioni, fondamentale per la pianificazione automatica. Senza questo formato, l'applicazione non sarebbe in grado di determinare la sequenza corretta degli allenamenti.

### Domande sull'Editor

**D: Posso importare allenamenti esistenti in Garmin Connect nell'editor?**
R: Sì, puoi esportare gli allenamenti da Garmin Connect in YAML e poi caricarli nell'editor.

**D: Quali zone di ritmo e frequenza cardiaca posso utilizzare?**
R: Puoi definire zone personalizzate nell'editor di configurazione o utilizzare le zone predefinite (Z1-Z5).

**D: Posso condividere i miei allenamenti con altri utenti?**
R: Sì, puoi esportare i tuoi allenamenti in file YAML e condividerli. Altri utenti potranno importarli nella loro istanza di Garmin Planner.

**D: Come posso trasformare un piano di allenamento da PDF o da un sito web in Garmin Planner?**
R: Il modo più semplice è creare un file Excel seguendo la struttura descritta in questa guida, inserendo ogni allenamento nel formato corretto. Poi usa la funzione di conversione Excel → YAML e importa gli allenamenti in Garmin Connect.

---

Questa guida ti ha fornito una panoramica dettagliata di Garmin Planner, concentrandosi sulle funzionalità dell'interfaccia grafica e sulla corretta strutturazione degli allenamenti. Per ulteriori informazioni o supporto, consulta la documentazione online.
